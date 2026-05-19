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
    dense_prefill_ms: float = 40.0,
    composed_prefill_ms: float = 20.0,
) -> dict[str, object]:
    return {
        "item_id": item_id,
        "benchmark": "mvbench",
        "group": group,
        "answer_index": 0,
        "dense_choice": dense_choice,
        "dense_correct": dense_correct,
        "dense_parse_failure": dense_choice is None,
        "composed_choice": composed_choice,
        "composed_correct": composed_correct,
        "composed_parse_failure": composed_choice is None,
        "dense_end_to_end_ms": dense_ms,
        "composed_end_to_end_ms": composed_ms,
        "dense_prefill_ms": dense_prefill_ms,
        "composed_prefill_ms": composed_prefill_ms,
        "dense_first_generated_confidence_capture_ms": 5.0,
        "composed_first_generated_confidence_capture_ms": 2.0,
    }


def _write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")


def _write_mvbench_json(root: Path) -> None:
    root.mkdir(parents=True)
    (root / "moving_attribute.json").write_text(
        json.dumps(
            [
                {
                    "question": "What color is the object?",
                    "candidates": ["red", "blue"],
                    "answer": "red",
                    "video": "unused.mp4",
                }
            ]
        ),
        encoding="utf-8",
    )
    (root / "moving_direction.json").write_text(
        json.dumps(
            [
                {
                    "question": "What direction is it moving?",
                    "candidates": ["left", "right"],
                    "answer": "left",
                    "video": "unused.mp4",
                }
            ]
        ),
        encoding="utf-8",
    )


def test_text_routed_admission_uses_raw_question_regex_and_fixed_dense_denominator(
    tmp_path: Path,
) -> None:
    manifest = tmp_path / "manifest.toml"
    manifest.write_text(
        'benchmark = "mvbench"\n'
        'item_ids = ["mvbench:moving_attribute:0", "mvbench:moving_direction:0"]\n',
        encoding="utf-8",
    )
    mvbench_json = tmp_path / "mvbench"
    _write_mvbench_json(mvbench_json)
    safe = tmp_path / "safe.jsonl"
    fast = tmp_path / "fast.jsonl"
    output = tmp_path / "analysis.json"
    _write_jsonl(
        safe,
        [
            _row(
                "mvbench:moving_attribute:0",
                group="moving_attribute",
                dense_correct=True,
                composed_correct=True,
                dense_ms=100.0,
                composed_ms=100.0,
            ),
            _row(
                "mvbench:moving_direction:0",
                group="moving_direction",
                dense_correct=True,
                composed_correct=True,
                dense_ms=200.0,
                composed_ms=200.0,
            ),
        ],
    )
    _write_jsonl(
        fast,
        [
            _row(
                "mvbench:moving_attribute:0",
                group="moving_attribute",
                dense_correct=True,
                composed_correct=False,
                dense_ms=110.0,
                composed_ms=40.0,
            ),
            _row(
                "mvbench:moving_direction:0",
                group="moving_direction",
                dense_correct=True,
                composed_correct=True,
                dense_ms=220.0,
                composed_ms=50.0,
            ),
        ],
    )

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/analyze_gemma_text_routed_admission.py",
            "--safe-paired-items",
            str(safe),
            "--fast-paired-items",
            str(fast),
            "--manifest",
            str(manifest),
            "--mvbench-json-dir",
            str(mvbench_json),
            "--n-bootstrap",
            "20",
            "--output",
            str(output),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    payload = json.loads(output.read_text())
    assert payload["schema"] == "gemma_text_routed_admission_v2"
    assert payload["safe_question_regex"] == (
        r"\bwhat\s+(?:(?:color|shape|material)\b|is\s+the\s+(?:color|shape|material)\b)"
    )
    assert payload["route_summary_by_group"] == {
        "moving_attribute": {"safe": 1},
        "moving_direction": {"fast": 1},
    }
    assert payload["summary"]["accuracy_delta_policy_minus_dense"] == 0.0
    assert payload["summary"]["source_counts"] == {"fast": 1, "safe": 1}
    assert payload["summary"]["dense_total_ms"] == 290.0
    assert payload["summary"]["policy_total_ms"] == 146.0
    assert payload["summary"]["e2e_speedup_dense_over_policy"] == 290.0 / 146.0
    assert payload["summary"]["dense_prefill_total_ms"] == 80.0
    assert payload["summary"]["policy_prefill_total_ms"] == 40.0
    assert payload["summary"]["prefill_speedup_dense_over_policy"] == 2.0
    assert payload["bootstrap_ci"]["n_bootstrap"] == 20
    assert (
        payload["bootstrap_ci"]["e2e_speedup_dense_over_policy_ci95"][0]
        <= payload["summary"]["e2e_speedup_dense_over_policy"]
        <= payload["bootstrap_ci"]["e2e_speedup_dense_over_policy_ci95"][1]
    )
    assert payload["items"][0]["question"] == "What color is the object?"


