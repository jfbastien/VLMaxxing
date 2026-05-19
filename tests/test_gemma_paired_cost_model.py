from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def _row(
    item_id: str,
    *,
    dense_correct: bool,
    composed_correct: bool,
    dense_ms: float = 100.0,
    composed_ms: float = 50.0,
    dense_prefill_ms: float = 40.0,
    composed_prefill_ms: float = 20.0,
    dense_vision_ms: float = 20.0,
    composed_vision_ms: float = 10.0,
    dense_video_decode_ms: float = 5.0,
    composed_video_decode_ms: float = 5.0,
    dense_text_generation_ms: float = 10.0,
    composed_text_generation_ms: float = 10.0,
    dense_generation_tokens: int = 2,
    composed_generation_tokens: int = 4,
) -> dict[str, object]:
    return {
        "item_id": item_id,
        "benchmark": "mvbench",
        "group": "moving_attribute",
        "answer_index": 0,
        "dense_choice": 0,
        "composed_choice": 0,
        "dense_correct": dense_correct,
        "composed_correct": composed_correct,
        "dense_parse_failure": False,
        "composed_parse_failure": False,
        "dense_end_to_end_ms": dense_ms,
        "composed_end_to_end_ms": composed_ms,
        "dense_prefill_ms": dense_prefill_ms,
        "composed_prefill_ms": composed_prefill_ms,
        "dense_video_decode_ms": dense_video_decode_ms,
        "composed_video_decode_ms": composed_video_decode_ms,
        "dense_vision_ms": dense_vision_ms,
        "composed_vision_ms": composed_vision_ms,
        "dense_text_generation_ms": dense_text_generation_ms,
        "composed_text_generation_ms": composed_text_generation_ms,
        "dense_generation_tokens": dense_generation_tokens,
        "composed_generation_tokens": composed_generation_tokens,
    }


def _write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")


def test_paired_cost_model_reports_stage_shares_and_bootstrap(tmp_path: Path) -> None:
    paired = tmp_path / "paired.jsonl"
    output = tmp_path / "cost.json"
    _write_jsonl(
        paired,
        [
            _row("a", dense_correct=True, composed_correct=True),
            _row(
                "b",
                dense_correct=True,
                composed_correct=False,
                dense_ms=200.0,
                composed_ms=100.0,
                dense_prefill_ms=80.0,
                composed_prefill_ms=40.0,
                dense_vision_ms=40.0,
                composed_vision_ms=20.0,
            ),
        ],
    )

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/analyze_gemma_paired_cost_model.py",
            "--paired-items",
            str(paired),
            "--output",
            str(output),
            "--label",
            "unit",
            "--n-bootstrap",
            "20",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    payload = json.loads(output.read_text(encoding="utf-8"))
    summary = payload["summary"]
    assert payload["schema"] == "gemma_paired_cost_model_v1"
    assert summary["n"] == 2
    assert summary["accuracy_delta_composed_minus_dense"] == -0.5
    assert summary["harmed_count"] == 1
    assert summary["e2e_speedup_dense_over_composed"] == 2.0
    assert summary["prefill_speedup_dense_over_composed"] == 2.0
    assert summary["vision_speedup_dense_over_composed"] == 2.0
    assert summary["dense_prefill_share_of_e2e"] == 0.4
    assert summary["prefill_only_e2e_ceiling_speedup"] == 300.0 / 240.0
    assert summary["prefill_plus_vision_e2e_ceiling_speedup"] == 300.0 / 210.0
    assert summary["tail_audit"]["dense_text_generation_total_ms"] == 20.0
    assert summary["tail_audit"]["composed_text_generation_total_ms"] == 20.0
    assert (
        summary["tail_audit"]["prefill_plus_vision_plus_text_generation_e2e_ceiling_speedup"]
        == 300.0 / 210.0
    )
    assert (
        summary["transition_stage_costs"]["harm_vs_preserved_correct"][
            "policy_generation_tokens_ratio_harmed_over_preserved_correct"
        ]
        == 1.0
    )
    assert payload["bootstrap_ci"]["n_bootstrap"] == 20
    assert payload["bootstrap_ci"]["e2e_speedup_dense_over_composed_ci95"] == [2.0, 2.0]


def test_paired_cost_model_rejects_inconsistent_stage_timing(tmp_path: Path) -> None:
    paired = tmp_path / "paired.jsonl"
    output = tmp_path / "cost.json"
    _write_jsonl(
        paired,
        [
            _row(
                "bad",
                dense_correct=True,
                composed_correct=True,
                dense_ms=100.0,
                dense_prefill_ms=80.0,
                dense_vision_ms=30.0,
            )
        ],
    )

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/analyze_gemma_paired_cost_model.py",
            "--paired-items",
            str(paired),
            "--output",
            str(output),
            "--label",
            "bad",
            "--n-bootstrap",
            "20",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode != 0
    assert "dense prefill+vision exceeds adjusted dense e2e" in completed.stderr


