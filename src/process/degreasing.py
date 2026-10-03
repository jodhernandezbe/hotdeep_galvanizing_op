"""Degreasing bath mass and energy balance.

Purpose: saponification of greases in NaOH solution and bath heat balance (annex D.3.3).
Author: Jose D. Hernandez-Betancur
Date: 2026-10-02
"""

from dataclasses import dataclass

import numpy as np

from src.process.densities import naoh_solution_density

SAPONIFIED_FRACTION = 0.7
GLYCEROL_MW = 92.0937
TRIGLYCERIDE_BACKBONE_MW = 41.0716
CARBOXYLATE_NA_MASS = 68.9694
# The thesis listing uses 38.9971 here while every other module uses 39.9971 for NaOH; kept to reproduce its numbers.
NAOH_MW_DEGREASING = 38.9971
HEAT_LOSS_REFERENCE_DELTA_T = 35.1
HEAT_LOSS_FRACTION = 0.1
REFERENCE_TEMPERATURE_C = 25.0
WATER_CP_REFERENCE_C = 1.08
CP_SLOPE = -627.6 / 16.73
CP_INTERCEPT = 4121.2
STEEL_HEAT_CAPACITY = 450.0
REMOVED_SOLUTION_PER_STEEL = 1e-6


@dataclass(frozen=True)
class DegreasingResult:
    """Outcome of one degreasing step.

    Attributes:
        saponified_kg: Grease mass saponified [kg].
        remaining_grease_kg: Grease mass left on the steel [kg].
        heat_j: Heat supplied to the bath [J].
        solution_mass_kg: Bath mass after the step [kg].
        composition_wt: [NaOH, H2O, glycerol, sodium carboxylates] [% wt].
        temperature_c: Bath temperature after the step [degC].
        removed_solution_kg: Solution dragged out with the steel [kg].
    """

    saponified_kg: float
    remaining_grease_kg: float
    heat_j: float
    solution_mass_kg: float
    composition_wt: np.ndarray
    temperature_c: float
    removed_solution_kg: float


def degrease(
    grease_and_oil_kg: float,
    grease_mw: float,
    solution_mass_kg: float,
    composition_wt: np.ndarray,
    temperature_c: float,
    greased_steel_kg: float,
    previous_heat_j: float,
    ambient_c: float,
) -> DegreasingResult:
    """Degrease one lot of steel.

    Args:
        grease_and_oil_kg: Grease and oil mass on the lot [kg].
        grease_mw: Mean molecular weight of the grease [kg/kmol].
        solution_mass_kg: Bath mass before the step [kg].
        composition_wt: Bath composition [% wt].
        temperature_c: Bath temperature [degC].
        greased_steel_kg: Mass of greased steel immersed [kg].
        previous_heat_j: Heat accumulated in the bath [J].
        ambient_c: Ambient temperature [degC].

    Returns:
        Updated bath state and balances.
    """
    saponified = SAPONIFIED_FRACTION * grease_and_oil_kg
    removed = REMOVED_SOLUTION_PER_STEEL * greased_steel_kg * naoh_solution_density(temperature_c, composition_wt[0])
    mass, composition = _mass_balance(saponified, grease_mw, solution_mass_kg - removed, composition_wt)
    new_temperature, heat = _energy_balance(
        mass, composition_wt[0], composition[0], temperature_c, greased_steel_kg, previous_heat_j, ambient_c
    )
    return DegreasingResult(saponified, grease_and_oil_kg - saponified, heat, mass, composition, new_temperature, removed)


def _mass_balance(saponified: float, grease_mw: float, retained_mass: float, composition_wt: np.ndarray) -> tuple:
    carboxylate_mw = grease_mw - TRIGLYCERIDE_BACKBONE_MW
    retained = 0.01 * composition_wt * retained_mass
    retained[0] -= saponified * NAOH_MW_DEGREASING * 3 / grease_mw
    retained[2] += saponified * GLYCEROL_MW / grease_mw
    retained[3] += saponified * (carboxylate_mw + CARBOXYLATE_NA_MASS) / grease_mw
    mass = float(retained.sum())
    return mass, retained * (100 / mass)


def naoh_solution_heat_capacity(concentration_wt: float) -> float:
    """Heat capacity of a NaOH solution.

    Args:
        concentration_wt: NaOH concentration [% wt].

    Returns:
        Heat capacity [J/(kg*K)].
    """
    return CP_SLOPE * (concentration_wt - WATER_CP_REFERENCE_C) + CP_INTERCEPT


def _energy_balance(
    mass: float,
    naoh_before: float,
    naoh_after: float,
    temperature_c: float,
    steel_kg: float,
    previous_heat_j: float,
    ambient_c: float,
) -> tuple[float, float]:
    cp_before = naoh_solution_heat_capacity(naoh_before)
    cp_after = naoh_solution_heat_capacity(naoh_after)
    lost = abs((temperature_c - ambient_c) / HEAT_LOSS_REFERENCE_DELTA_T)
    retained_heat = (1 - HEAT_LOSS_FRACTION * lost) * mass * cp_before * (temperature_c - REFERENCE_TEMPERATURE_C)
    numerator = (
        retained_heat + REFERENCE_TEMPERATURE_C * mass * cp_after + ambient_c * steel_kg * STEEL_HEAT_CAPACITY + previous_heat_j
    )
    new_temperature = numerator / (mass * cp_after + steel_kg * STEEL_HEAT_CAPACITY)
    lost_heat = HEAT_LOSS_FRACTION * lost * mass * cp_before * (temperature_c - REFERENCE_TEMPERATURE_C)
    return new_temperature, lost_heat + steel_kg * STEEL_HEAT_CAPACITY * (new_temperature - ambient_c)
