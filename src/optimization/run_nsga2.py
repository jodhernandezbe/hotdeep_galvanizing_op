"""NSGA-II execution and checkpointing for the robust HDG optimization.

Purpose: assemble, run and persist the optimization (spec optimization/nsga2); entry point
`python -m src.optimization.run_nsga2`.
Author: Jose D. Hernandez-Betancur
Date: 2026-10-02
"""

import argparse
import json
import logging
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Final, cast

import numpy as np
from pymoo.algorithms.moo.nsga2 import NSGA2
from pymoo.core.callback import Callback
from pymoo.core.population import Population
from pymoo.operators.crossover.sbx import SBX
from pymoo.operators.mutation.pm import PM
from pymoo.operators.sampling.lhs import LHS
from pymoo.optimize import minimize

from src.optimization.evaluation import OPTIMIZATION_ITEMS, OPTIMIZATION_SAMPLES
from src.optimization.problem import HdgRobustProblem
from src.optimization.termination import (
    DEFAULT_HV_TOLERANCE,
    DEFAULT_HV_WINDOW,
    DEFAULT_MIN_GENERATIONS,
    HypervolumeStagnation,
)
from src.sustainability.costs import COST_SCENARIOS, THESIS_CORRECTED_COSTS, get_cost_scenario

logger = logging.getLogger(__name__)

DEFAULT_POP_SIZE: Final = 100
DEFAULT_GENERATIONS: Final = 150
DEFAULT_CHECKPOINT_EVERY: Final = 5
DEFAULT_OUTPUT_DIR: Final = "results/checkpoints"
CONFIG_FILENAME: Final = "config.json"
FINAL_FILENAME: Final = "final.npz"
RESUME_LATEST: Final = "latest"
RESUME_HV_TOLERANCE: Final = 1e-9
EVALUATED_ATTRIBUTES: Final = frozenset({"F", "G", "H", "CV", "FEAS", "dF", "dG", "dH", "ddF", "ddG", "ddH"})


@dataclass(frozen=True)
class RunConfig:
    """Configuration of one NSGA-II run (persisted as `config.json`).

    Attributes:
        seed: Seed of the evolutionary algorithm and of the Monte Carlo batches.
        pop_size: Population size (equals the offspring count).
        n_generations: Generation budget.
        hv_tolerance: Relative hypervolume-stagnation tolerance.
        hv_window: Stagnation window [generations].
        min_generations: Generations before stagnation may stop the run.
        n_mc_samples: Monte Carlo samples per candidate evaluation.
        items: Steel pieces per simulated year.
        n_jobs: joblib workers.
        checkpoint_every: Checkpoint interval [generations].
        out_dir: Run directory.
        cost_scenario: Name of the COM cost scenario (`thesis_corrected`, `thesis` or `market2025`).
        fed_atom_economy: Fed-basis atom economy for the acid units (instrument sensitivity; see `compute_greenscope`).
        resume_from: Checkpoint to continue from (file name in the run directory, or `latest`); empty starts afresh.
    """

    seed: int = 0
    pop_size: int = DEFAULT_POP_SIZE
    n_generations: int = DEFAULT_GENERATIONS
    hv_tolerance: float = DEFAULT_HV_TOLERANCE
    hv_window: int = DEFAULT_HV_WINDOW
    min_generations: int = DEFAULT_MIN_GENERATIONS
    n_mc_samples: int = OPTIMIZATION_SAMPLES
    items: int = OPTIMIZATION_ITEMS
    n_jobs: int = 1
    checkpoint_every: int = DEFAULT_CHECKPOINT_EVERY
    out_dir: str = DEFAULT_OUTPUT_DIR
    cost_scenario: str = THESIS_CORRECTED_COSTS.name
    fed_atom_economy: bool = False
    resume_from: str = ""


@dataclass(frozen=True)
class ResumeState:
    """State read from a checkpoint to continue a run.

    Attributes:
        population: Evaluated population at the checkpoint (not re-evaluated).
        generation: Generation of the checkpoint.
        n_evaluations: Evaluations spent up to the checkpoint.
        hv_history: Hypervolume of every generation up to the checkpoint.
    """

    population: Population
    generation: int
    n_evaluations: int
    hv_history: list[float]


class CheckpointCallback(Callback):
    """Persist the population to `.npz` files at a fixed generation interval."""

    def __init__(self, run_dir: Path, every: int, generation_offset: int = 0, previous_evaluations: int = 0) -> None:
        """Set the destination and cadence.

        Args:
            run_dir: Directory the checkpoints are written to.
            every: Interval in generations.
            generation_offset: Generations completed before this run (resume only).
            previous_evaluations: Evaluations spent before this run (resume only).
        """
        super().__init__()
        self.run_dir = run_dir
        self.every = every
        self.generation_offset = generation_offset
        self.previous_evaluations = previous_evaluations

    def notify(self, algorithm: Any) -> None:
        """Write a checkpoint when the generation hits the interval.

        Args:
            algorithm: The running pymoo algorithm.
        """
        generation = algorithm.n_gen + self.generation_offset
        if self.generation_offset and algorithm.n_gen == 1:
            return
        if generation % self.every == 0:
            path = self.run_dir / f"gen_{generation:04d}.npz"
            _save_population(path, algorithm, self.generation_offset, self.previous_evaluations)
            logger.info("Checkpoint written: %s", path)


