"""Pickling kinetics in HCl: normal (rust removal) and abnormal (dezincification).

Purpose: ODE-based mass balance of the pickling baths (annex D.3.4).
Author: Jose D. Hernandez-Betancur
Date: 2026-10-02
"""

from dataclasses import dataclass

import numpy as np
from scipy.integrate import solve_ivp
from scipy.optimize import OptimizeResult as OdeResult

from src.common.constants import (
    FARADAY,
    GAS_CONSTANT,
    KELVIN_OFFSET,
    MW_FE,
    MW_FEO,
    MW_H2O,
    MW_HCL,
    MW_ZN,
)
from src.process.densities import hcl_solution_density

REMOVED_SOLUTION_PER_STEEL = 1e-6
RESIDUAL_SURFACE_FRACTION = 0.1175
ACTIVE_SURFACE_FRACTION = 0.0001
MIN_DIPPING_MINUTES = 10.0
DIPPING_RANGE_MINUTES = 10.0
FEO_PREEXPONENTIAL = 1011.2036
FEO_ACTIVATION_ENERGY = 48846.2
FE_PREEXPONENTIAL = 0.2864
FE_ACTIVATION_ENERGY = 33057.2
ZN_CURRENT_PREEXPONENTIAL = 5.9434e-9
ZN_CURRENT_EXPONENT = 13114.0
ZINC_STRIPPED_THRESHOLD_KG = 0.05
ODE_RTOL = 1e-3
ODE_ATOL = 1e-6


@dataclass(frozen=True)
class PicklingResult:
    """Outcome of one pickling step.

    Attributes:
        solution_mass_kg: Bath mass after the step [kg].
        composition_wt: Bath composition [% wt].
        surface_mass_kg: Remaining FeO (normal) or Zn (abnormal) on the steel [kg].
        removed_solution_kg: Solution dragged out with the steel [kg].
        volume_m3: Bath volume after the step [m3].
    """

    solution_mass_kg: float
    composition_wt: np.ndarray
    surface_mass_kg: float
    removed_solution_kg: float
    volume_m3: float


def pickle_normal(
    composition_wt: np.ndarray,
    solution_mass_kg: float,
    temperature_c: float,
    volume_m3: float,
    rust_kg: float,
    steel_area_m2: float,
    steel_mass_kg: float,
    rng: np.random.Generator,
    dip_time_s: float | None = None,
) -> PicklingResult:
    """Pickle one lot in the normal bath (composition [HCl, H2O, Fe2+]).

    Args:
        composition_wt: Bath composition [% wt].
        solution_mass_kg: Bath mass before the step [kg].
        temperature_c: Bath temperature [degC].
        volume_m3: Bath volume [m3].
        rust_kg: FeO mass on the lot [kg].
        steel_area_m2: Lot surface area [m2].
        steel_mass_kg: Lot mass [kg].
        rng: Random generator (dipping time).
        dip_time_s: Dipping time override [s]; drawn from the thesis range when None.

    Returns:
        Updated bath state.
    """
    removed = _removed_solution(steel_mass_kg, temperature_c, composition_wt[0])
    masses = 0.01 * solution_mass_kg * composition_wt
    solution = _integrate(
        _rxnn, [*masses, rust_kg], rng, (volume_m3, temperature_c, rust_kg), (_rust_removed_event,), dip_time_s
    )
    states = _states_with_event(solution, 0, rust_kg * RESIDUAL_SURFACE_FRACTION)
    retained, surface = _normal_outcome(states, masses, composition_wt, rust_kg, removed, solution_mass_kg)
    return _finalize(retained, surface, removed, temperature_c)


