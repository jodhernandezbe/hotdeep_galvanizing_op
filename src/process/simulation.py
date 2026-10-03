"""Yearly Monte Carlo simulation of the hot-dip galvanizing line.

Purpose: Python port of the MATLAB `HDG` function (thesis annex D.3), returning a structured year summary.
Author: Jose D. Hernandez-Betancur
Date: 2026-10-02
"""

import logging
from dataclasses import dataclass, field
from typing import Final

import numpy as np

from src.process.degreasing import DegreasingResult, degrease, naoh_solution_heat_capacity
from src.process.drying import FLUX_HEAT_CAPACITY, drying_heat_j
from src.process.fluxing import FluxingResult, flux
from src.process.galvanizing import (
    coating_mass_kg,
    coating_thickness_um,
    draw_bath_temperature,
    draw_skimming_losses,
    initial_bath,
    makeup_heat_j,
    standard_thickness_um,
)
from src.process.initial_conditions import (
    abnormal_pickling_initial_condition,
    degreasing_initial_condition,
    fluxing_initial_condition,
    normal_pickling_initial_condition,
    rinsing_initial_volume,
)
from src.process.operating_policy import OperatingPolicy
from src.process.pickling import PicklingResult, pickle_abnormal, pickle_normal
from src.process.plant import Bath, BathLedger, LineTotals, Plant
from src.process.steel_lots import SteelLot, draw_steel_lot

logger = logging.getLogger(__name__)

AMBIENT_MEAN_C: Final = 22.0
AMBIENT_STD_C: Final = 2.0
RINSE_REPLACEMENTS_PER_YEAR: Final = 54
WATER_DENSITY: Final = 1000.0
RINSE_COMPOSITION_WT: Final = np.array([0.0, 100.0, 0.0, 0.0])
NORMAL_PICKLING_IRON_LIMIT_G_PER_L: Final = 150.0
ABNORMAL_PICKLING_HCL_LIMIT_G_PER_L: Final = 10.0
FLUXING_IRON_LIMIT_G_PER_L: Final = 5.0
REPROCESSING_PROBABILITY: Final = 0.02
FLUX_SOLUTION_DENSITY: Final = 1030.0


@dataclass(frozen=True)
class YearResult:
    """Everything the sustainability assessment needs from one simulated year.

    Attributes:
        totals: Yearly accumulators (masses [kg], heats [J], quality sums).
        degreasing: Ledger of the degreasing bath.
        rinse_1: Ledger of the first rinsing tank.
        normal_pickling: Ledger of the normal pickling bath.
        abnormal_pickling: Ledger of the abnormal (dezincification) pickling bath.
        rinse_2: Ledger of the second rinsing tank.
        fluxing: Ledger of the fluxing bath.
        fluxing_bleed_kg: Component masses withdrawn from the fluxing bath as overflow bleed [kg], length 9
            (all zeros in thesis mode, which has no capacity constraint).
    """

    totals: LineTotals
    degreasing: BathLedger
    rinse_1: BathLedger
    normal_pickling: BathLedger
    abnormal_pickling: BathLedger
    rinse_2: BathLedger
    fluxing: BathLedger
    fluxing_bleed_kg: np.ndarray = field(default_factory=lambda: np.zeros(9))


@dataclass
class _DipLoad:
    """The pieces of a lot that go through one pickling-fluxing-galvanizing pass."""

    indices: np.ndarray
    steel_mass_kg: float
    surface_m2: float
    rust_kg: float
    coating_kg: float
    reprocessing: bool


def draw_ambient_temperature(rng: np.random.Generator) -> float:
    """Sample the ambient temperature.

    Args:
        rng: Random number generator.

    Returns:
        Ambient temperature [degC].
    """
    return float(rng.normal(AMBIENT_MEAN_C, AMBIENT_STD_C))


def simulate_year(
    items: int,
    rng: np.random.Generator,
    preserve_thesis_quirks: bool = True,
    policy: OperatingPolicy | None = None,
) -> YearResult:
    """Simulate the galvanizing of one year of production.

    Args:
        items: Number of steel pieces entering the line during the year.
        rng: Random number generator.
        preserve_thesis_quirks: Reproduce the thesis fluxing-state bookkeeping, where the listing stores the bath volume
            returned by the fluxing step in the pH variable and never updates the volume (this is what reproduces the
            thesis results). When False, the volume and pH returned by the fluxing step are stored as intended.
        policy: Operating-policy overrides for the controllable conditions; None preserves the thesis draws.

    Returns:
        Summary of the year.
    """
    plant = _start_plant(rng, policy)
    plant.preserve_thesis_quirks = preserve_thesis_quirks
    processed = 0
    while processed <= items:
        lot = draw_steel_lot(rng)
        processed += lot.size
        logger.debug("Processed %d of %d items", processed, items)
        _process_lot(plant, lot, processed, items, rng)
    return _summarize(plant)


