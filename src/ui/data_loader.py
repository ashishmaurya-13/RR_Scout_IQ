"""
RR ScoutIQ — Streamlit Cached Data Loader
Provides efficient, cached database and artifact access for the dashboard without heavy binary C-extensions.
"""

from __future__ import annotations
import csv
import json
from pathlib import Path
from typing import Any
import duckdb
import streamlit as st

from config.settings import ARTIFACTS_DIR, DUCKDB_PATH
from src.ingestion.database import get_duckdb_connection
from src.scouting.ranking_engine import RankingEngine


def _parse_csv(path: Path) -> list[dict[str, Any]]:
    """Parse CSV into list of typed dictionaries."""
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = []
        for r in reader:
            parsed = {}
            for k, v in r.items():
                if v is None or v == "":
                    parsed[k] = None
                    continue
                try:
                    if "." in v:
                        parsed[k] = float(v)
                    else:
                        parsed[k] = int(v)
                except ValueError:
                    parsed[k] = v
            rows.append(parsed)
        return rows


@st.cache_resource
def get_db():
    """Get persistent read-only DuckDB connection for Streamlit session."""
    return get_duckdb_connection(DUCKDB_PATH, read_only=True)


@st.cache_data(ttl=3600)
def load_db_overview():
    """Load canonical database counts and population summaries."""
    con = get_db()
    row = con.execute("""
        SELECT 
            (SELECT COUNT(*) FROM fact_match) AS total_matches,
            (SELECT COUNT(*) FROM fact_match WHERE has_delivery_data) AS played_matches,
            (SELECT COUNT(*) FROM fact_match WHERE comp_id IN (SELECT comp_id FROM dim_competition WHERE competition_category = 'IPL')) AS ipl_matches,
            (SELECT COUNT(*) FROM fact_delivery) AS total_deliveries,
            (SELECT COUNT(*) FROM fact_delivery_pressure WHERE pressure_score IS NOT NULL) AS scored_deliveries,
            (SELECT COUNT(*) FROM fact_delivery_pressure WHERE is_high_pressure) AS hp_deliveries,
            (SELECT COUNT(*) FROM fact_delivery WHERE is_wicket) AS total_dismissals,
            (SELECT COUNT(*) FROM fact_delivery WHERE is_bowler_wicket) AS bowler_wkts,
            (SELECT COUNT(DISTINCT comp_id) FROM dim_competition) AS total_comps
    """).fetchone()

    return {
        "total_matches": row[0],
        "played_matches": row[1],
        "ipl_matches": row[2],
        "total_deliveries": row[3],
        "scored_deliveries": row[4],
        "hp_deliveries": row[5],
        "total_dismissals": row[6],
        "bowler_wkts": row[7],
        "total_comps": row[8],
    }


@st.cache_data(ttl=3600)
def load_leaderboard(discipline: str = "batting", scope: str = "ipl", min_balls: int = 60) -> list[dict[str, Any]]:
    """Load ranked player leaderboard for batting or bowling across specified competition scope."""
    csv_name = f"top_10_{discipline}_{scope}.csv"
    csv_path = ARTIFACTS_DIR / "analytics" / csv_name

    if csv_path.exists():
        return _parse_csv(csv_path)

    engine = RankingEngine(get_db())
    if discipline in ["batters", "batting"]:
        return engine.score_all_batters(min_balls=min_balls, competition_scope=scope)[:10]
    return engine.score_all_bowlers(min_balls=min_balls, competition_scope=scope)[:10]


@st.cache_data(ttl=3600)
def load_all_players(discipline: str = "batting", scope: str = "ipl", min_balls: int = 45) -> list[dict[str, Any]]:
    """Load all qualified players for the given discipline and scope."""
    engine = RankingEngine(get_db())
    if discipline in ["batters", "batting"]:
        return engine.score_all_batters(min_balls=min_balls, competition_scope=scope)
    return engine.score_all_bowlers(min_balls=min_balls, competition_scope=scope)


