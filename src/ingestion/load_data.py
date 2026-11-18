"""
RR ScoutIQ — Data Ingestion & Canonical Table Loading Pipeline
Orchestrates transactional loading of audited CSV data into DuckDB dimensional
and fact tables with schema constraints, data quality sanitization, and verification.
"""

from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Any
import duckdb

from config.settings import DUCKDB_PATH, RAW_DATA_DIR
from src.ingestion.archive_extractor import (
    find_data_pack_archive,
    extract_data_pack,
)
from src.ingestion.database import get_duckdb_connection, initialize_schema
from src.ingestion.profiler import quote_literal


@dataclass(frozen=True)
class IngestionTableResult:
    """Ingestion statistics for an individual analytical table."""
    table_name: str
    source_file: str
    source_row_count: int
    loaded_row_count: int
    duration_seconds: float
    status: str


@dataclass(frozen=True)
class IngestionPipelineReport:
    """Summary metrics across the complete data ingestion run."""
    database_path: str
    tables: list[IngestionTableResult]
    total_source_rows: int
    total_loaded_rows: int
    is_successful: bool


def ensure_extracted_data(raw_dir: Path = RAW_DATA_DIR) -> Path:
    """Verify that source CSVs are extracted; auto-extract from ZIP archive if missing."""
    extracted_dir = raw_dir / "extracted"
    required_files = [
        "competitions.csv",
        "teams.csv",
        "matches.csv",
        "competition_team_player_mapping.csv",
        "playing_eleven.csv",
        "ball_by_ball.csv",
    ]

    all_present = extracted_dir.exists() and all(
        (extracted_dir / f).exists() for f in required_files
    )
    if not all_present:
        archive_path = find_data_pack_archive(raw_dir)
        extract_data_pack(archive_path, extracted_dir, flatten_top_dir=True)

    return extracted_dir


