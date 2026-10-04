"""GREENSCOPE indicators for the hot-dip galvanizing unit processes.

Purpose: compute the 17 selected indicators for the 7 unit processes together with their best and worst
reference values and the resulting GREENSCOPE scores (thesis annex D.4).
Author: Jose D. Hernandez-Betancur
Date: 2026-10-02
"""

import logging
from dataclasses import dataclass
from enum import IntEnum
from typing import Mapping

import numpy as np

from src.common.constants import MW_FE, MW_FECL2, MW_FEO, MW_H, MW_HCL, MW_NAOH, MW_ZN
from src.process.densities import hcl_solution_density, naoh_solution_density
from src.sustainability.costs import THESIS_COSTS, CostParameters, default_costs
from src.sustainability.hazard import ACUTE_TOXICITY, AIR_HAZARD, WATER_HAZARD, compute_physical_values
from src.sustainability.streams import (
    N_COMPOUNDS,
    N_INDICATORS,
    N_INPUT_STREAMS,
    N_OUTPUT_STREAMS,
    N_UNIT_PROCESSES,
    Compound,
    InputStream,
    OutputStream,
    UnitProcess,
)

logger = logging.getLogger(__name__)

PRESERVE_THESIS_QUIRKS = True


class Indicator(IntEnum):
    """Column index (0-based) of each GREENSCOPE indicator."""

    ACUTE_TOXICITY = 0
    AIR_HAZARD = 1
    WATER_HAZARD = 2
    GLOBAL_WARMING = 3
    PHOTOCHEMICAL_OXIDATION = 4
    ATMOSPHERIC_ACIDIFICATION = 5
    POLLUTED_LIQUID_VOLUME = 6
    HAZARDOUS_SOLID_WASTE = 7
    SOLID_WASTE_MASS = 8
    SPECIFIC_LIQUID_VOLUME = 9
    RECYCLING_MASS_FRACTION = 10
    ATOM_ECONOMY = 11
    ENVIRONMENTAL_FACTOR = 12
    RECYCLED_MATERIAL_FRACTION = 13
    WATER_CONSUMPTION = 14
    ENERGY_INTENSITY = 15
    MANUFACTURING_COST = 16


_PF_CO2 = np.zeros(N_COMPOUNDS)
_PF_ETHYLENE = np.zeros(N_COMPOUNDS)
_PF_SO2 = np.zeros(N_COMPOUNDS)
_PF_SO2[Compound.HYDROCHLORIC_ACID] = 0.88
_PF_SO2[Compound.AMMONIUM_HYDROXIDE] = 1.88
_PF_HYDROELECTRIC = 4.0
_NATURAL_GAS_FACTOR = 25 * 1e-6 / 1.99714
GRID_CO2_KG_PER_KWH_UPME_2024 = 0.220
"""Colombian grid (SIN) emission factor for GHG inventories, UPME 2024 [kgCO2e/kWh]."""
NATURAL_GAS_CO2_KG_PER_J = 56.06e-9 / 0.737
"""Colombian generic natural gas, FECOC/UPME (56.06 kgCO2/GJ of fuel) over the thesis boiler efficiency [kgCO2/J of duty]."""
_JOULE_TO_KWH = 2.78e-7
_FLUXING_SOLUTION_DENSITY = 1030.0
_WATER_DENSITY = 1000.0
_REFERENCE_TEMPERATURE_C = 25.0

_GAS_HEATED_UNITS = (UnitProcess.DEGREASING, UnitProcess.FLUXING, UnitProcess.GALVANIZING)
_ALL_COLUMNS = np.arange(N_COMPOUNDS)

_OUTPUT_ROWS: dict[UnitProcess, slice] = {
    UnitProcess.DEGREASING: slice(0, 2),
    UnitProcess.RINSING_1: slice(2, 3),
    UnitProcess.PICKLING: slice(3, 4),
    UnitProcess.RINSING_2: slice(4, 5),
    UnitProcess.FLUXING: slice(5, 7),
    UnitProcess.GALVANIZING: slice(7, 9),
}
_HAZARD_OUTPUT_ROWS: dict[UnitProcess, slice] = {**_OUTPUT_ROWS, UnitProcess.DEGREASING: slice(0, 1)}
_HAZARD_INPUT_ROWS: dict[UnitProcess, slice] = {
    UnitProcess.DEGREASING: slice(0, 3),
    UnitProcess.RINSING_1: slice(3, 4),
    UnitProcess.PICKLING: slice(4, 6),
    UnitProcess.RINSING_2: slice(6, 7),
    UnitProcess.FLUXING: slice(7, 11),
    UnitProcess.GALVANIZING: slice(11, 12),
}
_HAZARD_OUTPUT_COLUMNS: dict[UnitProcess, np.ndarray] = {
    UnitProcess.DEGREASING: np.array([5, 6]),
    UnitProcess.RINSING_1: np.delete(_ALL_COLUMNS, [4]),
    UnitProcess.PICKLING: np.delete(_ALL_COLUMNS, [4, 7]),
    UnitProcess.RINSING_2: np.delete(_ALL_COLUMNS, [4]),
    UnitProcess.FLUXING: np.array([0, 1, 2, 3, 5, 6, 8, 9, 13, 14, 15, 16]),
    UnitProcess.GALVANIZING: _ALL_COLUMNS,
}