def _start_plant(rng: np.random.Generator, policy: OperatingPolicy | None = None) -> Plant:
    renewal_rng = None if policy is None else rng.spawn(1)[0]
    ambient = draw_ambient_temperature(rng)
    plant = Plant(
        degreasing=Bath.from_initial_condition(
            degreasing_initial_condition(rng, _policy_value(policy, "degreasing_temperature_c")), ambient
        ),
        rinse_1=_new_rinse_tank(rng, ambient),
        normal_pickling=Bath.from_initial_condition(_new_normal_pickling(rng, ambient, policy), ambient),
        abnormal_pickling=Bath.from_initial_condition(abnormal_pickling_initial_condition(rng=rng, ambient_c=ambient), ambient),
        rinse_2=_new_rinse_tank(rng, ambient),
        fluxing=Bath.from_initial_condition(_new_fluxing(rng, policy), ambient),
        zinc_bath_temperature_c=0.0,
        zinc_bath_mass_kg=0.0,
        policy=policy,
        renewal_rng=renewal_rng,
    )
    _set_initial_heats(plant, ambient, rng)
    return plant


def _policy_value(policy: OperatingPolicy | None, name: str) -> float | None:
    return None if policy is None else float(getattr(policy, name))


def _renewal_rng(plant: Plant, rng: np.random.Generator) -> np.random.Generator:
    """Generator for bath renewals and other draws whose occurrence depends on the policy.

    With a policy, these draw from a dedicated stream so that their policy-dependent timing cannot
    desynchronize the exogenous uncertainty draws (steel lots, ambient, losses) between two policies
    evaluated under common random numbers. Without a policy the main stream is used (thesis behaviour).
    """
    return rng if plant.renewal_rng is None else plant.renewal_rng


def _new_normal_pickling(rng: np.random.Generator, ambient_c: float, policy: OperatingPolicy | None):
    return normal_pickling_initial_condition(rng=rng, ambient_c=ambient_c, hcl_pct=_policy_value(policy, "pickling_hcl_pct"))


def _new_fluxing(rng: np.random.Generator, policy: OperatingPolicy | None):
    return fluxing_initial_condition(
        rng,
        temperature_c=_policy_value(policy, "fluxing_temperature_c"),
        ph=_policy_value(policy, "fluxing_ph_target"),
        salt_kg_per_m3=_policy_value(policy, "fluxing_salt_g_per_l"),
    )


def _new_rinse_tank(rng: np.random.Generator, ambient: float) -> Bath:
    volume_m3 = rinsing_initial_volume(rng)
    return Bath(
        mass_kg=WATER_DENSITY * volume_m3,
        composition_wt=RINSE_COMPOSITION_WT.copy(),
        volume_m3=volume_m3,
        temperature_c=ambient,
        ledger=BathLedger(WATER_DENSITY * volume_m3, RINSE_COMPOSITION_WT),
    )


def _set_initial_heats(plant: Plant, ambient: float, rng: np.random.Generator) -> None:
    degreasing, fluxing = plant.degreasing, plant.fluxing
    heat_capacity = naoh_solution_heat_capacity(degreasing.composition_wt[0])
    plant.totals.degreasing_heat_j = degreasing.mass_kg * heat_capacity * (degreasing.temperature_c - ambient)
    plant.totals.fluxing_heat_j = fluxing.mass_kg * FLUX_HEAT_CAPACITY * (fluxing.temperature_c - ambient)
    setpoint = _policy_value(plant.policy, "galvanizing_temperature_c")
    zinc_bath, plant.totals.galvanizing_heat_j = initial_bath(ambient, rng, setpoint)
    plant.totals.molten_zinc_kg = zinc_bath.initial_mass_kg
    plant.zinc_bath_temperature_c = zinc_bath.temperature_c
    plant.zinc_bath_mass_kg = zinc_bath.initial_mass_kg


