#!/usr/bin/env python3
"""Summarize local and predecessor benchmark artifacts for reproduction review."""

from __future__ import annotations

import argparse
import json
import math
import re
from collections import Counter
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from codec_through.answers import extract_choice

CHOICE_LINE_PATTERN = re.compile(r"^([A-Z])\.\s+(.*)$")
REUSE_BINS = (
    ("<0.5", 0.0, 0.5),
    ("0.5-0.7", 0.5, 0.7),
    ("0.7-0.85", 0.7, 0.85),
    ("0.85-1.0", 0.85, 1.01),
)


def _wilson_interval(successes: int, total: int, *, z: float = 1.96) -> tuple[float, float]:
    if total <= 0:
        return 0.0, 0.0
    proportion = successes / total
    denominator = 1.0 + (z * z / total)
    center = (proportion + (z * z / (2.0 * total))) / denominator
    margin = (
        z
        * math.sqrt((proportion * (1.0 - proportion) + (z * z / (4.0 * total))) / total)
        / denominator
    )
    return center - margin, center + margin


def _binomial_two_sided_p(successes: int, failures: int) -> float:
    total = successes + failures
    if total <= 0:
        return 1.0
    probabilities = [math.comb(total, count) * (0.5**total) for count in range(total + 1)]
    target = probabilities[min(successes, failures)]
    return min(1.0, sum(value for value in probabilities if value <= target + 1e-12))


def _parse_candidates(question: str) -> list[str]:
    candidates: list[str] = []
    for line in question.splitlines():
        match = CHOICE_LINE_PATTERN.match(line.strip())
        if match is not None:
            candidates.append(match.group(2))
    if not candidates:
        raise ValueError("could not recover candidates from stored question prompt")
    return candidates


def _load_items(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text())
    items = payload["items"] if isinstance(payload, dict) and "items" in payload else payload
    if not isinstance(items, list):
        raise ValueError(f"expected list-like items in {path}")
    return items


def _local_metrics(
    items: list[dict[str, Any]],
    *,
    default_index_on_failure: int | None,
) -> dict[str, Any]:
    dense_correct = 0
    cached_correct = 0
    matched = 0
    dense_parse_failures = 0
    cached_parse_failures = 0
    cached_improves = 0
    cached_regresses = 0
    both_wrong_different = 0

    rescored_items: list[dict[str, Any]] = []
    for item in items:
        candidates = _parse_candidates(str(item["question"]))
        answer_index = int(item["answer_index"])
        dense_choice = extract_choice(
            str(item["dense"]["text"]),
            candidates,
            default_index_on_failure=default_index_on_failure,
        )
        cached_choice = extract_choice(
            str(item["cached"]["text"]),
            candidates,
            default_index_on_failure=default_index_on_failure,
        )
        dense_failure = dense_choice is None
        cached_failure = cached_choice is None
        dense_is_correct = dense_choice == answer_index if dense_choice is not None else False
        cached_is_correct = cached_choice == answer_index if cached_choice is not None else False
        match = (
            dense_choice == cached_choice
            if dense_choice is not None and cached_choice is not None
            else False
        )

        dense_correct += int(dense_is_correct)
        cached_correct += int(cached_is_correct)
        matched += int(match)
        dense_parse_failures += int(dense_failure)
        cached_parse_failures += int(cached_failure)
        cached_improves += int((not dense_is_correct) and cached_is_correct)
        cached_regresses += int(dense_is_correct and (not cached_is_correct))
        both_wrong_different += int(
            (not dense_is_correct)
            and (not cached_is_correct)
            and dense_choice is not None
            and cached_choice is not None
            and dense_choice != cached_choice
        )
        rescored_items.append(
            {
                "item_id": item["item_id"],
                "group": item["group"],
                "reuse_ratio_mean": float(item["reuse_ratio_mean"]),
                "dense_choice": dense_choice,
                "cached_choice": cached_choice,
                "dense_correct": dense_is_correct,
                "cached_correct": cached_is_correct,
                "match": match,
            }
        )

    total = len(items)
    return {
        "n": total,
        "dense_accuracy": dense_correct / total if total else 0.0,
        "dense_accuracy_ci95": _wilson_interval(dense_correct, total),
        "cached_accuracy": cached_correct / total if total else 0.0,
        "cached_accuracy_ci95": _wilson_interval(cached_correct, total),
        "agreement": matched / total if total else 0.0,
        "agreement_ci95": _wilson_interval(matched, total),
        "dense_parse_failures": dense_parse_failures,
        "cached_parse_failures": cached_parse_failures,
        "cached_improves": cached_improves,
        "cached_regresses": cached_regresses,
        "both_wrong_different": both_wrong_different,
        "mcnemar_exact_p": _binomial_two_sided_p(cached_improves, cached_regresses),
        "group_counts": dict(sorted(Counter(str(item["group"]) for item in items).items())),
        "reuse_bins": _reuse_bins(rescored_items),
    }


