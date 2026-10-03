"""Tests of the NSGA-II problem, termination and runner on a tiny budget.

Purpose: spec optimization/nsga2 scenarios (shapes, parallel==serial, checkpoint reload, reproducibility).
Author: Jose D. Hernandez-Betancur
Date: 2026-10-02
"""

from pathlib import Path

import numpy as np
import pytest

from src.optimization.problem import HdgRobustProblem
from src.optimization.run_nsga2 import RunConfig, load_checkpoint, run
from src.optimization.termination import HypervolumeStagnation
from src.process.operating_policy import BASELINE_POLICY

TINY = {"n_mc_samples": 3, "items": 50_000}
X_PAIR = np.array([BASELINE_POLICY.to_array(), [58.0, 12.5, 1150.0, 42.0, 4.9, 480.0, 446.0]])


def test_problem_returns_objectives_and_constraints() -> None:
    problem = HdgRobustProblem(base_seed=5, **TINY)
    out: dict = {}
    problem._evaluate(X_PAIR, out)
    assert out["F"].shape == (2, 4) and np.all(np.isfinite(out["F"]))
    assert out["G"].shape == (2, 2) and np.all(np.isfinite(out["G"]))
    assert np.all(out["F"][:, 1:] > 0)


def test_parallel_equals_serial() -> None:
    serial: dict = {}
    parallel: dict = {}
    HdgRobustProblem(base_seed=5, n_jobs=1, **TINY)._evaluate(X_PAIR, serial)
    HdgRobustProblem(base_seed=5, n_jobs=4, **TINY)._evaluate(X_PAIR, parallel)
    np.testing.assert_array_equal(serial["F"], parallel["F"])
    np.testing.assert_array_equal(serial["G"], parallel["G"])


def test_hypervolume_stagnation_terminates_on_flat_history() -> None:
    termination = HypervolumeStagnation(n_max_gen=1000, tolerance=1e-4, window=3, min_generations=0)
    termination.hv_history = [0.5, 0.5, 0.5, 0.5]
    assert termination._stagnated()
    termination.hv_history = [0.1, 0.2, 0.3, 0.4]
    assert not termination._stagnated()


def test_noisy_nonmonotone_history_with_new_best_is_not_stagnation() -> None:
    termination = HypervolumeStagnation(n_max_gen=1000, tolerance=1e-4, window=3, min_generations=0)
    termination.hv_history = [0.60, 0.70, 0.65, 0.66, 0.71, 0.68]
    assert not termination._stagnated()
    termination.hv_history = [0.60, 0.70, 0.65, 0.66, 0.69, 0.68]
    assert termination._stagnated()


def test_stagnation_cannot_fire_before_min_generations() -> None:
    termination = HypervolumeStagnation(n_max_gen=1000, tolerance=1e-4, window=3, min_generations=10)
    termination.hv_history = [0.5] * 8
    assert not termination._stagnated()


@pytest.fixture(scope="module")
def tiny_run(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, Path]:
    out_a = tmp_path_factory.mktemp("run_a")
    out_b = tmp_path_factory.mktemp("run_b")
    config_a = RunConfig(seed=3, pop_size=8, n_generations=3, checkpoint_every=1, out_dir=str(out_a), **TINY)
    config_b = RunConfig(seed=3, pop_size=8, n_generations=3, checkpoint_every=1, out_dir=str(out_b), **TINY)
    return run(config_a), run(config_b)


def test_tiny_run_checkpoints_and_reload(tiny_run: tuple[Path, Path]) -> None:
    run_dir, _ = tiny_run
    final = load_checkpoint(run_dir)
    assert final["X"].shape == (8, 7) and final["F"].shape == (8, 4) and final["G"].shape == (8, 2)
    assert final["opt_X"].shape[1] == 7
    assert final["config"]["pop_size"] == 8 and final["config"]["termination_reason"] == "generation budget"
    generation_files = sorted(run_dir.glob("gen_*.npz"))
    assert generation_files, "per-generation checkpoints missing"
    first = load_checkpoint(run_dir, generation_files[0].name)
    assert first["X"].shape == (8, 7)


def test_seeded_rerun_reproduces_front(tiny_run: tuple[Path, Path]) -> None:
    run_dir_a, run_dir_b = tiny_run
    final_a, final_b = load_checkpoint(run_dir_a), load_checkpoint(run_dir_b)
    np.testing.assert_array_equal(final_a["opt_F"], final_b["opt_F"])
    np.testing.assert_array_equal(final_a["opt_X"], final_b["opt_X"])
