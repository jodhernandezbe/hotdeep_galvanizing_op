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

    Returns:
        The batch summary with n + 1 rows; the last row is the baseline policy.
    """
    designs = np.vstack([_pad_legacy(np.atleast_2d(x)), BASELINE_POLICY.to_array()])
    problem = HdgRobustProblem(n_samples, items, base_seed, n_jobs, costs=get_cost_scenario(scenario))
    return problem.batch_summary(designs)


def _pad_legacy(x: np.ndarray) -> np.ndarray:
    if x.shape[1] == N_DECISION_VARIABLES:
        return x
    trigger = np.full((x.shape[0], 1), THESIS_PICKLING_RENEWAL_FE_G_PER_L)
    return np.hstack([x, trigger])
