# ruff: noqa: E402

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pytest


def _is_darwin() -> bool:
    return sys.platform == "darwin"


if not _is_darwin():
    pytest.skip("MLX tests require macOS/Darwin", allow_module_level=True)

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
        group_keep_rates={},
        prune_placeholders="none",
        group_prune_placeholders={},
        n_warmup=1,
        max_tokens=16,
        vision_tower_layer=1,
        vision_tower_keep_rate=1.0,
        group_vision_keep_rates={},
    )
    longer = argparse.Namespace(**{**vars(base), "max_tokens": 32})

    base_row = runner._schema_row(base, RLTMaskConfig())
    longer_row = runner._schema_row(longer, RLTMaskConfig())

    assert base_row["artifact_payload"]["max_tokens"] == 16
    assert base_row["artifact_payload"]["logprob_capture_version"] == runner.LOGPROB_CAPTURE_VERSION
    assert longer_row["artifact_payload"]["max_tokens"] == 32
    assert base_row["artifact_config_hash"] != longer_row["artifact_config_hash"]


def test_first_generated_token_confidence_computes_selected_and_top2_margins() -> None:
    class Tokenizer:
        def decode(self, token_ids: list[int]) -> str:
            return f"tok-{token_ids[0]}"

        def encode(self, text: str, *, add_special_tokens: bool) -> list[int]:
            del add_special_tokens
            return {"A": [0], " A": [1], "B": [2], " B": [3]}[text]

    confidence = runner._first_generated_token_confidence(
        token_id=2,
        logprobs=mx.array([-3.0, -1.0, -0.2, -2.0], dtype=mx.float32),
        tokenizer=Tokenizer(),
        n_candidates=2,
    )

    assert confidence["first_generated_token_id"] == 2
    assert confidence["first_generated_token_text"] == "tok-2"
    assert confidence["first_generated_selected_logprob"] == pytest.approx(-0.2)
    assert confidence["first_generated_top_logprob"] == pytest.approx(-0.2)
    assert confidence["first_generated_second_logprob"] == pytest.approx(-1.0)
    assert confidence["first_generated_top2_margin"] == pytest.approx(0.8)
    assert confidence["first_generated_selected_margin"] == pytest.approx(0.8)
    assert confidence["first_generated_candidate_top_letter"] == "B"
    assert confidence["first_generated_candidate_second_letter"] == "A"
    assert confidence["first_generated_candidate_top2_margin"] == pytest.approx(0.8)


def test_first_generated_token_confidence_accepts_bfloat16_logprobs() -> None:
    class Tokenizer:
        def decode(self, token_ids: list[int]) -> str:
            return f"tok-{token_ids[0]}"

        def encode(self, text: str, *, add_special_tokens: bool) -> list[int]:
            del add_special_tokens
            return {"A": [0], " A": [1], "B": [2], " B": [3]}[text]

    confidence = runner._first_generated_token_confidence(
        token_id=2,
        logprobs=mx.array([-3.0, -1.0, -0.25, -2.0], dtype=mx.bfloat16),
        tokenizer=Tokenizer(),
        n_candidates=2,
    )

    assert confidence["first_generated_token_id"] == 2
    assert confidence["first_generated_selected_logprob"] == pytest.approx(-0.25)
    assert confidence["first_generated_candidate_top_letter"] == "B"


def test_schema_hash_includes_group_keep_rate_overrides() -> None:
    base = argparse.Namespace(
        manifest="manifest.toml",
        model_path="gemma",
        frame_count=8,
        anchor_arm="gemma_structural",
        keep_rate=0.5,
        group_keep_rates={},
        prune_placeholders="rlt",
        group_prune_placeholders={},
        n_warmup=1,
        max_tokens=16,
        vision_tower_layer=1,
        vision_tower_keep_rate=0.5,
        group_vision_keep_rates={},
        vision_tower_score_mode="rlt_topk",
        arm_order="abba",
        prefill_step_size=1024,
    )
    adaptive = argparse.Namespace(
        **{
            **vars(base),
            "group_keep_rates": {"moving_attribute": 0.85},
            "group_vision_keep_rates": {"moving_attribute": 0.85},
        }
    )

    base_row = runner._schema_row(base, RLTMaskConfig())
    adaptive_row = runner._schema_row(adaptive, RLTMaskConfig())

    assert adaptive_row["artifact_payload"]["group_keep_rates"] == {"moving_attribute": 0.85}
    assert adaptive_row["artifact_payload"]["group_vision_tower_keep_rates"] == {
        "moving_attribute": 0.85
    }
    assert base_row["artifact_config_hash"] != adaptive_row["artifact_config_hash"]


