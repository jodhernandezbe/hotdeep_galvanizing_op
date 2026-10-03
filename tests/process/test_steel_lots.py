"""Tests for the random steel lots."""

import numpy as np
import pytest

from src.process import steel_lots
from src.process.steel_lots import LOT_CLASSES, draw_lot_class, draw_steel_lot


def test_lot_class_probabilities_are_increasing_and_close_at_one() -> None:
    probabilities = [lot_class.upper_probability for lot_class in LOT_CLASSES]
    assert probabilities == sorted(probabilities)
    assert probabilities[-1] == 1.0


class _FixedDraw:
    def __init__(self, draw: float) -> None:
        self._draw = draw

    def uniform(self) -> float:
        return self._draw


@pytest.mark.parametrize(
    ("draw", "expected_index"),
    [(0.0, 0), (0.2908, 0), (0.2909, 1), (0.9457, 8), (0.9458, 9), (0.9999, 9)],
)
def test_lot_class_selection_follows_cumulative_probability(draw: float, expected_index: int) -> None:
    assert draw_lot_class(_FixedDraw(draw)) is LOT_CLASSES[expected_index]  # type: ignore[arg-type]


def test_lot_arrays_share_size_and_respect_ranges() -> None:
    lot = draw_steel_lot(np.random.default_rng(1))
    assert lot.size == lot.gauge_m.size == lot.surface_area_m2.size == lot.silicon_wt.size == lot.needs_degreasing.size
    assert lot.gauge_m.min() >= steel_lots.GAUGE_RANGE_M[0]
    assert lot.gauge_m.max() <= steel_lots.GAUGE_RANGE_M[1]
    assert lot.silicon_wt.min() >= steel_lots.SILICON_RANGE_WT[0]
    assert lot.silicon_wt.max() <= steel_lots.SILICON_RANGE_WT[1]


def test_surface_area_matches_plate_geometry() -> None:
    mass_kg, gauge_m = np.array([0.0255]), np.array([0.002])
    length_m = np.sqrt(0.0255 / (7850.0 * 0.002))
    expected = 2 * length_m**2 + 4 * length_m * 0.002
    assert steel_lots._surface_area(mass_kg, gauge_m)[0] == pytest.approx(expected)


def test_grease_is_proportional_to_greased_mass() -> None:
    lot = draw_steel_lot(np.random.default_rng(2))
    assert lot.grease_and_oil_kg == pytest.approx(1e-5 * lot.mass_kg[lot.needs_degreasing].sum())
    assert 0 < lot.greased_mass_kg < lot.total_mass_kg


def test_rust_within_contamination_range_and_surface_mass_factor() -> None:
    lot = draw_steel_lot(np.random.default_rng(3))
    area = lot.surface_area_m2.sum()
    assert 0.3 * area <= lot.rust_kg <= 0.59 * area
    assert lot.rusted_surface_mass_kg == pytest.approx(lot.rust_kg * (55.845 / 70.8534) * (0.7 / 0.3))


def test_grease_molecular_weight_range() -> None:
    mws = [draw_steel_lot(np.random.default_rng(seed)).grease_mw for seed in range(5)]
    assert all(41.0716 / 0.06 <= mw <= 41.0716 / 0.04 for mw in mws)


def test_same_seed_gives_same_lot() -> None:
    first = draw_steel_lot(np.random.default_rng(9))
    second = draw_steel_lot(np.random.default_rng(9))
    np.testing.assert_array_equal(first.mass_kg, second.mass_kg)
