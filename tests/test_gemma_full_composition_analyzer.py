from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any


def _schema(*, prune_placeholders: str, vision_keep_rate: float) -> dict[str, Any]:
    return {
        "kind": "schema",
        "schema_version": "phase1_51r_gemma_admission_v4",
        "artifact_payload": {
            "manifest": "manifest.toml",
            "frame_count": 8,
            "prefill_step_size": 1024,
            "prune_placeholders": prune_placeholders,
            "vision_tower_keep_rate": vision_keep_rate,
            "vision_tower_score_mode": "rlt_topk" if vision_keep_rate < 1.0 else "magnitude",
        },
    }


def _row(item_id: str, *, group: str, dense_correct: bool, pruned_correct: bool) -> dict[str, Any]:
    return {
        "kind": "item",
        "item_id": item_id,
        "benchmark": "videomme",
        "group": group,
        "answer_index": 1,
        "dense_correct": dense_correct,
        "pruned_correct": pruned_correct,
        "dense_parse_failure": False,
        "pruned_parse_failure": False,
        "dense_choice": 1 if dense_correct else 0,
        "pruned_choice": 1 if pruned_correct else 0,
        "dense_prompt_tokens": 2200,
        "pruned_prompt_tokens": 1400,
        "dense_timing_ms": {
            "end_to_end": 1000.0,
            "vision": 300.0,
            "multimodal_prefill_ms": 400.0,
        },
        "pruned_timing_ms": {
            "end_to_end": 800.0,
            "vision": 120.0,
            "multimodal_prefill_ms": 250.0,
        },
        "metadata": {
            "vision_tower_keep_rate": 0.5,
            "vision_tower_score_mode": "rlt_topk",
        },
    }


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text("\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n")


def test_full_composition_analyzer_pairs_dense_reference_against_composed(tmp_path: Path) -> None:
    dense = tmp_path / "dense.jsonl"
    composed = tmp_path / "composed.jsonl"
    output = tmp_path / "analysis.json"
    paired = tmp_path / "paired.jsonl"
    items = [
        _row(f"item-{idx}", group="short", dense_correct=True, pruned_correct=True)
        for idx in range(5)
    ]
    _write_jsonl(dense, [_schema(prune_placeholders="none", vision_keep_rate=1.0), *items])
    _write_jsonl(composed, [_schema(prune_placeholders="rlt", vision_keep_rate=0.5), *items])

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/analyze_gemma_full_composition.py",
            "--dense-jsonl",
            str(dense),
            "--composed-jsonl",
            str(composed),
            "--output",
            str(output),
            "--paired-items",
            str(paired),
            "--expected-items",
            "5",
            "--n-bootstrap",
            "50",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    analysis = json.loads(output.read_text())
    assert analysis["decisions"][0]["decision"] == "continue"
    assert analysis["summary"]["e2e_speedup_dense_over_composed"] == 1.25
    assert analysis["summary"]["pass_bucket_quality_and_e2e"]
    assert len(paired.read_text().strip().splitlines()) == 5


def test_full_composition_analyzer_combines_disjoint_sources(tmp_path: Path) -> None:
    dense_dev = tmp_path / "dense_dev.jsonl"
    composed_dev = tmp_path / "composed_dev.jsonl"
    dense_holdout = tmp_path / "dense_holdout.jsonl"
    composed_holdout = tmp_path / "composed_holdout.jsonl"
    output = tmp_path / "analysis.json"
    paired = tmp_path / "paired.jsonl"
    dev_items = [
        _row(f"dev-{idx}", group="short", dense_correct=True, pruned_correct=True)
        for idx in range(5)
    ]
    holdout_items = [
        _row(f"holdout-{idx}", group="short", dense_correct=True, pruned_correct=True)
        for idx in range(5)
    ]
    dense_schema = _schema(prune_placeholders="none", vision_keep_rate=1.0)
    composed_schema = _schema(prune_placeholders="rlt", vision_keep_rate=0.5)
    _write_jsonl(dense_dev, [dense_schema, *dev_items])
    _write_jsonl(composed_dev, [composed_schema, *dev_items])
    _write_jsonl(dense_holdout, [dense_schema, *holdout_items])
    _write_jsonl(composed_holdout, [composed_schema, *holdout_items])

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/analyze_gemma_full_composition.py",
            "--dense-jsonl",
            str(dense_dev),
            "--dense-jsonl",
            str(dense_holdout),
            "--composed-jsonl",
            str(composed_dev),
            "--composed-jsonl",
            str(composed_holdout),
            "--output",
            str(output),
            "--paired-items",
            str(paired),
            "--expected-items",
            "10",
            "--bucket-min-n",
            "10",
            "--n-bootstrap",
            "50",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    analysis = json.loads(output.read_text())
    assert analysis["summary"]["n_items"] == 10
    assert analysis["source_pairs"] == [
        {"dense_jsonl": str(dense_dev), "composed_jsonl": str(composed_dev), "n_items": 5},
        {
            "dense_jsonl": str(dense_holdout),
            "composed_jsonl": str(composed_holdout),
            "n_items": 5,
        },
    ]
    assert len(paired.read_text().strip().splitlines()) == 10


def test_full_composition_analyzer_rejects_sparse_dense_reference(tmp_path: Path) -> None:
    dense = tmp_path / "dense.jsonl"
    composed = tmp_path / "composed.jsonl"
    output = tmp_path / "analysis.json"
    paired = tmp_path / "paired.jsonl"
    item = _row("item-0", group="short", dense_correct=True, pruned_correct=True)
    _write_jsonl(dense, [_schema(prune_placeholders="none", vision_keep_rate=0.5), item])
    _write_jsonl(composed, [_schema(prune_placeholders="rlt", vision_keep_rate=0.5), item])

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/analyze_gemma_full_composition.py",
            "--dense-jsonl",
            str(dense),
            "--composed-jsonl",
            str(composed),
            "--output",
            str(output),
            "--paired-items",
            str(paired),
            "--expected-items",
            "1",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode != 0
    assert "dense reference must not use sparse vision" in completed.stderr
