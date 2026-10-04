"""Tests of the fuzzy compromise selector and the deep characterization datasets.

Purpose: spec optimization/mcdm-selection scenarios.
Author: Jose D. Hernandez-Betancur
Date: 2026-10-02
"""

import json
from pathlib import Path

import numpy as np
import pytest

from src.analysis.critical_points import assess_sustainability
from src.optimization.evaluation import PolicyEvaluation
from src.optimization.mcdm import (
    characterize_designs,
    empirical_sustainability_probability,
    fuzzy_memberships,
    objective_weights_from_fahp,
    pareto_mask,
    select_compromise,
    sustainability_probability,
    utility_pct,
)
from src.optimization.problem import BatchSummary
from src.process.operating_policy import BASELINE_POLICY, OperatingPolicy
from src.sustainability.thesis_weights import thesis_indicator_weights
from src.sustainability.utility import QUALITY_WEIGHT_INDEX

TWO_POINT_X = np.array(
    [[50.0, 17.0, 900.0, 50.0, 4.5, 400.0, 450.0, 150.0], [55.0, 15.0, 800.0, 45.0, 4.2, 350.0, 452.0, 120.0]]
)
TWO_POINT_F = np.array([[-90.0, 1.0e6, 40.0, 200.0], [-80.0, 0.8e6, 50.0, 180.0]])


def test_pareto_mask_drops_dominated() -> None:
    objectives = np.array([[1.0, 1.0], [2.0, 2.0], [0.5, 3.0]])
    np.testing.assert_array_equal(pareto_mask(objectives), [True, False, True])


def test_fahp_objective_weights_normalized() -> None:
    weights = objective_weights_from_fahp()
    assert weights.shape == (4,)
    np.testing.assert_allclose(weights.sum(), 1.0)
    assert weights[0] > weights[1] > weights[2] == weights[3] > 0


def test_compromise_on_two_point_front() -> None:
    result = select_compromise(TWO_POINT_X, TWO_POINT_F)
    assert result.f.shape == (4,) and result.x.shape == (8,)
    assert np.all((result.memberships >= 0) & (result.memberships <= 1))
    np.testing.assert_array_equal(result.utopia, TWO_POINT_F.min(axis=0))
    np.testing.assert_array_equal(result.nadir, TWO_POINT_F.max(axis=0))
    assert result.f[0] == -90.0


def test_degenerate_objective_contributes_constant_membership() -> None:
    objectives = np.column_stack([TWO_POINT_F[:, :3], [5.0, 5.0]])
    memberships, _, _ = fuzzy_memberships(objectives)
    np.testing.assert_array_equal(memberships[:, 3], [1.0, 1.0])
    assert np.all(np.isfinite(memberships))


def test_deep_characterization_dataset_schema(tmp_path: Path) -> None:
    optimal = OperatingPolicy(55.0, 15.0, 900.0, 45.0, 4.2, 350.0, 452.0)
    evaluations = characterize_designs(
        optimal, baseline=BASELINE_POLICY, base_seed=13, n_samples=3, items=50_000, out_dir=tmp_path
    )
    for name in ("asis", "baseline", "optimal"):
        restored = PolicyEvaluation.load(tmp_path / f"{name}.npz")
        assert restored.n_samples == 3
        np.testing.assert_array_equal(restored.process_utility, evaluations[name].process_utility)
    summary = json.loads((tmp_path / "summary.json").read_text())
    assert summary["asis"]["policy"] is None
    for name in ("asis", "baseline", "optimal"):
        assert 0.0 <= summary[name]["p_sustainable"] <= 1.0
        assert {"mean", "std", "ci_lower", "ci_upper"} <= set(summary[name]["indicators"]["com_usd"])
    paired = evaluations["baseline"].mean_standard_thickness_um
    np.testing.assert_array_equal(paired, evaluations["optimal"].mean_standard_thickness_um)


def test_utility_pct_and_probability_consistent(tmp_path: Path) -> None:
    optimal = OperatingPolicy(55.0, 15.0, 900.0, 45.0, 4.2, 350.0, 452.0)
    evaluations = characterize_designs(optimal, base_seed=13, n_samples=3, items=50_000, out_dir=tmp_path)
    pct = utility_pct(evaluations["optimal"])
    assert pct.shape == (3,)
    np.testing.assert_allclose(
        empirical_sustainability_probability(evaluations["optimal"]),
        np.mean(pct >= 80.0),
    )


