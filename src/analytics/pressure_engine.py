"""
RR ScoutIQ — Pressure Index Engine
Mathematical modeling and reconstruction of continuous, pre-delivery match pressure
across both chase (2nd/4th innings) and structural first-innings (1st/3rd innings) states.

Zero future leakage: Strictly relies on pre-delivery states.
Handles edge cases: Unrecorded DLS targets (Match 23674), shortened matches, Super Overs.
"""

from __future__ import annotations
from typing import Any
import duckdb

# SQL query that computes pre-delivery pressure indices over fact_delivery_context_mat
DELIVERY_PRESSURE_SQL = """
WITH base AS (
    SELECT 
        d.*,
        
        -- 1. Chase Pressure Components (Innings 2 & 4)
        CASE 
            WHEN d.innings = 4 THEN 0.95 -- Super Over Chase
            WHEN d.is_chase AND d.target_runs IS NOT NULL THEN
                CASE
                    WHEN d.runs_required <= 0 THEN 0.0
                    ELSE
                        -- Rate Pressure: Sigmoidal activation centered at league median RRR (9.0 RPO)
                        (1.0 / (1.0 + EXP(-0.22 * (COALESCE(d.required_run_rate, 9.0) - 9.0))))
                END
            ELSE NULL 
        END AS chase_rate_comp,
        
        CASE 
            WHEN d.innings = 4 THEN 0.90
            WHEN d.is_chase AND d.target_runs IS NOT NULL THEN
                -- Wicket Leverage: Non-linear penalty as wickets in hand decrease
                (1.0 - POWER(d.wickets_in_hand / 10.0, 0.75))
            ELSE NULL 
        END AS chase_wkt_comp,
        
        CASE 
            WHEN d.innings = 4 THEN 1.00
            WHEN d.is_chase AND d.target_runs IS NOT NULL THEN
                -- Temporal Urgency Horizon: strictly increases as available legal balls diminish
                -- Bounded in [0.20, 1.00], strictly monotonic: lower early on, higher as balls run out
                (0.20 + 0.80 * POWER(
                    1.0 - (LEAST(d.legal_balls_remaining, d.scheduled_legal_balls)::FLOAT / CAST(GREATEST(1, d.scheduled_legal_balls) AS FLOAT)),
                    1.25
                ))
            ELSE NULL 
        END AS chase_urgency_comp,
        
        -- 2. First-Innings Structural Pressure Components (Innings 1 & 3)
        CASE
            WHEN d.innings = 3 THEN 0.88 -- Super Over First Innings
            WHEN NOT d.is_chase THEN
                -- Wicket Stress: Compares actual wickets lost to baseline expected progression
                LEAST(1.0, GREATEST(0.0, 
                    (d.pre_delivery_wickets - (6.0 * POWER(d.pre_delivery_legal_balls / CAST(GREATEST(1, d.scheduled_legal_balls) AS FLOAT), 0.85))) / 3.5
                ) + 0.50 * (1.0 - d.wickets_in_hand / 10.0))
            ELSE NULL
        END AS inn1_wkt_stress,
        
        CASE
            WHEN d.innings = 3 THEN 0.85
            WHEN NOT d.is_chase AND d.pre_delivery_legal_balls >= 36 THEN
                -- Stagnation Pressure: Escalates if team current run rate is depressed post-Powerplay
                -- Empirically calibrated: 1st innings median CRR post-PP is 8.34 RPO
                LEAST(1.0, GREATEST(0.0, (8.34 - d.current_run_rate) / 3.5))
            ELSE 0.0
        END AS inn1_stagnation,
        
        CASE
            WHEN d.innings = 3 THEN 0.90
            WHEN NOT d.is_chase THEN
                -- Phase Leverage: Powerplay (0.25), Middle (0.40), Death overs (0.70 to 1.00)
                CASE 
                    WHEN d.innings_phase = 'Powerplay' THEN 0.25
                    WHEN d.innings_phase = 'Middle' THEN 0.40
                    WHEN d.innings_phase = 'Death' THEN (0.70 + 0.30 * (GREATEST(0, d.pre_delivery_legal_balls - 90) / 30.0))
                    ELSE 0.90
                END
            ELSE NULL
        END AS inn1_phase_leverage

    FROM fact_delivery_context_mat d
)
SELECT 
    b.*,
    
    -- Chase Pressure Index (CPI in [0, 100])
    CASE
        WHEN b.innings = 4 THEN 95.0
        WHEN b.is_chase AND b.target_runs IS NOT NULL THEN
            ROUND(LEAST(100.0, GREATEST(0.0,
                (0.55 * b.chase_rate_comp + 0.30 * b.chase_wkt_comp + 0.15 * b.chase_urgency_comp) * 100.0 
                * (CASE WHEN b.runs_required <= 25 AND b.legal_balls_remaining <= 18 THEN 1.15 ELSE 1.0 END)
            )), 2)
        ELSE NULL
    END AS chase_pressure_index,
    
    -- First Innings Structural Pressure Index (FPI in [0, 100])
    CASE
        WHEN b.innings = 3 THEN 88.0
        WHEN NOT b.is_chase THEN
            ROUND(LEAST(100.0, GREATEST(0.0,
                (0.45 * b.inn1_wkt_stress + 0.20 * b.inn1_stagnation + 0.35 * b.inn1_phase_leverage) * 100.0
            )), 2)
        ELSE NULL
    END AS first_innings_pressure_index,
    
    -- Unified Continuous Pressure Score (P in [0, 100])
    CASE
        WHEN b.is_chase AND b.target_runs IS NOT NULL THEN
            ROUND(LEAST(100.0, GREATEST(0.0,
                (0.55 * b.chase_rate_comp + 0.30 * b.chase_wkt_comp + 0.15 * b.chase_urgency_comp) * 100.0 
                * (CASE WHEN b.runs_required <= 25 AND b.legal_balls_remaining <= 18 THEN 1.15 ELSE 1.0 END)
            )), 2)
        WHEN b.innings = 4 THEN 95.0
        WHEN b.innings = 3 THEN 88.0
        WHEN NOT b.is_chase THEN
            ROUND(LEAST(100.0, GREATEST(0.0,
                (0.45 * b.inn1_wkt_stress + 0.20 * b.inn1_stagnation + 0.35 * b.inn1_phase_leverage) * 100.0
            )), 2)
        ELSE NULL -- Match 23674 unrecorded DLS target
    END AS pressure_score

FROM base b
"""


