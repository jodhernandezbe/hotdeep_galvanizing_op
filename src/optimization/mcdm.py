"""Fuzzy compromise decision-making over the Pareto front and deep design characterization.

Purpose: select the best-compromise operating point with FAHP-derived weights and run the deep Monte Carlo
comparison of baseline vs. optimum (spec optimization/mcdm-selection); entry point `python -m src.optimization.mcdm`.
Author: Jose D. Hernandez-Betancur
Date: 2026-10-02
"""

import argparse
import json
import logging
from dataclasses import dataclass, fields
from pathlib import Path
from typing import Final

import numpy as np
from pymoo.util.nds.non_dominated_sorting import NonDominatedSorting
from scipy.stats import t as student_t

from src.analysis.critical_points import assess_sustainability
from src.optimization.evaluation import DEEP_SAMPLES, FULL_YEAR_ITEMS, PolicyEvaluation, evaluate_policy
from src.optimization.front_evaluation import reevaluate_front
from src.optimization.run_nsga2 import load_checkpoint
from src.process.operating_policy import BASELINE_POLICY, OperatingPolicy
from src.sustainability.costs import COST_SCENARIOS, CostParameters, default_costs, get_cost_scenario
from src.sustainability.thesis_weights import CATEGORY_WEIGHTS, thesis_indicator_weights
from src.sustainability.utility import QUALITY_WEIGHT_INDEX

logger = logging.getLogger(__name__)

SUSTAINABILITY_THRESHOLD_PCT: Final = 80.0
CONFIDENCE_LEVEL: Final = 0.95
PERCENT: Final = 100.0
_DEGENERATE_EPS: Final = 1e-12
_ENVIRONMENT, _EFFICIENCY, _ENERGY, _ECONOMY, _QUALITY = range(5)


@dataclass(frozen=True)
class CompromiseResult:
    """Best fuzzy compromise of a Pareto front.

    Attributes:
        index: Position of the compromise in the non-dominated subset.
        x: Decision vector of the compromise, shape (7,).
        f: Objective vector of the compromise, shape (4,).
        memberships: Fuzzy satisfaction mu_k of the compromise per objective, shape (4,).
        overall: Weighted additive score sum_k W_k mu_k.
        utopia: Best value of each objective on the front, shape (4,).
        nadir: Worst value of each objective on the front, shape (4,).
    """

    index: int
    x: np.ndarray
    f: np.ndarray
    memberships: np.ndarray
    overall: float
    utopia: np.ndarray
    nadir: np.ndarray


def pareto_mask(objectives: np.ndarray) -> np.ndarray:
    """Boolean mask of the non-dominated solutions (minimization).

    Args:
        objectives: Objective matrix, shape (n, k).

    Returns:
        Mask of shape (n,).
    """
    front = NonDominatedSorting().do(np.asarray(objectives, dtype=float), only_non_dominated_front=True)
    mask = np.zeros(len(objectives), dtype=bool)
    mask[front] = True
    return mask


