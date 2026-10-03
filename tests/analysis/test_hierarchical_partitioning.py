"""Tests for the hierarchical partitioning."""

from itertools import permutations

import numpy as np
import pytest
from scipy import stats

from src.analysis.hierarchical_partitioning import hierarchical_partitioning, raw_independent_effects


def _r2(y: np.ndarray, x: np.ndarray, columns: tuple[int, ...]) -> float:
    if not columns:
        return 0.0
    design = np.column_stack([np.ones(len(y)), x[:, list(columns)]])
    beta, *_ = np.linalg.lstsq(design, y, rcond=None)
    residual = y - design @ beta
    return 1 - residual.var() / y.var()


def _permutation_average(y: np.ndarray, x: np.ndarray) -> np.ndarray:
    m = x.shape[1]
    gains = np.zeros(m)
    orders = list(permutations(range(m)))
    for order in orders:
        for position, predictor in enumerate(order):
            before = tuple(sorted(order[:position]))
            after = tuple(sorted(order[: position + 1]))
            gains[predictor] += _r2(y, x, after) - _r2(y, x, before)
    return gains / len(orders)


@pytest.fixture
def correlated_data() -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(42)
    base = rng.normal(size=(200, 4))
    x = base.copy()
    x[:, 1] += 0.7 * base[:, 0]
    x[:, 3] += 0.5 * base[:, 2] + 0.3 * base[:, 1]
    y = x @ np.array([1.0, 0.5, -0.8, 0.3]) + rng.normal(scale=1.5, size=200)
    return y, x


def test_matches_permutation_average(correlated_data: tuple[np.ndarray, np.ndarray]) -> None:
    y, x = correlated_data
    assert raw_independent_effects(y, x) == pytest.approx(_permutation_average(y, x))


def test_independent_effects_sum_to_full_model_r2(correlated_data: tuple[np.ndarray, np.ndarray]) -> None:
    y, x = correlated_data
    assert raw_independent_effects(y, x).sum() == pytest.approx(_r2(y, x, (0, 1, 2, 3)))


def test_orthogonal_predictors_independent_equals_zero_order() -> None:
    rng = np.random.default_rng(1)
    centred = rng.normal(size=(100, 3))
    centred -= centred.mean(axis=0)
    x, _ = np.linalg.qr(centred)
    y = x @ np.array([3.0, 2.0, 1.0]) + rng.normal(scale=0.05, size=100)
    result = hierarchical_partitioning(y, x)
    assert raw_independent_effects(y, x) == pytest.approx(result.zero_order_r2, abs=1e-6)
    assert result.joint_pct == pytest.approx(np.zeros(3), abs=1e-3)


def test_percentages_and_critical_r2(correlated_data: tuple[np.ndarray, np.ndarray]) -> None:
    y, x = correlated_data
    result = hierarchical_partitioning(y, x)
    assert result.independent_pct.sum() == pytest.approx(100.0)
    assert result.joint_pct.sum() == pytest.approx(100.0)
    t = stats.t.ppf(0.995, len(y) - 2)
    assert result.critical_r2 == pytest.approx(t**2 / (len(y) - 2 + t**2))
    assert result.zero_order_r2 == pytest.approx([_r2(y, x, (i,)) for i in range(4)])


def test_rejects_bad_shapes() -> None:
    with pytest.raises(ValueError):
        hierarchical_partitioning(np.zeros(5), np.zeros((4, 2)))
    with pytest.raises(ValueError):
        hierarchical_partitioning(np.arange(3.0), np.zeros((3, 2)))