def test_text_routed_admission_rejects_dense_label_drift_by_default(
    tmp_path: Path,
) -> None:
    manifest = tmp_path / "manifest.toml"
    manifest.write_text(
        'benchmark = "mvbench"\nitem_ids = ["mvbench:moving_attribute:0"]\n',
        encoding="utf-8",
    )
    mvbench_json = tmp_path / "mvbench"
    _write_mvbench_json(mvbench_json)
    safe = tmp_path / "safe.jsonl"
    fast = tmp_path / "fast.jsonl"
    output = tmp_path / "analysis.json"
    _write_jsonl(
        safe,
        [
            _row(
                "mvbench:moving_attribute:0",
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
                "mvbench:moving_attribute:0",
                group="moving_attribute",
                dense_correct=False,
                composed_correct=False,
            )
        ],
    )

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/analyze_gemma_text_routed_admission.py",
            "--safe-paired-items",
            str(safe),
            "--fast-paired-items",
            str(fast),
            "--manifest",
            str(manifest),
            "--mvbench-json-dir",
            str(mvbench_json),
            "--output",
            str(output),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode != 0
    assert "safe and fast paired rows disagree on dense labels" in completed.stderr


def test_text_routed_admission_rejects_manifest_mismatch(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.toml"
    manifest.write_text(
        'benchmark = "mvbench"\n'
        'item_ids = ["mvbench:moving_attribute:0", "mvbench:moving_direction:0"]\n',
        encoding="utf-8",
    )
    mvbench_json = tmp_path / "mvbench"
    _write_mvbench_json(mvbench_json)
    safe = tmp_path / "safe.jsonl"
    fast = tmp_path / "fast.jsonl"
    output = tmp_path / "analysis.json"
    rows = [
        _row(
            "mvbench:moving_attribute:0",
            group="moving_attribute",
            dense_correct=True,
            composed_correct=True,
        )
    ]
    _write_jsonl(safe, rows)
    _write_jsonl(fast, rows)

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/analyze_gemma_text_routed_admission.py",
            "--safe-paired-items",
            str(safe),
            "--fast-paired-items",
            str(fast),
            "--manifest",
            str(manifest),
            "--mvbench-json-dir",
            str(mvbench_json),
            "--output",
            str(output),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode != 0
    assert "manifest and paired artifacts do not describe the same item set" in completed.stderr


def test_text_routed_admission_rejects_degenerate_route(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.toml"
    manifest.write_text(
        'benchmark = "mvbench"\nitem_ids = ["mvbench:moving_attribute:0"]\n',
        encoding="utf-8",
    )
    mvbench_json = tmp_path / "mvbench"
    _write_mvbench_json(mvbench_json)
    safe = tmp_path / "safe.jsonl"
    fast = tmp_path / "fast.jsonl"
    rows = [
        _row(
            "mvbench:moving_attribute:0",
            group="moving_attribute",
            dense_correct=True,
            composed_correct=True,
        )
    ]
    _write_jsonl(safe, rows)
    _write_jsonl(fast, rows)
    output = tmp_path / "analysis.json"

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/analyze_gemma_text_routed_admission.py",
            "--safe-paired-items",
            str(safe),
            "--fast-paired-items",
            str(fast),
            "--manifest",
            str(manifest),
            "--mvbench-json-dir",
            str(mvbench_json),
            "--output",
            str(output),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode != 0
    assert "text routing is degenerate" in completed.stderr
