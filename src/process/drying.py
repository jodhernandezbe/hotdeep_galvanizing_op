"""Drying oven between fluxing and galvanizing.

Purpose: heat required to dry the fluxed steel (thesis annex D.3, step 6).
Author: Jose D. Hernandez-Betancur
Date: 2026-10-02
"""

from typing import Final

from src.common.constants import STEEL_HEAT_CAPACITY

DRYING_TEMPERATURE_C: Final = 100.0
FLUX_HEAT_CAPACITY: Final = 96.232
FLUX_EVAPORATION_HEAT_J_PER_KG: Final = 22570600.0


def drying_heat_j(
    steel_mass_kg: float,
    carried_flux_kg: float,
    flux_temperature_c: float,
    flux_evaporating_wt: float,
) -> float:
    """Heat to bring steel and dragged-out flux to the oven temperature and evaporate the flux liquid.

    Args:
        steel_mass_kg: Steel mass dried [kg].
        carried_flux_kg: Fluxing solution dragged out with the steel [kg].
        flux_temperature_c: Fluxing bath temperature [degC].
        flux_evaporating_wt: Concentration [% wt] of the flux component the thesis evaporates (column 4, NH4+).

    Returns:
        Heat [J].
    """
    sensible = (steel_mass_kg * STEEL_HEAT_CAPACITY + FLUX_HEAT_CAPACITY * carried_flux_kg) * (
        DRYING_TEMPERATURE_C - flux_temperature_c
    )
    return sensible + FLUX_EVAPORATION_HEAT_J_PER_KG * 0.01 * flux_evaporating_wt * carried_flux_kg
