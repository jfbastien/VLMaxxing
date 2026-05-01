from __future__ import annotations

import json
import subprocess
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any


def _base_row(pair_index: int, arm: str) -> dict[str, Any]:
    video_id = f"vid{pair_index % 2}"
    pair_key = f"{video_id}/event{pair_index}"
    is_cstream = arm == "c_stream_native"
    return {
        "schema_version": "sam_scaleout_artifact_v1",
        "experiment_id": "test_cstream_stage0",
        "protocol_id": "test",
        "run_id": "run",
        "phase": "C-STREAM",
        "row_role": "paired",
        "arm": arm,
        "baseline_arm": "fresh_oracle_dense",
        "comparator_arm": "fresh_oracle_dense",
        "policy": "native_update_rebuild" if is_cstream else arm,
        "baseline_policy": "fresh_oracle_dense",
        "policy_params": {},
        "model_id": "test-model",
        "model_sha": "sha",
        "quantization": "test",
        "runtime": "test",
        "runtime_commit": "test",
        "hardware": "test",
        "os_version": "test",
        "mlx_version": None,
        "metal_version": None,
        "command_line": "test",
        "memory_definition": "test",
        "video_id": video_id,
        "event_id": f"event{pair_index}",
        "item_id": pair_key,
        "pair_key": pair_key,
        "q_index": 0,
        "turn_index": pair_index,
        "prompt_frame_count": 2 if is_cstream else 4,
        "frame_ids": ["f0", "f1"],
        "frame_hashes": ["h0", "h1"],
        "baseline_frame_ids": ["f0", "f1"],
        "baseline_frame_hashes": ["h0", "h1"],
        "frame_selection_hash": "frames",
        "frames_sha256": "frames",
        "raw_prompt": "Question?",
        "baseline_raw_prompt": "Question?",
        "prompt_hash": "prompt",
        "baseline_prompt_hash": "prompt",
        "input_ids_hash": "input",
        "baseline_input_ids_hash": "input",
        "raw_response": "A",
        "baseline_raw_response": "A",
        "session_choice": "A",
        "baseline_choice": "A",
        "choice_diff": False,
        "session_correct": True,
        "baseline_correct": True,
        "correctness_diff": False,
        "session_parse_failure": False,
        "baseline_parse_failure": False,
        "parse_failure": False,
        "text_identical": True,
        "decode_ms": 1.0,
        "vision_ms": 1.0,
        "prefill_ms": 1.0,
        "repair_prefill_ms": None,
        "generate_ms": 1.0,
        "end_to_end_ms": 4.0,
        "baseline_end_to_end_ms": 4.0,
        "elapsed_ms": 4.0,
        "baseline_elapsed_ms": 4.0,
        "vit_calls": 1 if is_cstream else 4,
        "baseline_vit_calls": 4,
        "peak_memory_gb": 1.0,
        "cache_topology": {},
        "prefix_hit": 1,
        "prefix_coverage": 1.0,
        "prompt_tokens": 10,
        "baseline_prompt_tokens": 10,
        "generation_tokens": 1,
        "seed": 0,
        "temperature": 0.0,
        "top_p": 1.0,
        "evidence_budget": "stage0",
        "cadence_sec": None,
        "fps": 30.0,
        "last_k": None,
        "selected_frame_indices": [0, 1],
        "event_time_s": float(pair_index + 1),
        "observation_window_s": 1.0,
        "stale_cache_case_id": "stale0" if pair_index == 0 else None,
        "changed_answer_expected": pair_index == 0,
        "source_media_path": f"/tmp/{video_id}.mp4",
        "source_media_sha256": "mediahash",
        "native_frames_processed": 30 if is_cstream else None,
        "native_update_count": 3 if is_cstream else None,
        "native_rebuild_count": 1 if is_cstream else None,
        "native_skip_count": 26 if is_cstream else None,
        "low_fps_dense_vit_calls": 4,
        "claim_id": None,
        "source_artifact_path": None,
        "source_artifact_sha256": None,
        "export_row_count": None,
        "expected_row_count": None,
        "exactness_match": None,
        "ci_method": None,
        "ci95": None,
        "provenance_note": None,
        "stage_timings_ms": None,
        "commit_sha": "commit",
    }


def _valid_rows() -> list[dict[str, Any]]:
    arms = [
        "fresh_oracle_dense",
        "low_fps_dense",
        "screenshot_polling",
        "recency_last_k",
        "c_stream_native",
    ]
    return [_base_row(pair_index, arm) for pair_index in range(6) for arm in arms]


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n")


def _run_validator(path: Path, summary_path: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            "scripts/validate_sam_scaleout_artifact.py",
            "--jsonl",
            str(path),
            "--phase",
            "C-STREAM",
            "--min-rows",
            "30",
            "--require-cstream-stage0",
            "--summary-output",
            str(summary_path),
        ],
        check=False,
        text=True,
        capture_output=True,
    )


def test_cstream_stage0_gate_accepts_native_rows(tmp_path: Path) -> None:
    jsonl = tmp_path / "rows.jsonl"
    summary = tmp_path / "summary.json"
    _write_jsonl(jsonl, _valid_rows())

    result = _run_validator(jsonl, summary)

    assert result.returncode == 0, result.stderr + result.stdout
    payload = json.loads(summary.read_text())
    assert payload["pass"] is True


def test_cstream_stage0_gate_rejects_representative_policy(tmp_path: Path) -> None:
    rows = _valid_rows()
    bad_rows = []
    for row in rows:
        mutated = deepcopy(row)
        if mutated["arm"] == "c_stream_native":
            mutated["policy"] = "representative_frame_selection"
        bad_rows.append(mutated)
    jsonl = tmp_path / "rows.jsonl"
    summary = tmp_path / "summary.json"
    _write_jsonl(jsonl, bad_rows)

    result = _run_validator(jsonl, summary)

    assert result.returncode != 0
    assert "representative policy" in result.stderr
