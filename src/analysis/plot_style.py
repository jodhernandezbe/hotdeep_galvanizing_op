"""Publication style for the manuscript figures.

Purpose: shared matplotlib configuration (300 DPI, serif, paper layout) and the validated color roles
(spec analysis/manuscript-outputs).
Author: Jose D. Hernandez-Betancur
Date: 2026-10-02
"""

import logging
from pathlib import Path
from typing import Any, Final, cast

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.figure import Figure  # noqa: E402

logger = logging.getLogger(__name__)

BASELINE_COLOR: Final = "#0072B2"
OPTIMIZED_COLOR: Final = "#D55E00"
NEUTRAL_COLOR: Final = "#999999"
ACCENT_COLOR: Final = "#009E73"
SEQUENTIAL_CMAP: Final = "viridis"
FIGURE_DPI: Final = 300

PAPER_RC: Final[dict[str, Any]] = {
    "figure.dpi": FIGURE_DPI,
    "savefig.dpi": FIGURE_DPI,
    "font.family": "serif",
    "font.serif": ["DejaVu Serif", "Times New Roman", "Times"],
    "mathtext.fontset": "dejavuserif",
    "font.size": 8.5,
    "axes.titlesize": 9.5,
    "axes.labelsize": 9.0,
    "xtick.labelsize": 8.0,
    "ytick.labelsize": 8.0,
    "legend.fontsize": 8.0,
    "axes.linewidth": 0.8,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "grid.color": "#d9d9d9",
    "grid.linewidth": 0.5,
    "grid.alpha": 0.8,
    "lines.linewidth": 1.6,
    "legend.frameon": False,
    "figure.constrained_layout.use": True,
}


def apply_paper_style() -> None:
    """Install the publication rcParams for all subsequent figures."""
    plt.rcParams.update(cast(Any, PAPER_RC))


def save_figure(figure: Figure, out_dir: Path, name: str) -> list[Path]:
    """Save a figure as vector PDF and raster PNG at 300 DPI.

    Args:
        figure: Figure to persist.
        out_dir: Destination directory (created if missing).
        name: File stem (no extension).

    Returns:
        The two written paths.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = [out_dir / f"{name}.pdf", out_dir / f"{name}.png"]
    figure.savefig(paths[0], metadata={"CreationDate": None})
    figure.savefig(paths[1])
    plt.close(figure)
    logger.info("Saved figure %s (.pdf/.png)", out_dir / name)
    return paths
