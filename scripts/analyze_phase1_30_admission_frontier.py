#!/usr/bin/env python3
"""Analyze the session-level Q0-admission frontier between 1.30 and 1.30W."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from codec_through.phase1_30_admission_frontier import analyze_admission_frontier


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--pruned-dir",
        type=Path,
        default=Path("research/experiments/2026/artifacts/phase1_30_sam_streaming"),
    )
    parser.add_argument(
        "--dense-dir",
        type=Path,
        default=Path(
            "research/experiments/2026/artifacts/phase1_30W_q0_dense_followup_pruned_full"
        ),
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    analysis = analyze_admission_frontier(
        pruned_streaming_jsonl=args.pruned_dir / "streaming.jsonl",
        pruned_cold_jsonl=args.pruned_dir / "cold.jsonl",
        dense_streaming_jsonl=args.dense_dir / "streaming_q0_dense_followup_pruned_off.jsonl",
        dense_cold_jsonl=args.dense_dir / "cold_dense.jsonl",
    )
    args.output.write_text(json.dumps(analysis, indent=2) + "\n")

    print(f"[1.30X] wrote {args.output}")
    for result in analysis["policy_results"]:
        if result["deployable"]:
            print(
                f"[1.30X] {result['name']}: "
                f"delta={result['accuracy_delta']:+.4f} "
                f"speedup={result['speedup_cold_over_stream']:.4f}x "
                f"rescue={result['rescue_pass']}"
            )
    for key, point in analysis["exact_frontier"].items():
        if point is None:
            print(f"[1.30X] {key}: none")
            continue
        print(
            f"[1.30X] {key}: delta={point['accuracy_delta']:+.4f} "
            f"speedup={point['speedup_cold_over_stream']:.4f}x "
            f"rescue={point['rescue_pass']}"
        )


if __name__ == "__main__":
    main()
