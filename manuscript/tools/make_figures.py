"""Build the manuscript flow figures (draw.io source + PNG) from one specification each.

Purpose: Figure 1 (framework), Figure 2 (HDG line and decision variables), Figure 3 (optimization loop).
Author: Jose D. Hernandez-Betancur
Date: 2026-10-03

Run from the repository root: `python manuscript/tools/make_figures.py`.
"""

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from diagram import Badge, Diagram, Edge, LegendItem, Node, to_drawio, to_png  # noqa: E402

logger = logging.getLogger(__name__)

OUT_DIR = Path(__file__).resolve().parents[1] / "figures"
WIDTH = 780
LEFT = 70
FULL = WIDTH - LEFT - 30


def framework() -> Diagram:
    """Figure 1: overview of the optimization framework."""
    d = Diagram("HDG-framework", WIDTH + 80, 1000)
    d.nodes += [
        Node("in", LEFT, 20, FULL, 110, "Inputs", color="gray", group=True),
        Node("in_x", LEFT + 20, 56, 330, 62, "Decision vector x", ("7 operating variables with box bounds",), "redsolid"),
        Node(
            "in_xi",
            LEFT + 380,
            56,
            280,
            62,
            "Uncertain inputs",
            ("steel lots, composition,", "contamination, ambient T"),
            "orange",
        ),
        Node("sim", LEFT, 168, FULL, 130, "Stage-resolved simulation of the HDG line", color="blue_bg", group=True),
        Node(
            "sim_a",
            LEFT + 20,
            206,
            200,
            78,
            "Mass and energy",
            (
                "balances of the 7 unit",
                "processes",
            ),
            "blue",
        ),
        Node(
            "sim_b",
            LEFT + 245,
            206,
            200,
            78,
            "Kinetics, equilibria",
            (
                "pickling, dezincification,",
                "fluxing pH",
            ),
            "blue",
        ),
        Node(
            "sim_c",
            LEFT + 470,
            206,
            190,
            78,
            "Coating model",
            (
                "thickness vs T and Si;",
                "ISO 1461 check",
            ),
            "blue",
        ),
        Node("sus", LEFT, 336, FULL, 120, "Sustainability assessment", color="purple_bg", group=True),
        Node("sus_a", LEFT + 20, 372, 200, 72, "17 GREENSCOPE", ("indicators + quality",), "purple"),
        Node("sus_b", LEFT + 245, 372, 200, 72, "FAHP weights", ("10 experts (2019 study)",), "purple"),
        Node("sus_c", LEFT + 470, 372, 190, 72, "Additive utility", ("U_P per simulated year",), "purple"),
        Node("obj", LEFT, 494, FULL, 108, "Objectives and constraints (Monte Carlo means)", color="yellow", group=True),
        Node("obj_a", LEFT + 20, 530, 330, 62, "Minimize", ("-E[U_P], E[COM], E[V_l-poll], E[V_WT]",), "yellow"),
        Node(
            "obj_b",
            LEFT + 380,
            530,
            280,
            62,
            "Subject to",
            (
                "P(thickness < ISO 1461) <= 0.02",
                "E[peak Fe2+, pickling] <= 150 g/L",
            ),
            "yellow",
        ),
        Node(
            "ga",
            LEFT,
            640,
            FULL,
            86,
            "NSGA-II search",
            ("population 100 · SBX · polynomial mutation · 100 to 150 generations",),
            "blue",
        ),
        Node(
            "sel",
            LEFT,
            764,
            FULL,
            86,
            "Selection",
            ("full-year re-evaluation of the Pareto set · fuzzy compromise", "sensitivity to objective weights and prices"),
            "green",
        ),
        Node(
            "cmp",
            LEFT,
            888,
            FULL,
            86,
            "Baseline vs optimized design",
            ("1,000 full-year simulations each · means, 95% CI, P_sustainable",),
            "green",
        ),
    ]
    d.badges += [
        Badge(str(i + 1), 34, y, c)
        for i, (y, c) in enumerate(
            [(75, "red"), (233, "blue"), (396, "purple"), (548, "yellow"), (683, "blue"), (807, "green"), (931, "green")]
        )
    ]
    for src, dst in [("in", "sim"), ("sim", "sus"), ("sus", "obj"), ("obj", "ga"), ("ga", "sel"), ("sel", "cmp")]:
        d.edges.append(Edge(src, dst))
    loop_x = LEFT + FULL + 48
    d.edges.append(
        Edge(
            "ga", "in", "r", "r", 0.5, 0.5, via=((loop_x, 683), (loop_x, 75)), label="next\ngeneration", label_xy=(loop_x, 380)
        )
    )
    return d


