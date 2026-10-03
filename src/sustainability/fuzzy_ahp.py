"""Fuzzy analytic hierarchy process (extent analysis) with entropy-based expert weighting.

Purpose: relative weights of sustainability categories/indicators from expert pairwise comparisons (annex D.2).
Author: Jose D. Hernandez-Betancur
Date: 2026-10-02
"""

import logging
from dataclasses import dataclass

import numpy as np

logger = logging.getLogger(__name__)

PRESERVE_THESIS_QUIRKS = True

_MAX_CODE = 4
_TRIANGULAR_SCALE = np.array(
    [
        [1, 1, 1],
        [2 / 3, 1, 3 / 2],
        [3 / 2, 2, 5 / 2],
        [5 / 2, 3, 7 / 2],
        [7 / 2, 4, 9 / 2],
    ],
)


@dataclass(frozen=True)
class FuzzyAhpResult:
    """Outcome of the fuzzy AHP.

    Attributes:
        weights: Final weights of the n criteria, summing to 1.
        expert_uncertainty: Weight theta of each expert, summing to 1.
    """

    weights: np.ndarray
    expert_uncertainty: np.ndarray


def sheet_block_to_comparisons(block: np.ndarray, n_experts: int) -> np.ndarray:
    """Reshape the flat spreadsheet block read in MATLAB into one comparison matrix per expert.

    Args:
        block: Array of shape (n_experts * n, n); expert k occupies rows k*n .. (k+1)*n - 1.
        n_experts: Number of experts.

    Returns:
        Array of shape (n_experts, n, n).
    """
    block = np.asarray(block)
    n = block.shape[1]
    if block.ndim != 2 or block.shape[0] != n_experts * n:
        logger.error(f"Sheet block of shape {block.shape} does not hold {n_experts} experts of {n}x{n}")
        raise ValueError(f"Expected a block of shape ({n_experts * n}, {n}), got {block.shape}")
    return block.reshape(n_experts, n, n)


def _reciprocal(numbers: np.ndarray, invert_modal: bool) -> np.ndarray:
    lower, modal, upper = numbers[..., 0], numbers[..., 1], numbers[..., 2]
    return np.stack([1 / upper, 1 / modal if invert_modal else modal, 1 / lower], axis=-1)


def _fuzzy_comparison_matrix(codes: np.ndarray, invert_modal: bool) -> np.ndarray:
    n = codes.shape[0]
    scale = _TRIANGULAR_SCALE[np.abs(codes)]
    reciprocal = _reciprocal(scale, invert_modal)
    positive = (codes >= 0)[..., None]
    upper_form = np.where(positive, scale, reciprocal)
    lower_form = np.where(positive, reciprocal, scale)
    matrix = np.zeros((n, n, 3))
    rows, cols = np.triu_indices(n)
    matrix[cols, rows] = lower_form[rows, cols]
    matrix[rows, cols] = upper_form[rows, cols]
    return matrix


def _synthetic_extent(matrix: np.ndarray, normalise_by_inverse: bool) -> np.ndarray:
    row_sums = matrix.sum(axis=1)
    total = row_sums.sum(axis=0)
    return row_sums / total[::-1] if normalise_by_inverse else row_sums * total


def _possibility_weights(extent: np.ndarray) -> np.ndarray:
    lower, modal, upper = extent[:, 0], extent[:, 1], extent[:, 2]
    modal_i, upper_i = modal[:, None], upper[:, None]
    modal_j, lower_j = modal[None, :], lower[None, :]
    with np.errstate(divide="ignore", invalid="ignore"):
        crossing = (lower_j - upper_i) / ((modal_i - upper_i) - (modal_j - lower_j))
    possibility = np.where(modal_i >= modal_j, 1.0, np.where(lower_j >= upper_i, 0.0, crossing))
    weights = possibility.min(axis=1)
    return weights / weights.sum()


def _expert_weights(codes: np.ndarray, preserve_quirks: bool) -> np.ndarray:
    invert_modal = not preserve_quirks
    extents = (_synthetic_extent(_fuzzy_comparison_matrix(c, invert_modal), invert_modal) for c in codes)
    return np.array([_possibility_weights(extent) for extent in extents])


def _expert_uncertainty(weights: np.ndarray) -> np.ndarray:
    n = weights.shape[1]
    logs = np.log(np.where(weights > 0, weights, 1.0))
    diversification = 1 + (weights * logs).sum(axis=1) / np.log(n)
    total = diversification.sum()
    if total == 0:
        logger.warning("All experts have uniform weights; assigning equal expert uncertainty")
        return np.full(weights.shape[0], 1 / weights.shape[0])
    return diversification / total


def _validate_codes(codes: np.ndarray) -> None:
    if codes.ndim != 3 or codes.shape[1] != codes.shape[2] or codes.shape[1] < 2:
        logger.error(f"Comparison codes have shape {codes.shape}")
        raise ValueError(f"comparison_codes must have shape (n_experts, n, n) with n >= 2, got {codes.shape}")
    if not np.array_equal(codes, np.round(codes)) or np.abs(codes).max() > _MAX_CODE:
        logger.error("Comparison codes must be integers between -4 and 4")
        raise ValueError("comparison_codes must be integers between -4 and 4")


def fuzzy_ahp_weights(
    comparison_codes: np.ndarray,
    *,
    preserve_thesis_quirks: bool = PRESERVE_THESIS_QUIRKS,
) -> FuzzyAhpResult:
    """Compute fuzzy AHP weights from expert comparison codes.

    Code c at (i, j) states how much criterion i outweighs j: 0 equal, 1..4 increasing importance of i over j,
    -1..-4 increasing importance of j over i. Only the upper triangle (including the diagonal) is read.

    With ``preserve_thesis_quirks=True`` (default) the MATLAB behaviour is reproduced: the modal value of a
    reciprocal triangular number is not inverted and the synthetic extent is multiplied by the sum of the
    fuzzy rows instead of by its inverse (annex D.2, lines 76-116 and 149-158). With ``False`` the textbook
    formulas are used.

    Args:
        comparison_codes: Integer array of shape (n_experts, n, n) with values in -4..4.
        preserve_thesis_quirks: Reproduce the thesis computation.

    Returns:
        Final weights and expert uncertainty weights.
    """
    codes = np.asarray(comparison_codes)
    _validate_codes(codes)
    integer_codes = codes.astype(int)
    expert_weights = _expert_weights(integer_codes, preserve_thesis_quirks)
    theta = _expert_uncertainty(expert_weights)
    weights = theta @ expert_weights
    return FuzzyAhpResult(weights=weights / weights.sum(), expert_uncertainty=theta)
