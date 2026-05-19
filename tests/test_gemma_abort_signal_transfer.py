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
    parse_failure: bool,
) -> dict[str, object]:
    return {
        "item_id": item_id,
        "benchmark": "mvbench",
        "group": "moving_attribute",
        "answer_index": 0,
        "dense_choice": 0,
        "composed_choice": None if parse_failure else 1,
        "dense_correct": dense_correct,
        "composed_correct": composed_correct,
        "dense_parse_failure": False,
        "composed_parse_failure": parse_failure,
        "dense_end_to_end_ms": 100.0,
        "composed_end_to_end_ms": 50.0,
        "dense_prefill_ms": 40.0,
        "composed_prefill_ms": 20.0,
        "composed_first_generated_token_text": "<|channel>" if parse_failure else "A",
        "composed_first_generated_top2_margin": 1.0,
        "composed_first_generated_candidate_top2_margin": 1.0,
    }


def test_abort_signal_transfer_reports_harm_recall(tmp_path: Path) -> None:
    paired = tmp_path / "paired.jsonl"
    output = tmp_path / "signal.json"
    paired.write_text(
        "\n".join(
            json.dumps(row)
            for row in [
                _row("a", dense_correct=True, composed_correct=False, parse_failure=True),
                _row("b", dense_correct=True, composed_correct=True, parse_failure=False),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/analyze_gemma_abort_signal_transfer.py",
            "--paired-items",
            str(paired),
            "--output",
            str(output),
            "--signal-rule",
            "parse_failure",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["schema"] == "gemma_abort_signal_transfer_v1"
    assert payload["summary"]["signal_count"] == 1
    assert payload["summary"]["harmed_count"] == 1
    assert payload["summary"]["harmed_recall"] == 1.0


def test_abort_signal_transfer_rejects_missing_margin(tmp_path: Path) -> None:
    paired = tmp_path / "paired.jsonl"
    output = tmp_path / "signal.json"
    row = _row("a", dense_correct=True, composed_correct=True, parse_failure=False)
    row.pop("composed_first_generated_top2_margin")
    paired.write_text(json.dumps(row) + "\n", encoding="utf-8")

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/analyze_gemma_abort_signal_transfer.py",
            "--paired-items",
            str(paired),
            "--output",
            str(output),
            "--signal-rule",
            "vocab_margin_lt",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode != 0
    assert "missing or non-finite composed_first_generated_top2_margin" in completed.stderr
