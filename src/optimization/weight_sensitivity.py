"""Sensitivity of the fuzzy compromise to the objective weights.

Purpose: the Pareto front does not depend on the weights, only the selected design does; this reports how stable the
selection is under alternative weighting schemes and a random sweep over the weight simplex (spec
optimization/mcdm-selection); entry point `python -m src.optimization.weight_sensitivity`.
Author: Jose D. Hernandez-Betancur
Date: 2026-10-03
"""

import argparse
import json
import logging
from pathlib import Path
from typing import Any, Final

import numpy as np

from src.optimization.mcdm import fuzzy_memberships, objective_weights_from_fahp, pareto_mask
from src.sustainability.greenscope import Indicator
from src.sustainability.thesis_weights import thesis_indicator_weights

logger = logging.getLogger(__name__)

N_OBJECTIVES: Final = 4
DEFAULT_DRAWS: Final = 10_000
DEFAULT_OUT_DIR: Final = "results/sensitivity"
OBJECTIVE_NAMES: Final = ("U_P", "COM", "V_l-poll", "V_WT")


def equal_weights() -> np.ndarray:
    """Equal weight on the four objectives.

    Returns:
        Weights of shape (4,).
    """
    return np.full(N_OBJECTIVES, 1.0 / N_OBJECTIVES)


def indicator_level_weights() -> np.ndarray:
    """Weights of the three indicators taken one by one from the thesis table, U_P carrying the remainder.

    Returns:
        Weights [U_P, COM, V_l-poll, V_WT] of shape (4,), summing to 1.
    """
    indicator_weights = thesis_indicator_weights()
    com = indicator_weights[Indicator.MANUFACTURING_COST]
    polluted = indicator_weights[Indicator.POLLUTED_LIQUID_VOLUME]
    water = indicator_weights[Indicator.WATER_CONSUMPTION]
    return np.array([1.0 - com - polluted - water, com, polluted, water])


def named_schemes() -> dict[str, np.ndarray]:
    """Weighting schemes compared with the selected one.

    Returns:
        Scheme name to weights; `category_mapped` is the default of the selection.
    """
    return {
        "category_mapped": objective_weights_from_fahp(),
        "indicator_level": indicator_level_weights(),
        "equal": equal_weights(),
    }


def selection_for_weights(memberships: np.ndarray, weights: np.ndarray) -> int:
    """Index of the design with the highest weighted membership.

    Args:
        memberships: Fuzzy memberships of the front, shape (n, 4).
        weights: Objective weights, shape (4,).

    Returns:
        Row index of the best compromise.
    """
    return int(np.argmax(memberships @ (weights / weights.sum())))


def random_sweep(memberships: np.ndarray, rng: np.random.Generator, n_draws: int = DEFAULT_DRAWS) -> np.ndarray:
    """Selection counts over weight vectors drawn uniformly from the simplex.

    Args:
        memberships: Fuzzy memberships of the front, shape (n, 4).
        rng: Random generator.
        n_draws: Number of weight vectors.

    Returns:
        Number of draws that select each front design, shape (n,).
    """
    draws = rng.dirichlet(np.ones(N_OBJECTIVES), size=n_draws)
    chosen = np.argmax(draws @ memberships.T, axis=1)
    return np.bincount(chosen, minlength=memberships.shape[0])


def analyze_weights(
    x: np.ndarray, objectives: np.ndarray, rng: np.random.Generator, n_draws: int = DEFAULT_DRAWS
) -> dict[str, Any]:
    """Weight sensitivity of the compromise on a set of designs.

    Args:
        x: Decision matrix, shape (n, 7).
        objectives: Objective matrix, shape (n, 4), minimization.
        rng: Random generator for the sweep.
        n_draws: Number of random weight vectors.

    Returns:
        Selected design per named scheme, plus the random-sweep selection frequencies and the spread of the
        selected designs in objective space relative to the front's range.
    """
    mask = pareto_mask(objectives)
    front_x, front_f = np.asarray(x, dtype=float)[mask], np.asarray(objectives, dtype=float)[mask]
    memberships, utopia, nadir = fuzzy_memberships(front_f)
    schemes = {name: _scheme_report(memberships, front_x, front_f, weights) for name, weights in named_schemes().items()}
    counts = random_sweep(memberships, rng, n_draws)
    return {
        "n_front": int(mask.sum()),
        "schemes": schemes,
        "sweep": _sweep_report(counts, front_x, front_f, utopia, nadir, n_draws, schemes["category_mapped"]["index"]),
    }


def _scheme_report(memberships: np.ndarray, x: np.ndarray, f: np.ndarray, weights: np.ndarray) -> dict[str, Any]:
    index = selection_for_weights(memberships, weights)
    return {
        "weights": dict(zip(OBJECTIVE_NAMES, (weights / weights.sum()).tolist())),
        "index": index,
        "x": x[index].tolist(),
        "f": f[index].tolist(),
    }


def _sweep_report(
    counts: np.ndarray,
    x: np.ndarray,
    f: np.ndarray,
    utopia: np.ndarray,
    nadir: np.ndarray,
    n_draws: int,
    default_index: int,
) -> dict[str, Any]:
    selected = np.flatnonzero(counts)
    span = np.where(nadir - utopia > 0, nadir - utopia, 1.0)
    return {
        "n_draws": n_draws,
        "n_distinct_selected": int(selected.size),
        "share_selecting_default": float(counts[default_index] / n_draws),
        "most_selected_index": int(np.argmax(counts)),
        "most_selected_share": float(counts.max() / n_draws),
        "selected_x_min": x[selected].min(axis=0).tolist(),
        "selected_x_max": x[selected].max(axis=0).tolist(),
        "selected_f_range_fraction_of_front": ((f[selected].max(axis=0) - f[selected].min(axis=0)) / span).tolist(),
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Weight sensitivity of the fuzzy compromise")
    parser.add_argument("--mc-dir", type=Path, default=Path("results/mc"), help="Directory with front.npz")
    parser.add_argument("--out-dir", type=Path, default=Path(DEFAULT_OUT_DIR))
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--draws", type=int, default=DEFAULT_DRAWS)
    return parser.parse_args()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    arguments = _parse_args()
    with np.load(arguments.mc_dir / "front.npz") as data:
        feasible = data["eligible"] if "eligible" in data.files else (data["g"] <= 0).all(axis=1)
        report = analyze_weights(
            data["x"][feasible], data["f"][feasible], np.random.default_rng(arguments.seed), arguments.draws
        )
    arguments.out_dir.mkdir(parents=True, exist_ok=True)
    (arguments.out_dir / "weight_sensitivity.json").write_text(json.dumps(report, indent=2))
