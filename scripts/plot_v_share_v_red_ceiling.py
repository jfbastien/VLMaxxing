"""V_share × V_red → predicted-E2E surface plot.

Validates the C-VISION scatter-back ceiling
``E2E ≤ 1 / (1 − V_share × V_red)`` visually. Plots observed E2E for all
landed (V_share, V_red) regime cells against the ceiling curve.

Emits:

- ``paper/figures/v_share_v_red_ceiling.{pdf,svg,png}`` — scatter of observed
  regimes overlaid on the ceiling surface. Colour encodes error
  (observed − predicted, pp).
- ``paper/figures/v_share_v_red_ceiling_data.json`` — per-cell numbers.

Numbers are transcribed from claim-matrix.md §"V_share Governs 1.51V
Gains" and the three holdout V-only findings docs (session 3 VideoMME,
session 4 MVBench, session 5 TOMATO). Predictions are derived from the
ceiling formula with the observed V_share and V_red; these are the same
pre-registered predictions that appear in each prereg.

Run:
    uv run python scripts/plot_v_share_v_red_ceiling.py
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent
FIGURES = REPO_ROOT / "paper" / "figures"
PDF_METADATA = {"CreationDate": None, "ModDate": None}
FIGURE_SANS_STACK = [
    "Arial",
    "Helvetica Neue",
    "Helvetica",
    "Liberation Sans",
    "Nimbus Sans",
]


@dataclass(frozen=True)
class CeilingCell:
    label: str
    split: str  # "dev", "holdout", "cross-arch", or "composition"
    v_share: float
    v_red: float
    predicted_e2e: float
    observed_e2e: float

    @property
    def product(self) -> float:
        return self.v_share * self.v_red

    @property
    def error_pp(self) -> float:
        return (self.observed_e2e - self.predicted_e2e) * 100.0


SOURCE_PATHS: dict[str, list[str]] = {
    "VideoMME 8f dev": [
        "research/experiments/2026/2026-04-21-phase-1_51V-expansion-findings.md",
        "research/experiments/2026/artifacts/phase1_51V_expansion/exp01_videomme_8f_unpatched_summary.json",
        "research/experiments/2026/artifacts/phase1_51V_expansion/exp02_videomme_8f_L2_kr050_summary.json",
    ],
    "VideoMME 16f dev": [
        "research/experiments/2026/2026-04-21-phase-1_51V-expansion-findings.md",
        "research/experiments/2026/artifacts/phase1_51V_expansion/exp11_videomme_16f_unpatched_summary.json",
        "research/experiments/2026/artifacts/phase1_51V_expansion/exp12_videomme_16f_L2_kr050_summary.json",
    ],
    "MVBench 8f dev": [
        "research/experiments/2026/2026-04-21-phase-1_51V-expansion-findings.md",
        "research/experiments/2026/artifacts/phase1_51V_expansion/exp05_mvbench_8f_unpatched_summary.json",
        "research/experiments/2026/artifacts/phase1_51V_expansion/exp06_mvbench_8f_L2_kr050_summary.json",
    ],
    "TOMATO 8f dev": [
        "research/experiments/2026/2026-04-21-phase-1_51V-expansion-findings.md",
        "research/experiments/2026/artifacts/phase1_51V_expansion/exp07_tomato_8f_unpatched_summary.json",
        "research/experiments/2026/artifacts/phase1_51V_expansion/exp08_tomato_8f_L2_kr050_summary.json",
    ],
    "VideoMME 8f holdout": [
        "research/experiments/2026/2026-04-21-phase-1_51V-session3-findings.md",
        "research/experiments/2026/artifacts/phase1_51V_session3/exp17_videomme_holdout_8f_unpatched_summary.json",
        "research/experiments/2026/artifacts/phase1_51V_session3/exp18_videomme_holdout_8f_L2_kr050_summary.json",
    ],
    "MVBench 8f holdout": [
        "research/experiments/2026/2026-04-21-phase-1_51V-session4-findings.md",
        "research/experiments/2026/artifacts/phase1_51V_session4/exp19_mvbench_holdout_8f_unpatched_summary.json",
        "research/experiments/2026/artifacts/phase1_51V_session4/exp20_mvbench_holdout_8f_L2_kr050_summary.json",
    ],
    "TOMATO 8f holdout": [
        "research/experiments/2026/2026-04-21-phase-1_51V-session5-findings.md",
        "research/experiments/2026/artifacts/phase1_51V_session5/exp23_tomato_holdout_8f_unpatched_summary.json",
        "research/experiments/2026/artifacts/phase1_51V_session5/exp24_tomato_holdout_8f_L2_kr050_summary.json",
    ],
    "Qwen VideoMME 8f dev": [
        "research/experiments/2026/2026-04-23-phase-1_51V-qwen-cross-arch-findings.md",
        "research/experiments/2026/artifacts/phase1_51V_qwen_cross_arch/videomme_dev30_8f_unpatched_summary.json",
        "research/experiments/2026/artifacts/phase1_51V_qwen_cross_arch/videomme_dev30_8f_L2_kr050_summary.json",
        "research/experiments/2026/artifacts/phase1_51V_qwen_cross_arch/pair_analysis.txt",
    ],
    "Qwen sparse vision 8f kr=0.25": [
        "research/experiments/2026/artifacts/phase1_63J_qwen_8f_kr_sweep/kr_sweep_summary.json",
        "research/experiments/2026/artifacts/phase1_63J_qwen_8f_kr_sweep/pair_summary_kr025_8f.json",
    ],
    "Qwen sparse vision 8f kr=0.50": [
        "research/experiments/2026/2026-04-27-phase-1_63E-8f-findings.md",
        "research/experiments/2026/artifacts/phase1_63E_track_b_frame_scaling/pair_summary_8f.json",
        "research/experiments/2026/artifacts/phase1_63J_qwen_8f_kr_sweep/kr_sweep_summary.json",
    ],
    "Qwen sparse vision 8f kr=0.75": [
        "research/experiments/2026/artifacts/phase1_63J_qwen_8f_kr_sweep/kr_sweep_summary.json",
        "research/experiments/2026/artifacts/phase1_63J_qwen_8f_kr_sweep/pair_summary_kr075_8f.json",
    ],
    "Gemma sparse vision 8f n=60": [
        "research/experiments/2026/2026-04-27-phase-1_63G-gemma-track-b-prereg.md",
        "research/experiments/2026/2026-04-29-phase-1_63G-format-diagnostic-findings.md",
        "research/experiments/2026/artifacts/phase1_63G_gemma_track_b/pair_summary_8f.json",
    ],
    "Gemma sparse vision 16f n=60": [
        "research/experiments/2026/2026-04-27-phase-1_63G-gemma-track-b-prereg.md",
        "research/experiments/2026/2026-04-29-phase-1_63G-format-diagnostic-findings.md",
        "research/experiments/2026/artifacts/phase1_63G_gemma_track_b/pair_summary_16f.json",
    ],
    "Gemma sparse vision 32f n=60": [
        "research/experiments/2026/2026-04-27-phase-1_63G-gemma-track-b-prereg.md",
        "research/experiments/2026/2026-04-29-phase-1_63G-format-diagnostic-findings.md",
        "research/experiments/2026/artifacts/phase1_63G_gemma_track_b/pair_summary_32f.json",
    ],
    "Gemma sparse vision 32f short": [
        "research/experiments/2026/2026-04-27-phase-1_63G-gemma-track-b-prereg.md",
        "research/experiments/2026/2026-04-29-phase-1_63G-format-diagnostic-findings.md",
        "research/experiments/2026/artifacts/phase1_63G_gemma_track_b/pair_summary_32f.json",
    ],
    "Qwen sparse vision 16f kr=0.85": [
        "research/experiments/2026/2026-04-29-phase-1_63H-16f-kr-sweep-findings.md",
        "research/experiments/2026/artifacts/phase1_63H_16f_kr_sweep/pair_summary_kr085_16f.json",
    ],
    "VideoMME n=60 composition audit": [
        "research/experiments/2026/2026-04-21-phase-1_51V-exp10-n60-findings.md",
        "research/experiments/2026/artifacts/phase1_51V_exp10_n60/exp10n60_a_vonly_ref_summary.json",
        "research/experiments/2026/artifacts/phase1_51V_exp10_n60/exp10n60_b_vplus_novelty030_summary.json",
    ],
}


def _cell_dict(cell: CeilingCell) -> dict[str, object]:
    data = asdict(cell)
    data["source_paths"] = SOURCE_PATHS[cell.label]
    return data


def ceiling(product: float) -> float:
    return 1.0 / (1.0 - product)


# Dev-tranche cells (claim-matrix.md §V_share Governs 1.51V Gains).
DEV_CELLS = [
    CeilingCell("VideoMME 8f dev", "dev", 0.152, 0.390, 1.062, 1.08),
    CeilingCell("VideoMME 16f dev", "dev", 0.243, 0.390, 1.105, 1.12),
    CeilingCell("MVBench 8f dev", "dev", 0.478, 0.400, 1.237, 1.21),
    CeilingCell("TOMATO 8f dev", "dev", 0.407, 0.427, 1.214, 1.24),
]

# Holdout V-only cells (session 3 / 4 / 5).
HOLDOUT_CELLS = [
    CeilingCell("VideoMME 8f holdout", "holdout", 0.1545, 0.413, ceiling(0.1545 * 0.413), 1.113),
    CeilingCell("MVBench 8f holdout", "holdout", 0.4521, 0.471, ceiling(0.4521 * 0.471), 1.407),
    CeilingCell("TOMATO 8f holdout", "holdout", 0.3839, 0.350, ceiling(0.3839 * 0.350), 1.194),
]

# Cross-architecture C-VISION transfer point (Qwen 2.5-VL-7B, VideoMME 8f).
CROSS_ARCH_CELLS = [
    CeilingCell("Qwen VideoMME 8f dev", "cross-arch", 0.103, 0.398, 1.043, 1.044),
]

# Measured sparse-execution points: timed vision-tower work is actually skipped.
SPARSE_CELLS = [
    CeilingCell("Qwen sparse vision 8f kr=0.25", "measured sparse", 0.099846, 0.648, 1.069, 1.069),
    CeilingCell("Qwen sparse vision 8f kr=0.50", "measured sparse", 0.099846, 0.448, 1.047, 1.042),
    CeilingCell("Qwen sparse vision 8f kr=0.75", "measured sparse", 0.099846, 0.172, 1.018, 0.998),
    CeilingCell("Gemma sparse vision 8f n=60", "measured sparse", 0.0785, 0.482, 1.039, 1.102),
    CeilingCell("Gemma sparse vision 16f n=60", "measured sparse", 0.1556, 0.406, 1.067, 1.035),
    CeilingCell("Gemma sparse vision 32f n=60", "measured sparse", 0.2420, 0.433, 1.117, 1.126),
    CeilingCell("Gemma sparse vision 32f short", "measured sparse", 0.5856, 0.422, 1.328, 1.316),
    CeilingCell("Qwen sparse vision 16f kr=0.85", "measured sparse", 0.1490, 0.136, 1.021, 1.032),
]

# Composition-audit cell (EXP10 n=60 CLOSED-NULL).
COMPOSITION_CELLS = [
    # Arm B V+novelty on VideoMME n=60: V_share collapsed to 0.0626,
    # V_red (vision-side only) 0.43 at kr_V=0.50. Observed E2E 1.042×.
    CeilingCell(
        "VideoMME n=60 composition audit",
        "composition",
        0.0626,
        0.430,
        ceiling(0.0626 * 0.430),
        1.042,
    ),
]


def plot() -> None:
    plt.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": FIGURE_SANS_STACK,
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "savefig.facecolor": "white",
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "svg.fonttype": "none",
        }
    )

    all_cells = DEV_CELLS + HOLDOUT_CELLS + CROSS_ARCH_CELLS + SPARSE_CELLS + COMPOSITION_CELLS

    fig, ax = plt.subplots(figsize=(9.5, 6.2))

    # Ceiling surface parameterised by V_share×V_red product.
    xs = np.linspace(0.0, 0.30, 300)
    ys = 1.0 / (1.0 - xs)
    ax.plot(xs, ys, color="black", linewidth=1.4, label="ceiling: 1 / (1 − V_share × V_red)")

    def _scatter(cells: list[CeilingCell], marker: str, color: str, label: str) -> None:
        ax.scatter(
            [c.product for c in cells],
            [c.observed_e2e for c in cells],
            marker=marker,
            s=110,
            facecolor=color,
            edgecolor="black",
            linewidth=0.8,
            label=label,
            zorder=3,
        )
        for c in cells:
            if c.label == "MVBench 8f holdout":
                ax.annotate(
                    "MVBench holdout\n+13.6pp, advisory\nnon-vision timing",
                    xy=(c.product, c.observed_e2e),
                    xytext=(-140, -52),
                    textcoords="offset points",
                    fontsize=8,
                    arrowprops={"arrowstyle": "->", "linewidth": 0.8, "color": "#5f370e"},
                    bbox={"boxstyle": "round,pad=0.25", "fc": "#fff7e6", "ec": "#8d6e00"},
                )
                continue
            if c.label == "Qwen sparse vision 8f kr=0.25":
                ax.annotate(
                    "Qwen keep-rate sweep\npredicts timing;\nfidelity fails",
                    xy=(c.product, c.observed_e2e),
                    xytext=(30, -28),
                    textcoords="offset points",
                    fontsize=8,
                    arrowprops={"arrowstyle": "->", "linewidth": 0.8, "color": "#5b2a86"},
                    bbox={"boxstyle": "round,pad=0.25", "fc": "#f3e8ff", "ec": "#6f42c1"},
                )
                continue
            if c.label == "Gemma sparse vision 32f short":
                ax.annotate(
                    "Gemma 32f short\nclean timed-skip cell",
                    xy=(c.product, c.observed_e2e),
                    xytext=(-116, 20),
                    textcoords="offset points",
                    fontsize=8,
                    arrowprops={"arrowstyle": "->", "linewidth": 0.8, "color": "#5b2a86"},
                    bbox={"boxstyle": "round,pad=0.25", "fc": "#f3e8ff", "ec": "#6f42c1"},
                )
                continue
            if c.split in {"measured sparse", "cross-arch", "composition"}:
                continue
            ax.annotate(
                c.label,
                xy=(c.product, c.observed_e2e),
                xytext=(5, 4),
                textcoords="offset points",
                fontsize=8,
            )

    _scatter(DEV_CELLS, "o", "tab:blue", "dev (n=30 thermally paired)")
    _scatter(HOLDOUT_CELLS, "s", "tab:orange", "holdout (V-only pairs)")
    _scatter(CROSS_ARCH_CELLS, "^", "tab:green", "Qwen cross-arch (n=30, matched point)")
    _scatter(SPARSE_CELLS, "P", "tab:purple", "measured sparse vision")
    _scatter(COMPOSITION_CELLS, "D", "tab:red", "n=60 composition audit")

    ax.set_xlabel("V_share × V_red  (share-weighted vision-tower pruning)")
    ax.set_ylabel("end-to-end speedup ×")
    ax.set_title(
        "C-VISION scatter-back ceiling validation\n"
        f"{len(all_cells)} regimes; C-CEILING is the null, not a fitted curve"
    )
    ax.grid(True, alpha=0.3)
    ax.set_xlim(0.0, 0.30)
    ax.set_ylim(1.0, 1.52)
    ax.legend(loc="lower right", fontsize=9)

    FIGURES.mkdir(parents=True, exist_ok=True)
    out_pdf = FIGURES / "v_share_v_red_ceiling.pdf"
    out_svg = FIGURES / "v_share_v_red_ceiling.svg"
    out_png = FIGURES / "v_share_v_red_ceiling.png"
    fig.tight_layout()
    fig.savefig(out_pdf, bbox_inches="tight", metadata=PDF_METADATA)
    fig.savefig(out_svg, bbox_inches="tight")
    fig.savefig(out_png, dpi=200, bbox_inches="tight")
    print(f"Wrote {out_pdf}")
    print(f"Wrote {out_svg}")
    print(f"Wrote {out_png}")

    summary = {
        "dev_cells": [
            {**_cell_dict(c), "error_pp": round(c.error_pp, 2), "product": round(c.product, 4)}
            for c in DEV_CELLS
        ],
        "holdout_cells": [
            {**_cell_dict(c), "error_pp": round(c.error_pp, 2), "product": round(c.product, 4)}
            for c in HOLDOUT_CELLS
        ],
        "cross_arch_cells": [
            {**_cell_dict(c), "error_pp": round(c.error_pp, 2), "product": round(c.product, 4)}
            for c in CROSS_ARCH_CELLS
        ],
        "measured_sparse_cells": [
            {**_cell_dict(c), "error_pp": round(c.error_pp, 2), "product": round(c.product, 4)}
            for c in SPARSE_CELLS
        ],
        "composition_cells": [
            {**_cell_dict(c), "error_pp": round(c.error_pp, 2), "product": round(c.product, 4)}
            for c in COMPOSITION_CELLS
        ],
        "worst_abs_error_pp": round(max(abs(c.error_pp) for c in all_cells), 2),
        "median_abs_error_pp": round(float(np.median([abs(c.error_pp) for c in all_cells])), 2),
    }
    out_json = FIGURES / "v_share_v_red_ceiling_data.json"
    out_json.write_text(json.dumps(summary, indent=2) + "\n")
    print(f"Wrote {out_json}")


if __name__ == "__main__":
    plot()
