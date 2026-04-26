#!/usr/bin/env python3
"""Analyze low-FPS dense VideoMME session baselines against an 8f dense reference."""

from __future__ import annotations

import argparse
import json
import random
from collections import defaultdict
from collections.abc import Callable
from pathlib import Path
from typing import Any


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open() as handle:
        for line in handle:
            stripped = line.strip()
            if stripped:
                rows.append(json.loads(stripped))
    return rows


def _key(row: dict[str, Any]) -> tuple[str, int]:
    return str(row["seed_item_id"]), int(row["q_index"])


def _index_rows(rows: list[dict[str, Any]], *, label: str) -> dict[tuple[str, int], dict[str, Any]]:
    indexed: dict[tuple[str, int], dict[str, Any]] = {}
    for row in rows:
        key = _key(row)
        if key in indexed:
            raise ValueError(f"duplicate {label} row for key {key!r}")
        indexed[key] = row
    return indexed


def _paired_rows(
    reference_rows: list[dict[str, Any]], candidate_rows: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    reference = _index_rows(reference_rows, label="reference")
    candidate = _index_rows(candidate_rows, label="candidate")
    if set(reference) != set(candidate):
        missing_candidate = sorted(set(reference) - set(candidate))
        missing_reference = sorted(set(candidate) - set(reference))
        raise ValueError(
            "reference/candidate key mismatch: "
            f"missing_candidate={missing_candidate[:5]}, "
            f"missing_reference={missing_reference[:5]}"
        )

    paired: list[dict[str, Any]] = []
    for key in sorted(reference):
        ref = reference[key]
        cand = candidate[key]
        paired.append(
            {
                "seed_item_id": key[0],
                "q_index": key[1],
                "duration": ref.get("duration"),
                "item_id": ref.get("item_id"),
                "reference_choice": ref.get("choice"),
                "candidate_choice": cand.get("choice"),
                "reference_correct": bool(ref.get("correct", False)),
                "candidate_correct": bool(cand.get("correct", False)),
                "reference_parse_failure": bool(ref.get("parse_failure", False)),
                "candidate_parse_failure": bool(cand.get("parse_failure", False)),
                "reference_degenerate": bool(ref.get("degenerate", False)),
                "candidate_degenerate": bool(cand.get("degenerate", False)),
                "reference_end_to_end_ms": float(ref.get("end_to_end_ms", 0.0)),
                "candidate_end_to_end_ms": float(cand.get("end_to_end_ms", 0.0)),
                "reference_prompt_tokens": ref.get("prompt_tokens"),
                "candidate_prompt_tokens": cand.get("prompt_tokens"),
            }
        )
    return paired


def _accuracy(rows: list[dict[str, Any]], key: str) -> float:
    if not rows:
        return 0.0
    return sum(bool(row[key]) for row in rows) / len(rows)


def _delta(rows: list[dict[str, Any]]) -> float:
    return _accuracy(rows, "candidate_correct") - _accuracy(rows, "reference_correct")


def _bootstrap_ci(
    rows: list[dict[str, Any]],
    *,
    predicate: Callable[[dict[str, Any]], bool] | None = None,
    n_bootstrap: int = 10_000,
    seed: int = 20260427,
) -> list[float]:
    filtered = [row for row in rows if predicate is None or predicate(row)]
    if not filtered:
        return [0.0, 0.0]
    by_session: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in filtered:
        by_session[str(row["seed_item_id"])].append(row)
    session_ids = sorted(by_session)
    rng = random.Random(seed)
    samples: list[float] = []
    for _ in range(n_bootstrap):
        boot_rows: list[dict[str, Any]] = []
        for session_id in rng.choices(session_ids, k=len(session_ids)):
            boot_rows.extend(by_session[session_id])
        samples.append(_delta(boot_rows))
    samples.sort()
    lo = samples[int(0.025 * (len(samples) - 1))]
    hi = samples[int(0.975 * (len(samples) - 1))]
    return [lo, hi]


def _slice_summary(
    rows: list[dict[str, Any]],
    *,
    predicate: Callable[[dict[str, Any]], bool],
    label: str,
) -> dict[str, Any]:
    sliced = [row for row in rows if predicate(row)]
    if not sliced:
        return {"label": label, "n": 0}
    ref_ms = sum(float(row["reference_end_to_end_ms"]) for row in sliced)
    cand_ms = sum(float(row["candidate_end_to_end_ms"]) for row in sliced)
    return {
        "label": label,
        "n": len(sliced),
        "reference_accuracy": _accuracy(sliced, "reference_correct"),
        "candidate_accuracy": _accuracy(sliced, "candidate_correct"),
        "accuracy_delta_candidate_minus_reference": _delta(sliced),
        "accuracy_delta_candidate_minus_reference_ci95": _bootstrap_ci(rows, predicate=predicate),
        "choice_agreement": sum(
            row["reference_choice"] == row["candidate_choice"] for row in sliced
        )
        / len(sliced),
        "reference_total_end_to_end_ms": ref_ms,
        "candidate_total_end_to_end_ms": cand_ms,
        "speedup_reference_over_candidate": ref_ms / cand_ms if cand_ms > 0 else None,
    }


def _outcome(delta: float, *, pass_format: bool) -> str:
    if not pass_format:
        return "format_invalid"
    if delta >= -0.05:
        return "low_fps_competitive"
    if delta <= -0.10:
        return "low_fps_rejected"
    return "ambiguous"


def _duration_predicate(duration: str) -> Callable[[dict[str, Any]], bool]:
    def predicate(row: dict[str, Any]) -> bool:
        return str(row.get("duration")) == duration

    return predicate


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference-jsonl", type=Path, required=True)
    parser.add_argument("--candidate-jsonl", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--paired-queries", type=Path, default=None)
    args = parser.parse_args()

    reference_rows = _load_jsonl(args.reference_jsonl)
    candidate_rows = _load_jsonl(args.candidate_jsonl)
    rows = _paired_rows(reference_rows, candidate_rows)
    if not rows:
        raise SystemExit("no paired rows")

    reference_frame_counts = sorted({int(row["frame_count"]) for row in reference_rows})
    candidate_frame_counts = sorted({int(row["frame_count"]) for row in candidate_rows})
    if len(reference_frame_counts) != 1 or len(candidate_frame_counts) != 1:
        raise ValueError(
            "expected one frame count per arm: "
            f"reference={reference_frame_counts}, candidate={candidate_frame_counts}"
        )

    all_summary = _slice_summary(rows, predicate=lambda row: True, label="all")
    payload = {
        "reference_jsonl": args.reference_jsonl.as_posix(),
        "candidate_jsonl": args.candidate_jsonl.as_posix(),
        "reference_frame_count": reference_frame_counts[0],
        "candidate_frame_count": candidate_frame_counts[0],
        "n_paired_queries": len(rows),
        "n_paired_sessions": len({row["seed_item_id"] for row in rows}),
        "parse_failures": {
            "reference": sum(row["reference_parse_failure"] for row in rows),
            "candidate": sum(row["candidate_parse_failure"] for row in rows),
        },
        "degenerates": {
            "reference": sum(row["reference_degenerate"] for row in rows),
            "candidate": sum(row["candidate_degenerate"] for row in rows),
        },
        "all": all_summary,
        "first_queries": _slice_summary(
            rows, predicate=lambda row: int(row["q_index"]) == 0, label="first_queries"
        ),
        "follow_ups": _slice_summary(
            rows, predicate=lambda row: int(row["q_index"]) > 0, label="follow_ups"
        ),
        "by_duration": {},
    }
    for duration in sorted({str(row.get("duration")) for row in rows}):
        payload["by_duration"][duration] = _slice_summary(
            rows,
            predicate=_duration_predicate(duration),
            label=duration,
        )
    payload["pass_complete_pairing"] = len(rows) == 171 and payload["n_paired_sessions"] == 57
    payload["pass_format"] = (
        payload["parse_failures"]["reference"] == 0
        and payload["parse_failures"]["candidate"] == 0
        and payload["degenerates"]["reference"] == 0
        and payload["degenerates"]["candidate"] == 0
    )
    delta = float(all_summary["accuracy_delta_candidate_minus_reference"])
    payload["outcome"] = _outcome(delta, pass_format=bool(payload["pass_format"]))

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    if args.paired_queries is not None:
        with args.paired_queries.open("w") as handle:
            for row in rows:
                handle.write(json.dumps(row, sort_keys=True) + "\n")
    print(f"[1.62D] wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
