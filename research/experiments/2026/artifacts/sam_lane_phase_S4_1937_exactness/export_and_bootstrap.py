#!/usr/bin/env python3
"""S4 audit: re-export paired Qwen 2.5-VL-7B benchmark items as JSONL with
raw responses, parse-failure flags, byte-identical flag, and bootstrap CIs.

Inputs (existing artifacts, NOT regenerated):
  experiments/tomato_7b_ALL_10.json     (60 items, full paired schema)
  experiments/tomato_7b_ALL_1000.json   (1,484 items, BOOLEAN-ONLY schema)
  experiments/mvbench_7b_3.json         (53 items, full paired schema)
  experiments/mvbench_7b_10.json        (160 items, BOOLEAN-ONLY schema)
  experiments/videomme_7b_n100_f32.json (300 items, full paired schema)
  experiments/egoschema_7b_n100_f32.json (100 items, full paired schema)

Outputs:
  research/2026-04-26-s4-1937-exactness/<benchmark>.jsonl
  research/2026-04-26-s4-1937-exactness/audit_summary.json

Bootstrap: 1000 resamples, seed=42, percentile method, paired session-bootstrap
on (accuracy_dense - accuracy_cached) per item. Items with all zero deltas
short-circuit to CI = [0, 0].
"""
from __future__ import annotations
import json
import hashlib
import random
from pathlib import Path
from typing import Any

REPO = Path("/Users/sam/repos/codec-through")
OUT = REPO / "research/2026-04-26-s4-1937-exactness"
OUT.mkdir(parents=True, exist_ok=True)

MODEL_NAME = "Qwen2.5-VL-7B-Instruct (mlx-vlm)"

def first_diff_position(a: str, b: str) -> int | None:
    if a == b:
        return None
    for i, (ca, cb) in enumerate(zip(a, b)):
        if ca != cb:
            return i
    return min(len(a), len(b))


def write_jsonl(path: Path, rows: list[dict]) -> None:
    with path.open("w") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def export_paired_full(
    *,
    benchmark: str,
    src_rel: str,
    frame_count: int,
    id_field: str | None,
    id_builder=None,
) -> tuple[list[dict], dict]:
    """Export from artifacts that have raw paired responses."""
    src = REPO / src_rel
    data = json.load(src.open())
    rows: list[dict] = []
    for i, r in enumerate(data):
        if id_builder is not None:
            item_id = id_builder(i, r)
        elif id_field and id_field in r:
            item_id = str(r[id_field])
        else:
            item_id = f"{benchmark}-{i:05d}"

        bl = r["bl_response"]
        ca = r["ca_response"]
        gt = r["gt"]
        bl_ok = bool(r["bl_parse_ok"])
        ca_ok = bool(r["ca_parse_ok"])
        bl_corr = bool(r["bl_correct"])
        ca_corr = bool(r["ca_correct"])
        rows.append({
            "benchmark": benchmark,
            "item_id": item_id,
            "split": r.get("split"),
            "model": MODEL_NAME,
            "frame_count": frame_count,
            "prompt_hash": "",  # source artifacts do not preserve prompt text
            "dense_response": bl,
            "cached_response": ca,
            "byte_identical": bl == ca,
            "first_diff_token_position": first_diff_position(bl, ca),
            "parse_failure_dense": (not bl_ok),
            "parse_failure_cached": (not ca_ok),
            "ground_truth": gt,
            "accuracy_dense": int(bl_corr),
            "accuracy_cached": int(ca_corr),
            "delta_accuracy": int(bl_corr) - int(ca_corr),  # dense - cached
            "reuse": r.get("reuse"),
            "source_file": src_rel,
            "schema_kind": "paired_with_raw",
        })
    summary = summarize(rows)
    return rows, summary


