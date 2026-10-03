"""NSGA-II problem definition: robust HDG operation under uncertainty.

Purpose: constrained four-objective pymoo problem over the operating policy (spec optimization/nsga2).
Author: Jose D. Hernandez-Betancur
Date: 2026-10-02
"""

import logging
from typing import Any, Final, cast

import numpy as np
from joblib import Parallel, delayed
from pymoo.core.problem import Problem

from src.optimization.evaluation import OPTIMIZATION_ITEMS, OPTIMIZATION_SAMPLES, sample_seeds
from src.process.operating_policy import (
    N_DECISION_VARIABLES,
    OperatingPolicy,
    policy_lower_bounds,
    policy_upper_bounds,
)
from src.process.simulation import NORMAL_PICKLING_IRON_LIMIT_G_PER_L, simulate_year
from src.sustainability.costs import RAW_MATERIAL_KEYS, CostParameters
from src.sustainability.greenscope import Indicator, raw_material_masses_kg
from src.sustainability.stream_assembly import build_balance
from src.sustainability.thesis_weights import thesis_indicator_weights
from src.sustainability.utility import evaluate_year_detailed

logger = logging.getLogger(__name__)

N_OBJECTIVES: Final = 4
N_CONSTRAINTS: Final = 2
DEFECT_PROBABILITY_LIMIT: Final = 0.02
MASS_SCALARS_OFFSET: Final = 7
_N_SCALARS: Final = MASS_SCALARS_OFFSET + len(RAW_MATERIAL_KEYS)


def candidate_sample_scalars(
    x: tuple[float, ...],
    seed: np.random.SeedSequence,
    items: int,
    weights: np.ndarray,
    preserve_thesis_quirks: bool,
    costs: CostParameters | None = None,
) -> np.ndarray:
    """Simulate one Monte Carlo sample of one candidate and reduce it to the optimizer scalars.

    Args:
        x: Decision vector (7 values in `POLICY_BOUNDS` order).
        seed: Child seed of this sample (common random numbers).
        items: Steel pieces simulated in the year.
        weights: Indicator weights, length 18.
        preserve_thesis_quirks: Simulation mode.
        costs: Cost scenario of the COM indicator.

    Returns:
        Array [U_P, COM, V_l-poll, V_WT, defect fraction, peak pickling Fe2+, peak fluxing Fe2+]
        followed by the raw-material masses per `RAW_MATERIAL_KEYS` [kg], length `_N_SCALARS`.
    """
    policy = OperatingPolicy.from_array(np.asarray(x))
    year = simulate_year(items, np.random.default_rng(seed), preserve_thesis_quirks, policy)
    evaluation, greenscope = evaluate_year_detailed(year, weights, preserve_thesis_quirks, costs)
    indicators = greenscope.indicators
    head = np.array(
        [
            evaluation.process_utility,
            indicators[:, Indicator.MANUFACTURING_COST].sum(),
            indicators[:, Indicator.POLLUTED_LIQUID_VOLUME].sum(),
            indicators[:, Indicator.WATER_CONSUMPTION].sum(),
            year.totals.n_defective_pieces / year.totals.n_quality_pieces,
            year.totals.peak_pickling_fe2_g_per_l,
            year.totals.peak_fluxing_fe2_g_per_l,
        ]
    )
    return np.concatenate([head, raw_material_masses_kg(build_balance(year).input_streams)])


class HdgRobustProblem(Problem):
    """Four-objective, two-constraint minimization over the seven-variable operating policy.

    Objectives: [-E[U_P], E[COM], E[V_l-poll], E[V_WT]]. Constraints (g <= 0 feasible):
    [E[defect] - 0.02, E[peak pickling Fe2+] - 150]. The fluxing-bath Fe2+ limit (5 g/L) is a renewal trigger,
    not a constraint: renewals are a consequence priced into COM and V_l-poll (docs/LITERATURE.md).
    """

    def __init__(
        self,
        n_mc_samples: int = OPTIMIZATION_SAMPLES,
        items: int = OPTIMIZATION_ITEMS,
        base_seed: int = 0,
        n_jobs: int = 1,
        weights: np.ndarray | None = None,
        preserve_thesis_quirks: bool = False,
        costs: CostParameters | None = None,
    ) -> None:
        """Configure the stochastic evaluation budget.

        Args:
            n_mc_samples: Monte Carlo samples per candidate evaluation.
            items: Steel pieces per simulated year.
            base_seed: Base seed of the common-random-number batch.
            n_jobs: joblib workers over the (candidate, sample) pairs; 1 is serial.
            weights: Indicator weights, length 18; thesis weights when None.
            preserve_thesis_quirks: Simulation mode (False = corrected, the optimization substrate).
            costs: Cost scenario of the COM indicator; the fidelity mode's default when None.
        """
        super().__init__(
            n_var=N_DECISION_VARIABLES,
            n_obj=N_OBJECTIVES,
            n_ieq_constr=N_CONSTRAINTS,
            xl=policy_lower_bounds(),
            xu=policy_upper_bounds(),
        )
        self.n_mc_samples = n_mc_samples
        self.items = items
        self.base_seed = base_seed
        self.n_jobs = n_jobs
        self.weights = thesis_indicator_weights() if weights is None else np.asarray(weights, dtype=float)
        self.preserve_thesis_quirks = preserve_thesis_quirks
        self.costs = costs

    def batch_means(self, x: np.ndarray) -> np.ndarray:
        """Monte Carlo means of the per-sample scalars for a batch of designs.

        Args:
            x: Decision matrix, shape (n, 7).

        Returns:
            Means of the `candidate_sample_scalars` layout, shape (n, `_N_SCALARS`): the optimizer
            scalars first, then the raw-material masses from `MASS_SCALARS_OFFSET` on.
        """
        return self._batch_scalars(np.atleast_2d(x)).mean(axis=1)

    def _evaluate(self, x: np.ndarray, out: dict[str, Any], *args: Any, **kwargs: Any) -> None:
        means = self.batch_means(np.atleast_2d(x))
        out["F"] = np.column_stack([-means[:, 0], means[:, 1], means[:, 2], means[:, 3]])
        out["G"] = np.column_stack(
            [
                means[:, 4] - DEFECT_PROBABILITY_LIMIT,
                means[:, 5] - NORMAL_PICKLING_IRON_LIMIT_G_PER_L,
            ]
        )

    def _batch_scalars(self, x: np.ndarray) -> np.ndarray:
        seeds = sample_seeds(self.base_seed, self.n_mc_samples)
        jobs = [(tuple(row), seed) for row in x for seed in seeds]
        rows = self._run_jobs(jobs)
        return np.asarray(rows).reshape(x.shape[0], self.n_mc_samples, _N_SCALARS)

    def _run_jobs(self, jobs: list[tuple[tuple[float, ...], np.random.SeedSequence]]) -> list[np.ndarray]:
        if self.n_jobs == 1:
            return [self._one_job(row, seed) for row, seed in jobs]
        parallel_rows = Parallel(n_jobs=self.n_jobs)(
            delayed(candidate_sample_scalars)(row, seed, self.items, self.weights, self.preserve_thesis_quirks, self.costs)
            for row, seed in jobs
        )
        return cast(list[np.ndarray], list(parallel_rows))

    def _one_job(self, row: tuple[float, ...], seed: np.random.SeedSequence) -> np.ndarray:
        return candidate_sample_scalars(row, seed, self.items, self.weights, self.preserve_thesis_quirks, self.costs)
