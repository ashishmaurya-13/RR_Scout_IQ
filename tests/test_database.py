"""
RR ScoutIQ — Database & Ingestion Test Suite
Unit tests for DuckDB connection, schema initialization, table loading,
referential integrity, constraint enforcement, and full statistical reconciliation.
"""

from __future__ import annotations
import csv
from pathlib import Path
import duckdb
import pytest

from src.ingestion.database import get_duckdb_connection, initialize_schema
from src.ingestion.load_data import (
    load_all_tables,
    validate_database_relationships,
)


class TestDatabaseManager:
    """Tests for database connectivity and schema DDL initialization."""

    def test_in_memory_connection(self):
        con = get_duckdb_connection(":memory:")
        assert con is not None
        res = con.execute("SELECT 1 AS val").fetchone()[0]
        assert res == 1
        con.close()

    def test_file_connection_and_schema_init(self, tmp_path: Path):
        db_file = tmp_path / "test_cricket.duckdb"
        con = get_duckdb_connection(db_file)
        initialize_schema(con)

        # Verify tables created
        tables = set(r[0] for r in con.execute("SHOW TABLES").fetchall())
        expected = {
            "dim_competition",
            "dim_team",
            "fact_match",
            "bridge_competition_team_player",
            "fact_playing_eleven",
            "fact_delivery",
        }
        assert expected.issubset(tables)
        con.close()
        assert db_file.exists()


