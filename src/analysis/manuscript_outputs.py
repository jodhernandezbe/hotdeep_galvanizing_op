"""Publication figures and LaTeX tables from persisted optimization results.

Purpose: generate the manuscript outputs (Pareto front, radar, boxplots, utility density, summary table)
from checkpoints and Monte Carlo datasets only — never re-simulating (spec analysis/manuscript-outputs);
entry point `python -m src.analysis.manuscript_outputs`.
Author: Jose D. Hernandez-Betancur
Date: 2026-10-02
"""

import argparse
import json
import logging
from pathlib import Path
from typing import Any, Final

import matplotlib.pyplot as plt  # noqa: E402  (backend fixed by plot_style)
import numpy as np
from matplotlib.axes import Axes
from matplotlib.patches import Rectangle
from scipy.stats import gaussian_kde

from src.analysis.plot_style import (
    BASELINE_COLOR,
    NEUTRAL_COLOR,
    OPTIMIZED_COLOR,
    SEQUENTIAL_CMAP,
    apply_paper_style,
    save_figure,
)
from src.optimization.evaluation import PolicyEvaluation
from src.optimization.mcdm import SUSTAINABILITY_THRESHOLD_PCT, pareto_mask, utility_pct
from src.sustainability.greenscope import Indicator
from src.sustainability.streams import UnitProcess

logger = logging.getLogger(__name__)

RADAR_LABELS: Final = (
    "TR",
    r"$H_{air}$",
    r"$H_{water}$",
    "GWP",
    "PCOP",
    "AP",
    r"$V_{l\mathrm{-}poll}$",
    r"$m_{haz}$",
    r"$m_{solid}$",
    r"$V_{l\mathrm{-}spec}$",
    r"$R_m$",
    "AAE",
    r"$E$-factor",
    r"$W_{RM}$",
    r"$V_{WT}$",
    r"$E_I$",
    "COM",
    r"$\delta_{ISO}$",
)
BOXPLOT_INDICATORS: Final = (
    (Indicator.POLLUTED_LIQUID_VOLUME, r"$V_{l\mathrm{-}poll}$ [m$^3$]"),
    (Indicator.SPECIFIC_LIQUID_VOLUME, r"$V_{l\mathrm{-}spec}$ [m$^3$/kg]"),
    (Indicator.ATOM_ECONOMY, "AAE [-]"),
    (Indicator.RECYCLED_MATERIAL_FRACTION, r"$W_{RM}$ [-]"),
    (Indicator.WATER_CONSUMPTION, r"$V_{WT}$ [m$^3$]"),
    (Indicator.MANUFACTURING_COST, "COM [USD]"),
)
CRITICAL_STAGES: Final = ((UnitProcess.PICKLING, "Pickling"), (UnitProcess.FLUXING, "Fluxing"))
POLICY_LABELS: Final = {
    "degreasing_temperature_c": (r"$T_{degreasing}$", r"$^{\circ}$C"),
    "pickling_hcl_pct": (r"$C_{HCl}$", r"\% wt"),
    "pickling_dip_time_s": (r"$t_{dipping}$", "s"),
    "fluxing_temperature_c": (r"$T_{fluxing}$", r"$^{\circ}$C"),
    "fluxing_ph_target": (r"pH$_{fluxing}$", "--"),
    "fluxing_salt_g_per_l": (r"$C_{salts}$", "g/L"),
    "galvanizing_temperature_c": (r"$T_{galvanizing}$", r"$^{\circ}$C"),
}
KPI_LABELS: Final = {
    "utility_pct": (r"$U_P$", r"\%"),
    "com_usd": ("COM", "USD"),
    "polluted_liquid_m3": (r"$V_{l\mathrm{-}poll}$", r"m$^3$"),
    "water_intake_m3": (r"$V_{WT}$", r"m$^3$"),
    "mean_coating_thickness_um": (r"$\bar{\delta}$", r"$\mu$m"),
    "defect_fraction": (r"$P(\delta < \delta_{ISO})$", "--"),
}
COM_SCALE: Final = 1e6


