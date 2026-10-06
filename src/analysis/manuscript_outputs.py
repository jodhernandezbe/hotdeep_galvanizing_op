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
    ACCENT_COLOR,
    BASELINE_COLOR,
    NEUTRAL_COLOR,
    OPTIMIZED_COLOR,
    SEQUENTIAL_CMAP,
    apply_paper_style,
    save_figure,
)
from src.optimization.evaluation import PolicyEvaluation
from src.optimization.mcdm import SUSTAINABILITY_THRESHOLD_PCT, sustainability_probability, utility_pct
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
    "pickling_renewal_fe_g_per_l": (r"$c_{Fe,trigger}$", "g/L"),
}
DESIGN_LABELS: Final = {"asis": "As-is operation", "baseline": "Nominal set-points", "optimal": "Compromise design"}
DESIGN_COLORS: Final = {"asis": BASELINE_COLOR, "baseline": ACCENT_COLOR, "optimal": OPTIMIZED_COLOR}
KPI_LABELS: Final = {
    "utility_pct": (r"$U_P$", r"\%"),
    "com_usd": ("COM", "USD"),
    "polluted_liquid_m3": (r"$V_{l\mathrm{-}poll}$", r"m$^3$"),
    "water_intake_m3": (r"$V_{WT}$", r"m$^3$"),
    "mean_coating_thickness_um": (r"$\bar{\delta}$", r"$\mu$m"),
    "defect_fraction": (r"$P(\delta < \delta_{ISO})$", "--"),
}
COM_SCALE: Final = 1e6


def figure_pareto(front: dict[str, np.ndarray], compromise: dict[str, Any], figures_dir: Path) -> list[Path]:
    """Figure 1: Pareto projection E[U_P] vs E[COM] with the vetoed arm, in full view and zoomed on the eligible set.

    Eligible designs are colored by E[V_l-poll]; designs excluded by the no-backsliding veto are drawn as hollow
    grey crosses so the arm the published utility rewards (frequent pickling renewal) stays visible.

    Args:
        front: Arrays of `front.npz` (x, f_mean, eligible, asis_f, baseline_f_mean).
        compromise: Arrays of `compromise.npz` (x).
        figures_dir: Destination directory.

    Returns:
        Written file paths.
    """
    objectives, eligible = front["f_mean"], front["eligible"].astype(bool)
    best = objectives[_compromise_row(front["x"], compromise["x"])]
    figure, (full, zoom) = plt.subplots(1, 2, figsize=(7.2, 3.4))
    for axis, mask in ((full, np.ones_like(eligible)), (zoom, eligible)):
        scatter = _pareto_scatter(axis, objectives[eligible], objectives[eligible, 2].min(), objectives[eligible, 2].max())
        if (~eligible & mask).any():
            _vetoed_scatter(axis, objectives[~eligible & mask])
        _reference_points(axis, front["asis_f"], front["baseline_f_mean"], best)
        axis.set_xlabel(r"$\mathrm{E}[U_P]$ [-]")
    full.set_ylabel(r"$\mathrm{E}[\mathrm{COM}]$ [$10^6$ USD/yr]")
    full.set_title("(a) Whole non-dominated set")
    zoom.set_title("(b) Designs eligible under the veto")
    figure.colorbar(scatter, ax=[full, zoom], label=r"$\mathrm{E}[V_{l\mathrm{-}poll}]$ [m$^3$/yr]", shrink=0.9)
    full.legend(loc="upper left", fontsize=7)
    return save_figure(figure, figures_dir, "figure1_pareto")


def _compromise_row(x: np.ndarray, compromise_x: np.ndarray) -> int:
    matches = np.where(np.all(np.isclose(x, compromise_x), axis=1))[0]
    if matches.size == 0:
        message = "The compromise design is not a row of front.npz"
        logger.error(message)
        raise ValueError(message)
    return int(matches[0])


def _pareto_scatter(axis: Axes, front: np.ndarray, vmin: float, vmax: float) -> Any:
    sizes = _size_scale(front[:, 3])
    return axis.scatter(
        -front[:, 0],
        front[:, 1] / COM_SCALE,
        c=front[:, 2],
        s=sizes,
        cmap=SEQUENTIAL_CMAP,
        vmin=vmin,
        vmax=vmax,
        edgecolors="white",
        linewidths=0.4,
        alpha=0.9,
        zorder=3,
        label=r"Eligible (size $\propto \mathrm{E}[V_{WT}]$)",
    )


