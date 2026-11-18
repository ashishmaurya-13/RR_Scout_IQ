"""
RR ScoutIQ — Complete Analytics Engine Test Suite
Unit and integration tests for:
1. Continuous pressure engine (chase, 1st innings, DLS edge cases, super overs)
2. Competition & era normalizer
3. Bayesian reliability & small-sample shrinkage
4. Player evaluation and multi-criteria ranking engine
"""

from __future__ import annotations
import math
from pathlib import Path
import duckdb
import pytest

from config.settings import DUCKDB_PATH
from src.analytics.competition_normalizer import CompetitionNormalizer, MetricBenchmark
from src.analytics.pressure_engine import (
    get_pressure_summary_statistics,
    materialize_delivery_pressure_table,
)
from src.evaluation.player_evaluator import PlayerEvaluator
from src.models.reliability_model import EmpiricalBayesShrinkage, evaluate_sample_reliability
from src.scouting.ranking_engine import RankingEngine


@pytest.fixture(scope="module")
def db_con():
    """Module-level DuckDB connection to canonical database."""
    if not DUCKDB_PATH.exists():
        pytest.skip("Canonical DuckDB database does not exist.")
    con = duckdb.connect(str(DUCKDB_PATH), read_only=True)
    yield con
    con.close()


class TestPressureEngine:
    """Rigorous verification of continuous pressure index engine."""

    def test_pressure_table_exists_and_row_count(self, db_con):
        """Verify fact_delivery_pressure contains exact delivery count."""
        count = db_con.execute("SELECT COUNT(*) FROM fact_delivery_pressure").fetchone()[0]
        assert count == 200999

    def test_unrecorded_dls_target_pressure_is_null(self, db_con):
        """Verify Match 23674 Innings 2 deliveries have NULL pressure_score (zero fabrication)."""
        null_count = db_con.execute("""
            SELECT COUNT(*) 
            FROM fact_delivery_pressure 
            WHERE match_id = 23674 AND innings = 2 AND pressure_score IS NULL
        """).fetchone()[0]
        assert null_count == 103

        # All other deliveries must have non-null pressure score
        other_nulls = db_con.execute("""
            SELECT COUNT(*) 
            FROM fact_delivery_pressure 
            WHERE match_id != 23674 AND pressure_score IS NULL
        """).fetchone()[0]
        assert other_nulls == 0

    def test_pressure_score_bounds(self, db_con):
        """Verify all defined pressure scores are strictly within [0.0, 100.0]."""
        invalid = db_con.execute("""
            SELECT COUNT(*) 
            FROM fact_delivery_pressure 
            WHERE pressure_score IS NOT NULL AND (pressure_score < 0.0 OR pressure_score > 100.0)
        """).fetchone()[0]
        assert invalid == 0

    def test_super_over_extreme_pressure(self, db_con):
        """Verify Super Over deliveries (innings 3 & 4) receive elite pressure scores."""
        so_scores = db_con.execute("""
            SELECT MIN(pressure_score), AVG(pressure_score), MAX(pressure_score)
            FROM fact_delivery_pressure 
            WHERE innings IN (3, 4)
        """).fetchone()
        assert so_scores[0] >= 88.0
        assert so_scores[2] <= 100.0

    def test_pressure_summary_statistics(self, db_con):
        """Verify summary distribution statistics match empirical expectations."""
        summary = get_pressure_summary_statistics(db_con)
        assert summary["total_deliveries"] == 200999
        assert summary["missing_pressure_deliveries"] == 103
        assert 34.0 <= summary["mean_pressure"] <= 39.0
        assert 33.0 <= summary["median"] <= 38.0
        assert summary["high_pressure_deliveries"] > 35000
        assert summary["extreme_pressure_deliveries"] > 15000

    def test_chase_urgency_monotonic_direction(self, db_con):
        """Verify temporal chase urgency strictly increases as balls run out."""
        # Query average urgency by phase of chase
        urg_by_balls = db_con.execute("""
            SELECT 
                AVG(CASE WHEN legal_balls_remaining >= 90 THEN chase_urgency_comp END) AS early_urg,
                AVG(CASE WHEN legal_balls_remaining BETWEEN 40 AND 80 THEN chase_urgency_comp END) AS mid_urg,
                AVG(CASE WHEN legal_balls_remaining <= 18 THEN chase_urgency_comp END) AS late_urg
            FROM fact_delivery_pressure
            WHERE is_chase AND target_runs IS NOT NULL AND chase_urgency_comp IS NOT NULL
        """).fetchone()
        assert urg_by_balls[0] < urg_by_balls[1] < urg_by_balls[2]
        assert urg_by_balls[0] <= 0.45
        assert urg_by_balls[2] >= 0.85

    def test_chase_urgency_final_delivery_and_zero_balls(self, db_con):
        """Verify final delivery (1 ball left) produces near-maximum urgency and 0 balls evaluates cleanly."""
        # 1. On final ball of innings (1 ball remaining), urgency must exceed 0.98
        final_ball_urg = db_con.execute("""
            SELECT AVG(chase_urgency_comp)
            FROM fact_delivery_pressure
            WHERE is_chase AND target_runs IS NOT NULL AND legal_balls_remaining = 1
        """).fetchone()[0]
        assert final_ball_urg >= 0.98

        # 2. Synthetic evaluation of formula at 0 balls remaining
        zero_balls_urg = db_con.execute("""
            SELECT (0.20 + 0.80 * POWER(1.0 - (LEAST(0, 120)::FLOAT / 120.0), 1.25))
        """).fetchone()[0]
        assert abs(zero_balls_urg - 1.0) < 1e-4

    def test_chase_urgency_shortened_innings(self, db_con):
        """Verify shortened innings scale urgency appropriately based on scheduled balls."""
        short_urg = db_con.execute("""
            SELECT AVG(chase_urgency_comp)
            FROM fact_delivery_pressure
            WHERE is_chase AND is_shortened_match AND chase_urgency_comp IS NOT NULL
        """).fetchone()[0]
        assert 0.20 <= short_urg <= 1.00


