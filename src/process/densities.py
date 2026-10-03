"""Densities of the NaOH (degreasing) and HCl (pickling) aqueous solutions.

Purpose: linear temperature/concentration correlations from the thesis (annex D.3.2).
Author: Jose D. Hernandez-Betancur
Date: 2026-10-02
"""


def naoh_solution_density(temperature_c: float, concentration_wt: float) -> float:
    """Density of a NaOH solution between 1 and 16 % wt.

    Args:
        temperature_c: Solution temperature [degC].
        concentration_wt: NaOH concentration [% wt].

    Returns:
        Density [kg/m3].
    """
    rho_16 = -0.0114 * (temperature_c - 40) / 20 + 1.1645
    rho_1 = -0.0092 * (temperature_c - 40) / 20 + 1.0033
    return 1000.0 * ((rho_16 - rho_1) * (concentration_wt - 1) / 15 + rho_1)


def hcl_solution_density(temperature_c: float, concentration_wt: float) -> float:
    """Density of an HCl solution between 1 and 18 % wt.

    Args:
        temperature_c: Solution temperature [degC].
        concentration_wt: HCl concentration [% wt].

    Returns:
        Density [kg/m3].
    """
    rho_18 = -0.0130 * (temperature_c - 10) / 30 + 1.0920
    rho_1 = -0.0078 * (temperature_c - 10) / 30 + 1.0048
    return 1000.0 * ((rho_18 - rho_1) * (concentration_wt - 1) / 16 + rho_1)
