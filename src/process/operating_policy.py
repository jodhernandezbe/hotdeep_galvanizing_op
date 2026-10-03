"""Controllable operating conditions of the hot-dip galvanizing line.

Purpose: explicit decision-variable vector for robust optimization under uncertainty (OPTIMIZATION.md).
Author: Jose D. Hernandez-Betancur
Date: 2026-10-02
"""

import logging
from dataclasses import dataclass, fields
from typing import Final

import numpy as np

logger = logging.getLogger(__name__)

POLICY_BOUNDS: Final[dict[str, tuple[float, float]]] = {
    "degreasing_temperature_c": (40.0, 60.0),
    "pickling_hcl_pct": (12.0, 18.0),
    "pickling_dip_time_s": (600.0, 1200.0),
    "fluxing_temperature_c": (40.0, 60.0),
    "fluxing_ph_target": (4.0, 5.0),
    "fluxing_salt_g_per_l": (300.0, 500.0),
    "galvanizing_temperature_c": (445.0, 455.0),
    "pickling_renewal_fe_g_per_l": (60.0, 150.0),
}
N_DECISION_VARIABLES: Final = len(POLICY_BOUNDS)
THESIS_PICKLING_RENEWAL_FE_G_PER_L: Final = 150.0


@dataclass(frozen=True)
class OperatingPolicy:
    """Decision variables of the line, validated against `POLICY_BOUNDS`.

    Attributes:
        degreasing_temperature_c: Fresh degreasing bath temperature [degC].
        pickling_hcl_pct: Fresh normal pickling bath HCl concentration [% wt].
        pickling_dip_time_s: Normal pickling dipping time [s].
        fluxing_temperature_c: Fresh fluxing bath temperature [degC].
        fluxing_ph_target: Fresh fluxing bath pH.
        fluxing_salt_g_per_l: Total ZnCl2/NH4Cl salt loading at the fixed 60/40 ratio [g/L].
        galvanizing_temperature_c: Zinc bath temperature set-point [degC].
        pickling_renewal_fe_g_per_l: Fe2+ concentration that triggers a normal pickling bath renewal [g/L].
            Renewing late exhausts the acid and carries residual rust into the flux; renewing early spends
            acid and spent-bath volume. The thesis renews at the 150 g/L exhaustion limit (the default).
    """

    degreasing_temperature_c: float
    pickling_hcl_pct: float
    pickling_dip_time_s: float
    fluxing_temperature_c: float
    fluxing_ph_target: float
    fluxing_salt_g_per_l: float
    galvanizing_temperature_c: float
    pickling_renewal_fe_g_per_l: float = THESIS_PICKLING_RENEWAL_FE_G_PER_L

    def __post_init__(self) -> None:
        """Validate every decision variable against its box bounds.

        Raises:
            ValueError: If a variable lies outside its bounds.
        """
        for name, (lower, upper) in POLICY_BOUNDS.items():
            value = getattr(self, name)
            if not lower <= value <= upper:
                message = f"{name}={value} is outside its bounds [{lower}, {upper}]"
                logger.error(message)
                raise ValueError(message)

    def to_array(self) -> np.ndarray:
        """Decision variables as a vector in `POLICY_BOUNDS` field order.

        Returns:
            Array of shape (`N_DECISION_VARIABLES`,).
        """
        return np.array([getattr(self, variable.name) for variable in fields(self)], dtype=float)

    @classmethod
    def from_array(cls, x: np.ndarray) -> "OperatingPolicy":
        """Build a policy from a decision vector in `POLICY_BOUNDS` field order.

        Args:
            x: Decision vector of shape (`N_DECISION_VARIABLES`,), or of the legacy 7-variable
                layout, in which case the pickling renewal trigger keeps its thesis value.

        Returns:
            Validated operating policy.

        Raises:
            ValueError: If the vector has the wrong length or a value is out of bounds.
        """
        values = np.asarray(x, dtype=float).ravel()
        if values.size not in (N_DECISION_VARIABLES, N_DECISION_VARIABLES - 1):
            message = f"Decision vector must have {N_DECISION_VARIABLES} (or the legacy 7) entries, got {values.size}"
            logger.error(message)
            raise ValueError(message)
        return cls(*(float(value) for value in values))


BASELINE_POLICY: Final = OperatingPolicy(
    degreasing_temperature_c=50.0,
    pickling_hcl_pct=17.0,
    pickling_dip_time_s=900.0,
    fluxing_temperature_c=50.0,
    fluxing_ph_target=4.5,
    fluxing_salt_g_per_l=400.0,
    galvanizing_temperature_c=450.0,
)
"""Nominal thesis operating point: the midpoints of the thesis draws (baseline design of the manuscript)."""


def policy_lower_bounds() -> np.ndarray:
    """Lower box bounds in `POLICY_BOUNDS` field order.

    Returns:
        Array of shape (`N_DECISION_VARIABLES`,).
    """
    return np.array([lower for lower, _ in POLICY_BOUNDS.values()], dtype=float)


def policy_upper_bounds() -> np.ndarray:
    """Upper box bounds in `POLICY_BOUNDS` field order.

    Returns:
        Array of shape (`N_DECISION_VARIABLES`,).
    """
    return np.array([upper for _, upper in POLICY_BOUNDS.values()], dtype=float)
