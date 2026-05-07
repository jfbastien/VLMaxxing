from __future__ import annotations

import hashlib
import io
from pathlib import Path
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
        metrics={
            "e2e_speedup": 1.315,
            "scorer_cost_ratio_maxmin_over_rlt": 114.0,
        },
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
        metrics={
            "e2e_speedup": 1.315,
            "scorer_cost_ratio_maxmin_over_rlt": 114.0,
        },
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


def test_repo_relative_manifest_paths_are_portable() -> None:
    path = renderer.REPO_ROOT / "research" / "experiments" / "artifact.json"

    assert renderer._repo_relative_str(path) == "research/experiments/artifact.json"
    assert renderer._repo_relative_str(Path("relative/path.json")) == "relative/path.json"
