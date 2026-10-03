"""Tests of the common-random-number policy evaluator.

Purpose: spec simulation/operating-policy, stochastic evaluation and CRN scenarios.
Author: Jose D. Hernandez-Betancur
Date: 2026-10-02
"""

from pathlib import Path

import numpy as np
import pytest

from src.optimization.evaluation import PolicyEvaluation, evaluate_policy, sample_seeds
from src.process.operating_policy import BASELINE_POLICY, OperatingPolicy
from src.sustainability.greenscope import Indicator
from src.sustainability.streams import UnitProcess

TEST_ITEMS = 100_000
TEST_SAMPLES = 4
ALT_POLICY = OperatingPolicy(58.0, 12.5, 1150.0, 42.0, 4.9, 480.0, 446.0)


@pytest.fixture(scope="module")
def baseline_eval() -> PolicyEvaluation:
    return evaluate_policy(BASELINE_POLICY, base_seed=77, n_samples=TEST_SAMPLES, items=TEST_ITEMS)


def test_array_shapes(baseline_eval: PolicyEvaluation) -> None:
    n = TEST_SAMPLES
    assert baseline_eval.n_samples == n
    assert baseline_eval.process_utility.shape == (n,)
    assert baseline_eval.process_scores.shape == (n, 18)
    assert baseline_eval.unit_indicators.shape == (n, 7, 17)
    assert baseline_eval.unit_scores.shape == (n, 7, 17)
    assert baseline_eval.defect_fraction.shape == (n,)
    assert np.all((baseline_eval.defect_fraction >= 0) & (baseline_eval.defect_fraction <= 1))


def test_seed_determinism(baseline_eval: PolicyEvaluation) -> None:
    repeat = evaluate_policy(BASELINE_POLICY, base_seed=77, n_samples=TEST_SAMPLES, items=TEST_ITEMS)
    np.testing.assert_array_equal(repeat.process_utility, baseline_eval.process_utility)
    np.testing.assert_array_equal(repeat.unit_indicators, baseline_eval.unit_indicators)


def test_paired_sampling_across_policies(baseline_eval: PolicyEvaluation) -> None:
    other = evaluate_policy(ALT_POLICY, base_seed=77, n_samples=TEST_SAMPLES, items=TEST_ITEMS)
    np.testing.assert_array_equal(other.mean_standard_thickness_um, baseline_eval.mean_standard_thickness_um)
    assert not np.array_equal(other.com_usd, baseline_eval.com_usd)


def test_sample_seeds_are_reproducible() -> None:
    entropy_a = [seed.entropy for seed in sample_seeds(5, 3)]
    entropy_b = [seed.entropy for seed in sample_seeds(5, 3)]
    assert entropy_a == entropy_b


def test_objective_extraction_matches_indicator_columns(baseline_eval: PolicyEvaluation) -> None:
    com = baseline_eval.unit_indicators[:, :, Indicator.MANUFACTURING_COST].sum(axis=1)
    np.testing.assert_array_equal(baseline_eval.com_usd, com)
    pickling_com = baseline_eval.stage_indicator(UnitProcess.PICKLING, Indicator.MANUFACTURING_COST)
    np.testing.assert_array_equal(pickling_com, baseline_eval.unit_indicators[:, UnitProcess.PICKLING, 16])
    assert np.all(baseline_eval.water_intake_m3 > 0)
    assert np.all(baseline_eval.polluted_liquid_m3 > 0)


def test_npz_round_trip(baseline_eval: PolicyEvaluation, tmp_path: Path) -> None:
    target = tmp_path / "eval.npz"
    baseline_eval.save(target)
    restored = PolicyEvaluation.load(target)
    np.testing.assert_array_equal(restored.process_utility, baseline_eval.process_utility)
    np.testing.assert_array_equal(restored.unit_scores, baseline_eval.unit_scores)
