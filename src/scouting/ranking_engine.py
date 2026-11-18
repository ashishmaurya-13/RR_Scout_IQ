"""
RR ScoutIQ — Scouting & Player Ranking Engine (Audited & Calibrated)
Computes multi-criteria pressure reliability scores, conducts sensitivity analysis,
and outputs certified top 10 batters and bowlers for the Rajasthan Royals IPL 2027 Auction Strategy.

Supports:
1. Primary Mode: IPL-Only (pure tournament reality, zero synthetic cross-competition multipliers).
2. Supplementary Mode: All-T20 (global context across T20Is and developmental competitions).
"""

from __future__ import annotations
import json
import math
from pathlib import Path
from typing import Any
import duckdb

from config.settings import ARTIFACTS_DIR, DUCKDB_PATH
from src.analytics.competition_normalizer import CompetitionNormalizer
from src.evaluation.player_evaluator import PlayerEvaluator
from src.ingestion.database import get_duckdb_connection
from src.models.reliability_model import EmpiricalBayesShrinkage


class RankingEngine:
    """End-to-end analytical ranking engine for pressure reliability evaluation."""

    def __init__(self, con: duckdb.DuckDBPyConnection | None = None):
        self.con = con or get_duckdb_connection(DUCKDB_PATH, read_only=True)
        self.evaluator = PlayerEvaluator(self.con)
        self.normalizer = CompetitionNormalizer(self.con)

        # Empirical high-pressure population priors:
        # IPL-specific priors (calibrated from 18,501 IPL high-pressure deliveries)
        self.ipl_priors = {
            "bat_sr": 147.19,
            "bat_avg": 22.0,
            "bat_dot_pct": 33.10,
            "bnd_pct": 18.33,
            "bowl_econ": 9.28,
            "wkt_pct": 6.43,
            "bowl_dot_pct": 32.86,
        }

        # Overall T20 priors (calibrated across all 43,831 high-pressure deliveries)
        hp_bench = self.normalizer.benchmarks["high_pressure_overall"]
        self.overall_priors = {
            "bat_sr": hp_bench["bat_sr"],
            "bat_avg": 20.0,
            "bat_dot_pct": hp_bench["bat_dot_pct"],
            "bnd_pct": hp_bench["bnd_pct"],
            "bowl_econ": hp_bench["bowl_econ"],
            "wkt_pct": hp_bench["wkt_pct"],
            "bowl_dot_pct": hp_bench["bowl_dot_pct"],
        }

        # Population between-player standard deviations
        self.std_devs = self.normalizer.benchmarks["std_devs"]

    def score_all_batters(
        self,
        min_balls: int = 60,
        competition_scope: str = "ipl",
        half_reliability_n: float = 45.0,
    ) -> list[dict[str, Any]]:
        """Score all eligible batters using multi-criteria pressure reliability formulation.

        Args:
            min_balls: Minimum pressure balls faced threshold.
            competition_scope: 'ipl' for primary IPL-only, or 'all' for broader T20.
            half_reliability_n: Empirical Bayes shrinkage constant n_0 (default 45.0).

        Returns:
            Sorted list of scored batter dictionaries.
        """
        raw_batters = self.evaluator.evaluate_batters(min_pressure_balls=1)
        priors = self.ipl_priors if competition_scope == "ipl" else self.overall_priors

        sr_shrik = EmpiricalBayesShrinkage(priors["bat_sr"], self.std_devs["bat_sr"], half_reliability_n=half_reliability_n)
        avg_shrik = EmpiricalBayesShrinkage(priors["bat_avg"], self.std_devs["bat_avg"], half_reliability_n=half_reliability_n)
        dot_shrik = EmpiricalBayesShrinkage(priors["bat_dot_pct"], self.std_devs["bat_dot_pct"], half_reliability_n=half_reliability_n)
        bnd_shrik = EmpiricalBayesShrinkage(priors["bnd_pct"], 6.5, half_reliability_n=half_reliability_n)

        scored: list[dict[str, Any]] = []

        for b in raw_batters:
            if competition_scope == "ipl":
                n = b["ipl_p_bf"]
                raw_sr = b["ipl_p_sr"]
                raw_runs = b["ipl_p_runs"]
                raw_avg = float(b["ipl_p_avg"]) if b["ipl_p_avg"] is not None else 20.0
                raw_dot = b["ipl_p_dot_pct"]
                raw_bnd = b["ipl_p_bnd_pct"]
                raw_clutch = b["ipl_clutch_sr_delta"] or 0.0
                baseline_sr = b["ipl_overall_sr"]
                total_balls = b["ipl_overall_bf"]
            else:
                n = b["pressure_bf"]
                raw_sr = b["pressure_sr"]
                raw_runs = b["pressure_runs"]
                raw_avg = float(b["pressure_avg"]) if b["pressure_avg"] is not None else 20.0
                raw_dot = b["pressure_dot_pct"]
                raw_bnd = b["pressure_bnd_pct"]
                raw_clutch = b["clutch_sr_delta"] or 0.0
                baseline_sr = b["overall_sr"]
                total_balls = b["overall_bf"]

            if n < min_balls:
                continue

            # Empirical Bayes Shrinkage
            sr_res = sr_shrik.shrink(raw_sr, n)
            eff_avg = min(50.0, max(5.0, raw_avg))
            avg_res = avg_shrik.shrink(eff_avg, n)
            dot_res = dot_shrik.shrink(raw_dot, n)
            bnd_res = bnd_shrik.shrink(raw_bnd, n)

            # Standardized Z-Scores
            z_sr = (sr_res.shrunk_value - priors["bat_sr"]) / self.std_devs["bat_sr"]
            z_avg = (avg_res.shrunk_value - priors["bat_avg"]) / self.std_devs["bat_avg"]
            z_dot = (priors["bat_dot_pct"] - dot_res.shrunk_value) / self.std_devs["bat_dot_pct"]
            z_bnd = (bnd_res.shrunk_value - priors["bnd_pct"]) / 6.5
            z_clutch = max(-2.5, min(2.5, raw_clutch / 20.0))

            # Non-redundant composite weights (sum = 1.00; volume is captured via Bayesian lambda)
            comp_metric = (
                0.35 * z_sr +
                0.20 * z_avg +
                0.15 * z_dot +
                0.15 * z_bnd +
                0.15 * z_clutch
            )

            # Final Score: Centered at 50.0, rescaled with Bayesian reliability factor
            final_score = round(50.0 + 12.0 * comp_metric * math.sqrt(sr_res.reliability_factor), 2)
            final_score = max(0.0, min(100.0, final_score))

            # Objective qualitative tags (no unverified auction speculation)
            strengths = []
            if raw_sr >= 185.0:
                strengths.append(f"Elite pressure SR ({raw_sr:.1f})")
            elif raw_sr >= 170.0:
                strengths.append(f"High pressure SR ({raw_sr:.1f})")
            if raw_clutch >= 20.0:
                strengths.append(f"Major clutch elevation (+{raw_clutch:.1f} SR above baseline)")
            elif raw_clutch >= 10.0:
                strengths.append(f"Positive clutch elevation (+{raw_clutch:.1f} SR)")
            if raw_dot <= 25.0:
                strengths.append(f"Superior strike rotation ({raw_dot:.1f}% dot)")
            if raw_bnd >= 24.0:
                strengths.append(f"High boundary frequency ({raw_bnd:.1f}%)")
            if eff_avg >= 35.0:
                strengths.append(f"Strong wicket preservation ({eff_avg:.1f} runs/out)")

            limitations = []
            if raw_dot >= 32.0:
                limitations.append(f"Elevated dot ball rate ({raw_dot:.1f}%)")
            if raw_clutch < -5.0:
                limitations.append(f"Scoring deceleration under pressure ({raw_clutch:.1f} SR)")
            if n < 90:
                limitations.append(f"Moderate sample volume ({n} pressure balls)")
            if competition_scope != "ipl" and b["ipl_p_bf"] < 40:
                limitations.append(f"Limited IPL exposure ({b['ipl_p_bf']} IPL balls)")

            record = {
                "player_id": b["player_id"],
                "canonical_player_id": b["player_id"],
                "player_name": b["full_player_name"],
                "player_role": b["player_role"],
                "pressure_score": final_score,
                "confidence_tier": sr_res.confidence_tier,
                "reliability_factor": sr_res.reliability_factor,
                "pressure_balls_faced": n,
                "total_balls_faced": total_balls,
                "pressure_runs": raw_runs,
                "pressure_sr": raw_sr,
                "shrunk_pressure_sr": sr_res.shrunk_value,
                "ci_lower_90_sr": sr_res.ci_lower_90,
                "ci_upper_90_sr": sr_res.ci_upper_90,
                "overall_sr": baseline_sr,
                "clutch_sr_delta": raw_clutch,
                "pressure_dot_pct": raw_dot,
                "pressure_bnd_pct": raw_bnd,
                "pressure_avg": eff_avg,
                "chase_p_balls": b["chase_p_bf"],
                "chase_p_sr": b["chase_p_sr"],
                "inn1_p_balls": b["inn1_p_bf"],
                "inn1_p_sr": b["inn1_p_sr"],
                "ipl_p_balls": b["ipl_p_bf"],
                "ipl_p_sr": b["ipl_p_sr"],
                "matches_played": b["matches_played"],
                "teams_represented": b["teams_represented"],
                "competitions_played": b["competitions_played"],
                "main_strengths": "; ".join(strengths) if strengths else "Balanced pressure metrics",
                "main_limitations": "; ".join(limitations) if limitations else "No critical statistical weaknesses",
                "tactical_role_fit": "Death Finisher" if b["player_role"] in ["All-Rounder", "Specialist Batter"] and eff_avg >= 30 else "Middle-Order Anchor / Accelerator",
                "verification_required": "Confirm external auction pool availability and official BCCI retained player status",
            }
            scored.append(record)

        scored.sort(key=lambda x: x["pressure_score"], reverse=True)
        for i, p in enumerate(scored, 1):
            p["rank"] = i
        return scored

    def score_all_bowlers(
        self,
        min_balls: int = 60,
        competition_scope: str = "ipl",
        half_reliability_n: float = 45.0,
    ) -> list[dict[str, Any]]:
        """Score all eligible bowlers using multi-criteria pressure reliability formulation.

        Args:
            min_balls: Minimum pressure legal balls bowled threshold.
            competition_scope: 'ipl' for primary IPL-only, or 'all' for broader T20.
            half_reliability_n: Empirical Bayes shrinkage constant n_0 (default 45.0).

        Returns:
            Sorted list of scored bowler dictionaries.
        """
        raw_bowlers = self.evaluator.evaluate_bowlers(min_pressure_balls=1)
        priors = self.ipl_priors if competition_scope == "ipl" else self.overall_priors

        econ_shrik = EmpiricalBayesShrinkage(priors["bowl_econ"], self.std_devs["bowl_econ"], half_reliability_n=half_reliability_n)
        wkt_shrik = EmpiricalBayesShrinkage(priors["wkt_pct"], self.std_devs["wkt_rate"], half_reliability_n=half_reliability_n)
        dot_shrik = EmpiricalBayesShrinkage(priors["bowl_dot_pct"], self.std_devs["bowl_dot_pct"], half_reliability_n=half_reliability_n)

        scored: list[dict[str, Any]] = []

        for b in raw_bowlers:
            if competition_scope == "ipl":
                n = b["ipl_p_balls"]
                raw_econ = b["ipl_p_econ"]
                raw_runs = b["ipl_p_runs"]
                raw_wkts = b["ipl_p_wkts"]
                raw_wkt_pct = b["ipl_p_wkt_pct"]
                raw_dot = b["ipl_p_dot_pct"]
                raw_bnd = b["ipl_p_bnd_pct"]
                raw_clutch = b["ipl_clutch_econ_delta"] or 0.0
                baseline_econ = b["ipl_overall_econ"]
                total_balls = b["ipl_overall_balls"]
                death_balls = b["ipl_death_p_balls"]
                death_econ = b["ipl_death_p_econ"]
            else:
                n = b["pressure_balls"]
                raw_econ = b["pressure_econ"]
                raw_runs = b["pressure_runs"]
                raw_wkts = b["pressure_wkts"]
                raw_wkt_pct = b["pressure_wkt_pct"]
                raw_dot = b["pressure_dot_pct"]
                raw_bnd = b["pressure_bnd_pct"]
                raw_clutch = b["clutch_econ_delta"] or 0.0
                baseline_econ = b["overall_econ"]
                total_balls = b["overall_balls"]
                death_balls = b["death_p_balls"]
                death_econ = b["death_p_econ"]

            if n < min_balls:
                continue

            # Empirical Bayes Shrinkage
            econ_res = econ_shrik.shrink(raw_econ, n)
            wkt_res = wkt_shrik.shrink(raw_wkt_pct, n)
            dot_res = dot_shrik.shrink(raw_dot, n)

            # Standardized Z-Scores (lower economy is superior)
            z_econ = (priors["bowl_econ"] - econ_res.shrunk_value) / self.std_devs["bowl_econ"]
            z_wkt = (wkt_res.shrunk_value - priors["wkt_pct"]) / self.std_devs["wkt_rate"]
            z_dot = (dot_res.shrunk_value - priors["bowl_dot_pct"]) / self.std_devs["bowl_dot_pct"]
            z_clutch = max(-2.5, min(2.5, raw_clutch / 1.50))

            # Non-redundant composite weights (no arbitrary death bonus; sum = 1.00)
            comp_metric = (
                0.40 * z_econ +
                0.25 * z_wkt +
                0.20 * z_dot +
                0.15 * z_clutch
            )

            # Final Score: Centered at 50.0, scaled with Bayesian reliability factor
            final_score = round(50.0 + 12.0 * comp_metric * math.sqrt(econ_res.reliability_factor), 2)
            final_score = max(0.0, min(100.0, final_score))

            strengths = []
            if raw_econ <= 7.00:
                strengths.append(f"Elite economy suppression ({raw_econ:.2f})")
            elif raw_econ <= 8.00:
                strengths.append(f"Strong economy control ({raw_econ:.2f})")
            if raw_clutch >= 1.00:
                strengths.append(f"Clutch tightening (+{raw_clutch:.2f} tighter than baseline)")
            if raw_dot >= 40.0:
                strengths.append(f"Elite dot ball generation ({raw_dot:.1f}%)")
            if raw_wkts >= 20:
                strengths.append(f"High pressure wicket volume ({raw_wkts} wkts)")
            if death_balls >= 60:
                strengths.append(f"Proven death-overs volume ({death_balls} balls)")

            limitations = []
            if raw_econ >= 9.20:
                limitations.append(f"Elevated economy under pressure ({raw_econ:.2f})")
            if raw_dot < 32.0:
                limitations.append(f"Lower dot generation ({raw_dot:.1f}%)")
            if n < 90:
                limitations.append(f"Moderate sample volume ({n} pressure balls)")
            if competition_scope != "ipl" and b["ipl_p_balls"] < 40:
                limitations.append(f"Limited IPL exposure ({b['ipl_p_balls']} IPL balls)")

            record = {
                "player_id": b["player_id"],
                "canonical_player_id": b["player_id"],
                "player_name": b["full_player_name"],
                "player_role": b["player_role"],
                "bowling_style": b["bowling_style"],
                "pressure_score": final_score,
                "confidence_tier": econ_res.confidence_tier,
                "reliability_factor": econ_res.reliability_factor,
                "pressure_legal_balls": n,
                "total_legal_balls": total_balls,
                "pressure_runs_conceded": raw_runs,
                "pressure_econ": raw_econ,
                "shrunk_pressure_econ": econ_res.shrunk_value,
                "ci_lower_90_econ": econ_res.ci_lower_90,
                "ci_upper_90_econ": econ_res.ci_upper_90,
                "overall_econ": baseline_econ,
                "clutch_econ_delta": raw_clutch,
                "pressure_wkts": raw_wkts,
                "pressure_dot_pct": raw_dot,
                "pressure_bnd_pct": raw_bnd,
                "pressure_wkt_pct": raw_wkt_pct,
                "death_p_balls": death_balls,
                "death_p_econ": death_econ,
                "ipl_p_balls": b["ipl_p_balls"],
                "ipl_p_econ": b["ipl_p_econ"],
                "matches_played": b["matches_played"],
                "teams_represented": b["teams_represented"],
                "competitions_played": b["competitions_played"],
                "main_strengths": "; ".join(strengths) if strengths else "Balanced pressure bowling",
                "main_limitations": "; ".join(limitations) if limitations else "No critical statistical weaknesses",
                "tactical_role_fit": "Death Specialist" if death_balls >= 50 else ("Middle-Overs Choke" if b["bowling_style"] == "Spin" else "Enforcer Pace"),
                "verification_required": "Confirm external auction pool availability and official BCCI retained player status",
            }
            scored.append(record)

        scored.sort(key=lambda x: x["pressure_score"], reverse=True)
        for i, p in enumerate(scored, 1):
            p["rank"] = i
        return scored

    def run_sensitivity_analysis(self) -> list[dict[str, Any]]:
        """Run hyperparameter sensitivity analysis across 7 distinct scenarios."""
        scenarios = [
            ("ipl_baseline", 60, "ipl", 45.0),
            ("ipl_strict_sample_90", 90, "ipl", 45.0),
            ("ipl_lenient_sample_45", 45, "ipl", 45.0),
            ("ipl_high_shrinkage_60", 60, "ipl", 60.0),
            ("ipl_low_shrinkage_30", 60, "ipl", 30.0),
            ("all_t20_baseline", 60, "all", 45.0),
            ("all_t20_strict_sample_90", 90, "all", 45.0),
        ]

        results = []
        for name, min_b, scope, n0 in scenarios:
            bats = self.score_all_batters(min_balls=min_b, competition_scope=scope, half_reliability_n=n0)
            bowls = self.score_all_bowlers(min_balls=min_b, competition_scope=scope, half_reliability_n=n0)

            top_bats = [f"{b['rank']}. {b['player_name']} ({b['pressure_score']:.1f})" for b in bats[:5]]
            top_bowls = [f"{b['rank']}. {b['player_name']} ({b['pressure_score']:.1f})" for b in bowls[:5]]

            results.append({
                "scenario": name,
                "min_balls": min_b,
                "competition_scope": scope,
                "shrinkage_n0": n0,
                "qualified_batters": len(bats),
                "qualified_bowlers": len(bowls),
                "top_5_batters": "; ".join(top_bats),
                "top_5_bowlers": "; ".join(top_bowls),
            })
        return results

    def export_all_artifacts(self, out_dir: Path | None = None) -> dict[str, str]:
        """Generate and export all verified analytics artifacts into artifacts/analytics/."""
        out = out_dir or (ARTIFACTS_DIR / "analytics")
        out.mkdir(parents=True, exist_ok=True)

        # 1. Primary Evaluations (IPL-Only, min 60 balls)
        batters_ipl = self.score_all_batters(min_balls=60, competition_scope="ipl")
        bowlers_ipl = self.score_all_bowlers(min_balls=60, competition_scope="ipl")

        # 2. Supplementary Evaluations (All-T20, min 60 balls)
        batters_all = self.score_all_batters(min_balls=60, competition_scope="all")
        bowlers_all = self.score_all_bowlers(min_balls=60, competition_scope="all")

        # Helper to export CSV
        def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
            if not rows:
                return
            headers = list(rows[0].keys())
            with path.open("w", newline="", encoding="utf-8") as f:
                import csv
                writer = csv.DictWriter(f, fieldnames=headers)
                writer.writeheader()
                writer.writerows(rows)

        # Primary deliverables (defaults to IPL-only as required for IPL Auction Strategy)
        write_csv(out / "top_10_batters.csv", batters_ipl[:10])
        write_csv(out / "top_10_bowlers.csv", bowlers_ipl[:10])
        write_csv(out / "top_10_batters_ipl.csv", batters_ipl[:10])
        write_csv(out / "top_10_bowlers_ipl.csv", bowlers_ipl[:10])

        # Supplementary broader T20 leaderboards
        write_csv(out / "top_10_batters_all_t20.csv", batters_all[:10])
        write_csv(out / "top_10_bowlers_all_t20.csv", bowlers_all[:10])

        # Full qualified populations
        write_csv(out / "all_batter_scores.csv", batters_ipl)
        write_csv(out / "all_bowler_scores.csv", bowlers_ipl)
        write_csv(out / "all_batter_scores_all_t20.csv", batters_all)
        write_csv(out / "all_bowler_scores_all_t20.csv", bowlers_all)

        # Combined player pressure metrics
        combined_metrics = []
        for b in batters_ipl:
            combined_metrics.append({
                "player_id": b["player_id"],
                "player_name": b["player_name"],
                "discipline": "Batting",
                "role": b["player_role"],
                "rank": b["rank"],
                "pressure_score": b["pressure_score"],
                "confidence_tier": b["confidence_tier"],
                "pressure_deliveries": b["pressure_balls_faced"],
                "primary_metric": b["pressure_sr"],
                "baseline_metric": b["overall_sr"],
                "clutch_delta": b["clutch_sr_delta"],
                "teams": b["teams_represented"],
                "competition_scope": "IPL Primary",
            })
        for b in bowlers_ipl:
            combined_metrics.append({
                "player_id": b["player_id"],
                "player_name": b["player_name"],
                "discipline": "Bowling",
                "role": b["player_role"],
                "rank": b["rank"],
                "pressure_score": b["pressure_score"],
                "confidence_tier": b["confidence_tier"],
                "pressure_deliveries": b["pressure_legal_balls"],
                "primary_metric": b["pressure_econ"],
                "baseline_metric": b["overall_econ"],
                "clutch_delta": b["clutch_econ_delta"],
                "teams": b["teams_represented"],
                "competition_scope": "IPL Primary",
            })
        write_csv(out / "player_pressure_metrics.csv", combined_metrics)

        # Sensitivity Analysis CSV
        sensitivity_results = self.run_sensitivity_analysis()
        write_csv(out / "ranking_sensitivity.csv", sensitivity_results)

        # Model Validation JSON
        validation_data = {
            "model_metadata": {
                "model_name": "RR ScoutIQ Audited Bayesian Pressure Architecture",
                "version": "2.1.0",
                "calibration_date": "2026-11-15",
                "total_deliveries_scored": 200896,
                "unrecorded_dls_excluded_deliveries": 103,
                "half_reliability_n0": 45.0,
                "primary_scope": "IPL Only",
                "supplementary_scope": "All T20",
            },
            "population_parameters": {
                "ipl_high_pressure_batting_sr": self.ipl_priors["bat_sr"],
                "ipl_high_pressure_bowling_econ": self.ipl_priors["bowl_econ"],
                "ipl_high_pressure_wicket_pct": self.ipl_priors["wkt_pct"],
                "all_high_pressure_batting_sr": self.overall_priors["bat_sr"],
                "all_high_pressure_bowling_econ": self.overall_priors["bowl_econ"],
            },
            "top_10_batters_ipl_summary": [
                {"rank": b["rank"], "name": b["player_name"], "score": b["pressure_score"], "pressure_sr": b["pressure_sr"], "balls": b["pressure_balls_faced"]}
                for b in batters_ipl[:10]
            ],
            "top_10_bowlers_ipl_summary": [
                {"rank": b["rank"], "name": b["player_name"], "score": b["pressure_score"], "pressure_econ": b["pressure_econ"], "balls": b["pressure_legal_balls"], "wkts": b["pressure_wkts"]}
                for b in bowlers_ipl[:10]
            ],
            "stability_metrics": {
                "rank_1_ipl_batter": batters_ipl[0]["player_name"],
                "rank_1_ipl_bowler": bowlers_ipl[0]["player_name"],
                "scenarios_tested": len(sensitivity_results),
            }
        }
        with (out / "model_validation.json").open("w", encoding="utf-8") as f:
            json.dump(validation_data, f, indent=2)

        return {
            "top_10_batters": str(out / "top_10_batters.csv"),
            "top_10_bowlers": str(out / "top_10_bowlers.csv"),
            "top_10_batters_ipl": str(out / "top_10_batters_ipl.csv"),
            "top_10_bowlers_ipl": str(out / "top_10_bowlers_ipl.csv"),
            "all_batter_scores": str(out / "all_batter_scores.csv"),
            "all_bowler_scores": str(out / "all_bowler_scores.csv"),
            "player_pressure_metrics": str(out / "player_pressure_metrics.csv"),
            "ranking_sensitivity": str(out / "ranking_sensitivity.csv"),
            "model_validation": str(out / "model_validation.json"),
        }