def pickle_abnormal(
    composition_wt: np.ndarray,
    solution_mass_kg: float,
    temperature_c: float,
    volume_m3: float,
    zinc_coating_kg: float,
    steel_area_m2: float,
    steel_mass_kg: float,
    rng: np.random.Generator,
) -> PicklingResult:
    """Pickle reprocessed items in the abnormal bath (composition [HCl, H2O, Fe2+, Zn2+]).

    Args:
        composition_wt: Bath composition [% wt].
        solution_mass_kg: Bath mass before the step [kg].
        temperature_c: Bath temperature [degC].
        volume_m3: Bath volume [m3].
        zinc_coating_kg: Zn mass to strip from the lot [kg].
        steel_area_m2: Lot surface area [m2].
        steel_mass_kg: Lot mass [kg].
        rng: Random generator (dipping time).

    Returns:
        Updated bath state.
    """
    removed = _removed_solution(steel_mass_kg, temperature_c, composition_wt[0])
    masses = 0.01 * solution_mass_kg * composition_wt
    initial = [masses[0], masses[2], masses[3], zinc_coating_kg]
    states = _abnormal_states(initial, rng, (volume_m3, temperature_c, zinc_coating_kg, steel_area_m2))
    retained = _abnormal_outcome(states, masses, composition_wt, removed, solution_mass_kg)
    return _finalize(retained, 0.0, removed, temperature_c)


def _abnormal_states(initial: list, rng: np.random.Generator, args: tuple) -> np.ndarray:
    if np.round(initial[3], 1) == 0:
        return np.array([initial], dtype=float)
    solution = _integrate(_rxna, initial, rng, args, (_zinc_stripped_event, _zinc_inactive_event))
    return _states_with_event(solution, 0, 0.0)


def _removed_solution(steel_mass_kg: float, temperature_c: float, hcl_wt: float) -> float:
    return float(REMOVED_SOLUTION_PER_STEEL * steel_mass_kg * hcl_solution_density(temperature_c, hcl_wt))


def _rust_removed_event(_t: float, state: np.ndarray, _volume: float, _temperature_c: float, surface_o: float) -> float:
    return state[3] - surface_o * RESIDUAL_SURFACE_FRACTION


def _zinc_stripped_event(
    _t: float, state: np.ndarray, _volume: float, _temperature_c: float, _surface_o: float, _area: float
) -> float:
    return state[3] - ZINC_STRIPPED_THRESHOLD_KG


def _zinc_inactive_event(
    _t: float, state: np.ndarray, _volume: float, _temperature_c: float, surface_o: float, _area: float
) -> float:
    return state[3] - surface_o * ACTIVE_SURFACE_FRACTION


for _event in (_rust_removed_event, _zinc_stripped_event, _zinc_inactive_event):
    setattr(_event, "terminal", True)
    setattr(_event, "direction", -1)


def _integrate(
    rhs, initial: list, rng: np.random.Generator, args: tuple, events: tuple, dip_time_s: float | None = None
) -> OdeResult:
    """Integrate over the dipping time, stopping at the first terminal event.

    The thesis only uses the trajectory up to the point where the surface target is met (or the rate switch turns the
    surface term off); integrating beyond it makes the solver chatter at that switch for no benefit.
    """
    dipping_seconds = (DIPPING_RANGE_MINUTES * rng.random() + MIN_DIPPING_MINUTES) * 60 if dip_time_s is None else dip_time_s
    return solve_ivp(
        rhs, (0.0, dipping_seconds), initial, method="LSODA", rtol=ODE_RTOL, atol=ODE_ATOL, args=args, events=list(events)
    )


def _states_with_event(solution: OdeResult, event_index: int, surface_value: float) -> np.ndarray:
    states = solution.y.T
    if solution.t_events[event_index].size:
        reached = np.array(solution.y_events[event_index][0], dtype=float)
        reached[3] = surface_value
        states = np.vstack([states, reached])
    return states


def _arrhenius(preexponential: float, energy: float, temperature_c: float) -> float:
    return preexponential * np.exp(-energy / (GAS_CONSTANT * (temperature_c + KELVIN_OFFSET)))