class TestIngestionPipeline:
    """Tests for idempotent table loading and relationship audits using synthetic data."""

    @pytest.fixture
    def synthetic_data_dir(self, tmp_path: Path) -> Path:
        raw_dir = tmp_path / "data" / "raw"
        extracted_dir = raw_dir / "extracted"
        extracted_dir.mkdir(parents=True, exist_ok=True)

        # 1. competitions.csv
        with (extracted_dir / "competitions.csv").open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["comp_id", "comp_name", "match_format", "season"])
            w.writerow([101, "IPL 2024", "T20", "2024"])
            w.writerow([102, "India in SA T20I 2024", "T20I", "2024"])

        # 2. teams.csv
        with (extracted_dir / "teams.csv").open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["comp_id", "team_id", "team_name"])
            w.writerow([101, 1, "Rajasthan Royals"])
            w.writerow([101, 2, "Chennai Super Kings"])
            w.writerow([102, 10, "India"])
            w.writerow([102, 20, "South Africa"])

        # 3. matches.csv
        with (extracted_dir / "matches.csv").open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow([
                "match_id", "comp_id", "match_number", "match_date", "stage",
                "venue_id", "venue_country", "home_team_id", "home_team",
                "away_team_id", "away_team", "home_team_captain_id", "away_team_captain_id",
                "toss_win_team_id", "toss_opted", "man_of_the_match",
                "first_inn_revised_overs", "second_inn_revised_overs", "revised_target",
                "knock_out", "win_team_id", "result"
            ])
            w.writerow([
                1001, 101, 1, "2024-04-01", "League",
                5, "India", 1, "Rajasthan Royals", 2, "Chennai Super Kings",
                501, 502, 1, "Fielding", 501,
                None, None, None, 0, 1, "Rajasthan Royals Won by 5 wickets"
            ])
            w.writerow([
                1002, 102, 1, "2024-05-01", "League",
                8, "South Africa", 10, "India", 20, "South Africa",
                501, 503, 10, "Fielding", 0,
                None, None, None, 0, None, "Match Abandoned"
            ])

        # 4. competition_team_player_mapping.csv
        with (extracted_dir / "competition_team_player_mapping.csv").open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["comp_id", "comp_name", "team_id", "team_name", "player_id", "player_name"])
            w.writerow([101, "IPL 2024", 1, "Rajasthan Royals", 501, "Sanju Samson"])
            w.writerow([101, "IPL 2024", 2, "Chennai Super Kings", 502, "MS Dhoni"])
            w.writerow([102, "India in SA T20I 2024", 20, "South Africa", 503, "Aiden Markram"])

        # 5. playing_eleven.csv
        with (extracted_dir / "playing_eleven.csv").open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["match_id", "team_id", "player_id", "batting_order", "is_played", "is_captain", "is_wk", "is_impact", "is_impact_off"])
            w.writerow([1001, 1, 501, 3, True, True, True, 0, 0])
            w.writerow([1001, 2, 502, 7, True, True, True, 0, 0])

        # 6. ball_by_ball.csv
        with (extracted_dir / "ball_by_ball.csv").open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow([
                "match_id", "innings", "overid", "over_ball_num", "innings_ball_num",
                "batting_team_id", "bowling_team_id", "striker_id", "striker_name",
                "non_striker_id", "non_striker_name", "bowler_id", "bowler_name",
                "batting_type", "bowling_type", "batting_order", "runs", "is_four",
                "is_six", "is_wicket", "dismissal_type_id", "dismissal_type",
                "dismissed_player_id", "extras_type", "extras1_runs", "extras_2_runs",
                "pace_or_spin", "bowl_speed", "stroke", "delivery_style",
                "over_or_around", "on_or_off", "delivery_ist_time"
            ])
            w.writerow([
                1001, 1, 1, 1, 1, 2, 1, 502, "MS Dhoni", 503, "Aiden Markram",
                501, "Sanju Samson", "RHB", "Right-arm Leg-Break", 7, 1, False,
                False, False, None, None, None, "None", 0, 0, "Spin", 88.5,
                "Worked", "Leg Break", "Over", "On-side", "2024-04-01 19:30:00"
            ])

        return raw_dir

    def test_load_all_tables_synthetic(self, synthetic_data_dir: Path, tmp_path: Path):
        db_path = tmp_path / "test_synth.duckdb"
        report = load_all_tables(db_path=db_path, raw_dir=synthetic_data_dir, recreate_tables=True)

        assert report.is_successful is True
        assert report.total_source_rows == 14
        assert report.total_loaded_rows == 14

        con = get_duckdb_connection(db_path, read_only=True)
        try:
            # Check fact_match derived columns
            m = con.execute("SELECT match_id, has_delivery_data, is_playoff, inn1_scheduled_balls FROM fact_match WHERE match_id = 1001").fetchone()
            assert m[0] == 1001
            assert m[1] is True  # Has delivery data
            assert m[2] is False # Not playoff
            assert m[3] == 120   # Standard scheduled balls

            m2 = con.execute("SELECT match_id, has_delivery_data FROM fact_match WHERE match_id = 1002").fetchone()
            assert m2[1] is False # Abandoned match has no deliveries

            # Check fact_delivery derived columns
            d = con.execute("SELECT batter_runs, extra_runs, total_runs, is_legal_delivery, is_batter_ball_faced, is_bowler_wicket FROM fact_delivery WHERE match_id = 1001").fetchone()
            assert d[0] == 1
            assert d[1] == 0
            assert d[2] == 1
            assert d[3] is True
            assert d[4] is True
            assert d[5] is False

            # Check duplicate delivery constraint
            with pytest.raises(Exception):
                # Attempt to insert identical PK
                con_w = get_duckdb_connection(db_path, read_only=False)
                con_w.execute("""
                    INSERT INTO fact_delivery (
                        match_id, innings, overid, over_ball_num, innings_ball_num,
                        batting_team_id, bowling_team_id, striker_id, striker_name,
                        non_striker_id, non_striker_name, bowler_id, bowler_name,
                        batting_type, bowling_type, batting_order, runs, is_four,
                        is_six, is_wicket, extras_type, extras1_runs, extras_2_runs,
                        pace_or_spin, bowl_speed, on_or_off, delivery_ist_time,
                        batter_runs, extra_runs, total_runs, is_legal_delivery,
                        is_batter_ball_faced, bowler_runs_conceded, is_bowler_wicket,
                        pace_or_spin_clean, is_four_clean, is_six_clean, is_boundary_clean,
                        is_dot_ball_batter, is_dot_ball_bowler, is_speed_missing, is_speed_outlier,
                        canonical_striker_id, canonical_non_striker_id, canonical_bowler_id
                    ) VALUES (
                        1001, 1, 1, 1, 1, 2, 1, 502, 'MS Dhoni',
                        503, 'Aiden Markram', 501, 'Sanju Samson',
                        'RHB', 'Right-arm Leg-Break', 7, 1, False,
                        False, False, 'None', 0, 0,
                        'Spin', 88.5, 'On-side', '2024-04-01 19:30:00',
                        1, 0, 1, True, True, 1, False,
                        'Spin', False, False, False,
                        False, False, False, False,
                        502, 503, 501
                    )
                """)
                con_w.close()
        finally:
            con.close()

    def test_relationship_audits_synthetic(self, synthetic_data_dir: Path, tmp_path: Path):
        db_path = tmp_path / "test_synth_rel.duckdb"
        load_all_tables(db_path=db_path, raw_dir=synthetic_data_dir)

        con = get_duckdb_connection(db_path, read_only=True)
        try:
            rel = validate_database_relationships(con)
            assert rel["orphan_deliveries_to_match"] == 0
            assert rel["orphan_matches_to_competition"] == 0
            assert rel["orphan_teams_to_competition"] == 0
            assert rel["unmatched_strikers"] == 0
            assert rel["unmatched_bowlers"] == 0
            assert rel["matches_missing_deliveries"] == 1  # match 1002 is abandoned
        finally:
            con.close()

    def test_player_identity_resolution_rules(self, tmp_path: Path):
        """Audit A Regression: Verify verified identity merge vs unverified retention."""
        raw_dir = tmp_path / "data" / "raw"
        extracted = raw_dir / "extracted"
        extracted.mkdir(parents=True, exist_ok=True)

        with (extracted / "competitions.csv").open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["comp_id", "comp_name", "match_format", "season"])
            w.writerow([101, "Test Comp", "T20", "2024"])

        with (extracted / "teams.csv").open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["comp_id", "team_id", "team_name"])
            w.writerow([101, 1, "Team 1"])
            w.writerow([101, 2, "Team 2"])

        with (extracted / "matches.csv").open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["match_id", "comp_id", "match_number", "match_date", "stage", "venue_id", "venue_country", "home_team_id", "home_team", "away_team_id", "away_team", "home_team_captain_id", "away_team_captain_id", "toss_win_team_id", "toss_opted", "man_of_the_match", "first_inn_revised_overs", "second_inn_revised_overs", "revised_target", "knock_out", "win_team_id", "result"])
            w.writerow([1001, 101, 1, "2024-04-01", "League", 1, "India", 1, "Team 1", 2, "Team 2", 8638, 20229, 1, "Fielding", 8638, None, None, None, 0, 1, "Won"])

        with (extracted / "competition_team_player_mapping.csv").open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["comp_id", "comp_name", "team_id", "team_name", "player_id", "player_name"])
            w.writerow([101, "Test Comp", 1, "Team 1", 39444, "Basil Hameed"]) # Should map to 8638
            w.writerow([101, "Test Comp", 2, "Team 2", 20229, "Mohammad Ali"]) # Must NOT map to 3083

        with (extracted / "playing_eleven.csv").open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["match_id", "team_id", "player_id", "batting_order", "is_played", "is_captain", "is_wk", "is_impact", "is_impact_off"])
            w.writerow([1001, 1, 39444, 4, True, False, False, 0, 0])
            w.writerow([1001, 2, 20229, 5, True, False, False, 0, 0])

        with (extracted / "ball_by_ball.csv").open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["match_id", "innings", "overid", "over_ball_num", "innings_ball_num", "batting_team_id", "bowling_team_id", "striker_id", "striker_name", "non_striker_id", "non_striker_name", "bowler_id", "bowler_name", "batting_type", "bowling_type", "batting_order", "runs", "is_four", "is_six", "is_wicket", "dismissal_type_id", "dismissal_type", "dismissed_player_id", "extras_type", "extras1_runs", "extras_2_runs", "pace_or_spin", "bowl_speed", "stroke", "delivery_style", "over_or_around", "on_or_off", "delivery_ist_time"])
            w.writerow([1001, 1, 1, 1, 1, 1, 2, 39444, "Basil Hameed", 39444, "Basil Hameed", 20229, "Mohammad Ali", "RHB", "Right-arm Fast", 4, 1, False, False, False, None, None, None, "None", 0, 0, "Pace", 130.0, "Drive", "Seam", "Over", "Off-side", "2024-04-01 19:30:00"])

        db_path = tmp_path / "test_identity.duckdb"
        load_all_tables(db_path=db_path, raw_dir=raw_dir)

        con = get_duckdb_connection(db_path, read_only=True)
        try:
            # 1. Basil Hameed 39444 -> 8638
            bh = con.execute("SELECT canonical_player_id FROM bridge_competition_team_player WHERE player_id = 39444").fetchone()[0]
            assert bh == 8638

            # 2. Mohammad Ali 20229 -> 20229 (unverified merge rejected)
            ma = con.execute("SELECT canonical_player_id FROM bridge_competition_team_player WHERE player_id = 20229").fetchone()[0]
            assert ma == 20229

            # 3. Delivery canonical IDs
            d = con.execute("SELECT canonical_striker_id, canonical_bowler_id FROM fact_delivery WHERE match_id = 1001").fetchone()
            assert d == (8638, 20229)
        finally:
            con.close()

    def test_super_over_lineup_duplicate_flagging(self, tmp_path: Path):
        """Audit B Regression: Verify Super Over lineup duplicate occurrence ranking and flagging."""
        raw_dir = tmp_path / "data" / "raw"
        extracted = raw_dir / "extracted"
        extracted.mkdir(parents=True, exist_ok=True)

        with (extracted / "competitions.csv").open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["comp_id", "comp_name", "match_format", "season"])
            w.writerow([101, "Test Comp", "T20", "2024"])

        with (extracted / "teams.csv").open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["comp_id", "team_id", "team_name"])
            w.writerow([101, 1, "Team 1"])

        with (extracted / "matches.csv").open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["match_id", "comp_id", "match_number", "match_date", "stage", "venue_id", "venue_country", "home_team_id", "home_team", "away_team_id", "away_team", "home_team_captain_id", "away_team_captain_id", "toss_win_team_id", "toss_opted", "man_of_the_match", "first_inn_revised_overs", "second_inn_revised_overs", "revised_target", "knock_out", "win_team_id", "result"])
            w.writerow([1001, 101, 1, "2024-04-01", "League", 1, "India", 1, "Team 1", 1, "Team 1", 100, 100, 1, "Fielding", 100, None, None, None, 0, 1, "Won"])

        with (extracted / "competition_team_player_mapping.csv").open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["comp_id", "comp_name", "team_id", "team_name", "player_id", "player_name"])
            w.writerow([101, "Test Comp", 1, "Team 1", 100, "Player 100"])

        # Insert 3 lineup rows for player 100 in the same match
        with (extracted / "playing_eleven.csv").open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["match_id", "team_id", "player_id", "batting_order", "is_played", "is_captain", "is_wk", "is_impact", "is_impact_off"])
            w.writerow([1001, 1, 100, 1, True, False, False, 0, 0])
            w.writerow([1001, 1, 100, 1, True, False, False, 0, 0])
            w.writerow([1001, 1, 100, 1, True, False, False, 0, 0])

        with (extracted / "ball_by_ball.csv").open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["match_id", "innings", "overid", "over_ball_num", "innings_ball_num", "batting_team_id", "bowling_team_id", "striker_id", "striker_name", "non_striker_id", "non_striker_name", "bowler_id", "bowler_name", "batting_type", "bowling_type", "batting_order", "runs", "is_four", "is_six", "is_wicket", "dismissal_type_id", "dismissal_type", "dismissed_player_id", "extras_type", "extras1_runs", "extras_2_runs", "pace_or_spin", "bowl_speed", "stroke", "delivery_style", "over_or_around", "on_or_off", "delivery_ist_time"])
            w.writerow([1001, 1, 1, 1, 1, 1, 1, 100, "Player 100", 100, "Player 100", 100, "Player 100", "RHB", "Pace", 1, 1, False, False, False, None, None, None, "None", 0, 0, "Pace", 130.0, "Drive", "Seam", "Over", "Off-side", "2024-04-01 19:30:00"])

        db_path = tmp_path / "test_p11_dup.duckdb"
        load_all_tables(db_path=db_path, raw_dir=raw_dir)

        con = get_duckdb_connection(db_path, read_only=True)
        try:
            rows = con.execute("SELECT lineup_id, is_super_over_duplicate FROM fact_playing_eleven WHERE match_id = 1001 ORDER BY lineup_id").fetchall()
            assert len(rows) == 3
            # Exactly 1 primary row, and 2 duplicate rows
            assert rows[0] == ("1001_1_100_1", False)
            assert rows[1] == ("1001_1_100_2", True)
            assert rows[2] == ("1001_1_100_3", True)
        finally:
            con.close()


