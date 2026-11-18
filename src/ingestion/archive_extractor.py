"""
Archive Inventory & Safe Extraction Utilities

Provides read-only inspection and sanitized extraction of official data pack
ZIP archives while preserving original source files and filtering OS metadata.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import zipfile

from config.settings import RAW_DATA_DIR

IGNORED_PATH_PARTS = {"__MACOSX"}
IGNORED_FILENAMES = {".DS_Store", "Thumbs.db"}
DEFAULT_ALLOWED_EXTENSIONS = {".csv", ".pdf"}


@dataclass(frozen=True)
class ArchiveEntry:
    """Metadata describing a single non-directory member in a ZIP archive."""

    archive_path: str
    filename: str
    extension: str
    file_size_bytes: int
    compressed_size_bytes: int


def is_ignored_member(member_name: str) -> bool:
    """Return True if an archive member is macOS/Windows OS metadata or a directory."""
    if member_name.endswith("/"):
        return True
    parts = Path(member_name).parts
    if any(part in IGNORED_PATH_PARTS for part in parts):
        return True
    filename = Path(member_name).name
    return filename in IGNORED_FILENAMES or filename.startswith("._")


def find_data_pack_archive(raw_dir: Path = RAW_DATA_DIR) -> Path:
    """Locate the official data pack ZIP archive inside the raw data directory.

    Prefers ``data_pack.zip`` if present, otherwise matches ``*data_pack*.zip``.
    Raises ``FileNotFoundError`` if no matching archive is found, or ``ValueError``
    if multiple ambiguous archives match.
    """
    exact = raw_dir / "data_pack.zip"
    if exact.is_file():
        return exact

    candidates = sorted(raw_dir.glob("*data_pack*.zip"))
    if not candidates:
        raise FileNotFoundError(
            f"No data pack ZIP archive found in {raw_dir}"
        )
    if len(candidates) > 1:
        names = ", ".join(p.name for p in candidates)
        raise ValueError(
            f"Multiple candidate data pack archives found in {raw_dir}: {names}"
        )
    return candidates[0]


def inventory_zip_archive(
    archive_path: Path,
    verify_crc: bool = True,
) -> list[ArchiveEntry]:
    """Inspect a ZIP archive and return non-metadata file entries without extracting.

    Optionally validates CRC checksums for all members in memory.
    """
    if not archive_path.is_file():
        raise FileNotFoundError(f"Archive not found: {archive_path}")

    with zipfile.ZipFile(archive_path, mode="r") as zf:
        if verify_crc:
            bad_member = zf.testzip()
            if bad_member is not None:
                raise zipfile.BadZipFile(
                    f"Corrupted archive member detected: {bad_member}"
                )

        entries: list[ArchiveEntry] = []
        for info in zf.infolist():
            if is_ignored_member(info.filename):
                continue
            member_path = Path(info.filename)
            entries.append(
                ArchiveEntry(
                    archive_path=info.filename,
                    filename=member_path.name,
                    extension=member_path.suffix.lower(),
                    file_size_bytes=info.file_size,
                    compressed_size_bytes=info.compress_size,
                )
            )
    return entries


def extract_data_pack(
    archive_path: Path,
    target_dir: Path,
    allowed_extensions: set[str] | None = None,
    flatten_top_dir: bool = True,
    overwrite: bool = False,
) -> list[Path]:
    """Safely extract allowed files from a ZIP archive while preserving the source ZIP.

    Filters out OS metadata (``__MACOSX``, ``.DS_Store``, ``._*``), validates against
    path traversal, and writes extracted files into ``target_dir``.
    """
    if allowed_extensions is None:
        allowed_extensions = DEFAULT_ALLOWED_EXTENSIONS
    normalized_exts = {ext.lower() for ext in allowed_extensions}

    target_dir.mkdir(parents=True, exist_ok=True)
    resolved_target = target_dir.resolve()
    extracted_paths: list[Path] = []

    with zipfile.ZipFile(archive_path, mode="r") as zf:
        bad_member = zf.testzip()
        if bad_member is not None:
            raise zipfile.BadZipFile(
                f"Corrupted archive member detected: {bad_member}"
            )

        for info in zf.infolist():
            if is_ignored_member(info.filename):
                continue

            member_path = Path(info.filename)
            if member_path.suffix.lower() not in normalized_exts:
                continue

            raw_dest = (resolved_target / info.filename).resolve()
            if not raw_dest.is_relative_to(resolved_target):
                raise ValueError(
                    f"Unsafe archive member path blocked (Zip-Slip attempt): {info.filename}"
                )

            rel_path = (
                Path(member_path.name)
                if flatten_top_dir
                else Path(*[p for p in member_path.parts if p not in {".", ".."}])
            )
            dest_path = (resolved_target / rel_path).resolve()
            if not dest_path.is_relative_to(resolved_target):
                raise ValueError(
                    f"Unsafe archive member path blocked: {info.filename}"
                )

            dest_path.parent.mkdir(parents=True, exist_ok=True)
            if dest_path.exists() and not overwrite:
                extracted_paths.append(dest_path)
                continue

            with zf.open(info, mode="r") as src, dest_path.open("wb") as dst:
                while chunk := src.read(1024 * 1024):
                    dst.write(chunk)
            extracted_paths.append(dest_path)

    return extracted_paths