def _process_lot(plant: Plant, lot: SteelLot, processed: int, items: int, rng: np.random.Generator) -> None:
    ambient = draw_ambient_temperature(rng)
    _record_lot(plant.totals, lot)
    removed_kg = _degrease(plant, lot, ambient)
    _rinse(plant.rinse_1, removed_kg, plant.degreasing.composition_wt, processed, items, rng)
    coating_kg = np.zeros(lot.size)
    thickness_um = np.zeros(lot.size)
    indices = np.arange(lot.size)
    first_pass = True
    while indices.size:
        load = _build_load(lot, indices, coating_kg, first_pass)
        _dip(plant, lot, load, (coating_kg, thickness_um), (ambient, processed, items), rng)
        indices = _select_for_reprocessing(indices, rng)
        first_pass = False
    _record_quality(plant.totals, lot, thickness_um)


def _record_lot(totals: LineTotals, lot: SteelLot) -> None:
    totals.n_lots += 1
    totals.steel_kg += lot.total_mass_kg
    totals.rust_kg += lot.rust_kg
    totals.grease_and_oil_kg += lot.grease_and_oil_kg
    totals.grease_mw_sum += lot.grease_mw
    totals.steel_surface_kg += lot.rusted_surface_mass_kg


def _degrease(plant: Plant, lot: SteelLot, ambient: float) -> float:
    bath = plant.degreasing
    result = degrease(
        lot.grease_and_oil_kg,
        lot.grease_mw,
        bath.mass_kg,
        bath.composition_wt,
        bath.temperature_c,
        lot.greased_mass_kg,
        bath.last_heat_j,
        ambient,
    )
    _apply_degreasing_result(plant, result)
    return result.removed_solution_kg


def _apply_degreasing_result(plant: Plant, result: DegreasingResult) -> None:
    bath = plant.degreasing
    bath.mass_kg, bath.composition_wt = result.solution_mass_kg, result.composition_wt
    bath.temperature_c, bath.last_heat_j = result.temperature_c, result.heat_j
    plant.totals.saponified_kg += result.saponified_kg
    plant.totals.remaining_grease_kg += result.remaining_grease_kg
    plant.totals.degreasing_heat_j += result.heat_j


def _rinse(
    tank: Bath, removed_kg: float, incoming_wt: np.ndarray, processed: int, items: int, rng: np.random.Generator
) -> None:
    if processed >= (tank.ledger.n_final + 1) * round(items / RINSE_REPLACEMENTS_PER_YEAR):
        tank.retire()
        tank.volume_m3 = rinsing_initial_volume(rng)
        tank.mass_kg = WATER_DENSITY * tank.volume_m3
        tank.composition_wt = RINSE_COMPOSITION_WT.copy()
        tank.ledger.initial_mass_kg += tank.mass_kg
    tank.mix_in(removed_kg, incoming_wt)


def _build_load(lot: SteelLot, indices: np.ndarray, coating_kg: np.ndarray, first_pass: bool) -> _DipLoad:
    return _DipLoad(
        indices=indices,
        steel_mass_kg=float(lot.mass_kg[indices].sum()),
        surface_m2=float(lot.surface_area_m2[indices].sum()),
        rust_kg=lot.rust_kg if first_pass else 0.0,
        coating_kg=float(coating_kg[indices].sum()),
        reprocessing=not first_pass,
    )


def _dip(
    plant: Plant,
    lot: SteelLot,
    load: _DipLoad,
    coating: tuple[np.ndarray, np.ndarray],
    context: tuple[float, int, int],
    rng: np.random.Generator,
) -> None:
    ambient, processed, items = context
    removed_kg, incoming_wt, residual_rust_kg = _pickle(plant, load, ambient, rng)
    _rinse(plant.rinse_2, removed_kg, incoming_wt, processed, items, rng)
    carried_flux_kg = _flux(plant, load, residual_rust_kg, ambient, rng)
    _dry(plant, load, carried_flux_kg)
    _galvanize(plant, lot, load, coating, ambient, rng)


def _pickle(plant: Plant, load: _DipLoad, ambient: float, rng: np.random.Generator) -> tuple[float, np.ndarray, float]:
    if load.reprocessing:
        return _pickle_abnormal(plant, load, ambient, rng)
    return _pickle_normal(plant, load, ambient, rng)