_FIXED_CAPITAL = np.array([80920 + 184275, 80920, 80920 * 2 + 184275, 80920, 80920, 60690, 1000000], dtype=float)
_ENERGY_UNIT_COST = 0.45 * _JOULE_TO_KWH / (15.75 * 0.737)


@dataclass(frozen=True)
class GreenscopeResult:
    """GREENSCOPE outcome per unit process (rows) and indicator (columns).

    Attributes:
        indicators: Indicator values G_I, shape (7, 17).
        best: Best reference values, shape (7, 17).
        worst: Worst reference values, shape (7, 17).
        score: Scores in percent, shape (7, 17).
    """

    indicators: np.ndarray
    best: np.ndarray
    worst: np.ndarray
    score: np.ndarray


@dataclass(frozen=True)
class _Balance:
    inputs: np.ndarray
    outputs: np.ndarray
    energy_j: np.ndarray
    phys: np.ndarray
    grease_mw: float
    fe2_pickling_kg: float
    fe2_fluxing_kg: float
    surface_mass_kg: float
    costs: CostParameters = THESIS_COSTS
    gas_co2_kg_per_j: float = _NATURAL_GAS_FACTOR
    grid_co2_kg_per_kwh: float = _PF_HYDROELECTRIC
    fed_atom_economy: bool = False

    @property
    def product(self) -> float:
        return float(self.outputs[OutputStream.GALVANIZED_STEEL].sum())

    def output_mass(self, unit: UnitProcess) -> np.ndarray:
        rows = _OUTPUT_ROWS.get(unit)
        return np.zeros(N_COMPOUNDS) if rows is None else self.outputs[rows].sum(axis=0)

    def water_in(self, rows: slice) -> float:
        return float(self.inputs[rows, Compound.WATER].sum())


def _unit_vector(values: Mapping[UnitProcess, float]) -> np.ndarray:
    vector = np.zeros(N_UNIT_PROCESSES)
    for unit, value in values.items():
        vector[unit] = value
    return vector


def _constant(value: float) -> np.ndarray:
    return np.full(N_UNIT_PROCESSES, float(value))


def _hazard_with_inputs(bal: _Balance, category: int) -> np.ndarray:
    factors = bal.phys[:, category]
    result = np.zeros(N_UNIT_PROCESSES)
    for unit, columns in _HAZARD_OUTPUT_COLUMNS.items():
        outputs = bal.outputs[_HAZARD_OUTPUT_ROWS[unit]].sum(axis=0)
        inputs = bal.inputs[_HAZARD_INPUT_ROWS[unit]].sum(axis=0)
        result[unit] = (inputs @ factors + outputs[columns] @ factors[columns]) / bal.product
    return result


def _water_hazard(bal: _Balance) -> np.ndarray:
    factors = bal.phys[:, WATER_HAZARD]
    return _unit_vector({unit: float(bal.output_mass(unit) @ factors) / bal.product for unit in _OUTPUT_ROWS})


def _emission_indicator(bal: _Balance, factors: np.ndarray, include_energy: bool) -> np.ndarray:
    result = np.zeros(N_UNIT_PROCESSES)
    for unit in _OUTPUT_ROWS:
        total = bal.output_mass(unit) @ factors
        if include_energy and unit in _GAS_HEATED_UNITS:
            total += bal.energy_j[unit] * bal.gas_co2_kg_per_j
        result[unit] = total / bal.product
    if include_energy:
        result[UnitProcess.DRYING] = bal.grid_co2_kg_per_kwh * bal.energy_j[UnitProcess.DRYING] * _JOULE_TO_KWH / bal.product
    return result


def _recovered_liquid_state(bal: _Balance) -> tuple[float, float, float, float]:
    spent_naoh = bal.outputs[OutputStream.SPENT_DEGREASING]
    spent_hcl = bal.outputs[OutputStream.SPENT_PICKLING]
    naoh = spent_naoh[Compound.SODIUM_HYDROXIDE]
    hcl = spent_hcl[Compound.HYDROCHLORIC_ACID]
    naoh_left = spent_naoh.sum() - 0.6 * naoh
    hcl_left = spent_hcl.sum() - 0.55 * hcl
    rho_naoh = naoh_solution_density(_REFERENCE_TEMPERATURE_C, 0.4 * naoh * 100 / naoh_left)
    rho_hcl = hcl_solution_density(_REFERENCE_TEMPERATURE_C, 0.45 * hcl * 100 / hcl_left)
    return naoh_left, rho_naoh, hcl_left, rho_hcl