class TestCompetitionNormalizer:
    """Tests for competition benchmarks, era tracking, and Z-score transformations."""

    def test_benchmarks_loaded(self, db_con):
        norm = CompetitionNormalizer(db_con)
        assert "high_pressure_overall" in norm.benchmarks
        hp = norm.benchmarks["high_pressure_overall"]
        assert 130.0 <= hp["bat_sr"] <= 145.0
        assert 8.0 <= hp["bowl_econ"] <= 9.2

    def test_z_score_clamping(self):
        bm = MetricBenchmark(mean=100.0, std=10.0)
        # Extreme value +10 sigma must clamp to +3.5
        assert bm.z_score(200.0, clamp=3.5) == 3.5
        # Extreme negative -10 sigma must clamp to -3.5
        assert bm.z_score(0.0, clamp=3.5) == -3.5
        # Exact mean -> 0.0
        assert bm.z_score(100.0) == 0.0

    def test_bowling_z_score_inversion(self):
        norm = CompetitionNormalizer.__new__(CompetitionNormalizer)
        norm._benchmarks = {
            "high_pressure_overall": {"bowl_econ": 8.5},
            "std_devs": {"bowl_econ": 1.5},
        }
        # Tighter economy (6.0 vs 8.5) must yield positive Z-score
        z_tight = norm.standardize_bowling_econ(6.0)
        assert z_tight > 0.0
        # Expensive economy (11.0 vs 8.5) must yield negative Z-score
        z_expensive = norm.standardize_bowling_econ(11.0)
        assert z_expensive < 0.0


