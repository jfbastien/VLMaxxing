#!/usr/bin/env python3
"""Summarize paired fidelity and latency for selective re-prefill runs."""

from __future__ import annotations

import argparse
import json
import random
import statistics
from collections.abc import Callable
from pathlib import Path
from typing import Any


def _is_pathological_like_response(text: str | None) -> bool:
    rendered = str(text or "")
    return "addCriterion" in rendered or "自动" in rendered


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open() as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def _key(row: dict[str, Any]) -> tuple[str, int]:
    return (str(row["item_id"]), int(row["q_index"]))


def _median(values: list[float]) -> float | None:
    return float(statistics.median(values)) if values else None


def _session_id(row: dict[str, Any]) -> str:
    video_id = row.get("video_id")
    if video_id is not None:
        return str(video_id)
    return str(row["item_id"]).rsplit("-", 1)[0]


def _optional_float(row: dict[str, Any], key: str) -> float | None:
    value = row.get(key)
    if value is None:
        return None
    return float(value)


def _paired_bootstrap_delta_ci(
    rows: list[dict[str, Any]],
    *,
    predicate: Callable[[dict[str, Any]], bool] | None,
    n_resamples: int,
    rng: random.Random,
) -> tuple[float | None, list[float] | None, int]:
    filtered = [row for row in rows if predicate is None or predicate(row)]
    if not filtered:
        return (None, None, 0)

    by_session: dict[str, list[dict[str, Any]]] = {}
    for row in filtered:
        by_session.setdefault(_session_id(row), []).append(row)
    session_ids = sorted(by_session)
    if not session_ids:
        return (None, None, 0)

    point = sum(
        (1.0 if row["session_correct"] else 0.0) - (1.0 if row["baseline_correct"] else 0.0)
        for row in filtered
    ) / len(filtered)
    deltas: list[float] = []
    for _ in range(n_resamples):
        sampled_rows: list[dict[str, Any]] = []
        for _ in range(len(session_ids)):
            sampled_rows.extend(by_session[session_ids[rng.randrange(len(session_ids))]])
        deltas.append(
            sum(
                (1.0 if row["session_correct"] else 0.0) - (1.0 if row["baseline_correct"] else 0.0)
                for row in sampled_rows
            )
            / len(sampled_rows)
        )
    deltas.sort()
    return (
        point,
        [deltas[int(0.025 * n_resamples)], deltas[int(0.975 * n_resamples) - 1]],
        len(session_ids),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--session-jsonl", type=Path, required=True)
    parser.add_argument("--baseline-jsonl", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--paired-queries", type=Path, default=None)
    parser.add_argument("--n-resamples", type=int, default=5000)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--label", default=None)
    args = parser.parse_args()

    session_rows = _load_jsonl(args.session_jsonl)
    baseline_rows = _load_jsonl(args.baseline_jsonl)
    session_by_key = {_key(row): row for row in session_rows}
    baseline_by_key = {_key(row): row for row in baseline_rows}
    if set(session_by_key) != set(baseline_by_key):
        raise SystemExit(
            "session/baseline keys differ: "
            f"{sorted(set(session_by_key) ^ set(baseline_by_key))[:5]}"
        )

    keys = sorted(session_by_key)
    correctness_diffs = 0
    choice_diffs = 0
    mismatches: list[dict[str, Any]] = []
    session_follow_up_ms: list[float] = []
    session_follow_up_ms_by_session: dict[str, list[float]] = {}
    follow_up_rows_with_cache_build_ms = 0
    baseline_follow_up_ms: list[float] = []
    baseline_all_ms = [float(row["elapsed_ms"]) for row in baseline_rows]
    session_total_ms_by_session: dict[str, float] = {}
    baseline_total_ms_by_session: dict[str, float] = {}
    cache_build_ms_by_session: dict[str, dict[str, float]] = {}
    session_n_correct = sum(bool(row["correct"]) for row in session_rows)
    baseline_n_correct = sum(bool(row["correct"]) for row in baseline_rows)
    q_index_breakdown: dict[str, dict[str, Any]] = {}
    pathological_follow_up_hits = 0
    pathological_q3_hits = 0
    paired_rows: list[dict[str, Any]] = []

    for key in keys:
        session = session_by_key[key]
        baseline = baseline_by_key[key]
        sid = _session_id(session)
        session_total_ms_by_session[sid] = session_total_ms_by_session.get(sid, 0.0) + float(
            session["elapsed_ms"]
        )
        baseline_total_ms_by_session[sid] = baseline_total_ms_by_session.get(sid, 0.0) + float(
            baseline["elapsed_ms"]
        )
        if bool(session["correct"]) != bool(baseline["correct"]):
            correctness_diffs += 1
        if session.get("choice") != baseline.get("choice"):
            choice_diffs += 1
        q_index = int(session["q_index"])
        q_label = f"q{q_index + 1}"
        if q_label not in q_index_breakdown:
            q_index_breakdown[q_label] = {
                "n": 0,
                "correctness_diffs": 0,
                "choice_diffs": 0,
                "pathological_hits": 0,
            }
        q_index_breakdown[q_label]["n"] += 1
        if bool(session["correct"]) != bool(baseline["correct"]):
            q_index_breakdown[q_label]["correctness_diffs"] += 1
        if session.get("choice") != baseline.get("choice"):
            q_index_breakdown[q_label]["choice_diffs"] += 1
        if _is_pathological_like_response(session.get("response")):
            q_index_breakdown[q_label]["pathological_hits"] += 1
            if q_index > 0:
                pathological_follow_up_hits += 1
            if q_index == 2:
                pathological_q3_hits += 1
        if q_index > 0:
            session_elapsed_ms = float(session["elapsed_ms"])
            session_follow_up_ms.append(session_elapsed_ms)
            session_follow_up_ms_by_session.setdefault(sid, []).append(session_elapsed_ms)
            baseline_follow_up_ms.append(float(baseline["elapsed_ms"]))
            cache_build_ms = _optional_float(session, "base_cache_build_ms")
            if cache_build_ms is not None:
                follow_up_rows_with_cache_build_ms += 1
                cache_source = str(
                    session.get("cache_source") or session.get("reprefill_k") or f"q{q_index + 1}"
                )
                cache_build_ms_by_session.setdefault(sid, {}).setdefault(
                    cache_source,
                    cache_build_ms,
                )
        paired_rows.append(
            {
                "session_id": sid,
                "item_id": session["item_id"],
                "q_index": q_index,
                "session_choice": session.get("choice"),
                "baseline_choice": baseline.get("choice"),
                "session_correct": bool(session["correct"]),
                "baseline_correct": bool(baseline["correct"]),
                "session_response": session.get("response"),
                "baseline_response": baseline.get("response"),
                "session_elapsed_ms": float(session["elapsed_ms"]),
                "baseline_elapsed_ms": float(baseline["elapsed_ms"]),
                "session_base_cache_build_ms": _optional_float(
                    session,
                    "base_cache_build_ms",
                ),
            }
        )
        if bool(session["correct"]) != bool(baseline["correct"]) or session.get(
            "choice"
        ) != baseline.get("choice"):
            mismatches.append(
                {
                    "item_id": session["item_id"],
                    "q_index": q_index,
                    "session_choice": session.get("choice"),
                    "baseline_choice": baseline.get("choice"),
                    "session_correct": bool(session["correct"]),
                    "baseline_correct": bool(baseline["correct"]),
                }
            )

    session_follow_up_median_ms = _median(session_follow_up_ms)
    baseline_follow_up_median_ms = _median(baseline_follow_up_ms)
    baseline_all_query_median_ms = _median(baseline_all_ms)
    session_cache_build_total_ms_by_session = {
        sid: sum(cache_builds.values()) for sid, cache_builds in cache_build_ms_by_session.items()
    }
    if session_cache_build_total_ms_by_session:
        # Amortize each one-time cache build across that session's follow-up rows.
        session_follow_up_setup_amortized_ms = [
            (sum(session_follow_up_ms_by_session[sid]) + setup_ms)
            / len(session_follow_up_ms_by_session[sid])
            for sid, setup_ms in session_cache_build_total_ms_by_session.items()
            if sid in session_follow_up_ms_by_session and session_follow_up_ms_by_session[sid]
        ]
        session_total_including_cache_build_ms = [
            session_total_ms_by_session[sid] + setup_ms
            for sid, setup_ms in session_cache_build_total_ms_by_session.items()
            if sid in session_total_ms_by_session
        ]
        baseline_total_ms = [
            baseline_total_ms_by_session[sid]
            for sid in session_cache_build_total_ms_by_session
            if sid in baseline_total_ms_by_session
        ]
    else:
        session_follow_up_setup_amortized_ms = []
        session_total_including_cache_build_ms = []
        baseline_total_ms = []
    session_follow_up_setup_amortized_median_ms = _median(session_follow_up_setup_amortized_ms)
    session_total_including_cache_build_median_ms = _median(session_total_including_cache_build_ms)
    baseline_total_median_ms = _median(baseline_total_ms)
    rng = random.Random(args.seed)
    all_delta, all_ci, n_sessions = _paired_bootstrap_delta_ci(
        paired_rows,
        predicate=None,
        n_resamples=args.n_resamples,
        rng=rng,
    )
    follow_delta, follow_ci, _follow_sessions = _paired_bootstrap_delta_ci(
        paired_rows,
        predicate=lambda row: int(row["q_index"]) > 0,
        n_resamples=args.n_resamples,
        rng=rng,
    )
    q3_delta, q3_ci, _q3_sessions = _paired_bootstrap_delta_ci(
        paired_rows,
        predicate=lambda row: int(row["q_index"]) == 2,
        n_resamples=args.n_resamples,
        rng=rng,
    )
    output = {
        "label": args.label or args.session_jsonl.stem,
        "n_pairs": len(keys),
        "n_sessions": n_sessions,
        "n_follow_up_pairs": len(session_follow_up_ms),
        "session_n_correct": session_n_correct,
        "baseline_n_correct": baseline_n_correct,
        "session_accuracy": session_n_correct / len(keys) if keys else None,
        "baseline_accuracy": baseline_n_correct / len(keys) if keys else None,
        "paired_correctness_diffs": correctness_diffs,
        "paired_choice_diffs": choice_diffs,
        "pathological_follow_up_hits": pathological_follow_up_hits,
        "pathological_q3_hits": pathological_q3_hits,
        "accuracy_delta_session_minus_baseline": all_delta,
        "accuracy_delta_session_minus_baseline_ci95": all_ci,
        "follow_up_accuracy_delta_session_minus_baseline": follow_delta,
        "follow_up_accuracy_delta_session_minus_baseline_ci95": follow_ci,
        "q3_accuracy_delta_session_minus_baseline": q3_delta,
        "q3_accuracy_delta_session_minus_baseline_ci95": q3_ci,
        "session_follow_up_median_ms": session_follow_up_median_ms,
        "session_follow_up_setup_amortized_median_ms": (
            session_follow_up_setup_amortized_median_ms
        ),
        "baseline_follow_up_median_ms": baseline_follow_up_median_ms,
        "baseline_all_query_median_ms": baseline_all_query_median_ms,
        "n_follow_up_rows_with_cache_build_ms": follow_up_rows_with_cache_build_ms,
        "n_sessions_with_cache_build_ms": len(session_cache_build_total_ms_by_session),
        "session_cache_build_total_median_ms": _median(
            list(session_cache_build_total_ms_by_session.values())
        ),
        "session_total_median_ms_including_cache_build": (
            session_total_including_cache_build_median_ms
        ),
        "baseline_total_median_ms": baseline_total_median_ms,
        "speedup_follow_up_median_cold_over_session": (
            baseline_follow_up_median_ms / session_follow_up_median_ms
            if baseline_follow_up_median_ms is not None
            and session_follow_up_median_ms is not None
            and session_follow_up_median_ms > 0
            else None
        ),
        "speedup_all_query_median_cold_over_session_follow_up": (
            baseline_all_query_median_ms / session_follow_up_median_ms
            if baseline_all_query_median_ms is not None
            and session_follow_up_median_ms is not None
            and session_follow_up_median_ms > 0
            else None
        ),
        "speedup_follow_up_median_cold_over_session_setup_amortized": (
            baseline_follow_up_median_ms / session_follow_up_setup_amortized_median_ms
            if baseline_follow_up_median_ms is not None
            and session_follow_up_setup_amortized_median_ms is not None
            and session_follow_up_setup_amortized_median_ms > 0
            else None
        ),
        "speedup_all_query_median_cold_over_session_follow_up_setup_amortized": (
            baseline_all_query_median_ms / session_follow_up_setup_amortized_median_ms
            if baseline_all_query_median_ms is not None
            and session_follow_up_setup_amortized_median_ms is not None
            and session_follow_up_setup_amortized_median_ms > 0
            else None
        ),
        "speedup_session_total_median_cold_over_session_including_cache_build": (
            baseline_total_median_ms / session_total_including_cache_build_median_ms
            if baseline_total_median_ms is not None
            and session_total_including_cache_build_median_ms is not None
            and session_total_including_cache_build_median_ms > 0
            else None
        ),
        "q_index_breakdown": q_index_breakdown,
        "mismatches": mismatches,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2) + "\n")
    if args.paired_queries is not None:
        args.paired_queries.parent.mkdir(parents=True, exist_ok=True)
        with args.paired_queries.open("w") as handle:
            for row in paired_rows:
                handle.write(json.dumps(row) + "\n")
        print(f"[selective-reprefill] wrote {args.paired_queries}")
    print(f"[selective-reprefill] wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
