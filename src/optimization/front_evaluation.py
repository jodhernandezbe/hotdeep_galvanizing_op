"""Re-evaluation of a set of designs (a Pareto front) at another simulation budget or cost scenario.

Purpose: the NSGA-II search runs on a reduced simulated year (fixed annual costs do not scale with the pieces), so
the front must be re-evaluated at the full-year budget before it is reported or a compromise is selected; the same
function serves the price-scenario sensitivity.
Author: Jose D. Hernandez-Betancur
Date: 2026-10-03
"""

import logging

import numpy as np

from src.optimization.problem import DEFECT_PROBABILITY_LIMIT, MASS_SCALARS_OFFSET, HdgRobustProblem
from src.process.operating_policy import BASELINE_POLICY
from src.process.simulation import NORMAL_PICKLING_IRON_LIMIT_G_PER_L
from src.sustainability.costs import get_cost_scenario

logger = logging.getLogger(__name__)


def reevaluate_front(
    x: np.ndarray,
    scenario: str,
    base_seed: int,
    n_samples: int,
    items: int,
    n_jobs: int = 1,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Objectives, constraints and raw-material masses of the designs plus the baseline under one cost scenario.

    Args:
        x: Decision matrix, shape (n, 7).
        scenario: Cost scenario name.
        base_seed: Common-random-number base seed (use the optimization's seed to reproduce its objectives).
        n_samples: Monte Carlo samples per design.
        items: Steel pieces per simulated year.
        n_jobs: joblib workers.

    Returns:
        Objectives (n + 1, 4), constraints (n + 1, 2) and mean raw-material masses per
        `RAW_MATERIAL_KEYS` (n + 1, 7) [kg]; the last row is the baseline policy.
    """
    designs = np.vstack([np.atleast_2d(x), BASELINE_POLICY.to_array()])
    problem = HdgRobustProblem(n_samples, items, base_seed, n_jobs, costs=get_cost_scenario(scenario))
    means = problem.batch_means(designs)
    objectives = np.column_stack([-means[:, 0], means[:, 1], means[:, 2], means[:, 3]])
    constraints = np.column_stack(
        [
            means[:, 4] - DEFECT_PROBABILITY_LIMIT,
            means[:, 5] - NORMAL_PICKLING_IRON_LIMIT_G_PER_L,
        ]
    )
    return objectives, constraints, means[:, MASS_SCALARS_OFFSET:]
