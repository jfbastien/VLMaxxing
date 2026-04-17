#!/usr/bin/env python3
"""Phase 1.36 feature-change oracle.

For every cached benchmark item whose ViT features are already present in
``research/cache/dense_features/``, decode its frames (CPU-only), compute the
four pixel-space statistics (MEAN, MAX_ABS, CHANGED_PIXEL_FRACTION,
TOP_K_MEAN) per 28-pixel block per adjacent-frame pair, load the cached ViT
features, and measure the per-block cosine distance between adjacent frames.

The output is a parquet of per-block rows plus a JSON summary with Pearson
and Spearman correlations between each pixel statistic and the ViT feature
delta. This answers "which pixel statistic best predicts real feature
change?" without running any new ViT inference.

The 28-pixel block size (QWEN_BLOCK_SIZE) aligns 1:1 with Qwen2.5-VL's
merged ViT tokens (patch_size=14 * spatial_merge=2), so per-block pixel
stats and per-token ViT features share the same spatial grid.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import numpy.typing as npt

from codec_through.feature_cache import (
    DEFAULT_FEATURE_CACHE_DIR,
    CacheKey,
    frame_sequence_sha256,
    get_feature_cache,
    model_content_sha256,
    preprocessing_hash,
)
from codec_through.temporal import BlockStatistic, PlannerConfig, block_statistic_values

REPO_ROOT = Path(__file__).resolve().parents[1]
RUNNER_PATH = REPO_ROOT / "scripts" / "run_benchmark_track_a.py"

# The Qwen2.5-VL default from the runner; kept here to decouple from CLI
# choice. One block = one merged ViT token.
QWEN_BLOCK_SIZE = 28
BENCHMARK_FRAME_SIZE = 560
SPATIAL_MERGE = 2

DEFAULT_MODEL_PATH = Path.home() / "models" / "Qwen2.5-VL-7B-Instruct-4bit"
STATISTICS: tuple[BlockStatistic, ...] = (
    BlockStatistic.MEAN,
    BlockStatistic.MAX_ABS,
    BlockStatistic.CHANGED_PIXEL_FRACTION,
    BlockStatistic.TOP_K_MEAN,
)


def _load_runner_module() -> Any:
    """Load the benchmark runner as an importable module.

    The runner lives in scripts/ and holds the item loaders and frame
    decoder. We load it via importlib to avoid duplicating that code.
    """

    name = "_feature_oracle_runner"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, RUNNER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot build spec for {RUNNER_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(name, None)
        raise
    return module


@dataclass(frozen=True, slots=True)
class OracleSample:
    item_id: str
    benchmark: str
    group: str
    frame_pair: tuple[int, int]
    block_row: int
    block_col: int
    # pixel stats (all derived from the same diff plane)
    mean: float
    max_abs: float
    cpf: float
    top_k_mean: float
    # feature delta
    cosine_distance: float


def _frames_to_numpy(frames: list[Any]) -> npt.NDArray[np.uint8]:
    """Convert a list of PIL Images to a float-ready uint8 tensor.

    The benchmark pipeline preprocesses frames through a letterbox pad to a
    square canvas at BENCHMARK_FRAME_SIZE. We need the same canvas here so
    the pixel diff blocks line up with ViT tokens, including any padding.
    """

    out = np.stack([np.asarray(frame, dtype=np.uint8) for frame in frames], axis=0)
    if out.ndim != 4 or out.shape[1:3] != (BENCHMARK_FRAME_SIZE, BENCHMARK_FRAME_SIZE):
        raise RuntimeError(f"unexpected frame tensor shape after decode: {out.shape}")
    return out


def _features_per_frame(
    features: npt.NDArray[Any], image_grid_thw: npt.NDArray[np.int64]
) -> list[npt.NDArray[np.float32]]:
    """Split the flat token feature array back into per-frame [H, W, D]."""

    per_frame: list[npt.NDArray[np.float32]] = []
    cursor = 0
    for t, patches_h, patches_w in image_grid_thw.tolist():
        if t != 1:
            raise RuntimeError(f"expected temporal grid == 1, got {t}")
        tokens_h = patches_h // SPATIAL_MERGE
        tokens_w = patches_w // SPATIAL_MERGE
        count = tokens_h * tokens_w
        block = features[cursor : cursor + count].astype(np.float32)
        per_frame.append(block.reshape(tokens_h, tokens_w, -1))
        cursor += count
    if cursor != features.shape[0]:
        raise RuntimeError(
            f"feature tokens consumed ({cursor}) does not match total ({features.shape[0]})"
        )
    return per_frame


def _pairwise_cosine(
    a: npt.NDArray[np.float32], b: npt.NDArray[np.float32]
) -> npt.NDArray[np.float32]:
    """Per-block cosine distance between two [H, W, D] feature grids."""

    if a.shape != b.shape:
        raise RuntimeError(f"feature grid shapes differ: {a.shape} vs {b.shape}")
    norm_a = np.linalg.norm(a, axis=-1)
    norm_b = np.linalg.norm(b, axis=-1)
    denom = np.clip(norm_a * norm_b, 1e-8, None)
    cosine_sim = np.sum(a * b, axis=-1) / denom
    return np.asarray(1.0 - cosine_sim, dtype=np.float32)


def _all_pixel_stats(
    frame_a: npt.NDArray[np.uint8], frame_b: npt.NDArray[np.uint8]
) -> dict[BlockStatistic, npt.NDArray[np.float32]]:
    out: dict[BlockStatistic, npt.NDArray[np.float32]] = {}
    for stat in STATISTICS:
        cfg = PlannerConfig(statistic=stat)
        out[stat] = block_statistic_values(frame_a, frame_b, block_size=QWEN_BLOCK_SIZE, config=cfg)
    return out


def _process_item(
    runner: Any,
    item: Any,
    *,
    frame_count: int,
    cache_dir: Path,
    model_path: Path,
    model_hash: str,
) -> tuple[list[OracleSample], dict[str, Any]]:
    frames, _active = runner._decode_uniform_frames(
        item.video_path,
        frame_count=frame_count,
        start_seconds=item.start_seconds,
        end_seconds=item.end_seconds,
    )
    frames_np = _frames_to_numpy(frames)
    key = CacheKey(
        model_id=str(model_path.resolve()),
        model_content_sha256=model_hash,
        item_id=item.item_id,
        frames_sha256=frame_sequence_sha256(frames),
        frame_count=len(frames),
        frame_size_h=frames[0].size[1],
        frame_size_w=frames[0].size[0],
        preprocessing_hash=preprocessing_hash(
            decode_backend="pyav",
            sampling_mode="uniform_global",
            max_size=BENCHMARK_FRAME_SIZE,
        ),
    )
    loaded = get_feature_cache(key, cache_dir=cache_dir)
    if loaded is None:
        return [], {"item_id": item.item_id, "status": "cache_miss"}
    features, grid, _meta = loaded
    per_frame = _features_per_frame(features, grid)

    samples: list[OracleSample] = []
    for pair_idx in range(len(frames_np) - 1):
        pixel_stats = _all_pixel_stats(frames_np[pair_idx], frames_np[pair_idx + 1])
        cosine = _pairwise_cosine(per_frame[pair_idx], per_frame[pair_idx + 1])
        if cosine.shape != pixel_stats[BlockStatistic.MEAN].shape:
            raise RuntimeError(
                f"block-grid mismatch: pixel={pixel_stats[BlockStatistic.MEAN].shape}, "
                f"feature={cosine.shape} on item {item.item_id}"
            )
        blocks_h, blocks_w = cosine.shape
        for r in range(blocks_h):
            for c in range(blocks_w):
                samples.append(
                    OracleSample(
                        item_id=item.item_id,
                        benchmark=item.benchmark,
                        group=item.group,
                        frame_pair=(pair_idx, pair_idx + 1),
                        block_row=r,
                        block_col=c,
                        mean=float(pixel_stats[BlockStatistic.MEAN][r, c]),
                        max_abs=float(pixel_stats[BlockStatistic.MAX_ABS][r, c]),
                        cpf=float(pixel_stats[BlockStatistic.CHANGED_PIXEL_FRACTION][r, c]),
                        top_k_mean=float(pixel_stats[BlockStatistic.TOP_K_MEAN][r, c]),
                        cosine_distance=float(cosine[r, c]),
                    )
                )
    return samples, {"item_id": item.item_id, "status": "ok", "blocks": len(samples)}


def _load_manifest_items(runner: Any, manifest_path: Path) -> list[Any]:
    payload = tomllib.loads(manifest_path.read_text())
    benchmark = payload["benchmark"]
    item_ids = payload["item_ids"]
    return runner._load_items_by_id(benchmark, item_ids)


def _load_manifests(runner: Any, manifest_paths: list[Path]) -> list[Any]:
    items: list[Any] = []
    seen: set[str] = set()
    for manifest_path in manifest_paths:
        for item in _load_manifest_items(runner, manifest_path):
            if item.item_id in seen:
                continue
            items.append(item)
            seen.add(item.item_id)
    return items


def _pearson(x: npt.NDArray[np.float64], y: npt.NDArray[np.float64]) -> float:
    if x.size < 2 or np.std(x) == 0 or np.std(y) == 0:
        return float("nan")
    r = float(np.corrcoef(x, y)[0, 1])
    return r


def _spearman(x: npt.NDArray[np.float64], y: npt.NDArray[np.float64]) -> float:
    if x.size < 2:
        return float("nan")
    rx = _rankdata(x)
    ry = _rankdata(y)
    return _pearson(rx, ry)


def _rankdata(x: npt.NDArray[np.float64]) -> npt.NDArray[np.float64]:
    """Average-rank tie handling, matching scipy.stats.rankdata default."""

    order = np.argsort(x, kind="mergesort")
    ranks = np.empty_like(x, dtype=np.float64)
    ranks[order] = np.arange(1, x.size + 1, dtype=np.float64)
    sorted_x = x[order]
    i = 0
    while i < sorted_x.size:
        j = i + 1
        while j < sorted_x.size and sorted_x[j] == sorted_x[i]:
            j += 1
        if j - i > 1:
            avg = 0.5 * (ranks[order[i]] + ranks[order[j - 1]])
            ranks[order[i:j]] = avg
        i = j
    return ranks


def _correlation_summary(
    samples: list[OracleSample],
) -> dict[str, Any]:
    if not samples:
        return {"n_blocks": 0, "statistics": {}}
    y = np.asarray([s.cosine_distance for s in samples], dtype=np.float64)
    stats_arrays = {
        "mean": np.asarray([s.mean for s in samples], dtype=np.float64),
        "max_abs": np.asarray([s.max_abs for s in samples], dtype=np.float64),
        "cpf": np.asarray([s.cpf for s in samples], dtype=np.float64),
        "top_k_mean": np.asarray([s.top_k_mean for s in samples], dtype=np.float64),
    }
    per_stat: dict[str, dict[str, float]] = {}
    for name, x in stats_arrays.items():
        per_stat[name] = {
            "pearson_r": _pearson(x, y),
            "spearman_r": _spearman(x, y),
        }
    return {
        "n_blocks": len(samples),
        "cosine_min": float(np.min(y)),
        "cosine_max": float(np.max(y)),
        "cosine_mean": float(np.mean(y)),
        "cosine_p95": float(np.quantile(y, 0.95)),
        "statistics": per_stat,
    }


def _write_parquet(samples: list[OracleSample], out_path: Path) -> None:
    import pyarrow as pa
    import pyarrow.parquet as pq

    out_path.parent.mkdir(parents=True, exist_ok=True)
    table = pa.table(
        {
            "item_id": [s.item_id for s in samples],
            "benchmark": [s.benchmark for s in samples],
            "group": [s.group for s in samples],
            "frame_a": [s.frame_pair[0] for s in samples],
            "frame_b": [s.frame_pair[1] for s in samples],
            "block_row": [s.block_row for s in samples],
            "block_col": [s.block_col for s in samples],
            "mean": [s.mean for s in samples],
            "max_abs": [s.max_abs for s in samples],
            "cpf": [s.cpf for s in samples],
            "top_k_mean": [s.top_k_mean for s in samples],
            "cosine_distance": [s.cosine_distance for s in samples],
        }
    )
    pq.write_table(table, out_path, compression="zstd")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest", type=Path, action="append", required=True, help="Benchmark manifest TOML"
    )
    parser.add_argument(
        "--frame-count", type=int, default=8, help="Frames per clip (matches cached features)"
    )
    parser.add_argument(
        "--cache-dir", type=Path, default=DEFAULT_FEATURE_CACHE_DIR, help="Dense feature cache dir"
    )
    parser.add_argument("--model-path", type=Path, default=DEFAULT_MODEL_PATH)
    parser.add_argument("--output", type=Path, required=True, help="Parquet output path")
    parser.add_argument("--summary", type=Path, required=True, help="JSON correlation summary path")
    args = parser.parse_args()

    runner = _load_runner_module()
    items = _load_manifests(runner, list(args.manifest))
    if not items:
        raise SystemExit("no items loaded from provided manifests")

    if not args.model_path.exists():
        raise SystemExit(f"model path missing: {args.model_path}")
    model_hash = model_content_sha256(args.model_path)

    all_samples: list[OracleSample] = []
    diagnostics: list[dict[str, Any]] = []
    hits = misses = 0
    for item in items:
        samples, diag = _process_item(
            runner,
            item,
            frame_count=args.frame_count,
            cache_dir=args.cache_dir,
            model_path=args.model_path,
            model_hash=model_hash,
        )
        diagnostics.append(diag)
        if diag["status"] == "ok":
            hits += 1
            all_samples.extend(samples)
        else:
            misses += 1

    summary = _correlation_summary(all_samples)
    summary["manifests"] = [str(p) for p in args.manifest]
    summary["frame_count"] = args.frame_count
    summary["cache_hits"] = hits
    summary["cache_misses"] = misses
    summary["model_content_sha256"] = model_hash
    summary["diagnostics"] = diagnostics

    _write_parquet(all_samples, args.output)
    args.summary.parent.mkdir(parents=True, exist_ok=True)
    args.summary.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")

    stats = summary["statistics"]
    print(
        f"items ok={hits} miss={misses} blocks={summary['n_blocks']} "
        f"cos_mean={summary['cosine_mean']:.4f} cos_p95={summary['cosine_p95']:.4f}"
    )
    for name, row in stats.items():
        print(f"  {name:<12s} pearson={row['pearson_r']:+.4f} spearman={row['spearman_r']:+.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
