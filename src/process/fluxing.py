"""Fluxing bath (ZnCl2/NH4Cl) ionic equilibrium, pH correction and energy balance.

Purpose: mass and energy balance of the fluxing tank (annex D.3.5, MATLAB `fluxing2`).
Author: Jose D. Hernandez-Betancur
Date: 2026-10-02
"""

from dataclasses import dataclass

import numpy as np

from src.common.constants import (
    GAS_CONSTANT_EQUILIBRIUM,
    KELVIN_OFFSET,
    MW_CL,
    MW_FE,
    MW_FE_OH_2,
    MW_FEO,
    MW_H,
    MW_H2O,
    MW_HCL,
    MW_NH4,
    MW_NH4OH,
    MW_ZN,
    MW_ZN_OH_2,
)
from src.process.drying import FLUX_HEAT_CAPACITY

PH_MEAN = 4.5
PH_STD = 0.3
PH_NO_NH4OH_THRESHOLD = 4.0
PH_HCL_CORRECTION_THRESHOLD = 5.0
HCL_SOLUTION_WT = 0.37
NH4OH_SOLUTION_WT = 0.3
HCL_WATER_PER_HCL = 0.63
NH4OH_WATER_PER_NH4OH = 0.7
REMOVED_SOLUTION_PER_STEEL = 1e-6
SOLUTION_DENSITY = 1030.0
STEEL_HEAT_CAPACITY = 450.0
HEAT_LOSS_REFERENCE_DELTA_T = 35.1
HEAT_LOSS_FRACTION = 0.1
REFERENCE_TEMPERATURE_C = 25.0
REFERENCE_TEMPERATURE_K = 298.15
K1_PREEXPONENTIAL, K1_ENERGY = 4.9e-12, 78680.0
K2_PREEXPONENTIAL, K2_ENERGY = 5.6e-10, 52140.0
K3_PREEXPONENTIAL, K3_ENERGY = 2.1e-14, 92074.4


@dataclass(frozen=True)
class FluxingResult:
    """Outcome of one fluxing step.

    Attributes:
        heat_j: Heat supplied to the bath [J].
        solution_mass_kg: Bath mass after the step [kg].
        composition_wt: [Cl-, Zn2+, Zn(OH)2, NH4+, H2O, NH4OH, H+, Fe, Fe(OH)2] [% wt].
        temperature_c: Bath temperature after the step [degC].
        removed_solution_kg: Solution dragged out with the steel [kg].
        hcl_added_kg: HCl added to lower the pH [kg].
        nh4oh_added_kg: NH4OH added to raise the pH [kg].
        volume_m3: Bath volume after the step [m3].
        ph: Bath pH after the step.
    """

    heat_j: float
    solution_mass_kg: float
    composition_wt: np.ndarray
    temperature_c: float
    removed_solution_kg: float
    hcl_added_kg: float
    nh4oh_added_kg: float
    volume_m3: float
    ph: float


@dataclass(frozen=True)
class _Bath:
    k1: float
    k2: float
    k3: float
    ch: float
    ch_o: float
    volume_o: float
    water_wt_mass: float
    water_conc_m: float
    water_conc: float
    rust_kg: float
    mass_o: float
    composition_wt: np.ndarray

    @property
    def water_balance_base(self) -> float:
        return 0.01 * self.composition_wt[4] * self.mass_o

    @property
    def rust_water(self) -> float:
        return self.rust_kg * MW_H2O / MW_FEO

    @property
    def h_released(self) -> float:
        return self.rust_kg * 2 / MW_FEO


@dataclass(frozen=True)
class _Species:
    eta1: float
    eta2: float
    eta3: float
    mol_zn: float
    mol_zn_oh2: float
    mol_fe: float
    mol_fe_oh2: float
    mol_nh4: float
    mol_nh4oh: float
    mol_hcl: float
    hcl_added: float
    nh4oh_added: float
    volume: float