def _pickle_normal(plant: Plant, load: _DipLoad, ambient: float, rng: np.random.Generator) -> tuple[float, np.ndarray, float]:
    bath = plant.normal_pickling
    iron_g_per_l = 0.01 * bath.composition_wt[2] * bath.mass_kg / bath.volume_m3
    plant.totals.peak_pickling_fe2_g_per_l = max(plant.totals.peak_pickling_fe2_g_per_l, float(iron_g_per_l))
    if iron_g_per_l >= NORMAL_PICKLING_IRON_LIMIT_G_PER_L:
        bath.renew(_new_normal_pickling(_renewal_rng(plant, rng), ambient, plant.policy), ambient)
    result = pickle_normal(
        bath.composition_wt,
        bath.mass_kg,
        bath.temperature_c,
        bath.volume_m3,
        load.rust_kg,
        load.surface_m2,
        load.steel_mass_kg,
        rng,
        dip_time_s=_policy_value(plant.policy, "pickling_dip_time_s"),
    )
    _update_pickling_bath(bath, result)
    return result.removed_solution_kg, np.append(bath.composition_wt, 0.0), result.surface_mass_kg


def _pickle_abnormal(plant: Plant, load: _DipLoad, ambient: float, rng: np.random.Generator) -> tuple[float, np.ndarray, float]:
    bath = plant.abnormal_pickling
    hcl_g_per_l = 0.01 * bath.composition_wt[0] * bath.mass_kg / bath.volume_m3
    if hcl_g_per_l < ABNORMAL_PICKLING_HCL_LIMIT_G_PER_L:
        bath.renew(abnormal_pickling_initial_condition(rng=_renewal_rng(plant, rng), ambient_c=ambient), ambient)
    result = pickle_abnormal(
        bath.composition_wt,
        bath.mass_kg,
        bath.temperature_c,
        bath.volume_m3,
        load.coating_kg,
        load.surface_m2,
        load.steel_mass_kg,
        _renewal_rng(plant, rng),
    )
    _update_pickling_bath(bath, result)
    return result.removed_solution_kg, bath.composition_wt.copy(), 0.0


def _update_pickling_bath(bath: Bath, result: PicklingResult) -> None:
    bath.mass_kg, bath.composition_wt, bath.volume_m3 = result.solution_mass_kg, result.composition_wt, result.volume_m3


def _flux(plant: Plant, load: _DipLoad, rust_kg: float, ambient: float, rng: np.random.Generator) -> float:
    result = _run_flux(plant, load, rust_kg, ambient, rng)
    _apply_flux_result(plant, plant.fluxing, result)
    if not plant.preserve_thesis_quirks:
        _bleed_fluxing_overflow(plant)
    _renew_fluxing_if_saturated(plant, ambient, rng)
    return result.removed_solution_kg


def _run_flux(plant: Plant, load: _DipLoad, rust_kg: float, ambient: float, rng: np.random.Generator) -> FluxingResult:
    bath = plant.fluxing
    return flux(
        rust_kg,
        bath.mass_kg,
        bath.composition_wt,
        bath.temperature_c,
        load.steel_mass_kg,
        bath.last_heat_j,
        ambient,
        bath.volume_m3,
        _fluxing_ph(bath),
        rng,
        preserve_thesis_quirks=plant.preserve_thesis_quirks,
    )


def _bleed_fluxing_overflow(plant: Plant) -> None:
    """Corrected mode only: withdraw the overflow above the tank capacity to the spent-fluxing stream.

    Industrial practice is a side-stream withdrawal of the flux bath rather than dumping it; the withdrawn
    stream is accounted as spent fluxing solution.
    """
    bath = plant.fluxing
    if bath.capacity_m3 is not None:
        plant.fluxing_bleed_kg += bath.bleed_to(bath.capacity_m3)


def _renew_fluxing_if_saturated(plant: Plant, ambient: float, rng: np.random.Generator) -> None:
    bath = plant.fluxing
    iron_g_per_l = 0.01 * bath.composition_wt[7] * bath.mass_kg / bath.volume_m3
    plant.totals.peak_fluxing_fe2_g_per_l = max(plant.totals.peak_fluxing_fe2_g_per_l, float(iron_g_per_l))
    if iron_g_per_l >= FLUXING_IRON_LIMIT_G_PER_L:
        bath.renew(_new_fluxing(_renewal_rng(plant, rng), plant.policy), ambient, keep_ph=plant.preserve_thesis_quirks)


def _fluxing_ph(bath: Bath) -> float:
    if bath.ph is None:
        message = "The fluxing bath has no pH"
        logger.error(message)
        raise ValueError(message)
    return bath.ph