def materialize_delivery_pressure_table(
    con: duckdb.DuckDBPyConnection,
    table_name: str = "fact_delivery_pressure",
) -> int:
    """Compute and materialize pre-delivery pressure indices into a dedicated physical table.

    Args:
        con: Connected DuckDB connection.
        table_name: Destination physical table name.

    Returns:
        Number of rows materialized.
    """
    con.execute(f"DROP TABLE IF EXISTS {table_name}")
    con.execute(f"""
        CREATE TABLE {table_name} AS 
        WITH calc AS ({DELIVERY_PRESSURE_SQL})
        SELECT 
            c.*,
            -- Continuous quadratic pressure weighting for smooth aggregation
            ROUND(POWER(COALESCE(c.pressure_score, 0.0) / 100.0, 2), 4) AS pressure_weight,
            
            -- Categorical quantile indicators
            (c.pressure_score >= 50.0) AS is_high_pressure,
            (c.pressure_score >= 65.0) AS is_extreme_pressure,
            (c.pressure_score >= 50.0 AND c.innings_phase = 'Death') AS is_clutch_death,
            (c.pressure_score >= 60.0 AND c.is_chase) AS is_crisis_chase
        FROM calc c
    """)

    # Indices for fast player evaluation queries
    con.execute(f"CREATE INDEX IF NOT EXISTS idx_{table_name}_match ON {table_name}(match_id, innings)")
    con.execute(f"CREATE INDEX IF NOT EXISTS idx_{table_name}_striker ON {table_name}(canonical_striker_id)")
    con.execute(f"CREATE INDEX IF NOT EXISTS idx_{table_name}_bowler ON {table_name}(canonical_bowler_id)")
    con.execute(f"CREATE INDEX IF NOT EXISTS idx_{table_name}_tier ON {table_name}(is_tier1_competition)")
    con.execute(f"CREATE INDEX IF NOT EXISTS idx_{table_name}_high_p ON {table_name}(is_high_pressure)")

    count = int(con.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0])
    return count


def get_pressure_summary_statistics(con: duckdb.DuckDBPyConnection) -> dict[str, Any]:
    """Retrieve statistical summary of pressure scores across deliveries.

    Args:
        con: Connected DuckDB connection.

    Returns:
        Dictionary containing distributions, quantiles, and segment counts.
    """
    stats = con.execute("""
        SELECT 
            COUNT(*) AS total_rows,
            COUNT(pressure_score) AS scored_rows,
            COUNT(*) - COUNT(pressure_score) AS missing_pressure_rows,
            ROUND(AVG(pressure_score), 2) AS mean_pressure,
            ROUND(STDDEV(pressure_score), 2) AS std_pressure,
            ROUND(PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY pressure_score), 2) AS p25,
            ROUND(PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY pressure_score), 2) AS median_pressure,
            ROUND(PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY pressure_score), 2) AS p75,
            ROUND(PERCENTILE_CONT(0.90) WITHIN GROUP (ORDER BY pressure_score), 2) AS p90,
            ROUND(PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY pressure_score), 2) AS p95,
            SUM(CASE WHEN is_high_pressure THEN 1 ELSE 0 END) AS high_pressure_deliveries,
            SUM(CASE WHEN is_extreme_pressure THEN 1 ELSE 0 END) AS extreme_pressure_deliveries,
            SUM(CASE WHEN is_clutch_death THEN 1 ELSE 0 END) AS clutch_death_deliveries,
            SUM(CASE WHEN is_crisis_chase THEN 1 ELSE 0 END) AS crisis_chase_deliveries
        FROM fact_delivery_pressure
    """).fetchone()

    return {
        "total_deliveries": stats[0],
        "scored_deliveries": stats[1],
        "missing_pressure_deliveries": stats[2],
        "mean_pressure": stats[3],
        "std_pressure": stats[4],
        "p25": stats[5],
        "median": stats[6],
        "p75": stats[7],
        "p90": stats[8],
        "p95": stats[9],
        "high_pressure_deliveries": stats[10],
        "extreme_pressure_deliveries": stats[11],
        "clutch_death_deliveries": stats[12],
        "crisis_chase_deliveries": stats[13],
    }


if __name__ == "__main__":
    from config.settings import DUCKDB_PATH
    from src.ingestion.database import get_duckdb_connection

    print("Executing Pressure Engine Materialization...")
    con = get_duckdb_connection(DUCKDB_PATH, read_only=False)
    try:
        n = materialize_delivery_pressure_table(con)
        print(f"Materialized {n:,} deliveries into fact_delivery_pressure.")
        summary = get_pressure_summary_statistics(con)
        print("\n=== Pressure Distribution Summary ===")
        for k, v in summary.items():
            print(f"  {k}: {v}")
    finally:
        con.close()
