#!/usr/bin/env python3
"""Generic paired audit for a Track B arm directory set."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, cast

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.analyze_ov3_statistics import mcnemar_exact, wilson_ci  # noqa: E402

DEFAULT_ARMS = (
    "dense",
    "magnitude_norm",
    "uniform_random",
    "codec_novel_coded",
    "codec_motion",
    "codec_residual",
)


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text())
    if not isinstance(payload, dict):
        raise ValueError(f"expected object JSON: {path}")
    return cast(dict[str, Any], payload)


def _load_rows(path: Path) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    with path.open() as handle:
        for line in handle:
            payload = json.loads(line)
            if not isinstance(payload, dict):
                raise ValueError(f"expected object JSONL row: {path}")
            item_id = str(payload["item_id"])
            if item_id in rows:
                raise ValueError(f"duplicate item_id {item_id} in {path}")
            rows[item_id] = cast(dict[str, Any], payload)
    return rows


def _prop(successes: int, n: int) -> dict[str, Any]:
    lo, hi = wilson_ci(successes, n)
    return {
        "successes": successes,
        "n": n,
        "rate": successes / n if n else 0.0,
        "wilson_95_ci": [round(lo, 4), round(hi, 4)],
    }


def _paired(
    candidate: dict[str, dict[str, Any]],
    baseline: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    if set(candidate) != set(baseline):
        raise ValueError(
            "paired item mismatch: "
            f"candidate_only={sorted(set(candidate) - set(baseline))[:5]} "
            f"baseline_only={sorted(set(baseline) - set(candidate))[:5]}"
        )
    fixes = 0
    breaks = 0
    choice_agree = 0
    for item_id in sorted(candidate):
        cand = candidate[item_id]
        base = baseline[item_id]
        cand_correct = bool(cand["correct"])
        base_correct = bool(base["correct"])
        fixes += int(cand_correct and not base_correct)
        breaks += int(base_correct and not cand_correct)
        choice_agree += int(cand.get("choice_index") == base.get("choice_index"))
    n = len(candidate)
    return {
        "candidate_correct_baseline_wrong": fixes,
        "candidate_wrong_baseline_correct": breaks,
        "mcnemar_exact_p_two_sided": round(mcnemar_exact(fixes, breaks), 4),
        "choice_agreement": _prop(choice_agree, n),
    }


def _arm(root: Path, name: str) -> dict[str, Any]:
    summary = _load_json(root / name / "summary.json")
    rows = _load_rows(root / name / "results.jsonl")
    correct = sum(1 for row in rows.values() if bool(row["correct"]))
    e2e = float(summary["mean_dense_end_to_end_ms"])
    e2e_with_score = float(summary.get("mean_end_to_end_including_codec_score_runtime_ms", e2e))
    return {
        "summary_path": str(root / name / "summary.json"),
        "n_items": len(rows),
        "accuracy": _prop(correct, len(rows)),
        "parse_failures": sum(1 for row in rows.values() if bool(row.get("parse_failure", False))),
        "mean_vision_ms": float(summary["mean_dense_vision_ms"]),
        "mean_e2e_ms_excluding_score_runtime": e2e,
        "mean_e2e_ms_including_score_runtime": e2e_with_score,
        "codec_score_runtime_source": summary.get("codec_score_runtime_source"),
        "codec_extract_mean_s_per_item": summary.get("codec_extract_mean_s_per_item"),
        "codec_sidecar_load_mean_s_per_item": summary.get("codec_sidecar_load_mean_s_per_item"),
        "effective_keep_rate": summary.get("mean_effective_keep_rate"),
    }


def analyze(root: Path, *, arms: tuple[str, ...]) -> dict[str, Any]:
    rows = {arm: _load_rows(root / arm / "results.jsonl") for arm in arms}
    payload_arms = {arm: _arm(root, arm) for arm in arms}
    comparisons: dict[str, Any] = {}
    for baseline in ("magnitude_norm", "uniform_random", "dense"):
        if baseline not in rows:
            continue
        for arm in arms:
            if arm == baseline:
                continue
            comparisons[f"{arm}_vs_{baseline}"] = _paired(rows[arm], rows[baseline])
    return {
        "schema": "track_b_arm_set_audit_v1",
        "root": str(root),
        "arms": payload_arms,
        "paired_comparisons": comparisons,
    }


def _markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Track B Arm Set Audit",
        "",
        "| arm | accuracy | Wilson 95% CI | vision_ms | e2e_ms | e2e+score_ms | score runtime |",
        "| --- | ---: | --- | ---: | ---: | ---: | --- |",
    ]
    for arm, value in payload["arms"].items():
        acc = value["accuracy"]
        ci = acc["wilson_95_ci"]
        score_runtime = "-"
        if value["codec_extract_mean_s_per_item"] is not None:
            score_runtime = f"live_pyav {float(value['codec_extract_mean_s_per_item']):.2f}s"
        elif value["codec_sidecar_load_mean_s_per_item"] is not None:
            score_runtime = f"sidecar {float(value['codec_sidecar_load_mean_s_per_item']):.4f}s"
        elif value["codec_score_runtime_source"] is not None:
            score_runtime = str(value["codec_score_runtime_source"])
        lines.append(
            "| "
            + " | ".join(
                [
                    arm,
                    f"{acc['successes']}/{acc['n']} = {acc['rate']:.3f}",
                    f"[{ci[0]:.3f}, {ci[1]:.3f}]",
                    f"{value['mean_vision_ms']:.0f}",
                    f"{value['mean_e2e_ms_excluding_score_runtime']:.0f}",
                    f"{value['mean_e2e_ms_including_score_runtime']:.0f}",
                    score_runtime,
                ]
            )
            + " |"
        )
    lines.extend(["", "| comparison | fixes | breaks | McNemar p | choice agreement |"])
    lines.append("| --- | ---: | ---: | ---: | --- |")
    for name, comparison in payload["paired_comparisons"].items():
        choice = comparison["choice_agreement"]
        lines.append(
            "| "
            + " | ".join(
                [
                    name,
                    str(comparison["candidate_correct_baseline_wrong"]),
                    str(comparison["candidate_wrong_baseline_correct"]),
                    f"{comparison['mcnemar_exact_p_two_sided']:.4f}",
                    f"{choice['successes']}/{choice['n']} = {choice['rate']:.3f}",
                ]
            )
            + " |"
        )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--arms", nargs="+", default=list(DEFAULT_ARMS))
    parser.add_argument("--out-json", type=Path, default=None)
    parser.add_argument("--out-md", type=Path, default=None)
    args = parser.parse_args()

    payload = analyze(args.root, arms=tuple(args.arms))
    out_json = args.out_json or args.root / "track_b_arm_set_audit.json"
    out_md = args.out_md or args.root / "track_b_arm_set_audit.md"
    out_json.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    out_md.write_text(_markdown(payload))
    print(out_json)
    print(out_md)


if __name__ == "__main__":
    main()
