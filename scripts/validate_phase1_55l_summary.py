#!/usr/bin/env python3
"""Validate an existing 1.55L summary against the requested run grid."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _parse_csv(value: str) -> list[str]:
    return [part.strip() for part in value.split(",") if part.strip()]


def _parse_int_csv(value: str) -> list[int]:
    return [int(part) for part in _parse_csv(value)]


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--video-ids", required=True)
    parser.add_argument("--turn-counts", required=True)
    parser.add_argument("--policies", required=True)
    parser.add_argument("--prompt-variant-mode")
    args = parser.parse_args()

    if not args.summary.exists():
        print(f"[1.55L] no summary found at {args.summary}")
        return 1

    summary = _load(args.summary)
    mismatches: list[str] = []
    if summary.get("video_ids") != _parse_csv(args.video_ids):
        mismatches.append("video_ids")
    if summary.get("turn_counts") != _parse_int_csv(args.turn_counts):
        mismatches.append("turn_counts")
    if summary.get("policies") != _parse_csv(args.policies):
        mismatches.append("policies")
    if args.prompt_variant_mode and summary.get("prompt_variant_mode") != args.prompt_variant_mode:
        mismatches.append("prompt_variant_mode")
    for gate in (
        "pass_complete_row_counts",
        "pass_complete_cells",
        "pass_complete_chain_counts",
        "pass_complete_turn_coverage",
        "pass_complete_policy_horizon_grid",
    ):
        if not summary.get(gate):
            mismatches.append(gate)
    if args.prompt_variant_mode and not summary.get("pass_prompt_hash_pairing"):
        mismatches.append("pass_prompt_hash_pairing")

    if mismatches:
        print("[1.55L] existing summary is incompatible/incomplete: " + ", ".join(mismatches))
        return 1

    print(f"[1.55L] existing summary is complete for requested grid: {args.summary}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
