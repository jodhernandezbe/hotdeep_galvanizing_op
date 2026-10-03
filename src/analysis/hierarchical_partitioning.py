"""Hierarchical partitioning of explained variance (Chevan & Sutherland).

Purpose: independent and joint contribution of each predictor to the variance of a response (annex D.5).
Author: Jose D. Hernandez-Betancur
Date: 2026-10-02
"""

import logging
from dataclasses import dataclass
from itertools import combinations
from math import factorial

import numpy as np
from scipy import stats

logger = logging.getLogger(__name__)

SIGNIFICANCE_LEVEL = 0.01


@dataclass(frozen=True)
class HierarchicalPartitioningResult:
    """Outcome of the hierarchical partitioning.

    Attributes:
        independent_pct: Independent effect of each predictor, normalised to 100.
        joint_pct: Joint effect of each predictor, normalised to 100.
        zero_order_r2: R^2 of the regression of the response on each predictor alone.
        critical_r2: Minimum R^2 that is significant at the 0.01 level, T^2 / (n - 2 + T^2).
    """

    independent_pct: np.ndarray
    joint_pct: np.ndarray
    zero_order_r2: np.ndarray
    critical_r2: float


class _R2Table:
    def __init__(self, y: np.ndarray, x: np.ndarray) -> None:
        self._y = y
        self._x = x
        self._variance = float(np.var(y, ddof=1))
        self._cache: dict[frozenset[int], float] = {frozenset(): 0.0}

    def __call__(self, predictors: frozenset[int]) -> float:
        if predictors not in self._cache:
            self._cache[predictors] = self._fit(sorted(predictors))
        return self._cache[predictors]

    def _fit(self, columns: list[int]) -> float:
        design = np.column_stack([np.ones(len(self._y)), self._x[:, columns]])
        beta, *_ = np.linalg.lstsq(design, self._y, rcond=None)
        return float(np.var(design @ beta, ddof=1) / self._variance)


def _weighted_marginal_gain(table: _R2Table, predictor: int, others: list[int], size: int) -> float:
    gains = 0.0
    for subset in combinations(others, size):
        base = frozenset(subset)
        gains += table(base | {predictor}) - table(base)
    return gains


def _independent_effects(table: _R2Table, n_predictors: int) -> np.ndarray:
    effects = np.zeros(n_predictors)
    for predictor in range(n_predictors):
        others = [j for j in range(n_predictors) if j != predictor]
        for size in range(n_predictors):
            weight = factorial(size) * factorial(n_predictors - 1 - size)
            effects[predictor] += weight * _weighted_marginal_gain(table, predictor, others, size)
    return effects / factorial(n_predictors)


def _normalise_to_percent(values: np.ndarray, total: float, label: str) -> np.ndarray:
    if np.isclose(total, 0.0):
        logger.warning(f"Total {label} effect is zero; returning zeros")
        return np.zeros_like(values)
    return 100 * values / total


def _validate(y: np.ndarray, x: np.ndarray) -> None:
    if y.ndim != 1 or x.ndim != 2 or x.shape[0] != y.shape[0]:
        logger.error(f"Incompatible shapes y={y.shape}, x={x.shape}")
        raise ValueError(f"y must be (n,) and x (n, m); got {y.shape} and {x.shape}")
    if x.shape[0] <= x.shape[1] + 1:
        logger.error("Not enough observations for the regressions")
        raise ValueError("The number of observations must exceed the number of predictors plus one")


def raw_independent_effects(y: np.ndarray, x: np.ndarray) -> np.ndarray:
    """Independent effects expressed as R^2 contributions (they add up to the full-model R^2).

    Args:
        y: Response, shape (n,).
        x: Predictors, shape (n, m).

    Returns:
        Array of shape (m,).
    """
    y, x = np.asarray(y, dtype=float), np.asarray(x, dtype=float)
    _validate(y, x)
    return _independent_effects(_R2Table(y, x), x.shape[1])


def hierarchical_partitioning(y: np.ndarray, x: np.ndarray) -> HierarchicalPartitioningResult:
    """Partition the explained variance of ``y`` among the predictors in ``x``.

    Args:
        y: Response, shape (n,).
        x: Predictors, shape (n, m).

    Returns:
        Independent and joint effects (percent), zero-order R^2 and the critical R^2.
    """
    y, x = np.asarray(y, dtype=float), np.asarray(x, dtype=float)
    _validate(y, x)
    n, m = x.shape
    table = _R2Table(y, x)
    independent = _independent_effects(table, m)
    zero_order = np.array([table(frozenset({i})) for i in range(m)])
    joint = zero_order - independent
    t_critical = stats.t.ppf(1 - SIGNIFICANCE_LEVEL / 2, n - 2)
    return HierarchicalPartitioningResult(
        independent_pct=_normalise_to_percent(independent, independent.sum(), "independent"),
        joint_pct=_normalise_to_percent(joint, zero_order.sum() - independent.sum(), "joint"),
        zero_order_r2=zero_order,
        critical_r2=float(t_critical**2 / (n - 2 + t_critical**2)),
    )
