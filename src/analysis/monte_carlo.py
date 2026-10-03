"""Monte Carlo sampling of the sustainability of the hot-dip galvanizing process.

Purpose: repeat the yearly simulation and evaluation to propagate input uncertainty (thesis annex D.1).
Author: Jose D. Hernandez-Betancur
Date: 2026-10-02
"""

import logging
from dataclasses import dataclass
from typing import Final

import numpy as np

from src.analysis.critical_points import (
    SustainabilityAssessment,
    assess_sustainability,
    select_critical_units,
)
from src.analysis.hierarchical_partitioning import (
    HierarchicalPartitioningResult,
    hierarchical_partitioning,
)
from src.process.simulation import simulate_year
from src.sustainability.streams import N_INDICATORS, N_UNIT_PROCESSES
from src.sustainability.utility import YearEvaluation, evaluate_year

logger = logging.getLogger(__name__)

DEFAULT_ANNUAL_ITEMS: Final = 41379264
DEFAULT_SAMPLES: Final = 100


@dataclass(frozen=True)
class MonteCarloResult:
    """Stacked evaluations of the simulated years.

    Attributes:
        unit_utility: Unit-process utilities, shape (n, 7).
        quality_utility_pct: Quality utility [%], shape (n,).
        mean_standard_thickness_um: Mean standard thickness [um], shape (n,).
        process_utility: Global process utility, shape (n,).
        process_scores: Mean indicator scores plus quality, shape (n, 18).
        unit_scores: Indicator scores per unit process, shape (n, 7, 17).
    """

    unit_utility: np.ndarray
    quality_utility_pct: np.ndarray
    mean_standard_thickness_um: np.ndarray
    process_utility: np.ndarray
    process_scores: np.ndarray
    unit_scores: np.ndarray


@dataclass(frozen=True)
class CriticalPointAnalysis:
    """Critical unit processes and sustainability probability of a Monte Carlo run.

    Attributes:
        partitioning: Hierarchical partitioning of the process utility over the unit-process utilities.
        critical_units: Indices (0-based) of the units explaining 80 % of the independent effect.
        assessment: Probability of being sustainable.
    """

    partitioning: HierarchicalPartitioningResult
    critical_units: np.ndarray
    assessment: SustainabilityAssessment


def run_monte_carlo(
    weights: np.ndarray,
    rng: np.random.Generator,
    n_samples: int = DEFAULT_SAMPLES,
    items: int = DEFAULT_ANNUAL_ITEMS,
    preserve_thesis_quirks: bool = True,
) -> MonteCarloResult:
    """Simulate and evaluate several years of production.

    Args:
        weights: Indicator weights, length 18 (see `build_indicator_weights`).
        rng: Random number generator.
        n_samples: Number of simulated years.
        items: Pieces processed per year.
        preserve_thesis_quirks: Reproduce the thesis listing's behaviour (see `simulate_year` and `compute_greenscope`).

    Returns:
        Stacked evaluations.
    """
    evaluations = []
    for sample in range(n_samples):
        logger.info("Sample %d of %d", sample + 1, n_samples)
        year = simulate_year(items, rng, preserve_thesis_quirks)
        evaluations.append(evaluate_year(year, weights, preserve_thesis_quirks))
    return _stack(evaluations)


def analyze_critical_points(result: MonteCarloResult, quality_weight: float) -> CriticalPointAnalysis:
    """Find the critical unit processes and the probability that the process is sustainable.

    Args:
        result: Monte Carlo evaluations.
        quality_weight: Relative weight of the quality category.

    Returns:
        Critical-point analysis.
    """
    partitioning = hierarchical_partitioning(result.process_utility, result.unit_utility)
    return CriticalPointAnalysis(
        partitioning=partitioning,
        critical_units=select_critical_units(partitioning.independent_pct),
        assessment=assess_sustainability(result.process_utility, result.mean_standard_thickness_um, quality_weight),
    )


def _stack(evaluations: list[YearEvaluation]) -> MonteCarloResult:
    return MonteCarloResult(
        unit_utility=np.array([e.unit_utility for e in evaluations]).reshape(-1, N_UNIT_PROCESSES),
        quality_utility_pct=np.array([e.quality_utility_pct for e in evaluations]),
        mean_standard_thickness_um=np.array([e.mean_standard_thickness_um for e in evaluations]),
        process_utility=np.array([e.process_utility for e in evaluations]),
        process_scores=np.array([e.process_scores for e in evaluations]).reshape(-1, N_INDICATORS + 1),
        unit_scores=np.array([e.unit_scores for e in evaluations]).reshape(-1, N_UNIT_PROCESSES, N_INDICATORS),
    )