def _polluted_liquid_volume(bal: _Balance) -> np.ndarray:
    naoh_left, rho_naoh, hcl_left, rho_hcl = _recovered_liquid_state(bal)
    fluxing = bal.outputs[OutputStream.SPENT_FLUXING].sum()
    return _unit_vector(
        {
            UnitProcess.DEGREASING: naoh_left / rho_naoh,
            UnitProcess.PICKLING: hcl_left / rho_hcl,
            UnitProcess.FLUXING: fluxing / _FLUXING_SOLUTION_DENSITY,
        },
    )


def _hazardous_solid_waste(bal: _Balance) -> np.ndarray:
    grease = bal.outputs[OutputStream.REMAINING_GREASE, Compound.TRIGLYCERIDE]
    return _unit_vector({UnitProcess.DEGREASING: grease / bal.product})


def _solid_waste_mass(bal: _Balance) -> np.ndarray:
    grease = bal.outputs[OutputStream.REMAINING_GREASE, Compound.TRIGLYCERIDE]
    sludge = bal.outputs[OutputStream.HYDROXIDE_SLUDGE].sum()
    dross = bal.outputs[OutputStream.DROSS, Compound.DROSS]
    ash = bal.outputs[OutputStream.ASH, Compound.ASH]
    return _unit_vector(
        {
            UnitProcess.DEGREASING: grease / bal.product,
            UnitProcess.FLUXING: sludge / bal.product,
            UnitProcess.GALVANIZING: (dross + ash) / bal.product,
        },
    )


def _specific_liquid_volume(bal: _Balance) -> np.ndarray:
    naoh_left, rho_naoh, hcl_left, rho_hcl = _recovered_liquid_state(bal)
    out = bal.outputs
    water_rinse_1 = out[OutputStream.RINSING_1_WASTEWATER]
    water_rinse_2 = out[OutputStream.RINSING_2_WASTEWATER]
    fluxing = out[OutputStream.SPENT_FLUXING].sum()
    p = bal.product
    return _unit_vector(
        {
            UnitProcess.DEGREASING: naoh_left / (p * rho_naoh),
            UnitProcess.RINSING_1: (water_rinse_1.sum() - 0.4 * water_rinse_1[Compound.WATER]) / (p * _WATER_DENSITY),
            UnitProcess.PICKLING: hcl_left / (p * rho_hcl),
            UnitProcess.RINSING_2: (water_rinse_2.sum() - 0.4 * water_rinse_2[Compound.WATER]) / (p * _WATER_DENSITY),
            UnitProcess.FLUXING: fluxing / (p * _FLUXING_SOLUTION_DENSITY),
        },
    )


def _recycling_mass_fraction() -> np.ndarray:
    return np.array([0, 1, 1, 1, 0, 1, 0], dtype=float)


def _atom_economy(bal: _Balance) -> np.ndarray:
    inp, out = bal.inputs, bal.outputs
    rust = inp[InputStream.STEEL_PIECE, Compound.WUSTITE]
    fe_in_rust = rust * MW_FE / MW_FEO
    soap = (bal.grease_mw + 3 * MW_NAOH) * (inp[InputStream.STEEL_PIECE, Compound.TRIGLYCERIDE] / bal.grease_mw)
    return _unit_vector(
        {
            UnitProcess.DEGREASING: out[OutputStream.SPENT_DEGREASING, Compound.SODIUM_CARBOXYLATES] / soap,
            UnitProcess.RINSING_1: 1.0,
            UnitProcess.PICKLING: (
                _acid_unit_atom_economy(
                    bal.fe2_pickling_kg, 0.8825 * rust, inp[InputStream.PICKLING_SOLUTION, Compound.HYDROCHLORIC_ACID]
                )
                if bal.fed_atom_economy
                else MW_FE * bal.fe2_pickling_kg / ((MW_FEO + 2 * MW_HCL) * 0.8825 * fe_in_rust)
            ),
            UnitProcess.RINSING_2: 1.0,
            UnitProcess.FLUXING: MW_FE * bal.fe2_fluxing_kg / ((MW_FEO + 2 * MW_H) * 0.1175 * fe_in_rust),
            UnitProcess.DRYING: 1.0,
            UnitProcess.GALVANIZING: _galvanizing_atom_economy(bal),
        },
    )


