"""Tests for the GREENSCOPE indicators."""

import numpy as np
import pytest

from src.sustainability.greenscope import Indicator, _score, compute_greenscope
from src.sustainability.streams import (
    N_COMPOUNDS,
    N_INDICATORS,
    N_INPUT_STREAMS,
    N_OUTPUT_STREAMS,
    N_UNIT_PROCESSES,
    Compound,
    InputStream,
    OutputStream,
    UnitProcess,
)


@pytest.fixture
def streams() -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    rng = np.random.default_rng(7)
    inputs = np.zeros((N_INPUT_STREAMS, N_COMPOUNDS))
    outputs = np.zeros((N_OUTPUT_STREAMS, N_COMPOUNDS))
    inputs[InputStream.STEEL_PIECE, [Compound.STEEL, Compound.TRIGLYCERIDE, Compound.WUSTITE]] = [1e5, 2.0, 30.0]
    inputs[InputStream.DEGREASING_SOLUTION, [Compound.SODIUM_HYDROXIDE]] = 300.0
    inputs[InputStream.DEGREASING_WATER, Compound.WATER] = 1500.0
    inputs[InputStream.RINSING_1_WATER, Compound.WATER] = 2000.0
    inputs[InputStream.PICKLING_SOLUTION, [Compound.HYDROCHLORIC_ACID]] = 600.0
    inputs[InputStream.PICKLING_WATER, Compound.WATER] = 1000.0
    inputs[InputStream.RINSING_2_WATER, Compound.WATER] = 2000.0
    inputs[InputStream.FLUXING_SALTS, [Compound.ZINC_DICHLORIDE, Compound.AMMONIUM_CHLORIDE]] = [40.0, 30.0]
    inputs[InputStream.FLUXING_WATER, Compound.WATER] = 900.0
    inputs[InputStream.FLUXING_NH4OH, Compound.AMMONIUM_HYDROXIDE] = 5.0
    inputs[InputStream.FLUXING_HCL, Compound.HYDROCHLORIC_ACID] = 3.0
    inputs[InputStream.MOLTEN_ZINC, Compound.ZINC] = 4000.0
    outputs[OutputStream.SPENT_DEGREASING, [3, 4, 5, 6]] = [200.0, 1400.0, 3.0, 8.0]
    outputs[OutputStream.REMAINING_GREASE, Compound.TRIGLYCERIDE] = 0.6
    outputs[OutputStream.RINSING_1_WASTEWATER, [3, 4, 5, 6]] = [1.0, 1800.0, 0.5, 1.0]
    outputs[OutputStream.SPENT_PICKLING, [Compound.HYDROCHLORIC_ACID, Compound.WATER, Compound.IRON_DICHLORIDE]] = [
        400.0,
        900.0,
        60.0,
    ]
    outputs[OutputStream.RINSING_2_WASTEWATER, [Compound.HYDROCHLORIC_ACID, Compound.WATER]] = [5.0, 1900.0]
    outputs[OutputStream.SPENT_FLUXING, [Compound.ZINC_DICHLORIDE, Compound.AMMONIUM_CHLORIDE, Compound.WATER]] = [
        35.0,
        25.0,
        880.0,
    ]
    outputs[OutputStream.HYDROXIDE_SLUDGE, [Compound.ZINC_HYDROXIDE, Compound.FERROUS_HYDROXIDE]] = [4.0, 3.0]
    outputs[OutputStream.DROSS, Compound.DROSS] = 60.0
    outputs[OutputStream.ASH, Compound.ASH] = 50.0
    outputs[OutputStream.GALVANIZED_STEEL, [Compound.STEEL, Compound.ZINC]] = [1e5, 3500.0]
    energy = rng.uniform(1e8, 1e9, size=N_UNIT_PROCESSES)
    return inputs, outputs, energy


def _run(streams: tuple[np.ndarray, np.ndarray, np.ndarray], **kwargs: bool):
    inputs, outputs, energy = streams
    return compute_greenscope(inputs, outputs, energy, 300.0, 850.0, 20.0, 5.0, 1e3, **kwargs)


def test_shapes_and_finiteness(streams: tuple[np.ndarray, np.ndarray, np.ndarray]) -> None:
    result = _run(streams)
    for matrix in (result.indicators, result.best, result.worst, result.score):
        assert matrix.shape == (N_UNIT_PROCESSES, N_INDICATORS)
        assert np.isfinite(matrix).all()


