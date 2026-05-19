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
    composed_parse_failure: bool = False,
    first_token_text: str = "A",
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
        "composed_choice": 0 if composed_correct else 1,
        "dense_correct": dense_correct,
        "composed_correct": composed_correct,
        "dense_parse_failure": False,
        "composed_parse_failure": composed_parse_failure,
        "dense_end_to_end_ms": dense_ms,
        "composed_end_to_end_ms": composed_ms,
        "dense_prefill_ms": dense_prefill_ms,
        "composed_prefill_ms": composed_prefill_ms,
        "dense_vision_ms": dense_vision_ms,
        "composed_vision_ms": composed_vision_ms,
        "composed_first_generated_confidence_capture_ms": 5.0,
        "composed_first_generated_token_text": first_token_text,
        "composed_first_generated_top2_margin": 1.0,
        "composed_first_generated_candidate_top2_margin": 1.0,
    }


def _write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")


def test_speculative_parse_failure_uses_safe_result_and_cached_vision_cost(
    tmp_path: Path,
) -> None:
    safe = tmp_path / "safe.jsonl"
    fast = tmp_path / "fast.jsonl"
    output = tmp_path / "spec.json"
    _write_jsonl(
        safe,
        [
            _row("a", dense_correct=True, composed_correct=True, composed_ms=100.0),
            _row("b", dense_correct=True, composed_correct=True, composed_ms=100.0),
        ],
    )
    _write_jsonl(
        fast,
        [
            _row("a", dense_correct=True, composed_correct=False, composed_parse_failure=True),
            _row("b", dense_correct=True, composed_correct=True),
        ],
    )

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/analyze_gemma_speculative_admission.py",
            "--safe-paired-items",
            str(safe),
            "--fast-paired-items",
            str(fast),
            "--output",
            str(output),
            "--abort-rule",
            "parse_failure",
            "--n-bootstrap",
            "20",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["schema"] == "gemma_speculative_admission_v1"
    assert payload["accuracy_reference"]["accuracy_delta_interpretation"] == (
        "paired_same_dense_reference"
    )
    cached = payload["with_vision_cache"]["summary"]
    no_cache = payload["without_vision_cache"]["summary"]
    assert cached["abort_count"] == 1
    assert cached["accuracy_delta_policy_minus_dense"] == 0.0
    assert cached["e2e_speedup_dense_over_policy"] == 200.0 / 175.0
    assert no_cache["e2e_speedup_dense_over_policy"] == 200.0 / 185.0
    audit = payload["with_vision_cache"]["abort_audit"]
    assert audit["fast_harmed_count"] == 1
    assert audit["aborted_harmed_count"] == 1
    assert audit["abort_stage_counts"] == {"post_generation": 1}
    assert audit["harm_recall"] == 1.0


def test_speculative_non_letter_aborts_at_first_token_cost(tmp_path: Path) -> None:
    safe = tmp_path / "safe.jsonl"
    fast = tmp_path / "fast.jsonl"
    output = tmp_path / "spec.json"
    _write_jsonl(
        safe,
        [
            _row("a", dense_correct=True, composed_correct=True, composed_ms=100.0),
            _row("b", dense_correct=True, composed_correct=True, composed_ms=100.0),
        ],
    )
    _write_jsonl(
        fast,
        [
            _row(
                "a",
                dense_correct=True,
                composed_correct=False,
                first_token_text="<|channel>",
            ),
            _row("b", dense_correct=True, composed_correct=True),
        ],
    )

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/analyze_gemma_speculative_admission.py",
            "--safe-paired-items",
            str(safe),
            "--fast-paired-items",
            str(fast),
            "--output",
            str(output),
            "--abort-rule",
            "non_letter",
            "--n-bootstrap",
            "20",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    payload = json.loads(output.read_text(encoding="utf-8"))
    cached = payload["with_vision_cache"]["summary"]
    assert cached["accuracy_delta_policy_minus_dense"] == 0.0
    assert cached["e2e_speedup_dense_over_policy"] == 200.0 / 160.0
    assert payload["with_vision_cache"]["abort_audit"]["abort_stage_counts"] == {"first_token": 1}


def test_speculative_margin_rule_charges_confidence_capture(tmp_path: Path) -> None:
    safe = tmp_path / "safe.jsonl"
    fast = tmp_path / "fast.jsonl"
    output = tmp_path / "spec.json"
    safe_rows = [
        _row("a", dense_correct=True, composed_correct=True, composed_ms=100.0),
        _row("b", dense_correct=True, composed_correct=True, composed_ms=100.0),
    ]
    fast_rows = [
        _row("a", dense_correct=True, composed_correct=False),
        _row("b", dense_correct=True, composed_correct=True),
    ]
    fast_rows[0]["composed_first_generated_top2_margin"] = 0.0
    _write_jsonl(safe, safe_rows)
    _write_jsonl(fast, fast_rows)

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/analyze_gemma_speculative_admission.py",
            "--safe-paired-items",
            str(safe),
            "--fast-paired-items",
            str(fast),
            "--output",
            str(output),
            "--abort-rule",
            "vocab_margin_lt",
            "--margin-threshold",
            "0.5",
            "--n-bootstrap",
            "20",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    payload = json.loads(output.read_text(encoding="utf-8"))
    cached = payload["with_vision_cache"]["summary"]
    assert cached["accuracy_delta_policy_minus_dense"] == 0.0
    assert cached["e2e_speedup_dense_over_policy"] == 200.0 / 170.0
    first_item = next(item for item in payload["items"] if item["item_id"] == "a")
    assert first_item["fast_decision_ms"] == 5.0


def test_speculative_non_letter_requires_first_token_text(tmp_path: Path) -> None:
    safe = tmp_path / "safe.jsonl"
    fast = tmp_path / "fast.jsonl"
    output = tmp_path / "spec.json"
    safe_row = _row("a", dense_correct=True, composed_correct=True)
    fast_row = _row("a", dense_correct=True, composed_correct=False)
    fast_row.pop("composed_first_generated_token_text")
    _write_jsonl(safe, [safe_row])
    _write_jsonl(fast, [fast_row])

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/analyze_gemma_speculative_admission.py",
            "--safe-paired-items",
            str(safe),
            "--fast-paired-items",
            str(fast),
            "--output",
            str(output),
            "--abort-rule",
            "non_letter",
            "--n-bootstrap",
            "20",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode != 0
    assert "missing composed_first_generated_token_text" in completed.stderr