def _acid_unit_atom_economy(fe2_kg: float, rust_kg: float, acid_fed_kg: float) -> float:
    product_kg = fe2_kg * MW_FECL2 / MW_FE
    reagents_kg = rust_kg + acid_fed_kg
    return product_kg / reagents_kg if reagents_kg > 0 else 1.0


def _galvanizing_atom_economy(bal: _Balance) -> float:
    coating = bal.outputs[OutputStream.GALVANIZED_STEEL, Compound.ZINC]
    return coating / ((3 * MW_FE + 10 * MW_ZN) * bal.surface_mass_kg / (3 * MW_FE))


def _environmental_factor(bal: _Balance) -> np.ndarray:
    non_water = np.delete(_ALL_COLUMNS, [Compound.WATER])
    return _unit_vector({unit: bal.output_mass(unit)[non_water].sum() / bal.product for unit in _OUTPUT_ROWS})


def _recycled_material_fraction(bal: _Balance) -> np.ndarray:
    inp, out = bal.inputs, bal.outputs
    return _unit_vector(
        {
            UnitProcess.DEGREASING: 0.6 * out[0, Compound.SODIUM_HYDROXIDE] / inp[0:3, 1:].sum(),
            UnitProcess.RINSING_1: 0.4 * out[2, Compound.WATER] / inp[3, Compound.WATER],
            UnitProcess.PICKLING: 0.55 * out[3, Compound.HYDROCHLORIC_ACID] / inp[4:6, 1:].sum(),
            UnitProcess.RINSING_2: 0.4 * out[4, Compound.WATER] / inp[6, Compound.WATER],
            UnitProcess.DRYING: 1.0,
        },
    )


def _water_consumption(bal: _Balance) -> np.ndarray:
    out = bal.outputs
    return _unit_vector(
        {
            UnitProcess.DEGREASING: bal.water_in(slice(1, 3)) / _WATER_DENSITY,
            UnitProcess.RINSING_1: (bal.water_in(slice(3, 4)) - 0.4 * out[2, Compound.WATER]) / _WATER_DENSITY,
            UnitProcess.PICKLING: bal.water_in(slice(4, 6)) / _WATER_DENSITY,
            UnitProcess.RINSING_2: (bal.water_in(slice(6, 7)) - 0.4 * out[4, Compound.WATER]) / _WATER_DENSITY,
            UnitProcess.FLUXING: bal.water_in(slice(8, 11)) / _WATER_DENSITY,
        },
    )


def _energy_intensity(bal: _Balance) -> np.ndarray:
    energy, p = bal.energy_j, bal.product
    heating = (2.5512 / 1.99714) * 1e-6 / p
    return _unit_vector(
        {
            UnitProcess.DEGREASING: heating * energy[UnitProcess.DEGREASING],
            UnitProcess.FLUXING: heating * energy[UnitProcess.FLUXING],
            UnitProcess.DRYING: (10.3 / 3.6) * energy[UnitProcess.DRYING] * 1e-6 / p,
            UnitProcess.GALVANIZING: energy[UnitProcess.GALVANIZING] * 1e-6 / p,
        },
    )


def _raw_material_cost(bal: _Balance) -> np.ndarray:
    inp, c = bal.inputs, bal.costs.raw_material_prices
    water = c["h2o"] * 1e-3
    cost = np.zeros(N_UNIT_PROCESSES)
    cost[UnitProcess.DEGREASING] = (c["naoh"] * inp[1].sum() + c["h2o"] * inp[2, Compound.WATER]) * 1e-3
    cost[UnitProcess.RINSING_1] = water * inp[3, Compound.WATER]
    cost[UnitProcess.PICKLING] = (c["hcl"] * inp[4].sum() + c["h2o"] * inp[5, Compound.WATER]) * 1e-3
    cost[UnitProcess.RINSING_2] = water * inp[6, Compound.WATER]
    cost[UnitProcess.FLUXING] = _fluxing_material_cost(inp, c)
    cost[UnitProcess.GALVANIZING] = c["zn"] * inp[11, Compound.ZINC] * 1e-3
    return cost


def _fluxing_material_cost(inp: np.ndarray, c: dict[str, float]) -> float:
    return (
        c["zncl2"] * inp[7, Compound.ZINC_DICHLORIDE]
        + c["nh4cl"] * inp[7, Compound.AMMONIUM_CHLORIDE]
        + c["h2o"] * inp[8, Compound.WATER]
        + c["hcl"] * inp[10].sum()
        + c["nh4oh"] * inp[9].sum()
    ) * 1e-3


