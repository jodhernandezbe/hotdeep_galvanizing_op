"""Tests for the Monte Carlo driver."""

import numpy as np

from src.analysis.monte_carlo import analyze_critical_points, run_monte_carlo
from src.sustainability.thesis_weights import thesis_indicator_weights

N_SAMPLES = 12
ITEMS = 3000


def test_run_monte_carlo_stacks_one_evaluation_per_sample() -> None:
    result = run_monte_carlo(thesis_indicator_weights(), np.random.default_rng(0), n_samples=N_SAMPLES, items=ITEMS)
    assert result.unit_utility.shape == (N_SAMPLES, 7)
    assert result.process_utility.shape == (N_SAMPLES,)
    assert result.process_scores.shape == (N_SAMPLES, 18)
    assert result.unit_scores.shape == (N_SAMPLES, 7, 17)


def test_run_monte_carlo_is_reproducible_for_a_seed() -> None:
    weights = thesis_indicator_weights()
    first = run_monte_carlo(weights, np.random.default_rng(3), n_samples=2, items=ITEMS)
    second = run_monte_carlo(weights, np.random.default_rng(3), n_samples=2, items=ITEMS)
    np.testing.assert_array_equal(first.process_utility, second.process_utility)


def test_critical_point_analysis_returns_consistent_pieces() -> None:
    weights = thesis_indicator_weights()
    result = run_monte_carlo(weights, np.random.default_rng(0), n_samples=N_SAMPLES, items=ITEMS)
    analysis = analyze_critical_points(result, quality_weight=weights[17])
    assert abs(analysis.partitioning.independent_pct.sum() - 100.0) < 1e-6
    assert analysis.critical_units.size >= 1
    assert 0.0 <= analysis.assessment.probability <= 1.0