def flux(
    rust_kg: float,
    solution_mass_kg: float,
    composition_wt: np.ndarray,
    temperature_c: float,
    steel_mass_kg: float,
    previous_heat_j: float,
    ambient_c: float,
    volume_m3: float,
    ph: float,
    rng: np.random.Generator,
    preserve_thesis_quirks: bool = True,
) -> FluxingResult:
    """Flux one lot of steel, correcting the bath pH.

    Args:
        rust_kg: FeO mass carried into the bath [kg].
        solution_mass_kg: Bath mass before the step [kg].
        composition_wt: Bath composition [% wt], length 9.
        temperature_c: Bath temperature [degC].
        steel_mass_kg: Lot mass [kg].
        previous_heat_j: Heat accumulated in the bath [J].
        ambient_c: Ambient temperature [degC].
        volume_m3: Bath volume before the step [m3].
        ph: Bath pH before the step.
        rng: Random generator (new pH draw).
        preserve_thesis_quirks: Keep the thesis listing's ammonium bookkeeping, which resets NH4OH to its equilibrium
            value without accounting for the created mass, and its volume balance missing the water molar mass on the
            extent terms (both in the pH-increase branch). When False, both balances conserve mass.

    Returns:
        Updated bath state and additions.
    """
    new_ph = rng.normal(PH_MEAN, PH_STD)
    bath = _build_bath(rust_kg, solution_mass_kg, composition_wt, temperature_c, volume_m3, ph, new_ph)
    species = _solve_species(bath, new_ph, ph, preserve_thesis_quirks)
    masses = _component_masses(bath, species)
    mass_before_drag = float(masses.sum())
    removed = REMOVED_SOLUTION_PER_STEEL * steel_mass_kg * SOLUTION_DENSITY
    mass = mass_before_drag - removed
    temperature, heat = _energy_balance(mass, temperature_c, steel_mass_kg, previous_heat_j, ambient_c)
    composition = masses * (100 / mass_before_drag)
    return FluxingResult(
        heat, mass, composition, temperature, removed, species.hcl_added, species.nh4oh_added, species.volume, new_ph
    )


def _arrhenius(preexponential: float, energy: float, temperature_c: float) -> float:
    gap = 1 / REFERENCE_TEMPERATURE_K - 1 / (temperature_c + KELVIN_OFFSET)
    return float(preexponential * np.exp(energy / GAS_CONSTANT_EQUILIBRIUM * gap))


def _build_bath(
    rust_kg: float,
    mass_o: float,
    composition_wt: np.ndarray,
    temperature_c: float,
    volume_o: float,
    ph_o: float,
    ph: float,
) -> _Bath:
    water_conc_m = 0.01 * composition_wt[4] * mass_o / volume_o
    return _Bath(
        k1=_arrhenius(K1_PREEXPONENTIAL, K1_ENERGY, temperature_c),
        k2=_arrhenius(K2_PREEXPONENTIAL, K2_ENERGY, temperature_c),
        k3=_arrhenius(K3_PREEXPONENTIAL, K3_ENERGY, temperature_c),
        ch=10 ** (-ph),
        ch_o=10 ** (-ph_o),
        volume_o=volume_o,
        water_wt_mass=0.01 * composition_wt[4] * mass_o,
        water_conc_m=water_conc_m,
        water_conc=water_conc_m / MW_H2O,
        rust_kg=rust_kg,
        mass_o=mass_o,
        composition_wt=composition_wt,
    )


def _hydroxide_extent(k: float, mol_ion_o: float, mol_hydroxide_o: float, bath: _Bath) -> float:
    return (k * mol_ion_o * bath.water_conc**2 - bath.ch**2 * mol_hydroxide_o) / (k * bath.water_conc**2 + bath.ch**2)


@dataclass(frozen=True)
class _Hydroxides:
    eta1: float
    eta3: float
    mol_zn: float
    mol_zn_oh2: float
    mol_fe: float
    mol_fe_oh2: float


def _hydroxide_equilibria(bath: _Bath) -> _Hydroxides:
    wt, mass = bath.composition_wt, bath.mass_o
    mol_zn_o = 0.01 * wt[1] * mass / MW_ZN
    mol_zn_oh2_o = 0.01 * wt[2] * mass / MW_ZN_OH_2
    mol_fe_o = 0.01 * wt[7] * mass / MW_FE + bath.rust_kg / MW_FEO
    mol_fe_oh2_o = 0.01 * wt[8] * mass / MW_FE_OH_2
    eta1 = _hydroxide_extent(bath.k1, mol_zn_o, mol_zn_oh2_o, bath)
    eta3 = _hydroxide_extent(bath.k3, mol_fe_o, mol_fe_oh2_o, bath)
    return _Hydroxides(eta1, eta3, mol_zn_o - eta1, mol_zn_oh2_o + eta1, mol_fe_o - eta3, mol_fe_oh2_o + eta3)


def _species(
    hydroxides: _Hydroxides,
    eta2: float,
    mol_nh4: float,
    mol_nh4oh: float,
    volume: float,
    mol_hcl: float = 0.0,
    hcl_added: float = 0.0,
    nh4oh_added: float = 0.0,
) -> _Species:
    return _Species(
        eta1=hydroxides.eta1,
        eta2=eta2,
        eta3=hydroxides.eta3,
        mol_zn=hydroxides.mol_zn,
        mol_zn_oh2=hydroxides.mol_zn_oh2,
        mol_fe=hydroxides.mol_fe,
        mol_fe_oh2=hydroxides.mol_fe_oh2,
        mol_nh4=mol_nh4,
        mol_nh4oh=mol_nh4oh,
        mol_hcl=mol_hcl,
        hcl_added=hcl_added,
        nh4oh_added=nh4oh_added,
        volume=volume,
    )