def raw_material_masses_kg(input_streams: np.ndarray) -> np.ndarray:
    """Total raw-material purchases of the year, in the order of `RAW_MATERIAL_KEYS` [kg].

    The picks mirror `_raw_material_cost`, so the raw-material part of COM is
    `1.23e-3 * (prices @ masses)` and the COM of another price scenario can be recomputed exactly
    without re-simulating, as long as water, energy and labor prices stay the same.

    Args:
        input_streams: Input mass matrix [kg], shape (12, 17); rows per ``InputStream``.

    Returns:
        Masses of [naoh, hcl, nh4cl, zncl2, zn, h2o, nh4oh], shape (7,).
    """
    inp = np.asarray(input_streams, dtype=float)
    water = inp[[2, 3, 5, 6, 8], Compound.WATER].sum()
    return np.array(
        [
            inp[1].sum(),
            inp[4].sum() + inp[10].sum(),
            inp[7, Compound.AMMONIUM_CHLORIDE],
            inp[7, Compound.ZINC_DICHLORIDE],
            inp[11, Compound.ZINC],
            water,
            inp[9].sum(),
        ]
    )


def _utility_cost(bal: _Balance) -> np.ndarray:
    energy = bal.energy_j
    cost = np.zeros(N_UNIT_PROCESSES)
    for unit in _GAS_HEATED_UNITS:
        cost[unit] = _ENERGY_UNIT_COST * energy[unit]
    cost[UnitProcess.DRYING] = 0.17 * energy[UnitProcess.DRYING] * _JOULE_TO_KWH
    return cost


def _waste_treatment_cost(bal: _Balance) -> np.ndarray:
    out, water = bal.outputs, bal.costs.raw_material_prices["h2o"]
    naoh = out[OutputStream.SPENT_DEGREASING, Compound.SODIUM_HYDROXIDE]
    hcl = out[OutputStream.SPENT_PICKLING, Compound.HYDROCHLORIC_ACID]
    return _unit_vector(
        {
            UnitProcess.DEGREASING: (water * 1 * naoh + 0.17 * 10 * naoh) / 2100,
            UnitProcess.RINSING_1: 0.001192 * out[OutputStream.RINSING_1_WASTEWATER].sum() * 264 / 1000,
            UnitProcess.PICKLING: (water * 1 * hcl + 0.17 * 10 * hcl) / 1190,
            UnitProcess.RINSING_2: 0.001192 * out[OutputStream.RINSING_2_WASTEWATER].sum() * 264 / 1000,
        },
    )


def _manufacturing_cost(bal: _Balance) -> np.ndarray:
    variable = _raw_material_cost(bal) + _utility_cost(bal) + _waste_treatment_cost(bal)
    return 0.280 * _FIXED_CAPITAL + 2.73 * bal.costs.labor_usd_per_year + 1.23 * variable


def _emission_columns(bal: _Balance, preserve_quirks: bool) -> dict[Indicator, np.ndarray]:
    """Thesis quirk: the listing writes the SO2 column over the photochemical one and leaves acidification empty."""
    photochemical = _emission_indicator(bal, _PF_ETHYLENE, include_energy=False)
    acidification = _emission_indicator(bal, _PF_SO2, include_energy=False)
    return {
        Indicator.GLOBAL_WARMING: _emission_indicator(bal, _PF_CO2, include_energy=True),
        Indicator.PHOTOCHEMICAL_OXIDATION: acidification if preserve_quirks else photochemical,
        Indicator.ATMOSPHERIC_ACIDIFICATION: np.zeros(N_UNIT_PROCESSES) if preserve_quirks else acidification,
    }


def _environment_columns(bal: _Balance, preserve_quirks: bool) -> dict[Indicator, np.ndarray]:
    return {
        Indicator.ACUTE_TOXICITY: _hazard_with_inputs(bal, ACUTE_TOXICITY),
        Indicator.AIR_HAZARD: _hazard_with_inputs(bal, AIR_HAZARD),
        Indicator.WATER_HAZARD: _water_hazard(bal),
        **_emission_columns(bal, preserve_quirks),
        Indicator.POLLUTED_LIQUID_VOLUME: _polluted_liquid_volume(bal),
        Indicator.HAZARDOUS_SOLID_WASTE: _hazardous_solid_waste(bal),
        Indicator.SOLID_WASTE_MASS: _solid_waste_mass(bal),
        Indicator.SPECIFIC_LIQUID_VOLUME: _specific_liquid_volume(bal),
        Indicator.RECYCLING_MASS_FRACTION: _recycling_mass_fraction(),
    }


def _efficiency_columns(bal: _Balance) -> dict[Indicator, np.ndarray]:
    return {
        Indicator.ATOM_ECONOMY: _atom_economy(bal),
        Indicator.ENVIRONMENTAL_FACTOR: _environmental_factor(bal),
        Indicator.RECYCLED_MATERIAL_FRACTION: _recycled_material_fraction(bal),
        Indicator.WATER_CONSUMPTION: _water_consumption(bal),
    }


