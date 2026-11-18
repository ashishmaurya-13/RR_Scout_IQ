"""
RR ScoutIQ — Bayesian Reliability & Small-Sample Shrinkage Model
Implements Empirical Bayes shrinkage for batting strike rate, bowling economy,
dot-ball rates, and wicket rates to prevent small-sample distortions.
"""

from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class ShrinkageResult:
    """Posterior estimate and credibility intervals following empirical Bayes shrinkage."""
    observed_value: float
    shrunk_value: float
    prior_mean: float
    sample_size: int
    reliability_factor: float
    posterior_se: float
    ci_lower_90: float
    ci_upper_90: float
    confidence_tier: Literal["High Confidence", "Moderate Confidence", "Low Confidence"]


class EmpiricalBayesShrinkage:
    """Shrinks noisy player-level sample metrics toward empirical population priors."""

    def __init__(
        self,
        prior_mean: float,
        prior_std: float,
        half_reliability_n: float = 45.0,
    ):
        """Initialize shrinkage model.

        Args:
            prior_mean: Population baseline mean (mu_0).
            prior_std: Population between-player standard deviation (sigma_0).
            half_reliability_n: Pseudo-count n_0 where shrinkage weight lambda = 0.50.
        """
        self.prior_mean = prior_mean
        self.prior_std = prior_std
        self.n_0 = half_reliability_n

    def shrink(self, observed_val: float, sample_size: int) -> ShrinkageResult:
        """Apply empirical Bayes shrinkage to observed metric based on sample size.

        Args:
            observed_val: Observed raw player metric (e.g. pressure strike rate).
            sample_size: Number of relevant deliveries (balls faced or legal balls bowled).

        Returns:
            ShrinkageResult containing posterior estimate and credibility bounds.
        """
        if sample_size <= 0:
            return ShrinkageResult(
                observed_value=observed_val,
                shrunk_value=self.prior_mean,
                prior_mean=self.prior_mean,
                sample_size=0,
                reliability_factor=0.0,
                posterior_se=self.prior_std,
                ci_lower_90=round(self.prior_mean - 1.645 * self.prior_std, 2),
                ci_upper_90=round(self.prior_mean + 1.645 * self.prior_std, 2),
                confidence_tier="Low Confidence",
            )

        # Reliability factor lambda in [0, 1]
        lam = sample_size / (sample_size + self.n_0)

        # Posterior mean: weighted combination of observed data and prior mean
        shrunk = lam * observed_val + (1.0 - lam) * self.prior_mean

        # Posterior standard error decreases as sample size grows
        # Var(theta | y) approx = (1 - lambda) * sigma_0^2
        post_variance = max(0.01, (1.0 - lam) * (self.prior_std ** 2) + (self.prior_std ** 2) / (sample_size + self.n_0))
        post_se = math.sqrt(post_variance)

        # 90% Credible Interval (Z = 1.645)
        ci_lower = round(shrunk - 1.645 * post_se, 2)
        ci_upper = round(shrunk + 1.645 * post_se, 2)

        if sample_size >= 90:
            tier = "High Confidence"
        elif sample_size >= 45:
            tier = "Moderate Confidence"
        else:
            tier = "Low Confidence"

        return ShrinkageResult(
            observed_value=round(observed_val, 2),
            shrunk_value=round(shrunk, 2),
            prior_mean=round(self.prior_mean, 2),
            sample_size=sample_size,
            reliability_factor=round(lam, 4),
            posterior_se=round(post_se, 2),
            ci_lower_90=ci_lower,
            ci_upper_90=ci_upper,
            confidence_tier=tier,
        )


def evaluate_sample_reliability(
    sample_size: int,
    min_qualification: int = 45,
    high_confidence_thresh: int = 90,
) -> tuple[float, str]:
    """Calculate normalized sample reliability weight and classification string."""
    rel = sample_size / (sample_size + min_qualification)
    if sample_size >= high_confidence_thresh:
        label = "High Confidence"
    elif sample_size >= min_qualification:
        label = "Moderate Confidence"
    else:
        label = "Low Confidence"
    return round(rel, 4), label