def _solve_species(bath: _Bath, ph: float, ph_o: float, preserve_thesis_quirks: bool) -> _Species:
    hydroxides = _hydroxide_equilibria(bath)
    mol_nh4_o = 0.01 * bath.composition_wt[3] * bath.mass_o / MW_NH4
    mol_nh4oh_o = 0.01 * bath.composition_wt[5] * bath.mass_o / MW_NH4OH
    if ph <= ph_o:
        return _acidified(bath, ph, mol_nh4_o, mol_nh4oh_o, hydroxides)
    return _basified(bath, ph, mol_nh4_o, mol_nh4oh_o, hydroxides, preserve_thesis_quirks)


def _conserving_ammonium_extent(bath: _Bath, mol_nh4_o: float, mol_nh4oh_o: float) -> float:
    return (bath.k2 * mol_nh4_o * bath.water_conc - bath.ch * mol_nh4oh_o) / (bath.ch + bath.k2 * bath.water_conc)


def _acidified(bath: _Bath, ph: float, mol_nh4_o: float, mol_nh4oh_o: float, hydroxides: _Hydroxides) -> _Species:
    eta2 = _conserving_ammonium_extent(bath, mol_nh4_o, mol_nh4oh_o)
    extent = 2 * hydroxides.eta1 + eta2 + 2 * hydroxides.eta3
    volume = (bath.water_balance_base - extent * MW_H2O + bath.rust_water) / bath.water_conc_m
    mol_hcl, hcl_added, volume = _hcl_correction(bath, ph, extent, volume)
    return _species(hydroxides, eta2, mol_nh4_o - eta2, mol_nh4oh_o + eta2, volume, mol_hcl, hcl_added)


def _hcl_correction(bath: _Bath, ph: float, extent: float, volume: float) -> tuple[float, float, float]:
    if ph <= PH_HCL_CORRECTION_THRESHOLD:
        return 0.0, 0.0, volume
    numerator = bath.ch * volume + bath.h_released - bath.ch_o * bath.volume_o - extent
    mol_hcl = numerator / (1 - HCL_WATER_PER_HCL * MW_HCL * bath.ch / (HCL_SOLUTION_WT * bath.water_conc_m))
    if mol_hcl < 0:
        return 0.0, 0.0, volume
    hcl_added = mol_hcl * MW_HCL
    return mol_hcl, hcl_added, volume + HCL_WATER_PER_HCL * hcl_added / (HCL_SOLUTION_WT * bath.water_conc_m)


def _basified(
    bath: _Bath,
    ph: float,
    mol_nh4_o: float,
    mol_nh4oh_o: float,
    hydroxides: _Hydroxides,
    preserve_thesis_quirks: bool,
) -> _Species:
    if ph < PH_NO_NH4OH_THRESHOLD:
        return _basified_with_nh4oh(bath, mol_nh4_o, mol_nh4oh_o, hydroxides, preserve_thesis_quirks)
    if preserve_thesis_quirks:
        return _basified_equilibrium_reset(bath, mol_nh4_o, mol_nh4oh_o, hydroxides)
    return _basified_conserving(bath, mol_nh4_o, mol_nh4oh_o, hydroxides)


def _basified_with_nh4oh(
    bath: _Bath,
    mol_nh4_o: float,
    mol_nh4oh_o: float,
    hydroxides: _Hydroxides,
    preserve_thesis_quirks: bool,
) -> _Species:
    eta1, eta3 = hydroxides.eta1, hydroxides.eta3
    dilution = bath.water_balance_base - (2 * eta1 + 2 * eta3) * MW_H2O + bath.rust_water
    addition_guess = bath.k2 * bath.water_conc * mol_nh4_o / bath.ch - mol_nh4oh_o
    dilution += addition_guess * NH4OH_WATER_PER_NH4OH * MW_NH4OH / NH4OH_SOLUTION_WT
    eta2 = _ammonium_extent(bath, dilution / bath.water_conc_m, eta1, eta3)
    mol_nh4 = mol_nh4_o - eta2
    mol_nh4oh = bath.k2 * mol_nh4 * bath.water_conc / bath.ch
    mol_added = mol_nh4oh - mol_nh4oh_o - eta2
    volume = _basified_volume(bath, eta1, eta2, eta3, mol_added, preserve_thesis_quirks)
    return _species(hydroxides, eta2, mol_nh4, mol_nh4oh, volume, nh4oh_added=mol_added * MW_NH4OH)


