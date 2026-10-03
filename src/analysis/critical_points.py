"""Critical-point selection and sustainability probability of the process.

Purpose: Pareto selection of the critical unit processes and normal-approximation sustainability probability (annex D.1).
Author: Jose D. Hernandez-Betancur
Date: 2026-10-02
"""

from dataclasses import dataclass
from typing import Final

import numpy as np
from scipy.stats import norm, t

CRITICAL_CUMULATIVE_PCT: Final = 80.0
ADMISSIBLE_FRACTION: Final = 0.8
SIGMA_COVERAGE: Final = 3.0
CONFIDENCE_LEVEL: Final = 0.95
PERCENT: Final = 100.0


@dataclass(frozen=True)
class SustainabilityAssessment:
    """Probability that the process utility lies in the admissible band.

    Attributes:
        probability: P(admissible utility <= U_P <= maximum utility).
        utility_max: Maximum attainable utility.
        utility_admissible: Lowest admissible utility.
        utility_std: Standard deviation assumed for the utility.
        mean_ci_lower: Lower bound of the confidence interval of the mean utility.
        mean_ci_upper: Upper bound of the confidence interval of the mean utility.
    """

    probability: float
    utility_max: float
    utility_admissible: float
    utility_std: float
    mean_ci_lower: float
    mean_ci_upper: float


def select_critical_units(independent_pct: np.ndarray, cumulative_pct: float = CRITICAL_CUMULATIVE_PCT) -> np.ndarray:
    """Select the units that jointly explain the given share of the independent effects.

    Args:
        independent_pct: Independent effect of each unit [%], summing to 100.
        cumulative_pct: Cumulative share to reach [%].

    Returns:
        Indices (0-based) of the selected units, most influential first.
    """
    order = np.argsort(-np.asarray(independent_pct), kind="stable")
    cumulative = np.cumsum(np.asarray(independent_pct)[order])
    n_selected = int(np.searchsorted(cumulative, cumulative_pct, side="left")) + 1
    return order[: min(n_selected, order.size)]


def assess_sustainability(
    process_utility: np.ndarray,
    mean_standard_thickness_um: np.ndarray,
    quality_weight: float,
) -> SustainabilityAssessment:
    """Estimate the probability of being sustainable from the simulated process utilities.

    Args:
        process_utility: Process utility of each simulated year.
        mean_standard_thickness_um: Mean standard coating thickness of each simulated year [um].
        quality_weight: Relative weight of the quality category.

    Returns:
        Probability and confidence interval of the mean utility.
    """
    utility_max = float(np.mean(mean_standard_thickness_um)) * PERCENT / quality_weight
    utility_mean = float(np.mean(process_utility))
    std = (utility_max - utility_mean) / SIGMA_COVERAGE
    admissible = ADMISSIBLE_FRACTION * utility_max
    probability = norm.cdf(utility_max, utility_mean, std) - norm.cdf(admissible, utility_mean, std)
    half_width = float(t.ppf(1 - (1 - CONFIDENCE_LEVEL) / 2, process_utility.size - 1)) * std / np.sqrt(process_utility.size)
    return SustainabilityAssessment(
        probability=float(probability),
        utility_max=utility_max,
        utility_admissible=admissible,
        utility_std=std,
        mean_ci_lower=utility_mean - half_width,
        mean_ci_upper=utility_mean + half_width,
    )
