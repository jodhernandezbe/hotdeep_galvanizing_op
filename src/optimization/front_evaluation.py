"""Re-evaluation of a set of designs (a Pareto front) at another simulation budget or cost scenario.

Purpose: the NSGA-II search runs on a reduced simulated year (fixed annual costs do not scale with the pieces), so
the front must be re-evaluated at the full-year budget before it is reported or a compromise is selected; the same
function serves the price-scenario sensitivity.
Author: Jose D. Hernandez-Betancur
Date: 2026-10-03
"""

import logging

import numpy as np

from src.optimization.problem import BatchSummary, HdgRobustProblem
from src.process.operating_policy import (
    BASELINE_POLICY,
    N_DECISION_VARIABLES,
    THESIS_PICKLING_RENEWAL_FE_G_PER_L,
)
from src.sustainability.costs import get_cost_scenario

logger = logging.getLogger(__name__)


def reevaluate_front(
    x: np.ndarray,
    scenario: str,
    base_seed: int,
    n_samples: int,
    items: int,
    n_jobs: int = 1,
    fed_atom_economy: bool = False,
) -> BatchSummary:
    """Summary of the given designs plus the baseline under one cost scenario.

    Pads legacy 7-variable decision matrices with the thesis pickling-renewal trigger.

    Args:
        x: Decision matrix, shape (n, `N_DECISION_VARIABLES`) or the legacy (n, 7).
        scenario: Cost scenario name of the evaluation (also the reference of the robust cost).
        base_seed: Common-random-number base seed (use the optimization's seed to reproduce its objectives).
        n_samples: Monte Carlo samples per design.
        items: Steel pieces per simulated year.
        n_jobs: joblib workers.
        fed_atom_economy: Fed-basis atom economy for the acid units (see `compute_greenscope`).

    Returns:
        The batch summary with n + 1 rows; the last row is the baseline policy.
    """
    designs = np.vstack([pad_legacy_designs(x), BASELINE_POLICY.to_array()])
    problem = HdgRobustProblem(
        n_samples, items, base_seed, n_jobs, costs=get_cost_scenario(scenario), fed_atom_economy=fed_atom_economy
    )
    return problem.batch_summary(designs)


def pad_legacy_designs(x: np.ndarray) -> np.ndarray:
    """Bring a decision matrix to the current variable count.

    Args:
        x: Decision matrix, shape (n, `N_DECISION_VARIABLES`) or the legacy (n, 7).

    Returns:
        Matrix of shape (n, `N_DECISION_VARIABLES`); legacy rows get the thesis pickling-renewal trigger.
    """
    matrix = np.atleast_2d(np.asarray(x, dtype=float))
    if matrix.shape[1] == N_DECISION_VARIABLES:
        return matrix
    trigger = np.full((matrix.shape[0], 1), THESIS_PICKLING_RENEWAL_FE_G_PER_L)
    return np.hstack([matrix, trigger])