def _basified_equilibrium_reset(bath: _Bath, mol_nh4_o: float, mol_nh4oh_o: float, hydroxides: _Hydroxides) -> _Species:
    """Thesis listing behaviour: NH4OH jumps to its equilibrium value with no mass source accounted."""
    eta1, eta3 = hydroxides.eta1, hydroxides.eta3
    dilution = bath.water_balance_base - (2 * eta1 + 2 * eta3) * MW_H2O + bath.rust_water
    eta2 = _ammonium_extent(bath, dilution / bath.water_conc_m, eta1, eta3)
    mol_nh4 = mol_nh4_o - eta2
    mol_nh4oh = bath.k2 * mol_nh4 * bath.water_conc / bath.ch
    volume = _basified_volume(bath, eta1, eta2, eta3, 0.0, preserve_thesis_quirks=True)
    return _species(hydroxides, eta2, mol_nh4, mol_nh4oh, volume)


def _basified_conserving(bath: _Bath, mol_nh4_o: float, mol_nh4oh_o: float, hydroxides: _Hydroxides) -> _Species:
    eta2 = _conserving_ammonium_extent(bath, mol_nh4_o, mol_nh4oh_o)
    extent = 2 * hydroxides.eta1 + eta2 + 2 * hydroxides.eta3
    volume = (bath.water_balance_base - extent * MW_H2O + bath.rust_water) / bath.water_conc_m
    return _species(hydroxides, eta2, mol_nh4_o - eta2, mol_nh4oh_o + eta2, volume)


def _ammonium_extent(bath: _Bath, volume_guess: float, eta1: float, eta3: float) -> float:
    numerator = bath.ch * volume_guess + bath.h_released - bath.ch_o * bath.volume_o - 2 * eta1 - 2 * eta3
    ammonia_term = NH4OH_WATER_PER_NH4OH * MW_NH4OH * (bath.k2 * bath.water_conc / bath.ch + 1) * bath.ch
    denominator = 1 + ammonia_term / (bath.water_conc_m * NH4OH_SOLUTION_WT) + MW_H2O * bath.ch / bath.water_conc_m
    return numerator / denominator


def _basified_volume(
    bath: _Bath, eta1: float, eta2: float, eta3: float, mol_added: float, preserve_thesis_quirks: bool
) -> float:
    extent = 2 * eta1 + eta2 + 2 * eta3
    if preserve_thesis_quirks:
        # The thesis listing omits the water molar mass on the extent terms of this balance; kept for its numbers.
        extent_water = extent
    else:
        extent_water = extent * MW_H2O
    added_water = NH4OH_WATER_PER_NH4OH * mol_added * MW_NH4OH / NH4OH_SOLUTION_WT
    return (added_water + bath.water_balance_base - extent_water + bath.rust_water) / bath.water_conc_m


def _component_masses(bath: _Bath, species: _Species) -> np.ndarray:
    wt, volume = bath.composition_wt, species.volume
    return np.array(
        [
            0.01 * wt[0] * bath.mass_o + species.mol_hcl * MW_CL,
            species.mol_zn * MW_ZN,
            species.mol_zn_oh2 * MW_ZN_OH_2,
            species.mol_nh4 * MW_NH4,
            bath.water_conc_m * volume,
            species.mol_nh4oh * MW_NH4OH,
            bath.ch * MW_H * volume,
            species.mol_fe * MW_FE,
            species.mol_fe_oh2 * MW_FE_OH_2,
        ]
    )


def _energy_balance(
    mass: float, temperature_c: float, steel_kg: float, previous_heat_j: float, ambient_c: float
) -> tuple[float, float]:
    lost = abs((temperature_c - ambient_c) / HEAT_LOSS_REFERENCE_DELTA_T)
    bath_heat = mass * FLUX_HEAT_CAPACITY * (temperature_c - REFERENCE_TEMPERATURE_C)
    numerator = (
        (1 - HEAT_LOSS_FRACTION * lost) * bath_heat
        + REFERENCE_TEMPERATURE_C * mass * FLUX_HEAT_CAPACITY
        + ambient_c * steel_kg * STEEL_HEAT_CAPACITY
        + previous_heat_j
    )
    new_temperature = numerator / (mass * FLUX_HEAT_CAPACITY + steel_kg * STEEL_HEAT_CAPACITY)
    heat = HEAT_LOSS_FRACTION * lost * bath_heat + steel_kg * STEEL_HEAT_CAPACITY * (new_temperature - ambient_c)
    return new_temperature, heat