def test_paired_cost_model_rejects_inconsistent_decode_timing(tmp_path: Path) -> None:
    paired = tmp_path / "paired.jsonl"
    output = tmp_path / "cost.json"
    _write_jsonl(
        paired,
        [
            _row(
                "bad",
                dense_correct=True,
                composed_correct=True,
                dense_ms=100.0,
                dense_prefill_ms=70.0,
                dense_vision_ms=20.0,
                dense_video_decode_ms=20.0,
            )
        ],
    )

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/analyze_gemma_paired_cost_model.py",
            "--paired-items",
            str(paired),
            "--output",
            str(output),
            "--label",
            "bad",
            "--n-bootstrap",
            "20",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode != 0
    assert "dense prefill+vision+video_decode exceeds adjusted dense e2e" in completed.stderr


def test_paired_cost_model_rejects_impossible_combined_tail_timing(tmp_path: Path) -> None:
    paired = tmp_path / "paired.jsonl"
    output = tmp_path / "cost.json"
    _write_jsonl(
        paired,
        [
            _row(
                "bad",
                dense_correct=True,
                composed_correct=True,
                dense_ms=100.0,
                dense_prefill_ms=70.0,
                dense_vision_ms=20.0,
                dense_video_decode_ms=5.0,
                dense_text_generation_ms=10.0,
                composed_ms=100.0,
                composed_prefill_ms=40.0,
                composed_vision_ms=20.0,
                composed_video_decode_ms=5.0,
                composed_text_generation_ms=10.0,
            )
        ],
    )

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/analyze_gemma_paired_cost_model.py",
            "--paired-items",
            str(paired),
            "--output",
            str(output),
            "--label",
            "bad",
            "--n-bootstrap",
            "20",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode != 0
    assert "dense video_decode+text_generation exceeds adjusted dense tail" in completed.stderr


def test_paired_cost_model_rejects_nonfinite_optional_tail_timing(tmp_path: Path) -> None:
    paired = tmp_path / "paired.jsonl"
    output = tmp_path / "cost.json"
    _write_jsonl(
        paired,
        [
            _row(
                "bad",
                dense_correct=True,
                composed_correct=True,
                dense_video_decode_ms=float("nan"),
            )
        ],
    )

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/analyze_gemma_paired_cost_model.py",
            "--paired-items",
            str(paired),
            "--output",
            str(output),
            "--label",
            "bad",
            "--n-bootstrap",
            "20",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode != 0
    assert "dense_video_decode_ms must be finite and positive" in completed.stderr


def test_paired_cost_model_subtracts_confidence_capture_from_text_generation(
    tmp_path: Path,
) -> None:
    paired = tmp_path / "paired.jsonl"
    output = tmp_path / "cost.json"
    row = _row("a", dense_correct=True, composed_correct=True)
    row["dense_first_generated_confidence_capture_ms"] = 2.0
    row["composed_first_generated_confidence_capture_ms"] = 4.0
    _write_jsonl(paired, [row])

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/analyze_gemma_paired_cost_model.py",
            "--paired-items",
            str(paired),
            "--output",
            str(output),
            "--label",
            "unit",
            "--n-bootstrap",
            "20",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    summary = json.loads(output.read_text(encoding="utf-8"))["summary"]
    assert summary["tail_audit"]["dense_text_generation_total_ms"] == 8.0
    assert summary["tail_audit"]["composed_text_generation_total_ms"] == 6.0


def test_paired_cost_model_rejects_unpaired_generation_tokens(tmp_path: Path) -> None:
    paired = tmp_path / "paired.jsonl"
    output = tmp_path / "cost.json"
    row = _row("bad", dense_correct=True, composed_correct=True)
    row.pop("composed_generation_tokens")
    _write_jsonl(paired, [row])

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/analyze_gemma_paired_cost_model.py",
            "--paired-items",
            str(paired),
            "--output",
            str(output),
            "--label",
            "bad",
            "--n-bootstrap",
            "20",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode != 0
    assert "generation token fields must both be present or absent" in completed.stderr


def test_paired_cost_model_rejects_bool_generation_tokens(tmp_path: Path) -> None:
    paired = tmp_path / "paired.jsonl"
    output = tmp_path / "cost.json"
    row = _row("bad", dense_correct=True, composed_correct=True)
    row["dense_generation_tokens"] = True
    _write_jsonl(paired, [row])

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/analyze_gemma_paired_cost_model.py",
            "--paired-items",
            str(paired),
            "--output",
            str(output),
            "--label",
            "bad",
            "--n-bootstrap",
            "20",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode != 0
    assert "dense_generation_tokens must be a non-negative integer" in completed.stderr


def test_paired_cost_model_rejects_malformed_correctness_label(tmp_path: Path) -> None:
    paired = tmp_path / "paired.jsonl"
    output = tmp_path / "cost.json"
    row = _row("bad", dense_correct=True, composed_correct=True)
    row["composed_correct"] = "false"
    _write_jsonl(paired, [row])

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/analyze_gemma_paired_cost_model.py",
            "--paired-items",
            str(paired),
            "--output",
            str(output),
            "--label",
            "bad",
            "--n-bootstrap",
            "20",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode != 0
    assert "composed_correct must be boolean" in completed.stderr
