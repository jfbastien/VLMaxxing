from __future__ import annotations

import tomllib
from pathlib import Path


def test_corpus_manifest_includes_synthetic_tier() -> None:
    payload = tomllib.loads(Path("data/corpus/manifest.toml").read_text())
    clips = payload["clip"]
    clip_ids = {clip["id"] for clip in clips}

    assert "xiph_akiyo_cif" in clip_ids
    assert "synthetic_affine_pan" in clip_ids
    assert "synthetic_screen_ocr" in clip_ids
    assert "synthetic_affine_pan_v2" in clip_ids
    assert "synthetic_mid_text_flash" in clip_ids


def test_generated_manifest_clips_pin_expected_sha256() -> None:
    payload = tomllib.loads(Path("data/corpus/manifest.toml").read_text())
    generated_clips = [clip for clip in payload["clip"] if clip["method"] == "generated"]

    assert generated_clips
    for clip in generated_clips:
        assert clip["expected_sha256"]


def test_prompt_bank_items_reference_manifest_clips() -> None:
    manifest = tomllib.loads(Path("data/corpus/manifest.toml").read_text())
    manifest_clip_ids = {clip["id"] for clip in manifest["clip"]}
    for prompt_bank_path, expected_count in (
        (Path("research/prompt_bank/local_suite_v1.toml"), 12),
        (Path("research/prompt_bank/local_suite_v2.toml"), 12),
    ):
        prompt_bank = tomllib.loads(prompt_bank_path.read_text())
        items = prompt_bank["item"]

        assert prompt_bank["sampling_mode"] == "contiguous_window"
        assert len(items) == expected_count

        for item in items:
            assert item["clip_id"] in manifest_clip_ids
            assert 0 <= item["answer_index"] < len(item["choices"])
            assert item["window_start"] >= 0
            assert item["window_frames"] > 1
            if "critical_pair_indices" in item:
                assert all(index >= 0 for index in item["critical_pair_indices"])
