"""Tests of the weight sensitivity of the fuzzy compromise.

Purpose: spec optimization/mcdm-selection (stability of the selected design under other weights).
Author: Jose D. Hernandez-Betancur
Date: 2026-10-03
"""

import numpy as np
import pytest

from src.optimization.mcdm import select_compromise
from src.optimization.weight_sensitivity import (
    analyze_weights,
    equal_weights,
    indicator_level_weights,
    named_schemes,
    random_sweep,
    selection_for_weights,
)

X = np.array(
    [
        [50.0, 17.0, 900.0, 50.0, 4.5, 400.0, 450.0, 150.0],
        [55.0, 15.0, 800.0, 45.0, 4.2, 350.0, 452.0, 120.0],
        [45.0, 13.0, 700.0, 42.0, 4.8, 450.0, 447.0, 90.0],
    ]
)
F = np.array([[-90.0, 1.0e6, 60.0, 200.0], [-80.0, 0.8e6, 50.0, 180.0], [-70.0, 0.6e6, 40.0, 160.0]])


def test_all_schemes_are_normalized_four_vectors() -> None:
    for weights in named_schemes().values():
        assert weights.shape == (4,)
        assert weights.sum() == pytest.approx(1.0)
        assert np.all(weights > 0)


def test_indicator_level_weights_use_the_thesis_indicator_table() -> None:
    weights = indicator_level_weights()
    assert weights[1] == pytest.approx(0.25)
    assert weights[0] > 0.6 and weights[2] < weights[3] < weights[1]


def test_category_mapped_scheme_matches_the_default_selection() -> None:
    report = analyze_weights(X, F, np.random.default_rng(1), n_draws=200)
    default = select_compromise(X, F)
    np.testing.assert_allclose(report["schemes"]["category_mapped"]["x"], default.x)
    assert report["schemes"]["category_mapped"]["f"] == default.f.tolist()


def test_dominant_objective_weight_selects_its_best_design() -> None:
    memberships = np.array([[1.0, 0.0, 0.5, 0.5], [0.0, 1.0, 0.5, 0.5]])
    assert selection_for_weights(memberships, np.array([0.97, 0.01, 0.01, 0.01])) == 0
    assert selection_for_weights(memberships, np.array([0.01, 0.97, 0.01, 0.01])) == 1


def test_random_sweep_counts_sum_to_draws_and_are_reproducible() -> None:
    memberships = np.random.default_rng(0).uniform(size=(5, 4))
    first = random_sweep(memberships, np.random.default_rng(3), 500)
    second = random_sweep(memberships, np.random.default_rng(3), 500)
    assert first.sum() == 500 and first.shape == (5,)
    np.testing.assert_array_equal(first, second)


def test_report_has_sweep_summary_fields() -> None:
    sweep = analyze_weights(X, F, np.random.default_rng(2), n_draws=300)["sweep"]
    assert sweep["n_draws"] == 300 and 1 <= sweep["n_distinct_selected"] <= 3
    assert 0.0 <= sweep["share_selecting_default"] <= 1.0
    assert len(sweep["selected_x_min"]) == 8 and len(sweep["selected_f_range_fraction_of_front"]) == 4
    assert equal_weights().sum() == pytest.approx(1.0)
