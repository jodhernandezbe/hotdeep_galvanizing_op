"""Assembly of the GREENSCOPE input/output stream matrices from a simulated year.

Purpose: translate the year summary of the line simulation into mass-balance matrices (thesis annex D.1).
Author: Jose D. Hernandez-Betancur
Date: 2026-10-02
"""

from dataclasses import dataclass
from typing import Final

import numpy as np

from src.common.constants import MW_NH4, MW_NH4CL, MW_ZN, MW_ZNCL2
from src.process.plant import BathLedger
from src.process.simulation import YearResult
from src.sustainability.streams import (
    N_COMPOUNDS,
    N_INPUT_STREAMS,
    N_OUTPUT_STREAMS,
    N_UNIT_PROCESSES,
    Compound,
    InputStream,
    OutputStream,
    UnitProcess,
)

COMMERCIAL_HCL_WATER_PER_ACID: Final = 0.63 / 0.37
COMMERCIAL_NH4OH_WATER_PER_BASE: Final = 0.7 / 0.3
GREASE_BACKBONE_MW: Final = 41.0716
SODIUM_ATOMIC_WEIGHT: Final = 22.9898
ZNCL2_PER_ZN: Final = MW_ZNCL2 / MW_ZN
NH4CL_PER_NH4: Final = MW_NH4CL / MW_NH4

DEGREASING_COMPOUNDS: Final = (
    Compound.SODIUM_HYDROXIDE,
    Compound.WATER,
    Compound.GLYCEROL,
    Compound.SODIUM_CARBOXYLATES,
)
PICKLING_HCL, PICKLING_WATER, PICKLING_IRON = 0, 1, 2
FLUX_ZINC, FLUX_ZINC_HYDROXIDE, FLUX_AMMONIUM, FLUX_WATER, FLUX_AMMONIA, FLUX_IRON, FLUX_IRON_HYDROXIDE = 1, 2, 3, 4, 5, 7, 8
FLUX_SLUDGE_COLUMNS: Final = (
    (Compound.AMMONIUM_HYDROXIDE, FLUX_AMMONIA),
    (Compound.ZINC_HYDROXIDE, FLUX_ZINC_HYDROXIDE),
    (Compound.FERROUS_HYDROXIDE, FLUX_IRON_HYDROXIDE),
)


@dataclass(frozen=True)
class ProcessBalance:
    """Everything GREENSCOPE needs about one simulated year.

    Attributes:
        input_streams: Input mass matrix [kg], shape (12, 17).
        output_streams: Output mass matrix [kg], shape (10, 17).
        energy_j: Heat consumed by each unit process [J], shape (7,).
        grease_mw: Average molecular weight of the greases [g/mol].
        sodium_carboxylate_mw: Molecular weight of the sodium carboxylates formed [g/mol].
        fe2_pickling_kg: Ferrous iron leaving with the spent pickling baths [kg].
        fe2_fluxing_kg: Ferrous iron leaving with the spent fluxing baths [kg].
        steel_surface_kg: Steel surface mass used as the zinc-iron alloy reference [kg].
    """

    input_streams: np.ndarray
    output_streams: np.ndarray
    energy_j: np.ndarray
    grease_mw: float
    sodium_carboxylate_mw: float
    fe2_pickling_kg: float
    fe2_fluxing_kg: float
    steel_surface_kg: float


def build_balance(year: YearResult) -> ProcessBalance:
    """Build the GREENSCOPE mass and energy balance of a simulated year.

    Args:
        year: Summary of the simulated year.

    Returns:
        Stream matrices and auxiliary quantities for GREENSCOPE.
    """
    grease_mw = year.totals.grease_mw_sum / year.totals.n_lots
    return ProcessBalance(
        input_streams=_input_streams(year),
        output_streams=_output_streams(year),
        energy_j=_energy(year),
        grease_mw=grease_mw,
        sodium_carboxylate_mw=grease_mw - GREASE_BACKBONE_MW + 3 * SODIUM_ATOMIC_WEIGHT,
        fe2_pickling_kg=_component_kg(year.normal_pickling, PICKLING_IRON),
        fe2_fluxing_kg=_component_kg(year.fluxing, FLUX_IRON) + float(year.fluxing_bleed_kg[FLUX_IRON]),
        steel_surface_kg=year.totals.steel_surface_kg,
    )


def _component_kg(ledger: BathLedger, column: int) -> float:
    return 0.01 * ledger.mean_final_composition_wt[column] * ledger.final_mass_kg


def _initial_component_kg(ledger: BathLedger, column: int) -> float:
    return 0.01 * ledger.mean_initial_composition_wt[column] * ledger.initial_mass_kg


def _energy(year: YearResult) -> np.ndarray:
    energy = np.zeros(N_UNIT_PROCESSES)
    energy[UnitProcess.DEGREASING] = year.totals.degreasing_heat_j
    energy[UnitProcess.FLUXING] = year.totals.fluxing_heat_j
    energy[UnitProcess.DRYING] = year.totals.drying_heat_j
    energy[UnitProcess.GALVANIZING] = year.totals.galvanizing_heat_j
    return energy


def _input_streams(year: YearResult) -> np.ndarray:
    streams = np.zeros((N_INPUT_STREAMS, N_COMPOUNDS))
    _add_pretreatment_inputs(streams, year)
    _add_pickling_inputs(streams, year)
    _add_fluxing_inputs(streams, year)
    streams[InputStream.MOLTEN_ZINC, Compound.ZINC] = year.totals.molten_zinc_kg
    return streams


