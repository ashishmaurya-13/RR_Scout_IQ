"""
RR ScoutIQ — Delivery Context & Match-State Reconstruction Engine
Implements sequential, ball-by-ball match-state reconstruction immediately
preceding each delivery, with strict prevention of future information leakage.
"""

from __future__ import annotations
from typing import Any
import duckdb


DELIVERY_CONTEXT_SQL = """
WITH inn_totals AS (
    SELECT
        match_id,
        innings,
        SUM(total_runs) AS inn_runs,
        SUM(CASE WHEN is_legal_delivery THEN 1 ELSE 0 END) AS inn_legal_balls,
        SUM(CASE WHEN is_wicket THEN 1 ELSE 0 END) AS inn_wickets
    FROM fact_delivery
    GROUP BY match_id, innings
),
delivery_base AS (
    SELECT
        d.match_id,
        d.innings,
        d.overid,
        d.over_ball_num,
        d.innings_ball_num,
        d.batting_team_id,
        d.bowling_team_id,
        d.striker_id,
        d.striker_name,
        d.non_striker_id,
        d.non_striker_name,
        d.bowler_id,
        d.bowler_name,
        d.batting_type,
        d.bowling_type,
        d.batting_order,
        d.runs AS batter_runs,
        d.extra_runs,
        d.total_runs,
        d.is_legal_delivery,
        d.is_batter_ball_faced,
        d.bowler_runs_conceded,
        d.is_bowler_wicket,
        d.is_wicket,
        d.dismissal_type_id,
        d.dismissal_type,
        d.dismissal_type_clean,
        d.dismissed_player_id,
        d.extras_type,
        d.extras1_runs,
        d.extras_2_runs,
        d.pace_or_spin_clean,
        d.is_four_clean,
        d.is_six_clean,
        d.is_boundary_clean,
        d.is_dot_ball_batter,
        d.is_dot_ball_bowler,
        d.bowl_speed_valid,
        d.is_speed_missing,
        d.is_speed_outlier,
        d.canonical_striker_id,
        d.canonical_non_striker_id,
        d.canonical_bowler_id,
        d.canonical_dismissed_player_id,
        d.delivery_ist_time,

        m.comp_id,
        m.match_date,
        m.stage,
        m.venue_id,
        m.venue_country,
        m.revised_target,
        m.is_shortened_match,
        m.is_playoff,
        m.match_status,
        c.competition_category,
        c.is_tier1_competition,

        -- Innings scheduled legal balls (accounts for revised overs in balls & shortened matches)
        CASE
            WHEN d.innings = 1 THEN m.inn1_scheduled_balls
            WHEN d.innings = 2 THEN m.inn2_scheduled_balls
            ELSE 6 -- Super Overs (innings 3 & 4)
        END AS scheduled_legal_balls,

        -- Target runs calculation (strict: no target in 1st innings; revised_target or inn1 + 1 in chase)
        -- In match 23674, innings 1 was shortened to 17 overs with DLS method recorded in match result,
        -- but official revised_target was unrecorded (NULL) in the source dataset. Per integrity rules,
        -- we do NOT fabricate an unrevised target; target_runs and derived pressure metrics are set to NULL (unavailable).
        CASE
            WHEN d.innings = 2 AND m.revised_target IS NOT NULL THEN m.revised_target
            WHEN d.innings = 2 AND m.match_id = 23674 THEN NULL
            WHEN d.innings = 2 AND i1.inn_runs IS NOT NULL THEN i1.inn_runs + 1
            WHEN d.innings = 4 AND i3.inn_runs IS NOT NULL THEN i3.inn_runs + 1
            ELSE NULL
        END AS target_runs

    FROM fact_delivery d
    JOIN fact_match m ON d.match_id = m.match_id
    JOIN dim_competition c ON m.comp_id = c.comp_id
    LEFT JOIN inn_totals i1 ON d.match_id = i1.match_id AND i1.innings = 1
    LEFT JOIN inn_totals i3 ON d.match_id = i3.match_id AND i3.innings = 3
),
pre_calc AS (
    SELECT
        b.*,
        (b.innings = 2 OR b.innings = 4) AS is_chase,

        -- Pre-delivery team score (strictly precedes current ball)
        COALESCE(
            SUM(b.total_runs) OVER (
                PARTITION BY b.match_id, b.innings
                ORDER BY b.innings_ball_num
                ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING
            ), 0
        ) AS pre_delivery_runs,

        -- Pre-delivery wickets lost (strictly precedes current ball)
        COALESCE(
            SUM(CASE WHEN b.is_wicket THEN 1 ELSE 0 END) OVER (
                PARTITION BY b.match_id, b.innings
                ORDER BY b.innings_ball_num
                ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING
            ), 0
        ) AS pre_delivery_wickets,

        -- Pre-delivery legal balls bowled (strictly precedes current ball)
        COALESCE(
            SUM(CASE WHEN b.is_legal_delivery THEN 1 ELSE 0 END) OVER (
                PARTITION BY b.match_id, b.innings
                ORDER BY b.innings_ball_num
                ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING
            ), 0
        ) AS pre_delivery_legal_balls

    FROM delivery_base b
)
SELECT
    p.*,
    (10 - p.pre_delivery_wickets) AS wickets_in_hand,
    GREATEST(0, p.scheduled_legal_balls - p.pre_delivery_legal_balls) AS legal_balls_remaining,
    p.pre_delivery_legal_balls // 6 AS completed_overs,
    p.pre_delivery_legal_balls % 6 AS balls_in_current_over,

    -- Pre-delivery Current Run Rate (CRR)
    CASE
        WHEN p.pre_delivery_legal_balls > 0
        THEN ROUND((p.pre_delivery_runs * 6.0) / p.pre_delivery_legal_balls, 4)
        ELSE 0.0
    END AS current_run_rate,

    -- Runs required in chase
    CASE
        WHEN p.target_runs IS NOT NULL
        THEN GREATEST(0, p.target_runs - p.pre_delivery_runs)
        ELSE NULL
    END AS runs_required,

    -- Pre-delivery Required Run Rate (RRR)
    CASE
        WHEN p.target_runs IS NOT NULL AND (p.scheduled_legal_balls - p.pre_delivery_legal_balls) > 0
        THEN ROUND((GREATEST(0, p.target_runs - p.pre_delivery_runs) * 6.0) / (p.scheduled_legal_balls - p.pre_delivery_legal_balls), 4)
        WHEN p.target_runs IS NOT NULL AND p.target_runs <= p.pre_delivery_runs
        THEN 0.0
        ELSE NULL
    END AS required_run_rate,

    -- Dynamic Innings Phase (calibrated for full 20-over and shortened matches)
    CASE
        WHEN p.innings IN (3, 4) THEN 'Super Over'
        WHEN p.scheduled_legal_balls <= 60 THEN
            CASE
                WHEN p.overid <= 2 THEN 'Powerplay'
                WHEN p.overid >= (p.scheduled_legal_balls // 6) - 1 THEN 'Death'
                ELSE 'Middle'
            END
        WHEN p.scheduled_legal_balls < 120 THEN
            CASE
                WHEN p.overid <= CAST(CEIL((p.scheduled_legal_balls / 6.0) * 0.3) AS BIGINT) THEN 'Powerplay'
                WHEN p.overid > (p.scheduled_legal_balls // 6) - 4 THEN 'Death'
                ELSE 'Middle'
            END
        ELSE
            CASE
                WHEN p.overid <= 6 THEN 'Powerplay'
                WHEN p.overid BETWEEN 7 AND 15 THEN 'Middle'
                ELSE 'Death'
            END
    END AS innings_phase,

    -- Post-delivery states for validation and reconciliation
    (p.pre_delivery_runs + p.total_runs) AS post_delivery_runs,
    (p.pre_delivery_wickets + CASE WHEN p.is_wicket THEN 1 ELSE 0 END) AS post_delivery_wickets,
    (p.pre_delivery_legal_balls + CASE WHEN p.is_legal_delivery THEN 1 ELSE 0 END) AS post_delivery_legal_balls

FROM pre_calc p
"""


