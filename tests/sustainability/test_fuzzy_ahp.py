"""Tests for the fuzzy AHP."""

import numpy as np
import pytest

from src.sustainability.fuzzy_ahp import fuzzy_ahp_weights, sheet_block_to_comparisons


def _equal_codes(n_experts: int, n: int) -> np.ndarray:
    return np.zeros((n_experts, n, n), dtype=int)


def test_equal_importance_gives_equal_weights() -> None:
    result = fuzzy_ahp_weights(_equal_codes(3, 4))
    assert result.weights == pytest.approx(np.full(4, 0.25))
    assert result.expert_uncertainty == pytest.approx(np.full(3, 1 / 3))


def test_dominant_criterion_gets_largest_weight_with_textbook_formulas() -> None:
    codes = _equal_codes(2, 4)
    codes[:, 0, 1:] = 4
    result = fuzzy_ahp_weights(codes, preserve_thesis_quirks=False)
    assert result.weights.argmax() == 0
    assert result.weights.sum() == pytest.approx(1.0)


def test_negative_code_reverses_preference() -> None:
    forward = np.array([[[0, 3, 3], [0, 0, 1], [0, 0, 0]]])
    reverse = np.array([[[0, -3, -3], [0, 0, -1], [0, 0, 0]]])
    w_forward = fuzzy_ahp_weights(forward, preserve_thesis_quirks=False).weights
    w_reverse = fuzzy_ahp_weights(reverse, preserve_thesis_quirks=False).weights
    assert w_forward[0] > w_forward[1] >= w_forward[2]
    assert w_reverse[0] < w_reverse[1] <= w_reverse[2]


def test_lower_triangle_is_ignored() -> None:
    upper = np.array([[[0, 2, 1], [0, 0, -1], [0, 0, 0]]])
    noisy = upper.copy()
    noisy[0, 2, 0] = 4
    noisy[0, 1, 0] = -3
    assert fuzzy_ahp_weights(noisy).weights == pytest.approx(fuzzy_ahp_weights(upper).weights)


@pytest.mark.parametrize("preserve", [True, False])
def test_random_codes_yield_valid_distributions(preserve: bool) -> None:
    rng = np.random.default_rng(0)
    codes = rng.integers(-4, 5, size=(10, 5, 5))
    result = fuzzy_ahp_weights(codes, preserve_thesis_quirks=preserve)
    assert result.weights.sum() == pytest.approx(1.0)
    assert result.expert_uncertainty.sum() == pytest.approx(1.0)
    assert (result.weights >= 0).all() and (result.expert_uncertainty >= 0).all()


def test_decisive_expert_receives_more_weight_than_indifferent_one() -> None:
    codes = _equal_codes(2, 3)
    codes[1, 0, 1:] = 4
    result = fuzzy_ahp_weights(codes, preserve_thesis_quirks=False)
    assert result.expert_uncertainty[1] > result.expert_uncertainty[0]


def test_invalid_codes_raise() -> None:
    with pytest.raises(ValueError):
        fuzzy_ahp_weights(np.full((1, 3, 3), 5))
    with pytest.raises(ValueError):
        fuzzy_ahp_weights(np.zeros((3, 3)))


def test_sheet_block_to_comparisons_splits_per_expert() -> None:
    block = np.arange(18).reshape(6, 3)
    comparisons = sheet_block_to_comparisons(block, 2)
    assert comparisons.shape == (2, 3, 3)
    assert comparisons[1, 0].tolist() == [9, 10, 11]
    with pytest.raises(ValueError):
        sheet_block_to_comparisons(block, 3)
