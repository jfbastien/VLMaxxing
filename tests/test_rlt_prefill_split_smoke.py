from __future__ import annotations

import json
from pathlib import Path

import scripts.build_rlt_prefill_split_smoke as smoke
import scripts.preflight_rlt_vlmax as preflight


def _write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row) + "\n")


def test_prefill_split_smoke_validates_nonzero_split_fields(tmp_path: Path) -> None:
    jsonl_path = tmp_path / "dense.jsonl"
    summary_path = tmp_path / "summary.json"
    _write_jsonl(
        jsonl_path,
        [
            {
                "kind": "schema",
                "schema_version": "phase1_63g_gemma_track_b_v4",
                "timing_split": "stream_generate_first_yield_wall_clock",
            },
            {
                "kind": "item",
                "item_id": "a",
                "timing_ms": {
                    "multimodal_prefill_ms": 90.0,
                    "text_generation_ms": 10.0,
                    "generate": 100.0,
                },
                "prompt_tokens": 900,
                "generation_tokens": 10,
            },
        ],
    )
    summary_path.write_text(json.dumps({"schema_version": "phase1_63g_gemma_track_b_v4"}))

    payload = smoke.validate_prefill_split_artifact(
        jsonl_path=jsonl_path,
        summary_path=summary_path,
        max_split_residual_pct=0.03,
        max_split_residual_ms=50.0,
    )

    assert payload["ready"] is True
    assert payload["fields_present"] == [
        "generate",
        "multimodal_prefill_ms",
        "text_generation_ms",
    ]
    assert payload["items"][0]["split_residual_ms"] == 0.0


def test_prefill_split_smoke_fails_missing_ms_alias(tmp_path: Path) -> None:
    jsonl_path = tmp_path / "dense.jsonl"
    summary_path = tmp_path / "summary.json"
    _write_jsonl(
        jsonl_path,
        [
            {"kind": "schema", "schema_version": "phase1_63g_gemma_track_b_v2"},
            {
                "kind": "item",
                "item_id": "a",
                "timing_ms": {
                    "multimodal_prefill": 90.0,
                    "text_generation": 10.0,
                    "generate": 100.0,
                },
            },
        ],
    )
    summary_path.write_text(json.dumps({"schema_version": "phase1_63g_gemma_track_b_v2"}))

    payload = smoke.validate_prefill_split_artifact(
        jsonl_path=jsonl_path,
        summary_path=summary_path,
        max_split_residual_pct=0.03,
        max_split_residual_ms=50.0,
    )

    assert payload["ready"] is False
    assert payload["failures"][0]["reason"] == "missing_fields"


def test_prefill_split_smoke_fails_large_generate_residual(tmp_path: Path) -> None:
    jsonl_path = tmp_path / "dense.jsonl"
    summary_path = tmp_path / "summary.json"
    _write_jsonl(
        jsonl_path,
        [
            {
                "kind": "schema",
                "schema_version": "phase1_63g_gemma_track_b_v4",
                "timing_split": "stream_generate_first_yield_wall_clock",
            },
            {
                "kind": "item",
                "item_id": "a",
                "timing_ms": {
                    "multimodal_prefill_ms": 90.0,
                    "text_generation_ms": 10.0,
                    "generate": 500.0,
                },
                "prompt_tokens": 900,
                "generation_tokens": 10,
            },
        ],
    )
    summary_path.write_text(json.dumps({"schema_version": "phase1_63g_gemma_track_b_v4"}))

    payload = smoke.validate_prefill_split_artifact(
        jsonl_path=jsonl_path,
        summary_path=summary_path,
        max_split_residual_pct=0.03,
        max_split_residual_ms=50.0,
    )

    assert payload["ready"] is False
    assert payload["failures"][0]["reason"] == "split_residual_exceeds_tolerance"
    assert payload["items"][0]["split_residual_within_tolerance"] is False


def test_prefill_preflight_requires_smoke_schema(tmp_path: Path) -> None:
    path = tmp_path / "prefill.json"
    path.write_text(json.dumps({"schema_version": "old", "ready": True, "n_items": 1}))

    result = preflight._check_prefill_split_smoke(path)

    assert result["ready"] is False
    assert result["detail"]["validation_failures"]
