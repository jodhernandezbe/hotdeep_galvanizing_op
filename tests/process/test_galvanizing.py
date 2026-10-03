"""Tests for the galvanizing bath model."""

import numpy as np
import pytest

from src.process.galvanizing import (
    coating_mass_kg,
    coating_thickness_um,
    draw_skimming_losses,
    initial_bath,
    makeup_heat_j,
    standard_thickness_um,
    zinc_enthalpy_j_per_kg,
)


def test_zinc_enthalpy_at_reference_point() -> None:
    assert zinc_enthalpy_j_per_kg(419.5, 25.0) == pytest.approx(1000 * (0.3883 * 394.5 + 100.9))


def test_coating_thickness_without_random_term_matches_polynomial() -> None:
    silicon = np.array([0.2])
    expected = -3017 + 6.714 * 450 + (4451 - 4.376 * 450) * 0.2 + (-1.297e4 + 2.611 * 450) * 0.04 + 1.145e4 * 0.008
    assert coating_thickness_um(450.0, silicon)[0] == pytest.approx(expected)


def test_first_dip_scales_constant_term_by_uniform_draw() -> None:
    silicon = np.full(1000, 0.2)
    plain = coating_thickness_um(450.0, silicon)
    random = coating_thickness_um(450.0, silicon, np.random.default_rng(0))
    constant = -3017 + 6.714 * 450
    ratio = (random - (plain - constant)) / constant
    assert 0 <= ratio.min() and ratio.max() <= 1
    assert ratio.std() > 0.1


def test_coating_mass_is_zinc_density_times_thickness_times_area() -> None:
    assert coating_mass_kg(np.array([100.0]), np.array([2.0]))[0] == pytest.approx(7000 * 100e-6 * 2.0)


@pytest.mark.parametrize(
    ("gauge_mm", "expected"),
    [(0.3, 35.0), (1.49, 35.0), (1.5, 45.0), (2.99, 45.0), (3.0, 55.0), (5.99, 55.0), (6.0, 70.0), (32.0, 70.0)],
)
def test_standard_thickness_thresholds(gauge_mm: float, expected: float) -> None:
    assert standard_thickness_um(np.array([gauge_mm * 1e-3]))[0] == expected


def test_skimming_losses_are_consistent() -> None:
    losses = draw_skimming_losses(1000.0, np.random.default_rng(0))
    assert 0 < losses.dross_kg < 20
    assert 0 < losses.zinc_lost_dross_kg < losses.dross_kg
    assert losses.zinc_lost_ash_kg < losses.ash_kg


def test_makeup_heat_is_zero_when_setpoint_does_not_rise() -> None:
    assert makeup_heat_j(50000.0, 10.0, 1000.0, 450.0, 449.0, 22.0) == 0.0


def test_makeup_heat_matches_hand_calculation_when_setpoint_rises() -> None:
    previous, new, ambient = 449.0, 451.0, 20.0
    lost_fraction = abs((previous - ambient) / 435)
    expected = (
        (50000.0 - 10.0) * zinc_enthalpy_j_per_kg(new, ambient)
        + (0.01 * lost_fraction - 1) * 50000.0 * zinc_enthalpy_j_per_kg(previous, ambient)
        + 450 * 1000.0 * (new - 100.0)
    )
    assert makeup_heat_j(50000.0, 10.0, 1000.0, previous, new, ambient) == pytest.approx(expected)


def test_initial_bath_mass_and_heat_are_consistent() -> None:
    bath, heat = initial_bath(22.0, np.random.default_rng(0))
    assert 6430 * 1.6 * 5.6 <= bath.initial_mass_kg <= 6430 * 1.8 * 5.6
    assert heat == pytest.approx(bath.initial_mass_kg * zinc_enthalpy_j_per_kg(bath.temperature_c, 22.0))
