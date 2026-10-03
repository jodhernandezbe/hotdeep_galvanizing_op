"""Tests for the drying oven heat balance."""

import pytest

from src.process.drying import drying_heat_j


def test_drying_heat_without_flux_is_steel_sensible_heat() -> None:
    assert drying_heat_j(1000.0, 0.0, 40.0, 0.5) == pytest.approx(1000 * 450 * 60)


def test_drying_heat_adds_flux_sensible_and_evaporation_terms() -> None:
    expected = (1000 * 450 + 96.232 * 2.0) * 60 + 22570600 * 0.01 * 0.4 * 2.0
    assert drying_heat_j(1000.0, 2.0, 40.0, 0.4) == pytest.approx(expected)
