from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def _row(
    item_id: str,
    *,
    group: str,
    dense_correct: bool,
    composed_correct: bool,
    dense_choice: int | None = 0,
    composed_choice: int | None = 0,
    dense_ms: float = 100.0,
    composed_ms: float = 50.0,
) -> dict[str, object]:
    return {
        "item_id": item_id,
        "paired_row_key": item_id,
        "benchmark": "mvbench",
        "group": group,
        "answer_index": 0,
        "dense_choice": dense_choice,
        "dense_correct": dense_correct,
        "dense_parse_failure": dense_choice is None,
        "dense_end_to_end_ms": dense_ms,
        "composed_choice": composed_choice,
        "composed_correct": composed_correct,
        "composed_parse_failure": composed_choice is None,
        "composed_end_to_end_ms": composed_ms,
    }


def _write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")


def test_admission_policy_simulates_group_fallback(tmp_path: Path) -> None:
    safe = tmp_path / "safe.jsonl"
    fast = tmp_path / "fast.jsonl"
    output = tmp_path / "policy.json"
    _write_jsonl(
        safe,
        [
            _row(
                "risky",
                group="moving_attribute",
                dense_correct=True,
                composed_correct=True,
                composed_ms=90.0,
            ),
            _row(
                "easy",
                group="moving_direction",
                dense_correct=True,
                composed_correct=True,
                composed_ms=90.0,
            ),
        ],
    )
    _write_jsonl(
        fast,
        [
            _row(
                "risky",
                group="moving_attribute",
                dense_correct=True,
                composed_correct=False,
                composed_choice=1,
                composed_ms=50.0,
            ),
            _row(
                "easy",
                group="moving_direction",
                dense_correct=True,
                composed_correct=True,
                dense_ms=300.0,
                composed_ms=50.0,
            ),
        ],
    )

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/analyze_gemma_admission_policy_simulation.py",
            "--safe-paired-items",
            str(safe),
            "--fast-paired-items",
            str(fast),
            "--fallback-group",
            "moving_attribute",
            "--output",
            str(output),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["schema"] == "gemma_admission_policy_simulation_v1"
    assert payload["dense_reference_source"] == "safe_paired_items"
    assert payload["summary"]["n"] == 2
    assert payload["summary"]["source_counts"] == {"fast": 1, "safe": 1}
    assert payload["summary"]["accuracy_delta_policy_minus_dense"] == 0.0
    assert payload["summary"]["failure_taxonomy"]["harmed"] == 0
    assert payload["summary"]["e2e_speedup_dense_over_policy"] == 200.0 / 140.0
    assert payload["source_baselines"]["fast_all_items"]["dense_total_ms"] == 400.0
    assert payload["source_baselines"]["fast_all_items"]["failure_taxonomy"]["harmed"] == 1
    assert payload["by_group"]["moving_attribute"]["source_counts"] == {"safe": 1}


def test_admission_policy_rejects_dense_label_drift_by_default(tmp_path: Path) -> None:
    safe = tmp_path / "safe.jsonl"
    fast = tmp_path / "fast.jsonl"
    output = tmp_path / "policy.json"
    _write_jsonl(
        safe,
        [
            _row(
                "same",
                group="moving_attribute",
                dense_correct=True,
                composed_correct=True,
                dense_choice=0,
            )
        ],
    )
    _write_jsonl(
        fast,
        [
            _row(
                "same",
                group="moving_attribute",
                dense_correct=False,
                composed_correct=False,
                dense_choice=1,
            )
        ],
    )

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/analyze_gemma_admission_policy_simulation.py",
            "--safe-paired-items",
            str(safe),
            "--fast-paired-items",
            str(fast),
            "--fallback-group",
            "moving_attribute",
            "--output",
            str(output),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode != 0
    assert "disagree on dense labels" in completed.stderr


def test_admission_policy_rejects_unknown_fallback_group(tmp_path: Path) -> None:
    safe = tmp_path / "safe.jsonl"
    fast = tmp_path / "fast.jsonl"
    output = tmp_path / "policy.json"
    _write_jsonl(
        safe,
        [
            _row(
                "same",
                group="moving_attribute",
                dense_correct=True,
                composed_correct=True,
            )
        ],
    )
    _write_jsonl(
        fast,
        [
            _row(
                "same",
                group="moving_attribute",
                dense_correct=True,
                composed_correct=False,
            )
        ],
    )

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/analyze_gemma_admission_policy_simulation.py",
            "--safe-paired-items",
            str(safe),
            "--fast-paired-items",
            str(fast),
            "--fallback-group",
            "moving_attributes",
            "--output",
            str(output),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode != 0
    assert "requested fallback groups are absent" in completed.stderr