def test_schema_hash_includes_group_prune_placeholder_overrides() -> None:
    base = argparse.Namespace(
        manifest="manifest.toml",
        model_path="gemma",
        frame_count=8,
        anchor_arm="gemma_structural",
        keep_rate=1.0,
        group_keep_rates={},
        prune_placeholders="none",
        group_prune_placeholders={},
        n_warmup=1,
        max_tokens=16,
        vision_tower_layer=1,
        vision_tower_keep_rate=0.5,
        group_vision_keep_rates={},
        vision_tower_score_mode="random_valid",
        arm_order="abba",
        prefill_step_size=1024,
    )
    scheduled = argparse.Namespace(
        **{
            **vars(base),
            "group_prune_placeholders": {"fine_grained_action": "rlt"},
        }
    )

    base_row = runner._schema_row(base, RLTMaskConfig())
    scheduled_row = runner._schema_row(scheduled, RLTMaskConfig())

    assert scheduled_row["artifact_payload"]["group_prune_placeholders"] == {
        "fine_grained_action": "rlt"
    }
    assert scheduled_row["artifact_payload"]["rlt_config"] is not None
    assert base_row["artifact_config_hash"] != scheduled_row["artifact_config_hash"]


def test_group_keep_rate_parser_and_resolver() -> None:
    parsed = runner._parse_group_keep_rates("long=0.7,medium=0.85")

    assert parsed == {"long": 0.7, "medium": 0.85}
    assert runner._resolve_group_keep_rate(0.5, parsed, "long") == 0.7
    assert runner._resolve_group_keep_rate(0.5, parsed, "short") == 0.5


def test_group_prune_placeholder_parser_and_resolver() -> None:
    parsed = runner._parse_group_prune_placeholders("fine_grained_action=rlt,moving_direction=none")

    assert parsed == {"fine_grained_action": "rlt", "moving_direction": "none"}
    assert runner._resolve_group_prune_placeholders("none", parsed, "fine_grained_action") == "rlt"
    assert runner._resolve_group_prune_placeholders("none", parsed, "action_localization") == "none"


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
        dense_first_generated_token_id=10,
        pruned_first_generated_token_id=11,
        dense_first_generated_token_text="A",
        pruned_first_generated_token_text="B",
        dense_first_generated_selected_logprob=-0.1,
        pruned_first_generated_selected_logprob=-0.3,
        dense_first_generated_top_logprob=-0.1,
        pruned_first_generated_top_logprob=-0.3,
        dense_first_generated_second_logprob=-1.0,
        pruned_first_generated_second_logprob=-0.9,
        dense_first_generated_top2_margin=0.9,
        pruned_first_generated_top2_margin=0.6,
        dense_first_generated_selected_margin=0.9,
        pruned_first_generated_selected_margin=0.6,
        dense_first_generated_confidence_capture_ms=1.0,
        pruned_first_generated_confidence_capture_ms=2.0,
        dense_first_generated_candidate_top_letter="A",
        pruned_first_generated_candidate_top_letter="B",
        dense_first_generated_candidate_second_letter="B",
        pruned_first_generated_candidate_second_letter="A",
        dense_first_generated_candidate_top_logprob=-0.1,
        pruned_first_generated_candidate_top_logprob=-0.3,
        dense_first_generated_candidate_second_logprob=-1.0,
        pruned_first_generated_candidate_second_logprob=-0.9,
        dense_first_generated_candidate_top2_margin=0.9,
        pruned_first_generated_candidate_top2_margin=0.6,
        metadata={},
    )

    payload = runner._record_payload(record)

    assert payload["dense_timing_ms"]["multimodal_prefill_ms"] == 4.0
    assert payload["dense_timing_ms"]["text_generation_ms"] == 5.0
    assert payload["pruned_timing_ms"]["multimodal_prefill_ms"] == 2.0
    assert payload["pruned_timing_ms"]["text_generation_ms"] == 4.0
    assert payload["dense_first_generated_top2_margin"] == 0.9
    assert payload["pruned_first_generated_top2_margin"] == 0.6
    assert payload["dense_first_generated_confidence_capture_ms"] == 1.0
    assert payload["pruned_first_generated_confidence_capture_ms"] == 2.0
    assert payload["dense_first_generated_candidate_top_letter"] == "A"
    assert payload["pruned_first_generated_candidate_top2_margin"] == 0.6


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