def process() -> Diagram:
    """Figure 2: process flow diagram of the HDG line (units U1 to U7), its streams and decision variables."""
    d = Diagram("HDG-line-PFD", WIDTH, 900)
    unit_x, unit_w, unit_h, tag_x, tag_w, y0, pitch = 255, 205, 64, 10, 190, 164, 94
    units = [
        (
            "u1",
            "U1 · Degreasing",
            "NaOH 14 to 16 wt%",
            "blue",
            "NaOH solution, water",
            "Spent solution, grease",
            [("x1", "x₁ · T")],
        ),
        ("u2", "U2 · Rinsing 1", "water", "blue", "Water", "Rinse wastewater 1", []),
        (
            "u3",
            "U3 · Pickling",
            "HCl 16 to 18 wt%",
            "blue",
            "HCl solution, water",
            "Spent pickling acid",
            [("x2", "x₂ · HCl"), ("x3", "x₃ · time")],
        ),
        ("u4", "U4 · Rinsing 2", "water", "blue", "Water", "Rinse wastewater 2", []),
        (
            "u5",
            "U5 · Fluxing",
            "ZnCl₂/NH₄Cl 60/40, pH about 4.5",
            "purple",
            "Salts, water, HCl,\nNH₄OH (pH control)",
            "Spent flux,\nhydroxide sludge",
            [("x4", "x₄ · T"), ("x5", "x₅ · pH"), ("x6", "x₆ · salt")],
        ),
        ("u6", "U6 · Drying", "oven at about 100 °C", "purple", "", "", []),
        ("u7", "U7 · Galvanizing", "molten zinc bath", "yellow", "Zinc make-up", "Dross, ash", [("x7", "x₇ · T")]),
    ]
    d.nodes.append(
        Node(
            "steel",
            10,
            14,
            450,
            62,
            "Incoming steel lots (random inputs)",
            ("10 product families · gauge 0.3 to 32 mm · Si 0.15 to 0.25 wt%", "rust 300 to 590 g/m² · grease and oil"),
            "orange",
            text_px=12,
        )
    )
    d.nodes.append(
        Node(
            "amb",
            550,
            200,
            225,
            62,
            "Surroundings",
            ("random ambient T ~ N(22, 2²) °C", "enters every heat balance"),
            "orange",
            text_px=12,
        )
    )
    for k, (uid, title, line, color, feed, waste, blocks) in enumerate(units):
        y = y0 + pitch * k
        d.nodes.append(Node(uid, unit_x, y, unit_w, unit_h, title, (line,), color, title_px=14, text_px=12))
        if feed:
            d.nodes.append(
                Node(
                    f"{uid}_f",
                    tag_x,
                    y + 1,
                    tag_w,
                    30,
                    "",
                    tuple(feed.split("\n")),
                    "blue",
                    text_px=11 if "\n" in feed else 12,
                    stroke=2,
                )
            )
            d.edges.append(Edge(f"{uid}_f", uid, "r", "l", 0.5, 16 / unit_h, color="#6c8ebf", width=2))
        if waste:
            d.nodes.append(
                Node(
                    f"{uid}_w",
                    tag_x,
                    y + 33,
                    tag_w,
                    30,
                    "",
                    tuple(waste.split("\n")),
                    "gray",
                    text_px=11 if "\n" in waste else 12,
                    stroke=2,
                )
            )
            d.edges.append(Edge(uid, f"{uid}_w", "l", "r", 48 / unit_h, 0.5, color="#666666", width=2))
        for j, (bid, text) in enumerate(blocks):
            d.nodes.append(Node(bid, unit_x + unit_w + 4 + 68 * j, y + 34, 64, 24, text, (), "redsolid", title_px=12, stroke=1))
    for first, second in zip(units[:-1], units[1:]):
        d.edges.append(Edge(first[0], second[0], "b", "t", color="#222222", width=5))
    d.edges.append(Edge("steel", "u1", "b", "t", (unit_x + unit_w / 2 - 10) / 450, 0.5, color="#222222", width=5))
    d.nodes.append(
        Node(
            "prod",
            unit_x,
            y0 + pitch * 7 - 12,
            unit_w,
            56,
            "Galvanized steel",
            ("ISO 1461 thickness check",),
            "green",
            text_px=12,
        )
    )
    d.edges.append(Edge("u7", "prod", "b", "t", color="#222222", width=5))
    dez_y = y0 + pitch * 3
    d.nodes.append(
        Node("dez", 570, dez_y, 205, unit_h, "Dezincification bath", ("HCl 2 to 4 wt%",), "blue", title_px=14, text_px=12)
    )
    d.edges.append(
        Edge(
            "u7",
            "dez",
            "r",
            "b",
            14 / unit_h,
            (700 - 570) / 205,
            via=((700, y0 + pitch * 6 + 14),),
            dashed=True,
            color="#444444",
            width=3,
            label="2% of the pieces\nare re-processed",
            label_xy=(632, y0 + pitch * 5 + 34),
        )
    )
    d.edges.append(Edge("dez", "u4", "l", "r", 0.5, 0.5, dashed=True, color="#444444", width=3))
    d.nodes.append(Node("legend", 475, 8, 300, 188, "Legend", color="gray", group=True, title_px=13))
    d.legend += [
        LegendItem("steel", 487, 44, "Steel pieces (main flow)"),
        LegendItem("feed", 487, 70, "Feed: chemicals, water, zinc", sample_width=190),
        LegendItem("waste", 487, 102, "Output: spent solutions,\nwastewater, dross, ash", sample_width=190),
        LegendItem("loop", 487, 136, "Re-processing loop of the\npieces with 2% probability", sample_width=190),
        LegendItem("block", 487, 170, "Decision variable (operating\ncondition set by the optimizer)", "x₁", sample_width=190),
    ]
    return d


