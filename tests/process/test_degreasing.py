"""Tests for the degreasing balance."""

import numpy as np
import pytest

from src.process.degreasing import NAOH_MW_DEGREASING, degrease
from src.process.densities import naoh_solution_density

COMPOSITION = np.array([15.0, 85.0, 0.0, 0.0])


def run(**overrides):
    args = dict(
        grease_and_oil_kg=2.0,
        grease_mw=860.0,
        solution_mass_kg=14000.0,
        composition_wt=COMPOSITION,
        temperature_c=50.0,
        greased_steel_kg=3000.0,
        previous_heat_j=0.0,
        ambient_c=22.0,
    )
    args.update(overrides)
    return degrease(**args)


def test_grease_balance() -> None:
    result = run()
    assert result.saponified_kg == pytest.approx(1.4)
    assert result.saponified_kg + result.remaining_grease_kg == pytest.approx(2.0)


def test_removed_solution_uses_density() -> None:
    result = run()
    assert result.removed_solution_kg == pytest.approx(1e-6 * 3000.0 * naoh_solution_density(50.0, 15.0))


def test_mass_and_composition_balance() -> None:
    result = run()
    retained = 14000.0 - result.removed_solution_kg
    produced = 1.4 * (92.0937 + (860.0 - 41.0716 + 68.9694) - NAOH_MW_DEGREASING * 3) / 860.0
    assert result.solution_mass_kg == pytest.approx(retained + produced)
    assert result.composition_wt.sum() == pytest.approx(100.0)
    assert result.composition_wt[2] > 0 and result.composition_wt[3] > 0
    assert result.composition_wt[0] < 15.0


def test_energy_balance_closed_form() -> None:
    result = run(greased_steel_kg=0.0, previous_heat_j=0.0, grease_and_oil_kg=0.0)
    cp = -627.6 * (15.0 - 1.08) / 16.73 + 4121.2
    lost = abs((50.0 - 22.0) / 35.1)
    mass = result.solution_mass_kg
    expected = ((1 - 0.1 * lost) * (50.0 - 25) + 25) * 1.0
    assert result.temperature_c == pytest.approx(expected)
    assert result.heat_j == pytest.approx(0.1 * lost * mass * cp * 25.0)


def test_steel_cools_the_bath() -> None:
    assert run().temperature_c < 50.0