def figure_pareto(front_f: np.ndarray, compromise: dict[str, Any], figures_dir: Path) -> list[Path]:
    """Figure 1: Pareto projection E[U_P] vs E[COM], colored by V_l-poll, sized by V_WT.

    Args:
        front_f: Objectives of the non-dominated feasible designs on the reporting (full-year) basis, shape (n, 4).
        compromise: Arrays of `compromise.npz` (f, utopia, nadir).
        figures_dir: Destination directory.

    Returns:
        Written file paths.
    """
    front = np.atleast_2d(front_f)
    figure, axis = plt.subplots(figsize=(4.8, 3.6))
    scatter = _pareto_scatter(axis, front)
    _pareto_annotations(axis, compromise)
    figure.colorbar(scatter, ax=axis, label=r"$\mathrm{E}[V_{l\mathrm{-}poll}]$ [m$^3$]")
    axis.set_xlabel(r"$\mathrm{E}[U_P]$ [-]")
    axis.set_ylabel(r"$\mathrm{E}[\mathrm{COM}]$ [$10^6$ USD/yr]")
    axis.set_title("Pareto front projection")
    axis.legend(loc="best")
    return save_figure(figure, figures_dir, "figure1_pareto")


def _pareto_scatter(axis: Axes, front: np.ndarray) -> Any:
    sizes = _size_scale(front[:, 3])
    return axis.scatter(
        -front[:, 0],
        front[:, 1] / COM_SCALE,
        c=front[:, 2],
        s=sizes,
        cmap=SEQUENTIAL_CMAP,
        edgecolors="white",
        linewidths=0.4,
        alpha=0.9,
        zorder=3,
        label=r"Non-dominated solutions (size $\propto \mathrm{E}[V_{WT}]$)",
    )


def _size_scale(values: np.ndarray) -> np.ndarray:
    span = np.ptp(values)
    normalized = (values - values.min()) / span if span > 0 else np.full_like(values, 0.5)
    return 12.0 + 68.0 * normalized


def _pareto_annotations(axis: Axes, compromise: dict[str, Any]) -> None:
    utopia, nadir, best = compromise["utopia"], compromise["nadir"], compromise["f"]
    axis.scatter(-utopia[0], utopia[1] / COM_SCALE, marker="P", s=70, color="#009E73", zorder=4, label="Utopia point")
    axis.scatter(-nadir[0], nadir[1] / COM_SCALE, marker="X", s=70, color=NEUTRAL_COLOR, zorder=4, label="Nadir point")
    axis.scatter(
        -best[0],
        best[1] / COM_SCALE,
        marker="*",
        s=180,
        color=OPTIMIZED_COLOR,
        edgecolors="black",
        linewidths=0.5,
        zorder=5,
        label="Fuzzy best compromise",
    )


def figure_radar(baseline: PolicyEvaluation, optimal: PolicyEvaluation, figures_dir: Path) -> list[Path]:
    """Figure 2: 18-indicator radar chart of mean scores, baseline vs. optimized.

    Args:
        baseline: Deep Monte Carlo batch of the baseline design.
        optimal: Deep Monte Carlo batch of the compromise design.
        figures_dir: Destination directory.

    Returns:
        Written file paths.
    """
    angles = np.linspace(0, 2 * np.pi, len(RADAR_LABELS), endpoint=False)
    figure, axis = plt.subplots(figsize=(4.6, 4.6), subplot_kw={"projection": "polar"})
    for evaluation, label, color in ((baseline, "Baseline", BASELINE_COLOR), (optimal, "Optimized", OPTIMIZED_COLOR)):
        scores = evaluation.process_scores.mean(axis=0)
        _radar_polygon(axis, angles, scores, label, color)
    _radar_axes(axis, angles)
    axis.legend(loc="upper right", bbox_to_anchor=(1.25, 1.1))
    return save_figure(figure, figures_dir, "figure2_radar")


def _radar_polygon(axis: Axes, angles: np.ndarray, scores: np.ndarray, label: str, color: str) -> None:
    closed_angles = np.append(angles, angles[0])
    closed_scores = np.append(scores, scores[0])
    axis.plot(closed_angles, closed_scores, color=color, label=label)
    axis.fill(closed_angles, closed_scores, color=color, alpha=0.12)


def _radar_axes(axis: Axes, angles: np.ndarray) -> None:
    axis.set_xticks(angles)
    axis.set_xticklabels(RADAR_LABELS)
    axis.set_ylim(0, 100)
    axis.set_yticks([20, 40, 60, 80, 100])
    axis.set_yticklabels(["20", "40", "60", "80", "100 %"])
    axis.tick_params(pad=1)