def _reuse_bins(items: Iterable[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    materialized = list(items)
    output: dict[str, dict[str, Any]] = {}
    for label, lower, upper in REUSE_BINS:
        selected = [
            item for item in materialized if lower <= float(item["reuse_ratio_mean"]) < upper
        ]
        if not selected:
            output[label] = {"n": 0}
            continue
        total = len(selected)
        dense_correct = sum(bool(item["dense_correct"]) for item in selected)
        cached_correct = sum(bool(item["cached_correct"]) for item in selected)
        matched = sum(bool(item["match"]) for item in selected)
        output[label] = {
            "n": total,
            "dense_accuracy": dense_correct / total,
            "cached_accuracy": cached_correct / total,
            "agreement": matched / total,
        }
    return output


def _legacy_metrics(
    entries: list[dict[str, Any]],
    *,
    dense_key: str,
    cached_key: str,
    match_key: str,
) -> dict[str, Any]:
    total = len(entries)
    dense_correct = sum(bool(entry[dense_key]) for entry in entries)
    cached_correct = sum(bool(entry[cached_key]) for entry in entries)
    matched = sum(bool(entry[match_key]) for entry in entries)
    both_wrong_match = sum(
        (not bool(entry[dense_key])) and (not bool(entry[cached_key])) and bool(entry[match_key])
        for entry in entries
    )
    return {
        "n": total,
        "dense_accuracy": dense_correct / total if total else 0.0,
        "cached_accuracy": cached_correct / total if total else 0.0,
        "agreement": matched / total if total else 0.0,
        "both_wrong_match": both_wrong_match,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("results/benchmark_reproduction_diagnostics.json"),
    )
    parser.add_argument(
        "--tomato-local",
        type=Path,
        default=Path("research/experiments/2026/artifacts/phase1_4_run_b_subset30.json"),
    )
    parser.add_argument(
        "--mvbench-local",
        type=Path,
        default=Path("research/experiments/2026/artifacts/phase1_5_run_b_subset54.json"),
    )
    parser.add_argument(
        "--tomato-predecessor",
        type=Path,
        default=Path("seed/original_repo/results/tomato_7b_ALL_1000.json"),
    )
    parser.add_argument(
        "--mvbench-predecessor",
        type=Path,
        default=Path("seed/original_repo/results/mvbench_7b_10.json"),
    )
    args = parser.parse_args()

    tomato_local_items = _load_items(args.tomato_local)
    mvbench_local_items = _load_items(args.mvbench_local)
    tomato_predecessor = _load_items(args.tomato_predecessor)
    mvbench_predecessor = _load_items(args.mvbench_predecessor)

    result = {
        "local": {
            "tomato_subset30": {
                "strict": _local_metrics(tomato_local_items, default_index_on_failure=None),
                "loose_default_to_a": _local_metrics(
                    tomato_local_items,
                    default_index_on_failure=0,
                ),
            },
            "mvbench_subset54": {
                "strict": _local_metrics(mvbench_local_items, default_index_on_failure=None),
                "loose_default_to_a": _local_metrics(
                    mvbench_local_items,
                    default_index_on_failure=0,
                ),
            },
        },
        "predecessor": {
            "tomato_full_1484": _legacy_metrics(
                tomato_predecessor,
                dense_key="bl_correct",
                cached_key="ca_correct",
                match_key="match",
            ),
            "mvbench_slice_160": _legacy_metrics(
                mvbench_predecessor,
                dense_key="bl_correct",
                cached_key="ca_correct",
                match_key="match",
            ),
        },
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
