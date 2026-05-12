#!/usr/bin/env python3
"""Analyze OV-6 Qwen random-baseline multi-seed results.

The experiment asks whether the kr=0.5/layer=2 random-over-magnitude point
estimate is seed-stable. It compares every ``uniform_random_seed*`` arm under a
root directory against the sibling ``magnitude_norm`` arm.
"""

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

DEFAULT_ROOT = Path("research/experiments/2026/artifacts/phase1_51V_ov6_random_multiseed")


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
    for item_id in sorted(candidate):
        cand_correct = bool(candidate[item_id]["correct"])
        base_correct = bool(baseline[item_id]["correct"])
        if cand_correct and not base_correct:
            fixes += 1
        elif base_correct and not cand_correct:
            breaks += 1
    return {
        "random_correct_magnitude_wrong": fixes,
        "random_wrong_magnitude_correct": breaks,
        "mcnemar_exact_p_two_sided": round(mcnemar_exact(fixes, breaks), 4),
    }


def analyze(root: Path) -> dict[str, Any]:
    magnitude_dir = root / "magnitude_norm"
    if not (magnitude_dir / "results.jsonl").exists():
        raise FileNotFoundError(f"missing magnitude baseline under {magnitude_dir}")
    magnitude_rows = _load_rows(magnitude_dir / "results.jsonl")
    magnitude_summary = _load_json(magnitude_dir / "summary.json")

    random_dirs = sorted(path for path in root.glob("uniform_random_seed*") if path.is_dir())
    if not random_dirs:
        raise FileNotFoundError(f"no uniform_random_seed* arms under {root}")

    seed_rows: list[dict[str, Any]] = []
    seeds_random_ge_magnitude = 0
    falsifying_seeds: list[str] = []
    magnitude_correct = int(_accuracy(magnitude_rows)["correct"])
    for random_dir in random_dirs:
        rows = _load_rows(random_dir / "results.jsonl")
        summary = _load_json(random_dir / "summary.json")
        acc = _accuracy(rows)
        paired = _paired(rows, magnitude_rows)
        if int(acc["correct"]) >= magnitude_correct:
            seeds_random_ge_magnitude += 1
        if magnitude_correct - int(acc["correct"]) >= 3:
            falsifying_seeds.append(random_dir.name)
        seed_rows.append(
            {
                "arm": random_dir.name,
                "summary_path": str(random_dir / "summary.json"),
                "accuracy": acc,
                "mean_vision_ms": summary.get("mean_dense_vision_ms"),
                "mean_e2e_ms": summary.get("mean_dense_end_to_end_ms"),
                "paired_vs_magnitude": paired,
            }
        )

    magnitude_acc = _accuracy(magnitude_rows)
    return {
        "phase": "OV-6",
        "question": "Is uniform_random >= magnitude_norm at kr=0.5/layer=2 seed-stable?",
        "root": str(root),
        "gate": "All tested random seeds must be >= magnitude_norm by point estimate.",
        "falsification": "Any seed where magnitude_norm exceeds random by at least 3 items.",
        "magnitude_norm": {
            "summary_path": str(magnitude_dir / "summary.json"),
            "accuracy": magnitude_acc,
            "mean_vision_ms": magnitude_summary.get("mean_dense_vision_ms"),
            "mean_e2e_ms": magnitude_summary.get("mean_dense_end_to_end_ms"),
        },
        "random_seeds": seed_rows,
        "gate_status": {
            "seeds_random_ge_magnitude": seeds_random_ge_magnitude,
            "n_seeds": len(seed_rows),
            "passes_point_estimate_gate": seeds_random_ge_magnitude == len(seed_rows),
            "falsifying_seeds": falsifying_seeds,
        },
    }


def _markdown(payload: dict[str, Any]) -> str:
    mag = payload["magnitude_norm"]["accuracy"]
    lines = [
        "# OV-6 Qwen Random Multi-Seed Audit",
        "",
        f"Gate: {payload['gate']}",
        f"Falsification: {payload['falsification']}",
        "",
        f"Magnitude baseline: {mag['correct']}/{mag['n']} = {mag['rate']:.3f}",
        "",
        "| random arm | accuracy | Wilson 95% CI | fixes | breaks | McNemar p |",
        "| --- | ---: | --- | ---: | ---: | ---: |",
    ]
    for row in payload["random_seeds"]:
        acc = row["accuracy"]
        paired = row["paired_vs_magnitude"]
        ci = acc["wilson_95_ci"]
        lines.append(
            "| "
            + " | ".join(
                [
                    row["arm"],
                    f"{acc['correct']}/{acc['n']} = {acc['rate']:.3f}",
                    f"[{ci[0]:.3f}, {ci[1]:.3f}]",
                    str(paired["random_correct_magnitude_wrong"]),
                    str(paired["random_wrong_magnitude_correct"]),
                    f"{paired['mcnemar_exact_p_two_sided']:.4f}",
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
                f"{status['seeds_random_ge_magnitude']}/{status['n_seeds']} seeds "
                "random >= magnitude_norm."
            ),
            f"Falsifying seeds: {status['falsifying_seeds']}",
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
    out_json = args.out_json or args.root / "random_multiseed_summary.json"
    out_md = args.out_md or args.root / "random_multiseed_summary.md"
    out_json.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    out_md.write_text(_markdown(payload))
    print(out_json)
    print(out_md)


if __name__ == "__main__":
    main()
