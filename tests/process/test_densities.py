"""Tests for the solution density correlations."""

import pytest

from src.process.densities import hcl_solution_density, naoh_solution_density


def test_naoh_density_at_reference_points() -> None:
    assert naoh_solution_density(40.0, 1.0) == pytest.approx(1003.3)
    assert naoh_solution_density(40.0, 16.0) == pytest.approx(1164.5)


def test_hcl_density_at_reference_points() -> None:
    assert hcl_solution_density(10.0, 1.0) == pytest.approx(1004.8)
    assert hcl_solution_density(10.0, 17.0) == pytest.approx(1004.8 + 16 / 16 * (1092.0 - 1004.8))


def test_density_decreases_with_temperature() -> None:
    assert naoh_solution_density(60.0, 14.0) < naoh_solution_density(40.0, 14.0)
    assert hcl_solution_density(40.0, 17.0) < hcl_solution_density(10.0, 17.0)
