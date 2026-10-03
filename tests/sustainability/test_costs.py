"""Tests of the cost scenarios and their effect on the COM indicator.

Purpose: prices change the raw COM [USD] only; the thesis scenario is the bit-identical default.
Author: Jose D. Hernandez-Betancur
Date: 2026-10-03
"""

import numpy as np
import pytest

from src.optimization.evaluation import evaluate_policy
from src.process.operating_policy import BASELINE_POLICY
from src.sustainability.costs import (
    COST_SCENARIOS,
    MARKET_2025_COSTS,
    RAW_MATERIAL_KEYS,
    THESIS_CORRECTED_COSTS,
    THESIS_COSTS,
    default_costs,
    get_cost_scenario,
)
from src.sustainability.greenscope import Indicator

TEST_KWARGS = {"base_seed": 21, "n_samples": 3, "items": 100_000}


def test_thesis_scenario_matches_matlab_values() -> None:
    prices = THESIS_COSTS.raw_material_prices
    assert tuple(prices) == RAW_MATERIAL_KEYS
    assert prices == {"naoh": 580.0, "hcl": 165.5, "nh4cl": 150.0, "zncl2": 990.0, "zn": 2590.0, "h2o": 0.7755, "nh4oh": 38.11}
    assert THESIS_COSTS.labor_usd_per_year == pytest.approx(4.5 * 4135.89 * 2)


def test_corrected_thesis_scenario_changes_only_nh4oh() -> None:
    changed = {
        k for k in RAW_MATERIAL_KEYS if THESIS_CORRECTED_COSTS.raw_material_prices[k] != THESIS_COSTS.raw_material_prices[k]
    }
    assert changed == {"nh4oh"}
    assert THESIS_CORRECTED_COSTS.nh4oh_usd_per_t > THESIS_COSTS.nh4oh_usd_per_t


def test_market_scenario_uses_sourced_bulk_prices() -> None:
    assert MARKET_2025_COSTS.zn_usd_per_t == pytest.approx(130 * 22.0462, abs=1.0)
    assert MARKET_2025_COSTS.naoh_usd_per_t == pytest.approx(0.5 * 370.0)
    assert MARKET_2025_COSTS.hcl_usd_per_t == 244.0
    assert MARKET_2025_COSTS.labor_usd_per_year == THESIS_COSTS.labor_usd_per_year


def test_default_costs_follow_fidelity_mode() -> None:
    assert default_costs(True) is THESIS_COSTS
    assert default_costs(False) is THESIS_CORRECTED_COSTS


def test_unknown_scenario_rejected() -> None:
    with pytest.raises(ValueError, match="Unknown cost scenario"):
        get_cost_scenario("nope")
    assert set(COST_SCENARIOS) == {"thesis", "thesis_corrected", "market2025"}


def test_prices_move_com_but_not_utility_or_volumes() -> None:
    thesis = evaluate_policy(BASELINE_POLICY, costs=THESIS_COSTS, **TEST_KWARGS)
    market = evaluate_policy(BASELINE_POLICY, costs=MARKET_2025_COSTS, **TEST_KWARGS)
    assert not np.array_equal(thesis.com_usd, market.com_usd)
    np.testing.assert_array_equal(thesis.process_utility, market.process_utility)
    np.testing.assert_array_equal(thesis.polluted_liquid_m3, market.polluted_liquid_m3)
    np.testing.assert_array_equal(thesis.water_intake_m3, market.water_intake_m3)


def test_evaluation_default_is_the_corrected_scenario() -> None:
    default = evaluate_policy(BASELINE_POLICY, **TEST_KWARGS)
    explicit = evaluate_policy(BASELINE_POLICY, costs=THESIS_CORRECTED_COSTS, **TEST_KWARGS)
    np.testing.assert_array_equal(default.unit_indicators, explicit.unit_indicators)


def test_com_score_is_price_independent() -> None:
    thesis = evaluate_policy(BASELINE_POLICY, costs=THESIS_COSTS, **TEST_KWARGS)
    market = evaluate_policy(BASELINE_POLICY, costs=MARKET_2025_COSTS, **TEST_KWARGS)
    np.testing.assert_allclose(
        thesis.unit_scores[:, :, Indicator.MANUFACTURING_COST],
        market.unit_scores[:, :, Indicator.MANUFACTURING_COST],
    )
