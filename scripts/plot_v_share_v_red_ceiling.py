"""V_share × V_red → predicted-E2E surface plot.

Validates the C-VISION scatter-back ceiling
``E2E ≤ 1 / (1 − V_share × V_red)`` visually. Plots observed E2E for all
landed (V_share, V_red) regime cells against the ceiling curve.

Emits:

- ``paper/figures/v_share_v_red_ceiling.png`` — scatter of observed
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

# Measured sparse-execution boundary point (Qwen 2.5-VL-7B, VideoMME 8f).
SPARSE_CELLS = [
    CeilingCell("Qwen sparse-ViT 8f n=60", "measured sparse", 0.0998, 0.448, 1.047, 1.042),
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
    _scatter(SPARSE_CELLS, "P", "tab:purple", "Qwen measured sparse (n=60, fidelity fail)")
    _scatter(COMPOSITION_CELLS, "D", "tab:red", "n=60 composition audit")

    ax.set_xlabel("V_share × V_red  (share-weighted vision-tower pruning)")
    ax.set_ylabel("end-to-end speedup ×")
    ax.set_title(
        "C-VISION scatter-back ceiling validation\n"
        "10 regimes (4 Gemma dev + 3 holdout + 2 Qwen + 1 composition audit); "
        "Qwen lands at +0.1pp; holdout max 13.6pp (MVBench, advisory)"
    )
    ax.grid(True, alpha=0.3)
    ax.set_xlim(0.0, 0.30)
    ax.set_ylim(1.0, 1.50)
    ax.legend(loc="lower right", fontsize=9)

    FIGURES.mkdir(parents=True, exist_ok=True)
    out_png = FIGURES / "v_share_v_red_ceiling.png"
    fig.tight_layout()
    fig.savefig(out_png, dpi=200, bbox_inches="tight")
    print(f"Wrote {out_png}")

    summary = {
        "dev_cells": [
            {**asdict(c), "error_pp": round(c.error_pp, 2), "product": round(c.product, 4)}
            for c in DEV_CELLS
        ],
        "holdout_cells": [
            {**asdict(c), "error_pp": round(c.error_pp, 2), "product": round(c.product, 4)}
            for c in HOLDOUT_CELLS
        ],
        "cross_arch_cells": [
            {**asdict(c), "error_pp": round(c.error_pp, 2), "product": round(c.product, 4)}
            for c in CROSS_ARCH_CELLS
        ],
        "measured_sparse_cells": [
            {**asdict(c), "error_pp": round(c.error_pp, 2), "product": round(c.product, 4)}
            for c in SPARSE_CELLS
        ],
        "composition_cells": [
            {**asdict(c), "error_pp": round(c.error_pp, 2), "product": round(c.product, 4)}
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
