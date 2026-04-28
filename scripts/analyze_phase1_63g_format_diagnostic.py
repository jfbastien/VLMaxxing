#!/usr/bin/env python3
"""Diagnose Gemma Track B parse failures for paper-safe framing.

This is analysis-only. It checks whether Gemma dense/sparse parse failures are
matched failures and whether a permissive letter parser would recover them.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

DEFAULT_ARTIFACT_DIR = Path("research/experiments/2026/artifacts/phase1_63G_gemma_track_b")


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open() as handle:
        for line in handle:
            stripped = line.strip()
            if stripped:
                rows.append(json.loads(stripped))
    return rows


def _index(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    for row in rows:
        item_id = str(row["item_id"])
        if item_id in indexed:
            raise ValueError(f"duplicate item_id in Gemma diagnostic: {item_id}")
        indexed[item_id] = row
    return indexed


def _permissive_choice(text: str | None) -> str | None:
    """Return a standalone A/B/C/D if one appears outside a word."""
    if not text:
        return None
    # Deliberately do not uppercase the text: otherwise every standalone
    # article "a" becomes a false option-A recovery in apology/prose failures.
    matches = re.findall(r"(?<![A-Za-z])([ABCD])(?![A-Za-z])", text)
    unique = sorted(set(matches))
    return unique[0] if len(unique) == 1 else None


def _snippet(row: dict[str, Any]) -> str:
    text = str(row.get("text") or row.get("response") or "")
    return " ".join(text.split())[:280]


def _cell(artifact_dir: Path, frame_count: int) -> dict[str, Any]:
    dense_path = artifact_dir / f"dense_{frame_count}f.jsonl"
    sparse_path = artifact_dir / f"sparse_L2_kr050_{frame_count}f.jsonl"
    pair_path = artifact_dir / f"pair_summary_{frame_count}f.json"
    if not dense_path.exists() or not sparse_path.exists() or not pair_path.exists():
        raise FileNotFoundError(f"missing Gemma 1.63G artifacts for {frame_count}f")

    dense = _index(_load_jsonl(dense_path))
    sparse = _index(_load_jsonl(sparse_path))
    if set(dense) != set(sparse):
        raise ValueError(
            f"Gemma dense/sparse item mismatch at {frame_count}f: "
            f"dense_only={sorted(set(dense) - set(sparse))[:5]}, "
            f"sparse_only={sorted(set(sparse) - set(dense))[:5]}"
        )

    dense_fail = {item_id for item_id, row in dense.items() if bool(row.get("parse_failure"))}
    sparse_fail = {item_id for item_id, row in sparse.items() if bool(row.get("parse_failure"))}
    union_fail = sorted(dense_fail | sparse_fail)

    recoverable_dense = [
        item_id for item_id in dense_fail if _permissive_choice(str(dense[item_id].get("text")))
    ]
    recoverable_sparse = [
        item_id for item_id in sparse_fail if _permissive_choice(str(sparse[item_id].get("text")))
    ]

    examples: list[dict[str, Any]] = []
    for item_id in union_fail[:10]:
        examples.append(
            {
                "item_id": item_id,
                "dense_parse_failure": item_id in dense_fail,
                "sparse_parse_failure": item_id in sparse_fail,
                "dense_permissive_choice": _permissive_choice(str(dense[item_id].get("text"))),
                "sparse_permissive_choice": _permissive_choice(str(sparse[item_id].get("text"))),
                "dense_text_snippet": _snippet(dense[item_id]),
                "sparse_text_snippet": _snippet(sparse[item_id]),
            }
        )

    pair_summary = json.loads(pair_path.read_text())
    return {
        "frame_count": frame_count,
        "n_items": len(dense),
        "dense_parse_failures": len(dense_fail),
        "sparse_parse_failures": len(sparse_fail),
        "matched_parse_failures": len(dense_fail & sparse_fail),
        "dense_only_parse_failures": sorted(dense_fail - sparse_fail),
        "sparse_only_parse_failures": sorted(sparse_fail - dense_fail),
        "parse_failure_jaccard": (
            len(dense_fail & sparse_fail) / len(dense_fail | sparse_fail)
            if dense_fail or sparse_fail
            else 1.0
        ),
        "dense_permissive_recoverable": len(recoverable_dense),
        "sparse_permissive_recoverable": len(recoverable_sparse),
        "permissive_recoverable_any": len(set(recoverable_dense) | set(recoverable_sparse)),
        "paired_accuracy_delta": pair_summary["all"]["accuracy_delta_sparse_minus_dense"],
        "paired_choice_agreement": pair_summary["all"]["choice_agreement"],
        "pass_format_original": pair_summary["pass_format"],
        "examples": examples,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact-dir", type=Path, default=DEFAULT_ARTIFACT_DIR)
    parser.add_argument("--frame-count", action="append", type=int, default=None)
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_ARTIFACT_DIR / "format_diagnostic_summary.json",
    )
    args = parser.parse_args()

    frame_counts = args.frame_count or [8, 16, 32]
    cells = [_cell(args.artifact_dir, frame_count) for frame_count in frame_counts]
    total_fail_union = sum(
        len(set(cell["dense_only_parse_failures"]) | set(cell["sparse_only_parse_failures"]))
        + int(cell["matched_parse_failures"])
        for cell in cells
    )
    total_recoverable = sum(int(cell["permissive_recoverable_any"]) for cell in cells)
    payload = {
        "phase": "1.63G-format-diagnostic",
        "artifact_dir": args.artifact_dir.as_posix(),
        "frame_counts": frame_counts,
        "cells": cells,
        "pass_matched_failure_diagnostic": all(
            not cell["dense_only_parse_failures"] and not cell["sparse_only_parse_failures"]
            for cell in cells
        ),
        "pass_parser_not_fixable": total_fail_union == 0
        or (total_recoverable / total_fail_union) <= 0.10,
        "total_failure_items": total_fail_union,
        "total_permissive_recoverable_items": total_recoverable,
        "interpretation": (
            "If matched_failure_diagnostic passes and parser_not_fixable passes, "
            "Gemma Track B should be framed as zero paired drift under matched "
            "dense/sparse format failures, not as format-clean C-VISION."
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(f"[1.63G-format] wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
