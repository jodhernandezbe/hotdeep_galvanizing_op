"""Tests of the price-scenario sensitivity computed from the saved full-year front.

Purpose: the mass-based COM shift reproduces a direct re-evaluation exactly and the comparison
reports agreement across scenarios without re-simulating.
Author: Jose D. Hernandez-Betancur
Date: 2026-10-03
"""

import json
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from src.optimization.front_evaluation import reevaluate_front
from src.optimization.mcdm import prepare_selection
from src.optimization.price_sensitivity import COM_COLUMN, compare_scenarios, run_sensitivity, shift_com
from src.optimization.run_nsga2 import RunConfig, run
from src.sustainability.costs import THESIS_COSTS, get_cost_scenario

TINY = {"n_mc_samples": 3, "items": 50_000}
X = np.array([[50.0, 17.0, 900.0, 50.0, 4.5, 400.0, 450.0, 150.0], [55.0, 15.0, 800.0, 45.0, 4.2, 350.0, 452.0, 120.0]])


@pytest.fixture(scope="module")
def tiny_front(tmp_path_factory: pytest.TempPathFactory) -> Path:
    config = RunConfig(
        seed=8, pop_size=8, n_generations=2, checkpoint_every=1, out_dir=str(tmp_path_factory.mktemp("sens_run")), **TINY
    )
    run_dir = run(config)
    out_dir = tmp_path_factory.mktemp("sens_mc")
    prepare_selection(run_dir, out_dir, front_items=TINY["items"], n_jobs=1)
    return out_dir / "front.npz"


def test_mass_based_shift_matches_direct_reevaluation() -> None:
    reference, other = get_cost_scenario("thesis_corrected"), get_cost_scenario("market2025")
    summary_ref = reevaluate_front(X, reference.name, 8, 2, TINY["items"])
    summary_direct = reevaluate_front(X, other.name, 8, 2, TINY["items"])
    f_shifted = shift_com(summary_ref.mean_objectives, summary_ref.raw_material_masses_kg, reference, other)
    np.testing.assert_allclose(f_shifted, summary_direct.mean_objectives, rtol=1e-10)


def test_shift_refuses_scenarios_differing_outside_raw_materials() -> None:
    modified = get_cost_scenario("market2025")
    tampered = replace(modified, name="tampered", labor_usd_per_year=1.0)
    with pytest.raises(ValueError, match="Labor differs"):
        shift_com(np.zeros((1, 4)), np.zeros((1, 7)), THESIS_COSTS, tampered)


def test_sensitivity_writes_outputs_and_changes_only_the_cost_column(tiny_front: Path, tmp_path: Path) -> None:
    comparison = run_sensitivity(tiny_front, tmp_path, ("thesis_corrected", "market2025"))
    assert comparison["items"] == TINY["items"]
    stored = json.loads((tmp_path / "price_sensitivity.json").read_text())
    assert set(stored["scenarios"]) == {"thesis_corrected", "market2025"}
    thesis = np.array(stored["scenarios"]["thesis_corrected"]["baseline_f"])
    market = np.array(stored["scenarios"]["market2025"]["baseline_f"])
    assert market[COM_COLUMN] != thesis[COM_COLUMN]
    np.testing.assert_array_equal(market[[0, 2, 3]], thesis[[0, 2, 3]])
    assert (tmp_path / "objectives.npz").exists()


def test_identical_scenarios_agree_perfectly() -> None:
    objectives = np.array([[-90.0, 1.0e6, 40.0, 200.0], [-80.0, 0.8e6, 50.0, 180.0]])
    baseline = np.array([-70.0, 1.2e6, 60.0, 220.0])
    comparison = compare_scenarios(X, {"a": objectives, "b": objectives.copy()}, {"a": baseline, "b": baseline.copy()})
    assert comparison["agreement"]["b"]["same_compromise_as_reference"] is True
    assert comparison["agreement"]["b"]["com_rank_spearman_vs_reference"] == pytest.approx(1.0)
