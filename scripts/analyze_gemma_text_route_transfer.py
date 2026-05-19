#!/usr/bin/env python3
"""Audit whether a text routing rule covers harmed rows in one paired artifact.

This CPU-only screen is intentionally weaker than
``analyze_gemma_text_routed_admission.py``: it does not simulate a mixed policy
because it has only one paired artifact. It answers the transfer question:
would a preregistered question-text rule have routed the rows that the fast
arm harmed?
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.analyze_gemma_admission_policy_simulation import (  # noqa: E402
    _index_rows,
    _read_jsonl,
    _transition,
)
from scripts.analyze_gemma_text_routed_admission import (  # noqa: E402
    DEFAULT_SAFE_QUESTION_REGEX,
    MVBENCH_JSON_DIR,
    TOMATO_DATA_DIR,
    VIDEOMME_PARQUET_DIR,
    _compile_regex,
    _load_manifest_item_ids,
    _load_questions,
)


def _summarize(
    rows: dict[str, dict[str, Any]],
    *,
    questions: dict[str, str],
    safe_regex: Any,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    items: list[dict[str, Any]] = []
    route_by_group: dict[str, Counter[str]] = defaultdict(Counter)
    harm_by_group: dict[str, Counter[str]] = defaultdict(Counter)
    for key in sorted(rows):
        row = rows[key]
        question = questions[key]
        matched = safe_regex.search(question) is not None
        dense_correct = bool(row["dense_correct"])
        composed_correct = bool(row["composed_correct"])
        transition = _transition(dense_correct, composed_correct)
        group = str(row["group"])
        route_by_group[group]["matched_safe_regex" if matched else "unmatched_fast"] += 1
        if transition == "harmed":
            harm_by_group[group]["matched_safe_regex" if matched else "unmatched_fast"] += 1
        items.append(
            {
                "item_id": key,
                "benchmark": row["benchmark"],
                "group": group,
                "question": question,
                "matched_safe_regex": matched,
                "dense_correct": dense_correct,
                "composed_correct": composed_correct,
                "correctness_transition": transition,
            }
        )
    harmed = [row for row in items if row["correctness_transition"] == "harmed"]
    matched = [row for row in items if row["matched_safe_regex"]]
    matched_harmed = [
        row
        for row in items
        if row["matched_safe_regex"] and row["correctness_transition"] == "harmed"
    ]
    summary = {
        "n": len(items),
        "matched_count": len(matched),
        "matched_rate": len(matched) / len(items),
        "harmed_count": len(harmed),
        "harmed_matched_count": len(matched_harmed),
        "harmed_recall": (len(matched_harmed) / len(harmed)) if harmed else None,
        "matched_precision_for_harm": (len(matched_harmed) / len(matched)) if matched else None,
        "route_summary_by_group": {
            group: dict(sorted(counter.items()))
            for group, counter in sorted(route_by_group.items())
        },
        "harm_coverage_by_group": {
            group: dict(sorted(counter.items())) for group, counter in sorted(harm_by_group.items())
        },
    }
    return summary, items


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--paired-items", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--policy-label", default="text_regex_transfer_screen")
    parser.add_argument("--safe-question-regex", default=DEFAULT_SAFE_QUESTION_REGEX)
    parser.add_argument("--mvbench-json-dir", type=Path, default=MVBENCH_JSON_DIR)
    parser.add_argument("--tomato-data-dir", type=Path, default=TOMATO_DATA_DIR)
    parser.add_argument("--videomme-parquet-dir", type=Path, default=VIDEOMME_PARQUET_DIR)
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    item_ids = _load_manifest_item_ids(args.manifest)
    rows = _index_rows(_read_jsonl(args.paired_items), label="paired-items")
    manifest_keys = set(item_ids)
    artifact_keys = set(rows)
    if manifest_keys != artifact_keys:
        missing_from_manifest = sorted(artifact_keys - manifest_keys)
        missing_from_artifacts = sorted(manifest_keys - artifact_keys)
        raise ValueError(
            "manifest and paired artifact do not describe the same item set: "
            f"missing_from_manifest={missing_from_manifest[:5]}, "
            f"missing_from_artifacts={missing_from_artifacts[:5]}"
        )
    questions = _load_questions(
        item_ids,
        mvbench_json_dir=args.mvbench_json_dir,
        tomato_data_dir=args.tomato_data_dir,
        videomme_parquet_dir=args.videomme_parquet_dir,
    )
    summary, items = _summarize(
        rows,
        questions=questions,
        safe_regex=_compile_regex(str(args.safe_question_regex)),
    )
    payload = {
        "schema": "gemma_text_route_transfer_v1",
        "analysis_role": "single_artifact_text_rule_transfer_screen",
        "policy_label": args.policy_label,
        "safe_question_regex": str(args.safe_question_regex),
        "source_path": str(args.paired_items),
        "manifest_path": str(args.manifest),
        "question_source": "benchmark_raw_question_text",
        "summary": summary,
        "items": items,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, allow_nan=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