def _add_pretreatment_inputs(streams: np.ndarray, year: YearResult) -> None:
    totals = year.totals
    streams[InputStream.STEEL_PIECE, [Compound.STEEL, Compound.TRIGLYCERIDE, Compound.WUSTITE]] = (
        totals.steel_kg,
        totals.grease_and_oil_kg,
        totals.rust_kg,
    )
    caustic_kg = _initial_component_kg(year.degreasing, 0)
    streams[InputStream.DEGREASING_SOLUTION, Compound.SODIUM_HYDROXIDE] = caustic_kg
    streams[InputStream.DEGREASING_SOLUTION, Compound.WATER] = caustic_kg
    streams[InputStream.DEGREASING_WATER, Compound.WATER] = _initial_component_kg(year.degreasing, 1) - caustic_kg
    streams[InputStream.RINSING_1_WATER, Compound.WATER] = year.rinse_1.initial_mass_kg
    streams[InputStream.RINSING_2_WATER, Compound.WATER] = year.rinse_2.initial_mass_kg


def _add_pickling_inputs(streams: np.ndarray, year: YearResult) -> None:
    acid_kg = _initial_component_kg(year.normal_pickling, PICKLING_HCL) + _initial_component_kg(
        year.abnormal_pickling, PICKLING_HCL
    )
    acid_water_kg = COMMERCIAL_HCL_WATER_PER_ACID * acid_kg
    bath_kg = year.normal_pickling.initial_mass_kg + year.abnormal_pickling.initial_mass_kg
    streams[InputStream.PICKLING_SOLUTION, Compound.HYDROCHLORIC_ACID] = acid_kg
    streams[InputStream.PICKLING_SOLUTION, Compound.WATER] = acid_water_kg
    streams[InputStream.PICKLING_WATER, Compound.WATER] = bath_kg - acid_kg - acid_water_kg


def _add_fluxing_inputs(streams: np.ndarray, year: YearResult) -> None:
    flux = year.fluxing
    streams[InputStream.FLUXING_SALTS, Compound.ZINC_DICHLORIDE] = _initial_component_kg(flux, FLUX_ZINC) * ZNCL2_PER_ZN
    streams[InputStream.FLUXING_SALTS, Compound.AMMONIUM_CHLORIDE] = _initial_component_kg(flux, FLUX_AMMONIUM) * NH4CL_PER_NH4
    streams[InputStream.FLUXING_WATER, Compound.WATER] = _initial_component_kg(flux, FLUX_WATER)
    ammonia_kg, acid_kg = year.totals.nh4oh_added_kg, year.totals.hcl_added_kg
    streams[InputStream.FLUXING_NH4OH, Compound.AMMONIUM_HYDROXIDE] = ammonia_kg
    streams[InputStream.FLUXING_NH4OH, Compound.WATER] = COMMERCIAL_NH4OH_WATER_PER_BASE * ammonia_kg
    streams[InputStream.FLUXING_HCL, Compound.HYDROCHLORIC_ACID] = acid_kg
    streams[InputStream.FLUXING_HCL, Compound.WATER] = COMMERCIAL_HCL_WATER_PER_ACID * acid_kg


def _output_streams(year: YearResult) -> np.ndarray:
    streams = np.zeros((N_OUTPUT_STREAMS, N_COMPOUNDS))
    _add_degreasing_outputs(streams, year)
    _add_pickling_outputs(streams, year)
    _add_fluxing_outputs(streams, year)
    totals = year.totals
    streams[OutputStream.DROSS, Compound.DROSS] = totals.dross_kg
    streams[OutputStream.ASH, Compound.ASH] = totals.ash_kg
    streams[OutputStream.GALVANIZED_STEEL, Compound.STEEL] = totals.steel_kg
    streams[OutputStream.GALVANIZED_STEEL, Compound.ZINC] = totals.zinc_coating_kg
    return streams


def _add_degreasing_outputs(streams: np.ndarray, year: YearResult) -> None:
    for column, compound in enumerate(DEGREASING_COMPOUNDS):
        streams[OutputStream.SPENT_DEGREASING, compound] = _component_kg(year.degreasing, column)
        streams[OutputStream.RINSING_1_WASTEWATER, compound] = _component_kg(year.rinse_1, column)
    streams[OutputStream.REMAINING_GREASE, Compound.TRIGLYCERIDE] = year.totals.remaining_grease_kg


def _add_pickling_outputs(streams: np.ndarray, year: YearResult) -> None:
    spent = OutputStream.SPENT_PICKLING
    for ledger in (year.normal_pickling, year.abnormal_pickling):
        streams[spent, Compound.HYDROCHLORIC_ACID] += _component_kg(ledger, PICKLING_HCL)
        streams[spent, Compound.WATER] += _component_kg(ledger, PICKLING_WATER)
    rinse = OutputStream.RINSING_2_WASTEWATER
    streams[rinse, Compound.HYDROCHLORIC_ACID] = _component_kg(year.rinse_2, PICKLING_HCL)
    streams[rinse, Compound.WATER] = _component_kg(year.rinse_2, PICKLING_WATER)


def _add_fluxing_outputs(streams: np.ndarray, year: YearResult) -> None:
    flux, bleed = year.fluxing, year.fluxing_bleed_kg
    spent = OutputStream.SPENT_FLUXING
    streams[spent, Compound.WATER] = _component_kg(flux, FLUX_WATER) + bleed[FLUX_WATER]
    streams[spent, Compound.ZINC_DICHLORIDE] = (_component_kg(flux, FLUX_ZINC) + bleed[FLUX_ZINC]) * ZNCL2_PER_ZN
    streams[spent, Compound.AMMONIUM_CHLORIDE] = (_component_kg(flux, FLUX_AMMONIUM) + bleed[FLUX_AMMONIUM]) * NH4CL_PER_NH4
    for compound, column in FLUX_SLUDGE_COLUMNS:
        streams[OutputStream.HYDROXIDE_SLUDGE, compound] = _component_kg(flux, column) + bleed[column]
