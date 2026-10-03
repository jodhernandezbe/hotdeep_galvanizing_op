"""Random steel lots entering the hot-dip galvanizing line.

Purpose: sample lot size, piece mass, geometry, composition and surface contamination (thesis annex D.3).
Author: Jose D. Hernandez-Betancur
Date: 2026-10-02
"""

from bisect import bisect_right
from dataclasses import dataclass
from typing import Final, NamedTuple

import numpy as np

from src.common.constants import MW_FE, STEEL_DENSITY

GAUGE_RANGE_M: Final = (0.0003, 0.0320)
SILICON_RANGE_WT: Final = (0.15, 0.25)
RUST_RANGE_G_PER_M2: Final = (300.0, 590.0)
DEGREASING_FRACTION: Final = 0.3
GREASE_KG_PER_KG_STEEL: Final = 10 * 1e-6
GREASE_PURITY_RANGE: Final = (0.94, 0.96)
GREASE_BASE_MW: Final = 41.0716
RUST_MOLAR_MASS_RATIO: Final = MW_FE / 70.8534
RUST_SURFACE_FRACTION: Final = 0.7 / 0.3
FULL_LOT_SIZE: Final = 111600


class LotClass(NamedTuple):
    """Product family of incoming pieces: cumulative probability, lot-size range and piece-mass range."""

    upper_probability: float
    lot_size_range: tuple[int, int]
    mass_range_kg: tuple[float, float]


LOT_CLASSES: Final = (
    LotClass(0.2909, (200, 54000), (0.02553, 0.02555)),
    LotClass(0.3985, (576, 29843), (0.09651, 0.09659)),
    LotClass(0.4935, (1092, 23101), (0.009428, 0.009438)),
    LotClass(0.5876, (285, 23661), (0.08460, 0.08466)),
    LotClass(0.6806, (46, 37230), (0.02440, 0.02442)),
    LotClass(0.7549, (10000, 24000), (0.12283, 0.12293)),
    LotClass(0.8220, (428, 28636), (0.07007, 0.07013)),
    LotClass(0.8862, (4614, 42930), (0.05802, 0.05808)),
    LotClass(0.9458, (3300, 39600), (0.08855, 0.08863)),
    LotClass(1.0, (FULL_LOT_SIZE, FULL_LOT_SIZE), (0.010611, 0.010623)),
)


UPPER_PROBABILITIES: Final = tuple(lot_class.upper_probability for lot_class in LOT_CLASSES)


@dataclass(frozen=True)
class SteelLot:
    """A lot of steel pieces with its contamination.

    Attributes:
        mass_kg: Piece masses [kg].
        gauge_m: Piece gauge (thickness) [m].
        surface_area_m2: Piece surface area [m2].
        silicon_wt: Silicon content of each piece [% wt].
        needs_degreasing: Boolean mask of greased pieces.
        grease_mw: Molecular weight of the grease of this lot [g/mol].
        rust_kg: Total rust mass of the lot [kg].
    """

    mass_kg: np.ndarray
    gauge_m: np.ndarray
    surface_area_m2: np.ndarray
    silicon_wt: np.ndarray
    needs_degreasing: np.ndarray
    grease_mw: float
    rust_kg: float

    @property
    def size(self) -> int:
        """Number of pieces in the lot."""
        return int(self.mass_kg.size)

    @property
    def total_mass_kg(self) -> float:
        """Total steel mass [kg]."""
        return float(self.mass_kg.sum())

    @property
    def greased_mass_kg(self) -> float:
        """Mass of the pieces that need degreasing [kg]."""
        return float(self.mass_kg[self.needs_degreasing].sum())

    @property
    def grease_and_oil_kg(self) -> float:
        """Mass of grease and oil on the lot [kg]."""
        return GREASE_KG_PER_KG_STEEL * self.greased_mass_kg

    @property
    def rusted_surface_mass_kg(self) -> float:
        """Steel mass tied up in the rust layer, used as the zinc-iron alloy reference [kg]."""
        return self.rust_kg * RUST_MOLAR_MASS_RATIO * RUST_SURFACE_FRACTION


def draw_lot_class(rng: np.random.Generator) -> LotClass:
    """Pick the product family of the next lot.

    Args:
        rng: Random number generator.

    Returns:
        Selected lot class.
    """
    return LOT_CLASSES[bisect_right(UPPER_PROBABILITIES, rng.uniform())]


def draw_steel_lot(rng: np.random.Generator) -> SteelLot:
    """Sample the next lot entering the line.

    Args:
        rng: Random number generator.

    Returns:
        Sampled lot.
    """
    lot_class = draw_lot_class(rng)
    size = _draw_lot_size(lot_class, rng)
    mass_kg = rng.uniform(*lot_class.mass_range_kg, size)
    gauge_m = rng.uniform(*GAUGE_RANGE_M, size)
    surface_area_m2 = _surface_area(mass_kg, gauge_m)
    return SteelLot(
        mass_kg=mass_kg,
        gauge_m=gauge_m,
        surface_area_m2=surface_area_m2,
        silicon_wt=rng.uniform(*SILICON_RANGE_WT, size),
        needs_degreasing=rng.uniform(size=size) <= DEGREASING_FRACTION,
        grease_mw=_draw_grease_mw(rng),
        rust_kg=_draw_rust_kg(surface_area_m2, rng),
    )


def _draw_lot_size(lot_class: LotClass, rng: np.random.Generator) -> int:
    low, high = lot_class.lot_size_range
    if low == high:
        return low
    return round(rng.uniform(low, high))


def _surface_area(mass_kg: np.ndarray, gauge_m: np.ndarray) -> np.ndarray:
    length_m = np.sqrt(mass_kg / (STEEL_DENSITY * gauge_m))
    return 2.0 * length_m**2 + 4.0 * length_m * gauge_m


def _draw_grease_mw(rng: np.random.Generator) -> float:
    return GREASE_BASE_MW / (1.0 - rng.uniform(*GREASE_PURITY_RANGE))


def _draw_rust_kg(surface_area_m2: np.ndarray, rng: np.random.Generator) -> float:
    rust_g_per_m2 = rng.uniform(*RUST_RANGE_G_PER_M2, surface_area_m2.size)
    return float(np.dot(rust_g_per_m2, surface_area_m2) * 1e-3)
