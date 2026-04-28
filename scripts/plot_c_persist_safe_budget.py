"""C-PERSIST tested-envelope table + follow-up speedup curve.

Emits:

- ``paper/figures/c_persist_safe_budget.png`` — two-panel figure. Left
  panel: Δacc vs frame-count for 7B and 3B Qwen 2.5-VL-4bit on the
  Phase 1.55A persistent-KV probe. Right panel: follow-up speedup
  (dense / session) vs frame-count for the same two architectures.
  Tested/tolerated thresholds (7B ≤16f, 3B ≤36f) are shaded.
- ``paper/figures/c_persist_safe_budget_data.json`` — the full per-cell
  numbers used to render the figure.

Numbers are transcribed from claim-matrix.md row 14 (C-PERSIST) and the
Phase 1.55A findings docs:

- 7B 8f/16f: `2026-04-19-phase-1_55A-persistent-kv-findings.md` + derived ramp
- 7B 18/20/24/32f: `2026-04-19-phase-1_55A-{18,20,24,32}f-frame-scaling-findings.md`
- 7B 40f: `2026-04-20-phase-1_55A-7b-40f-symmetry-findings.md`
- 3B 20f: `2026-04-19-phase-1_55A-3b-crossarch-findings.md`
- 3B 24f: `2026-04-20-phase-1_55A-3b-24f-shifted-ramp-findings.md`
- 3B 32f: `2026-04-20-phase-1_55A-3b-32f-plateaued-findings.md`
- 3B 36f: `2026-04-20-phase-1_55A-3b-36f-interpolation-findings.md`
- 3B 40f: `2026-04-20-phase-1_55A-3b-40f-deeper-plateau-findings.md`

Run:
    uv run python scripts/plot_c_persist_safe_budget.py
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

import matplotlib.pyplot as plt

REPO_ROOT = Path(__file__).resolve().parent.parent
FIGURES = REPO_ROOT / "paper" / "figures"


@dataclass(frozen=True)
class PersistCell:
    frame_count: int
    prefill_tokens_approx: int
    speedup_x: float
    delta_acc: float
    basin_session_share: str
    accepted_envelope: bool


SEVEN_B = [
    PersistCell(8, 3200, 47.23, -0.048, "0/14 non-letter", True),
    PersistCell(16, 6500, 91.06, 0.000, "0/14 non-letter", True),
    PersistCell(18, 7300, 70.28, -0.238, "7/14 non-letter (4-basin)", False),
    PersistCell(20, 8100, 94.42, -0.381, "13/14 non-letter (addCriterion)", False),
    PersistCell(24, 9700, 121.58, -0.429, "14/14 non-letter (saturated)", False),
    PersistCell(32, 12900, 149.88, -0.429, "14/14 non-letter (saturated)", False),
    PersistCell(40, 16100, 157.60, -0.476, "13/14 non-letter (addCriterion)", False),
]

THREE_B = [
    PersistCell(20, 8100, 136.07, -0.048, "0/14 non-letter", True),
    PersistCell(24, 9700, 154.0, -0.190, "0/14 non-letter (plateau)", True),
    PersistCell(32, 12900, 213.0, -0.190, "0/14 non-letter (plateau)", True),
    PersistCell(36, 14500, 215.2, -0.190, "0/14 non-letter (plateau)", True),
    PersistCell(40, 16100, 191.0, -0.238, "4/14 non-letter (basin onset)", False),
]


def _xs(cells: list[PersistCell]) -> list[int]:
    return [c.frame_count for c in cells]


def plot() -> None:
    fig, (ax_acc, ax_speed) = plt.subplots(1, 2, figsize=(13, 5.2))

    seven_xs = _xs(SEVEN_B)
    seven_acc = [c.delta_acc for c in SEVEN_B]
    seven_spd = [c.speedup_x for c in SEVEN_B]

    three_xs = _xs(THREE_B)
    three_acc = [c.delta_acc for c in THREE_B]
    three_spd = [c.speedup_x for c in THREE_B]

    # Accepted-region shading: 7B tolerated ≤16f (left of the 7B basin at 20f);
    # 3B tolerated ≤36f (left of the 3B basin bracketed (36f, 40f]).
    ax_acc.axvspan(0, 16, color="tab:blue", alpha=0.08, label="7B accepted ≤16f")
    ax_acc.axvspan(0, 36, color="tab:green", alpha=0.06, label="3B tolerated ≤36f")
    ax_speed.axvspan(0, 16, color="tab:blue", alpha=0.08)
    ax_speed.axvspan(0, 36, color="tab:green", alpha=0.06)

    ax_acc.plot(
        seven_xs,
        seven_acc,
        marker="o",
        color="tab:blue",
        linestyle="-",
        label="Qwen 2.5-VL-7B-4bit",
    )
    ax_acc.plot(
        three_xs,
        three_acc,
        marker="s",
        color="tab:green",
        linestyle="-",
        label="Qwen 2.5-VL-3B-4bit",
    )
    ax_acc.axhline(0.0, color="black", linewidth=0.6, linestyle=":")
    ax_acc.axhline(
        -0.05, color="tab:red", linewidth=0.6, linestyle="--", label="Δacc = -0.05 local criterion"
    )
    ax_acc.set_title("Follow-up accuracy cost (tested envelope shaded)")
    ax_acc.set_xlabel("frame count at ingest prefill")
    ax_acc.set_ylabel("Δacc (session − baseline)")
    ax_acc.set_xticks(sorted(set(seven_xs + three_xs)))
    ax_acc.grid(True, alpha=0.3)
    ax_acc.legend(loc="lower left", fontsize=8)

    ax_speed.plot(
        seven_xs,
        seven_spd,
        marker="o",
        color="tab:blue",
        linestyle="-",
        label="Qwen 2.5-VL-7B-4bit",
    )
    ax_speed.plot(
        three_xs,
        three_spd,
        marker="s",
        color="tab:green",
        linestyle="-",
        label="Qwen 2.5-VL-3B-4bit",
    )
    ax_speed.set_title("Follow-up speedup × (dense / session)")
    ax_speed.set_xlabel("frame count at ingest prefill")
    ax_speed.set_ylabel("speedup ×")
    ax_speed.set_xticks(sorted(set(seven_xs + three_xs)))
    ax_speed.grid(True, alpha=0.3)
    ax_speed.legend(loc="lower right", fontsize=8)

    fig.suptitle(
        "C-PERSIST tested envelope (Phase 1.55A four-regime probe, n=21/cell)\n"
        "Observed basin onset is deeper for the tested 3B point than the tested 7B point",
        fontsize=12,
    )
    fig.tight_layout()

    FIGURES.mkdir(parents=True, exist_ok=True)
    out_png = FIGURES / "c_persist_safe_budget.png"
    fig.savefig(out_png, dpi=200, bbox_inches="tight")
    print(f"Wrote {out_png}")

    summary = {
        "seven_b": [asdict(c) for c in SEVEN_B],
        "three_b": [asdict(c) for c in THREE_B],
        "thresholds": {
            "seven_b_accepted_frames": 16,
            "seven_b_accepted_prefill_tokens": 6500,
            "three_b_tolerated_frames": 36,
            "three_b_tolerated_prefill_tokens": 14500,
            "onset_depth_scaling_ratio": round(14500 / 8100, 2),
        },
    }
    out_json = FIGURES / "c_persist_safe_budget_data.json"
    out_json.write_text(json.dumps(summary, indent=2) + "\n")
    print(f"Wrote {out_json}")


if __name__ == "__main__":
    plot()