def _vetoed_scatter(axis: Axes, front: np.ndarray) -> None:
    axis.scatter(
        -front[:, 0],
        front[:, 1] / COM_SCALE,
        marker="x",
        s=22,
        color=NEUTRAL_COLOR,
        linewidths=0.8,
        zorder=2,
        label="Excluded by the no-backsliding veto",
    )


def _size_scale(values: np.ndarray) -> np.ndarray:
    span = np.ptp(values)
    normalized = (values - values.min()) / span if span > 0 else np.full_like(values, 0.5)
    return 12.0 + 68.0 * normalized


def _reference_points(axis: Axes, asis: np.ndarray, nominal: np.ndarray, best: np.ndarray) -> None:
    axis.scatter(-asis[0], asis[1] / COM_SCALE, marker="^", s=60, color=BASELINE_COLOR, zorder=4, label="As-is operation")
    axis.scatter(
        -nominal[0],
        nominal[1] / COM_SCALE,
        marker="s",
        s=45,
        facecolors="none",
        edgecolors=BASELINE_COLOR,
        zorder=4,
        label="Nominal set-points",
    )
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


def figure_radar(designs: dict[str, PolicyEvaluation], figures_dir: Path) -> list[Path]:
    """Figure 2: 18-indicator radar chart of mean scores for the as-is, nominal and compromise designs.

    Args:
        designs: Deep Monte Carlo batches keyed by design name (`DESIGN_LABELS` keys).
        figures_dir: Destination directory.

    Returns:
        Written file paths.
    """
    angles = np.linspace(0, 2 * np.pi, len(RADAR_LABELS), endpoint=False)
    figure, axis = plt.subplots(figsize=(4.6, 4.6), subplot_kw={"projection": "polar"})
    for name, evaluation in designs.items():
        _radar_polygon(axis, angles, evaluation.process_scores.mean(axis=0), DESIGN_LABELS[name], DESIGN_COLORS[name])
    _radar_axes(axis, angles)
    axis.legend(loc="upper right", bbox_to_anchor=(1.3, 1.12), fontsize=7)
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


def figure_boxplots(designs: dict[str, PolicyEvaluation], figures_dir: Path) -> list[Path]:
    """Figure 3: grouped boxplots of the critical-stage indicators for the as-is, nominal and compromise designs.

    Args:
        designs: Deep Monte Carlo batches keyed by design name (`DESIGN_LABELS` keys).
        figures_dir: Destination directory.

    Returns:
        Written file paths.
    """
    figure, axes = plt.subplots(2, 3, figsize=(7.2, 4.6))
    for axis, (indicator, label) in zip(axes.ravel(), BOXPLOT_INDICATORS):
        _stage_boxes(axis, designs, indicator)
        axis.set_ylabel(label)
    handles = [Rectangle((0, 0), 1, 1, facecolor=DESIGN_COLORS[name], alpha=0.6) for name in designs]
    labels = [DESIGN_LABELS[name] for name in designs]
    figure.legend(handles, labels, loc="outside lower center", ncol=len(designs))
    return save_figure(figure, figures_dir, "figure3_critical_stage_boxplots")


def _stage_boxes(axis: Axes, designs: dict[str, PolicyEvaluation], indicator: Indicator) -> None:
    names = list(designs)
    data = [designs[name].stage_indicator(unit, indicator) for unit, _ in CRITICAL_STAGES for name in names]
    width, gap = 0.55, 0.7
    positions = [
        stage * (len(names) * gap + 1.0) + index * gap for stage in range(len(CRITICAL_STAGES)) for index in range(len(names))
    ]
    boxes = axis.boxplot(data, positions=positions, widths=width, patch_artist=True, showfliers=False)
    for patch, name in zip(boxes["boxes"], names * len(CRITICAL_STAGES)):
        patch.set_facecolor(DESIGN_COLORS[name])
        patch.set_alpha(0.6)
    for median in boxes["medians"]:
        median.set_color("black")
    centers = [np.mean(positions[stage * len(names) : (stage + 1) * len(names)]) for stage in range(len(CRITICAL_STAGES))]
    axis.set_xticks(centers)
    axis.set_xticklabels([stage for _, stage in CRITICAL_STAGES])


