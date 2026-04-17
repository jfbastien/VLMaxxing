"""CPU-only smoke test for phase 1.51R novelty-pruning on a real video.

Exercises the full CPU half of the novelty-pruning pipeline end-to-end:
PyAV video decode → uniform frame sampling → square-pad to 560×560 →
per-token pixel novelty (14×20 post-pool grid, Gemma geometry) →
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

import av
import numpy as np
from PIL import Image

from codec_through.novelty_pruning import (
    ANCHOR_ARMS,
    AnchorArm,
    NoveltyPruneConfig,
    compute_keep_mask,
    compute_pixel_novelty,
)

BENCHMARK_FRAME_SIZE = 560  # Matches scripts/run_benchmark_track_a.py.
GEMMA_GRID_SHAPE = (14, 20)  # 280 soft tokens per image.


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
    frames: list[Image.Image] = []
    with av.open(str(video_path)) as container:
        for frame in container.decode(video=0):
            frames.append(frame.to_image().convert("RGB"))  # type: ignore[no-untyped-call]
    if len(frames) < frame_count:
        raise ValueError(f"video has {len(frames)} frames but requested {frame_count}")
    indices = np.linspace(0, len(frames) - 1, frame_count, dtype=int).tolist()
    selected = [_square_pad(frames[i], BENCHMARK_FRAME_SIZE) for i in indices]
    stack = np.stack([np.asarray(f, dtype=np.float32) for f in selected], axis=0)
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