def _dry(plant: Plant, load: _DipLoad, carried_flux_kg: float) -> None:
    bath = plant.fluxing
    plant.totals.drying_heat_j += drying_heat_j(load.steel_mass_kg, carried_flux_kg, bath.temperature_c, bath.composition_wt[3])


def _apply_flux_result(plant: Plant, bath: Bath, result: FluxingResult) -> None:
    bath.mass_kg, bath.composition_wt, bath.temperature_c = result.solution_mass_kg, result.composition_wt, result.temperature_c
    if not plant.preserve_thesis_quirks:
        bath.volume_m3, bath.ph = result.volume_m3, result.ph
    else:
        bath.ph = result.volume_m3
    bath.last_heat_j = result.heat_j
    plant.totals.fluxing_heat_j += result.heat_j
    plant.totals.hcl_added_kg += result.hcl_added_kg
    plant.totals.nh4oh_added_kg += result.nh4oh_added_kg


def _galvanize(
    plant: Plant,
    lot: SteelLot,
    load: _DipLoad,
    coating: tuple[np.ndarray, np.ndarray],
    ambient: float,
    rng: np.random.Generator,
) -> None:
    coating_kg, thickness_um = coating
    totals = plant.totals
    losses = draw_skimming_losses(load.steel_mass_kg, rng)
    totals.dross_kg += losses.dross_kg
    totals.ash_kg += losses.ash_kg
    deposited_kg = _deposit_coating(plant, lot, load, coating_kg, thickness_um, rng)
    zinc_lost_kg = deposited_kg + losses.zinc_lost_dross_kg + losses.zinc_lost_ash_kg
    next_temperature = draw_bath_temperature(rng, _policy_value(plant.policy, "galvanizing_temperature_c"))
    totals.galvanizing_heat_j += makeup_heat_j(
        plant.zinc_bath_mass_kg, zinc_lost_kg, load.steel_mass_kg, plant.zinc_bath_temperature_c, next_temperature, ambient
    )
    totals.molten_zinc_kg += zinc_lost_kg
    plant.zinc_bath_temperature_c = next_temperature


def _deposit_coating(
    plant: Plant,
    lot: SteelLot,
    load: _DipLoad,
    coating_kg: np.ndarray,
    thickness_um: np.ndarray,
    rng: np.random.Generator,
) -> float:
    indices = load.indices
    temperature = plant.zinc_bath_temperature_c
    random_scale = None if load.reprocessing else rng
    thickness_um[indices] = coating_thickness_um(temperature, lot.silicon_wt[indices], random_scale)
    coating_kg[indices] = coating_mass_kg(thickness_um[indices], lot.surface_area_m2[indices])
    plant.totals.zinc_coating_kg += float(coating_kg[indices].sum())
    if load.reprocessing:
        return float(coating_kg[indices[-1]])
    return float(coating_kg.sum())


def _select_for_reprocessing(indices: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    return indices[rng.uniform(size=indices.size) <= REPROCESSING_PROBABILITY]


def _record_quality(totals: LineTotals, lot: SteelLot, thickness_um: np.ndarray) -> None:
    standard_um = standard_thickness_um(lot.gauge_m)
    utility = np.minimum(1.0, thickness_um / standard_um)
    totals.quality_mass_weighted += float(np.dot(lot.mass_kg, utility))
    totals.standard_thickness_sum_um += float(standard_um.sum())
    totals.n_quality_pieces += lot.size
    totals.n_defective_pieces += int(np.count_nonzero(thickness_um < standard_um))
    totals.thickness_sum_um += float(thickness_um.sum())


def _summarize(plant: Plant) -> YearResult:
    plant.degreasing.retire()
    for bath in (plant.rinse_1, plant.normal_pickling, plant.abnormal_pickling, plant.rinse_2, plant.fluxing):
        if bath.ledger.n_final == 0:
            bath.retire()
    return YearResult(
        totals=plant.totals,
        degreasing=plant.degreasing.ledger,
        rinse_1=plant.rinse_1.ledger,
        normal_pickling=plant.normal_pickling.ledger,
        abnormal_pickling=plant.abnormal_pickling.ledger,
        rinse_2=plant.rinse_2.ledger,
        fluxing=plant.fluxing.ledger,
        fluxing_bleed_kg=plant.fluxing_bleed_kg,
    )
