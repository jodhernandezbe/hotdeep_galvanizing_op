"""Tests of resuming an NSGA-II run from a checkpoint.

Purpose: spec optimization/nsga2 (checkpointing and reproducibility), continuation after an interruption.
Author: Jose D. Hernandez-Betancur
Date: 2026-10-03
"""

import json
import shutil
from pathlib import Path

import numpy as np
import pytest

from src.optimization.run_nsga2 import RunConfig, load_checkpoint, load_resume_state, run

TINY = {"pop_size": 8, "n_mc_samples": 2, "items": 20_000, "checkpoint_every": 1, "min_generations": 0}


@pytest.fixture(scope="module")
def original_run(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return run(RunConfig(seed=5, n_generations=5, out_dir=str(tmp_path_factory.mktemp("orig")), **TINY))


def _resumed(original: Path, tmp: Path, checkpoint: str) -> Path:
    target = tmp / original.name
    shutil.copytree(original, target)
    for later in target.glob("gen_*.npz"):
        if later.name > checkpoint:
            later.unlink()
    (target / "final.npz").unlink()
    return run(RunConfig(seed=5, n_generations=5, out_dir=str(tmp), resume_from=checkpoint, **TINY))


def test_resumed_run_reproduces_the_uninterrupted_final_state(original_run: Path, tmp_path: Path) -> None:
    resumed = _resumed(original_run, tmp_path, "gen_0002.npz")
    first, second = load_checkpoint(original_run), load_checkpoint(resumed)
    assert int(second["n_gen"]) == int(first["n_gen"])
    assert int(second["n_evals"]) == int(first["n_evals"])
    assert len(second["hv_history"]) == len(first["hv_history"])


def test_resume_does_not_reevaluate_and_counts_total_evaluations(original_run: Path, tmp_path: Path) -> None:
    state = load_resume_state(original_run / "gen_0003.npz")
    assert state.generation == 3 and state.n_evaluations == 3 * TINY["pop_size"]
    resumed = _resumed(original_run, tmp_path, "gen_0003.npz")
    summary = json.loads((resumed / "config.json").read_text())
    assert summary["resumed_from_generation"] == 3
    assert summary["n_evaluations"] == int(np.load(original_run / "final.npz")["n_evals"])
    assert (resumed / "config_before_resume.json").exists()


def test_original_checkpoint_is_not_overwritten_by_the_resume(original_run: Path, tmp_path: Path) -> None:
    before = np.load(original_run / "gen_0002.npz")["F"].copy()
    target = tmp_path / original_run.name
    shutil.copytree(original_run, target)
    run(RunConfig(seed=5, n_generations=5, out_dir=str(tmp_path), resume_from="gen_0002.npz", **TINY))
    np.testing.assert_array_equal(np.load(target / "gen_0002.npz")["F"], before)


def test_latest_resolves_the_highest_checkpoint(original_run: Path, tmp_path: Path) -> None:
    target = tmp_path / original_run.name
    shutil.copytree(original_run, target)
    (target / "final.npz").unlink()
    for later in target.glob("gen_000[45].npz"):
        later.unlink()
    resumed = run(RunConfig(seed=5, n_generations=5, out_dir=str(tmp_path), resume_from="latest", **TINY))
    assert json.loads((resumed / "config.json").read_text())["resumed_from_generation"] == 3


def test_resume_fails_when_no_checkpoint_exists(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        run(RunConfig(seed=9, n_generations=3, out_dir=str(tmp_path), resume_from="latest", **TINY))
