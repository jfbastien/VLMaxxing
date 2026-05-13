#!/usr/bin/env python3
"""Artifact-level OV-8 session accounting.

Combines an OV-6 first-query sparse-vision cell with existing C-PERSIST
follow-up timing artifacts. This is accounting-only: it does not run models and
does not imply the two mechanisms have been executed in one live session.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, cast

DEFAULT_DENSE = Path("research/experiments/2026/artifacts/phase1_51V_ov6_n57/dense")
DEFAULT_SPARSE = Path(
    "research/experiments/2026/artifacts/phase1_51V_ov6_n57_kr070_l2/codec_novel_coded"
)
DEFAULT_CPERSIST = Path(
    "research/experiments/2026/artifacts/phase1_55L_many_turn_cpersist/summary.json"
)
DEFAULT_OUT = Path("research/experiments/2026/artifacts/onevision_cpersist_session")
QUERY_COUNTS = (1, 2, 5, 10, 50)


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(path)
    payload = json.loads(path.read_text())
    if not isinstance(payload, dict):
        raise ValueError(f"JSON root is not an object: {path}")
    return cast(dict[str, Any], payload)


def _load_jsonl_by_item(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(path)
    rows: dict[str, dict[str, Any]] = {}
    with path.open() as handle:
        for line in handle:
            payload = json.loads(line)
            if not isinstance(payload, dict):
                raise ValueError(f"JSONL row is not an object: {path}")
            item_id = str(payload["item_id"])
            if item_id in rows:
                raise ValueError(f"duplicate item_id {item_id} in {path}")
            rows[item_id] = cast(dict[str, Any], payload)
    return rows


def _first_query_pairing(*, dense_dir: Path, sparse_dir: Path) -> dict[str, Any]:
    dense_rows = _load_jsonl_by_item(dense_dir / "results.jsonl")
    sparse_rows = _load_jsonl_by_item(sparse_dir / "results.jsonl")
    if set(dense_rows) != set(sparse_rows):
        raise ValueError(
            "dense/sparse first-query item mismatch: "
            f"dense_only={sorted(set(dense_rows) - set(sparse_rows))[:5]} "
            f"sparse_only={sorted(set(sparse_rows) - set(dense_rows))[:5]}"
        )
    choice_drift = 0
    correctness_drift = 0
    sparse_correct_dense_wrong = 0
    sparse_wrong_dense_correct = 0
    dense_parse_failures = 0
    sparse_parse_failures = 0
    for item_id in sorted(dense_rows):
        dense = dense_rows[item_id]
        sparse = sparse_rows[item_id]
        dense_correct = bool(dense["correct"])
        sparse_correct = bool(sparse["correct"])
        dense_parse_failures += int(bool(dense.get("parse_failure", False)))
        sparse_parse_failures += int(bool(sparse.get("parse_failure", False)))
        choice_drift += int(dense.get("choice_index") != sparse.get("choice_index"))
        correctness_drift += int(dense_correct != sparse_correct)
        sparse_correct_dense_wrong += int(sparse_correct and not dense_correct)
        sparse_wrong_dense_correct += int(dense_correct and not sparse_correct)
    return {
        "n": len(dense_rows),
        "choice_drift": choice_drift,
        "correctness_drift": correctness_drift,
        "dense_parse_failures": dense_parse_failures,
        "sparse_parse_failures": sparse_parse_failures,
        "sparse_correct_dense_wrong": sparse_correct_dense_wrong,
        "sparse_wrong_dense_correct": sparse_wrong_dense_correct,
    }


def _select_cpersist_cells(summary: dict[str, Any], *, horizon: int) -> list[dict[str, Any]]:
    cells = [cell for cell in summary.get("cells", []) if int(cell.get("horizon", -1)) == horizon]
    if not cells:
        raise ValueError(f"no C-PERSIST cells found at horizon={horizon}")
    return cells


def _session_curve(
    *,
    dense_first_ms: float,
    sparse_first_ms: float,
    follow_ms: float,
) -> list[dict[str, float]]:
    rows: list[dict[str, float]] = []
    for q in QUERY_COUNTS:
        dense_total = q * dense_first_ms
        sparse_total = sparse_first_ms + (q - 1) * follow_ms
        rows.append(
            {
                "n_total_queries": float(q),
                "dense_cold_every_query_ms": float(dense_total),
                "sparse_first_plus_cpersist_followups_ms": float(sparse_total),
                "speedup_dense_over_combined": float(dense_total / max(sparse_total, 1e-12)),
            }
        )
    return rows


def build_payload(
    *,
    dense_dir: Path,
    sparse_dir: Path,
    cpersist_summary_path: Path,
    horizon: int,
) -> dict[str, Any]:
    dense_summary = _load_json(dense_dir / "summary.json")
    sparse_summary = _load_json(sparse_dir / "summary.json")
    cpersist_summary = _load_json(cpersist_summary_path)
    cpersist_cells = _select_cpersist_cells(cpersist_summary, horizon=horizon)

    dense_first_ms = float(dense_summary["mean_dense_end_to_end_ms"])
    sparse_first_excluding_codec_ms = float(sparse_summary["mean_dense_end_to_end_ms"])
    codec_extract_s = sparse_summary.get("codec_extract_mean_s_per_item")
    sidecar_load_s = sparse_summary.get("codec_sidecar_load_mean_s_per_item")
    runtime_source = sparse_summary.get("codec_score_runtime_source")
    if runtime_source not in {None, "live_pyav", "sidecar"}:
        raise ValueError(f"unknown codec_score_runtime_source: {runtime_source!r}")
    if runtime_source == "live_pyav" and codec_extract_s is None:
        raise ValueError("live_pyav sparse source is missing codec_extract_mean_s_per_item")
    if runtime_source == "sidecar" and sidecar_load_s is None:
        raise ValueError("sidecar sparse source is missing codec_sidecar_load_mean_s_per_item")
    sparse_first_including_codec_ms = sparse_first_excluding_codec_ms + (
        float(codec_extract_s) * 1000.0 if codec_extract_s is not None else 0.0
    )
    sparse_first_including_runtime_score_ms = float(
        sparse_summary.get(
            "mean_end_to_end_including_codec_score_runtime_ms",
            sparse_first_including_codec_ms,
        )
    )
    first_query_pairing = _first_query_pairing(dense_dir=dense_dir, sparse_dir=sparse_dir)

    rows: list[dict[str, Any]] = []
    for cell in cpersist_cells:
        follow = cell.get("followup_only", {})
        follow_ms = float(follow["median_total_elapsed_ms"])
        row_base = {
            "policy": cell["policy"],
            "horizon": int(cell["horizon"]),
            "followup_median_ms": follow_ms,
            "followup_choice_drift": int(follow.get("choice_drift", 0)),
            "followup_correctness_drift": int(follow.get("correctness_drift", 0)),
            "followup_n": int(follow.get("n", 0)),
            "followup_pathological": int(follow.get("pathological", 0)),
        }
        rows.append(
            {
                **row_base,
                "codec_extraction_policy": "excluded_model_side",
                "first_query_ms": sparse_first_excluding_codec_ms,
                "session_curve": _session_curve(
                    dense_first_ms=dense_first_ms,
                    sparse_first_ms=sparse_first_excluding_codec_ms,
                    follow_ms=follow_ms,
                ),
            }
        )
        if codec_extract_s is not None:
            rows.append(
                {
                    **row_base,
                    "codec_extraction_policy": "included_current_pyav",
                    "first_query_ms": sparse_first_including_codec_ms,
                    "session_curve": _session_curve(
                        dense_first_ms=dense_first_ms,
                        sparse_first_ms=sparse_first_including_codec_ms,
                        follow_ms=follow_ms,
                    ),
                }
            )
        if runtime_source == "sidecar":
            rows.append(
                {
                    **row_base,
                    "codec_extraction_policy": "included_sidecar_load",
                    "first_query_ms": sparse_first_including_runtime_score_ms,
                    "session_curve": _session_curve(
                        dense_first_ms=dense_first_ms,
                        sparse_first_ms=sparse_first_including_runtime_score_ms,
                        follow_ms=follow_ms,
                    ),
                }
            )

    return {
        "phase": "OV-8",
        "status": "artifact-level accounting only",
        "query_counts": list(QUERY_COUNTS),
        "dense_first_query_source": str(dense_dir / "summary.json"),
        "sparse_first_query_source": str(sparse_dir / "summary.json"),
        "cpersist_source": str(cpersist_summary_path),
        "dense_first_query_ms": dense_first_ms,
        "sparse_first_query_ms_excluding_codec_extract": sparse_first_excluding_codec_ms,
        "sparse_first_query_ms_including_current_pyav_extract": sparse_first_including_codec_ms,
        "sparse_first_query_ms_including_runtime_score": sparse_first_including_runtime_score_ms,
        "codec_extract_mean_s_per_item": codec_extract_s,
        "codec_sidecar_load_mean_s_per_item": sidecar_load_s,
        "codec_score_runtime_source": runtime_source,
        "first_query_pairing": first_query_pairing,
        "first_query_drift_clean": first_query_pairing["correctness_drift"] == 0
        and first_query_pairing["choice_drift"] == 0,
        "guardrails": [
            "This is not a live combined session run.",
            "Do not multiply OV-6 and C-PERSIST speedup ratios.",
            "The included_current_pyav rows are the conservative local wall-clock denominator.",
            "The excluded_model_side rows represent a precomputed or decoder-integrated "
            "metadata hypothesis.",
        ],
        "rows": rows,
    }


def _markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# OV-8 Artifact-Level Session Accounting",
        "",
        "This is accounting-only, not a live combined runtime claim.",
        "",
        "First-query sparse-vs-dense pairing: "
        f"choice_drift={payload['first_query_pairing']['choice_drift']}/"
        f"{payload['first_query_pairing']['n']}; "
        f"correctness_drift={payload['first_query_pairing']['correctness_drift']}/"
        f"{payload['first_query_pairing']['n']}.",
        "",
    ]
    for row in payload["rows"]:
        lines.append(f"## {row['policy']} — {row['codec_extraction_policy']}")
        lines.append("")
        lines.append(
            f"first_query_ms={row['first_query_ms']:.0f}; "
            f"followup_median_ms={row['followup_median_ms']:.0f}; "
            f"followup_drift={row['followup_correctness_drift']}/{row['followup_n']}"
        )
        lines.append("")
        lines.append("| Q | dense cold-every-query ms | combined ms | speedup |")
        lines.append("| ---: | ---: | ---: | ---: |")
        for curve in row["session_curve"]:
            lines.append(
                "| "
                + " | ".join(
                    [
                        f"{int(curve['n_total_queries'])}",
                        f"{curve['dense_cold_every_query_ms']:.0f}",
                        f"{curve['sparse_first_plus_cpersist_followups_ms']:.0f}",
                        f"{curve['speedup_dense_over_combined']:.2f}x",
                    ]
                )
                + " |"
            )
        lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dense-dir", type=Path, default=DEFAULT_DENSE)
    parser.add_argument("--sparse-dir", type=Path, default=DEFAULT_SPARSE)
    parser.add_argument("--cpersist-summary", type=Path, default=DEFAULT_CPERSIST)
    parser.add_argument("--horizon", type=int, default=50)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    payload = build_payload(
        dense_dir=args.dense_dir,
        sparse_dir=args.sparse_dir,
        cpersist_summary_path=args.cpersist_summary,
        horizon=args.horizon,
    )
    args.out_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.out_dir / "accounting.json"
    md_path = args.out_dir / "accounting.md"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    md_path.write_text(_markdown(payload) + "\n")
    print(json_path)
    print(md_path)


if __name__ == "__main__":
    main()