def fuzzy_memberships(objectives: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Linear satisfaction memberships on the utopia-nadir range of each objective.

    Args:
        objectives: Non-dominated objective matrix, shape (n, k), minimization.

    Returns:
        Memberships (n, k) in [0, 1], the utopia point (k,) and the nadir point (k,). A degenerate
        objective (utopia == nadir) contributes a constant membership of 1.
    """
    front = np.asarray(objectives, dtype=float)
    utopia, nadir = front.min(axis=0), front.max(axis=0)
    span = nadir - utopia
    memberships = np.where(span > _DEGENERATE_EPS, (nadir - front) / np.where(span > 0, span, 1.0), 1.0)
    return np.clip(memberships, 0.0, 1.0), utopia, nadir


def objective_weights_from_fahp() -> np.ndarray:
    """FAHP category weights mapped onto the four objectives.

    U_P carries the efficiency + energy + quality shares, COM the economy share, and V_l-poll / V_WT split
    the environment share equally; renormalized to sum to 1. This mapping is a documented modeling choice
    (design D7) and callers may override it.

    Returns:
        Weights [W_UP, W_COM, W_Vlpoll, W_VWT], shape (4,).
    """
    categories = CATEGORY_WEIGHTS
    weights = np.array(
        [
            categories[_EFFICIENCY] + categories[_ENERGY] + categories[_QUALITY],
            categories[_ECONOMY],
            categories[_ENVIRONMENT] / 2,
            categories[_ENVIRONMENT] / 2,
        ]
    )
    return weights / weights.sum()


def select_compromise(x: np.ndarray, objectives: np.ndarray, weights: np.ndarray | None = None) -> CompromiseResult:
    """Pick the best fuzzy compromise from a solution set.

    Args:
        x: Decision matrix, shape (n, 7).
        objectives: Objective matrix, shape (n, 4), minimization.
        weights: Objective weights, shape (4,); FAHP-derived defaults when None.

    Returns:
        The compromise solution with its memberships and the front's utopia/nadir points.
    """
    weight_vector = objective_weights_from_fahp() if weights is None else np.asarray(weights, dtype=float)
    mask = pareto_mask(objectives)
    front_x, front_f = np.asarray(x, dtype=float)[mask], np.asarray(objectives, dtype=float)[mask]
    memberships, utopia, nadir = fuzzy_memberships(front_f)
    overall = memberships @ (weight_vector / weight_vector.sum())
    best = int(np.argmax(overall))
    return CompromiseResult(
        index=best,
        x=front_x[best],
        f=front_f[best],
        memberships=memberships[best],
        overall=float(overall[best]),
        utopia=utopia,
        nadir=nadir,
    )


def utility_pct(evaluation: PolicyEvaluation, quality_weight: float | None = None) -> np.ndarray:
    """Process utility normalized by its per-sample maximum [%].

    Args:
        evaluation: Monte Carlo batch.
        quality_weight: Quality category weight; thesis value when None.

    Returns:
        U_P as a percentage of the attainable maximum, shape (n,).
    """
    weight = thesis_indicator_weights()[QUALITY_WEIGHT_INDEX] if quality_weight is None else quality_weight
    utility_max = evaluation.mean_standard_thickness_um * PERCENT / weight
    return evaluation.process_utility / utility_max * PERCENT


def sustainability_probability(evaluation: PolicyEvaluation, quality_weight: float | None = None) -> float:
    """P(LM_P <= U_P <= U_max) under the thesis' assumed normal (annex D.4, `assess_sustainability`).

    The thesis models U_P as Normal(mean, (U_max - mean)/3) and integrates between LM_P = 0.8 U_max and
    U_max; the validated 0.4526 of chapter 4 uses this construct. The empirical year-to-year spread of
    U_P/U_max is two orders of magnitude narrower than the assumed one, so the empirical exceedance
    fraction is degenerate (see `empirical_sustainability_probability`).

    Args:
        evaluation: Monte Carlo batch.
        quality_weight: Quality category weight; thesis value when None.

    Returns:
        Probability of the sustainability band under the thesis' normal assumption.
    """
    weight = thesis_indicator_weights()[QUALITY_WEIGHT_INDEX] if quality_weight is None else quality_weight
    return assess_sustainability(evaluation.process_utility, evaluation.mean_standard_thickness_um, weight).probability


def empirical_sustainability_probability(evaluation: PolicyEvaluation, quality_weight: float | None = None) -> float:
    """Empirical P(U_P >= LM_P) with a per-sample LM_P = 80 % of that sample's attainable maximum.

    Args:
        evaluation: Monte Carlo batch.
        quality_weight: Quality category weight; thesis value when None.

    Returns:
        Fraction of samples at or above the sustainability threshold.
    """
    return float(np.mean(utility_pct(evaluation, quality_weight) >= SUSTAINABILITY_THRESHOLD_PCT))


def confidence_interval(values: np.ndarray, level: float = CONFIDENCE_LEVEL) -> tuple[float, float]:
    """Student-t confidence interval of the mean.

    Args:
        values: Samples, shape (n,).
        level: Confidence level.

    Returns:
        (lower, upper) bounds of the mean.
    """
    data = np.asarray(values, dtype=float)
    half = float(student_t.ppf(1 - (1 - level) / 2, data.size - 1)) * data.std(ddof=1) / np.sqrt(data.size)
    return float(data.mean() - half), float(data.mean() + half)


def characterize_designs(
    optimal: OperatingPolicy,
    baseline: OperatingPolicy = BASELINE_POLICY,
    base_seed: int = 0,
    n_samples: int = DEEP_SAMPLES,
    items: int = FULL_YEAR_ITEMS,
    n_jobs: int = 1,
    out_dir: Path = Path("results/mc"),
    costs: CostParameters | None = None,
) -> dict[str, PolicyEvaluation]:
    """Deep paired Monte Carlo characterization of the as-is operation and the fixed designs.

    Three designs: "asis" is the thesis' stochastic operation (no fixed policy: every controllable
    condition keeps its thesis draw, the plant as it runs today), "baseline" holds every condition
    at its thesis-nominal value, and "optimal" is the compromise policy.

    Args:
        optimal: Compromise policy from the MCDM selection.
        baseline: Baseline policy (thesis-nominal operating point by default).
        base_seed: Common-random-number base seed shared by the designs.
        n_samples: Samples per design.
        items: Steel pieces per simulated year.
        n_jobs: joblib workers.
        out_dir: Directory receiving `asis.npz`, `baseline.npz`, `optimal.npz` and `summary.json`.
        costs: Cost scenario of the COM indicator; the corrected-mode default when None.

    Returns:
        The three evaluations keyed by design name.
    """
    designs: dict[str, OperatingPolicy | None] = {"asis": None, "baseline": baseline, "optimal": optimal}
    evaluations: dict[str, PolicyEvaluation] = {}
    for name, policy in designs.items():
        logger.info("Deep Monte Carlo (%s): n=%d, items=%d", name, n_samples, items)
        evaluations[name] = evaluate_policy(policy, base_seed, n_samples, items, n_jobs=n_jobs, costs=costs)
        evaluations[name].save(out_dir / f"{name}.npz")
    _write_summary(out_dir, designs, evaluations, default_costs(False) if costs is None else costs)
    return evaluations


def _headline_stats(evaluation: PolicyEvaluation) -> dict[str, dict[str, float]]:
    series = {
        "utility_pct": utility_pct(evaluation),
        "com_usd": evaluation.com_usd,
        "polluted_liquid_m3": evaluation.polluted_liquid_m3,
        "water_intake_m3": evaluation.water_intake_m3,
        "mean_coating_thickness_um": evaluation.mean_coating_thickness_um,
        "defect_fraction": evaluation.defect_fraction,
    }
    return {name: _series_stats(values) for name, values in series.items()}


def _series_stats(values: np.ndarray) -> dict[str, float]:
    lower, upper = confidence_interval(values)
    return {"mean": float(values.mean()), "std": float(values.std(ddof=1)), "ci_lower": lower, "ci_upper": upper}


def _write_summary(
    out_dir: Path,
    designs: dict[str, OperatingPolicy | None],
    evaluations: dict[str, PolicyEvaluation],
    costs: CostParameters,
) -> None:
    summary: dict[str, object] = {"cost_scenario": costs.name}
    summary |= {
        name: {
            "policy": None if policy is None else {field.name: float(getattr(policy, field.name)) for field in fields(policy)},
            "p_sustainable": sustainability_probability(evaluations[name]),
            "p_sustainable_empirical": empirical_sustainability_probability(evaluations[name]),
            "indicators": _headline_stats(evaluations[name]),
        }
        for name, policy in designs.items()
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2))


def prepare_selection(
    run_dir: Path,
    out_dir: Path,
    front_items: int = FULL_YEAR_ITEMS,
    n_jobs: int = 1,
    weights: np.ndarray | None = None,
    cost_scenario: str | None = None,
) -> CompromiseResult:
    """Re-evaluate the front at the reporting budget and select the compromise among its feasible designs.

    The search runs on a reduced simulated year whose fixed annual costs do not scale with the pieces, so objectives
    are only comparable with the deep Monte Carlo after re-evaluation at the reporting (full-year) budget.

    Args:
        run_dir: NSGA-II run directory.
        out_dir: Directory receiving `front.npz` and `compromise.npz`.
        front_items: Steel pieces per simulated year used to re-evaluate the front.
        n_jobs: joblib workers.
        weights: Objective weights; FAHP-derived defaults when None.
        cost_scenario: Cost scenario of the re-evaluation; the one the search used when None.

    Returns:
        The compromise computed on the re-evaluated front.

    Raises:
        ValueError: If no re-evaluated design satisfies the constraints.
    """
    checkpoint = load_checkpoint(run_dir)
    config, x = checkpoint["config"], np.atleast_2d(checkpoint["opt_X"])
    scenario = cost_scenario or config["cost_scenario"]
    objectives, constraints, masses = reevaluate_front(x, scenario, config["seed"], config["n_mc_samples"], front_items, n_jobs)
    feasible = (constraints[:-1] <= 0).all(axis=1)
    if not feasible.any():
        message = f"No design of the front is feasible at {front_items} items per year"
        logger.error(message)
        raise ValueError(message)
    _save_front(out_dir, x, objectives, constraints, masses, front_items, scenario)
    compromise = select_compromise(x[feasible], objectives[:-1][feasible], weights)
    _save_compromise(out_dir, compromise)
    return compromise


def _save_front(
    out_dir: Path,
    x: np.ndarray,
    objectives: np.ndarray,
    constraints: np.ndarray,
    masses: np.ndarray,
    items: int,
    scenario: str = "",
) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        out_dir / "front.npz",
        x=x,
        f=objectives[:-1],
        g=constraints[:-1],
        raw_material_masses_kg=masses[:-1],
        baseline_f=objectives[-1],
        baseline_g=constraints[-1],
        baseline_raw_material_masses_kg=masses[-1],
        items=items,
        cost_scenario=scenario,
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fuzzy compromise selection and deep Monte Carlo characterization")
    parser.add_argument("--run-dir", type=Path, required=True, help="NSGA-II run directory (results/checkpoints/...)")
    parser.add_argument("--out-dir", type=Path, default=Path("results/mc"))
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--n-samples", type=int, default=DEEP_SAMPLES)
    parser.add_argument("--items", type=int, default=FULL_YEAR_ITEMS)
    parser.add_argument("--front-items", type=int, default=FULL_YEAR_ITEMS)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--cost-scenario", type=str, default=None, choices=sorted(COST_SCENARIOS))
    return parser.parse_args()


def main() -> None:
    """Select the compromise from a finished run and characterize baseline vs. optimum."""
    args = _parse_args()
    config = load_checkpoint(args.run_dir)["config"]
    scenario = args.cost_scenario or config["cost_scenario"]
    compromise = prepare_selection(args.run_dir, args.out_dir, args.front_items, args.workers, cost_scenario=scenario)
    logger.info("Compromise: x=%s, f=%s, mu=%.4f", compromise.x, compromise.f, compromise.overall)
    characterize_designs(
        OperatingPolicy.from_array(compromise.x),
        base_seed=args.seed,
        n_samples=args.n_samples,
        items=args.items,
        n_jobs=args.workers,
        out_dir=args.out_dir,
        costs=get_cost_scenario(scenario),
    )


def _save_compromise(out_dir: Path, compromise: CompromiseResult) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        out_dir / "compromise.npz",
        x=compromise.x,
        f=compromise.f,
        memberships=compromise.memberships,
        overall=compromise.overall,
        utopia=compromise.utopia,
        nadir=compromise.nadir,
        weights=objective_weights_from_fahp(),
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    main()
