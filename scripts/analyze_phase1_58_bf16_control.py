#!/usr/bin/env python3
"""Summarize the Phase 1.58 4bit-vs-bf16 Qwen control."""

from __future__ import annotations

import argparse
import json
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any


def _fmt(value: float | None, spec: str = ".3f") -> str:
    if value is None:
        return "n/a"
    return format(value, spec)


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open() as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def _mean(values: list[float]) -> float | None:
    return float(sum(values) / len(values)) if values else None


def _median(values: list[float]) -> float | None:
    return float(statistics.median(values)) if values else None


def _approx_time_ms(tokens: int, tps: float) -> float | None:
    if tps <= 0:
        return None
    return float(tokens / tps * 1000.0)


def _group_stats(rows: list[dict[str, Any]]) -> dict[str, dict[str, float | int | None]]:
    by_group: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_group[str(row["group"])].append(row)

    payload: dict[str, dict[str, float | int | None]] = {}
    for group, group_rows in sorted(by_group.items()):
        accuracies = [1.0 if bool(row["dense"]["correct"]) else 0.0 for row in group_rows]
        elapsed = [float(row["dense"]["elapsed_ms"]) for row in group_rows]
        prompt_ms = [
            value
            for value in (
                _approx_time_ms(
                    int(row["dense"]["prompt_tokens"]),
                    float(row["dense"].get("prompt_tps", 0.0)),
                )
                for row in group_rows
            )
            if value is not None
        ]
        generation_ms = [
            value
            for value in (
                _approx_time_ms(
                    int(row["dense"]["generation_tokens"]),
                    float(row["dense"].get("generation_tps", 0.0)),
                )
                for row in group_rows
            )
            if value is not None
        ]
        payload[group] = {
            "n": len(group_rows),
            "accuracy": _mean(accuracies),
            "mean_elapsed_ms": _mean(elapsed),
            "median_elapsed_ms": _median(elapsed),
            "mean_prompt_ms": _mean(prompt_ms),
            "mean_generation_ms": _mean(generation_ms),
            "max_peak_memory_gb": max(float(row["dense"]["peak_memory_gb"]) for row in group_rows),
        }
    return payload


def _summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    accuracies = [1.0 if bool(row["dense"]["correct"]) else 0.0 for row in rows]
    elapsed = [float(row["dense"]["elapsed_ms"]) for row in rows]
    prompt_ms = [
        value
        for value in (
            _approx_time_ms(
                int(row["dense"]["prompt_tokens"]),
                float(row["dense"].get("prompt_tps", 0.0)),
            )
            for row in rows
        )
        if value is not None
    ]
    generation_ms = [
        value
        for value in (
            _approx_time_ms(
                int(row["dense"]["generation_tokens"]),
                float(row["dense"].get("generation_tps", 0.0)),
            )
            for row in rows
        )
        if value is not None
    ]
    return {
        "n": len(rows),
        "accuracy": _mean(accuracies),
        "mean_elapsed_ms": _mean(elapsed),
        "median_elapsed_ms": _median(elapsed),
        "mean_prompt_ms": _mean(prompt_ms),
        "mean_generation_ms": _mean(generation_ms),
        "max_peak_memory_gb": max(float(row["dense"]["peak_memory_gb"]) for row in rows),
    }