if __name__ == "__main__":
    print("Executing RR ScoutIQ Full Audited Ranking Pipeline...")
    engine = RankingEngine()
    artifacts = engine.export_all_artifacts()
    print("\n=== Analytics Artifacts Generated Successfully ===")
    for k, v in artifacts.items():
        print(f"  - {k}: {v}")

    # Print Top 10 Batters (Primary IPL)
    print("\n=== PRIMARY: TOP 10 IPL BATTERS UNDER PRESSURE ===")
    top_batters = engine.score_all_batters(min_balls=60, competition_scope="ipl")[:10]
    for b in top_batters:
        print(f"#{b['rank']:2d} | {b['player_name']:<22} | Score: {b['pressure_score']:5.2f} | Balls: {b['pressure_balls_faced']:3d} | Runs: {b['pressure_runs']:3d} | SR: {b['pressure_sr']:6.2f} | Base-SR: {b['overall_sr']:6.2f} | Delta: {b['clutch_sr_delta']:+6.2f}")

    # Print Top 10 Bowlers (Primary IPL)
    print("\n=== PRIMARY: TOP 10 IPL BOWLERS UNDER PRESSURE ===")
    top_bowlers = engine.score_all_bowlers(min_balls=60, competition_scope="ipl")[:10]
    for b in top_bowlers:
        print(f"#{b['rank']:2d} | {b['player_name']:<22} | Score: {b['pressure_score']:5.2f} | Balls: {b['pressure_legal_balls']:3d} | Wkts: {b['pressure_wkts']:2d} | Econ: {b['pressure_econ']:5.2f} | Base-Econ: {b['overall_econ']:5.2f} | Delta: {b['clutch_econ_delta']:+5.2f}")