def figure_boxplots(baseline: PolicyEvaluation, optimal: PolicyEvaluation, figures_dir: Path) -> list[Path]:
    """Figure 3: grouped boxplots of the critical-stage indicators, baseline vs. optimized.

    Args:
        baseline: Deep Monte Carlo batch of the baseline design.
        optimal: Deep Monte Carlo batch of the compromise design.
        figures_dir: Destination directory.

    Returns:
        Written file paths.
    """
    figure, axes = plt.subplots(2, 3, figsize=(7.2, 4.6))
    for axis, (indicator, label) in zip(axes.ravel(), BOXPLOT_INDICATORS):
        _stage_boxes(axis, baseline, optimal, indicator)
        axis.set_ylabel(label)
    handles = [Rectangle((0, 0), 1, 1, facecolor=color, alpha=0.6) for color in (BASELINE_COLOR, OPTIMIZED_COLOR)]
    figure.legend(handles, ["Baseline", "Optimized"], loc="lower center", ncol=2, bbox_to_anchor=(0.5, -0.04))
    return save_figure(figure, figures_dir, "figure3_critical_stage_boxplots")


def _stage_boxes(axis: Axes, baseline: PolicyEvaluation, optimal: PolicyEvaluation, indicator: Indicator) -> None:
    data = [design.stage_indicator(unit, indicator) for unit, _ in CRITICAL_STAGES for design in (baseline, optimal)]
    boxes = axis.boxplot(data, positions=[1, 1.8, 3.2, 4.0], widths=0.6, patch_artist=True, showfliers=False)
    for patch, color in zip(boxes["boxes"], [BASELINE_COLOR, OPTIMIZED_COLOR] * len(CRITICAL_STAGES)):
        patch.set_facecolor(color)
        patch.set_alpha(0.6)
    for median in boxes["medians"]:
        median.set_color("black")
    axis.set_xticks([1.4, 3.6])
    axis.set_xticklabels([stage for _, stage in CRITICAL_STAGES])


def figure_utility_density(baseline: PolicyEvaluation, optimal: PolicyEvaluation, figures_dir: Path) -> list[Path]:
    """Figure 4: Gaussian KDE of U_P [%] with the LM_P = 80 % threshold shading.

    Args:
        baseline: Deep Monte Carlo batch of the baseline design.
        optimal: Deep Monte Carlo batch of the compromise design.
        figures_dir: Destination directory.

    Returns:
        Written file paths.
    """
    figure, axis = plt.subplots(figsize=(4.8, 3.4))
    for evaluation, label, color in ((baseline, "Baseline", BASELINE_COLOR), (optimal, "Optimized", OPTIMIZED_COLOR)):
        _density_curve(axis, utility_pct(evaluation), label, color)
    axis.axvline(SUSTAINABILITY_THRESHOLD_PCT, color="black", linewidth=0.9, linestyle="--")
    axis.text(SUSTAINABILITY_THRESHOLD_PCT + 0.4, axis.get_ylim()[1] * 0.95, r"$LM_P = 80\,\%$", va="top", fontsize=8)
    axis.set_xlabel(r"$U_P$ [% of attainable maximum]")
    axis.set_ylabel("Probability density")
    axis.legend(loc="upper left")
    return save_figure(figure, figures_dir, "figure4_utility_density")


def _density_curve(axis: Axes, values: np.ndarray, label: str, color: str) -> None:
    density = gaussian_kde(values)
    grid = np.linspace(values.min() - 3 * values.std(), values.max() + 3 * values.std(), 400)
    probability = float(np.mean(values >= SUSTAINABILITY_THRESHOLD_PCT))
    axis.plot(grid, density(grid), color=color, label=f"{label} ($P_{{sost}}$ = {probability:.3f})")
    exceed = grid >= SUSTAINABILITY_THRESHOLD_PCT
    axis.fill_between(grid[exceed], density(grid[exceed]), color=color, alpha=0.25)


