"""Utility of the unit processes and of the whole hot-dip galvanizing process.

Purpose: weight the GREENSCOPE scores and the coating quality into additive utilities (thesis annex C and D.1).
Author: Jose D. Hernandez-Betancur
Date: 2026-10-02
"""

import logging
from dataclasses import dataclass
from typing import Final

import numpy as np

from src.process.simulation import YearResult
from src.sustainability.costs import CostParameters
from src.sustainability.greenscope import GreenscopeResult, compute_greenscope
from src.sustainability.stream_assembly import build_balance
from src.sustainability.streams import N_INDICATORS, N_UNIT_PROCESSES

logger = logging.getLogger(__name__)

N_ENVIRONMENT_INDICATORS: Final = 11
N_EFFICIENCY_INDICATORS: Final = 4
N_CATEGORIES: Final = 5
QUALITY_WEIGHT_INDEX: Final = N_INDICATORS
PERCENT: Final = 100.0


@dataclass(frozen=True)
class YearEvaluation:
    """Sustainability evaluation of one simulated year.

    Attributes:
        unit_utility: Utility of each unit process, shape (7,).
        quality_utility_pct: Mass-weighted coating-quality utility [%].
        mean_standard_thickness_um: Mean thickness required by the standard [um] (best quality scale).
        process_utility: Global process utility U_P.
        process_scores: Mean GREENSCOPE score of each indicator over the unit processes, plus quality, shape (18,).
        unit_scores: GREENSCOPE scores per unit process and indicator, shape (7, 17).
    """

    unit_utility: np.ndarray
    quality_utility_pct: float
    mean_standard_thickness_um: float
    process_utility: float
    process_scores: np.ndarray
    unit_scores: np.ndarray


def build_indicator_weights(
    category_weights: np.ndarray,
    environment_weights: np.ndarray,
    efficiency_weights: np.ndarray,
) -> np.ndarray:
    """Combine category and within-category weights into one weight per indicator.

    Args:
        category_weights: Weights of [environment, efficiency, energy, economy, quality], length 5.
        environment_weights: Weights of the 11 environmental indicators.
        efficiency_weights: Weights of the 4 efficiency indicators.

    Returns:
        Weights of the 17 GREENSCOPE indicators followed by the quality weight, length 18.
    """
    _check_length(category_weights, N_CATEGORIES, "category_weights")
    _check_length(environment_weights, N_ENVIRONMENT_INDICATORS, "environment_weights")
    _check_length(efficiency_weights, N_EFFICIENCY_INDICATORS, "efficiency_weights")
    return np.concatenate(
        [
            category_weights[0] * np.asarray(environment_weights),
            category_weights[1] * np.asarray(efficiency_weights),
            np.asarray(category_weights[2:4]),
            np.asarray(category_weights[4:5]),
        ]
    )


def evaluate_year(year: YearResult, weights: np.ndarray, preserve_thesis_quirks: bool = True) -> YearEvaluation:
    """Evaluate the sustainability of a simulated year.

    Args:
        year: Summary of the simulated year.
        weights: Indicator weights from `build_indicator_weights`, length 18.
        preserve_thesis_quirks: Forwarded to GREENSCOPE (see `compute_greenscope`).

    Returns:
        Unit and global utilities with the underlying scores.
    """
    evaluation, _ = evaluate_year_detailed(year, weights, preserve_thesis_quirks)
    return evaluation


def evaluate_year_detailed(
    year: YearResult,
    weights: np.ndarray,
    preserve_thesis_quirks: bool = True,
    costs: CostParameters | None = None,
) -> tuple[YearEvaluation, GreenscopeResult]:
    """Evaluate a simulated year and also return the underlying GREENSCOPE result.

    Args:
        year: Summary of the simulated year.
        weights: Indicator weights from `build_indicator_weights`, length 18.
        preserve_thesis_quirks: Forwarded to GREENSCOPE (see `compute_greenscope`).
        costs: Cost scenario of the COM indicator; the fidelity mode's default when None.

    Returns:
        The evaluation and the GREENSCOPE result it was computed from (raw indicator values included).
    """
    _check_length(weights, N_INDICATORS + 1, "weights")
    greenscope = _run_greenscope(year, preserve_thesis_quirks, costs)
    quality_pct = year.totals.quality_mass_weighted * PERCENT / year.totals.steel_kg
    standard_um = year.totals.standard_thickness_sum_um / year.totals.n_quality_pieces
    unit_utility = greenscope.score @ weights[:N_INDICATORS]
    evaluation = YearEvaluation(
        unit_utility=unit_utility,
        quality_utility_pct=quality_pct,
        mean_standard_thickness_um=standard_um,
        process_utility=_process_utility(unit_utility, quality_pct, standard_um, weights),
        process_scores=np.append(greenscope.score.mean(axis=0), quality_pct),
        unit_scores=greenscope.score,
    )
    return evaluation, greenscope


def _run_greenscope(year: YearResult, preserve_thesis_quirks: bool, costs: CostParameters | None) -> GreenscopeResult:
    balance = build_balance(year)
    return compute_greenscope(
        balance.input_streams,
        balance.output_streams,
        balance.energy_j,
        balance.sodium_carboxylate_mw,
        balance.grease_mw,
        balance.fe2_pickling_kg,
        balance.fe2_fluxing_kg,
        balance.steel_surface_kg,
        preserve_thesis_quirks=preserve_thesis_quirks,
        costs=costs,
    )


def _process_utility(unit_utility: np.ndarray, quality_pct: float, standard_um: float, weights: np.ndarray) -> float:
    quality_weight = weights[QUALITY_WEIGHT_INDEX]
    return float(standard_um * quality_pct + standard_um * unit_utility.sum() / (N_UNIT_PROCESSES * quality_weight))


def _check_length(values: np.ndarray, expected: int, name: str) -> None:
    if np.asarray(values).shape != (expected,):
        message = f"{name} must have shape ({expected},), got {np.asarray(values).shape}"
        logger.error(message)
        raise ValueError(message)
