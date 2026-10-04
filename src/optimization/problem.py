"""NSGA-II problem definition: robust HDG operation under uncertainty.

Purpose: constrained four-objective pymoo problem over the operating policy (spec optimization/nsga2).
Author: Jose D. Hernandez-Betancur
Date: 2026-10-02
"""

import logging
from dataclasses import dataclass
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
from src.sustainability.costs import (
    RAW_MATERIAL_COM_FACTOR,
    RAW_MATERIAL_KEYS,
    CostParameters,
    default_costs,
    get_cost_scenario,
    raw_material_price_delta,
)
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
TAIL_FRACTION: Final = 0.1
DEFECT_QUANTILE: Final = 0.95
PRICE_ROBUST_SCENARIOS: Final = ("market2025", "thesis_corrected", "thesis")


@dataclass(frozen=True)
class BatchSummary:
    """Aggregated Monte Carlo statistics of a batch of designs.

    Attributes:
        robust_objectives: Objectives the optimizer minimizes, shape (n, 4): CVaR of the tail of
            each objective and, for the cost, the worst scenario of `price_scenarios`.
        mean_objectives: Plain Monte Carlo means of the objectives, shape (n, 4).
        constraints: Constraint values (g <= 0 feasible), shape (n, 2).
        raw_material_masses_kg: Mean purchases per `RAW_MATERIAL_KEYS` [kg], shape (n, 7).
    """

    robust_objectives: np.ndarray
    mean_objectives: np.ndarray
    constraints: np.ndarray
    raw_material_masses_kg: np.ndarray


def lower_tail_mean(values: np.ndarray, tail_fraction: float) -> np.ndarray:
    """Mean of the worst (lowest) tail of each row: the CVaR of a quantity to maximize.

    Args:
        values: Sample matrix, shape (n, s).
        tail_fraction: Fraction of samples in the tail (at least one sample is used).

    Returns:
        Tail means, shape (n,).
    """
    ordered = np.sort(np.asarray(values, dtype=float), axis=1)
    count = max(1, round(ordered.shape[1] * tail_fraction))
    return ordered[:, :count].mean(axis=1)


def upper_tail_mean(values: np.ndarray, tail_fraction: float) -> np.ndarray:
    """Mean of the worst (highest) tail of each row: the CVaR of a quantity to minimize.

    Args:
        values: Sample matrix, shape (n, s).
        tail_fraction: Fraction of samples in the tail (at least one sample is used).

    Returns:
        Tail means, shape (n,).
    """
    ordered = np.sort(np.asarray(values, dtype=float), axis=1)
    count = max(1, round(ordered.shape[1] * tail_fraction))
    return ordered[:, -count:].mean(axis=1)