def optimization() -> Diagram:
    """Figure 3: evaluation of a candidate and the NSGA-II loop."""
    d = Diagram("HDG-optimization-loop", WIDTH, 770)
    d.nodes += [
        Node(
            "pop",
            70,
            20,
            640,
            66,
            "Population of 100 candidate operating policies",
            ("x_1 ... x_100, 7 variables each (LHS at generation 1; SBX and mutation afterwards)",),
            "blue",
        ),
        Node("ev", 70, 120, 640, 316, "Evaluation of each candidate (parallel workers)", color="purple_bg", group=True),
        Node(
            "seed",
            95,
            168,
            590,
            56,
            "Common random numbers",
            ("child seed s = 1 ... N from one base seed, identical for every candidate",),
            "purple",
        ),
        Node("y1", 95, 258, 175, 92, "Year 1", ("simulate one year", "evaluate indicators"), "purple"),
        Node("y2", 302, 258, 175, 92, "Year 2", ("simulate one year", "evaluate indicators"), "purple"),
        Node("yn", 510, 258, 175, 92, "Year N = 100", ("simulate one year", "evaluate indicators"), "purple"),
        Node(
            "mean",
            95,
            376,
            590,
            46,
            "Means over N years",
            ("F = [-U_P, COM, V_l-poll, V_WT] · g = [defect rate - 0.02, peak Fe2+ - 150]",),
            "purple",
        ),
        Node(
            "sort",
            70,
            470,
            640,
            66,
            "Constrained non-dominated sorting and crowding",
            ("feasible before infeasible · SBX (p = 0.9, eta = 15) · polynomial mutation (p = 0.1, eta = 20)",),
            "blue",
        ),
        Node(
            "stop",
            70,
            570,
            640,
            66,
            "Termination check",
            ("150 generations, or hypervolume stagnation (tolerance 1e-4, window 15) after generation 100",),
            "yellow",
        ),
        Node(
            "out",
            70,
            680,
            640,
            66,
            "Pareto set of feasible designs",
            ("checkpoint every 5 generations (X, F, G, hypervolume history)",),
            "green",
        ),
    ]
    d.edges += [
        Edge("pop", "ev"),
        Edge("seed", "y1", "b", "t", 0.1483, 0.5),
        Edge("seed", "y2", "b", "t", 0.4992, 0.5),
        Edge("seed", "yn", "b", "t", 0.8517, 0.5),
        Edge("y1", "mean", "b", "t", 0.5, 0.1483),
        Edge("y2", "mean", "b", "t", 0.5, 0.4992),
        Edge("yn", "mean", "b", "t", 0.5, 0.8517),
        Edge("ev", "sort"),
        Edge("sort", "stop"),
        Edge("stop", "out", label="stop", label_xy=(390, 658)),
        Edge(
            "stop", "pop", "r", "r", 0.5, 0.5, via=((756, 603), (756, 53)), label="continue", label_xy=(756, 330), label_rot=90
        ),
    ]
    d.badges += [
        Badge("1", 34, 53, "blue"),
        Badge("2", 34, 278, "purple"),
        Badge("3", 34, 503, "blue"),
        Badge("4", 34, 603, "yellow"),
        Badge("5", 34, 713, "green"),
    ]
    return d


def main() -> None:
    """Write the three figures as `.drawio` and `.png` under `manuscript/figures/`."""
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for stem, build in (("fig1_framework", framework), ("fig2_hdg_line", process), ("fig3_optimization_loop", optimization)):
        diagram = build()
        to_drawio(diagram, OUT_DIR / f"{stem}.drawio")
        to_png(diagram, OUT_DIR / f"{stem}.png")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    main()