def _indicator_columns(bal: _Balance, preserve_quirks: bool) -> dict[Indicator, np.ndarray]:
    return {
        **_environment_columns(bal, preserve_quirks),
        **_efficiency_columns(bal),
        Indicator.ENERGY_INTENSITY: _energy_intensity(bal),
        Indicator.MANUFACTURING_COST: _manufacturing_cost(bal),
    }


def _assemble(columns: Mapping[Indicator, np.ndarray]) -> np.ndarray:
    matrix = np.zeros((N_UNIT_PROCESSES, N_INDICATORS))
    for indicator, values in columns.items():
        matrix[:, indicator] = values
    return matrix


def _worst_emission_factors(factors: np.ndarray) -> np.ndarray:
    return np.where(factors == 0, 1.0, factors)


def _worst_emissions(bal: _Balance) -> dict[Indicator, np.ndarray]:
    gwp = _emission_indicator(bal, _worst_emission_factors(_PF_CO2), include_energy=True)
    pocp = _emission_indicator(bal, _worst_emission_factors(_PF_ETHYLENE), include_energy=False)
    aap = _emission_indicator(bal, _worst_emission_factors(_PF_SO2), include_energy=False)
    pocp[UnitProcess.DRYING] = aap[UnitProcess.DRYING] = 1.0
    return {
        Indicator.GLOBAL_WARMING: gwp,
        Indicator.PHOTOCHEMICAL_OXIDATION: pocp,
        Indicator.ATMOSPHERIC_ACIDIFICATION: aap,
    }


def _worst_liquid_state(bal: _Balance) -> tuple[float, float, float, float]:
    spent_naoh = bal.outputs[OutputStream.SPENT_DEGREASING]
    spent_hcl = bal.outputs[OutputStream.SPENT_PICKLING]
    naoh_water = spent_naoh[[Compound.SODIUM_HYDROXIDE, Compound.WATER]].sum()
    c_naoh = spent_naoh[Compound.SODIUM_HYDROXIDE] * 100 / naoh_water
    c_hcl = spent_hcl[Compound.HYDROCHLORIC_ACID] * 100 / spent_hcl.sum()
    rho_naoh = naoh_solution_density(_REFERENCE_TEMPERATURE_C, c_naoh)
    rho_hcl = hcl_solution_density(_REFERENCE_TEMPERATURE_C, c_hcl)
    return spent_naoh.sum(), rho_naoh, spent_hcl.sum(), rho_hcl


def _worst_liquid_volumes(bal: _Balance) -> dict[Indicator, np.ndarray]:
    naoh_mass, rho_naoh, hcl_mass, rho_hcl = _worst_liquid_state(bal)
    out, p = bal.outputs, bal.product
    fluxing = out[OutputStream.SPENT_FLUXING].sum()
    polluted = _constant(1)
    specific = _constant(1)
    polluted[[0, 2, 4]] = [naoh_mass / rho_naoh, hcl_mass / rho_hcl, fluxing / _FLUXING_SOLUTION_DENSITY]
    specific[[0, 2, 4]] = [naoh_mass / (p * rho_naoh), hcl_mass / (p * rho_hcl), fluxing / (p * _FLUXING_SOLUTION_DENSITY)]
    specific[UnitProcess.RINSING_1] = out[OutputStream.RINSING_1_WASTEWATER].sum() / (p * _WATER_DENSITY)
    specific[UnitProcess.RINSING_2] = out[OutputStream.RINSING_2_WASTEWATER].sum() / (p * _WATER_DENSITY)
    return {Indicator.POLLUTED_LIQUID_VOLUME: polluted, Indicator.SPECIFIC_LIQUID_VOLUME: specific}


def _worst_solid_waste(bal: _Balance) -> dict[Indicator, np.ndarray]:
    hazardous = _constant(1)
    hazardous[UnitProcess.DEGREASING] = _hazardous_solid_waste(bal)[UnitProcess.DEGREASING]
    mass = _constant(1)
    actual = _solid_waste_mass(bal)
    for unit in (UnitProcess.DEGREASING, UnitProcess.FLUXING, UnitProcess.GALVANIZING):
        mass[unit] = actual[unit]
    return {Indicator.HAZARDOUS_SOLID_WASTE: hazardous, Indicator.SOLID_WASTE_MASS: mass}


