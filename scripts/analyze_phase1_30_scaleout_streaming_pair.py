#!/usr/bin/env python3
"""Analyze a cold-vs-streaming Phase 1.30 pair."""

from __future__ import annotations

import argparse
import json
import random
from collections.abc import Callable
from pathlib import Path

from codec_through.session_bucketing import classify_streaming_pair


def _load_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open() as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def _index(rows: list[dict]) -> dict[tuple[str, int], dict]:
    return {(str(row["seed_item_id"]), int(row["q_index"])): row for row in rows}


def _mean(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def _fraction(numerator: int, denominator: int) -> float | None:
    if denominator <= 0:
        return None
    return numerator / denominator


def _paired_bootstrap_delta_ci(
    rows: list[dict],
    *,
    predicate: Callable[[dict], bool] | None,
    n_resamples: int,
    rng: random.Random,
) -> tuple[float | None, list[float] | None, int, int]:
    filtered = [row for row in rows if predicate is None or predicate(row)]
    if not filtered:
        return (None, None, 0, 0)

    by_session: dict[str, list[dict]] = {}
    for row in filtered:
        by_session.setdefault(str(row["session_id"]), []).append(row)
    session_ids = sorted(by_session)
    if not session_ids:
        return (None, None, 0, 0)

    point = sum(
        (1.0 if row["streaming_correct"] else 0.0) - (1.0 if row["cold_correct"] else 0.0)
        for row in filtered
    ) / len(filtered)
    n_sessions = len(session_ids)
    deltas: list[float] = []
    for _ in range(n_resamples):
        sampled_rows: list[dict] = []
        for _ in range(n_sessions):
            sampled_rows.extend(by_session[session_ids[rng.randrange(n_sessions)]])
        deltas.append(
            sum(
                (1.0 if row["streaming_correct"] else 0.0) - (1.0 if row["cold_correct"] else 0.0)
                for row in sampled_rows
            )
            / len(sampled_rows)
        )
    deltas.sort()
    return (
        point,
        [deltas[int(0.025 * n_resamples)], deltas[int(0.975 * n_resamples) - 1]],
        n_sessions,
        len(filtered),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cold-jsonl", type=Path, required=True)
    parser.add_argument("--streaming-jsonl", type=Path, required=True)
    parser.add_argument("--cold-summary", type=Path, required=True)
    parser.add_argument("--streaming-summary", type=Path, required=True)
    parser.add_argument("--pair-summary", type=Path, required=True)
    parser.add_argument("--per-clip-buckets", type=Path, required=True)
    parser.add_argument("--paired-queries", type=Path, required=True)
    parser.add_argument("--n-resamples", type=int, default=5000)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()

    cold_rows = _load_jsonl(args.cold_jsonl)
    streaming_rows = _load_jsonl(args.streaming_jsonl)
    cold_summary = json.loads(args.cold_summary.read_text())
    streaming_summary = json.loads(args.streaming_summary.read_text())

    cold_by_key = _index(cold_rows)
    streaming_by_key = _index(streaming_rows)
    keys = sorted(set(cold_by_key) & set(streaming_by_key))
    if not keys:
        raise SystemExit("no overlapping cold/streaming rows to compare")

    bucket_counts = {"clean": 0, "mixed": 0, "degenerate": 0}
    overlap_counts = {
        "both_correct": 0,
        "cold_only_correct": 0,
        "streaming_only_correct": 0,
        "both_wrong": 0,
    }
    per_clip: dict[str, dict] = {}
    paired_rows: list[dict] = []

    for key in keys:
        cold = cold_by_key[key]
        streaming = streaming_by_key[key]
        response_bucket = classify_streaming_pair(
            cold_choice=cold.get("choice"),
            cold_correct=bool(cold["correct"]),
            streaming_choice=streaming.get("choice"),
            streaming_correct=bool(streaming["correct"]),
            streaming_parse_failure=bool(streaming["parse_failure"]),
            streaming_text=str(streaming["response"]),
        )
        overlap_bucket = (
            "both_correct"
            if cold["correct"] and streaming["correct"]
            else "cold_only_correct"
            if cold["correct"] and not streaming["correct"]
            else "streaming_only_correct"
            if not cold["correct"] and streaming["correct"]
            else "both_wrong"
        )
        bucket_counts[response_bucket] += 1
        overlap_counts[overlap_bucket] += 1

        clip_entry = per_clip.setdefault(
            str(streaming["seed_item_id"]),
            {
                "video_id": streaming["video_id"],
                "duration": streaming["duration"],
                "split": streaming.get("split"),
                "source_manifests": streaming.get("source_manifests", []),
                "bucket_tally": {"clean": 0, "mixed": 0, "degenerate": 0},
                "overlap_tally": {
                    "both_correct": 0,
                    "cold_only_correct": 0,
                    "streaming_only_correct": 0,
                    "both_wrong": 0,
                },
                "queries": [],
            },
        )
        clip_entry["bucket_tally"][response_bucket] += 1
        clip_entry["overlap_tally"][overlap_bucket] += 1
        clip_entry["queries"].append(
            {
                "q_index": int(streaming["q_index"]),
                "item_id": streaming["item_id"],
                "response_bucket": response_bucket,
                "overlap_bucket": overlap_bucket,
                "cold_correct": bool(cold["correct"]),
                "streaming_correct": bool(streaming["correct"]),
                "cold_choice": cold.get("choice"),
                "streaming_choice": streaming.get("choice"),
            }
        )
        paired_rows.append(
            {
                "seed_item_id": streaming["seed_item_id"],
                "session_id": streaming.get("session_id", streaming["seed_item_id"]),
                "video_id": streaming["video_id"],
                "duration": streaming["duration"],
                "split": streaming.get("split"),
                "item_id": streaming["item_id"],
                "q_index": int(streaming["q_index"]),
                "cold_correct": bool(cold["correct"]),
                "streaming_correct": bool(streaming["correct"]),
                "cold_choice": cold.get("choice"),
                "streaming_choice": streaming.get("choice"),
                "cold_parse_failure": bool(cold["parse_failure"]),
                "streaming_parse_failure": bool(streaming["parse_failure"]),
                "pair_bucket_overlap": overlap_bucket,
                "streaming_response_bucket": response_bucket,
                "cold_end_to_end_ms": float(cold["end_to_end_ms"]),
                "streaming_end_to_end_ms": float(streaming["end_to_end_ms"]),
            }
        )

    cold_total_ms = sum(float(row["end_to_end_ms"]) for row in cold_rows)
    streaming_total_ms = sum(float(row["end_to_end_ms"]) for row in streaming_rows)
    rng = random.Random(args.seed)
    all_delta, all_ci, n_sessions, _n_all = _paired_bootstrap_delta_ci(
        paired_rows,
        predicate=None,
        n_resamples=args.n_resamples,
        rng=rng,
    )
    q0_delta, q0_ci, _q0_sessions, q0_n = _paired_bootstrap_delta_ci(
        paired_rows,
        predicate=lambda row: int(row["q_index"]) == 0,
        n_resamples=args.n_resamples,
        rng=rng,
    )
    follow_delta, follow_ci, _follow_sessions, follow_n = _paired_bootstrap_delta_ci(
        paired_rows,
        predicate=lambda row: int(row["q_index"]) > 0,
        n_resamples=args.n_resamples,
        rng=rng,
    )
    follow_up_streaming_rows = [row for row in streaming_rows if int(row["q_index"]) > 0]
    follow_up_pruning_instrumented_rows = [
        row for row in follow_up_streaming_rows if "vision_pruning_active" in row
    ]
    follow_up_image_token_rows = [
        row
        for row in follow_up_streaming_rows
        if row.get("image_token_count") is not None
        and row.get("image_tokens_recomputed") is not None
    ]
    follow_up_recomputed = [
        float(row["image_tokens_recomputed"])
        for row in follow_up_image_token_rows
        if row.get("image_tokens_recomputed") is not None
    ]
    follow_up_pruning_active_count = sum(
        1
        for row in follow_up_pruning_instrumented_rows
        if bool(row.get("vision_pruning_active", False))
    )
    follow_up_fully_reused_count = sum(
        1
        for row in follow_up_image_token_rows
        if row.get("image_token_count") is not None
        and int(row["image_token_count"]) > 0
        and int(row["image_tokens_recomputed"]) == 0
    )
    pair_summary = {
        "phase": "1.30",
        "n_paired_queries": len(keys),
        "n_paired_sessions": n_sessions,
        "cold_accuracy": cold_summary["all_queries"]["accuracy"],
        "streaming_accuracy": streaming_summary["all_queries"]["accuracy"],
        "accuracy_delta_streaming_minus_cold": (
            streaming_summary["all_queries"]["accuracy"] - cold_summary["all_queries"]["accuracy"]
        ),
        "accuracy_delta_streaming_minus_cold_ci95": all_ci,
        "q0_accuracy_delta_streaming_minus_cold": q0_delta,
        "q0_accuracy_delta_streaming_minus_cold_ci95": q0_ci,
        "q0_n_paired_queries": q0_n,
        "follow_up_accuracy_delta_streaming_minus_cold": follow_delta,
        "follow_up_accuracy_delta_streaming_minus_cold_ci95": follow_ci,
        "follow_up_n_paired_queries": follow_n,
        "cold_total_end_to_end_ms": cold_total_ms,
        "streaming_total_end_to_end_ms": streaming_total_ms,
        "amortized_speedup_cold_over_streaming": (
            cold_total_ms / streaming_total_ms if streaming_total_ms > 0 else None
        ),
        "response_bucket_counts": bucket_counts,
        "overlap_bucket_counts": overlap_counts,
        "clean_fraction": bucket_counts["clean"] / len(keys),
        "streaming_degenerate_count": bucket_counts["degenerate"],
        "degenerate_fraction": bucket_counts["degenerate"] / len(keys),
        "cold_parse_failures": int(cold_summary.get("parse_failures", 0)),
        "streaming_parse_failures": int(streaming_summary.get("parse_failures", 0)),
        "streaming_parse_failure_fraction": _fraction(
            int(streaming_summary.get("parse_failures", 0)),
            len(streaming_rows),
        ),
        "refresh_events": int(streaming_summary.get("refresh_events", 0)),
        "streaming_follow_up_n": len(follow_up_streaming_rows),
        "streaming_follow_up_pruning_instrumented_n": len(follow_up_pruning_instrumented_rows),
        "streaming_follow_up_image_token_instrumented_n": len(follow_up_image_token_rows),
        "streaming_follow_up_mean_image_tokens_recomputed": _mean(follow_up_recomputed),
        "streaming_follow_up_vision_pruning_active_count": follow_up_pruning_active_count,
        "streaming_follow_up_vision_pruning_active_fraction": (
            _fraction(
                follow_up_pruning_active_count,
                len(follow_up_pruning_instrumented_rows),
            )
        ),
        "streaming_follow_up_all_image_tokens_reused_count": follow_up_fully_reused_count,
        "streaming_follow_up_all_image_tokens_reused_fraction": (
            _fraction(
                follow_up_fully_reused_count,
                len(follow_up_image_token_rows),
            )
        ),
    }

    args.pair_summary.parent.mkdir(parents=True, exist_ok=True)
    args.pair_summary.write_text(json.dumps(pair_summary, indent=2) + "\n")
    args.per_clip_buckets.write_text(json.dumps(per_clip, indent=2) + "\n")
    with args.paired_queries.open("w") as handle:
        for row in paired_rows:
            handle.write(json.dumps(row) + "\n")
    print(f"[1.30 pair] wrote {args.pair_summary}")
    print(f"[1.30 pair] wrote {args.per_clip_buckets}")
    print(f"[1.30 pair] wrote {args.paired_queries}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