def figure_utility_density(designs: dict[str, PolicyEvaluation], figures_dir: Path) -> list[Path]:
    """Figure 4: Gaussian KDE of U_P [%] for the three designs with the LM_P = 80 % threshold.

    The legend reports P_sustainable as defined in the 2019 study (assumed normal, sigma = (U_max - mean)/3);
    the empirical exceedance fraction is degenerate at full-year scale and is not shown.

    Args:
        designs: Deep Monte Carlo batches keyed by design name (`DESIGN_LABELS` keys).
        figures_dir: Destination directory.

    Returns:
        Written file paths.
    """
    figure, axis = plt.subplots(figsize=(4.8, 3.4))
    for name, evaluation in designs.items():
        probability = sustainability_probability(evaluation)
        _density_curve(
            axis, utility_pct(evaluation), f"{DESIGN_LABELS[name]} ($P_{{sust}}$ = {probability:.3f})", DESIGN_COLORS[name]
        )
    axis.axvline(SUSTAINABILITY_THRESHOLD_PCT, color="black", linewidth=0.9, linestyle="--")
    axis.text(
        SUSTAINABILITY_THRESHOLD_PCT - 0.02, axis.get_ylim()[1] * 0.95, r"$LM_P = 80\,\%$", va="top", ha="right", fontsize=8
    )
    axis.set_xlabel(r"$U_P$ [% of attainable maximum]")
    axis.set_ylabel("Probability density")
    axis.legend(loc="upper left", fontsize=7)
    return save_figure(figure, figures_dir, "figure4_utility_density")


def _density_curve(axis: Axes, values: np.ndarray, label: str, color: str) -> None:
    density = gaussian_kde(values)
    grid = np.linspace(values.min() - 3 * values.std(), values.max() + 3 * values.std(), 400)
    axis.plot(grid, density(grid), color=color, label=label)
    axis.fill_between(grid, density(grid), color=color, alpha=0.15)


SWEEP_PANELS: Final = (
    ("utility_pct", r"$U_P$ [% of $U_{P,max}$]"),
    ("polluted_liquid_m3", r"$\mathrm{E}[V_{l\mathrm{-}poll}]$ [m$^3$/yr]"),
    ("com_usd", r"$\mathrm{E}[\mathrm{COM}]$ [$10^6$ USD/yr]"),
)
FE_PLATEAU_G_PER_L: Final = 130.0


def figure_trigger_sweep(sweeps: dict[str, dict[str, np.ndarray]], figures_dir: Path) -> list[Path]:
    """Figure 5: response of utility, polluted liquid and cost to the pickling renewal trigger (one-dimensional sweep).

    Only the utility depends on the atom-economy basis, so panel (a) shows one line per instrument while panels (b)
    and (c), identical for both instruments, show a single series.

    Args:
        sweeps: Sweep tables keyed by instrument label (e.g. "Published AAE", "Fed-basis AAE"), each with the
            arrays of `trigger_sweep.npz`.
        figures_dir: Destination directory.

    Returns:
        Written file paths.
    """
    figure, axes = plt.subplots(1, len(SWEEP_PANELS), figsize=(7.2, 2.7))
    first = next(iter(sweeps.values()))
    for index, (axis, (key, ylabel)) in enumerate(zip(axes, SWEEP_PANELS)):
        if key == "utility_pct":
            for (label, sweep), color in zip(sweeps.items(), (BASELINE_COLOR, OPTIMIZED_COLOR)):
                axis.plot(sweep["triggers"], sweep[key], marker="o", markersize=3.5, color=color, label=label)
        else:
            values = first[key] / COM_SCALE if key == "com_usd" else first[key]
            axis.plot(first["triggers"], values, marker="o", markersize=3.5, color="#555555")
        axis.axvline(FE_PLATEAU_G_PER_L, color=NEUTRAL_COLOR, linestyle=":", linewidth=1.0)
        axis.set_xlabel(r"Fe$^{2+}$ renewal trigger [g/L]")
        axis.set_ylabel(ylabel)
        axis.set_title(f"({'abc'[index]})", loc="left")
    figure.legend(loc="outside lower center", ncol=len(sweeps), fontsize=7.5)
    return save_figure(figure, figures_dir, "figure5_trigger_sweep")


def load_sweeps(sweep_dir: Path) -> dict[str, dict[str, np.ndarray]]:
    """Read the trigger sweeps present in a directory.

    Args:
        sweep_dir: Directory written by `src.analysis.trigger_sweep`.

    Returns:
        Sweep tables keyed by instrument label; empty when no sweep file exists.
    """
    files = (("Published AAE (limiting reagent)", "trigger_sweep.npz"), ("Fed-reagent AAE", "trigger_sweep_fedae.npz"))
    sweeps: dict[str, dict[str, np.ndarray]] = {}
    for label, name in files:
        if (sweep_dir / name).exists():
            with np.load(sweep_dir / name) as data:
                sweeps[label] = {key: data[key] for key in data.files}
    return sweeps


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


