"""
RR ScoutIQ — Player Evaluation Module
Computes multidimensional performance metrics for batters and bowlers under continuous
and quantile pressure states, comparing clutch execution against player and league baselines.
"""

from __future__ import annotations
from typing import Any
import duckdb


class PlayerEvaluator:
    """Evaluates batting and bowling performance under pressure using DuckDB SQL."""

    def __init__(self, con: duckdb.DuckDBPyConnection):
        self.con = con

    def evaluate_batters(self, min_pressure_balls: int = 1) -> list[dict[str, Any]]:
        """Compute comprehensive batting metrics under pressure and baseline conditions.

        Args:
            min_pressure_balls: Minimum pressure balls faced filter (defaults to 1 for all players).

        Returns:
            List of player batting performance dictionaries.
        """
        sql = f"""
        WITH player_meta AS (
            SELECT 
                p.canonical_player_id,
                MAX(p.player_name) AS player_name,
                STRING_AGG(DISTINCT p.team_name, ', ' ORDER BY p.team_name) AS teams_represented,
                STRING_AGG(DISTINCT p.comp_name, ', ' ORDER BY p.comp_name) AS competitions_played,
                COUNT(DISTINCT p.comp_id) AS comp_count,
                COUNT(DISTINCT p.match_id) AS matches_played,
                BOOL_OR(p.is_wk) AS is_wicketkeeper,
                ROUND(AVG(p.batting_order), 1) AS avg_batting_order
            FROM (
                SELECT 
                    p11.match_id,
                    p11.canonical_player_id,
                    b.player_name,
                    t.team_name,
                    c.comp_id,
                    c.comp_name,
                    p11.is_wk,
                    p11.batting_order
                FROM fact_playing_eleven p11
                JOIN fact_match m ON p11.match_id = m.match_id
                JOIN dim_competition c ON m.comp_id = c.comp_id
                JOIN dim_team t ON p11.team_id = t.team_id AND m.comp_id = t.comp_id
                JOIN bridge_competition_team_player b ON p11.canonical_player_id = b.canonical_player_id AND m.comp_id = b.comp_id AND p11.team_id = b.team_id
                WHERE NOT p11.is_super_over_duplicate
            ) p
            GROUP BY p.canonical_player_id
        ),
        bat_agg AS (
            SELECT 
                d.canonical_striker_id AS player_id,
                MAX(d.striker_name) AS striker_name,
                
                -- Overall Baseline
                COUNT(CASE WHEN d.is_batter_ball_faced THEN 1 END) AS overall_bf,
                SUM(d.batter_runs) AS overall_runs,
                ROUND(SUM(d.batter_runs) * 100.0 / NULLIF(COUNT(CASE WHEN d.is_batter_ball_faced THEN 1 END), 0), 2) AS overall_sr,
                ROUND(AVG(CASE WHEN d.is_dot_ball_batter THEN 1.0 ELSE 0.0 END) * 100, 2) AS overall_dot_pct,
                ROUND(AVG(CASE WHEN d.is_boundary_clean THEN 1.0 ELSE 0.0 END) * 100, 2) AS overall_bnd_pct,
                COUNT(CASE WHEN d.is_wicket AND d.canonical_dismissed_player_id = d.canonical_striker_id THEN 1 END) AS overall_outs,
                
                -- High Pressure (P >= 50.0)
                COUNT(CASE WHEN d.is_high_pressure AND d.is_batter_ball_faced THEN 1 END) AS pressure_bf,
                SUM(CASE WHEN d.is_high_pressure THEN d.batter_runs ELSE 0 END) AS pressure_runs,
                ROUND(SUM(CASE WHEN d.is_high_pressure THEN d.batter_runs ELSE 0 END) * 100.0 / NULLIF(COUNT(CASE WHEN d.is_high_pressure AND d.is_batter_ball_faced THEN 1 END), 0), 2) AS pressure_sr,
                ROUND(AVG(CASE WHEN d.is_high_pressure THEN d.is_dot_ball_batter::INT ELSE NULL END) * 100, 2) AS pressure_dot_pct,
                ROUND(AVG(CASE WHEN d.is_high_pressure THEN d.is_boundary_clean::INT ELSE NULL END) * 100, 2) AS pressure_bnd_pct,
                COUNT(CASE WHEN d.is_high_pressure AND d.is_wicket AND d.canonical_dismissed_player_id = d.canonical_striker_id THEN 1 END) AS pressure_outs,
                
                -- Extreme Pressure (P >= 65.0)
                COUNT(CASE WHEN d.is_extreme_pressure AND d.is_batter_ball_faced THEN 1 END) AS extreme_bf,
                SUM(CASE WHEN d.is_extreme_pressure THEN d.batter_runs ELSE 0 END) AS extreme_runs,
                ROUND(SUM(CASE WHEN d.is_extreme_pressure THEN d.batter_runs ELSE 0 END) * 100.0 / NULLIF(COUNT(CASE WHEN d.is_extreme_pressure AND d.is_batter_ball_faced THEN 1 END), 0), 2) AS extreme_sr,
                
                -- Innings Splits under High Pressure
                COUNT(CASE WHEN d.is_high_pressure AND d.is_chase AND d.is_batter_ball_faced THEN 1 END) AS chase_p_bf,
                ROUND(SUM(CASE WHEN d.is_high_pressure AND d.is_chase THEN d.batter_runs ELSE 0 END) * 100.0 / NULLIF(COUNT(CASE WHEN d.is_high_pressure AND d.is_chase AND d.is_batter_ball_faced THEN 1 END), 0), 2) AS chase_p_sr,
                COUNT(CASE WHEN d.is_high_pressure AND NOT d.is_chase AND d.is_batter_ball_faced THEN 1 END) AS inn1_p_bf,
                ROUND(SUM(CASE WHEN d.is_high_pressure AND NOT d.is_chase THEN d.batter_runs ELSE 0 END) * 100.0 / NULLIF(COUNT(CASE WHEN d.is_high_pressure AND NOT d.is_chase AND d.is_batter_ball_faced THEN 1 END), 0), 2) AS inn1_p_sr,
                
                -- Competition Tier Splits under High Pressure
                COUNT(CASE WHEN d.competition_category = 'IPL' AND d.is_batter_ball_faced THEN 1 END) AS ipl_overall_bf,
                SUM(CASE WHEN d.competition_category = 'IPL' THEN d.batter_runs ELSE 0 END) AS ipl_overall_runs,
                ROUND(SUM(CASE WHEN d.competition_category = 'IPL' THEN d.batter_runs ELSE 0 END) * 100.0 / NULLIF(COUNT(CASE WHEN d.competition_category = 'IPL' AND d.is_batter_ball_faced THEN 1 END), 0), 2) AS ipl_overall_sr,
                COUNT(CASE WHEN d.is_high_pressure AND d.competition_category = 'IPL' AND d.is_batter_ball_faced THEN 1 END) AS ipl_p_bf,
                SUM(CASE WHEN d.is_high_pressure AND d.competition_category = 'IPL' THEN d.batter_runs ELSE 0 END) AS ipl_p_runs,
                ROUND(SUM(CASE WHEN d.is_high_pressure AND d.competition_category = 'IPL' THEN d.batter_runs ELSE 0 END) * 100.0 / NULLIF(COUNT(CASE WHEN d.is_high_pressure AND d.competition_category = 'IPL' AND d.is_batter_ball_faced THEN 1 END), 0), 2) AS ipl_p_sr,
                COUNT(CASE WHEN d.is_high_pressure AND d.competition_category = 'IPL' AND d.is_wicket AND d.canonical_dismissed_player_id = d.canonical_striker_id THEN 1 END) AS ipl_p_outs,
                ROUND(AVG(CASE WHEN d.is_high_pressure AND d.competition_category = 'IPL' THEN d.is_dot_ball_batter::INT ELSE NULL END) * 100, 2) AS ipl_p_dot_pct,
                ROUND(AVG(CASE WHEN d.is_high_pressure AND d.competition_category = 'IPL' THEN d.is_boundary_clean::INT ELSE NULL END) * 100, 2) AS ipl_p_bnd_pct,
                ROUND(SUM(CASE WHEN d.is_high_pressure AND d.competition_category = 'IPL' THEN d.batter_runs ELSE 0 END) / CAST(GREATEST(1, COUNT(CASE WHEN d.is_high_pressure AND d.competition_category = 'IPL' AND d.is_wicket AND d.canonical_dismissed_player_id = d.canonical_striker_id THEN 1 END)) AS FLOAT), 2) AS ipl_p_avg,
                ROUND(
                    ROUND(SUM(CASE WHEN d.is_high_pressure AND d.competition_category = 'IPL' THEN d.batter_runs ELSE 0 END) * 100.0 / NULLIF(COUNT(CASE WHEN d.is_high_pressure AND d.competition_category = 'IPL' AND d.is_batter_ball_faced THEN 1 END), 0), 2)
                    - ROUND(SUM(CASE WHEN d.competition_category = 'IPL' THEN d.batter_runs ELSE 0 END) * 100.0 / NULLIF(COUNT(CASE WHEN d.competition_category = 'IPL' AND d.is_batter_ball_faced THEN 1 END), 0), 2),
                    2
                ) AS ipl_clutch_sr_delta,
                COUNT(CASE WHEN d.is_high_pressure AND d.is_tier1_competition AND d.is_batter_ball_faced THEN 1 END) AS tier1_p_bf,
                ROUND(SUM(CASE WHEN d.is_high_pressure AND d.is_tier1_competition THEN d.batter_runs ELSE 0 END) * 100.0 / NULLIF(COUNT(CASE WHEN d.is_high_pressure AND d.is_tier1_competition AND d.is_batter_ball_faced THEN 1 END), 0), 2) AS tier1_p_sr,

                -- Bowling participation for role detection
                (SELECT COUNT(*) FROM fact_delivery_pressure b WHERE b.canonical_bowler_id = d.canonical_striker_id AND b.is_legal_delivery) AS balls_bowled

            FROM fact_delivery_pressure d
            GROUP BY d.canonical_striker_id
            HAVING pressure_bf >= {min_pressure_balls}
        )
        SELECT 
            b.*,
            COALESCE(m.player_name, b.striker_name) AS full_player_name,
            COALESCE(m.teams_represented, 'Unattached') AS teams_represented,
            COALESCE(m.competitions_played, 'Unknown') AS competitions_played,
            COALESCE(m.matches_played, 0) AS matches_played,
            COALESCE(m.is_wicketkeeper, FALSE) AS is_wicketkeeper,
            COALESCE(m.avg_batting_order, 5.0) AS avg_batting_order,
            
            -- Runs per dismissal under pressure
            ROUND(b.pressure_runs / CAST(GREATEST(1, b.pressure_outs) AS FLOAT), 2) AS pressure_avg,
            
            -- Clutch elevation deltas vs overall baseline
            ROUND(b.pressure_sr - b.overall_sr, 2) AS clutch_sr_delta,
            ROUND(b.overall_dot_pct - b.pressure_dot_pct, 2) AS clutch_dot_delta,

            -- Inferred Player Role
            CASE 
                WHEN m.is_wicketkeeper THEN 'Wicketkeeper-Batter'
                WHEN b.balls_bowled >= 120 AND b.pressure_bf >= 60 THEN 'All-Rounder'
                WHEN b.balls_bowled >= 60 THEN 'Batting All-Rounder'
                ELSE 'Specialist Batter'
            END AS player_role

        FROM bat_agg b
        LEFT JOIN player_meta m ON b.player_id = m.canonical_player_id
        ORDER BY b.pressure_runs DESC
        """
        rows = self.con.execute(sql).fetchall()
        cols = [c[0] for c in self.con.description]
        return [dict(zip(cols, r)) for r in rows]

    def evaluate_bowlers(self, min_pressure_balls: int = 1) -> list[dict[str, Any]]:
        """Compute comprehensive bowling metrics under pressure and baseline conditions.

        Args:
            min_pressure_balls: Minimum pressure legal balls bowled filter.

        Returns:
            List of player bowling performance dictionaries.
        """
        sql = f"""
        WITH player_meta AS (
            SELECT 
                p11.canonical_player_id,
                MAX(b.player_name) AS player_name,
                STRING_AGG(DISTINCT t.team_name, ', ' ORDER BY t.team_name) AS teams_represented,
                STRING_AGG(DISTINCT c.comp_name, ', ' ORDER BY c.comp_name) AS competitions_played,
                COUNT(DISTINCT c.comp_id) AS comp_count,
                COUNT(DISTINCT p11.match_id) AS matches_played
            FROM fact_playing_eleven p11
            JOIN fact_match m ON p11.match_id = m.match_id
            JOIN dim_competition c ON m.comp_id = c.comp_id
            JOIN dim_team t ON p11.team_id = t.team_id AND m.comp_id = t.comp_id
            JOIN bridge_competition_team_player b ON p11.canonical_player_id = b.canonical_player_id AND m.comp_id = b.comp_id AND p11.team_id = b.team_id
            WHERE NOT p11.is_super_over_duplicate
            GROUP BY p11.canonical_player_id
        ),
        bowl_agg AS (
            SELECT 
                d.canonical_bowler_id AS player_id,
                MAX(d.bowler_name) AS bowler_name,
                MAX(d.pace_or_spin_clean) AS bowling_style,
                
                -- Overall Baseline
                COUNT(CASE WHEN d.is_legal_delivery THEN 1 END) AS overall_balls,
                SUM(d.bowler_runs_conceded) AS overall_runs,
                ROUND(SUM(d.bowler_runs_conceded) * 6.0 / NULLIF(COUNT(CASE WHEN d.is_legal_delivery THEN 1 END), 0), 2) AS overall_econ,
                ROUND(AVG(CASE WHEN d.is_dot_ball_bowler THEN 1.0 ELSE 0.0 END) * 100, 2) AS overall_dot_pct,
                ROUND(AVG(CASE WHEN d.is_boundary_clean THEN 1.0 ELSE 0.0 END) * 100, 2) AS overall_bnd_pct,
                SUM(CASE WHEN d.is_bowler_wicket THEN 1 ELSE 0 END) AS overall_wkts,
                
                -- High Pressure (P >= 50.0)
                COUNT(CASE WHEN d.is_high_pressure AND d.is_legal_delivery THEN 1 END) AS pressure_balls,
                SUM(CASE WHEN d.is_high_pressure THEN d.bowler_runs_conceded ELSE 0 END) AS pressure_runs,
                ROUND(SUM(CASE WHEN d.is_high_pressure THEN d.bowler_runs_conceded ELSE 0 END) * 6.0 / NULLIF(COUNT(CASE WHEN d.is_high_pressure AND d.is_legal_delivery THEN 1 END), 0), 2) AS pressure_econ,
                ROUND(AVG(CASE WHEN d.is_high_pressure THEN d.is_dot_ball_bowler::INT ELSE NULL END) * 100, 2) AS pressure_dot_pct,
                ROUND(AVG(CASE WHEN d.is_high_pressure THEN d.is_boundary_clean::INT ELSE NULL END) * 100, 2) AS pressure_bnd_pct,
                SUM(CASE WHEN d.is_high_pressure AND d.is_bowler_wicket THEN 1 ELSE 0 END) AS pressure_wkts,
                ROUND(SUM(CASE WHEN d.is_high_pressure AND d.is_bowler_wicket THEN 1 ELSE 0 END) * 100.0 / NULLIF(COUNT(CASE WHEN d.is_high_pressure AND d.is_legal_delivery THEN 1 END), 0), 2) AS pressure_wkt_pct,
                
                -- Extreme Pressure (P >= 65.0)
                COUNT(CASE WHEN d.is_extreme_pressure AND d.is_legal_delivery THEN 1 END) AS extreme_balls,
                SUM(CASE WHEN d.is_extreme_pressure THEN d.bowler_runs_conceded ELSE 0 END) AS extreme_runs,
                ROUND(SUM(CASE WHEN d.is_extreme_pressure THEN d.bowler_runs_conceded ELSE 0 END) * 6.0 / NULLIF(COUNT(CASE WHEN d.is_extreme_pressure AND d.is_legal_delivery THEN 1 END), 0), 2) AS extreme_econ,
                SUM(CASE WHEN d.is_extreme_pressure AND d.is_bowler_wicket THEN 1 ELSE 0 END) AS extreme_wkts,

                -- Death Overs & Chase Defense splits
                COUNT(CASE WHEN d.is_high_pressure AND d.innings_phase = 'Death' AND d.is_legal_delivery THEN 1 END) AS death_p_balls,
                ROUND(SUM(CASE WHEN d.is_high_pressure AND d.innings_phase = 'Death' THEN d.bowler_runs_conceded ELSE 0 END) * 6.0 / NULLIF(COUNT(CASE WHEN d.is_high_pressure AND d.innings_phase = 'Death' AND d.is_legal_delivery THEN 1 END), 0), 2) AS death_p_econ,
                COUNT(CASE WHEN d.is_high_pressure AND d.is_chase AND d.is_legal_delivery THEN 1 END) AS chase_defend_p_balls,
                ROUND(SUM(CASE WHEN d.is_high_pressure AND d.is_chase THEN d.bowler_runs_conceded ELSE 0 END) * 6.0 / NULLIF(COUNT(CASE WHEN d.is_high_pressure AND d.is_chase AND d.is_legal_delivery THEN 1 END), 0), 2) AS chase_defend_p_econ,

                -- Competition Tier Splits
                COUNT(CASE WHEN d.competition_category = 'IPL' AND d.is_legal_delivery THEN 1 END) AS ipl_overall_balls,
                SUM(CASE WHEN d.competition_category = 'IPL' THEN d.bowler_runs_conceded ELSE 0 END) AS ipl_overall_runs,
                ROUND(SUM(CASE WHEN d.competition_category = 'IPL' THEN d.bowler_runs_conceded ELSE 0 END) * 6.0 / NULLIF(COUNT(CASE WHEN d.competition_category = 'IPL' AND d.is_legal_delivery THEN 1 END), 0), 2) AS ipl_overall_econ,
                COUNT(CASE WHEN d.is_high_pressure AND d.competition_category = 'IPL' AND d.is_legal_delivery THEN 1 END) AS ipl_p_balls,
                SUM(CASE WHEN d.is_high_pressure AND d.competition_category = 'IPL' THEN d.bowler_runs_conceded ELSE 0 END) AS ipl_p_runs,
                ROUND(SUM(CASE WHEN d.is_high_pressure AND d.competition_category = 'IPL' THEN d.bowler_runs_conceded ELSE 0 END) * 6.0 / NULLIF(COUNT(CASE WHEN d.is_high_pressure AND d.competition_category = 'IPL' AND d.is_legal_delivery THEN 1 END), 0), 2) AS ipl_p_econ,
                SUM(CASE WHEN d.is_high_pressure AND d.competition_category = 'IPL' AND d.is_bowler_wicket THEN 1 ELSE 0 END) AS ipl_p_wkts,
                ROUND(SUM(CASE WHEN d.is_high_pressure AND d.competition_category = 'IPL' AND d.is_bowler_wicket THEN 1 ELSE 0 END) * 100.0 / NULLIF(COUNT(CASE WHEN d.is_high_pressure AND d.competition_category = 'IPL' AND d.is_legal_delivery THEN 1 END), 0), 2) AS ipl_p_wkt_pct,
                ROUND(AVG(CASE WHEN d.is_high_pressure AND d.competition_category = 'IPL' THEN d.is_dot_ball_bowler::INT ELSE NULL END) * 100, 2) AS ipl_p_dot_pct,
                ROUND(AVG(CASE WHEN d.is_high_pressure AND d.competition_category = 'IPL' THEN d.is_boundary_clean::INT ELSE NULL END) * 100, 2) AS ipl_p_bnd_pct,
                ROUND(
                    ROUND(SUM(CASE WHEN d.competition_category = 'IPL' THEN d.bowler_runs_conceded ELSE 0 END) * 6.0 / NULLIF(COUNT(CASE WHEN d.competition_category = 'IPL' AND d.is_legal_delivery THEN 1 END), 0), 2)
                    - ROUND(SUM(CASE WHEN d.is_high_pressure AND d.competition_category = 'IPL' THEN d.bowler_runs_conceded ELSE 0 END) * 6.0 / NULLIF(COUNT(CASE WHEN d.is_high_pressure AND d.competition_category = 'IPL' AND d.is_legal_delivery THEN 1 END), 0), 2),
                    2
                ) AS ipl_clutch_econ_delta,
                COUNT(CASE WHEN d.is_high_pressure AND d.competition_category = 'IPL' AND d.innings_phase = 'Death' AND d.is_legal_delivery THEN 1 END) AS ipl_death_p_balls,
                ROUND(SUM(CASE WHEN d.is_high_pressure AND d.competition_category = 'IPL' AND d.innings_phase = 'Death' THEN d.bowler_runs_conceded ELSE 0 END) * 6.0 / NULLIF(COUNT(CASE WHEN d.is_high_pressure AND d.competition_category = 'IPL' AND d.innings_phase = 'Death' AND d.is_legal_delivery THEN 1 END), 0), 2) AS ipl_death_p_econ,
                COUNT(CASE WHEN d.is_high_pressure AND d.is_tier1_competition AND d.is_legal_delivery THEN 1 END) AS tier1_p_balls,
                ROUND(SUM(CASE WHEN d.is_high_pressure AND d.is_tier1_competition THEN d.bowler_runs_conceded ELSE 0 END) * 6.0 / NULLIF(COUNT(CASE WHEN d.is_high_pressure AND d.is_tier1_competition AND d.is_legal_delivery THEN 1 END), 0), 2) AS tier1_p_econ,

                -- Batting participation for role detection
                (SELECT COUNT(*) FROM fact_delivery_pressure b WHERE b.canonical_striker_id = d.canonical_bowler_id AND b.is_batter_ball_faced) AS balls_faced

            FROM fact_delivery_pressure d
            GROUP BY d.canonical_bowler_id
            HAVING pressure_balls >= {min_pressure_balls}
        )
        SELECT 
            b.*,
            COALESCE(m.player_name, b.bowler_name) AS full_player_name,
            COALESCE(m.teams_represented, 'Unattached') AS teams_represented,
            COALESCE(m.competitions_played, 'Unknown') AS competitions_played,
            COALESCE(m.matches_played, 0) AS matches_played,
            
            -- Strike rate per wicket under pressure (balls per wicket)
            ROUND(b.pressure_balls / CAST(GREATEST(1, b.pressure_wkts) AS FLOAT), 1) AS pressure_bowling_sr,

            -- Clutch economy delta (positive = bowler tightened up under pressure)
            ROUND(b.overall_econ - b.pressure_econ, 2) AS clutch_econ_delta,
            ROUND(b.pressure_dot_pct - b.overall_dot_pct, 2) AS clutch_dot_delta,

            -- Inferred Player Role
            CASE
                WHEN b.balls_faced >= 120 AND b.pressure_balls >= 60 THEN 'All-Rounder'
                WHEN b.balls_faced >= 60 THEN 'Bowling All-Rounder'
                WHEN b.bowling_style = 'Spin' THEN 'Spin Bowler'
                ELSE 'Pace Bowler'
            END AS player_role

        FROM bowl_agg b
        LEFT JOIN player_meta m ON b.player_id = m.canonical_player_id
        ORDER BY b.pressure_wkts DESC, b.pressure_econ ASC
        """
        rows = self.con.execute(sql).fetchall()
        cols = [c[0] for c in self.con.description]
        return [dict(zip(cols, r)) for r in rows]
