"""Relative weights of the sustainability categories and indicators reported in the thesis.

Purpose: Table 4-1 (fuzzy analytic hierarchy process over 10 experts), usable when the expert survey is not available.
Author: Jose D. Hernandez-Betancur
Date: 2026-10-02
"""

from typing import Final

import numpy as np

from src.sustainability.utility import build_indicator_weights

CATEGORY_WEIGHTS: Final = np.array([0.1433, 0.1770, 0.1163, 0.2500, 0.3134])
ENVIRONMENT_WEIGHTS: Final = np.array(
    [0.1760, 0.0608, 0.0504, 0.0382, 0.0928, 0.1450, 0.1258, 0.0311, 0.0896, 0.0168, 0.1735],
)
EFFICIENCY_WEIGHTS: Final = np.array([0.8116, 0.0440, 0.0078, 0.1366])


def thesis_indicator_weights() -> np.ndarray:
    """Indicator weights of Table 4-1.

    Returns:
        Weights of the 17 GREENSCOPE indicators followed by the quality weight, length 18.
    """
    return build_indicator_weights(CATEGORY_WEIGHTS, ENVIRONMENT_WEIGHTS, EFFICIENCY_WEIGHTS)
