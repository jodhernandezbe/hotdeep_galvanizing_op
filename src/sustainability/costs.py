"""Economic parameters of the manufacturing-cost (COM) indicator, as swappable scenarios.

Purpose: keep the thesis (2016-2018) prices for thesis mode, a unit-corrected variant for corrected mode and a
market-2025 scenario, without touching the equations; prices only affect the raw COM [USD], never the GREENSCOPE scores (docs/LITERATURE.md).
Author: Jose D. Hernandez-Betancur
Date: 2026-10-03
"""

import logging
from dataclasses import dataclass
from typing import Final

logger = logging.getLogger(__name__)

RAW_MATERIAL_KEYS: Final = ("naoh", "hcl", "nh4cl", "zncl2", "zn", "h2o", "nh4oh")


@dataclass(frozen=True)
class CostParameters:
    """Raw-material prices of the COM indicator [USD/t] and the labor cost.

    Attributes:
        name: Scenario identifier (key of `COST_SCENARIOS`).
        naoh_usd_per_t: NaOH, 50 % wt solution.
        hcl_usd_per_t: HCl solution.
        nh4cl_usd_per_t: Ammonium chloride.
        zncl2_usd_per_t: Zinc chloride.
        zn_usd_per_t: Zinc, 99.9 % wt.
        h2o_usd_per_t: Water.
        nh4oh_usd_per_t: Ammonium hydroxide, 30 % wt.
        labor_usd_per_year: Operating labor of the plant [USD/year].
    """

    name: str
    naoh_usd_per_t: float
    hcl_usd_per_t: float
    nh4cl_usd_per_t: float
    zncl2_usd_per_t: float
    zn_usd_per_t: float
    h2o_usd_per_t: float
    nh4oh_usd_per_t: float
    labor_usd_per_year: float

    @property
    def raw_material_prices(self) -> dict[str, float]:
        """Prices keyed by `RAW_MATERIAL_KEYS` [USD/t]."""
        return {key: float(getattr(self, f"{key}_usd_per_t")) for key in RAW_MATERIAL_KEYS}


THESIS_COSTS: Final = CostParameters(
    name="thesis",
    naoh_usd_per_t=580.0,
    hcl_usd_per_t=165.5,
    nh4cl_usd_per_t=150.0,
    zncl2_usd_per_t=990.0,
    zn_usd_per_t=2590.0,
    h2o_usd_per_t=0.7755,
    nh4oh_usd_per_t=38.11,
    labor_usd_per_year=4.5 * 4135.89 * 2,
)

THESIS_CORRECTED_COSTS: Final = CostParameters(
    name="thesis_corrected",
    naoh_usd_per_t=THESIS_COSTS.naoh_usd_per_t,
    hcl_usd_per_t=THESIS_COSTS.hcl_usd_per_t,
    nh4cl_usd_per_t=THESIS_COSTS.nh4cl_usd_per_t,
    zncl2_usd_per_t=THESIS_COSTS.zncl2_usd_per_t,
    zn_usd_per_t=THESIS_COSTS.zn_usd_per_t,
    h2o_usd_per_t=THESIS_COSTS.h2o_usd_per_t,
    nh4oh_usd_per_t=173.0,
    labor_usd_per_year=THESIS_COSTS.labor_usd_per_year,
)

MARKET_2025_COSTS: Final = CostParameters(
    name="market2025",
    naoh_usd_per_t=0.5 * 370.0,
    hcl_usd_per_t=244.0,
    nh4cl_usd_per_t=260.0,
    zncl2_usd_per_t=1296.0,
    zn_usd_per_t=2866.0,
    h2o_usd_per_t=THESIS_COSTS.h2o_usd_per_t,
    nh4oh_usd_per_t=173.0,
    labor_usd_per_year=THESIS_COSTS.labor_usd_per_year,
)

COST_SCENARIOS: Final = {scenario.name: scenario for scenario in (THESIS_COSTS, THESIS_CORRECTED_COSTS, MARKET_2025_COSTS)}


def default_costs(preserve_thesis_quirks: bool) -> CostParameters:
    """Cost scenario matching the fidelity mode: thesis prices as written, or with the NH4OH unit defect corrected.

    Args:
        preserve_thesis_quirks: Thesis-faithful mode.

    Returns:
        `THESIS_COSTS` in thesis mode, `THESIS_CORRECTED_COSTS` in corrected mode.
    """
    return THESIS_COSTS if preserve_thesis_quirks else THESIS_CORRECTED_COSTS


def get_cost_scenario(name: str) -> CostParameters:
    """Look up a cost scenario by name.

    Args:
        name: Scenario identifier (see `COST_SCENARIOS`).

    Returns:
        The scenario's cost parameters.

    Raises:
        ValueError: If the scenario does not exist.
    """
    if name not in COST_SCENARIOS:
        message = f"Unknown cost scenario '{name}'; available: {sorted(COST_SCENARIOS)}"
        logger.error(message)
        raise ValueError(message)
    return COST_SCENARIOS[name]
