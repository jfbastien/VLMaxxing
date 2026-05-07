from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pytest

from tests._mlx_probe import mlx_is_usable

if not mlx_is_usable():
    pytest.skip(
        "mlx.core not usable on this host (import or Metal-init fails); see tests/_mlx_probe.py",
        allow_module_level=True,
    )

import mlx.core as mx

pytest.importorskip("mlx_vlm")

import scripts.run_novelty_pruning_gemma as runner
from codec_through.rlt_masks import RLTMaskConfig


def _payload(item_id: str) -> dict[str, object]:
    return {
        "kind": "item",
        "item_id": item_id,
        "dense_correct": True,
        "pruned_correct": True,
        "agreement": True,
        "kept_tokens_total": 4,
        "n_frames": 2,
        "tokens_per_frame": 4,
        "dense_generation_tokens": 2,
        "pruned_generation_tokens": 2,
        "dense_generation_tps": 1.0,
        "pruned_generation_tps": 1.0,
        "dense_prompt_tokens": 10,
        "pruned_prompt_tokens": 5,
        "dense_timing_ms": {
            "decode": 1.0,
            "processor": 1.0,
            "vision": 1.0,
            "multimodal_prefill_ms": 10.0,
            "text_generation_ms": 2.0,
            "generate": 12.0,
            "end_to_end": 15.0,
        },
        "pruned_timing_ms": {
            "decode": 1.0,
            "processor": 1.0,
            "novelty": 0.0,
            "mask": 1.0,
            "mask_compute": 1.0,
            "prune": 1.0,
            "placeholder_prune": 1.0,
            "vision": 1.0,
            "multimodal_prefill_ms": 5.0,
            "text_generation_ms": 2.0,
            "generate": 7.0,
            "end_to_end": 11.0,
        },
    }


def test_prune_placeholders_none_is_strict_bypass(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_prune(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("none mode must not call prune_image_placeholders")

    monkeypatch.setattr(runner, "prune_image_placeholders", fail_prune)

    input_ids_np = np.array([101, 7, 7, 102, 7, 7, 103], dtype=np.int64)
    dense_input_ids = mx.array(input_ids_np[None, :])
    vision_features = mx.array(np.ones((1, 4, 2), dtype=np.float32))
    keep_mask = np.ones((2, 2), dtype=bool)

    result = runner._apply_placeholder_prune_for_generation(
        prune_placeholders="none",
        input_ids_np=input_ids_np,
        dense_input_ids=dense_input_ids,
        vision_features=vision_features,
        keep_mask=keep_mask,
        image_token_id=7,
    )

    assert result.input_ids is dense_input_ids
    assert result.image_features is vision_features
    assert result.kept_per_frame == [2, 2]
    assert result.elapsed_ms == 0.0
    assert result.bypassed is True


def test_schema_hash_includes_max_tokens() -> None:
    base = argparse.Namespace(
        manifest="manifest.toml",
        model_path="gemma",
        frame_count=8,
        anchor_arm="gemma_structural",
        keep_rate=0.5,
        prune_placeholders="none",
        n_warmup=1,
        max_tokens=16,
        vision_tower_layer=1,
        vision_tower_keep_rate=1.0,
    )
    longer = argparse.Namespace(**{**vars(base), "max_tokens": 32})

    base_row = runner._schema_row(base, RLTMaskConfig())
    longer_row = runner._schema_row(longer, RLTMaskConfig())

    assert base_row["artifact_payload"]["max_tokens"] == 16
    assert longer_row["artifact_payload"]["max_tokens"] == 32
    assert base_row["artifact_config_hash"] != longer_row["artifact_config_hash"]


def test_record_payload_emits_direct_prefill_and_generation_fields() -> None:
    record = runner.ItemResult(
        item_id="item",
        benchmark="videomme",
        group="short",
        anchor_arm="gemma_structural",
        keep_rate=0.5,
        n_frames=8,
        tokens_per_frame=256,
        kept_tokens_total=128,
        kept_per_frame=[16] * 8,
        dense_text="A",
        pruned_text="A",
        dense_correct=True,
        pruned_correct=True,
        dense_parse_failure=False,
        pruned_parse_failure=False,
        agreement=True,
        answer_index=0,
        dense_choice=0,
        pruned_choice=0,
        dense_timing=runner.StageTimings(
            decode_ms=1.0,
            processor_ms=2.0,
            novelty_ms=0.0,
            mask_ms=0.0,
            prune_ms=0.0,
            vision_ms=3.0,
            multimodal_prefill_ms=4.0,
            text_generation_ms=5.0,
            generate_ms=9.0,
            end_to_end_ms=15.0,
        ),
        pruned_timing=runner.StageTimings(
            decode_ms=1.0,
            processor_ms=2.0,
            novelty_ms=0.0,
            mask_ms=0.5,
            prune_ms=0.25,
            vision_ms=3.0,
            multimodal_prefill_ms=2.0,
            text_generation_ms=4.0,
            generate_ms=6.0,
            end_to_end_ms=12.75,
        ),
        dense_prompt_tokens=100,
        pruned_prompt_tokens=50,
        dense_generation_tokens=2,
        pruned_generation_tokens=2,
        dense_prompt_tps=25.0,
        pruned_prompt_tps=25.0,
        dense_generation_tps=1.0,
        pruned_generation_tps=1.0,
        metadata={},
    )

    payload = runner._record_payload(record)

    assert payload["dense_timing_ms"]["multimodal_prefill_ms"] == 4.0
    assert payload["dense_timing_ms"]["text_generation_ms"] == 5.0
    assert payload["pruned_timing_ms"]["multimodal_prefill_ms"] == 2.0
    assert payload["pruned_timing_ms"]["text_generation_ms"] == 4.0


def test_resume_loader_reads_schema_and_item_rows(tmp_path: Path) -> None:
    path = tmp_path / "out.jsonl"
    schema = {"kind": "schema", "artifact_config_hash": "abc"}
    rows = [_payload("a"), _payload("b")]
    with path.open("w", encoding="utf-8") as handle:
        handle.write(json.dumps(schema) + "\n")
        for row in rows:
            handle.write(json.dumps(row) + "\n")

    loaded_schema, loaded_rows = runner._load_output_rows_for_resume(path)

    assert loaded_schema == schema
    assert [row["item_id"] for row in loaded_rows] == ["a", "b"]


def test_payload_summary_includes_resumed_rows() -> None:
    summary = runner._summarize_payload_rows([_payload("a"), _payload("b")])

    assert summary["n_items"] == 2
    assert summary["dense_accuracy"] == 1.0
    assert summary["pruned_accuracy"] == 1.0
    assert summary["mean_keep_rate"] == 0.5