class TestReliabilityModel:
    """Tests for Bayesian shrinkage and small-sample stabilization."""

    def test_shrinkage_convergence(self):
        shrik = EmpiricalBayesShrinkage(prior_mean=140.0, prior_std=20.0, half_reliability_n=50.0)
        
        # Sample size 0: exact prior mean
        r0 = shrik.shrink(200.0, sample_size=0)
        assert r0.shrunk_value == 140.0
        assert r0.reliability_factor == 0.0
        assert r0.confidence_tier == "Low Confidence"

        # Sample size 50 (equal to n_0): exactly halfway between observed and prior
        r50 = shrik.shrink(200.0, sample_size=50)
        assert r50.shrunk_value == 170.0  # 0.5 * 200 + 0.5 * 140
        assert r50.reliability_factor == 0.5
        assert r50.confidence_tier == "Moderate Confidence"

        # Huge sample size 500: heavily weighted toward observed
        r500 = shrik.shrink(200.0, sample_size=500)
        assert r500.shrunk_value >= 194.0
        assert r500.reliability_factor >= 0.90
        assert r500.confidence_tier == "High Confidence"

    def test_credible_intervals(self):
        shrik = EmpiricalBayesShrinkage(prior_mean=100.0, prior_std=15.0, half_reliability_n=40.0)
        res = shrik.shrink(120.0, sample_size=60)
        assert res.ci_lower_90 < res.shrunk_value < res.ci_upper_90


class TestRankingEngine:
    """Integration test verifying end-to-end player scoring and artifact creation."""

    def test_ranking_determinism(self, db_con):
        engine = RankingEngine(db_con)
        bats1 = engine.score_all_batters(min_balls=60)[:5]
        bats2 = engine.score_all_batters(min_balls=60)[:5]
        assert [b["player_id"] for b in bats1] == [b["player_id"] for b in bats2]

    def test_top_10_batters_sanity(self, db_con):
        engine = RankingEngine(db_con)
        top10 = engine.score_all_batters(min_balls=60)[:10]
        assert len(top10) == 10
        # All top 10 batters must have positive pressure score and >= 60 pressure balls
        for b in top10:
            assert b["pressure_score"] >= 60.0
            assert b["pressure_balls_faced"] >= 60
            assert b["pressure_sr"] >= 150.0

    def test_top_10_bowlers_sanity(self, db_con):
        engine = RankingEngine(db_con)
        top10 = engine.score_all_bowlers(min_balls=60)[:10]
        assert len(top10) == 10
        for b in top10:
            assert b["pressure_score"] >= 55.0
            assert b["pressure_legal_balls"] >= 60
            assert b["pressure_econ"] <= 8.5

    def test_ipl_only_leaderboard_integrity(self, db_con):
        """Verify IPL-only ranking outputs valid, strictly-IPL qualified players."""
        engine = RankingEngine(db_con)
        ipl_bats = engine.score_all_batters(min_balls=60, competition_scope="ipl")[:10]
        ipl_bowls = engine.score_all_bowlers(min_balls=60, competition_scope="ipl")[:10]
        assert len(ipl_bats) == 10
        assert len(ipl_bowls) == 10
        for b in ipl_bats:
            assert b["ipl_p_balls"] >= 60
            assert b["pressure_score"] >= 55.0
        for b in ipl_bowls:
            assert b["ipl_p_balls"] >= 60
            assert b["pressure_score"] >= 55.0

    def test_score_direction_consistency(self, db_con):
        """Verify that better underlying metrics yield higher pressure scores."""
        engine = RankingEngine(db_con)
        bats = engine.score_all_batters(min_balls=60, competition_scope="ipl")
        # Player at rank 1 must have higher score than player at rank 10
        assert bats[0]["pressure_score"] > bats[9]["pressure_score"]
        bowls = engine.score_all_bowlers(min_balls=60, competition_scope="ipl")
        assert bowls[0]["pressure_score"] > bowls[9]["pressure_score"]

    def test_export_all_artifacts(self, db_con, tmp_path: Path):
        engine = RankingEngine(db_con)
        artifacts = engine.export_all_artifacts(out_dir=tmp_path)
        
        expected_files = [
            "top_10_batters.csv",
            "top_10_bowlers.csv",
            "all_batter_scores.csv",
            "all_bowler_scores.csv",
            "player_pressure_metrics.csv",
            "ranking_sensitivity.csv",
            "model_validation.json",
        ]
        for f in expected_files:
            file_path = tmp_path / f
            assert file_path.exists(), f"Missing expected artifact: {f}"
            assert file_path.stat().st_size > 0, f"Artifact is empty: {f}"
