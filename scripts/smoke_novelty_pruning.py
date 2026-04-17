"""CPU-only smoke test for phase 1.51R novelty-pruning on a real video.

Exercises the full CPU half of the novelty-pruning pipeline end-to-end:
PyAV video decode → uniform frame sampling → square-pad to 512×512 →
per-token pixel novelty (16×16 post-pool grid, Gemma geometry) →
per-anchor-arm keep mask. Emits a JSON report describing, per arm,
the keep-rate, overlap with the `none` baseline, and the kept-token
position set.

This is a harness-free sanity check you can run once VideoMME videos
are on disk (or any .mp4), well before MLX / GPU work begins. It
validates that the anchor-arm policy module survives real-frame inputs
(divisibility checks, non-square grids, channel handling) without
needing a Gemma model loaded.

Example:
    uv run python scripts/smoke_novelty_pruning.py \
        data/benchmarks/videomme/videos/0eJvnKwGThw.mp4 \
        --keep-rate 0.5 --frame-count 8 --output /tmp/smoke.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image

from codec_through.novelty_pruning import (
    ANCHOR_ARMS,
    AnchorArm,
    NoveltyPruneConfig,
    compute_keep_mask,
    compute_pixel_novelty,
)
from codec_through.video_decode import decode_uniform_frames

BENCHMARK_FRAME_SIZE = 512  # Runtime-verified Gemma processor emission (2026-04-18).
GEMMA_GRID_SHAPE = (16, 16)  # 256 placeholders/frame observed via rendered prompt probe,
# not the 280 (14×20) that processor.image_seq_length falsely claims.


def _square_pad(frame: Image.Image, size: int) -> Image.Image:
    width, height = frame.size
    scale = min(size / width, size / height)
    resized = frame.resize(
        (round(width * scale), round(height * scale)),
        Image.Resampling.BICUBIC,
    )
    canvas = Image.new("RGB", (size, size), color=(0, 0, 0))
    offset_x = (size - resized.width) // 2
    offset_y = (size - resized.height) // 2
    canvas.paste(resized, (offset_x, offset_y))
    return canvas


def _decode_uniform(video_path: Path, frame_count: int) -> np.ndarray:
    """Memory-bounded uniform sample; letterbox each to BENCHMARK_FRAME_SIZE.

    Replaces the previous full-clip decode that contributed to the
    2026-04-18 OOM (see codec_through.video_decode module docstring).
    """
    selected = decode_uniform_frames(video_path, frame_count=frame_count)
    padded = [_square_pad(f, BENCHMARK_FRAME_SIZE) for f in selected]
    stack = np.stack([np.asarray(f, dtype=np.float32) for f in padded], axis=0)
    return stack


def _make_config(arm: AnchorArm, keep_rate: float) -> NoveltyPruneConfig:
    return NoveltyPruneConfig(
        anchor_arm=arm,
        keep_rate=keep_rate,
        grid_shape=GEMMA_GRID_SHAPE,
    )


def run_smoke(
    video_path: Path,
    *,
    keep_rate: float,
    frame_count: int,
) -> dict[str, object]:
    frames = _decode_uniform(video_path, frame_count)
    novelty = compute_pixel_novelty(frames, grid_shape=GEMMA_GRID_SHAPE)
    f_count, t_count = novelty.shape

    # Attention / feature substitutes for the arms that need them:
    # - cls_attention_proxy: use novelty itself as a proxy (correlated but
    #   ranked independently so the arm still exercises its own code path).
    # - nuwa_pillar / max_min_diversity: synthesize features from pixel-mean
    #   per token block. Deterministic, no randomness.
    rng = np.random.default_rng(0)
    features = rng.standard_normal((f_count, t_count, 16)).astype(np.float32)
    cls_attention = novelty.copy()

    baseline_arm: AnchorArm = "none"
    baseline_mask = compute_keep_mask(novelty, config=_make_config(baseline_arm, keep_rate))

    per_arm: dict[str, dict[str, object]] = {}
    for arm in ANCHOR_ARMS:
        mask = compute_keep_mask(
            novelty,
            config=_make_config(arm, keep_rate),
            features=features if arm in ("nuwa_pillar", "max_min_diversity") else None,
            cls_attention=cls_attention if arm == "cls_attention_proxy" else None,
        )
        kept_counts = mask.sum(axis=1).tolist()
        overlap_with_baseline = int((mask & baseline_mask).sum())
        per_arm[arm] = {
            "kept_per_frame": kept_counts,
            "total_kept": int(mask.sum()),
            "total_tokens": f_count * t_count,
            "effective_keep_rate": float(mask.sum() / (f_count * t_count)),
            "overlap_with_baseline_count": overlap_with_baseline,
            "overlap_with_baseline_rate": float(
                overlap_with_baseline / max(1, int(baseline_mask.sum()))
            ),
        }

    return {
        "video_path": str(video_path),
        "frame_count": int(f_count),
        "token_count_per_frame": int(t_count),
        "grid_shape": list(GEMMA_GRID_SHAPE),
        "requested_keep_rate": keep_rate,
        "baseline_arm": baseline_arm,
        "novelty_stats": {
            "min": float(novelty.min()),
            "max": float(novelty.max()),
            "mean": float(novelty.mean()),
            "per_frame_mean": novelty.mean(axis=1).tolist(),
        },
        "per_arm": per_arm,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("video_path", type=Path)
    parser.add_argument("--keep-rate", type=float, default=0.5)
    parser.add_argument("--frame-count", type=int, default=8)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()
    report = run_smoke(
        args.video_path,
        keep_rate=args.keep_rate,
        frame_count=args.frame_count,
    )
    payload = json.dumps(report, indent=2)
    if args.output is not None:
        args.output.write_text(payload)
    else:
        print(payload)


if __name__ == "__main__":
    main()
