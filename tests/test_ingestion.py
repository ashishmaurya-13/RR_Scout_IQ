import csv
import io
import zipfile
from pathlib import Path
import pytest

from src.ingestion.archive_extractor import (
    find_data_pack_archive,
    inventory_zip_archive,
    is_ignored_member,
    extract_data_pack,
)
from src.ingestion.profiler import (
    check_candidate_key,
    profile_csv_file,
    check_foreign_key_coverage,
    write_data_dictionary_csv,
    build_data_dictionary_rows,
)


class TestArchiveExtractor:
    """Unit tests for archive discovery, metadata filtering, and safe extraction."""

    def test_is_ignored_member(self):
        assert is_ignored_member("__MACOSX/._competitions.csv") is True
        assert is_ignored_member(".DS_Store") is True
        assert is_ignored_member("folder/.DS_Store") is True
        assert is_ignored_member("Thumbs.db") is True
        assert is_ignored_member("data_pack/competitions.csv") is False
        assert is_ignored_member("matches.csv") is False

    def test_find_data_pack_archive(self, tmp_path: Path):
        with pytest.raises(FileNotFoundError):
            find_data_pack_archive(tmp_path)

        # Create matching archive
        archive_path = tmp_path / "custom_data_pack.zip"
        with zipfile.ZipFile(archive_path, "w") as zf:
            zf.writestr("test.csv", "a,b\n1,2")

        found = find_data_pack_archive(tmp_path)
        assert found == archive_path

    def test_inventory_zip_archive(self, tmp_path: Path):
        archive_path = tmp_path / "test_pack.zip"
        with zipfile.ZipFile(archive_path, "w") as zf:
            zf.writestr("__MACOSX/._test.csv", "meta")
            zf.writestr(".DS_Store", "junk")
            zf.writestr("data/matches.csv", "match_id,result\n1,Won\n2,Lost")

        entries = inventory_zip_archive(archive_path, verify_crc=True)
        assert len(entries) == 1
        assert entries[0].filename == "matches.csv"
        assert entries[0].extension == ".csv"
        assert entries[0].file_size_bytes > 0

    def test_extract_data_pack_zip_slip_prevention(self, tmp_path: Path):
        archive_path = tmp_path / "malicious.zip"
        with zipfile.ZipFile(archive_path, "w") as zf:
            # Dangerous path attempting to escape with allowed extension
            zf.writestr("../evil.csv", "exploit")

        target_dir = tmp_path / "extracted"
        with pytest.raises(ValueError, match="Zip-Slip"):
            extract_data_pack(archive_path, target_dir, flatten_top_dir=False)

    def test_extract_data_pack_success(self, tmp_path: Path):
        archive_path = tmp_path / "valid.zip"
        with zipfile.ZipFile(archive_path, "w") as zf:
            zf.writestr("pack/table.csv", "id,val\n10,A\n20,B\n")
            zf.writestr("pack/.DS_Store", "ignore")

        target_dir = tmp_path / "extracted"
        extracted = extract_data_pack(archive_path, target_dir, flatten_top_dir=True)

        assert len(extracted) == 1
        assert extracted[0].name == "table.csv"
        assert (target_dir / "table.csv").exists()
        assert not (target_dir / ".DS_Store").exists()


class TestProfiler:
    """Unit tests for DuckDB-based table profiling, key checks, and data dictionaries."""

    @pytest.fixture
    def sample_csvs(self, tmp_path: Path):
        parent_csv = tmp_path / "parent.csv"
        child_csv = tmp_path / "child.csv"

        with parent_csv.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["id", "name", "category"])
            writer.writerow([1, "Alpha", "A"])
            writer.writerow([2, "Beta", "B"])
            writer.writerow([3, "Gamma", "C"])

        with child_csv.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["child_id", "parent_id", "score", "match_date"])
            writer.writerow([101, 1, 50.5, "2024-01-01"])
            writer.writerow([102, 2, 75.0, "2024-01-02"])
            writer.writerow([103, 999, 0.0, "2024-01-03"])  # 999 is orphan

        return parent_csv, child_csv

    def test_check_candidate_key(self, sample_csvs):
        import duckdb
        parent_csv, _ = sample_csvs
        con = duckdb.connect(":memory:")
        try:
            con.execute(f"CREATE TABLE parent AS SELECT * FROM read_csv_auto('{parent_csv.as_posix()}', header=true)")
            key_res = check_candidate_key(con, "parent", ["id"], {"id", "name", "category"})
            assert key_res.is_unique_not_null is True
            assert key_res.unique_count == 3
            assert key_res.duplicate_row_count == 0

            # Missing column check
            with pytest.raises(KeyError, match="Columns not found"):
                check_candidate_key(con, "parent", ["unknown"], {"id", "name", "category"})
        finally:
            con.close()

    def test_profile_csv_file(self, sample_csvs):
        parent_csv, _ = sample_csvs
        profile = profile_csv_file(parent_csv, candidate_keys=[["id"]])
        assert profile.row_count == 3
        assert profile.column_count == 3
        assert profile.exact_duplicate_rows == 0

        col_map = {c.column_name: c for c in profile.columns}
        assert "id" in col_map
        assert "name" in col_map
        assert col_map["id"].null_count == 0
        assert col_map["id"].unique_count == 3

    def test_check_foreign_key_coverage(self, sample_csvs):
        parent_csv, child_csv = sample_csvs
        coverage = check_foreign_key_coverage(child_csv, "parent_id", parent_csv, "id")
        assert coverage["child_unique_keys"] == 3
        assert coverage["parent_unique_keys"] == 3
        assert coverage["matched_keys"] == 2
        assert coverage["orphan_child_keys"] == 1
        assert "999" in coverage["sample_orphan_keys"]

    def test_write_data_dictionary_csv(self, sample_csvs, tmp_path: Path):
        parent_csv, _ = sample_csvs
        profile = profile_csv_file(parent_csv, candidate_keys=[["id"]])
        dict_path = tmp_path / "dict.csv"

        descriptions = {("parent", "id"): "Unique record identifier"}
        written = write_data_dictionary_csv([profile], dict_path, descriptions=descriptions)

        assert written.exists()
        with written.open(encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            assert len(rows) == 3
            assert rows[0]["column_name"] == "id"
            assert rows[0]["audit_notes"] == "Unique record identifier"
