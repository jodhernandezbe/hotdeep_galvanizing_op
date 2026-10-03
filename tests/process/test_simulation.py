"""Tests for the yearly line simulation."""

import numpy as np
import pytest

from src.process import simulation
from src.process.fluxing import FluxingResult
from src.process.simulation import simulate_year

SMALL_YEAR_ITEMS = 5000


@pytest.fixture(scope="module")
def year() -> simulation.YearResult:
    return simulate_year(SMALL_YEAR_ITEMS, np.random.default_rng(0))


def test_year_processes_at_least_the_requested_items(year: simulation.YearResult) -> None:
    assert year.totals.n_lots >= 1
    assert year.totals.n_quality_pieces >= SMALL_YEAR_ITEMS


def test_every_bath_has_a_spent_batch_after_the_year(year: simulation.YearResult) -> None:
    for ledger in (year.degreasing, year.rinse_1, year.normal_pickling, year.abnormal_pickling, year.rinse_2, year.fluxing):
        assert ledger.n_final >= 1
        assert ledger.final_mass_kg > 0


def test_totals_are_physically_consistent(year: simulation.YearResult) -> None:
    totals = year.totals
    assert totals.steel_kg > 0 and totals.rust_kg > 0 and totals.zinc_coating_kg > 0
    assert totals.saponified_kg + totals.remaining_grease_kg == pytest.approx(0.0 + totals.grease_and_oil_kg)
    assert 0 < totals.quality_mass_weighted <= totals.steel_kg
    assert totals.molten_zinc_kg > totals.zinc_coating_kg
    assert totals.dross_kg > 0 and totals.ash_kg > 0
    assert min(totals.degreasing_heat_j, totals.drying_heat_j, totals.galvanizing_heat_j) > 0


def test_same_seed_reproduces_the_year() -> None:
    first = simulate_year(SMALL_YEAR_ITEMS, np.random.default_rng(5))
    second = simulate_year(SMALL_YEAR_ITEMS, np.random.default_rng(5))
    assert first.totals == second.totals


def test_different_seeds_give_different_years() -> None:
    first = simulate_year(SMALL_YEAR_ITEMS, np.random.default_rng(1))
    second = simulate_year(SMALL_YEAR_ITEMS, np.random.default_rng(2))
    assert first.totals.steel_kg != second.totals.steel_kg


def _flux_result(volume: float, ph: float) -> FluxingResult:
    return FluxingResult(
        heat_j=1.0,
        solution_mass_kg=10.0,
        composition_wt=np.zeros(9),
        temperature_c=50.0,
        removed_solution_kg=0.1,
        hcl_added_kg=2.0,
        nh4oh_added_kg=3.0,
        volume_m3=volume,
        ph=ph,
    )


def test_thesis_quirk_stores_returned_volume_in_ph_and_keeps_volume() -> None:
    plant = simulation._start_plant(np.random.default_rng(0))
    volume_before = plant.fluxing.volume_m3
    simulation._apply_flux_result(plant, plant.fluxing, _flux_result(volume=13.0, ph=4.4))
    assert plant.fluxing.ph == 13.0
    assert plant.fluxing.volume_m3 == volume_before


def test_corrected_mode_stores_volume_and_ph_as_intended() -> None:
    plant = simulation._start_plant(np.random.default_rng(0))
    plant.preserve_thesis_quirks = False
    simulation._apply_flux_result(plant, plant.fluxing, _flux_result(volume=13.0, ph=4.4))
    assert (plant.fluxing.volume_m3, plant.fluxing.ph) == (13.0, 4.4)
    assert plant.totals.hcl_added_kg == 2.0 and plant.totals.nh4oh_added_kg == 3.0


def test_rinse_is_renewed_only_when_the_replacement_quota_is_reached() -> None:
    rng = np.random.default_rng(0)
    tank = simulation._new_rinse_tank(rng, 22.0)
    incoming = np.array([10.0, 90.0, 0.0, 0.0])
    simulation._rinse(tank, 5.0, incoming, processed=100, items=54000, rng=rng)
    assert tank.ledger.n_final == 0
    simulation._rinse(tank, 5.0, incoming, processed=1000, items=54000, rng=rng)
    assert tank.ledger.n_final == 1


def test_rinse_mixes_dragged_out_solution_by_mass() -> None:
    rng = np.random.default_rng(0)
    tank = simulation._new_rinse_tank(rng, 22.0)
    mass_before = tank.mass_kg
    simulation._rinse(tank, 10.0, np.array([100.0, 0.0, 0.0, 0.0]), processed=1, items=54000, rng=rng)
    assert tank.mass_kg == pytest.approx(mass_before + 10.0)
    assert tank.composition_wt[0] == pytest.approx(100.0 * 10.0 / (mass_before + 10.0))


def test_reprocessing_selection_keeps_roughly_two_percent() -> None:
    indices = np.arange(200000)
    selected = simulation._select_for_reprocessing(indices, np.random.default_rng(0))
    assert 0.018 < selected.size / indices.size < 0.022


def test_corrected_mode_bleeds_fluxing_overflow_to_the_spent_stream() -> None:
    plant = simulation._start_plant(np.random.default_rng(0))
    plant.preserve_thesis_quirks = False
    bath = plant.fluxing
    assert bath.capacity_m3 is not None
    bath.volume_m3 = bath.capacity_m3 * 2
    mass_before = bath.mass_kg
    simulation._bleed_fluxing_overflow(plant)
    assert bath.volume_m3 == bath.capacity_m3
    assert plant.fluxing_bleed_kg.sum() == pytest.approx(mass_before - bath.mass_kg)


def test_thesis_mode_never_bleeds() -> None:
    year = simulate_year(SMALL_YEAR_ITEMS, np.random.default_rng(0))
    np.testing.assert_array_equal(year.fluxing_bleed_kg, np.zeros(9))