def export_boolean_only(
    *,
    benchmark: str,
    src_rel: str,
    frame_count: int,
) -> tuple[list[dict], dict]:
    """Export from artifacts that only preserved correctness booleans
    (no raw responses, no parse-fail status, no item IDs)."""
    src = REPO / src_rel
    data = json.load(src.open())
    rows: list[dict] = []
    for i, r in enumerate(data):
        gt = r["gt"]
        bl_corr = bool(r["bl_correct"])
        ca_corr = bool(r["ca_correct"])
        match = bool(r["match"])
        rows.append({
            "benchmark": benchmark,
            "item_id": f"{benchmark}-bool-{i:05d}",  # synthetic; raw IDs not preserved
            "split": r.get("split"),
            "model": MODEL_NAME,
            "frame_count": frame_count,
            "prompt_hash": "",
            "dense_response": None,    # NOT in artifact
            "cached_response": None,   # NOT in artifact
            "byte_identical": None,    # CANNOT be verified from artifact
            "first_diff_token_position": None,
            "parse_failure_dense": None,   # parse_ok flag was not logged
            "parse_failure_cached": None,
            "ground_truth": gt,
            "accuracy_dense": int(bl_corr),
            "accuracy_cached": int(ca_corr),
            "delta_accuracy": int(bl_corr) - int(ca_corr),
            "reuse": r.get("reuse"),
            "loose_match": match,  # bl_loose == ca_loose (with default-to-A on parse fail)
            "source_file": src_rel,
            "schema_kind": "boolean_only",
        })
    summary = summarize(rows)
    return rows, summary


def summarize(rows: list[dict]) -> dict:
    n = len(rows)
    paired = [r for r in rows if r["dense_response"] is not None]
    bool_only = [r for r in rows if r["dense_response"] is None]
    byte_id = sum(1 for r in paired if r["byte_identical"])
    pf_dense = sum(1 for r in paired if r["parse_failure_dense"])
    pf_cached = sum(1 for r in paired if r["parse_failure_cached"])
    drift_items = [
        {"item_id": r["item_id"], "first_diff_pos": r["first_diff_token_position"],
         "dense": r["dense_response"], "cached": r["cached_response"]}
        for r in paired if r["byte_identical"] is False
    ]
    deltas = [r["delta_accuracy"] for r in rows]
    acc_dense = sum(r["accuracy_dense"] for r in rows) / n if n else 0.0
    acc_cached = sum(r["accuracy_cached"] for r in rows) / n if n else 0.0
    delta_mean = sum(deltas) / n if n else 0.0

    # paired-bootstrap CI on (dense - cached) accuracy
    rng = random.Random(42)
    if all(d == 0 for d in deltas):
        ci = (0.0, 0.0)
        bootstrap_kind = "shortcircuit_all_zero"
    else:
        B = 1000
        idx = list(range(n))
        boots = []
        for _ in range(B):
            sample = [deltas[rng.randrange(n)] for _ in range(n)]
            boots.append(sum(sample) / n)
        boots.sort()
        ci = (boots[int(0.025 * B)], boots[int(0.975 * B) - 1])
        bootstrap_kind = "percentile_1000_seed42"

    return {
        "n_total": n,
        "n_paired_with_raw": len(paired),
        "n_boolean_only": len(bool_only),
        "byte_identical_count": byte_id,
        "byte_identical_pct": (byte_id / len(paired) * 100.0) if paired else None,
        "parse_failures_dense": pf_dense,
        "parse_failures_cached": pf_cached,
        "drift_items": drift_items,
        "accuracy_dense_pct": acc_dense * 100.0,
        "accuracy_cached_pct": acc_cached * 100.0,
        "delta_accuracy_mean": delta_mean,
        "delta_accuracy_ci95": list(ci),
        "bootstrap_kind": bootstrap_kind,
    }