def create_delivery_context_view(con: duckdb.DuckDBPyConnection) -> None:
    """Create or replace the ``fact_delivery_context`` view in DuckDB."""
    con.execute(f"CREATE OR REPLACE VIEW fact_delivery_context AS {DELIVERY_CONTEXT_SQL}")


def materialize_delivery_context_table(
    con: duckdb.DuckDBPyConnection,
    table_name: str = "fact_delivery_context_mat",
) -> int:
    """Materialize delivery context query into a persisted physical table with indices.

    Args:
        con: Connected DuckDB database connection.
        table_name: Name of physical table to create.

    Returns:
        Number of rows materialized into table.
    """
    con.execute(f"DROP TABLE IF EXISTS {table_name}")
    con.execute(f"CREATE TABLE {table_name} AS {DELIVERY_CONTEXT_SQL}")

    # Add indices for fast downstream filtering
    con.execute(f"CREATE INDEX IF NOT EXISTS idx_{table_name}_match ON {table_name}(match_id, innings)")
    con.execute(f"CREATE INDEX IF NOT EXISTS idx_{table_name}_striker ON {table_name}(canonical_striker_id)")
    con.execute(f"CREATE INDEX IF NOT EXISTS idx_{table_name}_bowler ON {table_name}(canonical_bowler_id)")
    con.execute(f"CREATE INDEX IF NOT EXISTS idx_{table_name}_phase ON {table_name}(innings_phase)")

    count = int(con.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0])
    return count


