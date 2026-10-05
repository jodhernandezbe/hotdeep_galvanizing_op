"""Tests of the pickling renewal trigger sweep.

Purpose: the sweep returns one row per trigger with the headline keys and persists npz + JSON.
Author: Jose D. Hernandez-Betancur
Date: 2026-10-05
"""

import json
from pathlib import Path

import numpy as np

from src.analysis.trigger_sweep import default_triggers, save_sweep, sweep_renewal_trigger


def test_default_triggers_span_the_bounds() -> None:
    triggers = default_triggers(4)
    assert triggers[0] == 60.0 and triggers[-1] == 150.0 and triggers.shape == (4,)


def test_sweep_rows_and_persistence(tmp_path: Path) -> None:
    result = sweep_renewal_trigger(np.array([60.0, 150.0]), base_seed=3, n_samples=2, items=50_000)
    assert result["triggers"].shape == (2,) and result["utility_pct"].shape == (2,)
    assert {"com_usd", "polluted_liquid_m3", "hcl_purchased_t", "p_sustainable"} <= set(result)
    save_sweep(result, tmp_path, "sweep")
    table = json.loads((tmp_path / "sweep.json").read_text())
    assert len(table["triggers"]) == 2 and (tmp_path / "sweep.npz").exists()
