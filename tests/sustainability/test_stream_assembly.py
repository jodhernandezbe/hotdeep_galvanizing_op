"""Tests for the GREENSCOPE stream assembly."""

from dataclasses import replace

import numpy as np
import pytest

from src.process.plant import BathLedger, LineTotals
from src.process.simulation import YearResult, simulate_year
from src.sustainability.stream_assembly import build_balance
from src.sustainability.streams import Compound, InputStream, OutputStream, UnitProcess


def _ledger(initial_mass: float, initial: list[float], final_mass: float, final: list[float], n: int = 1) -> BathLedger:
    ledger = BathLedger(initial_mass, np.array(initial))
    ledger.retire(final_mass, np.array(final))
    ledger.n_initial = n
    ledger.initial_composition_sum = np.array(initial) * n
    ledger.final_composition_sum = np.array(final) * n
    ledger.n_final = n
    return ledger


@pytest.fixture()
def hand_year() -> YearResult:
    totals = LineTotals(
        steel_kg=1000.0,
        rust_kg=5.0,
        grease_and_oil_kg=0.01,
        grease_mw_sum=3000.0,
        n_lots=3,
        steel_surface_kg=40.0,
        remaining_grease_kg=0.003,
        zinc_coating_kg=60.0,
        dross_kg=7.0,
        ash_kg=8.0,
        molten_zinc_kg=500.0,
        hcl_added_kg=2.0,
        nh4oh_added_kg=3.0,
        degreasing_heat_j=1e6,
        fluxing_heat_j=2e6,
        drying_heat_j=3e6,
        galvanizing_heat_j=4e6,
    )
    return YearResult(
        totals=totals,
        degreasing=_ledger(1000.0, [15, 85, 0, 0], 990.0, [10, 80, 5, 5]),
        rinse_1=_ledger(2000.0, [0, 100, 0, 0], 2100.0, [1, 97, 1, 1], n=2),
        normal_pickling=_ledger(5000.0, [17, 83, 0], 4900.0, [10, 70, 20]),
        abnormal_pickling=_ledger(400.0, [3, 97, 0, 0], 390.0, [1, 90, 5, 4]),
        rinse_2=_ledger(3000.0, [0, 100, 0, 0], 3050.0, [2, 98, 0, 0], n=2),
        fluxing=_ledger(1000.0, [10, 5, 0, 8, 77, 0, 0, 0, 0], 900.0, [10, 4, 2, 6, 70, 1, 0, 5, 2]),
    )


def test_steel_and_galvanized_rows_match_totals(hand_year: YearResult) -> None:
    balance = build_balance(hand_year)
    steel_row = balance.input_streams[InputStream.STEEL_PIECE]
    assert (steel_row[Compound.STEEL], steel_row[Compound.TRIGLYCERIDE], steel_row[Compound.WUSTITE]) == (1000.0, 0.01, 5.0)
    product = balance.output_streams[OutputStream.GALVANIZED_STEEL]
    assert (product[Compound.STEEL], product[Compound.ZINC]) == (1000.0, 60.0)
    assert balance.input_streams[InputStream.MOLTEN_ZINC, Compound.ZINC] == 500.0


def test_degreasing_inputs_split_commercial_caustic_and_water(hand_year: YearResult) -> None:
    balance = build_balance(hand_year).input_streams
    assert balance[InputStream.DEGREASING_SOLUTION, Compound.SODIUM_HYDROXIDE] == pytest.approx(150.0)
    assert balance[InputStream.DEGREASING_SOLUTION, Compound.WATER] == pytest.approx(150.0)
    assert balance[InputStream.DEGREASING_WATER, Compound.WATER] == pytest.approx(850.0 - 150.0)


def test_pickling_inputs_combine_both_baths_with_commercial_37_percent_acid(hand_year: YearResult) -> None:
    balance = build_balance(hand_year).input_streams
    acid = 0.01 * 17 * 5000 + 0.01 * 3 * 400
    assert balance[InputStream.PICKLING_SOLUTION, Compound.HYDROCHLORIC_ACID] == pytest.approx(acid)
    assert balance[InputStream.PICKLING_SOLUTION, Compound.WATER] == pytest.approx(acid * 0.63 / 0.37)
    assert balance[InputStream.PICKLING_WATER, Compound.WATER] == pytest.approx(5400.0 - acid - acid * 0.63 / 0.37)


