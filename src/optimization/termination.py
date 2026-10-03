"""Hypervolume-stagnation termination for the NSGA-II run.

Purpose: stop the optimization when the normalized hypervolume stops improving (spec optimization/nsga2).
Author: Jose D. Hernandez-Betancur
Date: 2026-10-02
"""

import logging
from typing import Any, Final

import numpy as np
from pymoo.core.termination import Termination
from pymoo.indicators.hv import HV

logger = logging.getLogger(__name__)

DEFAULT_HV_TOLERANCE: Final = 1e-4
DEFAULT_HV_WINDOW: Final = 15
DEFAULT_MIN_GENERATIONS: Final = 100
REFERENCE_POINT_MARGIN: Final = 1.1
_NORMALIZATION_EPS: Final = 1e-12


class HypervolumeStagnation(Termination):
    """Terminate at a generation budget or when the running hypervolume stagnates.

    The ideal/nadir normalization is frozen at the first generation that has feasible solutions. The hypervolume of
    a crowding-truncated population is not monotone, so stagnation compares the best hypervolume of the last
    `window` generations with the best before them, and cannot fire before `min_generations`.

    Attributes:
        hv_history: Hypervolume of the feasible non-dominated set per generation (NaN before feasibility).
    """

    def __init__(
        self,
        n_max_gen: int,
        tolerance: float = DEFAULT_HV_TOLERANCE,
        window: int = DEFAULT_HV_WINDOW,
        min_generations: int = DEFAULT_MIN_GENERATIONS,
        generation_offset: int = 0,
        hv_history: list[float] | None = None,
        normalization: tuple[np.ndarray, np.ndarray] | None = None,
    ) -> None:
        """Configure the stagnation criterion.

        Args:
            n_max_gen: Generation budget.
            tolerance: Relative hypervolume improvement below which the run is considered stagnant.
            window: Number of consecutive generations the improvement is measured over.
            min_generations: Generations that must elapse before stagnation may stop the run.
            generation_offset: Generations already completed before this run (non-zero when resuming).
            hv_history: Hypervolume history of those generations (resume only).
            normalization: Ideal and nadir points frozen at the first feasible generation (resume only).
        """
        super().__init__()
        self.n_max_gen = n_max_gen
        self.tolerance = tolerance
        self.window = window
        self.min_generations = min_generations
        self.generation_offset = generation_offset
        self.hv_history: list[float] = [] if hv_history is None else list(hv_history)
        self.reason: str = "generation budget"
        self._ideal: np.ndarray | None = None if normalization is None else normalization[0]
        self._nadir: np.ndarray | None = None if normalization is None else normalization[1]

    @property
    def normalization(self) -> tuple[np.ndarray, np.ndarray] | None:
        """Ideal and nadir points used to normalize the objectives, or None before the first feasible generation."""
        if self._ideal is None or self._nadir is None:
            return None
        return self._ideal, self._nadir

    def _update(self, algorithm: Any) -> float:
        self._record_hypervolume(algorithm)
        if self._stagnated():
            self.reason = f"hypervolume stagnation (tol={self.tolerance}, window={self.window})"
            return 1.0
        return min(1.0, (algorithm.n_gen + self.generation_offset) / self.n_max_gen)

    def _record_hypervolume(self, algorithm: Any) -> None:
        objectives = self._feasible_objectives(algorithm)
        if objectives.size == 0:
            self.hv_history.append(float("nan"))
            return
        if self._ideal is None:
            self._ideal = objectives.min(axis=0)
            self._nadir = objectives.max(axis=0) + _NORMALIZATION_EPS
        self.hv_history.append(self._normalized_hypervolume(objectives))

    def _feasible_objectives(self, algorithm: Any) -> np.ndarray:
        optimum = algorithm.opt
        if optimum is None or len(optimum) == 0:
            return np.empty((0,))
        feasible = optimum.get("feas")
        return np.atleast_2d(optimum.get("F")[feasible])

    def _normalized_hypervolume(self, objectives: np.ndarray) -> float:
        if self._ideal is None or self._nadir is None:
            return 0.0
        span = np.maximum(self._nadir - self._ideal, _NORMALIZATION_EPS)
        normalized = np.clip((objectives - self._ideal) / span, 0.0, REFERENCE_POINT_MARGIN)
        indicator = HV(ref_point=np.full(objectives.shape[1], REFERENCE_POINT_MARGIN))
        value = indicator(normalized)
        return float(value) if value is not None else 0.0

    def _stagnated(self) -> bool:
        history = np.asarray(self.hv_history, dtype=float)
        if history.size < max(self.min_generations, self.window + 1):
            return False
        before, recent = history[: -self.window], history[-self.window :]
        if not (np.isfinite(before).any() and np.isfinite(recent).any()):
            return False
        improvement = np.nanmax(recent) - np.nanmax(before)
        return bool(improvement < self.tolerance * max(abs(np.nanmax(recent)), _NORMALIZATION_EPS))
