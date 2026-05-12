#!/usr/bin/env python3
"""Statistical audit for OV-6 Track B codec-grid sparse vision.

Reads existing Qwen Track B artifacts and emits a compact JSON/Markdown
summary with Wilson intervals, paired McNemar tests, and codec-extraction
overhead. This is CPU-only and does not load any model.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.analyze_ov3_statistics import mcnemar_exact, wilson_ci  # noqa: E402

DEFAULT_ROOT = Path("research/experiments/2026/artifacts")
DEFAULT_OUT = DEFAULT_ROOT / "onevision_vlmaxxing_plan" / "ov6_track_b_statistical_audit.json"


@dataclass(frozen=True, slots=True)
class ArmSpec:
    label: str
    path: Path
    kind: str


@dataclass(frozen=True, slots=True)
class CellSpec:
    label: str
    keep_rate: float
    layer: int
    arms: tuple[ArmSpec, ...]
    dense_path: Path | None = None
    compare_to: str = "magnitude_norm"
    compare_to_random: str | None = None


def _default_cells(root: Path) -> tuple[CellSpec, ...]:
    n57 = root / "phase1_51V_ov6_n57"
    kr070 = root / "phase1_51V_ov6_n57_kr070_l2"
    l8 = root / "phase1_51V_ov6_n57_kr050_l8"
    return (
        CellSpec(
            label="kr0.5_layer2_n57",
            keep_rate=0.5,
            layer=2,
            arms=(
                ArmSpec("dense", n57 / "dense", "dense"),
                ArmSpec("magnitude_norm", n57 / "magnitude_norm_kr050", "baseline"),
                ArmSpec("uniform_random", n57 / "uniform_random_kr050", "random"),
                ArmSpec("codec_novel_coded", n57 / "codec_novel_coded_kr050", "codec"),
                ArmSpec("codec_motion", n57 / "codec_motion_kr050", "codec"),
                ArmSpec("codec_residual", n57 / "codec_residual_kr050", "codec"),
            ),
            compare_to="magnitude_norm",
            compare_to_random="uniform_random",
        ),
        CellSpec(
            label="kr0.7_layer2_n57",
            keep_rate=0.7,
            layer=2,
            dense_path=n57 / "dense",
            arms=(
                ArmSpec("magnitude_norm", kr070 / "magnitude_norm", "baseline"),
                ArmSpec("codec_novel_coded", kr070 / "codec_novel_coded", "codec"),
                ArmSpec("codec_motion", kr070 / "codec_motion", "codec"),
                ArmSpec("codec_residual", kr070 / "codec_residual", "codec"),
            ),
            compare_to="magnitude_norm",
        ),
        CellSpec(
            label="kr0.5_layer8_n57",
            keep_rate=0.5,
            layer=8,
            dense_path=n57 / "dense",
            arms=(
                ArmSpec("magnitude_norm", l8 / "magnitude_norm", "baseline"),
                ArmSpec("codec_novel_coded", l8 / "codec_novel_coded", "codec"),
                ArmSpec("codec_motion", l8 / "codec_motion", "codec"),
                ArmSpec("codec_residual", l8 / "codec_residual", "codec"),
            ),
            compare_to="magnitude_norm",
        ),
    )


def _load_summary(path: Path) -> dict[str, Any]:
    summary_path = path / "summary.json"
    if not summary_path.exists():
        raise FileNotFoundError(f"missing summary: {summary_path}")
    payload = json.loads(summary_path.read_text())
    if not isinstance(payload, dict):
        raise ValueError(f"summary is not an object: {summary_path}")
    return cast(dict[str, Any], payload)


def _load_results(path: Path) -> dict[str, dict[str, Any]]:
    results_path = path / "results.jsonl"
    if not results_path.exists():
        raise FileNotFoundError(f"missing results: {results_path}")
    rows: dict[str, dict[str, Any]] = {}
    with results_path.open() as handle:
        for line in handle:
            payload = json.loads(line)
            item_id = str(payload["item_id"])
            if item_id in rows:
                raise ValueError(f"duplicate item_id {item_id} in {results_path}")
            rows[item_id] = payload
    return rows


def _prop(successes: int, n: int) -> dict[str, Any]:
    lo, hi = wilson_ci(successes, n)
    return {
        "successes": successes,
        "n": n,
        "rate": successes / n if n else 0.0,
        "wilson_95_ci": [round(lo, 4), round(hi, 4)],
    }


def _arm_summary(spec: ArmSpec) -> dict[str, Any]:
    summary = _load_summary(spec.path)
    rows = _load_results(spec.path)
    n = len(rows)
    correct = sum(1 for row in rows.values() if bool(row["correct"]))
    codec_extract = summary.get("codec_extract_mean_s_per_item")
    e2e_ms = float(summary["mean_dense_end_to_end_ms"])
    net_e2e_ms = e2e_ms + (float(codec_extract) * 1000.0 if codec_extract is not None else 0.0)
    return {
        "label": spec.label,
        "kind": spec.kind,
        "path": str(spec.path),
        "n_items": n,
        "accuracy": _prop(correct, n),
        "parse_failures": sum(1 for row in rows.values() if bool(row["parse_failure"])),
        "mean_vision_ms": float(summary["mean_dense_vision_ms"]),
        "mean_e2e_ms_excluding_codec_extract": e2e_ms,
        "mean_e2e_ms_including_codec_extract": net_e2e_ms,
        "codec_extract_mean_s_per_item": codec_extract,
        "effective_keep_rate": summary.get("mean_effective_keep_rate"),
    }


def _paired(a: dict[str, dict[str, Any]], b: dict[str, dict[str, Any]]) -> dict[str, Any]:
    if set(a) != set(b):
        missing_a = sorted(set(b) - set(a))
        missing_b = sorted(set(a) - set(b))
        raise ValueError(f"paired item mismatch: missing_a={missing_a} missing_b={missing_b}")
    fixed = 0
    broken = 0
    choice_agree = 0
    for item_id in sorted(a):
        a_row = a[item_id]
        b_row = b[item_id]
        a_correct = bool(a_row["correct"])
        b_correct = bool(b_row["correct"])
        if a_correct and not b_correct:
            fixed += 1
        elif b_correct and not a_correct:
            broken += 1
        if a_row.get("choice_index") == b_row.get("choice_index"):
            choice_agree += 1
    n = len(a)
    return {
        "a_correct_b_wrong": fixed,
        "a_wrong_b_correct": broken,
        "concordant_correctness": n - fixed - broken,
        "n": n,
        "mcnemar_exact_p_two_sided": round(mcnemar_exact(fixed, broken), 4),
        "choice_agreement": _prop(choice_agree, n),
    }


def _analyze_cell(cell: CellSpec) -> dict[str, Any]:
    arm_summaries = {arm.label: _arm_summary(arm) for arm in cell.arms}
    arm_rows = {arm.label: _load_results(arm.path) for arm in cell.arms}
    dense_rows = _load_results(cell.dense_path) if cell.dense_path is not None else None
    if dense_rows is None and "dense" in arm_rows:
        dense_rows = arm_rows["dense"]

    comparisons: dict[str, Any] = {}
    if cell.compare_to in arm_rows:
        baseline_rows = arm_rows[cell.compare_to]
        for label, rows in arm_rows.items():
            if label == cell.compare_to or label == "dense":
                continue
            comparisons[f"{label}_vs_{cell.compare_to}"] = _paired(rows, baseline_rows)
    if cell.compare_to_random and cell.compare_to_random in arm_rows:
        random_rows = arm_rows[cell.compare_to_random]
        for label, rows in arm_rows.items():
            if label in {cell.compare_to_random, "dense"}:
                continue
            comparisons[f"{label}_vs_{cell.compare_to_random}"] = _paired(rows, random_rows)
    if dense_rows is not None:
        for label, rows in arm_rows.items():
            if label == "dense":
                continue
            comparisons[f"{label}_vs_dense"] = _paired(rows, dense_rows)

    return {
        "label": cell.label,
        "keep_rate": cell.keep_rate,
        "layer": cell.layer,
        "arms": arm_summaries,
        "paired_comparisons": comparisons,
    }


def _markdown(payload: dict[str, Any]) -> str:
    lines = ["# OV-6 Track B Statistical Audit", ""]
    for cell in payload["cells"]:
        lines.append(f"## {cell['label']}")
        lines.append("")
        lines.append(
            "| arm | acc | Wilson 95% CI | vision_ms | e2e_ms | e2e+codec_ms | codec_extract_s |"
        )
        lines.append("| --- | ---: | --- | ---: | ---: | ---: | ---: |")
        for arm in cell["arms"].values():
            acc = arm["accuracy"]
            ci = acc["wilson_95_ci"]
            codec_extract = arm["codec_extract_mean_s_per_item"]
            lines.append(
                "| "
                + " | ".join(
                    [
                        arm["label"],
                        f"{acc['successes']}/{acc['n']} = {acc['rate']:.3f}",
                        f"[{ci[0]:.3f}, {ci[1]:.3f}]",
                        f"{arm['mean_vision_ms']:.0f}",
                        f"{arm['mean_e2e_ms_excluding_codec_extract']:.0f}",
                        f"{arm['mean_e2e_ms_including_codec_extract']:.0f}",
                        (f"{float(codec_extract):.2f}" if codec_extract is not None else "-"),
                    ]
                )
                + " |"
            )
        lines.append("")
        lines.append("| comparison | fixed | broken | McNemar p | choice agreement |")
        lines.append("| --- | ---: | ---: | ---: | --- |")
        for name, comparison in cell["paired_comparisons"].items():
            choice = comparison["choice_agreement"]
            lines.append(
                "| "
                + " | ".join(
                    [
                        name,
                        str(comparison["a_correct_b_wrong"]),
                        str(comparison["a_wrong_b_correct"]),
                        f"{comparison['mcnemar_exact_p_two_sided']:.4f}",
                        (f"{choice['successes']}/{choice['n']} = {choice['rate']:.3f}"),
                    ]
                )
                + " |"
            )
        lines.append("")
    lines.append("## Interpretation Guardrails")
    lines.append("")
    lines.append(
        "- N=57 Track B cells are reproduced here, but codec-over-magnitude "
        "superiority is point-estimate evidence unless a paired test gates."
    )
    lines.append(
        "- `mean_e2e_ms` excludes separate PyAV codec extraction; "
        "`e2e+codec_ms` includes the repo-local extraction overhead."
    )
    lines.append(
        "- C-PERSIST composition must use setup-inclusive accounting and must "
        "not multiply first-query sparse-vision ratios by follow-up ratios."
    )
    return "\n".join(lines) + "\n"


def build_payload(root: Path) -> dict[str, Any]:
    cells = [_analyze_cell(cell) for cell in _default_cells(root)]
    return {
        "phase": "OV-6",
        "model": "Qwen2.5-VL-7B-Instruct-4bit",
        "benchmark": "VideoMME short locally-present N=57",
        "frame_count": 8,
        "status": "reproduced here",
        "cells": cells,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    payload = build_payload(args.root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    md_path = args.output.with_suffix(".md")
    md_path.write_text(_markdown(payload))
    print(args.output)
    print(md_path)


if __name__ == "__main__":
    main()
