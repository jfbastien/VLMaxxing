#!/usr/bin/env python3
"""Build paper-facing per-item drift summary data from landed artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open() as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def _index(
    rows: list[dict[str, Any]], *, key_fields: tuple[str, ...]
) -> dict[tuple[str, ...], dict[str, Any]]:
    return {tuple(str(row[field]) for field in key_fields): row for row in rows}


def _is_pathological_like(text: str | None) -> bool:
    rendered = str(text or "")
    # "自动" catches the observed 自动生成 ("auto-generated") basin attractor.
    return "addCriterion" in rendered or "自动" in rendered


def _phase_130_v_only_q0(artifact_dir: Path) -> dict[str, Any]:
    dense_rows = _load_jsonl(artifact_dir / "cold_dense.jsonl")
    pruned_rows = _load_jsonl(artifact_dir / "cold_pruned.jsonl")
    dense = _index(
        [row for row in dense_rows if int(row["q_index"]) == 0],
        key_fields=("seed_item_id", "q_index"),
    )
    pruned = _index(
        [row for row in pruned_rows if int(row["q_index"]) == 0],
        key_fields=("seed_item_id", "q_index"),
    )
    keys = sorted(set(dense) & set(pruned))
    choice_changed = sum(1 for key in keys if dense[key].get("choice") != pruned[key].get("choice"))
    correctness_changed = sum(
        1 for key in keys if bool(dense[key]["correct"]) != bool(pruned[key]["correct"])
    )
    return {
        "label": "1.30 Phase A V-only Q0",
        "n": len(keys),
        "choice_changed": choice_changed,
        "choice_change_rate": choice_changed / len(keys) if keys else None,
        "correctness_changed": correctness_changed,
        "correctness_change_rate": correctness_changed / len(keys) if keys else None,
        "note": "Q0-only slice of the short root-cause decomposition (cold_dense vs cold_pruned).",
    }


def _phase_142_gemma_mvbench(results_path: Path) -> dict[str, Any]:
    rows = _load_jsonl(results_path)
    choice_changed = 0
    correctness_changed = 0
    dense_correct = 0
    cached_correct = 0
    by_group: dict[str, int] = {}
    for row in rows:
        dense_choice = row["dense"].get("choice_index")
        cached_choice = row["cached"].get("choice_index")
        if dense_choice != cached_choice:
            choice_changed += 1
            group = str(row["group"])
            by_group[group] = by_group.get(group, 0) + 1
        dense_ok = bool(row["dense"]["correct"])
        cached_ok = bool(row["cached"]["correct"])
        dense_correct += int(dense_ok)
        cached_correct += int(cached_ok)
        if dense_ok != cached_ok:
            correctness_changed += 1
    n = len(rows)
    return {
        "label": "1.42 Gemma MVBench holdout",
        "n": n,
        "choice_changed": choice_changed,
        "choice_change_rate": choice_changed / n if n else None,
        "correctness_changed": correctness_changed,
        "correctness_change_rate": correctness_changed / n if n else None,
        "dense_accuracy": dense_correct / n if n else None,
        "cached_accuracy": cached_correct / n if n else None,
        "changed_by_group": by_group,
        "note": (
            "Aggregate accuracy is preserved while answer identity drifts across four MVBench "
            "motion subgroups."
        ),
    }


def _phase_155a_persistent_kv(session_path: Path, baseline_path: Path) -> dict[str, Any]:
    session_rows = _load_jsonl(session_path)
    baseline_rows = _load_jsonl(baseline_path)
    session = _index(session_rows, key_fields=("item_id",))
    baseline = _index(baseline_rows, key_fields=("item_id",))
    keys = sorted(set(session) & set(baseline))
    pathological_count = 0
    empty_count = 0
    choice_changed = 0
    correctness_changed = 0
    q_index_breakdown: dict[str, dict[str, int]] = {}
    for key in keys:
        session_row = session[key]
        baseline_row = baseline[key]
        q_label = f"q{int(session_row['q_index']) + 1}"
        bucket = q_index_breakdown.setdefault(
            q_label,
            {
                "n": 0,
                "pathological_like": 0,
                "empty_response": 0,
                "choice_changed": 0,
                "correctness_changed": 0,
            },
        )
        bucket["n"] += 1
        pathological = _is_pathological_like(session_row.get("response"))
        empty = str(session_row.get("response", "")).strip() == ""
        if pathological:
            pathological_count += 1
            bucket["pathological_like"] += 1
        if empty:
            empty_count += 1
            bucket["empty_response"] += 1
        if session_row.get("choice") != baseline_row.get("choice"):
            choice_changed += 1
            bucket["choice_changed"] += 1
        if bool(session_row["correct"]) != bool(baseline_row["correct"]):
            correctness_changed += 1
            bucket["correctness_changed"] += 1
    n = len(keys)
    return {
        "label": "1.55A persistent-KV 20f",
        "n": n,
        "choice_changed": choice_changed,
        "choice_change_rate": choice_changed / n if n else None,
        "correctness_changed": correctness_changed,
        "correctness_change_rate": correctness_changed / n if n else None,
        "pathological_like": pathological_count,
        "pathological_like_rate": pathological_count / n if n else None,
        "empty_response": empty_count,
        "empty_response_rate": empty_count / n if n else None,
        "q_index_breakdown": q_index_breakdown,
        "note": (
            "Persistent-KV failure at 20f is not just a scalar accuracy drop; it is a "
            "distributional drift into pathological attractors concentrated on follow-ups."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--rootcause-dir",
        type=Path,
        default=Path(
            "research/experiments/2026/artifacts/phase1_30_rootcause_short_codex_20260423"
        ),
    )
    parser.add_argument(
        "--gemma-mvbench-results",
        type=Path,
        default=Path(
            "research/experiments/2026/artifacts/"
            "phase1_42_gemma_mvbench_motion_holdout_v2_mc_cached/results.jsonl"
        ),
    )
    parser.add_argument(
        "--persistent-kv-session",
        type=Path,
        default=Path(
            "research/experiments/2026/artifacts/phase1_55A_20f_frame_scaling/"
            "session_qwen7b_n7.jsonl"
        ),
    )
    parser.add_argument(
        "--persistent-kv-baseline",
        type=Path,
        default=Path(
            "research/experiments/2026/artifacts/phase1_55A_20f_frame_scaling/"
            "baseline_qwen7b_n7.jsonl"
        ),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("research/experiments/2026/artifacts/phase1_61_per_item_drift_summary.json"),
    )
    args = parser.parse_args()

    payload = {
        "phase": "1.61",
        "title": "Per-item drift summary",
        "panels": [
            _phase_130_v_only_q0(args.rootcause_dir),
            _phase_142_gemma_mvbench(args.gemma_mvbench_results),
            _phase_155a_persistent_kv(args.persistent_kv_session, args.persistent_kv_baseline),
        ],
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + "\n")
    print(f"[1.61] wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
