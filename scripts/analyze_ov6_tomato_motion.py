#!/usr/bin/env python3
"""Statistical audit for the OV-6 Qwen TOMATO motion replication."""

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

DEFAULT_ROOT = Path("research/experiments/2026/artifacts/phase1_51V_ov6_tomato_motion_kr070_l2")
ARMS = (
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
        raise ValueError(f"expected object JSON at {path}")
    return cast(dict[str, Any], payload)


def _load_rows(path: Path) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    with path.open() as handle:
        for line in handle:
            payload = json.loads(line)
            item_id = str(payload["item_id"])
            if item_id in rows:
                raise ValueError(f"duplicate item_id {item_id} in {path}")
            rows[item_id] = cast(dict[str, Any], payload)
    return rows


def _accuracy(rows: dict[str, dict[str, Any]]) -> dict[str, Any]:
    n = len(rows)
    correct = sum(1 for row in rows.values() if bool(row["correct"]))
    lo, hi = wilson_ci(correct, n)
    return {
        "correct": correct,
        "n": n,
        "rate": correct / n if n else 0.0,
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
        if cand_correct and not base_correct:
            fixes += 1
        elif base_correct and not cand_correct:
            breaks += 1
        if cand.get("choice_index") == base.get("choice_index"):
            choice_agree += 1
    n = len(candidate)
    agree_lo, agree_hi = wilson_ci(choice_agree, n)
    return {
        "candidate_correct_baseline_wrong": fixes,
        "candidate_wrong_baseline_correct": breaks,
        "mcnemar_exact_p_two_sided": round(mcnemar_exact(fixes, breaks), 4),
        "choice_agreement": {
            "correct": choice_agree,
            "n": n,
            "rate": choice_agree / n if n else 0.0,
            "wilson_95_ci": [round(agree_lo, 4), round(agree_hi, 4)],
        },
    }


def analyze(root: Path) -> dict[str, Any]:
    rows = {arm: _load_rows(root / arm / "results.jsonl") for arm in ARMS}
    summaries = {arm: _load_json(root / arm / "summary.json") for arm in ARMS}
    arm_payloads: dict[str, Any] = {}
    for arm in ARMS:
        summary = summaries[arm]
        codec_extract = summary.get("codec_extract_mean_s_per_item")
        e2e_ms = float(summary["mean_dense_end_to_end_ms"])
        arm_payloads[arm] = {
            "summary_path": str(root / arm / "summary.json"),
            "accuracy": _accuracy(rows[arm]),
            "parse_failures": sum(1 for row in rows[arm].values() if bool(row["parse_failure"])),
            "mean_vision_ms": float(summary["mean_dense_vision_ms"]),
            "mean_e2e_ms_excluding_codec_extract": e2e_ms,
            "mean_e2e_ms_including_codec_extract": (
                e2e_ms + float(codec_extract) * 1000.0 if codec_extract is not None else e2e_ms
            ),
            "codec_extract_mean_s_per_item": codec_extract,
        }

    comparisons: dict[str, Any] = {}
    for arm in ARMS:
        if arm not in {"dense", "magnitude_norm"}:
            comparisons[f"{arm}_vs_magnitude_norm"] = _paired(rows[arm], rows["magnitude_norm"])
        if arm != "dense":
            comparisons[f"{arm}_vs_dense"] = _paired(rows[arm], rows["dense"])

    codec_novel_correct = arm_payloads["codec_novel_coded"]["accuracy"]["correct"]
    magnitude_correct = arm_payloads["magnitude_norm"]["accuracy"]["correct"]
    return {
        "phase": "OV-6",
        "question": "Does Qwen Track B codec_novel_coded transfer to TOMATO motion?",
        "root": str(root),
        "gate": (
            "codec_novel_coded >= magnitude_norm by point estimate, with Wilson "
            "intervals and paired tests reported."
        ),
        "falsification": "magnitude_norm exceeds codec_novel_coded by at least 3 items.",
        "arms": arm_payloads,
        "paired_comparisons": comparisons,
        "gate_status": {
            "codec_novel_coded_ge_magnitude_norm": codec_novel_correct >= magnitude_correct,
            "codec_novel_coded_correct": codec_novel_correct,
            "magnitude_norm_correct": magnitude_correct,
            "falsified": magnitude_correct - codec_novel_correct >= 3,
            "interpretation": "boundary: all sparse arms remain near the chance floor",
        },
    }


def _markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# OV-6 Qwen TOMATO Motion Statistical Audit",
        "",
        f"Gate: {payload['gate']}",
        f"Falsification: {payload['falsification']}",
        "",
        "| arm | accuracy | Wilson 95% CI | vision_ms | e2e_ms | e2e+codec_ms |",
        "| --- | ---: | --- | ---: | ---: | ---: |",
    ]
    for arm, arm_payload in payload["arms"].items():
        acc = arm_payload["accuracy"]
        ci = acc["wilson_95_ci"]
        lines.append(
            "| "
            + " | ".join(
                [
                    arm,
                    f"{acc['correct']}/{acc['n']} = {acc['rate']:.3f}",
                    f"[{ci[0]:.3f}, {ci[1]:.3f}]",
                    f"{arm_payload['mean_vision_ms']:.0f}",
                    f"{arm_payload['mean_e2e_ms_excluding_codec_extract']:.0f}",
                    f"{arm_payload['mean_e2e_ms_including_codec_extract']:.0f}",
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
                    f"{choice['correct']}/{choice['n']} = {choice['rate']:.3f}",
                ]
            )
            + " |"
        )
    status = payload["gate_status"]
    lines.extend(
        [
            "",
            (
                "Point-estimate gate: "
                f"codec_novel_coded {status['codec_novel_coded_correct']} correct vs "
                f"magnitude_norm {status['magnitude_norm_correct']} correct."
            ),
            f"Falsified: {status['falsified']}",
            f"Interpretation: {status['interpretation']}.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--out-json", type=Path, default=None)
    parser.add_argument("--out-md", type=Path, default=None)
    args = parser.parse_args()

    payload = analyze(args.root)
    out_json = args.out_json or args.root / "statistical_audit.json"
    out_md = args.out_md or args.root / "statistical_audit.md"
    out_json.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    out_md.write_text(_markdown(payload))
    print(out_json)
    print(out_md)


if __name__ == "__main__":
    main()