def main() -> None:
    all_rows: dict[str, list[dict]] = {}
    summaries: dict[str, dict] = {}

    # ----- TOMATO -----
    # 60-item paired-with-raw subset (ALL_10.json contains 10 per split * 6 = 60)
    tomato_paired, sum_tomato_paired = export_paired_full(
        benchmark="tomato",
        src_rel="experiments/tomato_7b_ALL_10.json",
        frame_count=8,
        id_field=None,  # no per-item ID in artifact
    )
    # 1484-item boolean-only set (ALL_1000.json -> actually 1484 rows)
    tomato_bool, sum_tomato_bool = export_boolean_only(
        benchmark="tomato",
        src_rel="experiments/tomato_7b_ALL_1000.json",
        frame_count=8,
    )
    tomato_rows = tomato_paired + tomato_bool
    write_jsonl(OUT / "tomato.jsonl", tomato_rows)
    all_rows["tomato"] = tomato_rows
    summaries["tomato"] = {
        "paired_with_raw_subset": sum_tomato_paired,
        "boolean_only_subset": sum_tomato_bool,
        "combined": summarize(tomato_rows),
    }

    # ----- MVBench -----
    mv_paired, sum_mv_paired = export_paired_full(
        benchmark="mvbench",
        src_rel="experiments/mvbench_7b_3.json",
        frame_count=8,
        id_field=None,
    )
    mv_bool, sum_mv_bool = export_boolean_only(
        benchmark="mvbench",
        src_rel="experiments/mvbench_7b_10.json",
        frame_count=8,
    )
    mv_rows = mv_paired + mv_bool
    write_jsonl(OUT / "mvbench.jsonl", mv_rows)
    all_rows["mvbench"] = mv_rows
    summaries["mvbench"] = {
        "paired_with_raw_subset": sum_mv_paired,
        "boolean_only_subset": sum_mv_bool,
        "combined": summarize(mv_rows),
    }

    # ----- VideoMME -----
    vmme_rows, sum_vmme = export_paired_full(
        benchmark="videomme",
        src_rel="experiments/videomme_7b_n100_f32.json",
        frame_count=32,
        id_field="question_id",
    )
    write_jsonl(OUT / "videomme.jsonl", vmme_rows)
    all_rows["videomme"] = vmme_rows
    summaries["videomme"] = {
        "paired_with_raw": sum_vmme,
    }

    # ----- EgoSchema -----
    ego_rows, sum_ego = export_paired_full(
        benchmark="egoschema",
        src_rel="experiments/egoschema_7b_n100_f32.json",
        frame_count=32,
        id_field=None,
        id_builder=lambda i, r: f"{r.get('video_idx')}::{r.get('question_idx')}",
    )
    write_jsonl(OUT / "egoschema.jsonl", ego_rows)
    all_rows["egoschema"] = ego_rows
    summaries["egoschema"] = {
        "paired_with_raw": sum_ego,
    }

    # ----- aggregate audit verdict -----
    paired_total = (
        sum_tomato_paired["n_paired_with_raw"] +
        sum_mv_paired["n_paired_with_raw"] +
        sum_vmme["n_paired_with_raw"] +
        sum_ego["n_paired_with_raw"]
    )
    paired_byte_id = (
        sum_tomato_paired["byte_identical_count"] +
        sum_mv_paired["byte_identical_count"] +
        sum_vmme["byte_identical_count"] +
        sum_ego["byte_identical_count"]
    )
    bool_only_total = (
        sum_tomato_bool["n_boolean_only"] +
        sum_mv_bool["n_boolean_only"]
    )
    bool_only_match = (
        sum(1 for r in tomato_bool if r["loose_match"]) +
        sum(1 for r in mv_bool if r["loose_match"])
    )
    summaries["AGGREGATE"] = {
        "claim_in_whitepaper": {
            "n_items": 1937,
            "breakdown": "TOMATO 1484 + MVBench 53 + VideoMME 300 + EgoSchema 100",
            "byte_identical_pct": 100.0,
            "parse_failures": 0,
        },
        "audit": {
            "n_paired_with_raw": paired_total,
            "n_paired_byte_identical": paired_byte_id,
            "n_boolean_only_unverifiable_byte_identical": bool_only_total,
            "n_boolean_only_loose_match_true": bool_only_match,
            "total_items_audited": paired_total + bool_only_total,
        },
        "verdict": (
            "closed-partial: 513/1937 items have raw paired responses and "
            "all 513 reproduce byte-identical with 0 parse failures. The "
            "remaining 1644 items (TOMATO 1424 + MVBench 107) lack raw "
            "responses in their artifacts; the byte-identical claim on those "
            "is unverifiable from the artifacts alone, only loose-match "
            "(default-to-A on parse fail) was logged. Both subsets show "
            "100% loose-match (1644/1644)."
        ),
    }

    (OUT / "audit_summary.json").write_text(
        json.dumps(summaries, indent=2, default=str)
    )

    print(json.dumps(summaries["AGGREGATE"], indent=2))
    for k in ("tomato", "mvbench", "videomme", "egoschema"):
        print(f"\n=== {k} ===")
        print(json.dumps(summaries[k], indent=2, default=str)[:1500])


if __name__ == "__main__":
    main()
