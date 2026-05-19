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
        "dense_vision_ms": dense_vision_ms,
        "composed_vision_ms": composed_vision_ms,
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
