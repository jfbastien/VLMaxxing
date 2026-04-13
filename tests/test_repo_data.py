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


def test_prompt_bank_items_reference_manifest_clips() -> None:
    manifest = tomllib.loads(Path("data/corpus/manifest.toml").read_text())
    prompt_bank = tomllib.loads(Path("research/prompt_bank/local_suite_v1.toml").read_text())

    manifest_clip_ids = {clip["id"] for clip in manifest["clip"]}
    items = prompt_bank["item"]

    assert prompt_bank["sampling_mode"] == "contiguous_window"
    assert len(items) == 12

    for item in items:
        assert item["clip_id"] in manifest_clip_ids
        assert 0 <= item["answer_index"] < len(item["choices"])