def test_fluxing_inputs_convert_ions_to_salts_and_add_corrections(hand_year: YearResult) -> None:
    balance = build_balance(hand_year).input_streams
    assert balance[InputStream.FLUXING_SALTS, Compound.ZINC_DICHLORIDE] == pytest.approx(0.01 * 5 * 1000 * 136.315 / 65.409)
    assert balance[InputStream.FLUXING_SALTS, Compound.AMMONIUM_CHLORIDE] == pytest.approx(0.01 * 8 * 1000 * 53.4913 / 18.0383)
    assert balance[InputStream.FLUXING_WATER, Compound.WATER] == pytest.approx(770.0)
    assert balance[InputStream.FLUXING_NH4OH, Compound.WATER] == pytest.approx(3.0 * 0.7 / 0.3)
    assert balance[InputStream.FLUXING_HCL, Compound.WATER] == pytest.approx(2.0 * 0.63 / 0.37)


def test_fluxing_bleed_joins_spent_flux_and_sludge_outputs(hand_year: YearResult) -> None:
    bleed = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 0.0, 7.0, 8.0])
    bled_year = replace(hand_year, fluxing_bleed_kg=bleed)
    base = build_balance(hand_year)
    bled = build_balance(bled_year)
    out_delta = bled.output_streams - base.output_streams
    assert out_delta[OutputStream.SPENT_FLUXING, Compound.WATER] == pytest.approx(5.0)
    assert out_delta[OutputStream.SPENT_FLUXING, Compound.ZINC_DICHLORIDE] == pytest.approx(2.0 * 136.315 / 65.409)
    assert out_delta[OutputStream.SPENT_FLUXING, Compound.AMMONIUM_CHLORIDE] == pytest.approx(4.0 * 53.4913 / 18.0383)
    assert out_delta[OutputStream.HYDROXIDE_SLUDGE, Compound.AMMONIUM_HYDROXIDE] == pytest.approx(6.0)
    assert out_delta[OutputStream.HYDROXIDE_SLUDGE, Compound.ZINC_HYDROXIDE] == pytest.approx(3.0)
    assert out_delta[OutputStream.HYDROXIDE_SLUDGE, Compound.FERROUS_HYDROXIDE] == pytest.approx(8.0)
    assert bled.fe2_fluxing_kg - base.fe2_fluxing_kg == pytest.approx(7.0)


def test_output_streams_use_average_final_composition_and_final_mass(hand_year: YearResult) -> None:
    out = build_balance(hand_year).output_streams
    assert out[OutputStream.SPENT_DEGREASING, Compound.SODIUM_HYDROXIDE] == pytest.approx(0.01 * 10 * 990)
    assert out[OutputStream.RINSING_1_WASTEWATER, Compound.GLYCEROL] == pytest.approx(0.01 * 1 * 2100)
    assert out[OutputStream.SPENT_PICKLING, Compound.HYDROCHLORIC_ACID] == pytest.approx(0.01 * 10 * 4900 + 0.01 * 1 * 390)
    assert out[OutputStream.RINSING_2_WASTEWATER, Compound.WATER] == pytest.approx(0.01 * 98 * 3050)
    assert out[OutputStream.HYDROXIDE_SLUDGE, Compound.FERROUS_HYDROXIDE] == pytest.approx(0.01 * 2 * 900)
    assert out[OutputStream.SPENT_FLUXING, Compound.ZINC_DICHLORIDE] == pytest.approx(0.01 * 4 * 900 * 136.315 / 65.409)
    assert out[OutputStream.REMAINING_GREASE, Compound.TRIGLYCERIDE] == 0.003
    assert (out[OutputStream.DROSS, Compound.DROSS], out[OutputStream.ASH, Compound.ASH]) == (7.0, 8.0)


def test_energy_vector_and_auxiliary_quantities(hand_year: YearResult) -> None:
    balance = build_balance(hand_year)
    expected = np.zeros(7)
    expected[[UnitProcess.DEGREASING, UnitProcess.FLUXING, UnitProcess.DRYING, UnitProcess.GALVANIZING]] = 1e6, 2e6, 3e6, 4e6
    np.testing.assert_array_equal(balance.energy_j, expected)
    assert balance.grease_mw == pytest.approx(1000.0)
    assert balance.sodium_carboxylate_mw == pytest.approx(1000.0 - 41.0716 + 3 * 22.9898)
    assert balance.fe2_pickling_kg == pytest.approx(0.01 * 20 * 4900)
    assert balance.fe2_fluxing_kg == pytest.approx(0.01 * 5 * 900)
    assert balance.steel_surface_kg == 40.0


def test_simulated_year_balance_has_expected_shapes_and_nonnegative_masses() -> None:
    balance = build_balance(simulate_year(5000, np.random.default_rng(0)))
    assert balance.input_streams.shape == (12, 17) and balance.output_streams.shape == (10, 17)
    assert balance.input_streams.min() >= 0 and balance.output_streams.min() >= 0