def _worst_water_consumption(bal: _Balance) -> np.ndarray:
    return _unit_vector(
        {
            UnitProcess.DEGREASING: bal.water_in(slice(1, 3)) / _WATER_DENSITY,
            UnitProcess.RINSING_1: bal.water_in(slice(3, 4)) / _WATER_DENSITY,
            UnitProcess.PICKLING: bal.water_in(slice(4, 6)) / _WATER_DENSITY,
            UnitProcess.RINSING_2: bal.water_in(slice(6, 7)) / _WATER_DENSITY,
            UnitProcess.FLUXING: bal.water_in(slice(8, 11)) / _WATER_DENSITY,
            UnitProcess.DRYING: 1.0,
            UnitProcess.GALVANIZING: 1.0,
        },
    )


def _best_energy_intensity(bal: _Balance) -> np.ndarray:
    inp, p = bal.inputs, bal.product
    degreasing_feed = inp[1:3].sum()
    naoh_wt = inp[InputStream.DEGREASING_SOLUTION, Compound.SODIUM_HYDROXIDE] * 100 / degreasing_feed
    cp_naoh = -627.6 * (naoh_wt - 1.08) / 16.73 + 4121.2
    heating = (2.5512 / 1.99714) * 1e-6 / p * (50 - _REFERENCE_TEMPERATURE_C)
    molten_zinc_energy = 1000 * (0.3883 * (419.5 - 25) + 100.9 + 0.4801 * (450 - 419.5))
    steel = bal.outputs[OutputStream.GALVANIZED_STEEL, Compound.STEEL]
    return _unit_vector(
        {
            UnitProcess.DEGREASING: heating * degreasing_feed * cp_naoh,
            UnitProcess.FLUXING: heating * inp[7:11].sum() * 96.232,
            UnitProcess.DRYING: 0.5 * (10.3 / 3.6) * steel * 450 * (100 - 25) * 1e-6 / p,
            UnitProcess.GALVANIZING: 1e-6 * inp[11, Compound.ZINC] * molten_zinc_energy / p,
        },
    )


def _worst_energy_intensity(best: np.ndarray) -> np.ndarray:
    return _unit_vector(
        {
            UnitProcess.DEGREASING: 1e3 * best[UnitProcess.DEGREASING],
            UnitProcess.RINSING_1: 10.0,
            UnitProcess.PICKLING: 10.0,
            UnitProcess.RINSING_2: 10.0,
            UnitProcess.FLUXING: 1e3 * best[UnitProcess.FLUXING],
            UnitProcess.DRYING: 1e1 * best[UnitProcess.DRYING],
            UnitProcess.GALVANIZING: 1e2 * best[UnitProcess.GALVANIZING],
        },
    )


def _best_matrix(bal: _Balance, cost: np.ndarray, best_energy: np.ndarray) -> np.ndarray:
    return _assemble(
        {
            Indicator.RECYCLING_MASS_FRACTION: _constant(1),
            Indicator.ATOM_ECONOMY: _constant(1),
            Indicator.RECYCLED_MATERIAL_FRACTION: _constant(1),
            Indicator.ENERGY_INTENSITY: best_energy,
            Indicator.MANUFACTURING_COST: (0.38 / 0.85) * cost,
        },
    )


def _worst_matrix(bal: _Balance, cost: np.ndarray, best_energy: np.ndarray) -> np.ndarray:
    return _assemble(
        {
            Indicator.ACUTE_TOXICITY: _constant(1e5),
            Indicator.AIR_HAZARD: _constant(1e7),
            Indicator.WATER_HAZARD: _constant(1e5),
            **_worst_emissions(bal),
            **_worst_liquid_volumes(bal),
            **_worst_solid_waste(bal),
            Indicator.ENVIRONMENTAL_FACTOR: _constant(39),
            Indicator.WATER_CONSUMPTION: _worst_water_consumption(bal),
            Indicator.ENERGY_INTENSITY: _worst_energy_intensity(best_energy),
            Indicator.MANUFACTURING_COST: (1.7 / 0.85) * cost,
        },
    )


