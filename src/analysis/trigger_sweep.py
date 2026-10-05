"""One-dimensional parametric study of the pickling renewal trigger at the reporting budget.

Purpose: show the trade-off behind decision variable 8 directly (spent-acid volume and cost versus rust
conversion, flux contamination and utility) by sweeping the Fe2+ renewal trigger with every other
condition at its thesis-nominal value; entry point `python -m src.analysis.trigger_sweep`.
Author: Jose D. Hernandez-Betancur
Date: 2026-10-05
"""

import argparse
import json
import logging
from dataclasses import replace
from pathlib import Path
from typing import Any, Final

import numpy as np

from src.optimization.evaluation import FULL_YEAR_ITEMS, PolicyEvaluation, evaluate_policy
from src.optimization.mcdm import sustainability_probability, utility_pct
from src.process.operating_policy import BASELINE_POLICY, POLICY_BOUNDS
from src.sustainability.costs import COST_SCENARIOS, CostParameters, get_cost_scenario
from src.sustainability.greenscope import Indicator
from src.sustainability.streams import UnitProcess

logger = logging.getLogger(__name__)

DEFAULT_OUT_DIR: Final = "results/sweeps"
DEFAULT_N_TRIGGERS: Final = 16
SWEEP_SAMPLES: Final = 100


def default_triggers(n_points: int = DEFAULT_N_TRIGGERS) -> np.ndarray:
    """Evenly spaced trigger values over the decision-variable bounds.

    Args:
        n_points: Number of trigger values.

    Returns:
        Array of Fe2+ triggers [g/L], shape (n_points,).
    """
    lower, upper = POLICY_BOUNDS["pickling_renewal_fe_g_per_l"]
    return np.linspace(lower, upper, n_points)


def sweep_renewal_trigger(
    triggers: np.ndarray,
    base_seed: int = 0,
    n_samples: int = SWEEP_SAMPLES,
    items: int = FULL_YEAR_ITEMS,
    n_jobs: int = 1,
    costs: CostParameters | None = None,
    fed_atom_economy: bool = False,
) -> dict[str, np.ndarray]:
    """Evaluate the thesis-nominal policy for each renewal trigger under common random numbers.

    Args:
        triggers: Fe2+ renewal triggers [g/L].
        base_seed: Common-random-number base seed shared by every trigger.
        n_samples: Monte Carlo samples per trigger.
        items: Steel pieces per simulated year.
        n_jobs: joblib workers.
        costs: Cost scenario of the COM indicator; the corrected-mode default when None.
        fed_atom_economy: Fed-basis atom economy for the pickling unit (instrument sensitivity).

    Returns:
        Per-trigger means (and standard deviations where meaningful) of the headline quantities, each of
        shape (n_triggers,), under keys such as `utility_pct`, `com_usd`, `polluted_liquid_m3`,
        `water_intake_m3`, `defect_fraction`, `peak_pickling_fe2_g_per_l`, `pickling_atom_economy_score`,
        `fluxing_atom_economy_score`, `hcl_purchased_t` and `p_sustainable`, plus `triggers`.
    """
    rows = []
    for trigger in np.asarray(triggers, dtype=float):
        policy = replace(BASELINE_POLICY, pickling_renewal_fe_g_per_l=float(trigger))
        logger.info("Sweep: trigger %.1f g/L", trigger)
        evaluation = evaluate_policy(
            policy, base_seed, n_samples, items, n_jobs=n_jobs, costs=costs, fed_atom_economy=fed_atom_economy
        )
        rows.append(_headline(evaluation))
    result = {key: np.array([row[key] for row in rows]) for key in rows[0]}
    result["triggers"] = np.asarray(triggers, dtype=float)
    return result


def _headline(evaluation: PolicyEvaluation) -> dict[str, float]:
    scores = evaluation.unit_scores.mean(axis=0)
    return {
        "utility_pct": float(utility_pct(evaluation).mean()),
        "utility_pct_std": float(utility_pct(evaluation).std(ddof=1)),
        "com_usd": float(evaluation.com_usd.mean()),
        "polluted_liquid_m3": float(evaluation.polluted_liquid_m3.mean()),
        "water_intake_m3": float(evaluation.water_intake_m3.mean()),
        "defect_fraction": float(evaluation.defect_fraction.mean()),
        "peak_pickling_fe2_g_per_l": float(evaluation.peak_pickling_fe2_g_per_l.mean()),
        "peak_fluxing_fe2_g_per_l": float(evaluation.peak_fluxing_fe2_g_per_l.mean()),
        "pickling_atom_economy_score": float(scores[UnitProcess.PICKLING, Indicator.ATOM_ECONOMY]),
        "fluxing_atom_economy_score": float(scores[UnitProcess.FLUXING, Indicator.ATOM_ECONOMY]),
        "hcl_purchased_t": float(evaluation.raw_material_masses_kg[:, 1].mean() / 1e3),
        "p_sustainable": sustainability_probability(evaluation),
    }


def save_sweep(result: dict[str, np.ndarray], out_dir: Path, name: str = "trigger_sweep") -> None:
    """Persist a sweep as `.npz` plus a readable JSON table.

    Args:
        result: Output of `sweep_renewal_trigger`.
        out_dir: Destination directory.
        name: File stem.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    arrays: dict[str, Any] = dict(result)
    np.savez_compressed(out_dir / f"{name}.npz", **arrays)
    table: dict[str, Any] = {key: value.tolist() for key, value in result.items()}
    (out_dir / f"{name}.json").write_text(json.dumps(table, indent=2))


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Parametric sweep of the pickling renewal trigger")
    parser.add_argument("--out-dir", type=Path, default=Path(DEFAULT_OUT_DIR))
    parser.add_argument("--n-triggers", type=int, default=DEFAULT_N_TRIGGERS)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--n-samples", type=int, default=SWEEP_SAMPLES)
    parser.add_argument("--items", type=int, default=FULL_YEAR_ITEMS)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--cost-scenario", type=str, default="market2025", choices=sorted(COST_SCENARIOS))
    parser.add_argument("--fed-atom-economy", action="store_true")
    return parser.parse_args()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    arguments = _parse_args()
    sweep = sweep_renewal_trigger(
        default_triggers(arguments.n_triggers),
        arguments.seed,
        arguments.n_samples,
        arguments.items,
        arguments.workers,
        get_cost_scenario(arguments.cost_scenario),
        arguments.fed_atom_economy,
    )
    save_sweep(sweep, arguments.out_dir, "trigger_sweep_fedae" if arguments.fed_atom_economy else "trigger_sweep")
