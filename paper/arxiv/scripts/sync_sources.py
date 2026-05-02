#!/usr/bin/env python3
"""Generate manuscript-ready assets from repo evidence.

This script is intentionally conservative:

- it reads canonical, checked-in artifacts only
- it emits small diffable files under ``paper/arxiv/generated/``
- it keeps the default manuscript snapshot restricted to audited artifact,
  paper-grade evidence
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
os.environ.setdefault("MPLCONFIGDIR", str(REPO_ROOT / ".tmp" / "matplotlib"))

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.patches as mpatches  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402

MANUSCRIPT_ROOT = REPO_ROOT / "paper" / "arxiv"
GENERATED = MANUSCRIPT_ROOT / "generated"
ARTIFACTS = REPO_ROOT / "research" / "experiments" / "2026" / "artifacts"
PDF_METADATA = {"CreationDate": None, "ModDate": None}
SOURCE_KEYS = {
    "source",
    "artifact",
    "patched_source",
    "reference_source",
    "metrics_source",
    "summary_source",
}
ALLOWED_SOURCE_ROOTS = ("docs/", "paper/", "research/", "scripts/", "src/", "tests/")


def _run(cmd: list[str], cwd: Path | None = None) -> str:
    result = subprocess.run(
        cmd,
        cwd=cwd or REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _git_info(repo: Path) -> dict[str, str]:
    if not repo.exists():
        return {"sha": "missing", "commit_date": "missing"}
    sha = _run(["git", "rev-parse", "HEAD"], cwd=repo)
    commit_date = _run(["git", "show", "-s", "--format=%cs", "HEAD"], cwd=repo)
    if _run(["git", "status", "--short"], cwd=repo):
        sha = f"{sha}-dirty"
    return {"sha": sha, "commit_date": commit_date}


def _short_sha(sha: str, length: int = 7) -> str:
    if sha == "missing":
        return sha
    suffix = "-dirty" if sha.endswith("-dirty") else ""
    base = sha.removesuffix("-dirty")
    return f"{base[:length]}{suffix}"


def _iter_source_paths(payload: object) -> list[str]:
    paths: list[str] = []
    if isinstance(payload, dict):
        for key, value in payload.items():
            if key in SOURCE_KEYS and isinstance(value, str):
                paths.append(value)
            elif (key == "source_paths" or key.endswith("_source_paths")) and isinstance(
                value, list
            ):
                paths.extend(str(item) for item in value)
            else:
                paths.extend(_iter_source_paths(value))
    elif isinstance(payload, list):
        for value in payload:
            paths.extend(_iter_source_paths(value))
    return paths


def _tracked_paths() -> set[str]:
    return set(_run(["git", "ls-files"]).splitlines())


def _is_repo_source(path: str) -> bool:
    return path.startswith(ALLOWED_SOURCE_ROOTS)


def _source_path_problem(path: str) -> str | None:
    source = Path(path)
    if source.is_absolute() or path.startswith("~"):
        return f"non-repo source path {path}"
    if path.startswith("results/"):
        return f"ignored local results path {path}"
    if not _is_repo_source(path):
        return f"unknown source root {path}"
    return None


def _validate_source_paths(payload: object, *, context: str) -> None:
    tracked = _tracked_paths()
    problems: list[str] = []
    for source in _iter_source_paths(payload):
        if problem := _source_path_problem(source):
            problems.append(problem)
            continue
        source_path = REPO_ROOT / source
        if not source_path.exists():
            problems.append(f"missing source path {source}")
        elif source not in tracked:
            problems.append(f"untracked source path {source}")
    if problems:
        joined = "\n  - ".join(problems)
        raise FileNotFoundError(f"{context} has invalid source paths:\n  - {joined}")


def _run_artifact_integrity() -> None:
    _run([sys.executable, "scripts/audit_artifact_integrity.py"], cwd=REPO_ROOT)


def _run_auxiliary_table_builders() -> None:
    """Regenerate standalone tables that are sourced by the manuscript."""
    for script in [
        "scripts/build_c_persist_setup_inclusive.py",
        "scripts/build_competitor_positioning_table.py",
    ]:
        _run([sys.executable, script], cwd=REPO_ROOT)


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text())


def _ensure_dirs() -> None:
    for path in [
        REPO_ROOT / ".tmp" / "matplotlib",
        GENERATED,
        GENERATED / "figures",
        GENERATED / "tables",
        GENERATED / "tex",
        GENERATED / "data",
    ]:
        path.mkdir(parents=True, exist_ok=True)


def _save_pdf(fig: plt.Figure, path: Path, **kwargs: object) -> None:
    fig.savefig(path, metadata=PDF_METADATA, **kwargs)


def _sync_curated_paper_figures() -> None:
    figure_stems = [
        "v_share_v_red_ceiling",
        "c_persist_safe_budget",
        "anti_recomputation_overview",
    ]
    for stem in figure_stems:
        source_png = REPO_ROOT / "paper" / "figures" / f"{stem}.png"
        if source_png.exists():
            (GENERATED / "figures" / source_png.name).write_bytes(source_png.read_bytes())
        source_json = REPO_ROOT / "paper" / "figures" / f"{stem}_data.json"
        if source_json.exists():
            payload = _load_json(source_json)
            _validate_source_paths(payload, context=source_json.relative_to(REPO_ROOT).as_posix())
            (GENERATED / "data" / source_json.name).write_text(
                json.dumps(payload, indent=2, sort_keys=True) + "\n"
            )


def _draw_overview_box(
    ax,
    xy: tuple[float, float],
    width: float,
    height: float,
    *,
    face: str,
    edge: str = "#1f2933",
    text: str = "",
    size: float = 9,
    weight: str = "normal",
    linestyle: str = "solid",
    color: str = "#111827",
    lw: float = 1.0,
):
    rect = mpatches.FancyBboxPatch(
        xy,
        width,
        height,
        boxstyle="round,pad=0.004,rounding_size=0.020",
        linewidth=lw,
        edgecolor=edge,
        facecolor=face,
        linestyle=linestyle,
    )
    ax.add_patch(rect)
    if text:
        ax.text(
            xy[0] + width / 2,
            xy[1] + height / 2,
            text,
            ha="center",
            va="center",
            fontsize=size,
            weight=weight,
            color=color,
        )
    return rect


def _draw_overview_arrow(
    ax,
    start: tuple[float, float],
    end: tuple[float, float],
    *,
    color: str = "#374151",
    lw: float = 1.4,
) -> None:
    ax.annotate(
        "",
        xy=end,
        xytext=start,
        arrowprops=dict(arrowstyle="->", color=color, lw=lw, shrinkA=0, shrinkB=0),
    )


def _render_regime_overview_figure(snapshot: dict) -> None:
    """Render the paper's opening visual as a vector-first explainer."""

    repair = snapshot["selective_reprefill"]["adaptive"]
    persistent = snapshot["persistent_kv"]
    qwen_16f = next(row for row in persistent["rows"] if int(row["frame_count"]) == 16)
    measured = snapshot["measured_sparse_execution"]
    gemma_short = measured["gemma_32f_short"]

    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "svg.fonttype": "none",
            "svg.hashsalt": "codec-through-regime-overview",
        }
    )
    fig, ax = plt.subplots(figsize=(7.45, 4.45))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    def draw_grid(
        ax,
        x: float,
        y: float,
        *,
        w: float = 0.25,
        h: float = 0.25,
        rows: int = 5,
        cols: int = 5,
        highlight: list[tuple[int, int, str]] | None = None,
        fill: str = "#f8fafc",
    ) -> None:
        _draw_overview_box(ax, (x, y), w, h, face=fill, edge="#111827", lw=0.8)
        for i in range(1, cols):
            ax.plot([x + w * i / cols, x + w * i / cols], [y, y + h], color="#94a3b8", lw=0.45)
        for j in range(1, rows):
            ax.plot([x, x + w], [y + h * j / rows, y + h * j / rows], color="#94a3b8", lw=0.45)
        for row, col, color in highlight or []:
            cell_w = w / cols
            cell_h = h / rows
            ax.add_patch(
                mpatches.Rectangle(
                    (x + col * cell_w, y + (rows - 1 - row) * cell_h),
                    cell_w,
                    cell_h,
                    facecolor=color,
                    edgecolor="none",
                    alpha=0.88,
                )
            )

    def panel_rect(idx: int, title: str, color: str) -> tuple[float, float, float, float]:
        col = (idx - 1) % 4
        row = 0 if idx <= 4 else 1
        w = 0.224
        h = 0.335
        gap_x = 0.020
        x = 0.024 + col * (w + gap_x)
        y = 0.503 if row == 0 else 0.116
        _draw_overview_box(ax, (x, y), w, h, face="#ffffff", edge="#0f172a", lw=0.95)
        _draw_overview_box(
            ax,
            (x + 0.012, y + h - 0.070),
            0.046,
            0.054,
            face="#111827",
            edge="#111827",
            text=str(idx),
            color="white",
            size=7.6,
            weight="bold",
            lw=0.7,
        )
        ax.text(
            x + 0.069,
            y + h - 0.030,
            title,
            fontsize=7.1,
            color=color,
            weight="bold",
            va="top",
        )
        return x, y, w, h

    def px(panel: tuple[float, float, float, float], rx: float) -> float:
        return panel[0] + panel[2] * rx

    def py(panel: tuple[float, float, float, float], ry: float) -> float:
        return panel[1] + panel[3] * ry

    def local_grid(
        panel: tuple[float, float, float, float],
        rx: float,
        ry: float,
        rw: float,
        rh: float,
        *,
        highlight: list[tuple[int, int, str]] | None = None,
        rows: int = 4,
        cols: int = 5,
        fill: str = "#f8fafc",
    ) -> None:
        draw_grid(
            ax,
            px(panel, rx),
            py(panel, ry),
            w=panel[2] * rw,
            h=panel[3] * rh,
            rows=rows,
            cols=cols,
            highlight=highlight,
            fill=fill,
        )

    fig.suptitle(
        "Stop paying for the same video twice",
        fontsize=13.2,
        weight="bold",
        y=0.975,
    )
    fig.text(
        0.5,
        0.925,
        (
            "Carry state. Buy fresh evidence only where it matters. "
            "Never multiply incompatible speedups."
        ),
        ha="center",
        fontsize=7.5,
        color="#475569",
    )

    # 1. Today vs desired runtime.
    p = panel_rect(1, "TODAY -> TARGET", "#0f172a")
    ax.plot([px(p, 0.50), px(p, 0.50)], [py(p, 0.20), py(p, 0.77)], color="#cbd5e1", lw=0.85)
    ax.text(
        px(p, 0.25),
        py(p, 0.79),
        "recompute",
        fontsize=5.9,
        ha="center",
        color="#b91c1c",
        weight="bold",
    )
    ax.text(
        px(p, 0.75),
        py(p, 0.79),
        "update",
        fontsize=5.9,
        ha="center",
        color="#166534",
        weight="bold",
    )
    for i, yy in enumerate([0.62, 0.46, 0.30]):
        local_grid(p, 0.11, yy, 0.22, 0.10, rows=3, cols=4)
        _draw_overview_arrow(
            ax,
            (px(p, 0.35), py(p, yy + 0.05)),
            (px(p, 0.43), py(p, yy + 0.05)),
            color="#64748b",
            lw=0.7,
        )
        _draw_overview_box(
            ax,
            (px(p, 0.43), py(p, yy + 0.01)),
            p[2] * 0.06,
            p[3] * 0.08,
            face="#f8fafc",
            edge="#111827",
            text="V",
            size=4.9,
            lw=0.65,
        )
        local_grid(
            p,
            0.59,
            yy,
            0.21,
            0.10,
            rows=3,
            cols=4,
            highlight=[(1, (i + 1) % 4, "#22c55e")] if i else [],
        )
        _draw_overview_arrow(
            ax,
            (px(p, 0.81), py(p, yy + 0.05)),
            (px(p, 0.88), py(p, yy + 0.05)),
            color="#166534",
            lw=0.7,
        )
        _draw_overview_box(
            ax,
            (px(p, 0.88), py(p, yy + 0.01)),
            p[2] * 0.06,
            p[3] * 0.08,
            face="#ecfdf5",
            edge="#166534",
            text="Δ",
            size=5.0,
            lw=0.65,
        )
    ax.text(
        px(p, 0.25),
        py(p, 0.11),
        "pay again",
        fontsize=6.3,
        ha="center",
        color="#b91c1c",
        weight="bold",
    )
    ax.text(
        px(p, 0.75),
        py(p, 0.11),
        "buy changes",
        fontsize=6.3,
        ha="center",
        color="#166534",
        weight="bold",
    )

    # 2. Codec clue.
    p = panel_rect(2, "CODEC CLUE", "#0f172a")
    for y, label, highlights in [
        (0.65, "previous\nframe", []),
        (0.47, "motion +\nresidual", [(1, 1, "#3b82f6"), (2, 3, "#ef4444")]),
        (0.29, "changed\nblocks", [(1, 1, "#3b82f6"), (2, 3, "#ef4444")]),
    ]:
        local_grid(p, 0.16, y, 0.34, 0.13, rows=4, cols=5, highlight=highlights, fill="#ffffff")
        ax.text(px(p, 0.60), py(p, y + 0.065), label, fontsize=5.9, va="center", color="#334155")
    for y0, y1 in [(0.61, 0.54), (0.43, 0.36)]:
        _draw_overview_arrow(
            ax, (px(p, 0.33), py(p, y0)), (px(p, 0.33), py(p, y1)), color="#64748b", lw=0.8
        )
    ax.text(
        px(p, 0.50),
        py(p, 0.12),
        "not a codec claim;\nit is the systems clue",
        fontsize=5.8,
        ha="center",
        color="#64748b",
    )

    # 3. The wasteful VLM loop.
    p = panel_rect(3, "THROW STATE AWAY", "#b91c1c")
    _draw_overview_box(
        ax,
        (px(p, 0.10), py(p, 0.53)),
        p[2] * 0.20,
        p[3] * 0.13,
        face="#f8fafc",
        edge="#111827",
        text="▶",
        size=8.0,
        lw=0.7,
    )
    for i in range(3):
        _draw_overview_box(
            ax,
            (px(p, 0.38 + i * 0.045), py(p, 0.52 + i * 0.025)),
            p[2] * 0.16,
            p[3] * 0.13,
            face="#ffffff",
            edge="#64748b",
            lw=0.55,
        )
    _draw_overview_arrow(
        ax, (px(p, 0.31), py(p, 0.59)), (px(p, 0.40), py(p, 0.59)), color="#334155", lw=0.8
    )
    _draw_overview_arrow(
        ax, (px(p, 0.62), py(p, 0.59)), (px(p, 0.70), py(p, 0.59)), color="#334155", lw=0.8
    )
    _draw_overview_box(
        ax,
        (px(p, 0.70), py(p, 0.53)),
        p[2] * 0.15,
        p[3] * 0.12,
        face="#f8fafc",
        edge="#111827",
        text="ViT",
        size=5.7,
        lw=0.7,
    )
    ax.text(
        px(p, 0.50),
        py(p, 0.38),
        "throw away\nstate",
        fontsize=6.2,
        ha="center",
        color="#b91c1c",
        weight="bold",
    )
    ax.text(
        px(p, 0.50),
        py(p, 0.18),
        "rediscover the same scene",
        fontsize=6.3,
        ha="center",
        color="#b91c1c",
        weight="bold",
    )
    ax.plot([px(p, 0.19), px(p, 0.81)], [py(p, 0.14), py(p, 0.14)], color="#b91c1c", lw=0.9)

    # 4. C-PERSIST.
    p = panel_rect(4, "C-PERSIST", "#166534")
    for i, (q, text, face, edge) in enumerate(
        [
            ("Q1", "full\ncompute", "#fee2e2", "#b91c1c"),
            ("Q2", "repair\nsmall tail", "#dcfce7", "#166534"),
            ("Q3", "reuse\nrepaired", "#dcfce7", "#166534"),
        ]
    ):
        yy = 0.67 - i * 0.17
        ax.text(px(p, 0.11), py(p, yy), q, fontsize=6.3, va="center", color="#334155")
        _draw_overview_arrow(
            ax, (px(p, 0.22), py(p, yy)), (px(p, 0.34), py(p, yy)), color="#64748b", lw=0.75
        )
        _draw_overview_box(
            ax,
            (px(p, 0.35), py(p, yy - 0.043)),
            p[2] * 0.25,
            p[3] * 0.086,
            face=face,
            edge=edge,
            text=text,
            size=4.8,
            lw=0.7,
        )
    ax.text(
        px(p, 0.79),
        py(p, 0.63),
        f"{qwen_16f['speedup']:.1f}x",
        fontsize=10.2,
        ha="center",
        color="#166534",
        weight="bold",
    )
    ax.text(
        px(p, 0.79),
        py(p, 0.50),
        "warm follow-up\nafter ingest",
        fontsize=5.2,
        ha="center",
        color="#334155",
    )
    ax.text(
        px(p, 0.50),
        py(p, 0.18),
        f"{repair['speedup_min']:.2f}-{repair['speedup_max']:.2f}x repaired",
        fontsize=5.8,
        ha="center",
        color="#166534",
        weight="bold",
    )
    ax.text(
        px(p, 0.50),
        py(p, 0.105),
        "0/62 follow-up drift",
        fontsize=5.3,
        ha="center",
        color="#166534",
    )

    # 5. C-VISION.
    p = panel_rect(5, "C-VISION", "#0369a1")
    local_grid(p, 0.10, 0.55, 0.27, 0.18, rows=4, cols=5)
    _draw_overview_arrow(
        ax, (px(p, 0.39), py(p, 0.64)), (px(p, 0.52), py(p, 0.64)), color="#0369a1", lw=0.8
    )
    local_grid(
        p,
        0.55,
        0.55,
        0.27,
        0.18,
        rows=4,
        cols=5,
        highlight=[(1, 1, "#38bdf8"), (2, 2, "#38bdf8"), (1, 4, "#38bdf8")],
    )
    ax.text(px(p, 0.46), py(p, 0.73), "keep\nfewer", fontsize=5.5, ha="center", color="#0369a1")
    ax.text(
        px(p, 0.50),
        py(p, 0.38),
        f"{gemma_short['observed_e2e']:.3f}x E2E",
        fontsize=8.0,
        ha="center",
        color="#0369a1",
        weight="bold",
    )
    ax.text(
        px(p, 0.50),
        py(p, 0.27),
        "first-query sparse vision; 0/20 drift",
        fontsize=5.6,
        ha="center",
        color="#334155",
    )
    ax.text(
        px(p, 0.50),
        py(p, 0.14),
        "not every sparse point is safe",
        fontsize=5.7,
        ha="center",
        color="#64748b",
    )

    # 6. C-CEILING.
    p = panel_rect(6, "C-CEILING", "#4f46e5")
    _draw_overview_box(
        ax,
        (px(p, 0.12), py(p, 0.55)),
        p[2] * 0.76,
        p[3] * 0.11,
        face="#eef2ff",
        edge="#4f46e5",
        lw=0.75,
    )
    ax.add_patch(
        mpatches.Rectangle(
            (px(p, 0.12), py(p, 0.55)),
            p[2] * 0.30,
            p[3] * 0.11,
            facecolor="#bfdbfe",
            edgecolor="none",
        )
    )
    ax.text(
        px(p, 0.27), py(p, 0.605), "vision", fontsize=5.5, ha="center", va="center", color="#0f172a"
    )
    ax.text(
        px(p, 0.65),
        py(p, 0.605),
        "fixed work",
        fontsize=5.5,
        ha="center",
        va="center",
        color="#0f172a",
    )
    ax.text(
        px(p, 0.50),
        py(p, 0.33),
        "you only win where\ntime was spent",
        fontsize=5.8,
        ha="center",
        color="#4f46e5",
        weight="bold",
    )
    ax.text(
        px(p, 0.50),
        py(p, 0.16),
        "this is why gains\ndo not multiply",
        fontsize=5.6,
        ha="center",
        color="#334155",
    )

    # 7. Candidate C-STREAM.
    p = panel_rect(7, "C-STREAM?", "#92400e")
    for i, (yy, color) in enumerate([(0.66, "#22c55e"), (0.51, "#f97316"), (0.36, "#8b5cf6")]):
        local_grid(
            p, 0.12, yy, 0.19, 0.11, rows=3, cols=4, highlight=[(1, i + 1, color)], fill="#ffffff"
        )
        _draw_overview_arrow(
            ax,
            (px(p, 0.34), py(p, yy + 0.055)),
            (px(p, 0.49), py(p, yy + 0.055)),
            color="#92400e",
            lw=0.75,
        )
        _draw_overview_box(
            ax,
            (px(p, 0.52), py(p, yy + 0.020)),
            p[2] * 0.20,
            p[3] * 0.07,
            face="#fff7ed",
            edge="#92400e",
            text="state",
            size=4.9,
            lw=0.65,
        )
    ax.text(
        px(p, 0.50),
        py(p, 0.22),
        "shift / rebuild /\ninvalidate",
        fontsize=5.9,
        ha="center",
        color="#92400e",
        weight="bold",
    )
    ax.text(
        px(p, 0.50),
        py(p, 0.10),
        "checked mixed; not headline",
        fontsize=5.3,
        ha="center",
        color="#64748b",
    )

    # 8. Bigger picture.
    p = panel_rect(8, "STATE STREAMS", "#166534")
    for i in range(42):
        x = px(p, 0.13 + (i % 7) * 0.035)
        y = py(p, 0.34 + (i // 7) * 0.060)
        ax.add_patch(
            mpatches.Rectangle(
                (x, y),
                p[2] * 0.010,
                p[3] * 0.010,
                facecolor="#94a3b8",
                edgecolor="none",
                alpha=0.75,
            )
        )
    ax.plot([px(p, 0.47), px(p, 0.47)], [py(p, 0.27), py(p, 0.77)], color="#cbd5e1", lw=0.8)
    for yy, color, label in [
        (0.67, "#22c55e", "objects"),
        (0.53, "#3b82f6", "motion"),
        (0.39, "#8b5cf6", "cache"),
    ]:
        ax.add_patch(
            mpatches.RegularPolygon(
                (px(p, 0.59), py(p, yy)),
                4,
                radius=p[2] * 0.040,
                orientation=0.78,
                facecolor=color,
                edgecolor="#0f172a",
                lw=0.45,
                alpha=0.86,
            )
        )
        _draw_overview_arrow(
            ax, (px(p, 0.66), py(p, yy)), (px(p, 0.78), py(p, yy)), color="#334155", lw=0.65
        )
        ax.text(px(p, 0.79), py(p, yy), label, fontsize=5.0, va="center", color="#334155")
    _draw_overview_box(
        ax,
        (px(p, 0.16), py(p, 0.09)),
        p[2] * 0.68,
        p[3] * 0.11,
        face="#ecfdf5",
        edge="#166534",
        text="target: state updates",
        size=5.6,
        color="#166534",
        weight="bold",
        lw=0.8,
    )

    fig.subplots_adjust(left=0.01, right=0.99, top=0.91, bottom=0.03)
    out_png = GENERATED / "figures" / "regime_overview.png"
    out_pdf = GENERATED / "figures" / "regime_overview.pdf"
    out_svg = GENERATED / "figures" / "regime_overview.svg"
    fig.savefig(out_png, dpi=240, bbox_inches="tight")
    fig.savefig(out_svg, bbox_inches="tight", metadata={"Date": "2026-05-02"})
    out_svg.write_text("\n".join(line.rstrip() for line in out_svg.read_text().splitlines()) + "\n")
    _save_pdf(fig, out_pdf, bbox_inches="tight")
    overview = {
        "figure": "regime_overview",
        "purpose": "opening stateful-video infographic for anti-recomputation regimes",
        "social_summary": (
            "Video VLMs should not pay for the same visual state twice; "
            "C-PERSIST, C-VISION, and candidate C-STREAM touch different "
            "stages and must keep separate denominators."
        ),
        "c_vision": {
            "clean_sparse_execution": "Gemma 32f short 1.316x, 0/20 paired drift",
            "qwen_boundary": "Qwen 16f kr=0.85 restores aggregate/format gate at 1.032x",
            "denominator": "first-query E2E",
            "source_paths": [
                "research/experiments/2026/artifacts/phase1_63G_gemma_track_b/pair_summary_32f.json",
                "research/experiments/2026/artifacts/phase1_63H_16f_kr_sweep/pair_summary_kr085_16f.json",
                "research/experiments/2026/artifacts/phase1_51V_session3/exp18_videomme_holdout_8f_L2_kr050_summary.json",
                "research/experiments/2026/artifacts/phase1_51V_session4/exp20_mvbench_holdout_8f_L2_kr050_summary.json",
                "research/experiments/2026/artifacts/phase1_51V_session5/exp24_tomato_holdout_8f_L2_kr050_summary.json",
            ],
        },
        "c_persist": {
            "raw_16f_speedup": qwen_16f["speedup"],
            "adaptive_same_class_speedup_min": repair["speedup_min"],
            "adaptive_same_class_speedup_max": repair["speedup_max"],
            "adaptive_all_query_speedup_min": repair["all_query_speedup_min"],
            "adaptive_all_query_speedup_max": repair["all_query_speedup_max"],
            "many_turn_horizon": 50,
            "denominator": "after-ingest follow-up / repaired-session latency",
            "source_paths": [
                qwen_16f["source"],
                *[
                    cell["summary_source"]
                    for cell in snapshot["selective_reprefill"]["adaptive_cells"]
                ],
                "research/experiments/2026/artifacts/phase1_55L_many_turn_cpersist/summary.json",
            ],
        },
        "routing": {
            "denominator": "effective fresh frames under dense backend",
            "speedup_claim": False,
            "source_paths": ["paper/arxiv/generated/data/lane_a_snapshot.json"],
        },
        "streaming": {
            "denominator": "scale-out component counters and E2E timing",
            "artifact_harmonization_pending": False,
            "status": "checked_mixed_bundle_candidate_regime",
            "gemma_26b_followup_status": (
                "default_cache_path_blocked_prefix_snapshot_small_n_positive"
            ),
            "source_paths": [
                "research/experiments/2026/artifacts/sam_scaleout_m5_20260429/sam_b0b_cache_correctness_summary.json",
                "research/experiments/2026/artifacts/sam_scaleout_m5_r2_20260430/sam_b0b_cache_correctness_summary.json",
                "research/experiments/2026/artifacts/sam_scaleout_m5_r2_followup_20260430/sam_b0b_cache_correctness_unguarded_patched_summary.json",
                "research/experiments/2026/artifacts/sam_scaleout_m5_20260429/sam_m5_5b_swa_prefix_snapshot_summary.json",
                "research/experiments/2026/artifacts/sam_scaleout_m5_20260429/sam_b3_streaming_baselines_summary.json",
            ],
        },
    }
    (GENERATED / "data" / "regime_overview_snapshot.json").write_text(
        json.dumps(overview, indent=2) + "\n"
    )


def _artifact_json(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"missing canonical artifact: {path}")
    return _load_json(path)


def _render_c_persist_timeline_figure() -> None:
    """Render the adaptive C-PERSIST timing mechanism as a focused timeline."""

    summary = _artifact_json(ARTIFACTS / "phase1_55F_stage_timing" / "stage_timing_summary.json")
    fixed_q2 = summary["fixed_k1"]["q_index"]["q2"]
    fixed_q3 = summary["fixed_k1"]["q_index"]["q3"]
    adaptive_q2 = summary["adaptive"]["q_index"]["q2"]
    adaptive_q3 = summary["adaptive"]["q_index"]["q3"]
    paired = summary["paired_q3"]

    fixed_q3_s = fixed_q3["median_elapsed_ms"] / 1000.0
    adaptive_q3_s = adaptive_q3["median_elapsed_ms"] / 1000.0
    speedup = paired["median_fixed_over_adaptive_speedup"]
    token_reduction = paired["median_tail_token_reduction"] * 100.0

    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "figure.facecolor": "white",
            "axes.facecolor": "white",
        }
    )
    fig, ax = plt.subplots(figsize=(7.4, 3.2))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    ax.text(
        0.02,
        0.93,
        "Adaptive C-PERSIST: repair once, reuse the repaired state",
        fontsize=11,
        weight="bold",
    )
    ax.text(
        0.02,
        0.86,
        "The visual tail is bought at Q2. Fixed K=1 buys it again at Q3; "
        "adaptive Q3 mostly appends text.",
        fontsize=7.6,
        color="#475569",
    )

    xs = {"q0": 0.12, "q2": 0.42, "q3": 0.72}
    for key, label in [
        ("q0", "Q0/Q1 first query"),
        ("q2", "Q2 repair"),
        ("q3", "Q3 follow-up"),
    ]:
        ax.text(xs[key], 0.78, label, fontsize=8.0, weight="bold", ha="center", color="#334155")

    def bar(
        x: float,
        y: float,
        *,
        cached_w: float,
        tail_w: float,
        tail_color: str,
        label: str,
        tail_label: str,
    ) -> None:
        ax.add_patch(
            mpatches.FancyBboxPatch(
                (x, y),
                cached_w,
                0.075,
                boxstyle="round,pad=0.01,rounding_size=0.018",
                facecolor="#dcfce7",
                edgecolor="#16a34a",
                linewidth=1.0,
            )
        )
        ax.add_patch(
            mpatches.FancyBboxPatch(
                (x + cached_w + 0.006, y),
                tail_w,
                0.075,
                boxstyle="round,pad=0.01,rounding_size=0.018",
                facecolor=tail_color,
                edgecolor="#c2410c",
                linewidth=1.0,
            )
        )
        ax.text(x + cached_w / 2, y + 0.038, label, fontsize=6.6, ha="center", va="center")
        ax.text(
            x + cached_w + 0.006 + tail_w / 2,
            y + 0.038,
            tail_label,
            fontsize=6.3,
            ha="center",
            va="center",
        )

    def arrow(start: tuple[float, float], end: tuple[float, float], color: str = "#64748b") -> None:
        ax.annotate(
            "",
            xy=end,
            xytext=start,
            arrowprops=dict(arrowstyle="->", lw=1.1, color=color, shrinkA=0, shrinkB=0),
        )

    # Q0/Q1 establishes the long reusable prefix; both policies share this part.
    ax.add_patch(
        mpatches.FancyBboxPatch(
            (0.035, 0.53),
            0.18,
            0.13,
            boxstyle="round,pad=0.012,rounding_size=0.025",
            facecolor="#f8fafc",
            edgecolor="#64748b",
            linewidth=1.0,
        )
    )
    ax.text(0.125, 0.595, "full prefill\n~8.1k tokens", fontsize=7.0, ha="center", va="center")

    ax.text(0.02, 0.64, "Fixed K=1", fontsize=8.2, weight="bold", color="#14532d")
    ax.text(0.02, 0.40, "Adaptive", fontsize=8.2, weight="bold", color="#14532d")

    # Q2 repair is the same operation in both rows.
    bar(
        xs["q2"] - 0.13,
        0.60,
        cached_w=0.105,
        tail_w=0.11,
        tail_color="#fed7aa",
        label="cache",
        tail_label=f"{fixed_q2['median_tail_prompt_tokens']:.0f} tok",
    )
    bar(
        xs["q2"] - 0.13,
        0.36,
        cached_w=0.105,
        tail_w=0.11,
        tail_color="#fed7aa",
        label="cache",
        tail_label=f"{adaptive_q2['median_tail_prompt_tokens']:.0f} tok",
    )

    # Q3 is where the adaptive mechanism appears.
    bar(
        xs["q3"] - 0.14,
        0.60,
        cached_w=0.105,
        tail_w=0.11,
        tail_color="#fb923c",
        label="cache",
        tail_label=f"{fixed_q3['median_tail_prompt_tokens']:.0f} tok",
    )
    bar(
        xs["q3"] - 0.14,
        0.36,
        cached_w=0.17,
        tail_w=0.025,
        tail_color="#fdba74",
        label="repaired cache",
        tail_label=f"{adaptive_q3['median_tail_prompt_tokens']:.0f}",
    )

    arrow((0.22, 0.595), (0.285, 0.635))
    arrow((0.22, 0.595), (0.285, 0.395))
    arrow((0.515, 0.638), (0.58, 0.638), "#16a34a")
    arrow((0.515, 0.398), (0.58, 0.398), "#16a34a")

    ax.text(
        0.67,
        0.70,
        f"Q3: {fixed_q3_s:.2f}s\nrepeat tail",
        fontsize=7.0,
        ha="center",
        color="#7c2d12",
    )
    ax.text(
        0.68,
        0.28,
        f"Q3: {adaptive_q3_s:.3f}s\nreuse repaired cache",
        fontsize=7.0,
        ha="center",
        color="#14532d",
    )

    ax.add_patch(
        mpatches.FancyBboxPatch(
            (0.80, 0.33),
            0.17,
            0.24,
            boxstyle="round,pad=0.018,rounding_size=0.03",
            facecolor="#ecfdf5",
            edgecolor="#16a34a",
            linewidth=1.2,
        )
    )
    ax.text(
        0.885,
        0.49,
        f"{speedup:.2f}x\npaired Q3\nspeedup",
        fontsize=8.8,
        weight="bold",
        ha="center",
        va="center",
        color="#14532d",
    )
    ax.text(
        0.885,
        0.39,
        f"{token_reduction:.1f}% fewer\nQ3 tail tokens",
        fontsize=7.2,
        ha="center",
        va="center",
        color="#166534",
    )

    ax.text(0.05, 0.16, "green = cached prefix/state", fontsize=7.2, color="#166534")
    ax.text(0.28, 0.16, "orange = newly bought tail work", fontsize=7.2, color="#c2410c")
    ax.text(
        0.02,
        0.08,
        "Timing attribution from short-slice fixed and adaptive repair artifacts; "
        "phase IDs stay in provenance.",
        fontsize=6.8,
        color="#475569",
    )

    fig.tight_layout()
    out_png = GENERATED / "figures" / "c_persist_timeline.png"
    out_pdf = GENERATED / "figures" / "c_persist_timeline.pdf"
    fig.savefig(out_png, dpi=220, bbox_inches="tight")
    _save_pdf(fig, out_pdf, bbox_inches="tight")
    plt.close(fig)
    (GENERATED / "data" / "c_persist_timeline_snapshot.json").write_text(
        json.dumps(
            {
                "phase": summary["phase"],
                "fixed_q3_elapsed_s": fixed_q3_s,
                "adaptive_q3_elapsed_s": adaptive_q3_s,
                "fixed_q3_tail_prompt_tokens": fixed_q3["median_tail_prompt_tokens"],
                "adaptive_q3_tail_prompt_tokens": adaptive_q3["median_tail_prompt_tokens"],
                "paired_q3_fixed_over_adaptive_speedup": speedup,
                "paired_q3_tail_token_reduction": paired["median_tail_token_reduction"],
                "source": (
                    "research/experiments/2026/artifacts/"
                    "phase1_55F_stage_timing/stage_timing_summary.json"
                ),
            },
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )


def _source_path_label(path: Path) -> str:
    path = path.resolve()
    try:
        return path.relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        pass
    return path.name


def _effective_fresh_frames(payload: dict) -> float:
    frame_count = int(payload["frame_count"])
    reuse = payload.get("reuse_ratio_mean_active")
    if reuse is None:
        raise ValueError(f"summary lacks reuse_ratio_mean_active: {payload}")
    return 1.0 + (frame_count - 1) * (1.0 - float(reuse))


def _cached_point(path: Path) -> dict[str, object]:
    payload = _artifact_json(path)
    return {
        "cached_accuracy": float(payload["cached_accuracy"]),
        "agreement": float(payload["agreement"]),
        "effective_fresh_frames": _effective_fresh_frames(payload),
        "git_sha": payload["environment"]["git_sha"],
        "git_dirty": bool(payload["environment"]["git_dirty"]),
        "artifact": path.relative_to(REPO_ROOT).as_posix(),
    }


def _dense_curve(prefix: str, frame_counts: list[int]) -> dict[str, float]:
    values: dict[str, float] = {}
    for frame_count in frame_counts:
        payload = _artifact_json(ARTIFACTS / prefix / f"frame_{frame_count}_summary.json")
        values[f"{float(frame_count):.1f}"] = float(payload["dense_accuracy"])
    return values


def _dense_curve_sources(prefix: str, frame_counts: list[int]) -> list[str]:
    return [
        (ARTIFACTS / prefix / f"frame_{frame_count}_summary.json").relative_to(REPO_ROOT).as_posix()
        for frame_count in frame_counts
    ]


def _lane_a_snapshot() -> dict:
    tomato_base_path = (
        ARTIFACTS
        / "phase1_20_tomato_motion_holdout_v2_cached_clean"
        / "max_abs-8.0-32.0-static+shifted-age4_summary.json"
    )
    mvbench_base_path = (
        ARTIFACTS
        / "phase1_21_mvbench_motion_holdout_v2_cached_nosticky"
        / "max_abs-8.0-32.0-static+shifted-age4_summary.json"
    )
    mvbench_sticky_path = (
        ARTIFACTS
        / "phase1_21_mvbench_motion_holdout_v2_cached"
        / "max_abs-8.0-32.0-static+shifted-age4-sticky4_summary.json"
    )
    sticky_payload = _artifact_json(mvbench_sticky_path)

    return {
        "tomato": {
            "cached_base": _cached_point(tomato_base_path),
            "uniform_dense": _dense_curve(
                "phase1_20_tomato_motion_holdout_v2_dense",
                [4, 6, 8],
            ),
            "uniform_dense_source_paths": _dense_curve_sources(
                "phase1_20_tomato_motion_holdout_v2_dense",
                [4, 6, 8],
            ),
        },
        "mvbench": {
            "cached_base": _cached_point(mvbench_base_path),
            "uniform_dense": _dense_curve(
                "phase1_21_mvbench_motion_holdout_v2_dense",
                [4, 6, 8],
            ),
            "uniform_dense_source_paths": _dense_curve_sources(
                "phase1_21_mvbench_motion_holdout_v2_dense",
                [4, 6, 8],
            ),
        },
        "supplementary": {
            "mvbench_sticky4": {
                **_cached_point(mvbench_sticky_path),
                "status": "supplementary_dirty_tree_rerun_required",
                "reason": (
                    "The sticky4 MVBench holdout artifact is still dirty-tree and "
                    "remains supplementary until rerun clean."
                ),
            }
        },
        "source_policy": {
            "default_snapshot": "clean_tree_only",
            "supplementary_excluded_from_main_figure": True,
            "sticky4_git_dirty": bool(sticky_payload["environment"]["git_dirty"]),
        },
    }


def _render_lane_a_figure(snapshot: dict) -> None:
    plt.rcParams.update(
        {
            "font.size": 11,
            "axes.titlesize": 12,
            "axes.labelsize": 11,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "savefig.facecolor": "white",
        }
    )

    colors = {
        "dense": "#1d3557",
        "base": "#9b2226",
    }

    fig, axes = plt.subplots(1, 2, figsize=(11.8, 5.2))
    panels = [
        (
            "TOMATO motion holdout (N=30)",
            snapshot["tomato"],
            "ties dense-8\nat 44% budget",
            4.6,
        ),
        (
            "MVBench motion holdout (N=30)",
            snapshot["mvbench"],
            "beats dense-6\nat lower budget",
            4.9,
        ),
    ]

    for ax, (title, payload, note, note_x) in zip(axes, panels, strict=True):
        dense = payload["uniform_dense"]
        dense_x = [float(x) for x in dense]
        dense_y = list(dense.values())

        ax.plot(
            dense_x,
            dense_y,
            color=colors["dense"],
            marker="o",
            linewidth=2.2,
            markersize=6,
            label="uniform dense-N",
        )

        base = payload["cached_base"]
        ax.scatter(
            [base["effective_fresh_frames"]],
            [base["cached_accuracy"]],
            color=colors["base"],
            s=110,
            marker="*",
            edgecolors="black",
            linewidths=0.7,
            zorder=5,
            label="planner base",
        )
        ax.annotate(
            note,
            xy=(base["effective_fresh_frames"], base["cached_accuracy"]),
            xytext=(note_x, base["cached_accuracy"] + 0.06),
            fontsize=9,
            arrowprops={"arrowstyle": "-", "color": colors["base"], "lw": 1.0},
        )

        ax.set_title(title)
        ax.set_xlabel("effective fresh frames")
        ax.set_ylabel("accuracy")
        ax.grid(True, axis="y", alpha=0.25, linewidth=0.8)
        ax.set_xlim(0, 8.6)
        ax.set_ylim(0.1, 0.72)
        ax.legend(frameon=False, loc="lower right", fontsize=9)

    fig.suptitle("Training-free temporal routing: audited holdout snapshot", fontsize=13)
    fig.tight_layout()
    png_path = GENERATED / "figures" / "lane_a_pareto.png"
    pdf_path = GENERATED / "figures" / "lane_a_pareto.pdf"
    fig.savefig(png_path, dpi=220, bbox_inches="tight")
    _save_pdf(fig, pdf_path, bbox_inches="tight")
    plt.close(fig)

    (GENERATED / "data" / "lane_a_snapshot.json").write_text(
        json.dumps(snapshot, indent=2, sort_keys=True) + "\n"
    )


def _write_lane_a_table(snapshot: dict) -> None:
    rows = [
        (
            "TOMATO",
            "planner base",
            snapshot["tomato"]["cached_base"]["cached_accuracy"],
            snapshot["tomato"]["cached_base"]["effective_fresh_frames"],
            "dense-8",
            snapshot["tomato"]["uniform_dense"]["8.0"],
            8.0,
            "tie",
        ),
        (
            "MVBench",
            "planner base",
            snapshot["mvbench"]["cached_base"]["cached_accuracy"],
            snapshot["mvbench"]["cached_base"]["effective_fresh_frames"],
            "dense-6",
            snapshot["mvbench"]["uniform_dense"]["6.0"],
            6.0,
            "frontier",
        ),
    ]

    lines = [
        r"\begin{table}[H]",
        r"\centering",
        (
            r"\caption{Automated snapshot of the Qwen holdout frontier from "
            r"canonical artifact summaries. Supplementary non-canonical "
            r"variants are intentionally excluded.}"
        ),
        r"\label{tab:lane-a-holdout}",
        r"\begin{tabular}{lllrrrl}",
        r"\toprule",
        r"Benchmark & Policy & Relation & Acc. & Fresh & Comparator & Comparator acc. \\",
        r"\midrule",
    ]
    for benchmark, policy, acc, fresh, comp, comp_acc, comp_fresh, relation in rows:
        lines.append(
            f"{benchmark} & {policy} & {relation} & {acc:.3f} & {fresh:.2f} & "
            f"{comp} ({comp_fresh:.0f}) & {comp_acc:.3f} \\\\"
        )
    lines.extend([r"\bottomrule", r"\end{tabular}", r"\end{table}"])
    (GENERATED / "tables" / "lane_a_holdout.tex").write_text("\n".join(lines) + "\n")


def _paired_pruning_snapshot(
    reference_path: Path,
    patched_path: Path,
    *,
    benchmark: str,
    frame_count: int,
    status: str,
    advisory_note: str | None = None,
) -> dict[str, object]:
    reference = _artifact_json(reference_path)
    patched = _artifact_json(patched_path)
    observed_e2e = float(reference["mean_dense_end_to_end_ms"]) / float(
        patched["mean_pruned_end_to_end_ms"]
    )
    v_red = (
        float(reference["mean_dense_vision_ms"]) - float(patched["mean_dense_vision_ms"])
    ) / float(reference["mean_dense_vision_ms"])
    v_share = float(reference["mean_dense_vision_ms"]) / float(
        reference["mean_dense_end_to_end_ms"]
    )
    predicted_e2e = 1.0 / (1.0 - v_share * v_red)
    acc_delta = float(patched["pruned_accuracy"]) - float(reference["dense_accuracy"])
    decode_delta_ms = float(patched["mean_decode_ms"]) - float(reference["mean_decode_ms"])
    decode_delta_rel = decode_delta_ms / float(reference["mean_decode_ms"])
    return {
        "benchmark": benchmark,
        "frame_count": frame_count,
        "observed_e2e": observed_e2e,
        "predicted_e2e": predicted_e2e,
        "v_red": v_red,
        "v_share": v_share,
        "acc_delta": acc_delta,
        "decode_delta_ms": decode_delta_ms,
        "decode_delta_rel": decode_delta_rel,
        "status": status,
        "advisory_note": advisory_note or "",
        "reference_source": _source_path_label(reference_path),
        "patched_source": _source_path_label(patched_path),
    }


def _c_vision_snapshot() -> dict[str, object]:
    rows = [
        _paired_pruning_snapshot(
            ARTIFACTS / "phase1_51V_session3" / "exp17_videomme_holdout_8f_unpatched_summary.json",
            ARTIFACTS / "phase1_51V_session3" / "exp18_videomme_holdout_8f_L2_kr050_summary.json",
            benchmark="VideoMME",
            frame_count=8,
            status="clean-holdout",
        ),
        _paired_pruning_snapshot(
            ARTIFACTS / "phase1_51V_session4" / "exp19_mvbench_holdout_8f_unpatched_summary.json",
            ARTIFACTS / "phase1_51V_session4" / "exp20_mvbench_holdout_8f_L2_kr050_summary.json",
            benchmark="MVBench",
            frame_count=8,
            status="advisory-holdout",
            advisory_note="50 ms decode delta on a 432 ms window; interpreted as OS-jitter scale.",
        ),
    ]
    rows.append(
        _paired_pruning_snapshot(
            ARTIFACTS / "phase1_51V_session5" / "exp23_tomato_holdout_8f_unpatched_summary.json",
            ARTIFACTS / "phase1_51V_session5" / "exp24_tomato_holdout_8f_L2_kr050_summary.json",
            benchmark="TOMATO",
            frame_count=8,
            status="advisory-holdout",
            advisory_note=(
                "Revised thermal gate misses by 19 ms in the favorable direction; "
                "source artifacts are checked into this repo."
            ),
        )
    )

    return {"rows": rows}


def _measured_sparse_execution_snapshot() -> dict[str, object]:
    """Return artifact-backed measured sparse-vision execution cells.

    These rows are deliberately separate from the older semantic C-VISION
    holdouts. They time real skipped vision-tower work and therefore carry a
    different evidence class and a different failure surface.
    """

    gemma_dir = ARTIFACTS / "phase1_63G_gemma_track_b"
    qwen_dir = ARTIFACTS / "phase1_63H_16f_kr_sweep"
    qwen_e_dir = ARTIFACTS / "phase1_63E_track_b_frame_scaling"

    gemma_scaling = _artifact_json(gemma_dir / "scaling_summary.json")
    gemma_rows = []
    for cell in gemma_scaling["cells"]:
        frame_count = int(cell["frame_count"])
        pair = _artifact_json(gemma_dir / f"pair_summary_{frame_count}f.json")
        all_row = pair["all"]
        gemma_rows.append(
            {
                "model": "Gemma 4-E4B",
                "frame_count": frame_count,
                "n": int(cell["n_paired_items"]),
                "accuracy_delta": float(cell["accuracy_delta"]),
                "choice_agreement": float(all_row["choice_agreement"]),
                "dense_parse_failures": int(all_row["dense_parse_failures"]),
                "sparse_parse_failures": int(all_row["sparse_parse_failures"]),
                "vision_reduction": float(cell["vision_reduction"]),
                "vision_share_dense": float(cell["vision_share_dense"]),
                "observed_e2e": float(cell["actual_e2e_speedup"]),
                "predicted_e2e": float(cell["predicted_e2e_speedup"]),
                "residual": float(cell["actual_minus_predicted"]),
                "pass_format": bool(cell["pass_format"]),
                "pass_ceiling": bool(cell["pass_ceiling_explained"]),
                "source": _source_path_label(gemma_dir / f"pair_summary_{frame_count}f.json"),
            }
        )

    gemma_32f = _artifact_json(gemma_dir / "pair_summary_32f.json")
    gemma_32f_short = gemma_32f["by_group"]["short"]

    qwen_rows = []
    qwen_8f = _artifact_json(qwen_e_dir / "pair_summary_8f.json")["all"]
    qwen_rows.append(
        {
            "model": "Qwen2.5-VL-7B",
            "setting": "8f, kr=0.50",
            "n": int(qwen_8f["n"]),
            "accuracy_delta": float(qwen_8f["accuracy_delta_sparse_minus_dense"]),
            "choice_agreement": float(qwen_8f["choice_agreement"]),
            "sparse_parse_failures": int(qwen_8f["sparse_parse_failures"]),
            "vision_reduction": float(qwen_8f["vision_reduction"]),
            "observed_e2e": float(qwen_8f["actual_e2e_speedup_dense_over_sparse"]),
            "predicted_e2e": float(qwen_8f["predicted_e2e_speedup_from_vision_only"]),
            "residual": float(qwen_8f["actual_minus_predicted_e2e_speedup"]),
            "interpretation": "ceiling-validating fidelity fail",
            "source": _source_path_label(qwen_e_dir / "pair_summary_8f.json"),
        }
    )
    for kr_label, keep_rate in [("0.65", "065"), ("0.75", "075"), ("0.85", "085")]:
        path = qwen_dir / f"pair_summary_kr{keep_rate}_16f.json"
        row = _artifact_json(path)["all"]
        qwen_rows.append(
            {
                "model": "Qwen2.5-VL-7B",
                "setting": f"16f, kr={kr_label}",
                "n": int(row["n"]),
                "accuracy_delta": float(row["accuracy_delta_sparse_minus_dense"]),
                "choice_agreement": float(row["choice_agreement"]),
                "sparse_parse_failures": int(row["sparse_parse_failures"]),
                "vision_reduction": float(row["vision_reduction"]),
                "observed_e2e": float(row["actual_e2e_speedup_dense_over_sparse"]),
                "predicted_e2e": float(row["predicted_e2e_speedup_from_vision_only"]),
                "residual": float(row["actual_minus_predicted_e2e_speedup"]),
                "interpretation": (
                    "within aggregate-accuracy/format gates; low-gain boundary"
                    if kr_label == "0.85"
                    else "recovery sweep"
                ),
                "source": _source_path_label(path),
            }
        )

    return {
        "gemma_rows": gemma_rows,
        "gemma_32f_short": {
            "n": int(gemma_32f_short["n"]),
            "accuracy_delta": float(gemma_32f_short["accuracy_delta_sparse_minus_dense"]),
            "choice_agreement": float(gemma_32f_short["choice_agreement"]),
            "dense_parse_failures": int(gemma_32f_short["dense_parse_failures"]),
            "sparse_parse_failures": int(gemma_32f_short["sparse_parse_failures"]),
            "vision_reduction": float(gemma_32f_short["vision_reduction"]),
            "vision_share_dense": float(gemma_32f_short["vision_share_dense"]),
            "observed_e2e": float(gemma_32f_short["actual_e2e_speedup_dense_over_sparse"]),
            "predicted_e2e": float(gemma_32f_short["predicted_e2e_speedup_from_vision_only"]),
            "residual": float(gemma_32f_short["actual_minus_predicted_e2e_speedup"]),
            "source": _source_path_label(gemma_dir / "pair_summary_32f.json"),
        },
        "qwen_rows": qwen_rows,
    }


def _persistent_kv_snapshot() -> dict[str, object]:
    summary_paths = {
        8: (
            ARTIFACTS
            / "loop_queue_20260419_155108"
            / "phase1_55A_persistent_kv_qwen"
            / "summary.json"
        ),
        16: ARTIFACTS / "phase1_55A_16f_frame_scaling" / "summary.json",
        18: ARTIFACTS / "phase1_55A_18f_frame_scaling" / "summary.json",
        20: ARTIFACTS / "phase1_55A_20f_frame_scaling" / "summary.json",
        24: ARTIFACTS / "phase1_55A_24f_frame_scaling" / "summary.json",
        32: ARTIFACTS / "phase1_55A_32f_frame_scaling" / "summary.json",
    }

    rows: list[dict[str, object]] = []
    for frame_count, path in summary_paths.items():
        payload = _artifact_json(path)
        rows.append(
            {
                "frame_count": frame_count,
                "speedup": float(payload["speedup_first_over_follow"]),
                "follow_up_median_s": (
                    float(payload["session_follow_up"]["median_elapsed_ms"]) / 1000.0
                ),
                "accuracy_delta": float(payload["accuracy_delta_session_minus_baseline"]),
                "prefix_coverage": float(payload["mean_follow_up_prefix_coverage"]),
                "source": _source_path_label(path),
            }
        )
    return {"rows": rows}


def _selective_reprefill_cell(
    *,
    label: str,
    regime: str,
    policy: str,
    metrics_path: Path,
    summary_path: Path,
) -> dict:
    metrics = _artifact_json(metrics_path)
    summary = _artifact_json(summary_path)
    return {
        "label": label,
        "regime": regime,
        "policy": policy,
        "n_sessions": int(metrics["n_sessions"]),
        "n_pairs": int(metrics["n_pairs"]),
        "n_follow_up_pairs": int(metrics["n_follow_up_pairs"]),
        "n_q3_pairs": int(metrics["q_index_breakdown"]["q3"]["n"]),
        "paired_correctness_diffs": int(metrics["paired_correctness_diffs"]),
        "paired_choice_diffs": int(metrics["paired_choice_diffs"]),
        "pathological_follow_up_hits": int(metrics["pathological_follow_up_hits"]),
        "pathological_q3_hits": int(metrics["pathological_q3_hits"]),
        "speedup": float(metrics["speedup_follow_up_median_cold_over_session"]),
        "all_query_speedup": float(metrics["speedup_all_query_median_cold_over_session_follow_up"]),
        "session_follow_up_median_s": float(metrics["session_follow_up_median_ms"]) / 1000.0,
        "setup_inclusive_available": "session_follow_up_setup_amortized_median_ms" in metrics,
        "setup_inclusive_follow_up_median_s": (
            float(metrics["session_follow_up_setup_amortized_median_ms"]) / 1000.0
            if "session_follow_up_setup_amortized_median_ms" in metrics
            else None
        ),
        "setup_inclusive_speedup": (
            float(metrics["speedup_follow_up_median_cold_over_session_setup_amortized"])
            if "speedup_follow_up_median_cold_over_session_setup_amortized" in metrics
            else None
        ),
        "baseline_accuracy": float(summary["baseline"]["accuracy"]),
        "peak_rss_gb": float(summary["peak_rss_gb"]),
        "metrics_source": _source_path_label(metrics_path),
        "summary_source": _source_path_label(summary_path),
    }


def _sum_reprefill_cells(cells: list[dict]) -> dict:
    speedups = [float(cell["speedup"]) for cell in cells]
    all_query_speedups = [float(cell["all_query_speedup"]) for cell in cells]
    rss = [float(cell["peak_rss_gb"]) for cell in cells]
    latencies = [float(cell["session_follow_up_median_s"]) for cell in cells]
    return {
        "n_pairs": sum(int(cell["n_pairs"]) for cell in cells),
        "n_sessions": sum(int(cell["n_sessions"]) for cell in cells),
        "n_follow_up_pairs": sum(int(cell["n_follow_up_pairs"]) for cell in cells),
        "n_q3_pairs": sum(int(cell["n_q3_pairs"]) for cell in cells),
        "paired_correctness_diffs": sum(int(cell["paired_correctness_diffs"]) for cell in cells),
        "paired_choice_diffs": sum(int(cell["paired_choice_diffs"]) for cell in cells),
        "pathological_follow_up_hits": sum(
            int(cell["pathological_follow_up_hits"]) for cell in cells
        ),
        "pathological_q3_hits": sum(int(cell["pathological_q3_hits"]) for cell in cells),
        "speedup_min": min(speedups),
        "speedup_max": max(speedups),
        "all_query_speedup_min": min(all_query_speedups),
        "all_query_speedup_max": max(all_query_speedups),
        "latency_min_s": min(latencies),
        "latency_max_s": max(latencies),
        "rss_min": min(rss),
        "rss_max": max(rss),
        "setup_inclusive_available": all(bool(cell["setup_inclusive_available"]) for cell in cells),
    }


def _selective_reprefill_snapshot() -> dict:
    fixed_cells = [
        _selective_reprefill_cell(
            label="1.55D",
            regime="20f short",
            policy="fixed K=1",
            metrics_path=ARTIFACTS
            / "phase1_55D_selective_reprefill_v2"
            / "pair_metrics_k1_n7.json",
            summary_path=ARTIFACTS / "phase1_55D_selective_reprefill_v2" / "summary_k1_n7.json",
        ),
        _selective_reprefill_cell(
            label="1.55G",
            regime="20f medium",
            policy="fixed K=1",
            metrics_path=ARTIFACTS
            / "phase1_55G_k1_medium_replication"
            / "pair_metrics_k1_n10.json",
            summary_path=ARTIFACTS / "phase1_55G_k1_medium_replication" / "summary_k1_n10.json",
        ),
        _selective_reprefill_cell(
            label="1.55I",
            regime="20f long",
            policy="fixed K=1",
            metrics_path=ARTIFACTS / "phase1_55I_k1_long_replication" / "pair_metrics_k1_n7.json",
            summary_path=ARTIFACTS / "phase1_55I_k1_long_replication" / "summary_k1_n7.json",
        ),
        _selective_reprefill_cell(
            label="1.55H",
            regime="32f short",
            policy="fixed K=1",
            metrics_path=ARTIFACTS / "phase1_55H_k1_32f_short_probe" / "pair_metrics_k1_n7.json",
            summary_path=ARTIFACTS / "phase1_55H_k1_32f_short_probe" / "summary_k1_n7.json",
        ),
    ]
    adaptive_cells = [
        _selective_reprefill_cell(
            label="1.55F",
            regime="20f short",
            policy="adaptive Q2 K=1, Q3 post-Q2 K=0",
            metrics_path=ARTIFACTS / "phase1_55F_q3_post_q2_state" / "pair_metrics_k1_n7.json",
            summary_path=ARTIFACTS / "phase1_55F_q3_post_q2_state" / "summary_k1_n7.json",
        ),
        _selective_reprefill_cell(
            label="1.55F-medium",
            regime="20f medium",
            policy="adaptive Q2 K=1, Q3 post-Q2 K=0",
            metrics_path=ARTIFACTS
            / "phase1_55F_medium_adaptive_replication"
            / "pair_metrics_k1_n10.json",
            summary_path=ARTIFACTS
            / "phase1_55F_medium_adaptive_replication"
            / "summary_k1_n10.json",
        ),
        _selective_reprefill_cell(
            label="1.55F-long",
            regime="20f long",
            policy="adaptive Q2 K=1, Q3 post-Q2 K=0",
            metrics_path=ARTIFACTS
            / "phase1_55F_long_adaptive_replication"
            / "pair_metrics_k1_n7.json",
            summary_path=ARTIFACTS / "phase1_55F_long_adaptive_replication" / "summary_k1_n7.json",
        ),
        _selective_reprefill_cell(
            label="1.55F-32f",
            regime="32f short",
            policy="adaptive Q2 K=1, Q3 post-Q2 K=0",
            metrics_path=ARTIFACTS
            / "phase1_55F_32f_short_adaptive_replication"
            / "pair_metrics_k1_n7.json",
            summary_path=ARTIFACTS
            / "phase1_55F_32f_short_adaptive_replication"
            / "summary_k1_n7.json",
        ),
    ]
    return {
        "fixed_cells": fixed_cells,
        "fixed": _sum_reprefill_cells(fixed_cells),
        "adaptive_cells": adaptive_cells,
        "adaptive": _sum_reprefill_cells(adaptive_cells),
    }


def _paired_drift_snapshot() -> dict:
    path = ARTIFACTS / "phase1_61_per_item_drift_summary.json"
    payload = _artifact_json(path)
    return {
        "phase": payload["phase"],
        "title": payload["title"],
        "source": _source_path_label(path),
        "panels": payload["panels"],
    }


def _paired_drift_interpretation(label: str) -> str:
    if label.startswith("1.30"):
        return "first-query admission damage"
    if label.startswith("1.42"):
        return "aggregate tie hides answer drift"
    if label.startswith("1.55A"):
        return "follow-up cache basin"
    raise ValueError(f"unknown paired-drift panel label: {label}")


def _paired_drift_public_label(label: str) -> str:
    if label.startswith("1.30"):
        return "Qwen first-query admission scout"
    if label.startswith("1.42"):
        return "Gemma MVBench holdout"
    if label.startswith("1.55A"):
        return "unrepaired persistent-KV 20f"
    raise ValueError(f"unknown paired-drift panel label: {label}")


def _paired_drift_extra(panel: dict) -> str:
    if "pathological_like" in panel:
        return f"; pathological-like {int(panel['pathological_like'])}/{int(panel['n'])}"
    if "dense_accuracy" in panel and "cached_accuracy" in panel:
        dense = float(panel["dense_accuracy"])
        cached = float(panel["cached_accuracy"])
        return f"; dense/cached acc. {dense:.3f}/{cached:.3f}"
    return ""


def _write_paired_drift_table(snapshot: dict) -> None:
    lines = [
        r"\begin{table}[H]",
        r"\centering",
        (
            r"\caption{Paired-drift audit. Aggregate accuracy can preserve a point "
            r"estimate while answer identity, correctness on individual examples, or "
            r"output format changes.}"
        ),
        r"\label{tab:paired-drift}",
        r"\small",
        r"\renewcommand{\arraystretch}{1.12}",
        r"\begin{tabularx}{\linewidth}{@{}X r r r X@{}}",
        r"\toprule",
        r"Source & \(N\) & Choice drift & Correctness drift & Mechanism signal \\",
        r"\midrule",
    ]
    for panel in snapshot["panels"]:
        n = int(panel["n"])
        choice_changed = int(panel["choice_changed"])
        correctness_changed = int(panel["correctness_changed"])
        interpretation = _paired_drift_interpretation(str(panel["label"]))
        label = _paired_drift_public_label(str(panel["label"]))
        extra = _paired_drift_extra(panel)
        lines.append(
            f"{label} & {n} & {choice_changed}/{n} & "
            f"{correctness_changed}/{n} & {interpretation}{extra} \\\\"
        )
    lines.extend(
        [
            r"\bottomrule",
            r"\end{tabularx}",
            r"\end{table}",
        ]
    )
    (GENERATED / "tables" / "paired_drift.tex").write_text("\n".join(lines) + "\n")
    (GENERATED / "data" / "paired_drift_snapshot.json").write_text(
        json.dumps(snapshot, indent=2, sort_keys=True) + "\n"
    )


def _write_c_persist_repair_table(snapshot: dict) -> None:
    repair = snapshot["selective_reprefill"]
    fixed = repair["fixed"]
    adaptive = repair["adaptive"]
    lines = [
        r"\begin{table}[H]",
        r"\centering",
        (
            r"\caption{Selective re-prefill repair frontier. Fixed \(K=1\) is "
            r"the no-coordination baseline; adaptive repaired-cache inheritance "
            r"is the primary broad repair result. Gains are reported as "
            r"cold follow-up or all-query latency divided by repaired-session "
            r"latency. Setup-inclusive session economics are reported "
            r"separately in Table~\ref{tab:c-persist-setup-inclusive}; this "
            r"compact table keeps the median follow-up denominators used for "
            r"the repair fidelity frontier.}"
        ),
        r"\label{tab:c-persist-repair}",
        r"\scriptsize",
        r"\renewcommand{\arraystretch}{1.20}",
        (
            r"\begin{tabularx}{\linewidth}"
            r"{@{}l X >{\raggedright\arraybackslash}p{0.22\linewidth} X@{}}"
        ),
        r"\toprule",
        (r"Policy & Scope & Follow-up median / cold gain & Validation signal \\"),
        r"\midrule",
        (
            r"Fixed \(K=1\) & 20f short/medium/long + 32f short & "
            f"\\shortstack[l]{{{fixed['latency_min_s']:.2f}--{fixed['latency_max_s']:.2f}s\\\\"
            f"{fixed['speedup_min']:.2f}--{fixed['speedup_max']:.2f}$\\times$}} & "
            f"paired drift: sess {fixed['paired_correctness_diffs']}/{fixed['n_sessions']}; "
            f"choice {fixed['paired_choice_diffs']}/{fixed['n_pairs']}; "
            f"correct {fixed['paired_correctness_diffs']}/{fixed['n_pairs']}; "
            f"pathological follow-ups {fixed['pathological_follow_up_hits']}/"
            f"{fixed['n_follow_up_pairs']}; drift rule-of-three over "
            f"n={fixed['n_pairs']}: \\(\\leq\\)3.2\\%; follow-up subset "
            f"0/{fixed['n_follow_up_pairs']} \\(\\leq\\)4.8\\% \\\\"
        ),
        (
            r"Adaptive repaired-cache inheritance & "
            r"20f short/medium/long + 32f short & "
            f"\\shortstack[l]{{{adaptive['latency_min_s']:.2f}--{adaptive['latency_max_s']:.2f}s\\\\"
            f"{adaptive['speedup_min']:.2f}--"
            f"{adaptive['speedup_max']:.2f}$\\times$ same-class\\\\"
            f"{adaptive['all_query_speedup_min']:.2f}--"
            f"{adaptive['all_query_speedup_max']:.2f}$\\times$ all-query}} & "
            f"paired drift: sess {adaptive['paired_correctness_diffs']}/{adaptive['n_sessions']}; "
            f"choice {adaptive['paired_choice_diffs']}/{adaptive['n_pairs']}; "
            f"correct {adaptive['paired_correctness_diffs']}/{adaptive['n_pairs']}; "
            f"follow-up subset 0/{adaptive['n_follow_up_pairs']} "
            "\\(\\leq\\)4.8\\%; "
            "third follow-up inherits the repaired state; paired third-follow-up "
            "fixed/adaptive "
            "speedup 9.50$\\times$ \\\\"
        ),
        r"\bottomrule",
        r"\end{tabularx}",
        r"\end{table}",
    ]
    (GENERATED / "tables" / "c_persist_repair.tex").write_text("\n".join(lines) + "\n")


def _qwen_bridge_boundary_row(label: str, path: Path) -> dict:
    payload = _artifact_json(path)
    return {
        "label": label,
        "n": int(payload["n_paired_queries"]),
        "sessions": int(payload.get("n_paired_sessions", payload["n_paired_queries"] // 3)),
        "delta": float(payload["accuracy_delta_streaming_minus_cold"]),
        "q0_delta": float(payload["q0_accuracy_delta_streaming_minus_cold"]),
        "follow_up_delta": float(payload["follow_up_accuracy_delta_streaming_minus_cold"]),
        "speedup": float(payload["amortized_speedup_cold_over_streaming"]),
        "active_fraction": payload["streaming_follow_up_vision_pruning_active_fraction"],
        "degenerates": int(payload.get("streaming_degenerate_count", 0)),
        "source": _source_path_label(path),
    }


def _qwen_bridge_boundary_snapshot() -> dict:
    rows = [
        _qwen_bridge_boundary_row(
            "cache reuse",
            ARTIFACTS / "phase1_30AD_instrumented_w_rerun" / "pair_summary.json",
        ),
        _qwen_bridge_boundary_row(
            "cache invalidated",
            ARTIFACTS / "phase1_30AC_cache_invalidated_followups" / "pair_summary.json",
        ),
        _qwen_bridge_boundary_row(
            "dense Q0 reference",
            ARTIFACTS / "phase1_30W_q0_dense_followup_pruned_full" / "pair_summary.json",
        ),
        _qwen_bridge_boundary_row(
            "long kr=0.67",
            ARTIFACTS / "phase1_30Z_long_q0_kr067_20260424" / "pair_summary.json",
        ),
        _qwen_bridge_boundary_row(
            "long kr=0.75",
            ARTIFACTS / "phase1_30AB_long_q0_kr075" / "pair_summary.json",
        ),
        _qwen_bridge_boundary_row(
            "long kr=0.80",
            ARTIFACTS / "phase1_30AB_long_q0_kr080" / "pair_summary.json",
        ),
        _qwen_bridge_boundary_row(
            "long kr=0.85",
            ARTIFACTS / "phase1_30AB_long_q0_kr085" / "pair_summary.json",
        ),
        _qwen_bridge_boundary_row(
            "long kr=0.90",
            ARTIFACTS / "phase1_30AB_long_q0_kr090" / "pair_summary.json",
        ),
    ]
    return {"rows": rows}


def _format_optional_fraction(value: object) -> str:
    if value is None:
        return "--"
    return f"{float(value):.1f}"


def _write_qwen_bridge_boundary_table(snapshot: dict) -> None:
    lines = [
        r"\begin{table}[H]",
        r"\centering",
        (
            r"\caption{Qwen composition boundary. The tested admission family "
            r"does not produce a deployable composition point. Dense-Q0 cache "
            r"reuse and cache invalidation reach the same net aggregate loss "
            r"through different any-paired-drift sets; only cache reuse preserves "
            r"the three-query speed profile. The speedup column is paired "
            r"three-query amortized end-to-end speedup versus cold all-query "
            r"execution. Follow-up vision active is the measured follow-up "
            r"vision-pruning activity fraction; -- means the row was not "
            r"instrumented.}"
        ),
        r"\label{tab:qwen-bridge-boundary}",
        r"\small",
        r"\renewcommand{\arraystretch}{1.18}",
        r"\resizebox{\linewidth}{!}{%",
        r"\begin{tabular}{@{}l r r r r r r r r@{}}",
        r"\toprule",
        (
            r"Policy & Sessions & Queries & \(\Delta\)acc & Q0 \(\Delta\) & "
            r"Follow-up \(\Delta\) & 3-query E2E & Follow-up vision active & Degenerate outputs \\"
        ),
        r"\midrule",
    ]
    for row in snapshot["rows"]:
        lines.append(
            f"{row['label']} & {row['sessions']} & {row['n']} & {row['delta']:+.3f} & "
            f"{row['q0_delta']:+.3f} & {row['follow_up_delta']:+.3f} & "
            f"{row['speedup']:.2f}$\\times$ & "
            f"{_format_optional_fraction(row['active_fraction'])} & "
            f"{row['degenerates']} \\\\"
        )
    lines.extend(
        [
            r"\bottomrule",
            r"\end{tabular}%",
            r"}",
            r"\end{table}",
        ]
    )
    (GENERATED / "tables" / "qwen_bridge_boundary.tex").write_text("\n".join(lines) + "\n")
    (GENERATED / "data" / "qwen_bridge_boundary_snapshot.json").write_text(
        json.dumps(snapshot, indent=2, sort_keys=True) + "\n"
    )


def _headline_snapshot() -> dict[str, object]:
    return {
        "c_vision": _c_vision_snapshot(),
        "measured_sparse_execution": _measured_sparse_execution_snapshot(),
        "persistent_kv": _persistent_kv_snapshot(),
        "selective_reprefill": _selective_reprefill_snapshot(),
    }


def _render_headline_figure(snapshot: dict) -> None:
    plt.rcParams.update(
        {
            "font.size": 10.5,
            "axes.titlesize": 12,
            "axes.labelsize": 10.5,
            "axes.spines.top": False,
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "savefig.facecolor": "white",
        }
    )

    fig, axes = plt.subplots(1, 2, figsize=(13.2, 5.2))
    left, right = axes

    status_styles = {
        "clean-holdout": {"facecolor": "#dfe7f2", "edgecolor": "#1d3557", "hatch": ""},
        "advisory-holdout": {"facecolor": "#f3ebd3", "edgecolor": "#8d6e00", "hatch": "///"},
        "dev-only": {"facecolor": "#eef0f2", "edgecolor": "#6c757d", "hatch": ".."},
    }

    cvision_rows = snapshot["c_vision"]["rows"]
    xs = list(range(len(cvision_rows)))
    observed = [row["observed_e2e"] for row in cvision_rows]
    predicted = [row["predicted_e2e"] for row in cvision_rows]
    labels = [f"{row['benchmark']}\n{int(row['frame_count'])}f" for row in cvision_rows]

    for x, row in zip(xs, cvision_rows, strict=True):
        style = status_styles[row["status"]]
        left.bar(
            x,
            row["observed_e2e"] - 1.0,
            bottom=1.0,
            width=0.62,
            color=style["facecolor"],
            edgecolor=style["edgecolor"],
            hatch=style["hatch"],
            linewidth=1.4,
            zorder=3,
        )
        left.scatter([x], [row["predicted_e2e"]], color="#9b2226", marker="D", s=48, zorder=5)
        left.text(
            x,
            row["observed_e2e"] + 0.02,
            f"{row['observed_e2e']:.3f}x",
            ha="center",
            va="bottom",
            fontsize=9,
        )

    left.axhline(1.0, color="#666666", linewidth=0.9)
    left.set_xticks(xs, labels)
    left.set_ylabel("end-to-end speedup (x)")
    left.set_ylim(1.0, max(max(observed), max(predicted)) + 0.18)
    left.set_title("First-pass vision pruning")
    left.grid(True, axis="y", alpha=0.22, linewidth=0.8, zorder=0)
    left.legend(
        handles=[
            mpatches.Patch(facecolor="#dfe7f2", edgecolor="#1d3557", label="clean holdout"),
            mpatches.Patch(
                facecolor="#f3ebd3",
                edgecolor="#8d6e00",
                hatch="///",
                label="advisory holdout",
            ),
            mpatches.Patch(
                facecolor="#eef0f2",
                edgecolor="#6c757d",
                hatch="..",
                label="dev-only fallback",
            ),
            plt.Line2D(
                [0],
                [0],
                marker="D",
                color="w",
                markerfacecolor="#9b2226",
                markersize=7,
                label="ceiling prediction",
            ),
        ],
        frameon=False,
        loc="upper left",
        fontsize=8.8,
    )

    kv_rows = snapshot["persistent_kv"]["rows"]
    frames = [row["frame_count"] for row in kv_rows]
    speedups = [row["speedup"] for row in kv_rows]
    deltas = [row["accuracy_delta"] for row in kv_rows]
    follow_up = [row["follow_up_median_s"] for row in kv_rows]

    right.plot(
        frames,
        speedups,
        color="#1d3557",
        marker="o",
        linewidth=2.0,
        markersize=5.8,
    )
    right.set_yscale("log")
    right.set_xlabel("frame count")
    right.set_ylabel("follow-up speedup vs first query (x)")
    right.set_title("Same-video follow-up reuse")
    right.grid(True, axis="y", alpha=0.22, linewidth=0.8)
    right.axvspan(7.5, 16.5, color="#8ecae6", alpha=0.12, lw=0)
    right.text(8.2, 18, "tested tolerance\n(<=16f)", color="#1d3557", fontsize=8.7)

    right_twin = right.twinx()
    right_twin.plot(
        frames,
        deltas,
        color="#9b2226",
        marker="s",
        linestyle="--",
        linewidth=1.6,
        markersize=5,
    )
    right_twin.axhline(0.0, color="#9b2226", linewidth=0.8, alpha=0.5)
    right_twin.set_ylabel("accuracy delta")
    right_twin.set_ylim(min(deltas) - 0.05, 0.05)

    for frame_count, speedup, median_s in zip(frames, speedups, follow_up, strict=True):
        right.annotate(
            f"{speedup:.0f}x\n{median_s:.2f}s",
            xy=(frame_count, speedup),
            xytext=(0, 8),
            textcoords="offset points",
            ha="center",
            fontsize=8.2,
        )

    fig.suptitle("Anti-recomputation gains are regime-dependent", fontsize=13)
    fig.tight_layout()
    (GENERATED / "figures" / "headline_results.png").parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(GENERATED / "figures" / "headline_results.png", dpi=220, bbox_inches="tight")
    _save_pdf(fig, GENERATED / "figures" / "headline_results.pdf", bbox_inches="tight")
    plt.close(fig)

    (GENERATED / "data" / "headline_snapshot.json").write_text(
        json.dumps(snapshot, indent=2, sort_keys=True) + "\n"
    )


def _write_headline_table(snapshot: dict) -> None:
    cvision_rows = snapshot["c_vision"]["rows"]
    measured_sparse = snapshot["measured_sparse_execution"]
    gemma_sparse_short = measured_sparse["gemma_32f_short"]
    qwen_sparse_safe = measured_sparse["qwen_rows"][-1]
    kv_by_frame = {row["frame_count"]: row for row in snapshot["persistent_kv"]["rows"]}
    repair = snapshot["selective_reprefill"]
    fixed_repair = repair["fixed"]
    adaptive_repair = repair["adaptive"]

    lines = [
        r"\begin{table}[H]",
        r"\centering",
        r"\caption{Headline anti-recomputation results by regime.}",
        r"\label{tab:headline-results}",
        r"\scriptsize",
        r"\renewcommand{\arraystretch}{1.14}",
        r"\begin{tabularx}{\linewidth}{@{}l X p{0.16\linewidth} c X l@{}}",
        r"\toprule",
        r"Regime & Setting & Speedup denominator & Gain & Validation / notes & Evidence \\",
        r"\midrule",
        (
            "After-ingest & Qwen raw warm follow-up reuse, 16f & "
            "cold/cached follow-up & "
            f"{kv_by_frame[16]['speedup']:.1f}$\\times$ & "
            f"{kv_by_frame[16]['follow_up_median_s']:.3f}\\,s median; "
            f"$\\Delta$acc {kv_by_frame[16]['accuracy_delta']:+.3f} & local clean \\\\"
        ),
        (
            "After-ingest & Qwen raw warm follow-up reuse, 8f & "
            "cold/cached follow-up & "
            f"{kv_by_frame[8]['speedup']:.1f}$\\times$ & "
            f"{kv_by_frame[8]['follow_up_median_s']:.3f}\\,s median; "
            f"$\\Delta$acc {kv_by_frame[8]['accuracy_delta']:+.3f} & local within criterion \\\\"
        ),
        (
            "After-ingest & Qwen repaired basin escape, adaptive & "
            "cold/repaired follow-up median & "
            f"{adaptive_repair['speedup_min']:.2f}--"
            f"{adaptive_repair['speedup_max']:.2f}$\\times$ & "
            f"choice/correct diffs {adaptive_repair['paired_choice_diffs']}/"
            f"{adaptive_repair['n_pairs']}; cold-all-query ratio "
            f"{adaptive_repair['all_query_speedup_min']:.2f}--"
            f"{adaptive_repair['all_query_speedup_max']:.2f}$\\times$ & "
            "local repair breadth \\\\"
        ),
        (
            "After-ingest & Qwen repaired basin escape, fixed K=1 & "
            "cold/repaired follow-up & "
            f"{fixed_repair['speedup_min']:.2f}--"
            f"{fixed_repair['speedup_max']:.2f}$\\times$ & "
            f"choice/correct diffs {fixed_repair['paired_choice_diffs']}/"
            f"{fixed_repair['n_pairs']}; pathological follow-ups "
            f"{fixed_repair['pathological_follow_up_hits']}/"
            f"{fixed_repair['n_follow_up_pairs']} & local repair breadth \\\\"
        ),
        (
            "First-pass & Gemma VideoMME 8f holdout & "
            "first-query E2E & "
            f"{cvision_rows[0]['observed_e2e']:.3f}$\\times$ "
            f"& $\\Delta$acc {cvision_rows[0]['acc_delta']:+.3f} & clean local \\\\"
        ),
        (
            "First-pass & Gemma measured sparse vision, 32f short & "
            "first-query E2E & "
            f"{gemma_sparse_short['observed_e2e']:.3f}$\\times$ & "
            f"choice agreement {gemma_sparse_short['choice_agreement'] * 100:.0f}\\%; "
            f"$\\Delta$acc {gemma_sparse_short['accuracy_delta']:+.3f}; "
            "parse failures 0/0 & clean sparse-execution cell \\\\"
        ),
        (
            "First-pass & Gemma MVBench 8f holdout & "
            "first-query E2E & "
            f"{cvision_rows[1]['observed_e2e']:.3f}$\\times$ & "
            f"$\\Delta$acc {cvision_rows[1]['acc_delta']:+.3f}; "
            "favorable timing caveat & advisory local \\\\"
        ),
        (
            "First-pass & Qwen measured sparse vision, 16f kr=0.85 & "
            "first-query E2E & "
            f"{qwen_sparse_safe['observed_e2e']:.3f}$\\times$ & "
            f"$\\Delta$acc {qwen_sparse_safe['accuracy_delta']:+.3f}; "
            f"vision reduction {qwen_sparse_safe['vision_reduction'] * 100:.1f}\\%; "
            "parse failures 0; agreement 81.7\\% & "
            "aggregate/format gate; low-gain boundary \\\\"
        ),
        r"\bottomrule",
        r"\end{tabularx}",
        r"\end{table}",
    ]
    (GENERATED / "tables" / "headline_results.tex").write_text("\n".join(lines) + "\n")


def _write_measured_sparse_execution_tables(snapshot: dict) -> None:
    measured = snapshot["measured_sparse_execution"]

    gemma_lines = [
        r"\begin{table}[H]",
        r"\centering",
        (
            r"\caption{Measured sparse vision execution on Gemma. The timed "
            r"path skips real vision-tower work. All three frame budgets have "
            r"zero paired accuracy delta and 100\% choice agreement, but the "
            r"full sweep is not format-clean because dense and sparse arms "
            r"share parse failures. The final row exposes the 32f short bucket "
            r"that supplies the clean 1.316\(\times\) headline cell.}"
        ),
        r"\label{tab:gemma-measured-sparse-vision}",
        r"\scriptsize",
        r"\renewcommand{\arraystretch}{1.12}",
        r"\begin{tabularx}{\linewidth}{@{}l r r r r r r r X@{}}",
        r"\toprule",
        (
            r"Frames / slice & \(n\) & \(\Delta\)acc & Agree & Parse fails & "
            r"\(V_{\mathrm{red}}\) & Observed & Residual & Ceiling / format verdict \\"
        ),
        r"\midrule",
    ]
    for row in measured["gemma_rows"]:
        parse = f"{row['dense_parse_failures']}/{row['sparse_parse_failures']}"
        if row["pass_ceiling"] and row["pass_format"]:
            interp = "ceiling + format pass"
        elif row["pass_ceiling"]:
            interp = "ceiling pass; format not clean (matched parse failures)"
        else:
            interp = "ceiling miss"
            if not row["pass_format"]:
                interp += "; format not clean (matched parse failures)"
        gemma_lines.append(
            f"{row['frame_count']}f & {row['n']} & "
            f"{row['accuracy_delta']:+.3f} & "
            f"{row['choice_agreement'] * 100:.0f}\\% & {parse} & "
            f"{row['vision_reduction'] * 100:.1f}\\% & "
            f"{row['observed_e2e']:.3f}$\\times$ & "
            f"{row['residual']:+.3f} & {interp} \\\\"
        )
    short = measured["gemma_32f_short"]
    gemma_lines.append(
        f"32f short & {short['n']} & "
        f"{short['accuracy_delta']:+.3f} & "
        f"{short['choice_agreement'] * 100:.0f}\\% & "
        f"{short['dense_parse_failures']}/{short['sparse_parse_failures']} & "
        f"{short['vision_reduction'] * 100:.1f}\\% & "
        f"{short['observed_e2e']:.3f}$\\times$ & "
        f"{short['residual']:+.3f} & clean sparse-execution operating point \\\\"
    )
    gemma_lines.extend([r"\bottomrule", r"\end{tabularx}", r"\end{table}"])

    qwen_lines = [
        r"\begin{table}[H]",
        r"\centering",
        (
            r"\caption{Measured sparse vision execution on Qwen. The 8f point "
            r"validates the timing model but fails fidelity. At 16f, increasing "
            r"the keep rate monotonically recovers aggregate accuracy and "
            r"format, ending at a point inside those tested gates but not "
            r"paired answer identity; it also no longer clears the "
            r"vision-reduction gate.}"
        ),
        r"\label{tab:qwen-measured-sparse-vision}",
        r"\scriptsize",
        r"\renewcommand{\arraystretch}{1.12}",
        r"\begin{tabularx}{\linewidth}{@{}l r r r r r r r X@{}}",
        r"\toprule",
        (
            r"Setting & \(n\) & \(\Delta\)acc & Agree & Parse fails & "
            r"\(V_{\mathrm{red}}\) & Observed & Residual & Ceiling / quality verdict \\"
        ),
        r"\midrule",
    ]
    for row in measured["qwen_rows"]:
        qwen_lines.append(
            f"{row['setting']} & {row['n']} & {row['accuracy_delta']:+.3f} & "
            f"{row['choice_agreement'] * 100:.1f}\\% & "
            f"{row['sparse_parse_failures']} & "
            f"{row['vision_reduction'] * 100:.1f}\\% & "
            f"{row['observed_e2e']:.3f}$\\times$ & "
            f"{row['residual']:+.3f} & {row['interpretation']} \\\\"
        )
    qwen_lines.extend([r"\bottomrule", r"\end{tabularx}", r"\end{table}"])

    out = GENERATED / "tables"
    out.joinpath("gemma_measured_sparse_vision.tex").write_text("\n".join(gemma_lines) + "\n")
    out.joinpath("qwen_measured_sparse_vision.tex").write_text("\n".join(qwen_lines) + "\n")
    (GENERATED / "data" / "measured_sparse_execution_snapshot.json").write_text(
        json.dumps(measured, indent=2, sort_keys=True) + "\n"
    )


def _write_c_persist_sampler_table() -> None:
    summary = _artifact_json(
        ARTIFACTS / "phase1_55K_adaptive_temperature_sweep" / "temperature_sweep_summary.json"
    )
    lines = [
        r"\begin{table}[H]",
        r"\centering",
        (
            r"\caption{Adaptive C-PERSIST sampler-temperature sweep on the "
            r"short-slice mechanism cell. This is robustness evidence "
            r"against a greedy-decoding artifact, not the full 0/93 breadth "
            r"claim and not a universal stochastic robustness theorem.}"
        ),
        r"\label{tab:c-persist-sampler-stability}",
        r"\small",
        r"\begin{tabular}{@{}r r r r r r@{}}",
        r"\toprule",
        (
            r"\(T\) & Baseline & Session & \(\Delta\)acc & "
            r"Choice/correct diffs & Speedup \\"
        ),
        r"\midrule",
    ]
    for row in summary["cells"]:
        lines.append(
            f"{row['temperature']:.1f} & "
            f"{row['baseline_n_correct']}/{row['n_pairs']} & "
            f"{row['session_n_correct']}/{row['n_pairs']} & "
            f"{row['accuracy_delta_session_minus_baseline']:+.3f} & "
            f"{row['paired_choice_diffs']}/{row['paired_correctness_diffs']} & "
            f"{row['speedup_all_query_median_cold_over_session_follow_up']:.2f}"
            r"$\times$ \\"
        )
    lines.extend([r"\bottomrule", r"\end{tabular}", r"\end{table}"])
    (GENERATED / "tables" / "c_persist_sampler_stability.tex").write_text("\n".join(lines) + "\n")


def _many_turn_snapshot() -> dict[str, object]:
    path = ARTIFACTS / "phase1_55L_many_turn_cpersist" / "summary.json"
    summary = _artifact_json(path)
    cells = {(str(cell["policy"]), int(cell["horizon"])): cell for cell in summary["cells"]}
    policy_labels = {
        "fixed_k1": r"fixed \(K=1\)",
        "adaptive_post_q2": r"adaptive repair",
        "refresh10": r"scheduled refresh-10",
    }
    rows = []
    for policy in ["fixed_k1", "adaptive_post_q2", "refresh10"]:
        cell = cells[(policy, 50)]
        follow = cell["followup_only"]
        post = cell.get("post_repair_only") or {}
        rows.append(
            {
                "policy": policy,
                "label": policy_labels[policy],
                "horizon": 50,
                "followup_n": int(follow["n"]),
                "choice_drift": int(follow["choice_drift"]),
                "correctness_drift": int(follow["correctness_drift"]),
                "pathological": int(follow["pathological"]),
                "median_followup_s": float(follow["median_elapsed_ms"]) / 1000.0,
                "post_repair_n": int(post.get("n", 0)),
                "post_repair_choice_drift": int(post.get("choice_drift", 0)),
                "post_repair_correctness_drift": int(post.get("correctness_drift", 0)),
                "post_repair_median_s": (
                    float(post["median_elapsed_ms"]) / 1000.0
                    if "median_elapsed_ms" in post
                    else None
                ),
                "pass_three_percent": bool(cell["pass_three_percent_drift_followup_only"]),
                "cliff": bool(cell["cliff_bucket_detected"]),
            }
        )
    return {
        "phase": summary["phase"],
        "history_mode": summary["history_mode"],
        "frame_count": int(summary["frame_count"]),
        "video_ids": summary["video_ids"],
        "n_baseline_chains": int(summary["n_baseline_chains"]),
        "n_baseline_rows": int(summary["n_baseline_rows"]),
        "n_paired_rows": int(summary["n_paired_rows"]),
        "policies": summary["policies"],
        "turn_counts": summary["turn_counts"],
        "rows": rows,
        "source_paths": [
            _source_path_label(path),
            summary["paths"]["baseline_jsonl"],
            summary["paths"]["paired_jsonl"],
            summary["paths"]["session_jsonl"],
        ],
    }


def _write_c_persist_seed_sweep_table() -> None:
    summary = _artifact_json(
        ARTIFACTS / "phase1_55K_extended_seed_sweep" / "extended_seed_sweep_summary.json"
    )
    by_temperature = summary["by_temperature"]
    lines = [
        r"\begin{table}[H]",
        r"\centering",
        (
            r"\caption{Adaptive C-PERSIST sampler-seed cross-product on the "
            r"short-slice mechanism cell. Three sampler seeds "
            r"\(\{42, 99, 2026\}\) at three temperatures "
            r"\(\{0.5, 1.0, 1.5\}\) on the same seven-clip 21-paired tranche. "
            r"All nine cells pass the preregistered fidelity, format, and "
            r"baseline-quality gates. This is robustness evidence that "
            r"the sampler-temperature result is not a single-seed coincidence "
            r"on the short tranche; it is not the full 0/93 breadth claim and "
            r"not benchmark generalization beyond this slice.}"
        ),
        r"\label{tab:c-persist-sampler-seed-sweep}",
        r"\small",
        r"\begin{tabular}{@{}r r r r r r@{}}",
        r"\toprule",
        (
            r"\(T\) & Seed cells & Max \(|\Delta\)acc\(|\) & "
            r"Max choice diffs & Max correctness diffs & Min baseline acc \\"
        ),
        r"\midrule",
    ]
    for temperature_str in sorted(by_temperature, key=float):
        cell = by_temperature[temperature_str]
        max_abs_delta = max(
            abs(float(cell["max_accuracy_delta"])),
            abs(float(cell["min_accuracy_delta"])),
        )
        lines.append(
            f"{float(temperature_str):.1f} & "
            f"{int(cell['n_seed_cells'])} pass & "
            f"{max_abs_delta:.3f} & "
            f"{int(cell['max_paired_choice_diffs'])}/21 & "
            f"{int(cell['max_paired_correctness_diffs'])}/21 & "
            f"{float(cell['min_baseline_accuracy']):.3f} \\\\"
        )
    lines.extend([r"\bottomrule", r"\end{tabular}", r"\end{table}"])
    (GENERATED / "tables" / "c_persist_sampler_seed_sweep.tex").write_text("\n".join(lines) + "\n")


def _write_c_persist_many_turn_table() -> None:
    snapshot = _many_turn_snapshot()
    lines = [
        r"\begin{table}[H]",
        r"\centering",
        (
            r"\caption{Many-turn C-PERSIST stress on seven 20f short VideoMME "
            r"videos. The stress cycles the same three questions through a "
            r"50-turn stateless question schedule, so it tests cache-horizon "
            r"stability under repeated follow-ups rather than natural dialogue. "
            r"The 560 dense baseline rows are deterministic replicas of 21 "
            r"unique stateless dense runs for turn-matched pairing, not "
            r"independent timing samples.}"
        ),
        r"\label{tab:c-persist-many-turn}",
        r"\scriptsize",
        r"\renewcommand{\arraystretch}{1.14}",
        (
            r"\begin{tabularx}{\linewidth}"
            r"{@{}p{0.18\linewidth} r r r r X@{}}"
        ),
        r"\toprule",
        (
            r"Policy & Horizon & Follow-ups & Choice/correct drift & "
            r"Median follow-up & Gate / post-repair check \\"
        ),
        r"\midrule",
    ]
    for row in snapshot["rows"]:
        if row["post_repair_n"]:
            interpretation = (
                f"post-repair drift {row['post_repair_choice_drift']}/"
                f"{row['post_repair_n']} / {row['post_repair_correctness_drift']}/"
                f"{row['post_repair_n']}; no cliff"
            )
        elif row["choice_drift"]:
            interpretation = (
                "passes 3\\% gate but has nonzero repeated-question drift; no pathologies"
            )
        else:
            interpretation = "passes 3\\% gate with no observed drift"
        lines.append(
            f"{row['label']} & {row['horizon']} & {row['followup_n']} & "
            f"{row['choice_drift']}/{row['correctness_drift']} & "
            f"{row['median_followup_s']:.3f}\\,s & {interpretation} \\\\"
        )
    lines.extend([r"\bottomrule", r"\end{tabularx}", r"\end{table}"])
    (GENERATED / "tables" / "c_persist_many_turn.tex").write_text("\n".join(lines) + "\n")
    (GENERATED / "data" / "c_persist_many_turn_snapshot.json").write_text(
        json.dumps(snapshot, indent=2, sort_keys=True) + "\n"
    )


def _write_memory_characterization_table() -> None:
    summary = _artifact_json(
        ARTIFACTS / "phase1_66_memory_characterization" / "memory_characterization_summary.json"
    )
    if summary.get("missing_source_dirs"):
        missing = ", ".join(summary["missing_source_dirs"])
        raise FileNotFoundError(f"memory characterization has missing source dirs: {missing}")
    family_labels = {
        "C-PERSIST/1.55": "After-ingest follow-up reuse",
        "C-VISION/1.30": "Composition/admission boundary",
        "Track-B/1.63": "Measured sparse vision execution",
    }
    lines = [
        r"\begin{table}[H]",
        r"\centering",
        (
            r"\caption{Memory characterization across landed cells. The "
            r"runtime mitigation configures an MLX allocation cap and avoided "
            r"kernel panics in the clean queue, but observed process working-set "
            r"peaks still reached 13.6\,GB.}"
        ),
        r"\label{tab:memory-characterization}",
        r"\small",
        r"\begin{tabularx}{\linewidth}{@{}X r r r X@{}}",
        r"\toprule",
        r"Family & Cells & Max peak & Cells \(>10\)GB & Paper meaning \\",
        r"\midrule",
    ]
    for family, row in summary["by_family"].items():
        label = family_labels.get(family, family)
        lines.append(
            f"{label} & {row['n_cells']} & {row['max_peak_observed_gb']:.2f}\\,GB & "
            f"{row['n_cells_over_10gb']} & observed envelope \\\\"
        )
    lines.extend([r"\bottomrule", r"\end{tabularx}", r"\end{table}"])
    (GENERATED / "tables" / "memory_characterization.tex").write_text("\n".join(lines) + "\n")


def _load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def _median_ratio(rows: list[dict], numerator: str, denominator: str) -> float:
    values = [
        float(row[numerator]) / float(row[denominator])
        for row in rows
        if isinstance(row.get(numerator), (int, float))
        and isinstance(row.get(denominator), (int, float))
        and float(row[denominator]) > 0
    ]
    if not values:
        raise ValueError(f"no ratios for {numerator}/{denominator}")
    values.sort()
    mid = len(values) // 2
    if len(values) % 2:
        return values[mid]
    return (values[mid - 1] + values[mid]) / 2.0


def _median_value(rows: list[dict], key: str) -> float:
    values = [float(row[key]) for row in rows if isinstance(row.get(key), (int, float))]
    if not values:
        raise ValueError(f"no numeric values for {key}")
    values.sort()
    mid = len(values) // 2
    if len(values) % 2:
        return values[mid]
    return (values[mid - 1] + values[mid]) / 2.0


def _scaleout_bundle_snapshot() -> dict[str, object]:
    base = ARTIFACTS / "sam_scaleout_m5_20260429"
    r2 = ARTIFACTS / "sam_scaleout_m5_r2_20260430"
    r2_followup = ARTIFACTS / "sam_scaleout_m5_r2_followup_20260430"

    b0_default = _artifact_json(base / "sam_b0b_cache_correctness_summary.json")
    b0_guard = _artifact_json(r2 / "sam_b0b_cache_correctness_summary.json")
    b0_patched = _artifact_json(
        r2_followup / "sam_b0b_cache_correctness_unguarded_patched_summary.json"
    )
    b0_patched_rows = _load_jsonl(r2_followup / "sam_b0b_cache_correctness_unguarded_patched.jsonl")
    b0_patched_cross_rows = [
        row
        for row in b0_patched_rows
        if row.get("policy") == "prompt_cache_state_cross_turn_chained"
    ]

    prefix8_path = base / "sam_m5_5b_swa_prefix_snapshot.jsonl"
    prefix32_path = base / "sam_m5_5b_swa_prefix_snapshot_32f.jsonl"
    prefix8_summary = _artifact_json(base / "sam_m5_5b_swa_prefix_snapshot_summary.json")
    prefix32_summary = _artifact_json(base / "sam_m5_5b_swa_prefix_snapshot_32f_summary.json")
    prefix8_rows = _load_jsonl(prefix8_path)
    prefix32_rows = _load_jsonl(prefix32_path)

    def _mc_row_count(rows: list[dict]) -> int:
        return sum(
            1
            for row in rows
            if row.get("session_choice") is not None or row.get("baseline_choice") is not None
        )

    b3_path = base / "sam_b3_streaming_baselines.jsonl"
    b3_summary = _artifact_json(base / "sam_b3_streaming_baselines_summary.json")
    b3_rows = _load_jsonl(b3_path)
    by_arm: dict[str, list[dict]] = {}
    for row in b3_rows:
        by_arm.setdefault(str(row["arm"]), []).append(row)
    b3_table = []
    for arm, label in [
        ("low_fps_dense", "low-FPS dense"),
        ("screenshot_polling", "screenshot polling"),
        ("sam_policy", "event-window proxy"),
        ("recency_last_k", "recency last-K"),
    ]:
        rows = by_arm[arm]
        b3_table.append(
            {
                "arm": arm,
                "label": label,
                "n": len(rows),
                "oracle_matches": sum(1 for row in rows if not bool(row["correctness_diff"])),
                "parse_failures": sum(1 for row in rows if bool(row["parse_failure"])),
            }
        )

    b4_summary = _artifact_json(base / "sam_b4_sparse_vit_ceiling_summary.json")
    b4_rows = _load_jsonl(base / "sam_b4_sparse_vit_ceiling.jsonl")
    b4_by_frames: dict[int, list[dict]] = {}
    for row in b4_rows:
        b4_by_frames.setdefault(int(row["prompt_frame_count"]), []).append(row)

    b5_accuracy = _artifact_json(base / "sam_b5_s4_accuracy_1937_summary.json")
    b5_raw = _artifact_json(base / "sam_b5_s4_raw_paired_513_summary.json")

    return {
        "default_cache_path": {
            "n": int(b0_default["n_rows"]),
            "text_diffs": int(b0_default["text_diffs"]),
            "choice_diffs": int(b0_default["choice_diffs"]),
            "correctness_diffs": int(b0_default["correctness_diffs"]),
            "parse_failures": int(b0_default["parse_failures"]),
            "pass": bool(b0_default["pass"]),
            "source": _source_path_label(base / "sam_b0b_cache_correctness_summary.json"),
        },
        "guarded_correctness_control": {
            "n": int(b0_guard["n_rows"]),
            "text_diffs": int(b0_guard["text_diffs"]),
            "choice_diffs": int(b0_guard["choice_diffs"]),
            "correctness_diffs": int(b0_guard["correctness_diffs"]),
            "parse_failures": int(b0_guard["parse_failures"]),
            "pass": bool(b0_guard["pass"]),
            "policy": "full_refill_guard_rotating_kv",
            "source": _source_path_label(r2 / "sam_b0b_cache_correctness_summary.json"),
        },
        "patched_library_closure": {
            "n": int(b0_patched["n_rows"]),
            "text_diffs": int(b0_patched["text_diffs"]),
            "choice_diffs": int(b0_patched["choice_diffs"]),
            "correctness_diffs": int(b0_patched["correctness_diffs"]),
            "parse_failures": int(b0_patched["parse_failures"]),
            "pass": bool(b0_patched["pass"]),
            "policy": "prompt_cache_state_cross_turn_chained",
            "cross_turn_median_speedup": _median_ratio(
                b0_patched_cross_rows, "baseline_elapsed_ms", "elapsed_ms"
            ),
            "cross_turn_median_prefill_ms": _median_value(b0_patched_cross_rows, "prefill_ms"),
            "source_paths": [
                _source_path_label(
                    r2_followup / "sam_b0b_cache_correctness_unguarded_patched_summary.json"
                ),
                _source_path_label(
                    r2_followup / "sam_b0b_cache_correctness_unguarded_patched.jsonl"
                ),
            ],
        },
        "prefix_snapshot": [
            {
                "frames": 8,
                "n": int(prefix8_summary["n_rows"]),
                "choice_diffs": int(prefix8_summary["choice_diffs"]),
                "correctness_diffs": int(prefix8_summary["correctness_diffs"]),
                "text_diffs": int(prefix8_summary["text_diffs"]),
                "parse_failures": int(prefix8_summary["parse_failures"]),
                "mc_rows": _mc_row_count(prefix8_rows),
                "open_ended_rows": len(prefix8_rows) - _mc_row_count(prefix8_rows),
                "median_speedup": _median_ratio(prefix8_rows, "baseline_elapsed_ms", "elapsed_ms"),
                "median_elapsed_s": _median_value(prefix8_rows, "elapsed_ms") / 1000.0,
                "source": _source_path_label(prefix8_path),
            },
            {
                "frames": 32,
                "n": int(prefix32_summary["n_rows"]),
                "choice_diffs": int(prefix32_summary["choice_diffs"]),
                "correctness_diffs": int(prefix32_summary["correctness_diffs"]),
                "text_diffs": int(prefix32_summary["text_diffs"]),
                "parse_failures": int(prefix32_summary["parse_failures"]),
                "mc_rows": _mc_row_count(prefix32_rows),
                "open_ended_rows": len(prefix32_rows) - _mc_row_count(prefix32_rows),
                "median_speedup": _median_ratio(prefix32_rows, "baseline_elapsed_ms", "elapsed_ms"),
                "median_elapsed_s": _median_value(prefix32_rows, "elapsed_ms") / 1000.0,
                "source": _source_path_label(prefix32_path),
            },
        ],
        "streaming_baselines": {
            "summary": {
                "n": int(b3_summary["n_rows"]),
                "choice_diffs": int(b3_summary["choice_diffs"]),
                "correctness_diffs": int(b3_summary["correctness_diffs"]),
                "parse_failures": int(b3_summary["parse_failures"]),
            },
            "arms": b3_table,
            "source": _source_path_label(b3_path),
        },
        "post_vit_hard_prune": {
            "n": int(b4_summary["n_rows"]),
            "choice_diffs": int(b4_summary["choice_diffs"]),
            "correctness_diffs": int(b4_summary["correctness_diffs"]),
            "text_diffs": int(b4_summary["text_diffs"]),
            "parse_failures": int(b4_summary["parse_failures"]),
            "by_frames": [
                {
                    "frames": frames,
                    "n": len(rows),
                    "median_speedup": _median_ratio(rows, "baseline_elapsed_ms", "elapsed_ms"),
                }
                for frames, rows in sorted(b4_by_frames.items())
            ],
            "source": _source_path_label(base / "sam_b4_sparse_vit_ceiling.jsonl"),
        },
        "exactness_export": {
            "accuracy_rows": int(b5_accuracy["n_rows"]),
            "accuracy_correctness_diffs": int(b5_accuracy["correctness_diffs"]),
            "accuracy_parse_failures": int(b5_accuracy["parse_failures"]),
            "raw_rows": int(b5_raw["n_rows"]),
            "raw_text_diffs": int(b5_raw["text_diffs"]),
            "raw_choice_diffs": int(b5_raw["choice_diffs"]),
            "raw_parse_failures": int(b5_raw["parse_failures"]),
            "source_paths": [
                _source_path_label(base / "sam_b5_s4_accuracy_1937_summary.json"),
                _source_path_label(base / "sam_b5_s4_raw_paired_513_summary.json"),
            ],
        },
        "source_paths": [
            _source_path_label(base / "sam_b0b_cache_correctness_summary.json"),
            _source_path_label(r2 / "sam_b0b_cache_correctness_summary.json"),
            _source_path_label(
                r2_followup / "sam_b0b_cache_correctness_unguarded_patched_summary.json"
            ),
            _source_path_label(r2_followup / "sam_b0b_cache_correctness_unguarded_patched.jsonl"),
            _source_path_label(base / "sam_m5_5b_swa_prefix_snapshot_summary.json"),
            _source_path_label(base / "sam_m5_5b_swa_prefix_snapshot_32f_summary.json"),
            _source_path_label(base / "sam_b3_streaming_baselines_summary.json"),
            _source_path_label(base / "sam_b4_sparse_vit_ceiling_summary.json"),
            _source_path_label(base / "sam_b5_s4_accuracy_1937_summary.json"),
            _source_path_label(base / "sam_b5_s4_raw_paired_513_summary.json"),
        ],
    }


def _write_scaleout_bundle_table() -> None:
    snapshot = _scaleout_bundle_snapshot()
    prefix8, prefix32 = snapshot["prefix_snapshot"]
    low_fps = next(
        row for row in snapshot["streaming_baselines"]["arms"] if row["arm"] == "low_fps_dense"
    )
    screenshot = next(
        row for row in snapshot["streaming_baselines"]["arms"] if row["arm"] == "screenshot_polling"
    )
    proxy = next(
        row for row in snapshot["streaming_baselines"]["arms"] if row["arm"] == "sam_policy"
    )
    recency = next(
        row for row in snapshot["streaming_baselines"]["arms"] if row["arm"] == "recency_last_k"
    )
    b4 = snapshot["post_vit_hard_prune"]
    patched = snapshot["patched_library_closure"]
    b4_parts = ", ".join(
        f"{row['frames']}f {row['median_speedup']:.3f}$\\times$" for row in b4["by_frames"]
    )
    lines = [
        r"\begin{table}[H]",
        r"\centering",
        (
            r"\caption{Checked scale-out artifact bundle. These rows make "
            r"native-rate streaming state reuse more concrete, while "
            r"cache correctness, matched baselines, and native mechanism quality "
            r"remain open standardization gates.}"
        ),
        r"\label{tab:scaleout-bundle}",
        r"\scriptsize",
        r"\renewcommand{\arraystretch}{1.16}",
        r"\begin{tabularx}{\linewidth}{@{}p{0.22\linewidth} X p{0.25\linewidth}@{}}",
        r"\toprule",
        r"Probe & Result & Claim status \\",
        r"\midrule",
        (
            "Default 26B cache reuse & "
            f"{snapshot['default_cache_path']['text_diffs']}/"
            f"{snapshot['default_cache_path']['n']} text diffs; "
            f"{snapshot['default_cache_path']['choice_diffs']} choice diffs; "
            f"{snapshot['default_cache_path']['parse_failures']} parse failures; "
            "cross-turn path fails cache-correctness test & "
            "diagnostic boundary; do not promote default cache reuse \\\\"
        ),
        (
            "Correctness guard & "
            f"{snapshot['guarded_correctness_control']['text_diffs']}/"
            f"{snapshot['guarded_correctness_control']['n']} text diffs under "
            "RotatingKV full-refill guard; "
            f"{snapshot['guarded_correctness_control']['parse_failures']} parse failures & "
            "correctness control, not a speedup \\\\"
        ),
        (
            "Patched cache-library closure & "
            f"{patched['text_diffs']}/{patched['n']} text diffs; "
            f"{patched['choice_diffs']} choice diffs; "
            f"{patched['correctness_diffs']} correctness diffs; "
            f"{patched['parse_failures']} matched parse failures; patched path "
            f"refuses unsafe cross-turn trim; cross-turn wall-clock "
            f"{patched['cross_turn_median_speedup']:.2f}$\\times$ vs cold dense, "
            f"median prefill {patched['cross_turn_median_prefill_ms']:.0f} ms & "
            "full-regression correctness closure; not a speedup path \\\\"
        ),
        (
            "26B prefix snapshot & "
            f"8f after warm: {prefix8['median_speedup']:.2f}$\\times$, "
            f"MC choice/correct {prefix8['choice_diffs']}/{prefix8['mc_rows']} / "
            f"{prefix8['correctness_diffs']}/{prefix8['mc_rows']}, "
            f"{prefix8['open_ended_rows']} open-ended equality rows, text diffs "
            f"{prefix8['text_diffs']}/{prefix8['n']}, parse "
            f"{prefix8['parse_failures']}/{prefix8['n']}; "
            f"32f after warm: {prefix32['median_speedup']:.2f}$\\times$, "
            f"MC choice/correct {prefix32['choice_diffs']}/{prefix32['mc_rows']} / "
            f"{prefix32['correctness_diffs']}/{prefix32['mc_rows']}, "
            f"{prefix32['open_ended_rows']} open-ended equality rows, text diffs "
            f"{prefix32['text_diffs']}/{prefix32['n']}, parse "
            f"{prefix32['parse_failures']}/{prefix32['n']} & "
            "positive small-N scale-out C-PERSIST row; excludes warm setup; "
            "wrapper-specific and not byte-identical \\\\"
        ),
        (
            "Fixed-evidence stream baselines & "
            f"low-FPS dense {low_fps['oracle_matches']}/{low_fps['n']} beats "
            f"screenshot {screenshot['oracle_matches']}/{screenshot['n']}, "
            f"event-window proxy {proxy['oracle_matches']}/{proxy['n']}, "
            f"recency {recency['oracle_matches']}/{recency['n']} & baseline pressure; "
            "throughput axis remains separate \\\\"
        ),
        (
            "Post-vision-tower hard prune & "
            f"{b4_parts}; text diffs {b4['text_diffs']}/{b4['n']}; "
            "timing-only descriptive prompts & overhead boundary; no correctness gate; "
            "not real sparse vision-tower speedup \\\\"
        ),
        (
            "Sparse exactness export & "
            "zero correctness delta on "
            f"{snapshot['exactness_export']['accuracy_rows']:,} "
            f"logged rows; byte-identical raw-paired text on "
            f"{snapshot['exactness_export']['raw_rows']} rows & denominator-safe "
            "artifact harmonization \\\\"
        ),
        r"\bottomrule",
        r"\end{tabularx}",
        r"\end{table}",
    ]
    (GENERATED / "tables" / "scaleout_bundle_status.tex").write_text("\n".join(lines) + "\n")
    (GENERATED / "data" / "scaleout_bundle_snapshot.json").write_text(
        json.dumps(snapshot, indent=2, sort_keys=True) + "\n"
    )


def _write_build_meta(primary: dict[str, str]) -> None:
    lines = [
        f"\\newcommand{{\\PrimaryRepoSHA}}{{{_short_sha(primary['sha'])}}}",
        f"\\newcommand{{\\PrimaryRepoCommitDate}}{{{primary['commit_date']}}}",
        r"\newcommand{\UpstreamRepoSHA}{not used}",
        r"\newcommand{\UpstreamRepoCommitDate}{not used}",
        (
            "\\newcommand{\\ScaleoutRepoSHA}{"
            f"checked in primary repo at {_short_sha(primary['sha'])}"
            "}"
        ),
        f"\\newcommand{{\\ScaleoutRepoCommitDate}}{{{primary['commit_date']}}}",
    ]
    (GENERATED / "tex" / "build_meta.tex").write_text("\n".join(lines) + "\n")


def _write_repo_provenance_table(primary: dict[str, str]) -> None:
    lines = [
        r"\begin{table}[H]",
        r"\centering",
        (
            r"\caption{Repo provenance captured by the manuscript sync step. "
            r"Regenerate from a clean release tag for the frozen artifact "
            r"bundle.}"
        ),
        r"\label{tab:repo-provenance}",
        r"\begin{tabular}{lll}",
        r"\toprule",
        r"Repo & Commit & Commit date \\",
        r"\midrule",
        f"codec-through & {_short_sha(primary['sha'], 12)} & {primary['commit_date']} \\\\",
        (
            "scale-out checked artifacts & "
            f"primary repo {_short_sha(primary['sha'], 12)} & {primary['commit_date']} \\\\"
        ),
        r"\bottomrule",
        r"\end{tabular}",
        r"\end{table}",
    ]
    (GENERATED / "tables" / "repo_provenance.tex").write_text("\n".join(lines) + "\n")


def main() -> int:
    _ensure_dirs()
    _run_auxiliary_table_builders()
    snapshot = _lane_a_snapshot()
    _render_lane_a_figure(snapshot)
    _write_lane_a_table(snapshot)
    headline_snapshot = _headline_snapshot()
    _render_regime_overview_figure(headline_snapshot)
    _render_headline_figure(headline_snapshot)
    _write_headline_table(headline_snapshot)
    _write_measured_sparse_execution_tables(headline_snapshot)
    _write_c_persist_repair_table(headline_snapshot)
    _write_c_persist_sampler_table()
    _write_c_persist_seed_sweep_table()
    _write_c_persist_many_turn_table()
    _write_memory_characterization_table()
    _write_scaleout_bundle_table()
    _render_c_persist_timeline_figure()
    qwen_bridge_snapshot = _qwen_bridge_boundary_snapshot()
    _write_qwen_bridge_boundary_table(qwen_bridge_snapshot)
    paired_drift_snapshot = _paired_drift_snapshot()
    _write_paired_drift_table(paired_drift_snapshot)
    _sync_curated_paper_figures()
    for path in (GENERATED / "data").glob("*.json"):
        _validate_source_paths(_load_json(path), context=path.relative_to(REPO_ROOT).as_posix())
    _run_artifact_integrity()
    primary = _git_info(REPO_ROOT)
    _write_build_meta(primary)
    _write_repo_provenance_table(primary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