def _compare_pair(
    *,
    fourbit_rows: list[dict[str, Any]],
    bf16_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    fourbit = _summary(fourbit_rows)
    bf16 = _summary(bf16_rows)
    per_group_fourbit = _group_stats(fourbit_rows)
    per_group_bf16 = _group_stats(bf16_rows)
    groups = sorted(set(per_group_fourbit) | set(per_group_bf16))

    per_group: dict[str, Any] = {}
    for group in groups:
        ref = per_group_fourbit.get(group, {})
        test = per_group_bf16.get(group, {})
        ref_elapsed = ref.get("mean_elapsed_ms")
        test_elapsed = test.get("mean_elapsed_ms")
        ref_prompt = ref.get("mean_prompt_ms")
        test_prompt = test.get("mean_prompt_ms")
        per_group[group] = {
            "fourbit": ref,
            "bf16": test,
            "accuracy_delta_bf16_minus_fourbit": (
                None
                if ref.get("accuracy") is None or test.get("accuracy") is None
                else float(test["accuracy"]) - float(ref["accuracy"])
            ),
            "elapsed_ratio_fourbit_over_bf16": (
                None
                if not ref_elapsed or not test_elapsed
                else float(ref_elapsed) / float(test_elapsed)
            ),
            "prompt_time_ratio_bf16_over_fourbit": (
                None
                if not ref_prompt or not test_prompt
                else float(test_prompt) / float(ref_prompt)
            ),
        }

    ref_elapsed = fourbit.get("mean_elapsed_ms")
    test_elapsed = bf16.get("mean_elapsed_ms")
    ref_prompt = fourbit.get("mean_prompt_ms")
    test_prompt = bf16.get("mean_prompt_ms")
    return {
        "fourbit": fourbit,
        "bf16": bf16,
        "accuracy_delta_bf16_minus_fourbit": (
            None
            if fourbit.get("accuracy") is None or bf16.get("accuracy") is None
            else float(bf16["accuracy"]) - float(fourbit["accuracy"])
        ),
        "elapsed_ratio_fourbit_over_bf16": (
            None if not ref_elapsed or not test_elapsed else float(ref_elapsed) / float(test_elapsed)
        ),
        "prompt_time_ratio_bf16_over_fourbit": (
            None if not ref_prompt or not test_prompt else float(test_prompt) / float(ref_prompt)
        ),
        "per_group": per_group,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fourbit-8f", type=Path, required=True)
    parser.add_argument("--bf16-8f", type=Path, required=True)
    parser.add_argument("--fourbit-16f", type=Path, required=True)
    parser.add_argument("--bf16-16f", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    payload = {
        "phase": "1.58",
        "8f": _compare_pair(
            fourbit_rows=_load_jsonl(args.fourbit_8f),
            bf16_rows=_load_jsonl(args.bf16_8f),
        ),
        "16f": _compare_pair(
            fourbit_rows=_load_jsonl(args.fourbit_16f),
            bf16_rows=_load_jsonl(args.bf16_16f),
        ),
    }

    sixteen_groups = payload["16f"]["per_group"]
    long_delta = sixteen_groups.get("long", {}).get("accuracy_delta_bf16_minus_fourbit")
    short_delta_8f = payload["8f"]["per_group"].get("short", {}).get(
        "accuracy_delta_bf16_minus_fourbit"
    )
    short_delta_16f = sixteen_groups.get("short", {}).get("accuracy_delta_bf16_minus_fourbit")
    peak_rss = payload["16f"]["bf16"].get("max_peak_memory_gb")
    prompt_ratio = payload["16f"].get("prompt_time_ratio_bf16_over_fourbit")
    payload["prereg_checks"] = {
        "h1_long_bucket_gap_ge_0p20": (
            long_delta is not None and float(long_delta) >= 0.20
        ),
        "h2_short_bucket_within_0p10": (
            short_delta_8f is not None
            and short_delta_16f is not None
            and abs(float(short_delta_8f)) <= 0.10
            and abs(float(short_delta_16f)) <= 0.10
        ),
        "h3_peak_rss_lt_14gb": peak_rss is not None and float(peak_rss) < 14.0,
        "h4_prompt_ratio_bf16_over_4bit_ge_3p0": (
            prompt_ratio is not None and float(prompt_ratio) >= 3.0
        ),
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")

    print(f"Wrote {args.output}")
    for label in ("8f", "16f"):
        entry = payload[label]
        print(
            f"{label}: acc Δ={_fmt(entry['accuracy_delta_bf16_minus_fourbit'], '+.3f')} "
            f"elapsed ratio 4bit/bf16={_fmt(entry['elapsed_ratio_fourbit_over_bf16'])}"
        )
        for group, group_entry in entry["per_group"].items():
            print(
                f"  {group:<8} acc Δ="
                f"{_fmt(group_entry['accuracy_delta_bf16_minus_fourbit'], '+.3f')} "
                f"elapsed ratio={_fmt(group_entry['elapsed_ratio_fourbit_over_bf16'])}"
            )


if __name__ == "__main__":
    main()
