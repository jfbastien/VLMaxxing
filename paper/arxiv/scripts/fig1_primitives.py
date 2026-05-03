"""Shared drawing primitives for exploratory Figure 1 renderers."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt

PDF_METADATA = {"CreationDate": None, "ModDate": None}


@dataclass(frozen=True)
class Theme:
    ink: str = "#0f172a"
    muted: str = "#475569"
    faint: str = "#e2e8f0"
    faint2: str = "#f8fafc"
    panel: str = "#ffffff"
    cache: str = "#16a34a"
    cache_soft: str = "#dcfce7"
    fresh: str = "#f97316"
    fresh_soft: str = "#ffedd5"
    waste: str = "#dc2626"
    waste_soft: str = "#fee2e2"
    question: str = "#2563eb"
    question_soft: str = "#dbeafe"
    guard: str = "#7c3aed"
    guard_soft: str = "#ede9fe"
    gray: str = "#94a3b8"


THEME = Theme()

FIGURE_SANS_STACK = [
    "Helvetica Neue",
    "Helvetica",
    "Arial",
    "Liberation Sans",
    "Nimbus Sans",
]


def setup_figure_style(hashsalt: str = "codec-through-fig1-v2") -> None:
    """Use a Helvetica-compatible paper-figure font stack.

    Prefer system Helvetica/Arial-style faces over Matplotlib's bundled default
    while preserving editable SVG text and embedded TrueType PDF text.
    """

    plt.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": FIGURE_SANS_STACK,
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "svg.fonttype": "none",
            "svg.hashsalt": hashsalt,
        }
    )


def new_canvas(
    figsize: tuple[float, float] = (7.45, 4.15),
    *,
    hashsalt: str = "codec-through-fig1-v2",
) -> tuple[plt.Figure, plt.Axes]:
    setup_figure_style(hashsalt)
    fig, ax = plt.subplots(figsize=figsize)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    return fig, ax


def save_figure(
    fig: plt.Figure,
    out_dir: Path,
    stem: str,
    *,
    dpi: int = 240,
    also_png: bool = True,
) -> list[str]:
    out_dir.mkdir(parents=True, exist_ok=True)
    paths: list[str] = []
    svg = out_dir / f"{stem}.svg"
    pdf = out_dir / f"{stem}.pdf"
    fig.savefig(svg, bbox_inches="tight", pad_inches=0.02)
    fig.savefig(pdf, bbox_inches="tight", pad_inches=0.02, metadata=PDF_METADATA)
    paths.extend([str(svg), str(pdf)])
    if also_png:
        png = out_dir / f"{stem}.png"
        fig.savefig(png, dpi=dpi, bbox_inches="tight", pad_inches=0.02)
        paths.append(str(png))
    plt.close(fig)
    return paths


def label(
    ax: plt.Axes,
    x: float,
    y: float,
    text: str,
    *,
    fs: float = 8.0,
    color: str = THEME.ink,
    weight: str = "normal",
    ha: str = "left",
    va: str = "center",
    linespacing: float = 1.05,
    z: int = 20,
    **kwargs: Any,
) -> None:
    ax.text(
        x,
        y,
        text,
        fontsize=fs,
        color=color,
        weight=weight,
        ha=ha,
        va=va,
        linespacing=linespacing,
        zorder=z,
        **kwargs,
    )


def rounded_panel(
    ax: plt.Axes,
    x: float,
    y: float,
    w: float,
    h: float,
    *,
    face: str = THEME.panel,
    edge: str = THEME.faint,
    lw: float = 0.8,
    radius: float = 0.010,
    z: int = 1,
) -> mpatches.FancyBboxPatch:
    patch = mpatches.FancyBboxPatch(
        (x, y),
        w,
        h,
        boxstyle=mpatches.BoxStyle("Round", pad=0.004, rounding_size=radius),
        facecolor=face,
        edgecolor=edge,
        linewidth=lw,
        zorder=z,
    )
    ax.add_patch(patch)
    return patch


def arrow(
    ax: plt.Axes,
    x0: float,
    y0: float,
    x1: float,
    y1: float,
    *,
    color: str = "#64748b",
    lw: float = 1.0,
    alpha: float = 1.0,
) -> None:
    ax.annotate(
        "",
        xy=(x1, y1),
        xytext=(x0, y0),
        arrowprops=dict(
            arrowstyle="-|>",
            color=color,
            lw=lw,
            alpha=alpha,
            shrinkA=0,
            shrinkB=0,
        ),
        zorder=10,
    )


def pill(
    ax: plt.Axes,
    x: float,
    y: float,
    w: float,
    h: float,
    text: str,
    *,
    face: str,
    edge: str,
    color: str | None = None,
    fs: float = 6.4,
    weight: str = "bold",
) -> None:
    rounded_panel(ax, x, y, w, h, face=face, edge=edge, lw=0.75, radius=h / 2)
    label(ax, x + w / 2, y + h / 2, text, fs=fs, color=color or edge, weight=weight, ha="center")


def draw_raster_frame(
    ax: plt.Axes,
    image: Any,
    x: float,
    y: float,
    w: float,
    h: float,
    *,
    border: bool = True,
    alpha: float = 1.0,
    z: int = 2,
) -> None:
    ax.imshow(image, extent=(x, x + w, y, y + h), aspect="auto", alpha=alpha, zorder=z)
    if border:
        ax.add_patch(
            mpatches.Rectangle(
                (x, y),
                w,
                h,
                facecolor="none",
                edgecolor=THEME.ink,
                lw=0.55,
                zorder=z + 1,
            )
        )


def draw_highlight_regions(
    ax: plt.Axes,
    x: float,
    y: float,
    w: float,
    h: float,
    boxes: Sequence[tuple[float, float, float, float]],
    *,
    fill: str = THEME.fresh,
    edge: str = "#c2410c",
    alpha: float = 0.16,
    lw: float = 0.85,
    z: int = 8,
) -> None:
    """Draw normalized boxes where coordinates are x0,y0,x1,y1 with y down."""

    for bx0, by0, bx1, by1 in boxes:
        rx = x + bx0 * w
        ry = y + (1.0 - by1) * h
        rw = (bx1 - bx0) * w
        rh = (by1 - by0) * h
        ax.add_patch(
            mpatches.Rectangle(
                (rx, ry),
                rw,
                rh,
                facecolor=fill,
                edgecolor=edge,
                alpha=alpha,
                lw=lw,
                zorder=z,
            )
        )


def brick_row(
    ax: plt.Axes,
    x: float,
    y: float,
    *,
    n: int,
    filled: int,
    w: float,
    h: float,
    gap: float = 0.0035,
    fill_color: str = THEME.cache,
    empty_color: str = "#ffffff",
    edge: str = "#94a3b8",
    fresh_tail: int = 0,
) -> None:
    if n <= 0:
        return
    brick_w = (w - gap * (n - 1)) / n
    for idx in range(n):
        xx = x + idx * (brick_w + gap)
        if idx < filled:
            face = fill_color
            ec = fill_color
        else:
            face = empty_color
            ec = edge
        if fresh_tail and filled - fresh_tail <= idx < filled:
            face = THEME.fresh
            ec = THEME.fresh
        ax.add_patch(
            mpatches.Rectangle(
                (xx, y),
                brick_w,
                h,
                facecolor=face,
                edgecolor=ec,
                lw=0.45,
                zorder=4,
            )
        )


def reuse_bar(
    ax: plt.Axes,
    x: float,
    y: float,
    w: float,
    h: float,
    reuse: float,
    *,
    edge: str = THEME.faint,
) -> None:
    reuse = max(0.0, min(1.0, reuse))
    ax.add_patch(
        mpatches.Rectangle((x, y), w * reuse, h, facecolor=THEME.cache, edgecolor="none", zorder=5)
    )
    ax.add_patch(
        mpatches.Rectangle(
            (x + w * reuse, y),
            w * (1.0 - reuse),
            h,
            facecolor=THEME.fresh,
            edgecolor="none",
            zorder=5,
        )
    )
    ax.add_patch(
        mpatches.Rectangle((x, y), w, h, facecolor="none", edgecolor=edge, lw=0.35, zorder=6)
    )


def runtime_bar(
    ax: plt.Axes,
    x: float,
    y: float,
    w: float,
    h: float,
    segments: Sequence[tuple[str, float, str]],
    *,
    fs: float = 4.8,
) -> None:
    cursor = x
    for name, frac, color in segments:
        seg_w = w * frac
        ax.add_patch(
            mpatches.Rectangle(
                (cursor, y),
                seg_w,
                h,
                facecolor=color,
                edgecolor="white",
                lw=0.4,
                zorder=3,
            )
        )
        if seg_w > 0.055:
            label(
                ax,
                cursor + seg_w / 2,
                y + h / 2,
                name,
                fs=fs,
                color="white",
                weight="bold",
                ha="center",
                va="center",
            )
        cursor += seg_w
    ax.add_patch(
        mpatches.Rectangle((x, y), w, h, facecolor="none", edgecolor=THEME.ink, lw=0.45, zorder=4)
    )
