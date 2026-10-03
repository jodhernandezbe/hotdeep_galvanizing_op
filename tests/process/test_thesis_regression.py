"""Regression pin of the seeded thesis-mode yearly simulation.

Purpose: guard that operating-policy plumbing leaves thesis-mode numerics bit-identical (change
add-nsga2-robust-optimization, spec simulation/operating-policy).
Author: Jose D. Hernandez-Betancur
Date: 2026-10-02
"""

import numpy as np

from src.process.simulation import YearResult, simulate_year

REGRESSION_SEED = 20261002
REGRESSION_ITEMS = 200_000
EXPECTED_DIGEST = np.array(
    [
        10074.300291726875,
        282.4972242113123,
        0.03029333674147068,
        0.021205335719029477,
        521.8612317841487,
        75.85816132554191,
        75.1933877003004,
        60328.8539549701,
        0.0,
        0.0,
        10057.98995119913,
        19948940.0,
        301975.0,
        2524519000.0354958,
        161718162.35592407,
        295691535.5384139,
        18724879733.793262,
        14198.179324546061,
        14176.943681622837,
        13601.18572467636,
        13578.342874044787,
    ]
)


def _digest(year: YearResult) -> np.ndarray:
    t = year.totals
    return np.array(
        [
            t.steel_kg,
            t.rust_kg,
            t.grease_and_oil_kg,
            t.saponified_kg,
            t.zinc_coating_kg,
            t.dross_kg,
            t.ash_kg,
            t.molten_zinc_kg,
            t.hcl_added_kg,
            t.nh4oh_added_kg,
            t.quality_mass_weighted,
            t.standard_thickness_sum_um,
            float(t.n_quality_pieces),
            t.degreasing_heat_j,
            t.fluxing_heat_j,
            t.drying_heat_j,
            t.galvanizing_heat_j,
            year.normal_pickling.initial_mass_kg,
            year.normal_pickling.final_mass_kg,
            year.fluxing.initial_mass_kg,
            year.fluxing.final_mass_kg,
        ]
    )


def test_thesis_mode_digest_is_bit_identical() -> None:
    rng = np.random.default_rng(REGRESSION_SEED)
    year = simulate_year(REGRESSION_ITEMS, rng, preserve_thesis_quirks=True)
    np.testing.assert_array_equal(_digest(year), EXPECTED_DIGEST)