def candidate_sample_scalars(
    x: tuple[float, ...],
    seed: np.random.SeedSequence,
    items: int,
    weights: np.ndarray,
    preserve_thesis_quirks: bool,
    costs: CostParameters | None = None,
    fed_atom_economy: bool = False,
) -> np.ndarray:
    """Simulate one Monte Carlo sample of one candidate and reduce it to the optimizer scalars.

    Args:
        x: Decision vector (7 values in `POLICY_BOUNDS` order).
        seed: Child seed of this sample (common random numbers).
        items: Steel pieces simulated in the year.
        weights: Indicator weights, length 18.
        preserve_thesis_quirks: Simulation mode.
        costs: Cost scenario of the COM indicator.
        fed_atom_economy: Fed-basis atom economy for the acid units (see `compute_greenscope`).

    Returns:
        Array [U_P, COM, V_l-poll, V_WT, defect fraction, peak pickling Fe2+, peak fluxing Fe2+]
        followed by the raw-material masses per `RAW_MATERIAL_KEYS` [kg], length `_N_SCALARS`.
    """
    policy = OperatingPolicy.from_array(np.asarray(x))
    year = simulate_year(items, np.random.default_rng(seed), preserve_thesis_quirks, policy)
    evaluation, greenscope = evaluate_year_detailed(year, weights, preserve_thesis_quirks, costs, fed_atom_economy)
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
        tail_fraction: float | None = TAIL_FRACTION,
        defect_quantile: float | None = DEFECT_QUANTILE,
        price_scenarios: tuple[str, ...] | None = PRICE_ROBUST_SCENARIOS,
        fed_atom_economy: bool = False,
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
            tail_fraction: CVaR tail of the robust objectives; None optimizes plain means.
            defect_quantile: Quantile of the chance constraints; None constrains the means.
            price_scenarios: Scenario names of the worst-case cost objective; None or empty keeps
                the evaluation scenario only.
            fed_atom_economy: Fed-basis atom economy for the acid units (see `compute_greenscope`).
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
        self.tail_fraction = tail_fraction
        self.defect_quantile = defect_quantile
        self.price_scenarios = price_scenarios
        self.fed_atom_economy = fed_atom_economy

    def batch_summary(self, x: np.ndarray) -> BatchSummary:
        """Robust and mean Monte Carlo statistics for a batch of designs.

        Args:
            x: Decision matrix, shape (n, `N_DECISION_VARIABLES`).

        Returns:
            The batch summary; `robust_objectives` equals `mean_objectives` when `tail_fraction`
            is None and the scenario set is empty.
        """
        scalars = self._batch_scalars(np.atleast_2d(x))
        masses = scalars[:, :, MASS_SCALARS_OFFSET:]
        mean = scalars.mean(axis=1)
        mean_objectives = np.column_stack([-mean[:, 0], mean[:, 1], mean[:, 2], mean[:, 3]])
        return BatchSummary(
            robust_objectives=self._robust_objectives(scalars, masses, mean_objectives),
            mean_objectives=mean_objectives,
            constraints=self._constraints(scalars, mean),
            raw_material_masses_kg=masses.mean(axis=1),
        )

    def _robust_objectives(self, scalars: np.ndarray, masses: np.ndarray, mean_objectives: np.ndarray) -> np.ndarray:
        if self.tail_fraction is None:
            return np.array(mean_objectives, copy=True)
        tail = self.tail_fraction
        return np.column_stack(
            [
                -lower_tail_mean(scalars[:, :, 0], tail),
                self._robust_cost(scalars[:, :, 1], masses, tail),
                upper_tail_mean(scalars[:, :, 2], tail),
                upper_tail_mean(scalars[:, :, 3], tail),
            ]
        )

    def _robust_cost(self, com_samples: np.ndarray, masses: np.ndarray, tail: float) -> np.ndarray:
        reference = self.costs if self.costs is not None else default_costs(self.preserve_thesis_quirks)
        worst = upper_tail_mean(com_samples, tail)
        for name in self.price_scenarios or ():
            delta = raw_material_price_delta(reference, get_cost_scenario(name))
            shifted = com_samples + RAW_MATERIAL_COM_FACTOR * masses @ delta
            worst = np.maximum(worst, upper_tail_mean(shifted, tail))
        return worst

    def _constraints(self, scalars: np.ndarray, mean: np.ndarray) -> np.ndarray:
        if self.defect_quantile is None:
            defect, peak = mean[:, 4], mean[:, 5]
        else:
            defect = np.quantile(scalars[:, :, 4], self.defect_quantile, axis=1)
            peak = np.quantile(scalars[:, :, 5], self.defect_quantile, axis=1)
        return np.column_stack([defect - DEFECT_PROBABILITY_LIMIT, peak - NORMAL_PICKLING_IRON_LIMIT_G_PER_L])

    def _evaluate(self, x: np.ndarray, out: dict[str, Any], *args: Any, **kwargs: Any) -> None:
        summary = self.batch_summary(np.atleast_2d(x))
        out["F"] = summary.robust_objectives
        out["G"] = summary.constraints

    def _batch_scalars(self, x: np.ndarray) -> np.ndarray:
        seeds = sample_seeds(self.base_seed, self.n_mc_samples)
        jobs = [(tuple(row), seed) for row in x for seed in seeds]
        rows = self._run_jobs(jobs)
        return np.asarray(rows).reshape(x.shape[0], self.n_mc_samples, _N_SCALARS)

    def _run_jobs(self, jobs: list[tuple[tuple[float, ...], np.random.SeedSequence]]) -> list[np.ndarray]:
        if self.n_jobs == 1:
            return [self._one_job(row, seed) for row, seed in jobs]
        parallel_rows = Parallel(n_jobs=self.n_jobs)(
            delayed(candidate_sample_scalars)(
                row, seed, self.items, self.weights, self.preserve_thesis_quirks, self.costs, self.fed_atom_economy
            )
            for row, seed in jobs
        )
        return cast(list[np.ndarray], list(parallel_rows))

    def _one_job(self, row: tuple[float, ...], seed: np.random.SeedSequence) -> np.ndarray:
        return candidate_sample_scalars(
            row, seed, self.items, self.weights, self.preserve_thesis_quirks, self.costs, self.fed_atom_economy
        )
