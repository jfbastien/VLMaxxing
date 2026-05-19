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
) -> dict[str, object]:
    return {
        "item_id": item_id,
        "benchmark": "mvbench",
        "group": group,
        "answer_index": 0,
        "dense_choice": 0,
        "dense_correct": dense_correct,
        "dense_parse_failure": False,
        "dense_end_to_end_ms": 100.0,
        "dense_prefill_ms": 40.0,
        "composed_choice": 1,
        "composed_correct": composed_correct,
        "composed_parse_failure": False,
        "composed_end_to_end_ms": 50.0,
        "composed_prefill_ms": 20.0,
    }


def _write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")


def _write_mvbench_json(root: Path) -> None:
    root.mkdir(parents=True)
    (root / "moving_attribute.json").write_text(
        json.dumps([{"question": "What color is the object?"}]),
        encoding="utf-8",
    )
    (root / "moving_direction.json").write_text(
        json.dumps([{"question": "What direction is it moving?"}]),
        encoding="utf-8",
    )


def test_text_route_transfer_reports_harmed_recall(tmp_path: Path) -> None:
    paired = tmp_path / "paired.jsonl"
    manifest = tmp_path / "manifest.toml"
    output = tmp_path / "transfer.json"
    mvbench_json = tmp_path / "mvbench"
    _write_mvbench_json(mvbench_json)
    manifest.write_text(
        'benchmark = "mvbench"\n'
        'item_ids = ["mvbench:moving_attribute:0", "mvbench:moving_direction:0"]\n',
        encoding="utf-8",
    )
    _write_jsonl(
        paired,
        [
            _row(
                "mvbench:moving_attribute:0",
                group="moving_attribute",
                dense_correct=True,
                composed_correct=False,
            ),
            _row(
                "mvbench:moving_direction:0",
                group="moving_direction",
                dense_correct=True,
                composed_correct=True,
            ),
        ],
    )

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/analyze_gemma_text_route_transfer.py",
            "--paired-items",
            str(paired),
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

    assert completed.returncode == 0, completed.stderr
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["schema"] == "gemma_text_route_transfer_v1"
    assert payload["summary"]["harmed_count"] == 1
    assert payload["summary"]["harmed_matched_count"] == 1
    assert payload["summary"]["harmed_recall"] == 1.0
    assert payload["summary"]["matched_precision_for_harm"] == 1.0
    assert payload["summary"]["route_summary_by_group"] == {
        "moving_attribute": {"matched_safe_regex": 1},
        "moving_direction": {"unmatched_fast": 1},
    }