def test_score_is_100_at_best_and_0_at_worst() -> None:
    best = np.array([[1.0, 5.0], [2.0, 8.0]])
    worst = np.array([[0.0, 10.0], [4.0, 0.0]])
    assert _score(best, best, worst) == pytest.approx(np.full((2, 2), 100.0))
    assert _score(worst, best, worst) == pytest.approx(np.zeros((2, 2)))


def test_score_degenerate_reference_is_logged(caplog: pytest.LogCaptureFixture) -> None:
    flat = np.ones((1, 2))
    assert _score(flat, flat, flat).tolist() == [[100.0, 100.0]]
    assert "identical best and worst" in caplog.text


def test_hand_computed_indicators(streams: tuple[np.ndarray, np.ndarray, np.ndarray]) -> None:
    inputs, outputs, _ = streams
    result = _run(streams)
    product = outputs[OutputStream.GALVANIZED_STEEL].sum()
    g = result.indicators
    rinse_1 = outputs[OutputStream.RINSING_1_WASTEWATER]
    assert g[UnitProcess.RINSING_1, Indicator.ENVIRONMENTAL_FACTOR] == pytest.approx((rinse_1.sum() - rinse_1[4]) / product)
    assert g[UnitProcess.DEGREASING, Indicator.WATER_CONSUMPTION] == pytest.approx(1.5)
    assert g[UnitProcess.RINSING_1, Indicator.WATER_CONSUMPTION] == pytest.approx((2000 - 0.4 * 1800) / 1000)
    assert g[UnitProcess.RINSING_2, Indicator.RECYCLED_MATERIAL_FRACTION] == pytest.approx(0.4 * 1900 / 2000)
    assert g[UnitProcess.DEGREASING, Indicator.RECYCLED_MATERIAL_FRACTION] == pytest.approx(0.6 * 200 / (2 + 30 + 300 + 1500))
    assert g[:, Indicator.RECYCLING_MASS_FRACTION].tolist() == [0, 1, 1, 1, 0, 1, 0]
    assert g[UnitProcess.DEGREASING, Indicator.HAZARDOUS_SOLID_WASTE] == pytest.approx(0.6 / product)
    assert g[UnitProcess.GALVANIZING, Indicator.SOLID_WASTE_MASS] == pytest.approx(110.0 / product)


def test_energy_intensity_and_atom_economy(streams: tuple[np.ndarray, np.ndarray, np.ndarray]) -> None:
    _, outputs, energy = streams
    product = outputs[OutputStream.GALVANIZED_STEEL].sum()
    g = _run(streams).indicators
    assert g[UnitProcess.GALVANIZING, Indicator.ENERGY_INTENSITY] == pytest.approx(energy[6] * 1e-6 / product)
    assert g[UnitProcess.DRYING, Indicator.ENERGY_INTENSITY] == pytest.approx((10.3 / 3.6) * energy[5] * 1e-6 / product)
    assert g[UnitProcess.RINSING_1, Indicator.ATOM_ECONOMY] == 1.0


def test_manufacturing_cost_score_is_constant(streams: tuple[np.ndarray, np.ndarray, np.ndarray]) -> None:
    score = _run(streams).score[:, Indicator.MANUFACTURING_COST]
    assert score == pytest.approx(np.full(N_UNIT_PROCESSES, 100 * (1 - 2) / (0.38 / 0.85 - 2)))


def test_acidification_quirk_flag(streams: tuple[np.ndarray, np.ndarray, np.ndarray]) -> None:
    quirk = _run(streams, preserve_thesis_quirks=True).indicators
    fixed = _run(streams, preserve_thesis_quirks=False).indicators
    assert (quirk[:, Indicator.ATMOSPHERIC_ACIDIFICATION] == 0).all()
    assert quirk[:, Indicator.PHOTOCHEMICAL_OXIDATION] == pytest.approx(fixed[:, Indicator.ATMOSPHERIC_ACIDIFICATION])
    assert (fixed[:, Indicator.PHOTOCHEMICAL_OXIDATION] == 0).all()
    assert fixed[UnitProcess.PICKLING, Indicator.ATMOSPHERIC_ACIDIFICATION] > 0


def test_invalid_inputs_raise(streams: tuple[np.ndarray, np.ndarray, np.ndarray]) -> None:
    inputs, outputs, energy = streams
    with pytest.raises(ValueError):
        compute_greenscope(inputs[:5], outputs, energy, 1.0, 1.0, 1.0, 1.0, 1.0)
    with pytest.raises(ValueError):
        compute_greenscope(inputs, np.zeros_like(outputs), energy, 1.0, 1.0, 1.0, 1.0, 1.0)
