"""Tests for the initial bath conditions."""

import numpy as np
import pytest

from src.process import initial_conditions as ic
from src.process.densities import hcl_solution_density, naoh_solution_density


def test_rinsing_volume_range() -> None:
    rng = np.random.default_rng(0)
    volumes = [ic.rinsing_initial_volume(rng) for _ in range(200)]
    assert 12.6 <= min(volumes) and max(volumes) <= 14.0


def test_degreasing_condition() -> None:
    state = ic.degreasing_initial_condition(np.random.default_rng(1))
    assert 14 <= state.composition_wt[0] <= 16
    assert state.composition_wt.sum() == pytest.approx(100.0)
    assert 48.9 <= state.temperature_c <= 51.1
    expected = naoh_solution_density(state.temperature_c, state.composition_wt[0]) * state.volume_m3
    assert state.mass_kg == pytest.approx(expected)


@pytest.mark.parametrize(
    ("factory", "size", "low", "high"),
    [
        (ic.normal_pickling_initial_condition, 3, 16, 18),
        (ic.abnormal_pickling_initial_condition, 4, 2, 4),
    ],
)
def test_pickling_conditions(factory, size: int, low: float, high: float) -> None:
    state = factory(np.random.default_rng(2), 22.0)
    assert state.composition_wt.shape == (size,)
    assert low <= state.composition_wt[0] <= high
    assert state.composition_wt.sum() == pytest.approx(100.0)
    assert state.mass_kg == pytest.approx(hcl_solution_density(22.0, state.composition_wt[0]) * state.volume_m3)
    assert state.temperature_c is None and state.ph is None


def test_fluxing_condition_is_closed_mass_balance() -> None:
    state = ic.fluxing_initial_condition(np.random.default_rng(3))
    assert state.composition_wt.shape == (9,)
    assert state.composition_wt.sum() == pytest.approx(100.0)
    assert state.mass_kg == pytest.approx(1030 * state.volume_m3)
    assert state.ph is not None and 3.0 < state.ph < 6.0
    assert np.all(state.composition_wt[:7] >= 0)
    assert state.composition_wt[7:].sum() == 0


def test_seeded_rng_is_deterministic() -> None:
    first = ic.fluxing_initial_condition(np.random.default_rng(7))
    second = ic.fluxing_initial_condition(np.random.default_rng(7))
    np.testing.assert_array_equal(first.composition_wt, second.composition_wt)
    assert first.ph == second.ph


def test_fluxing_without_admissible_root_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ic, "_admissible_roots", lambda *args: [])
    with pytest.raises(ValueError, match="No admissible"):
        ic.fluxing_initial_condition(np.random.default_rng(0))
