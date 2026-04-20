#!/usr/bin/env python3
"""Phase 1.57 — Feature-drift by BlockClass (STATIC/SHIFTED/NOVEL).

Measures per-token cosine similarity between adjacent-frame ViT features,
stratified by the planner's block classification. Preregistered in
``research/experiments/2026/2026-04-19-phase-1_57-feature-drift-mechanism-prereg.md``.

Hypotheses (earned vs falsified decided in the findings doc):
  H1  Gemma  STATIC mean cos ∈ [0.60, 0.85]
  H2  Qwen   STATIC mean cos ∈ [0.95, 1.000]
  H3  Gemma  STATIC cos decreases monotonically across 8f → 16f → 32f
  H4  (deferred) entropy-vs-cosine correlation vs per-cell accuracy

Scope of this scaffold:
- **Qwen 2.5-VL-7B-Instruct-4bit**: pure CPU path. Reuses cached dense ViT
  features (``research/cache/dense_features/``), decodes the same frames
  so block classification lines up with the 28-pixel per-token grid, and
  emits per-class cosine aggregates. Runs without MLX.
- **Gemma 4-E4B-4bit**: deferred to a follow-up pass. Gemma lacks the
  feature cache key schema (pre-pooled 14×14 grid vs 16×16 post-pool)
  and requires an inline ViT encode. Stubbed with ``NotImplementedError``
  so the CLI surface already exists when the Gemma path lands.

What drift we actually measure:
  For each pair of adjacent frames (t, t+1) in a clip, per block:
    1. pixel-diff-based classification → STATIC / SHIFTED / NOVEL
    2. per-block cosine similarity between frame_t's ViT feature at that
       spatial position and frame_{t+1}'s ViT feature at the same position
  Aggregated per class across all (item, pair, block) triples.

  Under the planner's defaults (MEAN stat, 3.0/8.0 thresholds) the
  STATIC class is "tokens the planner would have said are reusable."
  Per Sam's research_queue lines 14-29, a cache-substitute forward pass
  at those positions drifts from a fresh encode because ViT global
  attention mixes NOVEL neighbors' content into the output tokens.
  Adjacent-frame fresh-vs-fresh cosine is the direct measurement of
  that same mixing phenomenon: the same spatial position encodes
  differently in frame_{t+1} than in frame_t whenever NOVEL content
  appeared nearby, even if the local pixel content is unchanged.

Output JSON schema (stable):
{
  "model": "qwen2.5-vl-7b-4bit",
  "manifest": [...],
  "frame_count": 8,
  "planner": {"statistic": "mean", "static_threshold": 3.0,
              "shifted_threshold": 8.0},
  "cache_hits": int, "cache_misses": int,
  "per_item": [
     {"item_id": str, "benchmark": str, "group": str,
      "n_pairs": int,
      "class_counts": {"static": N, "shifted": N, "novel": N},
      "per_class_cos": {"static": {...}, "shifted": {...}, "novel": {...}}}
  ],
  "aggregate": {
    "static":  {"n": N, "mean_cos": ..., "std_cos": ..., "median_cos": ...,
                "p05_cos": ..., "p95_cos": ...},
    "shifted": {...},
    "novel":   {...}
  }
}

Usage:
    uv run python scripts/measure_feature_drift.py \\
        --model qwen \\
        --manifest research/benchmark_manifests/videomme_dev_v1.toml \\
        --frame-count 8 \\
        --output research/experiments/2026/artifacts/phase1_57/qwen_8f.json
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
from codec_through.temporal import (
    BlockClass,
    BlockStatistic,
    PlannerConfig,
    classify_blocks_with_planner,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
RUNNER_PATH = REPO_ROOT / "scripts" / "run_benchmark_track_a.py"

# Qwen 2.5-VL-7B: 28-pixel block = one merged ViT token (patch 14 × merge 2).
QWEN_BLOCK_SIZE = 28
QWEN_FRAME_SIZE = 560
QWEN_SPATIAL_MERGE = 2
DEFAULT_QWEN_MODEL = Path.home() / "models" / "Qwen2.5-VL-7B-Instruct-4bit"

CLASS_KEYS = ("static", "shifted", "novel")
CLASS_ENUM_TO_KEY = {
    BlockClass.STATIC: "static",
    BlockClass.SHIFTED: "shifted",
    BlockClass.NOVEL: "novel",
}


@dataclass(frozen=True, slots=True)
class DriftSample:
    """One (item, pair, block) measurement."""

    item_id: str
    benchmark: str
    group: str
    frame_pair: tuple[int, int]
    block_row: int
    block_col: int
    block_class: int  # BlockClass enum value
    cosine_sim: float


def _load_runner_module() -> Any:
    """Load the benchmark runner as an importable module."""
    name = "_feature_drift_runner"
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


def _frames_to_numpy(frames: list[Any], *, expected_size: int) -> npt.NDArray[np.uint8]:
    out = np.stack([np.asarray(f, dtype=np.uint8) for f in frames], axis=0)
    if out.ndim != 4 or out.shape[1:3] != (expected_size, expected_size):
        raise RuntimeError(f"unexpected decoded-frame tensor shape: {out.shape}")
    return out


def _features_per_frame_qwen(
    features: npt.NDArray[Any],
    image_grid_thw: npt.NDArray[np.int64],
) -> list[npt.NDArray[np.float32]]:
    """Split the flat token feature array into per-frame [H, W, D]."""
    per_frame: list[npt.NDArray[np.float32]] = []
    cursor = 0
    for t, patches_h, patches_w in image_grid_thw.tolist():
        if t != 1:
            raise RuntimeError(f"expected temporal grid == 1, got {t}")
        tokens_h = patches_h // QWEN_SPATIAL_MERGE
        tokens_w = patches_w // QWEN_SPATIAL_MERGE
        count = tokens_h * tokens_w
        block = features[cursor : cursor + count].astype(np.float32)
        per_frame.append(block.reshape(tokens_h, tokens_w, -1))
        cursor += count
    if cursor != features.shape[0]:
        raise RuntimeError(f"feature tokens consumed ({cursor}) != total ({features.shape[0]})")
    return per_frame


def _pairwise_cosine_sim(
    a: npt.NDArray[np.float32],
    b: npt.NDArray[np.float32],
) -> npt.NDArray[np.float32]:
    """Per-block cosine SIMILARITY between two [H, W, D] feature grids."""
    if a.shape != b.shape:
        raise RuntimeError(f"feature grid shapes differ: {a.shape} vs {b.shape}")
    norm_a = np.linalg.norm(a, axis=-1)
    norm_b = np.linalg.norm(b, axis=-1)
    denom = np.clip(norm_a * norm_b, 1e-8, None)
    sim = np.sum(a * b, axis=-1) / denom
    return np.asarray(sim, dtype=np.float32)


def _process_qwen_item(
    runner: Any,
    item: Any,
    *,
    frame_count: int,
    planner: PlannerConfig,
    cache_dir: Path,
    model_path: Path,
    model_hash: str,
) -> tuple[list[DriftSample], dict[str, Any]]:
    frames, _active = runner._decode_uniform_frames(
        item.video_path,
        frame_count=frame_count,
        start_seconds=item.start_seconds,
        end_seconds=item.end_seconds,
    )
    frames_np = _frames_to_numpy(frames, expected_size=QWEN_FRAME_SIZE)
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
            max_size=QWEN_FRAME_SIZE,
        ),
    )
    loaded = get_feature_cache(key, cache_dir=cache_dir)
    if loaded is None:
        return [], {"item_id": item.item_id, "status": "cache_miss"}
    features, grid, _meta = loaded
    per_frame_features = _features_per_frame_qwen(features, grid)

    samples: list[DriftSample] = []
    for pair_idx in range(len(frames_np) - 1):
        classes = classify_blocks_with_planner(
            frames_np[pair_idx],
            frames_np[pair_idx + 1],
            block_size=QWEN_BLOCK_SIZE,
            config=planner,
        )
        cos = _pairwise_cosine_sim(
            per_frame_features[pair_idx],
            per_frame_features[pair_idx + 1],
        )
        if cos.shape != classes.shape:
            raise RuntimeError(
                f"block-grid mismatch: classes={classes.shape}, feats={cos.shape} "
                f"on item {item.item_id}"
            )
        blocks_h, blocks_w = cos.shape
        for r in range(blocks_h):
            for c in range(blocks_w):
                samples.append(
                    DriftSample(
                        item_id=item.item_id,
                        benchmark=item.benchmark,
                        group=item.group,
                        frame_pair=(pair_idx, pair_idx + 1),
                        block_row=r,
                        block_col=c,
                        block_class=int(classes[r, c]),
                        cosine_sim=float(cos[r, c]),
                    )
                )
    return samples, {
        "item_id": item.item_id,
        "status": "ok",
        "n_pairs": len(frames_np) - 1,
        "blocks_total": len(samples),
    }


def _percentiles(values: npt.NDArray[np.float64]) -> dict[str, float]:
    if values.size == 0:
        return {}
    return {
        "n": int(values.size),
        "mean_cos": float(np.mean(values)),
        "std_cos": float(np.std(values, ddof=0)),
        "median_cos": float(np.median(values)),
        "p05_cos": float(np.quantile(values, 0.05)),
        "p95_cos": float(np.quantile(values, 0.95)),
    }


def _aggregate_by_class(samples: list[DriftSample]) -> dict[str, dict[str, float]]:
    out: dict[str, dict[str, float]] = {}
    for block_class, key in CLASS_ENUM_TO_KEY.items():
        subset = np.asarray(
            [s.cosine_sim for s in samples if s.block_class == int(block_class)],
            dtype=np.float64,
        )
        out[key] = _percentiles(subset)
    return out


def _per_item_summary(samples_by_item: dict[str, list[DriftSample]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item_id, samples in samples_by_item.items():
        first = samples[0]
        counts = {k: 0 for k in CLASS_KEYS}
        for s in samples:
            counts[CLASS_ENUM_TO_KEY[BlockClass(s.block_class)]] += 1
        per_class = _aggregate_by_class(samples)
        rows.append(
            {
                "item_id": item_id,
                "benchmark": first.benchmark,
                "group": first.group,
                "n_pairs": len({s.frame_pair for s in samples}),
                "class_counts": counts,
                "per_class_cos": per_class,
            }
        )
    return rows


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


def _filter_group(items: list[Any], group: str | None) -> list[Any]:
    if group is None:
        return items
    return [i for i in items if i.group == group]


def _default_planner() -> PlannerConfig:
    return PlannerConfig(
        statistic=BlockStatistic.MEAN,
        static_threshold=3.0,
        shifted_threshold=8.0,
    )


def _run_qwen(
    args: argparse.Namespace,
    items: list[Any],
) -> dict[str, Any]:
    runner = _load_runner_module()
    if not args.model_path.exists():
        raise SystemExit(f"model path missing: {args.model_path}")
    model_hash = model_content_sha256(args.model_path)
    planner = _default_planner()

    all_samples: list[DriftSample] = []
    samples_by_item: dict[str, list[DriftSample]] = {}
    diagnostics: list[dict[str, Any]] = []
    hits = misses = 0
    for item in items:
        samples, diag = _process_qwen_item(
            runner,
            item,
            frame_count=args.frame_count,
            planner=planner,
            cache_dir=args.cache_dir,
            model_path=args.model_path,
            model_hash=model_hash,
        )
        diagnostics.append(diag)
        if diag["status"] == "ok":
            hits += 1
            all_samples.extend(samples)
            samples_by_item[item.item_id] = samples
        else:
            misses += 1

    aggregate = _aggregate_by_class(all_samples)
    per_item = _per_item_summary(samples_by_item)

    return {
        "model": "qwen2.5-vl-7b-4bit",
        "model_content_sha256": model_hash,
        "manifest": [str(p) for p in args.manifest],
        "group_filter": args.group,
        "frame_count": args.frame_count,
        "planner": {
            "statistic": planner.statistic.value,
            "static_threshold": planner.static_threshold,
            "shifted_threshold": planner.shifted_threshold,
        },
        "cache_hits": hits,
        "cache_misses": misses,
        "n_items": len(items),
        "n_samples": len(all_samples),
        "per_item": per_item,
        "aggregate": aggregate,
        "diagnostics": diagnostics,
    }


def _run_gemma(
    args: argparse.Namespace,
    items: list[Any],
) -> dict[str, Any]:
    raise NotImplementedError(
        "Gemma 4 path not yet wired. This scaffold reuses the Qwen feature cache "
        "(research/cache/dense_features/), which has no Gemma entries (different "
        "grid: 16×16 post-pool vs Qwen's 40×40 patches → 20×20 merged tokens). "
        "Gemma drift measurement requires inline ViT encode per frame via "
        "`model.vision_tower` + `model.embed_vision` (see run_novelty_pruning_gemma.py "
        "`_compute_vision_features`). Add that path as --model gemma support "
        "when ready to burn MLX compute."
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", choices=("qwen", "gemma"), default="qwen")
    parser.add_argument(
        "--manifest",
        type=Path,
        action="append",
        required=True,
        help="Benchmark manifest TOML (repeat for multiple)",
    )
    parser.add_argument(
        "--frame-count",
        type=int,
        default=8,
        help="Frames per clip (must match cached-feature frame count for Qwen)",
    )
    parser.add_argument(
        "--group",
        choices=("short", "medium", "long"),
        default=None,
        help="Optionally restrict to one VideoMME duration bucket",
    )
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=DEFAULT_FEATURE_CACHE_DIR,
        help="Dense feature cache dir (Qwen path only)",
    )
    parser.add_argument(
        "--model-path",
        type=Path,
        default=DEFAULT_QWEN_MODEL,
        help="MLX model directory (used for content hash; no weights loaded in Qwen path)",
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    runner = _load_runner_module()
    items = _filter_group(_load_manifests(runner, list(args.manifest)), args.group)
    if not items:
        raise SystemExit("no items loaded from provided manifests")

    if args.model == "qwen":
        summary = _run_qwen(args, items)
    elif args.model == "gemma":
        summary = _run_gemma(args, items)
    else:
        raise SystemExit(f"unknown model: {args.model}")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")

    agg = summary["aggregate"]
    print(
        f"model={summary['model']} items_ok={summary['cache_hits']} "
        f"miss={summary['cache_misses']} samples={summary['n_samples']}"
    )
    for key in CLASS_KEYS:
        row = agg.get(key, {})
        if not row:
            print(f"  {key:<8s} n=0 (no blocks of this class)")
            continue
        print(
            f"  {key:<8s} n={int(row['n']):>6d} "
            f"mean_cos={row['mean_cos']:+.4f} "
            f"p05={row['p05_cos']:+.4f} p95={row['p95_cos']:+.4f}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
