"""Tests for the GREENSCOPE hazard physical values."""

import math

import numpy as np
import pytest

from src.sustainability.hazard import (
    ACUTE_TOXICITY,
    AIR_HAZARD,
    WATER_HAZARD,
    SubstanceProperties,
    compute_physical_values,
)
from src.sustainability.streams import N_COMPOUNDS, Compound


def test_shape_and_non_negative() -> None:
    values = compute_physical_values()
    assert values.shape == (N_COMPOUNDS, 3)
    assert (values >= 0).all()


def test_naoh_acute_toxicity_saturates_at_idlh_10() -> None:
    values = compute_physical_values()
    assert values[Compound.SODIUM_HYDROXIDE, ACUTE_TOXICITY] == pytest.approx(10**5)


def test_hcl_air_hazard_from_mak() -> None:
    index = -0.087 * math.log(3) + 0.8
    values = compute_physical_values()
    assert values[Compound.HYDROCHLORIC_ACID, AIR_HAZARD] == pytest.approx(10 ** (5 * index + 2))


def test_hcl_acute_toxicity_from_idlh_log_branch() -> None:
    index = -0.109 * math.log(74.56) + 1.25
    values = compute_physical_values()
    assert values[Compound.HYDROCHLORIC_ACID, ACUTE_TOXICITY] == pytest.approx(10 ** (4 * index + 1))


def test_no_hazard_when_limits_exceed_upper_bounds() -> None:
    values = compute_physical_values()
    assert values[Compound.STEEL].tolist() == [0.0, 0.0, 0.0]


def test_water_hazard_uses_lc50_before_r_code() -> None:
    index = -0.087 * math.log(160) + 0.8
    values = compute_physical_values()
    assert values[Compound.SODIUM_HYDROXIDE, WATER_HAZARD] == pytest.approx(10 ** (4 * index + 1))


def test_fallback_to_classification_codes() -> None:
    props = {
        Compound.ZINC_DICHLORIDE: SubstanceProperties(ec_class="Xn", r_code=22),
        Compound.ZINC_HYDROXIDE: SubstanceProperties(r_code=22),
        Compound.WATER: SubstanceProperties(gk=2, gwk=1),
    }
    values = compute_physical_values(props)
    assert values[Compound.ZINC_DICHLORIDE, ACUTE_TOXICITY] == pytest.approx(10 ** (4 * 0.375 + 1))
    assert values[Compound.ZINC_DICHLORIDE, AIR_HAZARD] == pytest.approx(10 ** (5 * 0.3 + 2))
    assert values[Compound.ZINC_HYDROXIDE, ACUTE_TOXICITY] == pytest.approx(10 ** (4 * 0.375 + 1))
    assert values[Compound.WATER, AIR_HAZARD] == pytest.approx(10 ** (5 * 0.7 + 2))
    assert values[Compound.WATER, WATER_HAZARD] == pytest.approx(10 ** (4 * 0.125 + 1))


def test_corrosive_class_without_numeric_data_has_no_acute_value() -> None:
    values = compute_physical_values({Compound.IRON_DICHLORIDE: SubstanceProperties(ec_class="C", gk=1)})
    assert values[Compound.IRON_DICHLORIDE, ACUTE_TOXICITY] == 0.0
    assert np.isfinite(values).all()
