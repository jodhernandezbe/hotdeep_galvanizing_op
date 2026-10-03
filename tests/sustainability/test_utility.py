"""Tests for the utility calculations."""

import numpy as np
import pytest

from src.process.simulation import simulate_year
from src.sustainability.thesis_weights import (
    CATEGORY_WEIGHTS,
    EFFICIENCY_WEIGHTS,
    ENVIRONMENT_WEIGHTS,
    thesis_indicator_weights,
)
from src.sustainability.utility import _process_utility, build_indicator_weights, evaluate_year


def test_thesis_tables_are_normalised() -> None:
    assert CATEGORY_WEIGHTS.sum() == pytest.approx(1.0, abs=1e-4)
    assert ENVIRONMENT_WEIGHTS.sum() == pytest.approx(1.0, abs=1e-4)
    assert EFFICIENCY_WEIGHTS.sum() == pytest.approx(1.0, abs=1e-4)


def test_indicator_weights_layout_and_normalisation() -> None:
    weights = thesis_indicator_weights()
    assert weights.shape == (18,)
    assert weights.sum() == pytest.approx(1.0, abs=1e-4)
    assert weights[0] == pytest.approx(0.1433 * 0.1760)
    assert weights[11] == pytest.approx(0.1770 * 0.8116)
    assert weights[15] == pytest.approx(0.1163) and weights[16] == pytest.approx(0.25) and weights[17] == pytest.approx(0.3134)


def test_indicator_weights_reject_wrong_lengths() -> None:
    with pytest.raises(ValueError, match="environment_weights"):
        build_indicator_weights(np.ones(5), np.ones(10), np.ones(4))


def test_process_utility_formula() -> None:
    weights = np.zeros(18)
    weights[17] = 0.5
    unit_utility = np.full(7, 10.0)
    expected = 60.0 * 90.0 + 60.0 * 70.0 / (7 * 0.5)
    assert _process_utility(unit_utility, 90.0, 60.0, weights) == pytest.approx(expected)


def test_evaluate_year_outputs_are_consistent() -> None:
    weights = thesis_indicator_weights()
    evaluation = evaluate_year(simulate_year(5000, np.random.default_rng(0)), weights)
    assert evaluation.unit_scores.shape == (7, 17) and evaluation.process_scores.shape == (18,)
    np.testing.assert_allclose(evaluation.unit_utility, evaluation.unit_scores @ weights[:17])
    assert 90 < evaluation.quality_utility_pct <= 100
    assert evaluation.process_scores[17] == evaluation.quality_utility_pct
    assert 35 <= evaluation.mean_standard_thickness_um <= 70
    assert np.isfinite(evaluation.process_utility)
