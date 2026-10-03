"""Physical values of the GREENSCOPE hazard indicators (acute toxicity, air hazard, water hazard).

Purpose: data-driven port of the thesis' SH() function (annex D.4); one property record per compound.
Author: Jose D. Hernandez-Betancur
Date: 2026-10-02
"""

import math
from dataclasses import dataclass
from typing import Mapping, Sequence

import numpy as np

from src.sustainability.streams import N_COMPOUNDS, Compound

N_HAZARD_CATEGORIES = 3
ACUTE_TOXICITY, AIR_HAZARD, WATER_HAZARD = range(N_HAZARD_CATEGORIES)

_ACUTE_EC_CLASS_INDEX = {"T_plus": 0.875, "T": 0.625, "Xn": 0.375}
_ACUTE_GK_INDEX = {1: 1.0, 2: 0.875, 3: 0.625, 4: 0.375, 5: 0.125}
_ACUTE_R_CODE_INDEX = [({26, 27, 28, 29, 32}, 0.875), ({23, 24, 25, 31}, 0.625), ({20, 21, 22}, 0.375)]

_AIR_EC_CLASS_INDEX = {"T_plus": 0.7, "T": 0.5, "Xn": 0.3}
_AIR_GK_INDEX = {1: 0.8, 2: 0.7, 3: 0.5, 4: 0.3, 5: 0.1}
_AIR_R_CODE_INDEX = [
    ({45, 46, 47, 49, 60, 61}, 1.0),
    ({40, 62, 63, 64}, 0.8),
    ({29, 32, 64}, 0.7),
    ({42, 43}, 0.6),
    ({31, 33}, 0.5),
]

_WATER_R_CODE_INDEX = [({50}, 0.875), ({51}, 0.625), ({52}, 0.375)]
_WATER_GWK_INDEX = {3: 0.875, 2: 0.5, 1: 0.125, "nwg": 0.0}


@dataclass(frozen=True)
class SubstanceProperties:
    """Hazard-related properties of one compound; ``None`` means not available (MATLAB 'NA').

    Attributes:
        ec_class: European Community hazard class ('T_plus', 'T', 'Xn', 'C', ...).
        r_code: R-phrase code.
        gk: German air hazard class (Gefahrstoffklasse).
        gwk: German water hazard class (Wassergefaehrdungsklasse).
        idlh: Immediately dangerous to life or health [mg/m3].
        erpg_3: Emergency response planning guideline 3 [mg/m3].
        lc_50: Aquatic lethal concentration [mg/L].
        mak_ch: Swiss maximum workplace concentration [mg/m3].
    """

    ec_class: str | None = None
    r_code: int | None = None
    gk: int | None = None
    gwk: int | str | None = None
    idlh: float | None = None
    erpg_3: float | None = None
    lc_50: float | None = None
    mak_ch: float | None = None


SUBSTANCE_PROPERTIES: dict[Compound, SubstanceProperties] = {
    Compound.STEEL: SubstanceProperties(idlh=1e5, lc_50=1e3, mak_ch=1e4),
    Compound.TRIGLYCERIDE: SubstanceProperties(lc_50=1e4, mak_ch=1e4),
    Compound.WUSTITE: SubstanceProperties(idlh=2500, lc_50=50000, mak_ch=10),
    Compound.SODIUM_HYDROXIDE: SubstanceProperties(
        ec_class="C",
        r_code=35,
        gk=2,
        idlh=10,
        erpg_3=50,
        lc_50=160,
        mak_ch=2,
    ),
    Compound.WATER: SubstanceProperties(lc_50=1e4),
    Compound.GLYCEROL: SubstanceProperties(lc_50=5000, mak_ch=1e4),
    Compound.SODIUM_CARBOXYLATES: SubstanceProperties(lc_50=1e4, mak_ch=1e4),
    Compound.HYDROCHLORIC_ACID: SubstanceProperties(
        ec_class="C",
        r_code=34,
        gk=2,
        gwk=1,
        idlh=74.56,
        erpg_3=223.68,
        lc_50=20.5,
        mak_ch=3,
    ),
    Compound.IRON_DICHLORIDE: SubstanceProperties(ec_class="C", r_code=34, lc_50=3.124),
    Compound.ZINC: SubstanceProperties(ec_class="Xn", r_code=20, lc_50=5.100, mak_ch=5),
    Compound.ZINC_DICHLORIDE: SubstanceProperties(ec_class="Xn", r_code=22),
    Compound.AMMONIUM_CHLORIDE: SubstanceProperties(ec_class="Xn", r_code=22),
    Compound.AMMONIUM_HYDROXIDE: SubstanceProperties(
        ec_class="Xn",
        r_code=22,
        idlh=208.96,
        erpg_3=1044.79,
        lc_50=8.2,
        mak_ch=14,
    ),
    Compound.ZINC_HYDROXIDE: SubstanceProperties(ec_class="Xn", r_code=22),
    Compound.FERROUS_HYDROXIDE: SubstanceProperties(r_code=22, lc_50=1e5, mak_ch=10),
    Compound.DROSS: SubstanceProperties(idlh=1e5, lc_50=1e3, mak_ch=1e4),
    Compound.ASH: SubstanceProperties(idlh=1e5, lc_50=1e3, mak_ch=1e4),
}