def validate_delivery_context(con: duckdb.DuckDBPyConnection) -> dict[str, Any]:
    """Execute mathematical integrity and consistency checks on reconstructed delivery context.

    Returns:
        Dictionary detailing results of 10 automated consistency checks.
    """
    # Ensure view exists
    create_delivery_context_view(con)

    checks: dict[str, Any] = {}

    # 1. Total row count consistency
    fd_count = int(con.execute("SELECT COUNT(*) FROM fact_delivery").fetchone()[0])
    ctx_count = int(con.execute("SELECT COUNT(*) FROM fact_delivery_context").fetchone()[0])
    checks["row_count_match"] = (fd_count == ctx_count, fd_count, ctx_count)

    # 2. First ball of each innings pre-state equals 0
    first_ball_violations = int(con.execute("""
        SELECT COUNT(*)
        FROM fact_delivery_context
        WHERE innings_ball_num = 1
          AND (pre_delivery_runs != 0 OR pre_delivery_wickets != 0 OR pre_delivery_legal_balls != 0)
    """).fetchone()[0])
    checks["first_ball_zeros"] = (first_ball_violations == 0, first_ball_violations)

    # 3. Pre-delivery runs monotonically non-decreasing
    negative_runs_progressions = int(con.execute("""
        SELECT COUNT(*)
        FROM fact_delivery_context
        WHERE post_delivery_runs < pre_delivery_runs
    """).fetchone()[0])
    checks["runs_monotonic"] = (negative_runs_progressions == 0, negative_runs_progressions)

    # 4. Pre-delivery wickets monotonically non-decreasing
    negative_wickets_progressions = int(con.execute("""
        SELECT COUNT(*)
        FROM fact_delivery_context
        WHERE post_delivery_wickets < pre_delivery_wickets
    """).fetchone()[0])
    checks["wickets_monotonic"] = (negative_wickets_progressions == 0, negative_wickets_progressions)

    # 5. Legal balls remaining never negative
    negative_balls_remaining = int(con.execute("""
        SELECT COUNT(*)
        FROM fact_delivery_context
        WHERE legal_balls_remaining < 0
    """).fetchone()[0])
    checks["balls_remaining_non_negative"] = (negative_balls_remaining == 0, negative_balls_remaining)

    # 6. Wickets in hand strictly within [0, 10]
    invalid_wickets_in_hand = int(con.execute("""
        SELECT COUNT(*)
        FROM fact_delivery_context
        WHERE wickets_in_hand < 0 OR wickets_in_hand > 10
    """).fetchone()[0])
    checks["wickets_in_hand_valid"] = (invalid_wickets_in_hand == 0, invalid_wickets_in_hand)

    # 7. First innings never has chase target
    inn1_with_target = int(con.execute("""
        SELECT COUNT(*)
        FROM fact_delivery_context
        WHERE innings IN (1, 3) AND target_runs IS NOT NULL
    """).fetchone()[0])
    checks["first_innings_no_target"] = (inn1_with_target == 0, inn1_with_target)

    # 8. Chase innings target accuracy
    chase_deliveries = int(con.execute("SELECT COUNT(*) FROM fact_delivery_context WHERE is_chase").fetchone()[0])
    chase_missing_target = int(con.execute("""
        SELECT COUNT(*)
        FROM fact_delivery_context
        WHERE is_chase AND target_runs IS NULL
    """).fetchone()[0])
    unrecorded_dls_missing = int(con.execute("""
        SELECT COUNT(*)
        FROM fact_delivery_context
        WHERE is_chase AND target_runs IS NULL AND match_id != 23674
    """).fetchone()[0])
    # Exactly match 23674 (97 deliveries) has unavailable target due to unrecorded DLS revised target
    checks["chase_target_coverage"] = (unrecorded_dls_missing == 0, chase_deliveries, chase_missing_target)

    # 9. Required run rate non-negative where defined
    negative_rrr = int(con.execute("""
        SELECT COUNT(*)
        FROM fact_delivery_context
        WHERE required_run_rate IS NOT NULL AND required_run_rate < 0
    """).fetchone()[0])
    checks["rrr_non_negative"] = (negative_rrr == 0, negative_rrr)

    # 10. Phase distribution coverage
    phase_counts = con.execute("""
        SELECT innings_phase, COUNT(*)
        FROM fact_delivery_context
        GROUP BY innings_phase
        ORDER BY 2 DESC
    """).fetchall()
    checks["phase_counts"] = {r[0]: int(r[1]) for r in phase_counts}

    all_passed = all(
        res[0] if isinstance(res, tuple) and isinstance(res[0], bool) else True
        for res in checks.values()
    )
    checks["all_passed"] = all_passed

    return checks


if __name__ == "__main__":
    from src.ingestion.database import get_duckdb_connection
    print("Testing Delivery Context Reconstruction Engine...")
    con = get_duckdb_connection(read_only=False)
    try:
        val = validate_delivery_context(con)
        print("\n=== Validation Results ===")
        for k, v in val.items():
            print(f"  - {k}: {v}")
        print(f"\nMaterializing table...")
        n = materialize_delivery_context_table(con)
        print(f"Materialized {n:,} rows into fact_delivery_context_mat.")
    finally:
        con.close()
