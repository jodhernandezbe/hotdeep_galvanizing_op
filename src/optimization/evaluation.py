"""Stochastic evaluation of an operating policy: decision vector -> Monte Carlo distributions.

Purpose: common-random-number Monte Carlo wrapper around the yearly simulation for the NSGA-II optimization
(spec simulation/operating-policy, change add-nsga2-robust-optimization).
Author: Jose D. Hernandez-Betancur
Date: 2026-10-02
"""

import logging
from dataclasses import dataclass, fields
from pathlib import Path
from typing import Final, cast

import numpy as np
from joblib import Parallel, delayed

from src.process.operating_policy import OperatingPolicy
from src.process.simulation import simulate_year
from src.sustainability.costs import CostParameters
from src.sustainability.greenscope import Indicator, raw_material_masses_kg
from src.sustainability.stream_assembly import build_balance
from src.sustainability.streams import UnitProcess
from src.sustainability.thesis_weights import thesis_indicator_weights
from src.sustainability.utility import evaluate_year_detailed

logger = logging.getLogger(__name__)

OPTIMIZATION_ITEMS: Final = 1_000_000
OPTIMIZATION_SAMPLES: Final = 100
FULL_YEAR_ITEMS: Final = 41_379_264
DEEP_SAMPLES: Final = 1000
CRITICAL_STAGES: Final = (UnitProcess.PICKLING, UnitProcess.FLUXING)


@dataclass(frozen=True)
class PolicyEvaluation:
    """Monte Carlo distributions of one operating policy (n samples).

    Attributes:
        process_utility: Global process utility U_P, shape (n,).
        quality_utility_pct: Mass-weighted coating-quality utility [%], shape (n,).
        mean_standard_thickness_um: Mean ISO 1461 required thickness [um], shape (n,).
        process_scores: Mean indicator scores plus quality [%], shape (n, 18).
        unit_indicators: Raw GREENSCOPE indicator values per unit process, shape (n, 7, 17).
        unit_scores: GREENSCOPE scores per unit process [%], shape (n, 7, 17).
        defect_fraction: Fraction of pieces below the ISO 1461 thickness, shape (n,).
        mean_coating_thickness_um: Mean deposited coating thickness [um], shape (n,).
        peak_pickling_fe2_g_per_l: Peak Fe2+ concentration seen in the normal pickling bath [g/L], shape (n,).
        peak_fluxing_fe2_g_per_l: Peak Fe2+ concentration seen in the fluxing bath [g/L], shape (n,).
        raw_material_masses_kg: Raw-material purchases per `RAW_MATERIAL_KEYS` [kg], shape (n, 7).
    """

    process_utility: np.ndarray
    quality_utility_pct: np.ndarray
    mean_standard_thickness_um: np.ndarray
    process_scores: np.ndarray
    unit_indicators: np.ndarray
    unit_scores: np.ndarray
    defect_fraction: np.ndarray
    mean_coating_thickness_um: np.ndarray
    peak_pickling_fe2_g_per_l: np.ndarray
    peak_fluxing_fe2_g_per_l: np.ndarray
    raw_material_masses_kg: np.ndarray

    @property
    def n_samples(self) -> int:
        """Number of Monte Carlo samples."""
        return int(self.process_utility.size)

    @property
    def com_usd(self) -> np.ndarray:
        """Cost of manufacture per sample [USD], summed over the unit processes, shape (n,)."""
        return self.unit_indicators[:, :, Indicator.MANUFACTURING_COST].sum(axis=1)

    @property
    def polluted_liquid_m3(self) -> np.ndarray:
        """Polluted liquid volume per sample [m3], summed over the unit processes, shape (n,)."""
        return self.unit_indicators[:, :, Indicator.POLLUTED_LIQUID_VOLUME].sum(axis=1)

    @property
    def water_intake_m3(self) -> np.ndarray:
        """Freshwater intake per sample [m3], summed over the unit processes, shape (n,)."""
        return self.unit_indicators[:, :, Indicator.WATER_CONSUMPTION].sum(axis=1)

    @property
    def objective_means(self) -> np.ndarray:
        """Optimizer objectives [-E[U_P], E[COM], E[V_l-poll], E[V_WT]], shape (4,)."""
        return np.array(
            [
                -self.process_utility.mean(),
                self.com_usd.mean(),
                self.polluted_liquid_m3.mean(),
                self.water_intake_m3.mean(),
            ]
        )

    def stage_indicator(self, unit: UnitProcess, indicator: Indicator) -> np.ndarray:
        """Raw indicator values of one unit process, shape (n,).

        Args:
            unit: Unit process.
            indicator: GREENSCOPE indicator.

        Returns:
            Per-sample values in the indicator's native unit.
        """
        return self.unit_indicators[:, unit, indicator]

    def save(self, path: Path) -> None:
        """Persist the arrays to a compressed `.npz` file.

        Args:
            path: Destination file.
        """
        path.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(path, **{item.name: getattr(self, item.name) for item in fields(self)})

    @classmethod
    def load(cls, path: Path) -> "PolicyEvaluation":
        """Load a persisted evaluation.

        Args:
            path: `.npz` file written by `save`.

        Returns:
            The restored evaluation.
        """
        with np.load(path) as data:
            return cls(**{item.name: data[item.name] for item in fields(cls)})


