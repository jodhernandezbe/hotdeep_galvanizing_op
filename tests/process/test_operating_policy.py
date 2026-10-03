"""Tests of the operating-policy decision vector and its injection into the simulator.

Purpose: spec simulation/operating-policy (change add-nsga2-robust-optimization).
Author: Jose D. Hernandez-Betancur
Date: 2026-10-02
"""

import numpy as np
import pytest

from src.process.operating_policy import (
    N_DECISION_VARIABLES,
    POLICY_BOUNDS,
    OperatingPolicy,
    policy_lower_bounds,
    policy_upper_bounds,
)
from src.process.simulation import simulate_year

IN_BOUNDS_VALUES = {
    "degreasing_temperature_c": 55.0,
    "pickling_hcl_pct": 15.0,
    "pickling_dip_time_s": 900.0,
    "fluxing_temperature_c": 45.0,
    "fluxing_ph_target": 4.2,
    "fluxing_salt_g_per_l": 350.0,
    "galvanizing_temperature_c": 452.0,
}


def test_in_bounds_policy_accepted() -> None:
    policy = OperatingPolicy(**IN_BOUNDS_VALUES)
    for name, value in IN_BOUNDS_VALUES.items():
        assert getattr(policy, name) == value


def test_out_of_bounds_policy_rejected_with_variable_name() -> None:
    values = dict(IN_BOUNDS_VALUES, pickling_hcl_pct=25.0)
    with pytest.raises(ValueError, match=r"pickling_hcl_pct.*\[12\.0, 18\.0\]"):
        OperatingPolicy(**values)


@pytest.mark.parametrize("name", list(POLICY_BOUNDS))
def test_every_bound_is_enforced(name: str) -> None:
    _, upper = POLICY_BOUNDS[name]
    values = dict(IN_BOUNDS_VALUES, **{name: upper + 1.0})
    with pytest.raises(ValueError, match=name):
        OperatingPolicy(**values)


def test_array_round_trip() -> None:
    policy = OperatingPolicy(**IN_BOUNDS_VALUES)
    recovered = OperatingPolicy.from_array(policy.to_array())
    assert recovered == policy


def test_from_array_rejects_wrong_length() -> None:
    with pytest.raises(ValueError, match=str(N_DECISION_VARIABLES)):
        OperatingPolicy.from_array(np.zeros(5))


def test_bound_vectors_match_policy_order() -> None:
    lower, upper = policy_lower_bounds(), policy_upper_bounds()
    assert lower.shape == upper.shape == (N_DECISION_VARIABLES,)
    assert np.all(lower < upper)
    mid = OperatingPolicy.from_array((lower + upper) / 2)
    np.testing.assert_allclose(mid.to_array(), (lower + upper) / 2)


def test_policy_changes_corrected_mode_outputs() -> None:
    baseline = simulate_year(100_000, np.random.default_rng(11), preserve_thesis_quirks=False)
    policy = OperatingPolicy(**IN_BOUNDS_VALUES)
    steered = simulate_year(100_000, np.random.default_rng(11), preserve_thesis_quirks=False, policy=policy)
    assert steered.totals.zinc_coating_kg != baseline.totals.zinc_coating_kg


def test_policy_run_tracks_new_accumulators() -> None:
    policy = OperatingPolicy(**IN_BOUNDS_VALUES)
    year = simulate_year(100_000, np.random.default_rng(11), preserve_thesis_quirks=False, policy=policy)
    assert year.totals.n_quality_pieces > 0
    assert 0 <= year.totals.n_defective_pieces <= year.totals.n_quality_pieces
    assert year.totals.peak_pickling_fe2_g_per_l >= 0.0
    assert year.totals.peak_fluxing_fe2_g_per_l >= 0.0