def load_all_tables(
    con: duckdb.DuckDBPyConnection | None = None,
    db_path: Path | str | None = None,
    raw_dir: Path = RAW_DATA_DIR,
    recreate_tables: bool = True,
) -> IngestionPipelineReport:
    """Execute complete transactional ingestion pipeline into DuckDB.

    Args:
        con: Optional active DuckDB connection. If None, connects to ``db_path`` or ``DUCKDB_PATH``.
        db_path: Optional path to DuckDB file.
        raw_dir: Path to raw data directory containing zip or extracted files.
        recreate_tables: If True, drops and rebuilds tables within a transaction.

    Returns:
        IngestionPipelineReport detailing source vs loaded rows for all tables.
    """
    import time

    start_total = time.perf_counter()
    extracted_dir = ensure_extracted_data(raw_dir)
    close_con = False

    if con is None:
        con = get_duckdb_connection(db_path=db_path, read_only=False)
        close_con = True

    results: list[IngestionTableResult] = []

    try:
        # 1. Initialize schema DDL
        initialize_schema(con)

        # 2. Begin transaction
        con.execute("BEGIN TRANSACTION")

        if recreate_tables:
            con.execute("DELETE FROM fact_delivery")
            con.execute("DELETE FROM fact_playing_eleven")
            con.execute("DELETE FROM bridge_competition_team_player")
            con.execute("DELETE FROM fact_match")
            con.execute("DELETE FROM dim_team")
            con.execute("DELETE FROM dim_competition")

        # Table paths
        p_comp = quote_literal(str(extracted_dir / "competitions.csv").replace("\\", "/"))
        p_teams = quote_literal(str(extracted_dir / "teams.csv").replace("\\", "/"))
        p_matches = quote_literal(str(extracted_dir / "matches.csv").replace("\\", "/"))
        p_ctpm = quote_literal(str(extracted_dir / "competition_team_player_mapping.csv").replace("\\", "/"))
        p_p11 = quote_literal(str(extracted_dir / "playing_eleven.csv").replace("\\", "/"))
        p_bbb = quote_literal(str(extracted_dir / "ball_by_ball.csv").replace("\\", "/"))

        # --- A. dim_competition ---
        t0 = time.perf_counter()
        con.execute(f"CREATE TEMP TABLE raw_comp AS SELECT * FROM read_csv_auto({p_comp}, header=true, sample_size=-1)")
        src_comp = int(con.execute("SELECT COUNT(*) FROM raw_comp").fetchone()[0])
        con.execute("""
            INSERT INTO dim_competition
            SELECT
                comp_id,
                comp_name,
                match_format,
                season,
                CASE
                    WHEN comp_name LIKE 'IPL %' THEN 'IPL'
                    WHEN match_format = 'T20I' THEN 'T20I'
                    ELSE 'Other T20'
                END AS competition_category,
                CASE
                    WHEN comp_name LIKE 'IPL %' OR match_format = 'T20I' THEN TRUE
                    ELSE FALSE
                END AS is_tier1_competition
            FROM raw_comp
        """)
        loaded_comp = int(con.execute("SELECT COUNT(*) FROM dim_competition").fetchone()[0])
        results.append(IngestionTableResult("dim_competition", "competitions.csv", src_comp, loaded_comp, time.perf_counter() - t0, "SUCCESS"))

        # --- B. dim_team ---
        t0 = time.perf_counter()
        con.execute(f"CREATE TEMP TABLE raw_teams AS SELECT * FROM read_csv_auto({p_teams}, header=true, sample_size=-1)")
        src_teams = int(con.execute("SELECT COUNT(*) FROM raw_teams").fetchone()[0])
        con.execute("""
            INSERT INTO dim_team
            SELECT comp_id, team_id, team_name
            FROM raw_teams
        """)
        loaded_teams = int(con.execute("SELECT COUNT(*) FROM dim_team").fetchone()[0])
        results.append(IngestionTableResult("dim_team", "teams.csv", src_teams, loaded_teams, time.perf_counter() - t0, "SUCCESS"))

        # --- C. fact_match ---
        t0 = time.perf_counter()
        con.execute(f"CREATE TEMP TABLE raw_matches AS SELECT * FROM read_csv_auto({p_matches}, header=true, sample_size=-1)")
        con.execute(f"CREATE TEMP TABLE raw_bbb_match_ids AS SELECT DISTINCT match_id FROM read_csv_auto({p_bbb}, header=true, sample_size=-1)")
        src_matches = int(con.execute("SELECT COUNT(*) FROM raw_matches").fetchone()[0])
        con.execute("""
            INSERT INTO fact_match
            SELECT
                m.match_id,
                m.comp_id,
                m.match_number,
                m.match_date,
                m.stage,
                m.venue_id,
                m.venue_country,
                m.home_team_id,
                m.home_team,
                m.away_team_id,
                m.away_team,
                m.home_team_captain_id,
                m.away_team_captain_id,
                m.toss_win_team_id,
                m.toss_opted,
                m.man_of_the_match AS man_of_the_match_raw,
                CASE WHEN m.man_of_the_match = 0 THEN NULL ELSE m.man_of_the_match END AS man_of_the_match_clean,
                TRY_CAST(m.first_inn_revised_overs AS BIGINT) AS first_inn_revised_balls,
                TRY_CAST(m.second_inn_revised_overs AS BIGINT) AS second_inn_revised_balls,
                TRY_CAST(m.revised_target AS BIGINT) AS revised_target,
                m.knock_out,
                (m.knock_out = 1) AS is_playoff,
                m.win_team_id,
                m.result,
                CASE
                    WHEN m.result = 'Match Abandoned' THEN 'Match Abandoned'
                    WHEN m.result = 'No Result' THEN 'No Result'
                    WHEN m.result LIKE '%tied%' OR m.result LIKE '%Tied%' THEN 'Tied'
                    ELSE 'Completed'
                END AS match_status,
                (b.match_id IS NOT NULL) AS has_delivery_data,
                CASE
                    WHEN TRY_CAST(m.first_inn_revised_overs AS BIGINT) IS NOT NULL
                      OR TRY_CAST(m.second_inn_revised_overs AS BIGINT) IS NOT NULL
                      OR TRY_CAST(m.revised_target AS BIGINT) IS NOT NULL
                      OR m.match_id IN (15795, 23674, 31278, 48514)
                      OR m.result LIKE '%D/L%'
                      OR m.result LIKE '%DLS%'
                    THEN TRUE
                    ELSE FALSE
                END AS is_shortened_match,
                -- Scheduled balls for Innings 1
                CASE
                    WHEN TRY_CAST(m.first_inn_revised_overs AS BIGINT) IS NOT NULL THEN TRY_CAST(m.first_inn_revised_overs AS BIGINT)
                    WHEN m.match_id IN (15795, 48514) THEN 72
                    WHEN m.match_id = 31278 THEN 96
                    WHEN m.match_id = 23674 THEN 102
                    ELSE 120
                END AS inn1_scheduled_balls,
                -- Scheduled balls for Innings 2
                CASE
                    WHEN TRY_CAST(m.second_inn_revised_overs AS BIGINT) IS NOT NULL THEN TRY_CAST(m.second_inn_revised_overs AS BIGINT)
                    WHEN TRY_CAST(m.first_inn_revised_overs AS BIGINT) IS NOT NULL THEN TRY_CAST(m.first_inn_revised_overs AS BIGINT)
                    WHEN m.match_id IN (15795, 48514) THEN 72
                    WHEN m.match_id = 31278 THEN 96
                    WHEN m.match_id = 23674 THEN 102
                    ELSE 120
                END AS inn2_scheduled_balls
            FROM raw_matches m
            LEFT JOIN raw_bbb_match_ids b ON m.match_id = b.match_id
        """)
        loaded_matches = int(con.execute("SELECT COUNT(*) FROM fact_match").fetchone()[0])
        results.append(IngestionTableResult("fact_match", "matches.csv", src_matches, loaded_matches, time.perf_counter() - t0, "SUCCESS"))

        # --- D. bridge_competition_team_player ---
        t0 = time.perf_counter()
        con.execute(f"CREATE TEMP TABLE raw_ctpm AS SELECT * FROM read_csv_auto({p_ctpm}, header=true, sample_size=-1)")
        src_ctpm = int(con.execute("SELECT COUNT(*) FROM raw_ctpm").fetchone()[0])
        con.execute("""
            INSERT INTO bridge_competition_team_player
            SELECT
                comp_id,
                comp_name,
                team_id,
                team_name,
                player_id,
                player_name,
                -- Canonical player ID resolution for verified split identity
                CASE
                    WHEN player_id = 39444 THEN 8638  -- Basil Hameed UAE national player (verified in comp 2670)
                    ELSE player_id
                END AS canonical_player_id
            FROM raw_ctpm
        """)
        loaded_ctpm = int(con.execute("SELECT COUNT(*) FROM bridge_competition_team_player").fetchone()[0])
        results.append(IngestionTableResult("bridge_competition_team_player", "competition_team_player_mapping.csv", src_ctpm, loaded_ctpm, time.perf_counter() - t0, "SUCCESS"))

        # --- E. fact_playing_eleven ---
        t0 = time.perf_counter()
        con.execute(f"CREATE TEMP TABLE raw_p11 AS SELECT * FROM read_csv_auto({p_p11}, header=true, sample_size=-1)")
        src_p11 = int(con.execute("SELECT COUNT(*) FROM raw_p11").fetchone()[0])
        con.execute("""
            WITH ranked_p11 AS (
                SELECT
                    match_id,
                    team_id,
                    player_id,
                    batting_order,
                    is_played,
                    is_captain,
                    is_wk,
                    is_impact,
                    is_impact_off,
                    ROW_NUMBER() OVER (
                        PARTITION BY match_id, team_id, player_id
                        ORDER BY is_played DESC, batting_order ASC NULLS LAST
                    ) AS occurrence_rank
                FROM raw_p11
            )
            INSERT INTO fact_playing_eleven
            SELECT
                CAST(match_id AS VARCHAR) || '_' || CAST(team_id AS VARCHAR) || '_' || CAST(player_id AS VARCHAR) || '_' || CAST(occurrence_rank AS VARCHAR) AS lineup_id,
                match_id,
                team_id,
                player_id,
                CASE
                    WHEN player_id = 39444 THEN 8638
                    ELSE player_id
                END AS canonical_player_id,
                batting_order,
                is_played,
                is_captain,
                is_wk,
                is_impact,
                is_impact_off,
                (occurrence_rank > 1) AS is_super_over_duplicate
            FROM ranked_p11
        """)
        loaded_p11 = int(con.execute("SELECT COUNT(*) FROM fact_playing_eleven").fetchone()[0])
        results.append(IngestionTableResult("fact_playing_eleven", "playing_eleven.csv", src_p11, loaded_p11, time.perf_counter() - t0, "SUCCESS"))

        # --- F. fact_delivery ---
        t0 = time.perf_counter()
        con.execute(f"CREATE TEMP TABLE raw_bbb AS SELECT * FROM read_csv_auto({p_bbb}, header=true, sample_size=-1)")
        src_bbb = int(con.execute("SELECT COUNT(*) FROM raw_bbb").fetchone()[0])
        con.execute("""
            INSERT INTO fact_delivery
            SELECT
                -- Raw source columns preserved verbatim
                match_id,
                innings,
                overid,
                over_ball_num,
                innings_ball_num,
                batting_team_id,
                bowling_team_id,
                striker_id,
                striker_name,
                non_striker_id,
                non_striker_name,
                bowler_id,
                bowler_name,
                batting_type,
                bowling_type,
                batting_order,
                runs,
                is_four,
                is_six,
                is_wicket,
                TRY_CAST(dismissal_type_id AS BIGINT) AS dismissal_type_id,
                dismissal_type,
                TRY_CAST(dismissed_player_id AS BIGINT) AS dismissed_player_id,
                extras_type,
                extras1_runs,
                extras_2_runs,
                pace_or_spin,
                bowl_speed,
                stroke,
                delivery_style,
                over_or_around,
                on_or_off,
                delivery_ist_time,

                -- Canonical derived analytical fields
                runs AS batter_runs,
                (extras1_runs + extras_2_runs) AS extra_runs,
                (runs + extras1_runs + extras_2_runs) AS total_runs,
                (extras_type NOT IN ('wide', 'Overstep', 'other')) AS is_legal_delivery,
                (extras_type != 'wide') AS is_batter_ball_faced,
                (runs + CASE WHEN extras_type NOT IN ('byes', 'legbyes', 'Penalty') THEN (extras1_runs + extras_2_runs) ELSE 0 END) AS bowler_runs_conceded,
                (is_wicket AND dismissal_type IN ('Caught', 'Bowled', 'LBW', 'Stump', 'Hit Wicket')) AS is_bowler_wicket,
                CASE WHEN dismissal_type = 'Obstracting the field' THEN 'Obstructing the field' ELSE dismissal_type END AS dismissal_type_clean,
                CASE WHEN bowling_type IN ('Right-arm offbreak', 'Slow left-arm orthodox', 'Right-arm Leg-Break', 'Left-arm Chinaman') THEN 'Spin' ELSE 'Pace' END AS pace_or_spin_clean,
                (runs = 4) AS is_four_clean,
                (runs = 6) AS is_six_clean,
                (runs IN (4, 6)) AS is_boundary_clean,
                (extras_type != 'wide' AND runs = 0) AS is_dot_ball_batter,
                ((extras_type NOT IN ('wide', 'Overstep', 'other')) AND (runs + CASE WHEN extras_type NOT IN ('byes', 'legbyes', 'Penalty') THEN (extras1_runs + extras_2_runs) ELSE 0 END) = 0) AS is_dot_ball_bowler,
                CASE WHEN bowl_speed >= 60.0 AND bowl_speed <= 165.0 THEN bowl_speed ELSE NULL END AS bowl_speed_valid,
                (bowl_speed = 0.0) AS is_speed_missing,
                (bowl_speed < 0.0 OR (bowl_speed > 0.0 AND bowl_speed < 50.0) OR bowl_speed > 165.0) AS is_speed_outlier,
                CASE WHEN striker_id = 39444 THEN 8638 ELSE striker_id END AS canonical_striker_id,
                CASE WHEN non_striker_id = 39444 THEN 8638 ELSE non_striker_id END AS canonical_non_striker_id,
                CASE WHEN bowler_id = 39444 THEN 8638 ELSE bowler_id END AS canonical_bowler_id,
                CASE
                    WHEN TRY_CAST(dismissed_player_id AS BIGINT) = 39444 THEN 8638
                    ELSE TRY_CAST(dismissed_player_id AS BIGINT)
                END AS canonical_dismissed_player_id
            FROM raw_bbb
        """)
        loaded_bbb = int(con.execute("SELECT COUNT(*) FROM fact_delivery").fetchone()[0])
        results.append(IngestionTableResult("fact_delivery", "ball_by_ball.csv", src_bbb, loaded_bbb, time.perf_counter() - t0, "SUCCESS"))

        # Commit transaction
        con.execute("COMMIT")

    except Exception:
        con.execute("ROLLBACK")
        raise
    finally:
        # Clean temp tables
        for tmp in ["raw_comp", "raw_teams", "raw_matches", "raw_bbb_match_ids", "raw_ctpm", "raw_p11", "raw_bbb"]:
            try:
                con.execute(f"DROP TABLE IF EXISTS {tmp}")
            except Exception:
                pass
        if close_con:
            con.close()

    total_src = sum(r.source_row_count for r in results)
    total_loaded = sum(r.loaded_row_count for r in results)
    db_loc = str(db_path or DUCKDB_PATH)

    return IngestionPipelineReport(
        database_path=db_loc,
        tables=results,
        total_source_rows=total_src,
        total_loaded_rows=total_loaded,
        is_successful=(total_src == total_loaded and total_src > 0),
    )