def _rxnn(_t: float, state: np.ndarray, volume: float, temperature_c: float, surface_o: float) -> np.ndarray:
    hcl_mg_per_l = state[0] * 1000 / volume
    active = 0.0 if state[3] <= surface_o * ACTIVE_SURFACE_FRACTION else 1.0
    r_feo = _arrhenius(FEO_PREEXPONENTIAL, FEO_ACTIVATION_ENERGY, temperature_c) * hcl_mg_per_l**2 * 1e-3 * active
    r_fe = _arrhenius(FE_PREEXPONENTIAL, FE_ACTIVATION_ENERGY, temperature_c) * hcl_mg_per_l**2 * 1e-3
    return np.array(
        [
            -2 * MW_HCL * (r_feo / MW_FEO + r_fe / MW_FE) * volume,
            MW_H2O * r_feo * volume / MW_FEO,
            (r_fe + MW_FE * r_feo / MW_FEO) * volume,
            -r_feo * volume,
        ]
    )


def _rxna(t: float, state: np.ndarray, volume: float, temperature_c: float, surface_o: float, area: float) -> np.ndarray:
    hcl_mol_per_m3 = 1000 * state[0] / (MW_HCL * volume)
    active = 0.0 if state[3] <= surface_o * ACTIVE_SURFACE_FRACTION else 1.0
    kelvin = temperature_c + KELVIN_OFFSET
    current = ZN_CURRENT_PREEXPONENTIAL * np.exp(ZN_CURRENT_EXPONENT / kelvin) * hcl_mol_per_m3 * active
    r_fe = _arrhenius(FE_PREEXPONENTIAL, FE_ACTIVATION_ENERGY, temperature_c) * (hcl_mol_per_m3 * MW_HCL) ** 2 * 1e-3
    charge = current * area * t * 1e-3 / FARADAY
    zn_rate = MW_ZN * charge / 2
    return np.array([-MW_HCL * (charge + 2 * r_fe * volume / MW_FE), r_fe * volume, zn_rate, -zn_rate])


def _first_index(mask: np.ndarray) -> int | None:
    hits = np.flatnonzero(mask)
    return int(hits[0]) if hits.size else None


def _interp_extrap(x: np.ndarray, y: np.ndarray, target: float) -> float:
    order = np.argsort(x)
    xs, ys = x[order], y[order]
    if target < xs[0]:
        return float(ys[0] + (target - xs[0]) * (ys[1] - ys[0]) / (xs[1] - xs[0]))
    if target > xs[-1]:
        return float(ys[-1] + (target - xs[-1]) * (ys[-1] - ys[-2]) / (xs[-1] - xs[-2]))
    return float(np.interp(target, xs, ys))


def _normal_outcome(
    states: np.ndarray,
    masses: np.ndarray,
    composition_wt: np.ndarray,
    rust_kg: float,
    removed: float,
    solution_mass_kg: float,
) -> tuple[np.ndarray, float]:
    drag = 0.01 * composition_wt * removed
    position = _first_index(states[:, 3] <= rust_kg * RESIDUAL_SURFACE_FRACTION)
    if position is None:
        return 0.01 * composition_wt * (solution_mass_kg - removed), 0.0
    if position == 0:
        return states[0, :3] - drag, 0.0
    surface = rust_kg * RESIDUAL_SURFACE_FRACTION
    reached = states[: position + 1]
    return np.array([_interp_extrap(reached[:, 3], reached[:, i], surface) for i in range(3)]) - drag, surface


def _abnormal_outcome(
    states: np.ndarray,
    masses: np.ndarray,
    composition_wt: np.ndarray,
    removed: float,
    solution_mass_kg: float,
) -> np.ndarray:
    drag = 0.01 * composition_wt * removed
    position = _first_index(np.round(states[:, 3], 1) == 0)
    if position is None:
        return 0.01 * composition_wt * (solution_mass_kg - removed)
    final = states[position]
    return np.array([final[0], masses[1], final[1], final[2]]) - drag


def _finalize(retained: np.ndarray, surface: float, removed: float, temperature_c: float) -> PicklingResult:
    mass = float(retained.sum())
    composition = retained * (100 / mass)
    volume = mass / hcl_solution_density(temperature_c, composition[0])
    return PicklingResult(mass, composition, surface, removed, volume)
