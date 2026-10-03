"""Initial state of the pretreatment baths (degreasing, pickling and fluxing).

Purpose: random fresh-bath conditions from the thesis (annex D.3.1).
Author: Jose D. Hernandez-Betancur
Date: 2026-10-02
"""

import logging
from dataclasses import dataclass

import numpy as np

from src.common.constants import (
    GAS_CONSTANT_EQUILIBRIUM,
    KELVIN_OFFSET,
    MW_CL,
    MW_H,
    MW_H2O,
    MW_NH4,
    MW_NH4CL,
    MW_NH4OH,
    MW_ZN,
    MW_ZN_OH_2,
    MW_ZNCL2,
)
from src.process.densities import hcl_solution_density, naoh_solution_density

logger = logging.getLogger(__name__)

SALT_LOADING_KG_PER_M3 = 400.0
FLUXING_SOLUTION_DENSITY = 1030.0
ZNCL2_MASS_FRACTION = 0.6
NH4CL_MASS_FRACTION = 0.4
FLUXING_PH_MEAN = 4.5
FLUXING_PH_STD = 0.1667
ROOT_MASS_TOLERANCE = 1e-4
REFERENCE_TEMPERATURE_K = 298.15
ZN_HYDROLYSIS_K = 4.9e-12
ZN_HYDROLYSIS_ENERGY = 78680.0
NH4_DISSOCIATION_K = 5.6e-10
NH4_DISSOCIATION_ENERGY = 52140.0


@dataclass(frozen=True)
class BathInitialCondition:
    """Fresh bath state.

    Attributes:
        volume_m3: Bath volume [m3].
        composition_wt: Composition [% wt].
        mass_kg: Solution mass [kg].
        temperature_c: Bath temperature [degC] (degreasing and fluxing only).
        ph: Bath pH (fluxing only).
    """

    volume_m3: float
    composition_wt: np.ndarray
    mass_kg: float
    temperature_c: float | None = None
    ph: float | None = None


def rinsing_initial_volume(rng: np.random.Generator) -> float:
    """Draw the volume of a rinsing tank.

    Args:
        rng: Random generator.

    Returns:
        Tank volume [m3].
    """
    return _tank_volume(rng)


def degreasing_initial_condition(rng: np.random.Generator, temperature_c: float | None = None) -> BathInitialCondition:
    """Draw a fresh NaOH degreasing bath.

    Args:
        rng: Random generator.
        temperature_c: Bath temperature override [degC]; drawn from the thesis range when None.

    Returns:
        Bath state with composition [NaOH, H2O, glycerol, sodium carboxylates].
    """
    volume = _tank_volume(rng)
    naoh = 2 * rng.random() + 14
    temperature = 2.2 * rng.random() + 48.9 if temperature_c is None else temperature_c
    composition = np.array([naoh, 100 - naoh, 0.0, 0.0])
    mass = naoh_solution_density(temperature, naoh) * volume
    return BathInitialCondition(volume, composition, mass, temperature_c=temperature)


def normal_pickling_initial_condition(
    rng: np.random.Generator, ambient_c: float, hcl_pct: float | None = None
) -> BathInitialCondition:
    """Draw a fresh normal pickling bath (about 17 % HCl).

    Args:
        rng: Random generator.
        ambient_c: Ambient temperature, used to evaluate the density [degC].
        hcl_pct: HCl concentration override [% wt]; drawn from the thesis range when None.

    Returns:
        Bath state with composition [HCl, H2O, Fe2+].
    """
    return _pickling_condition(rng, ambient_c, hcl_offset=16.0, n_species=3, hcl_pct=hcl_pct)


def abnormal_pickling_initial_condition(rng: np.random.Generator, ambient_c: float) -> BathInitialCondition:
    """Draw a fresh abnormal (dezincification) pickling bath (about 3 % HCl).

    Args:
        rng: Random generator.
        ambient_c: Ambient temperature, used to evaluate the density [degC].

    Returns:
        Bath state with composition [HCl, H2O, Fe2+, Zn2+].
    """
    return _pickling_condition(rng, ambient_c, hcl_offset=2.0, n_species=4)


