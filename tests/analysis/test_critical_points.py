"""Tests for the critical-point selection and sustainability probability."""

import numpy as np
import pytest
from scipy.stats import norm

from src.analysis.critical_points import assess_sustainability, select_critical_units


def test_selection_includes_the_unit_that_crosses_the_threshold() -> None:
    effects = np.array([5.0, 14.0, 68.0, 1.0, 12.0])
    np.testing.assert_array_equal(select_critical_units(effects), [2, 1])


def test_selection_returns_single_unit_when_it_alone_exceeds_threshold() -> None:
    np.testing.assert_array_equal(select_critical_units(np.array([85.0, 10.0, 5.0])), [0])


def test_selection_returns_all_units_if_threshold_is_never_reached() -> None:
    assert select_critical_units(np.array([10.0, 20.0]), cumulative_pct=95.0).size == 2


def test_selection_threshold_is_inclusive() -> None:
    np.testing.assert_array_equal(select_critical_units(np.array([50.0, 30.0, 20.0]), cumulative_pct=80.0), [0, 1])


def test_sustainability_probability_matches_normal_band() -> None:
    utility = np.array([15000.0, 16000.0, 17000.0, 16000.0])
    thickness = np.full(4, 60.0)
    assessment = assess_sustainability(utility, thickness, quality_weight=0.3)
    assert assessment.utility_max == pytest.approx(20000.0)
    assert assessment.utility_admissible == pytest.approx(16000.0)
    assert assessment.utility_std == pytest.approx((20000.0 - 16000.0) / 3)
    expected = norm.cdf(20000, 16000, assessment.utility_std) - norm.cdf(16000, 16000, assessment.utility_std)
    assert assessment.probability == pytest.approx(expected)
    assert assessment.probability == pytest.approx(0.49865, abs=1e-4)


def test_confidence_interval_is_symmetric_around_the_mean() -> None:
    utility = np.array([15000.0, 16000.0, 17000.0, 16000.0])
    assessment = assess_sustainability(utility, np.full(4, 60.0), 0.3)
    center = (assessment.mean_ci_lower + assessment.mean_ci_upper) / 2
    assert center == pytest.approx(utility.mean())
    assert assessment.mean_ci_lower < utility.mean() < assessment.mean_ci_upper