def table_summary(summary: dict[str, Any], tables_dir: Path) -> Path:
    """Table 1: LaTeX summary of decision variables, KPIs and P_sostenible.

    Args:
        summary: Parsed `summary.json` of the deep characterization.
        tables_dir: Destination directory.

    Returns:
        Path of the written `.tex` file.
    """
    rows = [*_policy_rows(summary), r"\midrule", *_kpi_rows(summary), r"\midrule", _probability_row(summary)]
    tables_dir.mkdir(parents=True, exist_ok=True)
    path = tables_dir / "table1_summary.tex"
    path.write_text(_table_shell("\n".join(rows)))
    logger.info("Saved table %s", path)
    return path


def _table_shell(body: str) -> str:
    return (
        "\\begin{table}[htbp]\n\\centering\n"
        "\\caption{Decision variables and key performance indicators before and after optimization "
        "(mean $\\pm$ std; 95\\,\\% confidence intervals in brackets; $N = 1000$ Monte Carlo samples).}\n"
        "\\label{tab:summary}\n"
        "\\begin{tabular}{llcc}\n\\toprule\n"
        " & Units & Baseline & Optimized \\\\\n\\midrule\n"
        f"{body}\n"
        "\\bottomrule\n\\end{tabular}\n\\end{table}\n"
    )


def _policy_rows(summary: dict[str, Any]) -> list[str]:
    rows = []
    for key, (symbol, units) in POLICY_LABELS.items():
        base, opt = summary["baseline"]["policy"][key], summary["optimal"]["policy"][key]
        rows.append(f"{symbol} & {units} & {base:.3g} & {opt:.3g} \\\\")
    return rows


def _kpi_rows(summary: dict[str, Any]) -> list[str]:
    rows = []
    for key, (symbol, units) in KPI_LABELS.items():
        cells = [_stat_cell(summary[name]["indicators"][key]) for name in ("baseline", "optimal")]
        rows.append(f"{symbol} & {units} & {cells[0]} & {cells[1]} \\\\")
    return rows


def _stat_cell(stats: dict[str, float]) -> str:
    return f"${stats['mean']:.4g} \\pm {stats['std']:.3g}$ " f"$[{stats['ci_lower']:.4g}, {stats['ci_upper']:.4g}]$"


def _probability_row(summary: dict[str, Any]) -> str:
    base, opt = summary["baseline"]["p_sustainable"], summary["optimal"]["p_sustainable"]
    return f"$P_{{sostenible}}$ & -- & {base:.3f} & {opt:.3f} \\\\"


def generate_all(mc_dir: Path, results_dir: Path) -> None:
    """Regenerate every manuscript output from persisted results only.

    Args:
        mc_dir: Directory with `front.npz`, `compromise.npz`, baseline/optimal `.npz` and `summary.json`.
        results_dir: Root receiving `figures/` and `tables/`.
    """
    apply_paper_style()
    with np.load(mc_dir / "compromise.npz") as data:
        compromise = {key: data[key] for key in data.files}
    front_f = _reporting_front(mc_dir)
    baseline = PolicyEvaluation.load(mc_dir / "baseline.npz")
    optimal = PolicyEvaluation.load(mc_dir / "optimal.npz")
    figures_dir, tables_dir = results_dir / "figures", results_dir / "tables"
    figure_pareto(front_f, compromise, figures_dir)
    figure_radar(baseline, optimal, figures_dir)
    figure_boxplots(baseline, optimal, figures_dir)
    figure_utility_density(baseline, optimal, figures_dir)
    table_summary(json.loads((mc_dir / "summary.json").read_text()), tables_dir)


def _reporting_front(mc_dir: Path) -> np.ndarray:
    with np.load(mc_dir / "front.npz") as data:
        objectives = data["f"]
        feasible = data["eligible"] if "eligible" in data.files else (data["g"] <= 0).all(axis=1)
    if not feasible.any():
        logger.warning("No eligible design in front.npz; plotting the whole non-dominated set")
        feasible[:] = True
    candidates = objectives[feasible]
    return candidates[pareto_mask(candidates)]


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate the manuscript figures and tables from persisted results")
    parser.add_argument("--mc-dir", type=Path, default=Path("results/mc"))
    parser.add_argument("--results-dir", type=Path, default=Path("results"))
    return parser.parse_args()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    arguments = _parse_args()
    generate_all(arguments.mc_dir, arguments.results_dir)