def _save_population(path: Path, algorithm: Any, generation_offset: int = 0, previous_evaluations: int = 0) -> None:
    population, optimum = algorithm.pop, algorithm.opt
    hv_history = getattr(algorithm.termination, "hv_history", [])
    np.savez_compressed(
        path,
        X=population.get("X"),
        F=population.get("F"),
        G=population.get("G"),
        opt_X=optimum.get("X"),
        opt_F=optimum.get("F"),
        opt_G=optimum.get("G"),
        opt_feasible=optimum.get("feas"),
        n_gen=algorithm.n_gen + generation_offset,
        n_evals=algorithm.evaluator.n_eval + previous_evaluations,
        hv_history=np.asarray(hv_history, dtype=float),
    )


def build_algorithm(config: RunConfig, sampling: Population | None = None) -> NSGA2:
    """NSGA-II with the thesis-manuscript operator settings.

    Args:
        config: Run configuration.
        sampling: Evaluated population to start from (resume); Latin hypercube sampling when None.

    Returns:
        Configured algorithm (LHS sampling, SBX 0.9/15, PM 0.1/20).
    """
    return NSGA2(
        pop_size=config.pop_size,
        n_offsprings=config.pop_size,
        sampling=LHS() if sampling is None else sampling,  # pyright: ignore[reportArgumentType]
        crossover=SBX(prob=0.9, eta=15),
        mutation=PM(prob=0.1, eta=20),
    )


def run(config: RunConfig) -> Path:
    """Execute the optimization and persist config, checkpoints and the final state.

    Args:
        config: Run configuration; with `resume_from` set, the run continues from that checkpoint.

    Returns:
        The run directory containing `config.json`, `gen_*.npz` and `final.npz`.
    """
    run_dir = _prepare_run_dir(config)
    problem = HdgRobustProblem(
        config.n_mc_samples,
        config.items,
        config.seed,
        config.n_jobs,
        costs=get_cost_scenario(config.cost_scenario),
        fed_atom_economy=config.fed_atom_economy,
    )
    state = _resume_state(config, run_dir)
    offset, spent = (0, 0) if state is None else (state.generation - 1, state.n_evaluations)
    start = time.perf_counter()
    result = minimize(
        problem,
        build_algorithm(config, None if state is None else state.population),
        _build_termination(config, problem, state),
        seed=config.seed if state is None else config.seed + state.generation,
        callback=CheckpointCallback(run_dir, config.checkpoint_every, offset, spent),
        verbose=True,
    )
    _finalize_run(run_dir, config, result, time.perf_counter() - start, state)
    return run_dir


def _find_checkpoint(run_dir: Path, name: str) -> Path:
    if name != RESUME_LATEST:
        return run_dir / name
    candidates = sorted(run_dir.glob("gen_*.npz"))
    if not candidates:
        message = f"No gen_*.npz checkpoint to resume from in {run_dir}"
        logger.error(message)
        raise FileNotFoundError(message)
    return candidates[-1]


def load_resume_state(path: Path) -> ResumeState:
    """Read the population and history of a checkpoint so that the run can continue.

    Args:
        path: Checkpoint `.npz` written by a run.

    Returns:
        The resume state; the population is flagged as evaluated, so it is not simulated again.
    """
    with np.load(path) as data:
        population = Population.new(X=data["X"], F=data["F"], G=data["G"])
        state = ResumeState(population, int(data["n_gen"]), int(data["n_evals"]), data["hv_history"].tolist())
    for individual in population:
        individual.evaluated = set(EVALUATED_ATTRIBUTES)
    return state


def _resume_state(config: RunConfig, run_dir: Path) -> ResumeState | None:
    if not config.resume_from:
        return None
    return load_resume_state(_find_checkpoint(run_dir, config.resume_from))


def reproduce_normalization(
    problem: HdgRobustProblem, config: RunConfig, saved_first_hv: float
) -> tuple[np.ndarray, np.ndarray]:
    """Recover the ideal and nadir points of the first generation by repeating it with the original seed.

    Args:
        problem: The optimization problem of the run.
        config: Run configuration (seed and operators as in the original run).
        saved_first_hv: Hypervolume of generation 1 stored in the checkpoint, used to verify the reproduction.

    Returns:
        Ideal and nadir points of the first feasible generation.

    Raises:
        ValueError: If the reproduced first-generation hypervolume differs from the stored one.
    """
    probe = HypervolumeStagnation(1, config.hv_tolerance, config.hv_window, config.min_generations)
    result = minimize(problem, build_algorithm(config), probe, seed=config.seed, verbose=False)
    repeated = cast(HypervolumeStagnation, cast(Any, result).algorithm.termination)
    if repeated.normalization is None or abs(repeated.hv_history[0] - saved_first_hv) > RESUME_HV_TOLERANCE:
        message = "The first generation could not be reproduced; the saved hypervolume history does not match"
        logger.error(message)
        raise ValueError(message)
    return repeated.normalization


