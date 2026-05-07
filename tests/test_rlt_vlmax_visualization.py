from __future__ import annotations

import hashlib
import io
from types import SimpleNamespace

import numpy as np
from PIL import Image

from scripts import render_rlt_vlmax_composition_overlays as renderer


def _png_digest(image: Image.Image) -> str:
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return hashlib.sha256(buffer.getvalue()).hexdigest()


def test_composition_frame_render_is_byte_stable() -> None:
    spec = SimpleNamespace(benchmark="unit", video_id="synthetic", role="determinism")
    base = Image.new("RGB", (96, 54), (120, 140, 160))
    stats = {
        "rlt_admit_active_pixel_fraction": 0.25,
        "vlmax_fresh_active_pixel_fraction": 0.20,
        "combined_refresh_active_pixel_fraction": 0.35,
        "overlap_active_pixel_fraction": 0.10,
    }

    first = renderer._render_frame(
        spec=spec,
        frame_idx=0,
        frame_count=1,
        crop=base,
        vl_overlay=base,
        rlt_overlay=base,
        combined_overlay=base,
        stats=stats,
        rlt_keep_rate=0.125,
    )
    second = renderer._render_frame(
        spec=spec,
        frame_idx=0,
        frame_count=1,
        crop=base,
        vl_overlay=base,
        rlt_overlay=base,
        combined_overlay=base,
        stats=stats,
        rlt_keep_rate=0.125,
    )

    assert first.size == renderer.OUTPUT_SIZE
    assert _png_digest(first) == _png_digest(second)


def test_measured_cvision_frame_render_is_deterministic() -> None:
    spec = SimpleNamespace(benchmark="VideoMME", video_id="synthetic", role="mechanism")
    base = Image.new("RGB", (96, 54), (120, 140, 160))
    stats = {
        "kept_active_pixel_fraction": 0.50,
        "skipped_active_pixel_fraction": 0.50,
    }
    metrics = {
        "e2e_speedup": 1.058,
        "vision_reduction": 0.703,
        "rlt_scorer_ms": 19.2,
        "scorer_cost_ratio_maxmin_over_rlt": 122.0,
    }

    first = renderer._render_measured_frame(
        spec=spec,
        frame_idx=0,
        frame_count=1,
        crop=base,
        dense_overlay=base,
        kept_overlay=base,
        skipped_overlay=base,
        stats=stats,
        token_keep_rate=0.5,
        metrics=metrics,
    )
    second = renderer._render_measured_frame(
        spec=spec,
        frame_idx=0,
        frame_count=1,
        crop=base,
        dense_overlay=base,
        kept_overlay=base,
        skipped_overlay=base,
        stats=stats,
        token_keep_rate=0.5,
        metrics=metrics,
    )

    assert first.size == renderer.OUTPUT_SIZE
    assert _png_digest(first) == _png_digest(second)


def test_composition_stats_names_expose_active_pixel_denominator() -> None:
    crop = Image.new("RGB", (10, 10), (0, 0, 0))
    rlt_active = np.zeros((10, 10), dtype=bool)
    vl_fresh = np.zeros((10, 10), dtype=bool)
    rlt_active[:5, :5] = True
    vl_fresh[5:, 5:] = True

    _, stats = renderer._overlay_combined(crop, rlt_active, vl_fresh)

    assert stats["rlt_admit_active_pixel_fraction"] == 0.25
    assert stats["vlmax_fresh_active_pixel_fraction"] == 0.25
    assert stats["combined_refresh_active_pixel_fraction"] == 0.50
    assert stats["overlap_active_pixel_fraction"] == 0.0
    assert "rlt_admit_fraction" not in stats


def test_measured_grid_mask_stats_use_kept_and_skipped_denominators() -> None:
    crop = Image.new("RGB", (8, 8), (0, 0, 0))
    keep = np.zeros((4, 4), dtype=bool)
    keep[:2, :] = True

    _, stats = renderer._overlay_grid_mask(
        crop,
        keep,
        active_box=(0, 0, 8, 8),
        padded_size=(8, 8),
        mode="kept",
    )

    assert stats["kept_active_pixel_fraction"] == 0.5
    assert stats["skipped_active_pixel_fraction"] == 0.5
