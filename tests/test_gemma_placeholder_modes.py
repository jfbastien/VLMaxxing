from __future__ import annotations

import argparse

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