def fluxing_initial_condition(
    rng: np.random.Generator,
    temperature_c: float | None = None,
    ph: float | None = None,
    salt_kg_per_m3: float | None = None,
) -> BathInitialCondition:
    """Draw a fresh ZnCl2/NH4Cl fluxing bath in ionic equilibrium.

    Args:
        rng: Random generator.
        temperature_c: Bath temperature override [degC]; drawn from the thesis range when None.
        ph: Bath pH override; drawn from the thesis distribution when None.
        salt_kg_per_m3: Total salt loading override [kg/m3 = g/L]; thesis value (400) when None.

    Returns:
        Bath state with composition [Cl-, Zn2+, Zn(OH)2, NH4+, H2O, NH4OH, H+, Fe, Fe(OH)2].

    Raises:
        ValueError: If the equilibrium has no admissible root.
    """
    volume = _tank_volume(rng)
    temperature = 2.2 * rng.random() + 48.9 if temperature_c is None else temperature_c
    mass = FLUXING_SOLUTION_DENSITY * volume
    bath_ph = rng.normal(FLUXING_PH_MEAN, FLUXING_PH_STD) if ph is None else ph
    salt_loading = SALT_LOADING_KG_PER_M3 if salt_kg_per_m3 is None else salt_kg_per_m3
    composition = _fluxing_equilibrium(volume, mass, temperature, bath_ph, salt_loading)
    return BathInitialCondition(volume, composition, mass, temperature_c=temperature, ph=bath_ph)


def _tank_volume(rng: np.random.Generator) -> float:
    return (2 - 0.2 * rng.random()) * 1 * 7


def _pickling_condition(
    rng: np.random.Generator, ambient_c: float, hcl_offset: float, n_species: int, hcl_pct: float | None = None
) -> BathInitialCondition:
    volume = _tank_volume(rng)
    hcl = 2 * rng.random() + hcl_offset if hcl_pct is None else hcl_pct
    composition = np.zeros(n_species)
    composition[:2] = [hcl, 100 - hcl]
    return BathInitialCondition(volume, composition, hcl_solution_density(ambient_c, hcl) * volume)


def _equilibrium_constants(temperature_c: float) -> tuple[float, float]:
    inverse_gap = 1 / REFERENCE_TEMPERATURE_K - 1 / (temperature_c + KELVIN_OFFSET)
    k1 = ZN_HYDROLYSIS_K * np.exp(ZN_HYDROLYSIS_ENERGY / GAS_CONSTANT_EQUILIBRIUM * inverse_gap)
    k2 = NH4_DISSOCIATION_K * np.exp(NH4_DISSOCIATION_ENERGY / GAS_CONSTANT_EQUILIBRIUM * inverse_gap)
    return float(k1), float(k2)


def _admissible_roots(k1: float, k2: float, zn_o: float, nh4_o: float, ch: float) -> list[float]:
    coefficients = [
        k1 + k2**2,
        2 * (k1 * zn_o - k2**2 * nh4_o) - (k1 + k2**2) * ch,
        (2 * k1 * ch + k2**2 * nh4_o) * nh4_o,
        -(k2**2) * ch * nh4_o**2,
    ]
    roots = np.roots(coefficients)
    return [float(r.real) for r in roots if r.imag == 0 and r.real > 0]


def _fluxing_composition(eta2: float, volume: float, ch: float, zn_o: float, nh4_o: float, h2o_o: float) -> tuple:
    eta1 = (ch - eta2) / 2
    masses = np.array(
        [
            zn_o * 2 * MW_CL + nh4_o * MW_CL,
            (zn_o - eta1) * MW_ZN,
            eta1 * MW_ZN_OH_2,
            (nh4_o - eta2) * MW_NH4,
            (h2o_o - 2 * eta1 - eta2) * MW_H2O,
            eta2 * MW_NH4OH,
            ch * MW_H,
        ]
    )
    return masses, float(masses.sum() * volume)


def _fluxing_equilibrium(
    volume: float, mass: float, temperature_c: float, ph: float, salt_kg_per_m3: float = SALT_LOADING_KG_PER_M3
) -> np.ndarray:
    zn_o = ZNCL2_MASS_FRACTION * salt_kg_per_m3 / MW_ZNCL2
    nh4_o = NH4CL_MASS_FRACTION * salt_kg_per_m3 / MW_NH4CL
    h2o_o = (mass - salt_kg_per_m3 * volume) / (MW_H2O * volume)
    ch = 10 ** (-ph)
    k1, k2 = _equilibrium_constants(temperature_c)
    for eta2 in _admissible_roots(k1, k2, zn_o, nh4_o, ch):
        masses, mass_aux = _fluxing_composition(eta2, volume, ch, zn_o, nh4_o, h2o_o)
        if abs(mass_aux - mass) <= ROOT_MASS_TOLERANCE:
            return np.concatenate([masses, [0.0, 0.0]]) * (100 * volume / mass)
    message = f"No admissible fluxing equilibrium root matches the solution mass (pH={ph:.3f}, T={temperature_c:.1f} C)"
    logger.error(message)
    raise ValueError(message)