@st.cache_data(ttl=3600)
def load_sensitivity_grid() -> list[dict[str, Any]]:
    """Load 7-scenario sensitivity analysis grid."""
    csv_path = ARTIFACTS_DIR / "analytics" / "ranking_sensitivity.csv"
    if csv_path.exists():
        return _parse_csv(csv_path)
    engine = RankingEngine(get_db())
    return engine.run_sensitivity_analysis()


@st.cache_data(ttl=3600)
def load_model_validation() -> dict[str, Any]:
    """Load model validation metadata and parameters."""
    json_path = ARTIFACTS_DIR / "analytics" / "model_validation.json"
    if json_path.exists():
        with json_path.open("r", encoding="utf-8") as f:
            return json.load(f)
    return {}


@st.cache_data(ttl=3600)
def load_pressure_distribution() -> list[dict[str, Any]]:
    """Load pressure tier delivery distribution and hazard metrics."""
    con = get_db()
    rows = con.execute("""
        SELECT 
            CASE 
                WHEN pressure_score < 30.0 THEN 'Low (<30)'
                WHEN pressure_score < 50.0 THEN 'Medium (30-50)'
                WHEN pressure_score < 65.0 THEN 'High (50-65)'
                ELSE 'Extreme (>=65)'
            END AS pressure_tier,
            COUNT(*) AS deliveries,
            ROUND(SUM(batter_runs) * 100.0 / NULLIF(COUNT(CASE WHEN is_batter_ball_faced THEN 1 END), 0), 2) AS bat_sr,
            ROUND(SUM(bowler_runs_conceded) * 6.0 / NULLIF(COUNT(CASE WHEN is_legal_delivery THEN 1 END), 0), 2) AS bowl_econ,
            ROUND(AVG(CASE WHEN is_dot_ball_batter THEN 1.0 ELSE 0.0 END) * 100, 2) AS dot_pct,
            ROUND(AVG(CASE WHEN is_boundary_clean THEN 1.0 ELSE 0.0 END) * 100, 2) AS bnd_pct,
            ROUND(AVG(CASE WHEN is_bowler_wicket THEN 1.0 ELSE 0.0 END) * 100, 2) AS wkt_hazard
        FROM fact_delivery_pressure
        WHERE pressure_score IS NOT NULL
        GROUP BY 1
        ORDER BY MIN(pressure_score)
    """).fetchall()

    return [
        {
            "pressure_tier": r[0],
            "deliveries": r[1],
            "bat_sr": r[2],
            "bowl_econ": r[3],
            "dot_pct": r[4],
            "bnd_pct": r[5],
            "wkt_hazard": r[6],
        }
        for r in rows
    ]


