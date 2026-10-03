"""Price-scenario sensitivity of the Pareto front and of the compromise design.

Purpose: recompute the cost objective of the re-evaluated (full-year) front under each cost scenario and report
whether the best compromise and the baseline-vs-optimum cost saving change (spec optimization/mcdm-selection);
entry point `python -m src.optimization.price_sensitivity`. Prices enter the model only through the raw-material
part of COM (the GREENSCOPE scores are price-invariant), so the recomputation from the stored raw-material masses
is exact and needs no new simulation.
Author: Jose D. Hernandez-Betancur
Date: 2026-10-03
"""

import argparse
import json
import logging
from pathlib import Path
from typing import Any, Final

import numpy as np
from scipy.stats import spearmanr

from src.optimization.mcdm import CompromiseResult, select_compromise
from src.sustainability.costs import (
    COST_SCENARIOS,
    RAW_MATERIAL_COM_FACTOR,
    CostParameters,
    get_cost_scenario,
    raw_material_price_delta,
)

logger = logging.getLogger(__name__)

COM_COLUMN: Final = 1
DEFAULT_FRONT: Final = "results/mc/front.npz"
DEFAULT_OUT_DIR: Final = "results/sensitivity"


def shift_com(objectives: np.ndarray, masses: np.ndarray, reference: CostParameters, scenario: CostParameters) -> np.ndarray:
    """Objectives with the cost column moved from one price scenario to another.

    COM = 0.280 FCI + 2.73 COL + 1.23 (CRM + CUT + CWT) and only CRM depends on the raw-material
    prices, linearly through the purchased masses, so the exact COM of another scenario is the
    reference COM plus `1.23e-3 * (prices_scenario - prices_reference) @ masses`.

    Args:
        objectives: Objective matrix under the reference scenario, shape (n, 4).
        masses: Mean raw-material masses per `RAW_MATERIAL_KEYS` [kg], shape (n, 7).
        reference: Scenario the objectives were computed with.
        scenario: Scenario to move the cost column to.

    Returns:
        Objective matrix under `scenario`, shape (n, 4).

    Raises:
        ValueError: If the scenarios differ in a price outside the raw materials (water or labor),
            which the mass-based recomputation cannot absorb.
    """
    delta = raw_material_price_delta(reference, scenario)
    shifted = np.array(objectives, dtype=float, copy=True)
    shifted[..., COM_COLUMN] += RAW_MATERIAL_COM_FACTOR * np.atleast_2d(masses) @ delta
    return shifted


def _compromise_summary(
    x: np.ndarray, objectives: np.ndarray, baseline_f: np.ndarray
) -> tuple[CompromiseResult, dict[str, Any]]:
    result = select_compromise(x, objectives)
    saving_pct = 100.0 * (baseline_f[COM_COLUMN] - result.f[COM_COLUMN]) / baseline_f[COM_COLUMN]
    summary = {
        "compromise_x": result.x.tolist(),
        "compromise_f": result.f.tolist(),
        "compromise_overall_membership": result.overall,
        "baseline_f": baseline_f.tolist(),
        "com_saving_vs_baseline_pct": float(saving_pct),
    }
    return result, summary


def compare_scenarios(
    x: np.ndarray, objectives_by_scenario: dict[str, np.ndarray], baselines_by_scenario: dict[str, np.ndarray]
) -> dict[str, Any]:
    """Compare compromise designs and cost rankings across scenarios.

    Args:
        x: Decision matrix of the (feasible) front, shape (n, 7).
        objectives_by_scenario: Objective matrix per scenario, shape (n, 4) each; the first is the reference.
        baselines_by_scenario: Baseline objective vector per scenario, shape (4,) each.

    Returns:
        Per-scenario summaries plus the agreement of the compromise design and the COM rank correlation with
        the reference scenario.
    """
    names = list(objectives_by_scenario)
    results, summaries = {}, {}
    for name in names:
        results[name], summaries[name] = _compromise_summary(x, objectives_by_scenario[name], baselines_by_scenario[name])
    reference = names[0]
    agreement = {
        name: {
            "same_compromise_as_reference": bool(np.allclose(results[name].x, results[reference].x)),
            "com_rank_spearman_vs_reference": _rank_correlation(objectives_by_scenario, reference, name),
        }
        for name in names[1:]
    }
    return {"reference_scenario": reference, "scenarios": summaries, "agreement": agreement}


def _rank_correlation(objectives: dict[str, np.ndarray], reference: str, other: str) -> float:
    coefficient = spearmanr(objectives[reference][:, COM_COLUMN], objectives[other][:, COM_COLUMN])[0]
    return float(coefficient)


def run_sensitivity(front_path: Path, out_dir: Path, scenarios: tuple[str, ...]) -> dict[str, Any]:
    """Recompute the saved full-year front under each cost scenario and persist the comparison.

    Only the cost objective changes between scenarios (utility, polluted liquid, water intake and the
    constraints are price-invariant), so the comparison runs on the feasible designs of `front.npz`
    at the simulation budget it was saved with.

    Args:
        front_path: `front.npz` written by `mcdm.prepare_selection` (full-year re-evaluation).
        out_dir: Destination for `price_sensitivity.json` and `objectives.npz`.
        scenarios: Scenario names; the front's own scenario is always the reference.

    Returns:
        The comparison dictionary written to JSON.
    """
    front = np.load(front_path, allow_pickle=True)
    reference = get_cost_scenario(str(front["cost_scenario"]))
    feasible = (front["g"] <= 0).all(axis=1)
    x, f, masses = front["x"][feasible], front["f_mean"][feasible], front["raw_material_masses_kg"][feasible]
    names = [reference.name, *[name for name in scenarios if name != reference.name]]
    objectives = {name: shift_com(f, masses, reference, get_cost_scenario(name)) for name in names}
    baseline_f, baseline_masses = np.atleast_2d(front["baseline_f_mean"]), np.atleast_2d(
        front["baseline_raw_material_masses_kg"]
    )
    baselines = {name: shift_com(baseline_f, baseline_masses, reference, get_cost_scenario(name))[0] for name in names}
    comparison = compare_scenarios(x, objectives, baselines)
    comparison["items"] = int(front["items"])
    comparison["n_feasible"] = int(feasible.sum())
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "price_sensitivity.json").write_text(json.dumps(comparison, indent=2))
    arrays: dict[str, Any] = {"x": x, **objectives}
    np.savez_compressed(out_dir / "objectives.npz", **arrays)
    return comparison


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Cost-scenario sensitivity of the re-evaluated full-year front")
    parser.add_argument("--front", type=Path, default=Path(DEFAULT_FRONT))
    parser.add_argument("--out-dir", type=Path, default=Path(DEFAULT_OUT_DIR))
    parser.add_argument("--scenarios", nargs="+", default=sorted(COST_SCENARIOS))
    return parser.parse_args()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    arguments = _parse_args()
    run_sensitivity(arguments.front, arguments.out_dir, tuple(arguments.scenarios))