def validate_database_relationships(con: duckdb.DuckDBPyConnection) -> dict[str, Any]:
    """Execute referential integrity, entity resolution, and relationship audits across tables.

    Returns:
        Dictionary of relationship verification counts and pass/fail statuses.
    """
    results: dict[str, Any] = {}

    # 1. Delivery to match referential integrity (0 orphans)
    orphans_deliv_match = int(con.execute("""
        SELECT COUNT(*)
        FROM fact_delivery d
        LEFT JOIN fact_match m ON d.match_id = m.match_id
        WHERE m.match_id IS NULL
    """).fetchone()[0])
    results["orphan_deliveries_to_match"] = orphans_deliv_match

    # 2. Match to competition integrity (0 orphans)
    orphans_match_comp = int(con.execute("""
        SELECT COUNT(*)
        FROM fact_match m
        LEFT JOIN dim_competition c ON m.comp_id = c.comp_id
        WHERE c.comp_id IS NULL
    """).fetchone()[0])
    results["orphan_matches_to_competition"] = orphans_match_comp

    # 3. Team to competition integrity (0 orphans)
    orphans_team_comp = int(con.execute("""
        SELECT COUNT(*)
        FROM dim_team t
        LEFT JOIN dim_competition c ON t.comp_id = c.comp_id
        WHERE c.comp_id IS NULL
    """).fetchone()[0])
    results["orphan_teams_to_competition"] = orphans_team_comp

    # 4. Lineup to match and player integrity
    orphans_p11_match = int(con.execute("""
        SELECT COUNT(*)
        FROM fact_playing_eleven p
        LEFT JOIN fact_match m ON p.match_id = m.match_id
        WHERE m.match_id IS NULL
    """).fetchone()[0])
    results["orphan_lineups_to_match"] = orphans_p11_match

    orphans_p11_player = int(con.execute("""
        SELECT COUNT(*)
        FROM fact_playing_eleven p
        LEFT JOIN (SELECT DISTINCT player_id FROM bridge_competition_team_player) b ON p.player_id = b.player_id
        WHERE b.player_id IS NULL
    """).fetchone()[0])
    results["orphan_lineups_to_player"] = orphans_p11_player

    # 5. Delivery players to CTPM bridge
    unmatched_strikers = int(con.execute("""
        SELECT COUNT(DISTINCT d.striker_id)
        FROM fact_delivery d
        LEFT JOIN (SELECT DISTINCT player_id FROM bridge_competition_team_player) b ON d.striker_id = b.player_id
        WHERE b.player_id IS NULL
    """).fetchone()[0])
    results["unmatched_strikers"] = unmatched_strikers

    unmatched_bowlers = int(con.execute("""
        SELECT COUNT(DISTINCT d.bowler_id)
        FROM fact_delivery d
        LEFT JOIN (SELECT DISTINCT player_id FROM bridge_competition_team_player) b ON d.bowler_id = b.player_id
        WHERE b.player_id IS NULL
    """).fetchone()[0])
    results["unmatched_bowlers"] = unmatched_bowlers

    unmatched_dismissed = int(con.execute("""
        SELECT COUNT(DISTINCT d.dismissed_player_id)
        FROM fact_delivery d
        LEFT JOIN (SELECT DISTINCT player_id FROM bridge_competition_team_player) b ON d.dismissed_player_id = b.player_id
        WHERE d.dismissed_player_id IS NOT NULL AND b.player_id IS NULL
    """).fetchone()[0])
    results["unmatched_dismissed_players"] = unmatched_dismissed

    # 6. Matches missing deliveries (expected: 16 abandoned matches)
    missing_deliveries = int(con.execute("""
        SELECT COUNT(*)
        FROM fact_match
        WHERE NOT has_delivery_data
    """).fetchone()[0])
    results["matches_missing_deliveries"] = missing_deliveries

    # 7. Super Over duplicate lineup records
    super_over_dups = int(con.execute("""
        SELECT COUNT(*)
        FROM fact_playing_eleven
        WHERE is_super_over_duplicate
    """).fetchone()[0])
    results["super_over_lineup_duplicates"] = super_over_dups

    # 8. Canonical player ID resolutions
    striker_resolutions = int(con.execute("""
        SELECT COUNT(*)
        FROM fact_delivery
        WHERE striker_id != canonical_striker_id
    """).fetchone()[0])
    results["canonical_striker_resolutions"] = striker_resolutions

    bowler_resolutions = int(con.execute("""
        SELECT COUNT(*)
        FROM fact_delivery
        WHERE bowler_id != canonical_bowler_id
    """).fetchone()[0])
    results["canonical_bowler_resolutions"] = bowler_resolutions

    results["is_valid"] = (
        orphans_deliv_match == 0
        and orphans_match_comp == 0
        and orphans_team_comp == 0
        and orphans_p11_match == 0
        and orphans_p11_player == 0
        and unmatched_strikers == 0
        and unmatched_bowlers == 0
        and unmatched_dismissed == 0
        and missing_deliveries == 16
    )

    return results


if __name__ == "__main__":
    import sys
    print("Executing RR ScoutIQ Data Ingestion Pipeline...")
    report = load_all_tables()
    print(f"\nIngestion Complete -> Database: {report.database_path}")
    print(f"Total Source Rows: {report.total_source_rows:,} | Total Loaded Rows: {report.total_loaded_rows:,} | Status: {'SUCCESS' if report.is_successful else 'FAILED'}")
    for t in report.tables:
        print(f"  - {t.table_name}: source={t.source_row_count:,} loaded={t.loaded_row_count:,} time={t.duration_seconds:.2f}s")
