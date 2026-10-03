"""Tiny diagram engine: one specification renders to an editable draw.io file and to a PNG.

Purpose: keep the manuscript flow figures and their draw.io sources identical (same boxes, text and routing).
Author: Jose D. Hernandez-Betancur
Date: 2026-10-03
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Final
from xml.sax.saxutils import escape

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch  # noqa: E402

logger = logging.getLogger(__name__)

PALETTE: Final = {
    "red": ("#f8cecc", "#b85450"),
    "blue": ("#dae8fc", "#6c8ebf"),
    "blue_bg": ("#eef3ff", "#6c8ebf"),
    "purple": ("#e1d5e7", "#9673a6"),
    "purple_bg": ("#f5eefa", "#9673a6"),
    "yellow": ("#fff2cc", "#d6b656"),
    "green": ("#d5e8d4", "#82b366"),
    "orange": ("#ffe6cc", "#d79b00"),
    "gray": ("#f5f5f5", "#666666"),
    "redsolid": ("#b85450", "#b85450"),
}
TEXT_COLORS: Final = {"purple": "#4a2c7a", "purple_bg": "#4a2c7a", "blue_bg": "#1f3a8a", "redsolid": "#ffffff"}
PX_TO_INCH: Final = 0.01
PX_TO_PT: Final = 0.72
SIDES: Final = {"t": (0.5, 0.0), "b": (0.5, 1.0), "l": (0.0, 0.5), "r": (1.0, 0.5)}


@dataclass
class Node:
    """A box. `group=True` draws a container whose title sits at its top-left corner."""

    id: str
    x: float
    y: float
    w: float
    h: float
    title: str = ""
    lines: tuple[str, ...] = ()
    color: str = "blue"
    group: bool = False
    title_px: int = 15
    text_px: int = 13
    stroke: int = 3
    shape: str = "box"


@dataclass
class Edge:
    """An arrow between two nodes; `via` are absolute waypoints; anchors are side + fraction along the side."""

    src: str
    dst: str
    src_side: str = "b"
    dst_side: str = "t"
    src_frac: float = 0.5
    dst_frac: float = 0.5
    via: tuple[tuple[float, float], ...] = ()
    label: str = ""
    label_xy: tuple[float, float] | None = None
    label_rot: float = 0
    dashed: bool = False
    color: str = "#444444"
    width: int = 3


@dataclass
class Badge:
    """A numbered circle."""

    text: str
    x: float
    y: float
    color: str = "red"
    r: float = 17

    @property
    def width(self) -> float:
        """Badge width: a circle for one character, a pill for longer labels."""
        return 2 * self.r if len(self.text) == 1 else 11.0 * len(self.text) + 22.0


@dataclass
class LegendItem:
    """One legend row: a sample of a line style or of a block, followed by its meaning.

    `kind` is one of: steel, feed, waste, loop (arrows) or block (a red decision-variable block).
    """

    kind: str
    x: float
    y: float
    text: str
    sample: str = ""
    sample_width: float = 220


LEGEND_STYLES: Final = {
    "steel": ("#222222", 5, False),
    "feed": ("#6c8ebf", 2, False),
    "waste": ("#666666", 2, False),
    "loop": ("#444444", 3, True),
}
SAMPLE_LENGTH: Final = 46


@dataclass
class Diagram:
    """A complete figure."""

    name: str
    width: int
    height: int
    nodes: list[Node] = field(default_factory=list)
    edges: list[Edge] = field(default_factory=list)
    badges: list[Badge] = field(default_factory=list)
    legend: list[LegendItem] = field(default_factory=list)

    def node(self, node_id: str) -> Node:
        """Look a node up by id.

        Args:
            node_id: Identifier of the node.

        Returns:
            The node.
        """
        return next(item for item in self.nodes if item.id == node_id)


def anchor(node: Node, side: str, frac: float) -> tuple[float, float]:
    """Absolute point on a side of a node.

    Args:
        node: The node.
        side: One of t, b, l, r.
        frac: Position along the side, 0 to 1.

    Returns:
        (x, y) in diagram pixels.
    """
    if side in ("t", "b"):
        return node.x + node.w * frac, node.y + (node.h if side == "b" else 0.0)
    return node.x + (node.w if side == "r" else 0.0), node.y + node.h * frac


def _value_html(node: Node) -> str:
    parts = []
    if node.title:
        parts.append(f"<b>{escape(node.title)}</b>")
    parts.extend(escape(line) for line in node.lines)
    return "<br>".join(parts)


def _node_xml(node: Node) -> str:
    fill, stroke = PALETTE[node.color]
    rounded = "rounded=1;arcSize=8;" if node.shape == "box" else "rounded=1;arcSize=50;"
    align = "align=left;verticalAlign=top;spacingLeft=14;spacingTop=6;" if node.group else "align=center;verticalAlign=middle;"
    style = f"{rounded}whiteSpace=wrap;html=1;fillColor={fill};strokeColor={stroke};strokeWidth={node.stroke};fontSize={node.text_px};fontColor={TEXT_COLORS.get(node.color, "#000000")};{align}"
    value = escape(_value_html(node), {'"': "&quot;"})
    return (
        f'        <mxCell id="{node.id}" parent="1" style="{style}" value="{value}" vertex="1">\n'
        f'          <mxGeometry x="{node.x:g}" y="{node.y:g}" width="{node.w:g}" height="{node.h:g}" as="geometry" />\n'
        "        </mxCell>\n"
    )


def _edge_xml(index: int, edge: Edge, diagram: Diagram) -> str:
    sx, sy = SIDES[edge.src_side]
    tx, ty = SIDES[edge.dst_side]
    sx, sy = (edge.src_frac, sy) if edge.src_side in ("t", "b") else (sx, edge.src_frac)
    tx, ty = (edge.dst_frac, ty) if edge.dst_side in ("t", "b") else (tx, edge.dst_frac)
    dash = "dashed=1;" if edge.dashed else ""
    style = (
        f"rounded=0;html=1;{dash}strokeWidth={edge.width};strokeColor={edge.color};"
        f"exitX={sx:g};exitY={sy:g};entryX={tx:g};entryY={ty:g};endArrow=block;endFill=1;"
    )
    points = "".join(f'<mxPoint x="{x:g}" y="{y:g}" />' for x, y in edge.via)
    geometry = f'<Array as="points">{points}</Array>' if points else ""
    return (
        f'        <mxCell id="e{index}" edge="1" parent="1" source="{edge.src}" target="{edge.dst}" style="{style}" '
        f'value="{escape(edge.label.replace(chr(10), "<br>"))}">\n'
        f'          <mxGeometry relative="1" as="geometry">{geometry}</mxGeometry>\n'
        "        </mxCell>\n"
    )


def _badge_xml(index: int, badge: Badge) -> str:
    fill, _ = PALETTE[badge.color]
    stroke = PALETTE[badge.color][1]
    shape = "ellipse" if len(badge.text) == 1 else "rounded=1;arcSize=50"
    style = f"{shape};whiteSpace=wrap;html=1;fillColor={stroke};strokeColor=none;fontColor=#ffffff;fontStyle=1;fontSize=16;"
    return (
        f'        <mxCell id="b{index}" parent="1" style="{style}" value="{escape(badge.text)}" vertex="1">\n'
        f'          <mxGeometry x="{badge.x - badge.width / 2:g}" y="{badge.y - badge.r:g}" width="{badge.width:g}" height="{2 * badge.r:g}" as="geometry" />\n'
        "        </mxCell>\n"
    )


def _legend_xml(index: int, item: LegendItem) -> str:
    text = (
        f'        <mxCell id="lt{index}" parent="1" style="text;html=1;align=left;verticalAlign=middle;whiteSpace=wrap;fontSize=12;" '
        f'value="{escape(item.text.replace(chr(10), "<br>"))}" vertex="1">\n'
        f'          <mxGeometry x="{item.x + SAMPLE_LENGTH + 12:g}" y="{item.y - 16:g}" width="{item.sample_width:g}" height="32" as="geometry" />\n'
        "        </mxCell>\n"
    )
    if item.kind == "block":
        fill, stroke = PALETTE["red"]
        style = f"rounded=1;arcSize=20;whiteSpace=wrap;html=1;fillColor={stroke};strokeColor=none;fontColor=#ffffff;fontStyle=1;fontSize=11;"
        sample = (
            f'        <mxCell id="ls{index}" parent="1" style="{style}" value="{escape(item.sample)}" vertex="1">\n'
            f'          <mxGeometry x="{item.x + 5:g}" y="{item.y - 10:g}" width="36" height="20" as="geometry" />\n'
            "        </mxCell>\n"
        )
        return sample + text
    color, width, dashed = LEGEND_STYLES[item.kind]
    style = f"rounded=0;html=1;{'dashed=1;' if dashed else ''}strokeWidth={width};strokeColor={color};endArrow=block;endFill=1;"
    sample = (
        f'        <mxCell id="ls{index}" edge="1" parent="1" style="{style}" value="">\n'
        '          <mxGeometry relative="1" as="geometry">'
        f'<mxPoint x="{item.x:g}" y="{item.y:g}" as="sourcePoint" />'
        f'<mxPoint x="{item.x + SAMPLE_LENGTH:g}" y="{item.y:g}" as="targetPoint" /></mxGeometry>\n'
        "        </mxCell>\n"
    )
    return sample + text


def to_drawio(diagram: Diagram, path: Path) -> None:
    """Write the diagram as an editable draw.io (mxGraph) file.

    Args:
        diagram: The figure specification.
        path: Destination `.drawio` file.
    """
    body = "".join(_node_xml(node) for node in diagram.nodes)
    body += "".join(_badge_xml(i, badge) for i, badge in enumerate(diagram.badges))
    body += "".join(_edge_xml(i, edge, diagram) for i, edge in enumerate(diagram.edges))
    body += "".join(_legend_xml(i, item) for i, item in enumerate(diagram.legend))
    xml = (
        '<mxfile host="app.diagrams.net">\n'
        f'  <diagram name="{escape(diagram.name)}" id="{escape(diagram.name)}">\n'
        f'    <mxGraphModel grid="1" page="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" '
        f'pageScale="1" pageWidth="{diagram.width}" pageHeight="{diagram.height}" math="0" shadow="0">\n'
        '      <root>\n        <mxCell id="0" />\n        <mxCell id="1" parent="0" />\n'
        f"{body}      </root>\n    </mxGraphModel>\n  </diagram>\n</mxfile>\n"
    )
    path.write_text(xml, encoding="utf-8")
    logger.info("Wrote %s", path)


def _draw_node(ax: plt.Axes, node: Node) -> None:
    fill, stroke = PALETTE[node.color]
    arc = 8 if node.shape == "box" else min(node.h, node.w) / 2
    patch = FancyBboxPatch(
        (node.x + 1, node.y + 1),
        node.w - 2,
        node.h - 2,
        boxstyle=f"round,pad=0,rounding_size={arc}",
        facecolor=fill,
        edgecolor=stroke,
        linewidth=node.stroke * PX_TO_PT * 1.4,
        zorder=2 if node.group else 3,
    )
    ax.add_patch(patch)
    color = TEXT_COLORS.get(node.color, "#000000")
    if node.group:
        ax.text(
            node.x + 14,
            node.y + 8,
            node.title,
            fontsize=node.title_px * PX_TO_PT,
            fontweight="bold",
            va="top",
            ha="left",
            color=color,
            zorder=5,
        )
        for k, line in enumerate(node.lines):
            ax.text(
                node.x + 14,
                node.y + 8 + (node.title_px + 6) * (k + 1),
                line,
                fontsize=node.text_px * PX_TO_PT,
                va="top",
                ha="left",
                color=color,
                zorder=5,
            )
        return
    _draw_centered(ax, node, color)


def _draw_centered(ax: plt.Axes, node: Node, color: str) -> None:
    heights = ([node.title_px] if node.title else []) + [node.text_px] * len(node.lines)
    gap = 4
    total = sum(heights) + gap * (len(heights) - 1)
    y = node.y + (node.h - total) / 2
    entries = ([("title", node.title)] if node.title else []) + [("line", line) for line in node.lines]
    for (kind, text), height in zip(entries, heights):
        ax.text(
            node.x + node.w / 2,
            y + height / 2,
            text,
            fontsize=height * PX_TO_PT,
            fontweight="bold" if kind == "title" else "normal",
            ha="center",
            va="center",
            color=color,
            zorder=5,
        )
        y += height + gap


def _draw_edge(ax: plt.Axes, edge: Edge, diagram: Diagram) -> None:
    start = anchor(diagram.node(edge.src), edge.src_side, edge.src_frac)
    end = anchor(diagram.node(edge.dst), edge.dst_side, edge.dst_frac)
    points = [start, *edge.via, end]
    style = (0, (4, 3)) if edge.dashed else "-"
    for first, second in zip(points[:-2], points[1:-1]):
        ax.plot(
            [first[0], second[0]],
            [first[1], second[1]],
            color=edge.color,
            lw=edge.width * PX_TO_PT * 1.1,
            ls=style,
            zorder=6,
            solid_capstyle="butt",
        )
    ax.add_patch(
        FancyArrowPatch(
            points[-2],
            points[-1],
            arrowstyle="-|>",
            mutation_scale=9 + 2.4 * edge.width,
            color=edge.color,
            lw=edge.width * PX_TO_PT * 1.1,
            linestyle=style,
            shrinkA=0,
            shrinkB=0,
            zorder=6,
        )
    )
    if edge.label:
        lx, ly = edge.label_xy or ((start[0] + end[0]) / 2, (start[1] + end[1]) / 2)
        ax.text(
            lx,
            ly,
            edge.label,
            fontsize=12 * PX_TO_PT,
            ha="center",
            va="center",
            zorder=7,
            color="#333333",
            rotation=edge.label_rot,
            bbox={"facecolor": "white", "edgecolor": "none", "pad": 1.5},
        )


def _draw_legend(ax: plt.Axes, item: LegendItem) -> None:
    if item.kind == "block":
        _, stroke = PALETTE["red"]
        ax.add_patch(
            FancyBboxPatch(
                (item.x + 5, item.y - 10),
                36,
                20,
                boxstyle="round,pad=0,rounding_size=4",
                facecolor=stroke,
                edgecolor="none",
                zorder=8,
            )
        )
        ax.text(
            item.x + 23,
            item.y,
            item.sample,
            color="white",
            fontsize=11 * PX_TO_PT,
            fontweight="bold",
            ha="center",
            va="center",
            zorder=9,
        )
    else:
        color, width, dashed = LEGEND_STYLES[item.kind]
        style = (0, (4, 3)) if dashed else "-"
        ax.plot(
            [item.x, item.x + SAMPLE_LENGTH - 8],
            [item.y, item.y],
            color=color,
            lw=width * PX_TO_PT * 1.1,
            ls=style,
            zorder=8,
            solid_capstyle="butt",
        )
        ax.add_patch(
            FancyArrowPatch(
                (item.x + SAMPLE_LENGTH - 10, item.y),
                (item.x + SAMPLE_LENGTH, item.y),
                arrowstyle="-|>",
                mutation_scale=9 + 2.4 * width,
                color=color,
                lw=width * PX_TO_PT * 1.1,
                shrinkA=0,
                shrinkB=0,
                zorder=8,
            )
        )
    ax.text(
        item.x + SAMPLE_LENGTH + 12,
        item.y,
        item.text,
        fontsize=12 * PX_TO_PT,
        ha="left",
        va="center",
        zorder=8,
        color="#222222",
    )


def to_png(diagram: Diagram, path: Path, dpi: int = 300) -> None:
    """Render the diagram to a PNG with the same geometry as the draw.io file.

    Args:
        diagram: The figure specification.
        path: Destination `.png` file.
        dpi: Raster resolution.
    """
    figure, ax = plt.subplots(figsize=(diagram.width * PX_TO_INCH, diagram.height * PX_TO_INCH))
    figure.subplots_adjust(0, 0, 1, 1)
    ax.set_xlim(0, diagram.width)
    ax.set_ylim(diagram.height, 0)
    ax.axis("off")
    for node in sorted(diagram.nodes, key=lambda item: not item.group):
        _draw_node(ax, node)
    for edge in diagram.edges:
        _draw_edge(ax, edge, diagram)
    for item in diagram.legend:
        _draw_legend(ax, item)
    for badge in diagram.badges:
        _, stroke = PALETTE[badge.color]
        ax.add_patch(
            FancyBboxPatch(
                (badge.x - badge.width / 2, badge.y - badge.r),
                badge.width,
                2 * badge.r,
                boxstyle=f"round,pad=0,rounding_size={badge.r}",
                facecolor=stroke,
                edgecolor="none",
                zorder=8,
            )
        )
        ax.text(
            badge.x,
            badge.y,
            badge.text,
            color="white",
            fontsize=16 * PX_TO_PT,
            fontweight="bold",
            ha="center",
            va="center",
            zorder=9,
        )
    figure.savefig(path, dpi=dpi, facecolor="white")
    plt.close(figure)
    logger.info("Wrote %s", path)