@st.cache_data(ttl=3600)
def load_player_profile_details(player_name: str) -> dict[str, Any]:
    """Extract exhaustive individual player delivery splits from DuckDB."""
    con = get_db()

    # 1. Batting splits
    bat_row = con.execute(f"""
        SELECT 
            COUNT(CASE WHEN is_batter_ball_faced THEN 1 END) AS career_bf,
            SUM(batter_runs) AS career_runs,
            ROUND(SUM(batter_runs) * 100.0 / NULLIF(COUNT(CASE WHEN is_batter_ball_faced THEN 1 END), 0), 2) AS career_sr,
            
            -- High pressure (P >= 50)
            COUNT(CASE WHEN is_high_pressure AND is_batter_ball_faced THEN 1 END) AS p_bf,
            SUM(CASE WHEN is_high_pressure THEN batter_runs ELSE 0 END) AS p_runs,
            ROUND(SUM(CASE WHEN is_high_pressure THEN batter_runs ELSE 0 END) * 100.0 / NULLIF(COUNT(CASE WHEN is_high_pressure AND is_batter_ball_faced THEN 1 END), 0), 2) AS p_sr,
            
            -- Extreme pressure (P >= 65)
            COUNT(CASE WHEN is_extreme_pressure AND is_batter_ball_faced THEN 1 END) AS ext_bf,
            SUM(CASE WHEN is_extreme_pressure THEN batter_runs ELSE 0 END) AS ext_runs,
            ROUND(SUM(CASE WHEN is_extreme_pressure THEN batter_runs ELSE 0 END) * 100.0 / NULLIF(COUNT(CASE WHEN is_extreme_pressure AND is_batter_ball_faced THEN 1 END), 0), 2) AS ext_sr,
            
            -- Phase splits under high pressure
            COUNT(CASE WHEN is_high_pressure AND innings_phase = 'Powerplay' AND is_batter_ball_faced THEN 1 END) AS pp_p_bf,
            ROUND(SUM(CASE WHEN is_high_pressure AND innings_phase = 'Powerplay' THEN batter_runs ELSE 0 END) * 100.0 / NULLIF(COUNT(CASE WHEN is_high_pressure AND innings_phase = 'Powerplay' AND is_batter_ball_faced THEN 1 END), 0), 2) AS pp_p_sr,
            COUNT(CASE WHEN is_high_pressure AND innings_phase = 'Middle' AND is_batter_ball_faced THEN 1 END) AS mid_p_bf,
            ROUND(SUM(CASE WHEN is_high_pressure AND innings_phase = 'Middle' THEN batter_runs ELSE 0 END) * 100.0 / NULLIF(COUNT(CASE WHEN is_high_pressure AND innings_phase = 'Middle' AND is_batter_ball_faced THEN 1 END), 0), 2) AS mid_p_sr,
            COUNT(CASE WHEN is_high_pressure AND innings_phase = 'Death' AND is_batter_ball_faced THEN 1 END) AS death_p_bf,
            ROUND(SUM(CASE WHEN is_high_pressure AND innings_phase = 'Death' THEN batter_runs ELSE 0 END) * 100.0 / NULLIF(COUNT(CASE WHEN is_high_pressure AND innings_phase = 'Death' AND is_batter_ball_faced THEN 1 END), 0), 2) AS death_p_sr,
            
            -- Chase vs Inn1
            COUNT(CASE WHEN is_high_pressure AND is_chase AND is_batter_ball_faced THEN 1 END) AS chase_p_bf,
            ROUND(SUM(CASE WHEN is_high_pressure AND is_chase THEN batter_runs ELSE 0 END) * 100.0 / NULLIF(COUNT(CASE WHEN is_high_pressure AND is_chase AND is_batter_ball_faced THEN 1 END), 0), 2) AS chase_p_sr,
            COUNT(CASE WHEN is_high_pressure AND NOT is_chase AND is_batter_ball_faced THEN 1 END) AS inn1_p_bf,
            ROUND(SUM(CASE WHEN is_high_pressure AND NOT is_chase THEN batter_runs ELSE 0 END) * 100.0 / NULLIF(COUNT(CASE WHEN is_high_pressure AND NOT is_chase AND is_batter_ball_faced THEN 1 END), 0), 2) AS inn1_p_sr

        FROM fact_delivery_pressure
        WHERE striker_name = '{player_name}'
    """).fetchone()

    # 2. Bowling splits
    bowl_row = con.execute(f"""
        SELECT 
            COUNT(CASE WHEN is_legal_delivery THEN 1 END) AS career_balls,
            SUM(bowler_runs_conceded) AS career_runs,
            ROUND(SUM(bowler_runs_conceded) * 6.0 / NULLIF(COUNT(CASE WHEN is_legal_delivery THEN 1 END), 0), 2) AS career_econ,
            SUM(CASE WHEN is_bowler_wicket THEN 1 ELSE 0 END) AS career_wkts,
            
            -- High pressure (P >= 50)
            COUNT(CASE WHEN is_high_pressure AND is_legal_delivery THEN 1 END) AS p_balls,
            SUM(CASE WHEN is_high_pressure THEN bowler_runs_conceded ELSE 0 END) AS p_runs,
            ROUND(SUM(CASE WHEN is_high_pressure THEN bowler_runs_conceded ELSE 0 END) * 6.0 / NULLIF(COUNT(CASE WHEN is_high_pressure AND is_legal_delivery THEN 1 END), 0), 2) AS p_econ,
            SUM(CASE WHEN is_high_pressure AND is_bowler_wicket THEN 1 ELSE 0 END) AS p_wkts,
            
            -- Phase splits under high pressure
            COUNT(CASE WHEN is_high_pressure AND innings_phase = 'Powerplay' AND is_legal_delivery THEN 1 END) AS pp_p_balls,
            ROUND(SUM(CASE WHEN is_high_pressure AND innings_phase = 'Powerplay' THEN bowler_runs_conceded ELSE 0 END) * 6.0 / NULLIF(COUNT(CASE WHEN is_high_pressure AND innings_phase = 'Powerplay' AND is_legal_delivery THEN 1 END), 0), 2) AS pp_p_econ,
            COUNT(CASE WHEN is_high_pressure AND innings_phase = 'Middle' AND is_legal_delivery THEN 1 END) AS mid_p_balls,
            ROUND(SUM(CASE WHEN is_high_pressure AND innings_phase = 'Middle' THEN bowler_runs_conceded ELSE 0 END) * 6.0 / NULLIF(COUNT(CASE WHEN is_high_pressure AND innings_phase = 'Middle' AND is_legal_delivery THEN 1 END), 0), 2) AS mid_p_econ,
            COUNT(CASE WHEN is_high_pressure AND innings_phase = 'Death' AND is_legal_delivery THEN 1 END) AS death_p_balls,
            ROUND(SUM(CASE WHEN is_high_pressure AND innings_phase = 'Death' THEN bowler_runs_conceded ELSE 0 END) * 6.0 / NULLIF(COUNT(CASE WHEN is_high_pressure AND innings_phase = 'Death' AND is_legal_delivery THEN 1 END), 0), 2) AS death_p_econ

        FROM fact_delivery_pressure
        WHERE bowler_name = '{player_name}'
    """).fetchone()

    return {
        "batting": {
            "career_bf": (bat_row[0] if bat_row else 0) or 0,
            "career_runs": (bat_row[1] if bat_row else 0) or 0,
            "career_sr": (bat_row[2] if bat_row else 0.0) or 0.0,
            "p_bf": (bat_row[3] if bat_row else 0) or 0,
            "p_runs": (bat_row[4] if bat_row else 0) or 0,
            "p_sr": (bat_row[5] if bat_row else 0.0) or 0.0,
            "ext_bf": (bat_row[6] if bat_row else 0) or 0,
            "ext_sr": (bat_row[8] if bat_row else 0.0) or 0.0,
            "pp_p_bf": (bat_row[9] if bat_row else 0) or 0,
            "pp_p_sr": (bat_row[10] if bat_row else 0.0) or 0.0,
            "mid_p_bf": (bat_row[11] if bat_row else 0) or 0,
            "mid_p_sr": (bat_row[12] if bat_row else 0.0) or 0.0,
            "death_p_bf": (bat_row[13] if bat_row else 0) or 0,
            "death_p_sr": (bat_row[14] if bat_row else 0.0) or 0.0,
            "chase_p_bf": (bat_row[15] if bat_row else 0) or 0,
            "chase_p_sr": (bat_row[16] if bat_row else 0.0) or 0.0,
            "inn1_p_bf": (bat_row[17] if bat_row else 0) or 0,
            "inn1_p_sr": (bat_row[18] if bat_row else 0.0) or 0.0,
        },
        "bowling": {
            "career_balls": (bowl_row[0] if bowl_row else 0) or 0,
            "career_runs": (bowl_row[1] if bowl_row else 0) or 0,
            "career_econ": (bowl_row[2] if bowl_row else 0.0) or 0.0,
            "career_wkts": (bowl_row[3] if bowl_row else 0) or 0,
            "p_balls": (bowl_row[4] if bowl_row else 0) or 0,
            "p_runs": (bowl_row[5] if bowl_row else 0) or 0,
            "p_econ": (bowl_row[6] if bowl_row else 0.0) or 0.0,
            "p_wkts": (bowl_row[7] if bowl_row else 0) or 0,
            "pp_p_balls": (bowl_row[8] if bowl_row else 0) or 0,
            "pp_p_econ": (bowl_row[9] if bowl_row else 0.0) or 0.0,
            "mid_p_balls": (bowl_row[10] if bowl_row else 0) or 0,
            "mid_p_econ": (bowl_row[11] if bowl_row else 0.0) or 0.0,
            "death_p_balls": (bowl_row[12] if bowl_row else 0) or 0,
            "death_p_econ": (bowl_row[13] if bowl_row else 0.0) or 0.0,
        }
    }
