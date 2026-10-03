"""Tests for the bath state objects."""

import numpy as np
import pytest

from src.process.initial_conditions import BathInitialCondition
from src.process.plant import Bath, BathLedger


def _initial(mass: float = 1000.0, ph: float | None = None, temperature: float | None = None) -> BathInitialCondition:
    return BathInitialCondition(
        volume_m3=1.0,
        composition_wt=np.array([20.0, 80.0]),
        mass_kg=mass,
        temperature_c=temperature,
        ph=ph,
    )


def test_ledger_averages_compositions_by_batch_count() -> None:
    ledger = BathLedger(100.0, np.array([10.0, 90.0]))
    ledger.commission(200.0, np.array([20.0, 80.0]))
    ledger.retire(50.0, np.array([30.0, 70.0]))
    ledger.retire(70.0, np.array([40.0, 60.0]))
    np.testing.assert_allclose(ledger.mean_initial_composition_wt, [15.0, 85.0])
    np.testing.assert_allclose(ledger.mean_final_composition_wt, [35.0, 65.0])
    assert (ledger.initial_mass_kg, ledger.n_initial, ledger.final_mass_kg, ledger.n_final) == (300.0, 2, 120.0, 2)


def test_bath_from_initial_condition_uses_given_temperature_when_batch_has_none() -> None:
    bath = Bath.from_initial_condition(_initial(), 22.0)
    assert bath.temperature_c == 22.0
    assert Bath.from_initial_condition(_initial(temperature=50.0), 22.0).temperature_c == 50.0


def test_renew_retires_old_batch_and_commissions_new_one() -> None:
    bath = Bath.from_initial_condition(_initial(mass=1000.0, ph=4.0), 22.0)
    bath.mass_kg = 900.0
    bath.last_heat_j = 5.0
    bath.renew(_initial(mass=1200.0, ph=4.5), 22.0)
    assert bath.mass_kg == 1200.0 and bath.last_heat_j == 0.0 and bath.ph == 4.5
    assert (bath.ledger.n_final, bath.ledger.final_mass_kg) == (1, 900.0)
    assert (bath.ledger.n_initial, bath.ledger.initial_mass_kg) == (2, 2200.0)


def test_renew_can_keep_previous_ph() -> None:
    bath = Bath.from_initial_condition(_initial(ph=4.0), 22.0)
    bath.renew(_initial(ph=4.5), 22.0, keep_ph=True)
    assert bath.ph == 4.0


def test_mix_in_conserves_mass_and_mixes_composition_by_mass() -> None:
    bath = Bath.from_initial_condition(_initial(mass=900.0), 22.0)
    bath.mix_in(100.0, np.array([0.0, 100.0]))
    assert bath.mass_kg == pytest.approx(1000.0)
    np.testing.assert_allclose(bath.composition_wt, [18.0, 82.0])


def test_bleed_keeps_composition_and_caps_volume() -> None:
    bath = Bath.from_initial_condition(_initial(mass=2000.0), 22.0)
    bath.volume_m3 = 2.0
    bled = bath.bleed_to(1.5)
    np.testing.assert_allclose(bled, 0.01 * np.array([20.0, 80.0]) * 500.0)
    assert bath.mass_kg == pytest.approx(1500.0)
    assert bath.volume_m3 == 1.5
    np.testing.assert_allclose(bath.composition_wt, [20.0, 80.0])


def test_bleed_is_a_no_op_when_the_bath_fits() -> None:
    bath = Bath.from_initial_condition(_initial(mass=1000.0), 22.0)
    np.testing.assert_array_equal(bath.bleed_to(bath.volume_m3), np.zeros(2))
    assert bath.mass_kg == 1000.0


def test_commissioned_volume_is_recorded_as_capacity() -> None:
    bath = Bath.from_initial_condition(_initial(), 22.0)
    assert bath.capacity_m3 == 1.0
    bath.volume_m3 = 5.0
    bath.renew(_initial(), 22.0)
    assert bath.capacity_m3 == 1.0