def _log_index(value: float, lower: float, upper: float, slope: float, intercept: float) -> float:
    if value <= lower:
        return 1.0
    if value >= upper:
        return 0.0
    return slope * math.log(value) + intercept


def _r_code_index(r_code: int, rules: Sequence[tuple[set[int], float]]) -> float:
    for codes, index in rules:
        if r_code in codes:
            return index
    return 0.0


def _acute_toxicity_index(props: SubstanceProperties) -> float:
    limit = props.idlh if props.idlh is not None else props.erpg_3
    if limit is not None:
        return _log_index(limit, 10, 1e5, -0.109, 1.25)
    if props.ec_class is not None:
        return _ACUTE_EC_CLASS_INDEX.get(props.ec_class, 0.0)
    if props.gk is not None:
        return _ACUTE_GK_INDEX.get(props.gk, 0.0)
    if props.r_code is not None:
        return _r_code_index(props.r_code, _ACUTE_R_CODE_INDEX)
    return 0.0


def _air_hazard_index(props: SubstanceProperties) -> float:
    if props.mak_ch is not None:
        return _log_index(props.mak_ch, 0.1, 1e4, -0.087, 0.8)
    if props.ec_class is not None:
        return _AIR_EC_CLASS_INDEX.get(props.ec_class, 0.0)
    if props.gk is not None:
        return _AIR_GK_INDEX.get(props.gk, 0.0)
    if props.r_code is not None:
        return _r_code_index(props.r_code, _AIR_R_CODE_INDEX)
    return 0.0


def _water_hazard_index(props: SubstanceProperties) -> float:
    if props.lc_50 is not None:
        return _log_index(props.lc_50, 0.1, 1e3, -0.087, 0.8)
    if props.r_code is not None:
        return _r_code_index(props.r_code, _WATER_R_CODE_INDEX)
    if props.gwk is not None:
        return _WATER_GWK_INDEX.get(props.gwk, 0.0)
    return 0.0


def _physical_value(index: float, slope: float, intercept: float) -> float:
    return 10 ** (slope * index + intercept) if index > 0 else 0.0


def compute_physical_values(properties: Mapping[Compound, SubstanceProperties] | None = None) -> np.ndarray:
    """Physical values of the three hazard indicators for every compound.

    Args:
        properties: Property record per compound; defaults to ``SUBSTANCE_PROPERTIES``. Compounds
            missing from the mapping are treated as having no data (physical value 0).

    Returns:
        Array of shape (17, 3) with columns acute toxicity, air hazard and water hazard.
    """
    table = SUBSTANCE_PROPERTIES if properties is None else properties
    values = np.zeros((N_COMPOUNDS, N_HAZARD_CATEGORIES))
    for compound, props in table.items():
        values[compound, ACUTE_TOXICITY] = _physical_value(_acute_toxicity_index(props), 4, 1)
        values[compound, AIR_HAZARD] = _physical_value(_air_hazard_index(props), 5, 2)
        values[compound, WATER_HAZARD] = _physical_value(_water_hazard_index(props), 4, 1)
    return values