def _reference_matrices(bal: _Balance, indicators: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    best_energy = _best_energy_intensity(bal)
    cost = indicators[:, Indicator.MANUFACTURING_COST]
    return _best_matrix(bal, cost, best_energy), _worst_matrix(bal, cost, best_energy)


def _score(indicators: np.ndarray, best: np.ndarray, worst: np.ndarray) -> np.ndarray:
    span = best - worst
    degenerate = span == 0
    if degenerate.any():
        logger.warning(f"{int(degenerate.sum())} indicator(s) have identical best and worst values; scoring them 100")
    safe_span = np.where(degenerate, 1.0, span)
    return np.where(degenerate, 100.0, (indicators - worst) * 100 / safe_span)


def _validate_inputs(input_streams: np.ndarray, output_streams: np.ndarray, energy_j: np.ndarray) -> None:
    expected = {
        "input_streams": (input_streams, (N_INPUT_STREAMS, N_COMPOUNDS)),
        "output_streams": (output_streams, (N_OUTPUT_STREAMS, N_COMPOUNDS)),
        "energy_j": (energy_j, (N_UNIT_PROCESSES,)),
    }
    for name, (array, shape) in expected.items():
        if array.shape != shape:
            logger.error(f"{name} has shape {array.shape}, expected {shape}")
            raise ValueError(f"{name} must have shape {shape}, got {array.shape}")
    if output_streams[OutputStream.GALVANIZED_STEEL].sum() <= 0:
        logger.error("Galvanized steel output stream has no mass")
        raise ValueError("The galvanized steel output stream must have a positive mass")


def compute_greenscope(
    input_streams: np.ndarray,
    output_streams: np.ndarray,
    energy_j: np.ndarray,
    sodium_carboxylate_mw: float,
    grease_mw: float,
    fe2_mass_pickling_kg: float,
    fe2_mass_fluxing_kg: float,
    steel_surface_mass_kg: float,
    *,
    preserve_thesis_quirks: bool = PRESERVE_THESIS_QUIRKS,
    costs: CostParameters | None = None,
    fed_atom_economy: bool = False,
) -> GreenscopeResult:
    """Compute GREENSCOPE indicators, reference values and scores.

    With ``preserve_thesis_quirks=True`` (default) the thesis behaviour is reproduced: the atmospheric
    acidification potential (SO2 equivalents) overwrites the photochemical oxidation column and the
    acidification column stays at zero (annex D.4, ``G_I(:,5)`` assigned twice), and the thesis energy
    emission factors are kept. With ``False`` each indicator goes in its own column and the energy
    emission factors are the sourced ones: the UPME 2024 Colombian grid factor for the electric dryer
    and the IPCC natural-gas factor over the boiler efficiency for the gas-heated baths
    (docs/MATLAB_PORT_NOTES.md).

    Args:
        input_streams: Input mass matrix [kg], shape (12, 17); rows per ``InputStream``.
        output_streams: Output mass matrix [kg], shape (10, 17); rows per ``OutputStream``.
        energy_j: Energy consumption per unit process [J], shape (7,), indexed by ``UnitProcess``.
        sodium_carboxylate_mw: Molecular weight of the sodium carboxylates [g/mol]. Kept for interface parity
            with the MATLAB code; it cancels out of the degreasing atom economy.
        grease_mw: Molecular weight of the grease (triglyceride) [g/mol].
        fe2_mass_pickling_kg: Fe2+ mass produced in the pickling bath [kg].
        fe2_mass_fluxing_kg: Fe2+ mass produced in the fluxing bath [kg].
        steel_surface_mass_kg: Mass of the steel surface reacting with zinc [kg].
        preserve_thesis_quirks: Reproduce the thesis' column assignment for POCP/AAP.
        costs: Prices and labor of the COM indicator; `default_costs(preserve_thesis_quirks)` when None.
        fed_atom_economy: Compute the pickling atom economy over the reagents actually fed (rust
            share plus the acid charged, Ruiz-Mercado's general form) instead of the thesis'
            limiting-reagent basis, which is a rust-dissolution conversion and cannot penalize
            acid overfeeding. The fluxing unit keeps the thesis basis: its reacting iron arrives
            as an internal transfer (residual rust) and its chloride comes from the bath salts,
            so a fed-reagent denominator is not definable from the stored input streams
            (docs/MATLAB_PORT_NOTES.md).

    Returns:
        Indicators, best and worst reference values and scores, each of shape (7, 17).
    """
    inputs, outputs, energy = (np.asarray(a, dtype=float) for a in (input_streams, output_streams, energy_j))
    _validate_inputs(inputs, outputs, energy)
    balance = _Balance(
        inputs=inputs,
        outputs=outputs,
        energy_j=energy,
        phys=compute_physical_values(),
        grease_mw=grease_mw,
        fe2_pickling_kg=fe2_mass_pickling_kg,
        fe2_fluxing_kg=fe2_mass_fluxing_kg,
        surface_mass_kg=steel_surface_mass_kg,
        costs=default_costs(preserve_thesis_quirks) if costs is None else costs,
        gas_co2_kg_per_j=_NATURAL_GAS_FACTOR if preserve_thesis_quirks else NATURAL_GAS_CO2_KG_PER_J,
        grid_co2_kg_per_kwh=_PF_HYDROELECTRIC if preserve_thesis_quirks else GRID_CO2_KG_PER_KWH_UPME_2024,
        fed_atom_economy=fed_atom_economy,
    )
    indicators = _assemble(_indicator_columns(balance, preserve_thesis_quirks))
    best, worst = _reference_matrices(balance, indicators)
    return GreenscopeResult(indicators, best, worst, _score(indicators, best, worst))