def test_admission_policy_rejects_missing_composed_label(tmp_path: Path) -> None:
    safe = tmp_path / "safe.jsonl"
    fast = tmp_path / "fast.jsonl"
    output = tmp_path / "policy.json"
    safe_row = _row(
        "same",
        group="moving_attribute",
        dense_correct=True,
        composed_correct=True,
    )
    del safe_row["composed_correct"]
    _write_jsonl(safe, [safe_row])
    _write_jsonl(
        fast,
        [
            _row(
                "same",
                group="moving_attribute",
                dense_correct=True,
                composed_correct=False,
            )
        ],
    )

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/analyze_gemma_admission_policy_simulation.py",
            "--safe-paired-items",
            str(safe),
            "--fast-paired-items",
            str(fast),
            "--fallback-group",
            "moving_attribute",
            "--output",
            str(output),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode != 0
    assert "missing composed_correct" in completed.stderr


def test_admission_policy_can_record_explicit_dense_label_drift(
    tmp_path: Path,
) -> None:
    safe = tmp_path / "safe.jsonl"
    fast = tmp_path / "fast.jsonl"
    output = tmp_path / "policy.json"
    _write_jsonl(
        safe,
        [
            _row(
                "same",
                group="moving_attribute",
                dense_correct=True,
                composed_correct=True,
                dense_choice=0,
            )
        ],
    )
    _write_jsonl(
        fast,
        [
            _row(
                "same",
                group="moving_attribute",
                dense_correct=False,
                composed_correct=False,
                dense_choice=1,
            )
        ],
    )

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/analyze_gemma_admission_policy_simulation.py",
            "--safe-paired-items",
            str(safe),
            "--fast-paired-items",
            str(fast),
            "--fallback-group",
            "moving_attribute",
            "--allow-dense-label-drift",
            "--output",
            str(output),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["pairing_audit"]["dense_label_mismatch_count"] == 1
    assert payload["pairing_audit"]["observed_groups"] == ["moving_attribute"]
    assert payload["pairing_audit"]["requested_fallback_groups"] == ["moving_attribute"]


def test_admission_policy_subtracts_confidence_capture_overhead(
    tmp_path: Path,
) -> None:
    safe = tmp_path / "safe.jsonl"
    fast = tmp_path / "fast.jsonl"
    output = tmp_path / "policy.json"
    safe_row = _row(
        "risky",
        group="moving_attribute",
        dense_correct=True,
        composed_correct=True,
        dense_ms=110.0,
        composed_ms=90.0,
    )
    safe_row["dense_first_generated_confidence_capture_ms"] = 10.0
    safe_row["composed_first_generated_confidence_capture_ms"] = 20.0
    fast_row = _row(
        "risky",
        group="moving_attribute",
        dense_correct=True,
        composed_correct=False,
        dense_ms=110.0,
        composed_ms=50.0,
    )
    fast_row["dense_first_generated_confidence_capture_ms"] = 10.0
    fast_row["composed_first_generated_confidence_capture_ms"] = 5.0
    _write_jsonl(safe, [safe_row])
    _write_jsonl(fast, [fast_row])

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/analyze_gemma_admission_policy_simulation.py",
            "--safe-paired-items",
            str(safe),
            "--fast-paired-items",
            str(fast),
            "--fallback-group",
            "moving_attribute",
            "--output",
            str(output),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["summary"]["dense_total_ms"] == 100.0
    assert payload["summary"]["policy_total_ms"] == 70.0


def test_admission_policy_rejects_invalid_confidence_capture_timing(
    tmp_path: Path,
) -> None:
    safe = tmp_path / "safe.jsonl"
    fast = tmp_path / "fast.jsonl"
    output = tmp_path / "policy.json"
    safe_row = _row(
        "negative",
        group="moving_attribute",
        dense_correct=True,
        composed_correct=True,
    )
    safe_row["composed_first_generated_confidence_capture_ms"] = -1.0
    fast_row = _row(
        "negative",
        group="moving_attribute",
        dense_correct=True,
        composed_correct=True,
    )
    _write_jsonl(safe, [safe_row])
    _write_jsonl(fast, [fast_row])

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/analyze_gemma_admission_policy_simulation.py",
            "--safe-paired-items",
            str(safe),
            "--fast-paired-items",
            str(fast),
            "--fallback-group",
            "moving_attribute",
            "--output",
            str(output),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode != 0
    assert "negative composed_first_generated_confidence_capture_ms" in completed.stderr

    safe_row["composed_first_generated_confidence_capture_ms"] = 50.0
    safe_row["composed_end_to_end_ms"] = 50.0
    _write_jsonl(safe, [safe_row])
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/analyze_gemma_admission_policy_simulation.py",
            "--safe-paired-items",
            str(safe),
            "--fast-paired-items",
            str(fast),
            "--fallback-group",
            "moving_attribute",
            "--output",
            str(output),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode != 0
    assert "adjusted composed timing must be positive" in completed.stderr
