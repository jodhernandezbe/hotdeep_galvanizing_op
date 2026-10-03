"""Tests for the pickling kinetics."""

import numpy as np
import pytest

from src.process import pickling
from src.process.densities import hcl_solution_density
from src.process.pickling import pickle_abnormal, pickle_normal

NORMAL = np.array([17.0, 83.0, 0.0])
ABNORMAL = np.array([3.0, 97.0, 0.0, 0.0])


def normal(rust_kg: float = 100.0, seed: int = 0):
    return pickle_normal(NORMAL, 13700.0, 22.0, 12.8, rust_kg, 500.0, 5000.0, np.random.default_rng(seed))


def test_normal_kinetics_direction() -> None:
    result = normal()
    assert result.composition_wt[0] < 17.0
    assert result.composition_wt[2] > 0
    assert result.composition_wt.sum() == pytest.approx(100.0)
    assert result.surface_mass_kg == pytest.approx(100.0 * 0.1175)


def test_normal_removed_solution_and_volume() -> None:
    result = normal()
    assert result.removed_solution_kg == pytest.approx(1e-6 * 5000.0 * hcl_solution_density(22.0, 17.0))
    assert result.volume_m3 == pytest.approx(result.solution_mass_kg / hcl_solution_density(22.0, result.composition_wt[0]))


def test_normal_without_rust_only_drags_solution_out() -> None:
    result = normal(rust_kg=0.0)
    assert result.surface_mass_kg == 0.0
    assert result.solution_mass_kg == pytest.approx(13700.0 - result.removed_solution_kg)
    np.testing.assert_allclose(result.composition_wt, NORMAL)


def test_normal_fallback_when_threshold_not_reached(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(pickling, "RESIDUAL_SURFACE_FRACTION", -1.0)
    result = normal()
    assert result.surface_mass_kg == 0.0
    np.testing.assert_allclose(result.composition_wt, NORMAL)


def test_ode_surface_is_monotonic() -> None:
    solution = pickling._integrate(
        pickling._rxnn,
        [2300.0, 11000.0, 0.0, 100.0],
        np.random.default_rng(0),
        (12.8, 22.0, 100.0),
        (pickling._rust_removed_event,),
    )
    states = solution.y.T
    assert np.all(np.diff(states[:, 3]) <= 1e-9)
    assert np.all(np.diff(states[:, 2]) >= -1e-9)
    assert states[-1, 0] < states[0, 0]


def test_normal_stops_integrating_at_residual_rust() -> None:
    solution = pickling._integrate(
        pickling._rxnn,
        [2300.0, 11000.0, 0.0, 100.0],
        np.random.default_rng(0),
        (12.8, 22.0, 100.0),
        (pickling._rust_removed_event,),
    )
    assert solution.status == 1
    assert solution.y_events[0][0][3] == pytest.approx(100.0 * pickling.RESIDUAL_SURFACE_FRACTION)


def test_abnormal_with_negligible_zinc_is_instant_and_keeps_bath() -> None:
    rng = np.random.default_rng(0)
    result = pickle_abnormal(ABNORMAL, 13000.0, 22.0, 12.8, 0.009, 0.0125, 0.3, rng)
    assert result.surface_mass_kg == 0.0
    assert result.composition_wt.sum() == pytest.approx(100.0)


def test_abnormal_strips_zinc() -> None:
    rng = np.random.default_rng(0)
    result = pickle_abnormal(ABNORMAL, 13000.0, 22.0, 12.8, 20.0, 500.0, 5000.0, rng)
    assert result.surface_mass_kg == 0.0
    assert result.composition_wt[3] > 0
    assert result.composition_wt[0] < 3.0
    assert result.composition_wt.sum() == pytest.approx(100.0)


def test_abnormal_fallback_without_zinc_removal() -> None:
    rng = np.random.default_rng(0)
    result = pickle_abnormal(ABNORMAL, 13000.0, 22.0, 12.8, 1e9, 500.0, 5000.0, rng)
    np.testing.assert_allclose(result.composition_wt, ABNORMAL)


def test_deterministic_with_seed() -> None:
    first, second = normal(seed=5), normal(seed=5)
    np.testing.assert_array_equal(first.composition_wt, second.composition_wt)


def test_interp_extrap_linear() -> None:
    x = np.array([3.0, 2.0, 1.0])
    y = np.array([30.0, 20.0, 10.0])
    assert pickling._interp_extrap(x, y, 1.5) == pytest.approx(15.0)
    assert pickling._interp_extrap(x, y, 0.5) == pytest.approx(5.0)
    assert pickling._interp_extrap(x, y, 4.0) == pytest.approx(40.0)
