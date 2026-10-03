"""Tests for the fluxing balance."""

import numpy as np
import pytest

from src.process import fluxing
from src.process.initial_conditions import fluxing_initial_condition


class FixedPh:
    """Random generator stub that returns a fixed pH."""

    def __init__(self, ph: float) -> None:
        self.ph = ph

    def normal(self, *_args: float) -> float:
        return self.ph


@pytest.fixture(name="bath")
def fixture_bath():
    return fluxing_initial_condition(np.random.default_rng(3))


def run(
    bath,
    new_ph: float,
    ph_before: float | None = None,
    rust_kg: float = 50.0,
    steel_kg: float = 5000.0,
    preserve_thesis_quirks: bool = True,
):
    return fluxing.flux(
        rust_kg,
        bath.mass_kg,
        bath.composition_wt,
        bath.temperature_c,
        steel_kg,
        0.0,
        22.0,
        bath.volume_m3,
        bath.ph if ph_before is None else ph_before,
        FixedPh(new_ph),
        preserve_thesis_quirks=preserve_thesis_quirks,
    )


def nitrogen_kmol(mass_kg: float, composition_wt: np.ndarray) -> float:
    return 0.01 * mass_kg * (composition_wt[3] / fluxing.MW_NH4 + composition_wt[5] / fluxing.MW_NH4OH)


def test_composition_sums_to_100_and_ph_returned(bath) -> None:
    result = run(bath, 4.5)
    assert result.composition_wt.shape == (9,)
    assert result.composition_wt.sum() == pytest.approx(100.0)
    assert result.ph == 4.5
    assert result.volume_m3 > 0


def test_removed_solution_and_mass(bath) -> None:
    result = run(bath, 4.5)
    assert result.removed_solution_kg == pytest.approx(1e-6 * 5000.0 * 1030)
    assert result.solution_mass_kg > 0


def test_lower_ph_without_hcl_addition(bath) -> None:
    result = run(bath, 4.0, ph_before=4.5)
    assert result.hcl_added_kg == 0.0 and result.nh4oh_added_kg == 0.0


def test_lower_ph_with_hcl_addition(bath) -> None:
    result = run(bath, 5.5, ph_before=6.0)
    assert result.hcl_added_kg >= 0.0
    assert result.nh4oh_added_kg == 0.0


def test_hcl_correction_skipped_when_negative(bath) -> None:
    result = run(bath, 5.5, ph_before=6.0, rust_kg=0.0)
    assert result.hcl_added_kg == 0.0


def test_higher_ph_below_4_adds_nh4oh(bath) -> None:
    result = run(bath, 3.5, ph_before=3.0)
    assert result.hcl_added_kg == 0.0
    assert result.nh4oh_added_kg != 0.0


def test_higher_ph_above_4_adds_nothing(bath) -> None:
    result = run(bath, 4.6, ph_before=4.5)
    assert result.hcl_added_kg == 0.0 and result.nh4oh_added_kg == 0.0


def test_energy_balance_closed_form() -> None:
    temperature, heat = fluxing._energy_balance(1000.0, 50.0, 0.0, 0.0, 22.0)
    lost = abs((50.0 - 22.0) / 35.1)
    assert temperature == pytest.approx((1 - 0.1 * lost) * 25 + 25)
    assert heat == pytest.approx(0.1 * lost * 1000.0 * 96.232 * 25)


def test_steel_cools_the_bath(bath) -> None:
    assert run(bath, 4.5).temperature_c < bath.temperature_c


def test_thesis_mode_creates_nitrogen_on_ph_increase_above_4(bath) -> None:
    result = run(bath, 4.8, ph_before=4.2, steel_kg=0.0, preserve_thesis_quirks=True)
    nitrogen_in = nitrogen_kmol(bath.mass_kg, bath.composition_wt)
    nitrogen_out = nitrogen_kmol(result.solution_mass_kg, result.composition_wt)
    assert result.nh4oh_added_kg == 0.0
    assert nitrogen_out != pytest.approx(nitrogen_in, rel=1e-6)


def test_corrected_mode_conserves_nitrogen_on_ph_increase_above_4(bath) -> None:
    result = run(bath, 4.8, ph_before=4.2, steel_kg=0.0, preserve_thesis_quirks=False)
    nitrogen_in = nitrogen_kmol(bath.mass_kg, bath.composition_wt)
    nitrogen_out = nitrogen_kmol(result.solution_mass_kg, result.composition_wt)
    assert result.nh4oh_added_kg == 0.0 and result.hcl_added_kg == 0.0
    assert nitrogen_out == pytest.approx(nitrogen_in, rel=1e-9)


def test_both_modes_conserve_nitrogen_on_ph_decrease_without_hcl(bath) -> None:
    for preserve in (True, False):
        result = run(bath, 4.0, ph_before=4.5, steel_kg=0.0, preserve_thesis_quirks=preserve)
        nitrogen_in = nitrogen_kmol(bath.mass_kg, bath.composition_wt)
        nitrogen_out = nitrogen_kmol(result.solution_mass_kg, result.composition_wt)
        assert nitrogen_out == pytest.approx(nitrogen_in, rel=1e-9)


def test_corrected_mode_bath_mass_stays_bounded_under_recycling(bath) -> None:
    mass, wt, temperature, volume, ph = bath.mass_kg, bath.composition_wt, bath.temperature_c, bath.volume_m3, bath.ph
    rng = np.random.default_rng(11)
    for _ in range(300):
        result = fluxing.flux(5.0, mass, wt, temperature, 300.0, 0.0, 22.0, volume, ph, rng, preserve_thesis_quirks=False)
        mass, wt, temperature = result.solution_mass_kg, result.composition_wt, result.temperature_c
        volume, ph = result.volume_m3, result.ph
    assert mass < 1.6 * bath.mass_kg