def sample_seeds(base_seed: int, n_samples: int) -> list[np.random.SeedSequence]:
    """Spawn the per-sample seed sequences (common random numbers across policies).

    Args:
        base_seed: Base seed of the Monte Carlo batch.
        n_samples: Number of samples.

    Returns:
        One child seed sequence per sample; identical for every policy evaluated with the same base seed.
    """
    return np.random.SeedSequence(base_seed).spawn(n_samples)


def evaluate_policy(
    policy: OperatingPolicy | None,
    base_seed: int,
    n_samples: int = OPTIMIZATION_SAMPLES,
    items: int = OPTIMIZATION_ITEMS,
    weights: np.ndarray | None = None,
    preserve_thesis_quirks: bool = False,
    n_jobs: int = 1,
    costs: CostParameters | None = None,
    fed_atom_economy: bool = False,
) -> PolicyEvaluation:
    """Evaluate one policy over a common-random-number Monte Carlo batch.

    Args:
        policy: Operating policy; None evaluates the baseline (thesis draws).
        base_seed: Base seed; the i-th sample uses the i-th spawned child seed regardless of the policy.
        n_samples: Number of Monte Carlo samples.
        items: Steel pieces simulated per sample year.
        weights: Indicator weights, length 18; thesis Table 4-1 weights when None.
        preserve_thesis_quirks: Thesis-faithful mode when True; corrected (mass-conserving) mode when False.
        n_jobs: joblib workers; 1 runs serially in-process.
        costs: Cost scenario of the COM indicator; thesis prices in thesis mode, unit-corrected thesis prices otherwise.
        fed_atom_economy: Fed-basis atom economy for the acid units (see `compute_greenscope`).

    Returns:
        Per-sample distributions of the objectives and constraint quantities.
    """
    weight_vector = thesis_indicator_weights() if weights is None else np.asarray(weights, dtype=float)
    seeds = sample_seeds(base_seed, n_samples)
    if n_jobs == 1:
        rows = [
            _evaluate_sample(policy, seed, items, weight_vector, preserve_thesis_quirks, costs, fed_atom_economy)
            for seed in seeds
        ]
    else:
        parallel_rows = Parallel(n_jobs=n_jobs)(
            delayed(_evaluate_sample)(policy, seed, items, weight_vector, preserve_thesis_quirks, costs, fed_atom_economy)
            for seed in seeds
        )
        rows = cast(list[dict[str, np.ndarray | float]], list(parallel_rows))
    return _stack(rows)


def _evaluate_sample(
    policy: OperatingPolicy | None,
    seed: np.random.SeedSequence,
    items: int,
    weights: np.ndarray,
    preserve_thesis_quirks: bool,
    costs: CostParameters | None,
    fed_atom_economy: bool = False,
) -> dict[str, np.ndarray | float]:
    rng = np.random.default_rng(seed)
    year = simulate_year(items, rng, preserve_thesis_quirks, policy)
    evaluation, greenscope = evaluate_year_detailed(year, weights, preserve_thesis_quirks, costs, fed_atom_economy)
    return {
        "process_utility": evaluation.process_utility,
        "quality_utility_pct": evaluation.quality_utility_pct,
        "mean_standard_thickness_um": evaluation.mean_standard_thickness_um,
        "process_scores": evaluation.process_scores,
        "unit_indicators": greenscope.indicators,
        "unit_scores": greenscope.score,
        "defect_fraction": year.totals.n_defective_pieces / year.totals.n_quality_pieces,
        "mean_coating_thickness_um": year.totals.thickness_sum_um / year.totals.n_quality_pieces,
        "peak_pickling_fe2_g_per_l": year.totals.peak_pickling_fe2_g_per_l,
        "peak_fluxing_fe2_g_per_l": year.totals.peak_fluxing_fe2_g_per_l,
        "raw_material_masses_kg": raw_material_masses_kg(build_balance(year).input_streams),
    }


def _stack(rows: list[dict[str, np.ndarray | float]]) -> PolicyEvaluation:
    return PolicyEvaluation(**{item.name: np.array([row[item.name] for row in rows]) for item in fields(PolicyEvaluation)})