def test_sustainability_probability_follows_the_thesis_normal_band(tmp_path: Path) -> None:
    optimal = OperatingPolicy(55.0, 15.0, 900.0, 45.0, 4.2, 350.0, 452.0)
    evaluations = characterize_designs(optimal, base_seed=13, n_samples=3, items=50_000, out_dir=tmp_path)
    evaluation = evaluations["optimal"]
    weight = thesis_indicator_weights()[QUALITY_WEIGHT_INDEX]
    expected = assess_sustainability(evaluation.process_utility, evaluation.mean_standard_thickness_um, weight)
    assert sustainability_probability(evaluation) == pytest.approx(expected.probability)
    assert 0.0 < sustainability_probability(evaluation) < 1.0


def _fake_reevaluation(objectives: np.ndarray, constraints: np.ndarray):  # type: ignore[no-untyped-def]
    def _fake(*_args: object, **_kwargs: object) -> BatchSummary:
        return BatchSummary(objectives, objectives.copy(), constraints, np.ones((objectives.shape[0], 7)))

    return _fake


def _finished_tiny_run(tmp_path: Path) -> Path:
    from src.optimization.run_nsga2 import RunConfig, run

    config = RunConfig(seed=6, pop_size=8, n_generations=2, n_mc_samples=2, items=50_000, out_dir=str(tmp_path))
    return run(config)


def test_prepare_selection_picks_only_feasible_designs(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    from src.optimization import mcdm

    run_dir = _finished_tiny_run(tmp_path / "run")
    n = np.atleast_2d(np.load(run_dir / "final.npz")["opt_X"]).shape[0]
    objectives = np.column_stack([-np.arange(n, 0, -1.0), np.arange(n) + 1.0, np.ones(n), np.ones(n)])
    objectives = np.vstack([objectives, [0.0, 1.0, 1.0, 1.0]])
    constraints = np.full((n + 1, 2), -1.0)
    constraints[0] = 1.0
    monkeypatch.setattr(mcdm, "reevaluate_front", _fake_reevaluation(objectives, constraints))
    compromise = mcdm.prepare_selection(run_dir, tmp_path / "out", front_items=1, n_jobs=1)
    saved = np.load(tmp_path / "out" / "front.npz")
    assert saved["f"].shape == (n, 4) and saved["baseline_f"].shape == (4,)
    assert not np.allclose(compromise.f, objectives[0])


def test_prepare_selection_rejects_a_front_without_feasible_designs(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    from src.optimization import mcdm

    run_dir = _finished_tiny_run(tmp_path / "run")
    n = np.atleast_2d(np.load(run_dir / "final.npz")["opt_X"]).shape[0]
    monkeypatch.setattr(mcdm, "reevaluate_front", _fake_reevaluation(np.ones((n + 1, 4)), np.ones((n + 1, 2))))
    with pytest.raises(ValueError, match="No design of the front is feasible"):
        mcdm.prepare_selection(run_dir, tmp_path / "out", front_items=1, n_jobs=1)


def test_no_backsliding_veto_excludes_backsliding_designs(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    from src.optimization import mcdm

    run_dir = _finished_tiny_run(tmp_path / "run")
    n = np.atleast_2d(np.load(run_dir / "final.npz")["opt_X"]).shape[0]
    objectives = np.column_stack([-np.arange(n, 0, -1.0), np.ones(n), np.ones(n), np.ones(n)])
    objectives[0, 2] = 50.0
    objectives = np.vstack([objectives, [0.0, 1.0, 1.0, 1.0]])
    constraints = np.full((n + 1, 2), -1.0)
    monkeypatch.setattr(mcdm, "reevaluate_front", _fake_reevaluation(objectives, constraints))
    monkeypatch.setattr(mcdm, "_asis_objectives", lambda *a, **k: np.array([0.0, 1.0, 5.0, 5.0]))
    mcdm.prepare_selection(run_dir, tmp_path / "out", front_items=1, n_jobs=1)
    saved = np.load(tmp_path / "out" / "front.npz")
    assert not saved["eligible"][0] and saved["eligible"][1:].all()
    np.testing.assert_array_equal(saved["asis_f"], [0.0, 1.0, 5.0, 5.0])