class TestStatisticalReconciliation:
    """Task 03.2 Regression Suite: Full source-to-database statistical reconciliation."""

    @pytest.fixture
    def db_con(self):
        from config.settings import DUCKDB_PATH
        if not DUCKDB_PATH.exists():
            pytest.skip("Canonical DuckDB database does not exist.")
        con = get_duckdb_connection(DUCKDB_PATH, read_only=True)
        yield con
        con.close()

    def test_canonical_table_row_counts(self, db_con):
        """Verify all 6 canonical tables match source CSV row counts exactly."""
        assert db_con.execute("SELECT COUNT(*) FROM dim_competition").fetchone()[0] == 141
        assert db_con.execute("SELECT COUNT(*) FROM dim_team").fetchone()[0] == 353
        assert db_con.execute("SELECT COUNT(*) FROM fact_match").fetchone()[0] == 883
        assert db_con.execute("SELECT COUNT(*) FROM bridge_competition_team_player").fetchone()[0] == 6413
        assert db_con.execute("SELECT COUNT(*) FROM fact_playing_eleven").fetchone()[0] == 28381
        assert db_con.execute("SELECT COUNT(*) FROM fact_delivery").fetchone()[0] == 200999

    def test_ipl_match_census_reconciliation(self, db_con):
        """Verify IPL competition IDs, match counts, and abandoned matches."""
        rows = db_con.execute("""
            SELECT c.comp_id, c.comp_name, COUNT(m.match_id),
                   SUM(CASE WHEN m.has_delivery_data THEN 1 ELSE 0 END),
                   SUM(CASE WHEN NOT m.has_delivery_data THEN 1 ELSE 0 END)
            FROM dim_competition c
            JOIN fact_match m ON c.comp_id = m.comp_id
            WHERE c.competition_category = 'IPL'
            GROUP BY c.comp_id, c.comp_name
            ORDER BY c.comp_id
        """).fetchall()

        expected = [
            (1358, "IPL 2022", 74, 74, 0),
            (1715, "IPL 2023", 74, 74, 0),
            (2193, "IPL 2024", 74, 71, 3),
            (2725, "IPL 2025", 75, 74, 1),
            (3298, "IPL 2026", 74, 74, 0),
        ]
        assert rows == expected

        total_ipl = db_con.execute("SELECT COUNT(*) FROM fact_match m JOIN dim_competition c ON m.comp_id = c.comp_id WHERE c.competition_category = 'IPL'").fetchone()[0]
        assert total_ipl == 371

    def test_wicket_and_dismissal_reconciliation(self, db_con):
        """Verify dismissal counts and bowler-attribution rules."""
        is_w = db_con.execute("SELECT COUNT(*) FROM fact_delivery WHERE is_wicket").fetchone()[0]
        assert is_w == 10881

        bowler_w = db_con.execute("SELECT COUNT(*) FROM fact_delivery WHERE is_bowler_wicket").fetchone()[0]
        assert bowler_w == 10272

        dt_counts = dict(db_con.execute("SELECT dismissal_type, COUNT(*) FROM fact_delivery WHERE is_wicket GROUP BY dismissal_type").fetchall())
        assert dt_counts["Caught"] == 7557
        assert dt_counts["Bowled"] == 1775
        assert dt_counts["LBW"] == 709
        assert dt_counts["RunOut"] == 600
        assert dt_counts["Stump"] == 214
        assert dt_counts["Hit Wicket"] == 17
        assert dt_counts["Retire Out"] == 6
        assert dt_counts["Obstracting the field"] == 2
        assert dt_counts["Obstructing the field"] == 1

    def test_derived_runs_and_deliveries_reconciliation(self, db_con):
        """Verify derived runs, legal balls, balls faced, and extras accounting."""
        res = db_con.execute("""
            SELECT 
                SUM(total_runs),
                SUM(batter_runs),
                SUM(bowler_runs_conceded),
                SUM(CASE WHEN extras_type = 'byes' THEN extra_runs ELSE 0 END),
                SUM(CASE WHEN extras_type = 'legbyes' THEN extra_runs ELSE 0 END),
                SUM(CASE WHEN extras_type = 'Penalty' THEN extra_runs ELSE 0 END),
                SUM(CASE WHEN is_legal_delivery THEN 1 ELSE 0 END),
                SUM(CASE WHEN is_batter_ball_faced THEN 1 ELSE 0 END)
            FROM fact_delivery
        """).fetchone()

        assert res[0] == 284257  # total team runs
        assert res[1] == 269550  # batter runs
        assert res[2] == 279649  # bowler runs conceded
        assert res[3] == 1000    # byes
        assert res[4] == 3603    # leg-byes
        assert res[5] == 5       # penalty runs
        assert res[6] == 192445  # legal deliveries
        assert res[7] == 193285  # batter balls faced