TABLE_DESIGNS: Final = ("asis", "baseline", "optimal")


def _table_shell(body: str) -> str:
    return (
        "\\begin{table}[htbp]\n\\centering\n"
        "\\caption{Decision variables and key performance indicators of the as-is operation, the nominal set-points and "
        "the compromise design (mean $\\pm$ std; 95\\,\\% confidence intervals in brackets; $N = 1000$ Monte Carlo "
        "samples; $P_{sustainable}$ as defined in the 2019 study).}\n"
        "\\label{tab:summary}\n"
        "\\begin{tabular}{llccc}\n\\toprule\n"
        " & Units & As-is & Nominal & Compromise \\\\\n\\midrule\n"
        f"{body}\n"
        "\\bottomrule\n\\end{tabular}\n\\end{table}\n"
    )


def _policy_rows(summary: dict[str, Any]) -> list[str]:
    rows = []
    for key, (symbol, units) in POLICY_LABELS.items():
        cells = []
        for name in TABLE_DESIGNS:
            policy = summary.get(name, {}).get("policy")
            cells.append("random" if policy is None else f"{policy[key]:.3g}")
        rows.append(f"{symbol} & {units} & " + " & ".join(cells) + " \\\\")
    return rows


def _kpi_rows(summary: dict[str, Any]) -> list[str]:
    rows = []
    for key, (symbol, units) in KPI_LABELS.items():
        cells = [_stat_cell(summary[name]["indicators"][key]) for name in TABLE_DESIGNS if name in summary]
        rows.append(f"{symbol} & {units} & " + " & ".join(cells) + " \\\\")
    return rows


def _stat_cell(stats: dict[str, float]) -> str:
    return f"${stats['mean']:.4g} \\pm {stats['std']:.3g}$ " f"$[{stats['ci_lower']:.4g}, {stats['ci_upper']:.4g}]$"


def _probability_row(summary: dict[str, Any]) -> str:
    cells = [f"{summary[name]['p_sustainable']:.3f}" for name in TABLE_DESIGNS if name in summary]
    return "$P_{sustainable}$ & -- & " + " & ".join(cells) + " \\\\"


def generate_all(mc_dir: Path, results_dir: Path, sweep_dir: Path | None = None) -> None:
    """Regenerate every manuscript output from persisted results only.

    Args:
        mc_dir: Directory with `front.npz`, `compromise.npz`, baseline/optimal `.npz` and `summary.json`.
        results_dir: Root receiving `figures/` and `tables/`.
        sweep_dir: Directory with the trigger sweeps; figure 5 is skipped when None or empty.
    """
    apply_paper_style()
    with np.load(mc_dir / "compromise.npz") as data:
        compromise = {key: data[key] for key in data.files}
    with np.load(mc_dir / "front.npz", allow_pickle=True) as data:
        front = {key: data[key] for key in data.files}
    designs = {
        name: PolicyEvaluation.load(mc_dir / f"{name}.npz") for name in DESIGN_LABELS if (mc_dir / f"{name}.npz").exists()
    }
    figures_dir, tables_dir = results_dir / "figures", results_dir / "tables"
    figure_pareto(front, compromise, figures_dir)
    figure_radar(designs, figures_dir)
    figure_boxplots(designs, figures_dir)
    figure_utility_density(designs, figures_dir)
    sweeps = load_sweeps(sweep_dir) if sweep_dir is not None else {}
    if sweeps:
        figure_trigger_sweep(sweeps, figures_dir)
    else:
        logger.warning("No trigger sweep found; figure 5 skipped")
    table_summary(json.loads((mc_dir / "summary.json").read_text()), tables_dir)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate the manuscript figures and tables from persisted results")
    parser.add_argument("--mc-dir", type=Path, default=Path("results/mc"))
    parser.add_argument("--results-dir", type=Path, default=Path("results"))
    parser.add_argument("--sweep-dir", type=Path, default=Path("results/sweeps"))
    return parser.parse_args()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    arguments = _parse_args()
    generate_all(arguments.mc_dir, arguments.results_dir, arguments.sweep_dir)