def _build_termination(config: RunConfig, problem: HdgRobustProblem, state: ResumeState | None) -> HypervolumeStagnation:
    settings = (config.n_generations, config.hv_tolerance, config.hv_window, config.min_generations)
    if state is None:
        return HypervolumeStagnation(*settings)
    return HypervolumeStagnation(
        *settings,
        generation_offset=state.generation - 1,
        hv_history=state.hv_history[: state.generation - 1],
        normalization=reproduce_normalization(problem, config, state.hv_history[0]),
    )


def _prepare_run_dir(config: RunConfig) -> Path:
    scenario = "" if config.cost_scenario == THESIS_CORRECTED_COSTS.name else f"_{config.cost_scenario}"
    instrument = "_fedae" if config.fed_atom_economy else ""
    run_dir = Path(config.out_dir) / f"nsga2{scenario}{instrument}_seed{config.seed}"
    run_dir.mkdir(parents=True, exist_ok=True)
    original = run_dir / "config_before_resume.json"
    if config.resume_from and not original.exists() and (run_dir / CONFIG_FILENAME).exists():
        original.write_text((run_dir / CONFIG_FILENAME).read_text())
    (run_dir / CONFIG_FILENAME).write_text(json.dumps(asdict(config), indent=2))
    return run_dir


def _finalize_run(run_dir: Path, config: RunConfig, result: Any, elapsed: float, state: ResumeState | None) -> None:
    termination = result.algorithm.termination
    offset, spent = (0, 0) if state is None else (state.generation - 1, state.n_evaluations)
    _save_population(run_dir / FINAL_FILENAME, result.algorithm, offset, spent)
    summary = {
        **asdict(config),
        "termination_reason": termination.reason,
        "n_generations_run": int(result.algorithm.n_gen + offset),
        "n_evaluations": int(result.algorithm.evaluator.n_eval + spent),
        "resumed_from_generation": None if state is None else state.generation,
        "elapsed_s": elapsed,
    }
    (run_dir / CONFIG_FILENAME).write_text(json.dumps(summary, indent=2))
    logger.info("Run finished in %.1f s (%s)", elapsed, termination.reason)


def load_checkpoint(run_dir: Path, filename: str = FINAL_FILENAME) -> dict[str, Any]:
    """Load a persisted checkpoint for post-processing (no simulation required).

    Args:
        run_dir: Run directory written by `run`.
        filename: Checkpoint file name inside the run directory.

    Returns:
        Dict with the stored arrays plus the run configuration under `"config"`.
    """
    with np.load(run_dir / filename) as data:
        payload: dict[str, Any] = {key: data[key] for key in data.files}
    payload["config"] = json.loads((run_dir / CONFIG_FILENAME).read_text())
    return payload


def _parse_args() -> RunConfig:
    parser = argparse.ArgumentParser(description="Robust NSGA-II optimization of the HDG operating policy")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--pop-size", type=int, default=DEFAULT_POP_SIZE)
    parser.add_argument("--generations", type=int, default=DEFAULT_GENERATIONS)
    parser.add_argument("--n-mc-samples", type=int, default=OPTIMIZATION_SAMPLES)
    parser.add_argument("--items", type=int, default=OPTIMIZATION_ITEMS)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--min-generations", type=int, default=DEFAULT_MIN_GENERATIONS)
    parser.add_argument("--checkpoint-every", type=int, default=DEFAULT_CHECKPOINT_EVERY)
    parser.add_argument("--out-dir", type=str, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--cost-scenario", type=str, default=THESIS_CORRECTED_COSTS.name, choices=sorted(COST_SCENARIOS))
    parser.add_argument("--fed-atom-economy", action="store_true", help="Fed-basis atom economy (instrument sensitivity)")
    parser.add_argument("--resume", type=str, default="", help="Checkpoint file name or 'latest' to continue a run")
    args = parser.parse_args()
    return RunConfig(
        seed=args.seed,
        pop_size=args.pop_size,
        n_generations=args.generations,
        n_mc_samples=args.n_mc_samples,
        items=args.items,
        n_jobs=args.workers,
        min_generations=args.min_generations,
        checkpoint_every=args.checkpoint_every,
        out_dir=args.out_dir,
        cost_scenario=args.cost_scenario,
        fed_atom_economy=args.fed_atom_economy,
        resume_from=args.resume,
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    run(_parse_args())
