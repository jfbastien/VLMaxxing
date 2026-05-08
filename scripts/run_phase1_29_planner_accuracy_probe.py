#!/usr/bin/env python3
"""Phase 1.29 planner-accuracy probe for continuous codec scores on Qwen."""
# ruff: noqa: E402

from __future__ import annotations

import argparse
import gc
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import numpy as np

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from codec_through.codec.continuous_score import (  # noqa: E402
    CodecScoreSource,
    ScoreThresholds,
    calibrate_score_thresholds,
    class_share_vector,
    classify_score_grid,
    codec_score_units,
    macroblock_score_plane,
    project_macroblock_scores_to_token_grid,
    sparse_pair_spans,
    sparse_sample_indices,
)
from codec_through.codec.h264_metadata import H264MetadataExtractor  # noqa: E402
from codec_through.codec.onevision_patchification import FuseMode  # noqa: E402
from codec_through.feature_cache import DEFAULT_FEATURE_CACHE_DIR  # noqa: E402
from codec_through.precompute_cache import (  # noqa: E402
    decode_array,
    encode_array,
    read_json_cache,
    write_json_cache_atomic,
)
from codec_through.temporal import (  # noqa: E402
    BlockStatistic,
    BlockThresholds,
    PlannerConfig,
    classify_blocks_with_planner,
)
from codec_through.track_a import (
    active_region_block_mask,
    flattened_reuse_mask,
    qwen_merged_token_counts,
)  # noqa: E402
from codec_through.video_decode import _count_frames  # noqa: E402

runner: Any | None = None
mx: Any | None = None

DEFAULT_OUTPUT_PATH = Path(
    "research/experiments/2026/artifacts/phase1_29_planner_accuracy_probe/results.jsonl"
)
DEFAULT_SUMMARY_PATH = Path(
    "research/experiments/2026/artifacts/phase1_29_planner_accuracy_probe/summary.json"
)
DEFAULT_MANIFEST_PATH = Path("research/benchmark_manifests/videomme_dev_v1_short_only.toml")
DEFAULT_MODEL_PATH = Path.home() / "models" / "Qwen2.5-VL-7B-Instruct-4bit"
DEFAULT_THRESHOLDS = BlockThresholds(static_threshold=3.0, shifted_threshold=8.0)
DEFAULT_PLANNER = PlannerConfig(
    statistic=BlockStatistic.MEAN,
    static_threshold=DEFAULT_THRESHOLDS.static_threshold,
    shifted_threshold=DEFAULT_THRESHOLDS.shifted_threshold,
)
BENCHMARK_FRAME_SIZE = 560
QWEN_BLOCK_SIZE = 28
QWEN_SPATIAL_MERGE = 2
PRECOMPUTE_CACHE_VERSION = 2
SCORE_PAIR_REDUCTION = "native_macroblock_mean_over_sparse_pair_span_then_project"
SCORE_PROJECTION_VERSION = 2
ACTIVE_BOX_POLICY = "uniform_decode_active_box_for_current_sampled_frame"
H264_EXTRACTOR_DEFAULTS = {
    "mv_only": False,
    "cbf_thresh": 3.0,
    "b_cbf_thresh": 6.0,
    "static_thresh": 3.0,
    "zero_mv_thresh": 0.5,
    "novel_thresh": 8.0,
}
RESIDUAL_EXTRACTOR_LABEL = "pyav_motion_compensated_reconstructed_y_proxy"
CODEC_SCORE_SOURCE_CHOICES: tuple[str, ...] = tuple(source.value for source in CodecScoreSource)
FUSION_MODE_CHOICES: tuple[FuseMode, ...] = ("weighted", "sum", "max", "geomean")


def _load_runtime_modules() -> None:
    """Import model-runtime modules only after argparse has handled --help."""

    global mx, runner
    if mx is not None and runner is not None:
        return
    import mlx.core as mx_module  # type: ignore[import-not-found]
    import run_benchmark_track_a as runner_module  # type: ignore[import-not-found]

    mx = mx_module
    runner = runner_module


@dataclass(frozen=True, slots=True)
class PrecomputedProbeItem:
    item: runner.BenchmarkItem
    active_boxes: list[tuple[int, int, int, int]]
    pixel_classifications: list[np.ndarray]
    codec_score_pairs: list[np.ndarray]
    target_shares: np.ndarray
    codec_extract_s: float
    total_frames: int


@dataclass(frozen=True, slots=True)
class MixedSelectionResult:
    features: mx.array
    raw_reused_ratios: list[float]
    active_reused_ratios: list[float]
    allowed_masks: list[np.ndarray]
    active_masks: list[np.ndarray]


def _reference_share_vector_from_counts(class_counts: dict[str, Any]) -> np.ndarray:
    counts = np.array(
        [
            int(class_counts["static"]),
            int(class_counts["shifted"]),
            int(class_counts["novel"]),
        ],
        dtype=np.float64,
    )
    total = float(counts.sum())
    if total <= 0:
        raise ValueError("reference class_counts must sum to a positive value")
    return counts / total


def _load_reference_map(path: Path) -> dict[str, dict[str, Any]]:
    payload = json.loads(path.read_text())
    return {str(item["item_id"]): item for item in payload["per_item"]}


def _score_pair_from_video(
    item: runner.BenchmarkItem,
    *,
    frame_count: int,
    active_boxes: list[tuple[int, int, int, int]],
    codec_score_source: CodecScoreSource,
    fusion_mode: FuseMode,
    motion_weight: float,
    residual_weight: float,
    normalize_fusion_inputs: bool,
) -> tuple[list[np.ndarray], int, float]:
    if item.start_seconds is not None or item.end_seconds is not None:
        raise ValueError(
            f"codec score extraction for windowed clips is not implemented for {item.item_id}; "
            "H264MetadataExtractor currently decodes from frame 0 and would misalign the sparse "
            "sampling window"
        )
    if len(active_boxes) != frame_count:
        raise ValueError(
            f"expected {frame_count} active boxes for {item.item_id}, got {len(active_boxes)}"
        )

    total_frames = _count_frames(
        item.video_path,
        start_seconds=item.start_seconds,
        end_seconds=item.end_seconds,
    )
    sampled = sparse_sample_indices(total_frames, frame_count)
    spans = sparse_pair_spans(sampled)

    start_ns = runner.time.perf_counter_ns()
    extractor = H264MetadataExtractor(str(item.video_path), max_frames=sampled[-1] + 1)
    macroblock_score_planes: list[np.ndarray] = []
    for frame_metadata in extractor.iter_frames():
        macroblock_score_planes.append(
            macroblock_score_plane(
                frame_metadata.macroblocks,
                source=codec_score_source,
                mode=fusion_mode,
                motion_weight=motion_weight,
                residual_weight=residual_weight,
                normalize_inputs=normalize_fusion_inputs,
            )
        )
    extract_s = (runner.time.perf_counter_ns() - start_ns) / 1_000_000_000
    if len(macroblock_score_planes) <= sampled[-1]:
        raise ValueError(
            f"H264MetadataExtractor yielded {len(macroblock_score_planes)} frames for "
            f"{item.item_id}, but sparse sampling needs frame {sampled[-1]}"
        )

    codec_scores: list[np.ndarray] = []
    for pair_index, (lo, hi) in enumerate(spans, start=1):
        if pair_index >= len(active_boxes):
            raise ValueError(f"missing active box for pair {pair_index} on {item.item_id}")
        stacked = np.stack(macroblock_score_planes[lo : hi + 1], axis=0)
        macroblock_pair_mean = np.asarray(stacked.mean(axis=0), dtype=np.float32)
        codec_scores.append(
            project_macroblock_scores_to_token_grid(
                macroblock_pair_mean,
                macroblock_size=extractor.mb_size,
                frame_width=extractor.width,
                frame_height=extractor.height,
                canvas_size=BENCHMARK_FRAME_SIZE,
                active_box=active_boxes[pair_index],
                token_block=QWEN_BLOCK_SIZE,
            )
        )
    return codec_scores, total_frames, float(extract_s)


def _compute_pixel_classifications(
    frames: list[Any],
    *,
    planner_config: PlannerConfig,
) -> list[np.ndarray]:
    classifications: list[np.ndarray] = []
    for previous, current in zip(frames[:-1], frames[1:], strict=True):
        classifications.append(
            classify_blocks_with_planner(
                np.asarray(previous, dtype=np.uint8),
                np.asarray(current, dtype=np.uint8),
                block_size=QWEN_BLOCK_SIZE,
                config=planner_config,
            )
        )
    return classifications


def _planner_cache_payload(planner_config: PlannerConfig) -> dict[str, Any]:
    return {
        "statistic": planner_config.statistic.value,
        "static_threshold": planner_config.static_threshold,
        "shifted_threshold": planner_config.shifted_threshold,
        "pixel_change_threshold": planner_config.pixel_change_threshold,
        "top_k": planner_config.top_k,
    }


def _precompute_cache_metadata(
    *,
    manifest_path: Path,
    items: list[Any],
    frame_count: int,
    planner_config: PlannerConfig,
    calibration_source: str,
    reference_summary: Path | None,
    codec_score_source: CodecScoreSource,
    fusion_mode: FuseMode,
    motion_weight: float,
    residual_weight: float,
    normalize_fusion_inputs: bool,
) -> dict[str, Any]:
    return {
        "schema": "phase1_29_planner_precompute",
        "version": PRECOMPUTE_CACHE_VERSION,
        "manifest_path": str(manifest_path),
        "item_ids": [item.item_id for item in items],
        "item_windows": [
            {
                "item_id": item.item_id,
                "video_path": str(item.video_path),
                "start_seconds": item.start_seconds,
                "end_seconds": item.end_seconds,
            }
            for item in items
        ],
        "frame_count": frame_count,
        "calibration_source": calibration_source,
        "reference_summary": str(reference_summary) if reference_summary is not None else None,
        "codec_score_source": codec_score_source.value,
        "codec_score_units": _codec_score_units_for_run(
            codec_score_source=codec_score_source,
            fusion_mode=fusion_mode,
            motion_weight=motion_weight,
            residual_weight=residual_weight,
            normalize_fusion_inputs=normalize_fusion_inputs,
        ),
        "score_pair_reduction": SCORE_PAIR_REDUCTION,
        "score_projection_version": SCORE_PROJECTION_VERSION,
        "active_box_policy": ACTIVE_BOX_POLICY,
        "fusion_mode": fusion_mode,
        "motion_weight": motion_weight,
        "residual_weight": residual_weight,
        "normalize_fusion_inputs": normalize_fusion_inputs,
        "residual_extractor": RESIDUAL_EXTRACTOR_LABEL,
        "h264_extractor": H264_EXTRACTOR_DEFAULTS,
        "planner_config": _planner_cache_payload(planner_config),
        "benchmark_frame_size": BENCHMARK_FRAME_SIZE,
        "qwen_block_size": QWEN_BLOCK_SIZE,
    }


def _precomputed_item_to_cache_payload(item: PrecomputedProbeItem) -> dict[str, Any]:
    return {
        "item_id": item.item.item_id,
        "active_boxes": [list(box) for box in item.active_boxes],
        "pixel_classifications": [
            encode_array(np.asarray(classification, dtype=np.int32))
            for classification in item.pixel_classifications
        ],
        "codec_score_pairs": [
            encode_array(np.asarray(score_pair, dtype=np.float32))
            for score_pair in item.codec_score_pairs
        ],
        "target_shares": encode_array(np.asarray(item.target_shares, dtype=np.float64)),
        "codec_extract_s": float(item.codec_extract_s),
        "total_frames": int(item.total_frames),
    }


def _precomputed_item_from_cache_payload(
    payload: dict[str, Any],
    *,
    item_by_id: dict[str, runner.BenchmarkItem],
) -> PrecomputedProbeItem:
    item_id = str(payload["item_id"])
    if item_id not in item_by_id:
        raise KeyError(f"precompute cache contains unexpected item_id {item_id!r}")
    active_boxes: list[tuple[int, int, int, int]] = []
    for box in payload["active_boxes"]:
        if len(box) != 4:
            raise ValueError(f"active box for {item_id!r} must have four coordinates")
        active_boxes.append(cast(tuple[int, int, int, int], tuple(int(value) for value in box)))
    return PrecomputedProbeItem(
        item=item_by_id[item_id],
        active_boxes=active_boxes,
        pixel_classifications=[
            np.asarray(decode_array(classification), dtype=np.int32)
            for classification in payload["pixel_classifications"]
        ],
        codec_score_pairs=[
            np.asarray(decode_array(score_pair), dtype=np.float32)
            for score_pair in payload["codec_score_pairs"]
        ],
        target_shares=np.asarray(decode_array(payload["target_shares"]), dtype=np.float64),
        codec_extract_s=float(payload["codec_extract_s"]),
        total_frames=int(payload["total_frames"]),
    )


def _load_precompute_cache(
    path: Path,
    *,
    expected_metadata: dict[str, Any],
    item_by_id: dict[str, runner.BenchmarkItem],
) -> dict[str, PrecomputedProbeItem]:
    payload = read_json_cache(path)
    if int(payload.get("version", -1)) != PRECOMPUTE_CACHE_VERSION:
        raise ValueError(
            f"precompute cache {path} has version {payload.get('version')!r}, "
            f"expected {PRECOMPUTE_CACHE_VERSION}"
        )
    if payload.get("metadata") != expected_metadata:
        raise ValueError(
            f"precompute cache {path} metadata does not match this run; "
            "rerun with --refresh-precompute-cache to rebuild it"
        )

    cached: dict[str, PrecomputedProbeItem] = {}
    for entry in payload.get("items", []):
        item = _precomputed_item_from_cache_payload(entry, item_by_id=item_by_id)
        if item.item.item_id in cached:
            raise ValueError(f"duplicate item_id {item.item.item_id!r} in precompute cache")
        cached[item.item.item_id] = item
    return cached


def _write_precompute_cache(
    path: Path,
    *,
    metadata: dict[str, Any],
    cached_items: dict[str, PrecomputedProbeItem],
) -> None:
    item_ids = list(metadata["item_ids"])
    payload = {
        "version": PRECOMPUTE_CACHE_VERSION,
        "metadata": metadata,
        "items": [
            _precomputed_item_to_cache_payload(cached_items[item_id])
            for item_id in item_ids
            if item_id in cached_items
        ],
    }
    write_json_cache_atomic(path, payload)


def _precompute_items(
    *,
    items: list[runner.BenchmarkItem],
    manifest_path: Path,
    frame_count: int,
    planner_config: PlannerConfig,
    calibration_source: str,
    reference_summary: Path | None,
    reference_map: dict[str, dict[str, Any]] | None,
    precompute_cache_path: Path | None,
    refresh_precompute_cache: bool,
    codec_score_source: CodecScoreSource,
    fusion_mode: FuseMode,
    motion_weight: float,
    residual_weight: float,
    normalize_fusion_inputs: bool,
) -> list[PrecomputedProbeItem]:
    _validate_no_windowed_items(items)
    item_by_id = {item.item_id: item for item in items}
    if len(item_by_id) != len(items):
        raise ValueError("duplicate item_id in manifest items")

    cache_metadata = _precompute_cache_metadata(
        manifest_path=manifest_path,
        items=items,
        frame_count=frame_count,
        planner_config=planner_config,
        calibration_source=calibration_source,
        reference_summary=None if calibration_source == "live-pixel" else reference_summary,
        codec_score_source=codec_score_source,
        fusion_mode=fusion_mode,
        motion_weight=motion_weight,
        residual_weight=residual_weight,
        normalize_fusion_inputs=normalize_fusion_inputs,
    )
    cached_items: dict[str, PrecomputedProbeItem] = {}
    if precompute_cache_path is not None and precompute_cache_path.exists():
        if refresh_precompute_cache:
            print(
                f"[precompute] rebuilding cache {precompute_cache_path}",
                file=sys.stderr,
                flush=True,
            )
        else:
            cached_items = _load_precompute_cache(
                precompute_cache_path,
                expected_metadata=cache_metadata,
                item_by_id=item_by_id,
            )
            print(
                f"[precompute] loaded {len(cached_items)}/{len(items)} cached items "
                f"from {precompute_cache_path}",
                file=sys.stderr,
                flush=True,
            )

    payload: list[PrecomputedProbeItem] = []
    for item_index, item in enumerate(items, start=1):
        if item.item_id in cached_items:
            print(
                f"[precompute] {item_index}/{len(items)} {item.item_id} cache-hit",
                file=sys.stderr,
                flush=True,
            )
            payload.append(cached_items[item.item_id])
            continue

        print(
            f"[precompute] {item_index}/{len(items)} {item.item_id} computing",
            file=sys.stderr,
            flush=True,
        )
        frames, active_boxes = runner._decode_uniform_frames(
            item.video_path,
            frame_count=frame_count,
            start_seconds=item.start_seconds,
            end_seconds=item.end_seconds,
        )
        pixel_classifications = _compute_pixel_classifications(
            frames, planner_config=planner_config
        )
        codec_score_pairs, total_frames, codec_extract_s = _score_pair_from_video(
            item,
            frame_count=frame_count,
            active_boxes=active_boxes,
            codec_score_source=codec_score_source,
            fusion_mode=fusion_mode,
            motion_weight=motion_weight,
            residual_weight=residual_weight,
            normalize_fusion_inputs=normalize_fusion_inputs,
        )
        if len(codec_score_pairs) != len(pixel_classifications):
            raise ValueError(
                f"pair-count mismatch on {item.item_id}: "
                f"codec={len(codec_score_pairs)} pixel={len(pixel_classifications)}"
            )
        if calibration_source == "live-pixel":
            target_shares = class_share_vector(pixel_classifications)
        else:
            if reference_map is None or item.item_id not in reference_map:
                raise KeyError(f"missing reference item for {item.item_id}")
            target_shares = _reference_share_vector_from_counts(
                reference_map[item.item_id]["class_counts"]
            )
        precomputed = PrecomputedProbeItem(
            item=item,
            active_boxes=active_boxes,
            pixel_classifications=pixel_classifications,
            codec_score_pairs=codec_score_pairs,
            target_shares=target_shares,
            codec_extract_s=codec_extract_s,
            total_frames=total_frames,
        )
        payload.append(precomputed)
        cached_items[item.item_id] = precomputed
        if precompute_cache_path is not None:
            _write_precompute_cache(
                precompute_cache_path,
                metadata=cache_metadata,
                cached_items=cached_items,
            )
            print(
                f"[precompute] cached {len(cached_items)}/{len(items)} items "
                f"to {precompute_cache_path}",
                file=sys.stderr,
                flush=True,
            )
    return payload


def _thresholds_by_item(
    items: list[PrecomputedProbeItem],
    *,
    calibration_mode: str,
) -> dict[str, ScoreThresholds]:
    if calibration_mode == "pooled":
        pooled_scores = np.concatenate(
            [score.reshape(-1) for item in items for score in item.codec_score_pairs]
        ).astype(np.float32)
        target = np.mean([item.target_shares for item in items], axis=0)
        thresholds = calibrate_score_thresholds(
            pooled_scores,
            static_share=float(target[0]),
            shifted_share=float(target[1]),
        )
        return {item.item.item_id: thresholds for item in items}
    return {
        item.item.item_id: calibrate_score_thresholds(
            np.concatenate([score.reshape(-1) for score in item.codec_score_pairs]).astype(
                np.float32
            ),
            static_share=float(item.target_shares[0]),
            shifted_share=float(item.target_shares[1]),
        )
        for item in items
    }


def _mix_features_from_classifications(
    sample: runner.PreparedSample,
    features: mx.array,
    *,
    classifications: list[np.ndarray],
    reuse_classes: tuple[Any, ...],
    max_age: int | None,
) -> MixedSelectionResult:
    image_grid_thw = np.array(sample.extra_kwargs["image_grid_thw"].tolist(), dtype=np.int64)
    counts = qwen_merged_token_counts(image_grid_thw, spatial_merge_size=QWEN_SPATIAL_MERGE)
    if len(counts) != len(sample.frames):
        raise ValueError("frame count and Qwen grid count mismatch")
    if len(classifications) != len(sample.frames) - 1:
        raise ValueError("expected one classification grid per adjacent frame pair")

    dense_segments: list[mx.array] = []
    offset = 0
    for count in counts:
        dense_segments.append(features[offset : offset + count])
        offset += count

    mixed_segments = [dense_segments[0]]
    ages = np.zeros(dense_segments[0].shape[0], dtype=np.int32)
    raw_reused_ratios: list[float] = []
    active_reused_ratios: list[float] = []
    allowed_masks: list[np.ndarray] = []
    active_masks: list[np.ndarray] = []

    for frame_index, classification in enumerate(classifications, start=1):
        reuse_mask = flattened_reuse_mask(classification, reuse_classes=reuse_classes)
        if reuse_mask.size != dense_segments[frame_index].shape[0]:
            raise ValueError(
                "classification/token mismatch: "
                f"mask={reuse_mask.size}, tokens={dense_segments[frame_index].shape[0]}"
            )
        allowed_mask, ages = runner._apply_age_gate(reuse_mask, ages, max_age=max_age)
        previous_active = active_region_block_mask(
            sample.frames[frame_index - 1].size,
            sample.active_boxes[frame_index - 1],
            block_size=QWEN_BLOCK_SIZE,
        )
        current_active = active_region_block_mask(
            sample.frames[frame_index].size,
            sample.active_boxes[frame_index],
            block_size=QWEN_BLOCK_SIZE,
        )
        active_mask = previous_active & current_active
        if active_mask.size != reuse_mask.size:
            raise ValueError(
                f"active-region/token mismatch: mask={active_mask.size}, tokens={reuse_mask.size}"
            )
        mixed_segments.append(
            mx.where(
                mx.array(allowed_mask[:, None]),
                mixed_segments[-1],
                dense_segments[frame_index],
            )
        )
        raw_reused_ratios.append(float(allowed_mask.mean()))
        active_reused_ratios.append(
            runner._masked_mean(allowed_mask.astype(np.float32), active_mask)
        )
        allowed_masks.append(allowed_mask.copy())
        active_masks.append(active_mask.copy())

    mixed = mx.concatenate(mixed_segments, axis=0)
    mx.eval(mixed)
    return MixedSelectionResult(
        features=mixed,
        raw_reused_ratios=raw_reused_ratios,
        active_reused_ratios=active_reused_ratios,
        allowed_masks=allowed_masks,
        active_masks=active_masks,
    )


def _mean_or_none(values: list[float]) -> float | None:
    return float(np.mean(values)) if values else None


def _masked_jaccard(mask_a: np.ndarray, mask_b: np.ndarray, active_mask: np.ndarray) -> float:
    if mask_a.shape != mask_b.shape or mask_a.shape != active_mask.shape:
        raise ValueError("all masks must have the same shape")
    a = mask_a & active_mask
    b = mask_b & active_mask
    union = np.logical_or(a, b)
    if not union.any():
        return 1.0
    return float(np.logical_and(a, b).sum() / union.sum())


def _write_results(output_path: Path, rows: list[dict[str, Any]]) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def _write_summary(
    summary_path: Path,
    *,
    rows: list[dict[str, Any]],
    environment: dict[str, Any],
    manifest_path: Path,
    frame_count: int,
    calibration_mode: str,
    calibration_source: str,
    codec_score_source: CodecScoreSource,
    fusion_mode: FuseMode,
    motion_weight: float,
    residual_weight: float,
    normalize_fusion_inputs: bool,
    precompute_cache_path: Path | None,
    planner_config: PlannerConfig,
    reuse_classes: tuple[Any, ...],
    max_age: int | None,
) -> None:
    dense_correct = sum(bool(row["dense"]["correct"]) for row in rows)
    pixel_correct = sum(bool(row["pixel_cached"]["correct"]) for row in rows)
    codec_correct = sum(bool(row["codec_cached"]["correct"]) for row in rows)
    summary = {
        "phase": "1.29",
        "environment": environment,
        "manifest_path": str(manifest_path),
        "frame_count": frame_count,
        "calibration_mode": calibration_mode,
        "calibration_source": calibration_source,
        "codec_score_source": codec_score_source.value,
        "codec_score_units": _codec_score_units_for_run(
            codec_score_source=codec_score_source,
            fusion_mode=fusion_mode,
            motion_weight=motion_weight,
            residual_weight=residual_weight,
            normalize_fusion_inputs=normalize_fusion_inputs,
        ),
        "score_pair_reduction": SCORE_PAIR_REDUCTION,
        "score_projection_version": SCORE_PROJECTION_VERSION,
        "active_box_policy": ACTIVE_BOX_POLICY,
        "h264_extractor": H264_EXTRACTOR_DEFAULTS,
        "fusion": {
            "mode": fusion_mode,
            "motion_weight": motion_weight,
            "residual_weight": residual_weight,
            "normalize_inputs": normalize_fusion_inputs,
            "residual_extractor": RESIDUAL_EXTRACTOR_LABEL,
        },
        "precompute_cache_path": str(precompute_cache_path) if precompute_cache_path else None,
        "planner": runner._planner_payload(
            planner_config,
            reuse_classes=reuse_classes,
            max_age=max_age,
        ),
        "n_items": len(rows),
        "dense_accuracy": dense_correct / len(rows) if rows else 0.0,
        "pixel_accuracy": pixel_correct / len(rows) if rows else 0.0,
        "codec_accuracy": codec_correct / len(rows) if rows else 0.0,
        "codec_minus_pixel_accuracy": (
            (codec_correct - pixel_correct) / len(rows) if rows else 0.0
        ),
        "pixel_dense_agreement": (
            sum(bool(row["pixel_matches_dense"]) for row in rows) / len(rows) if rows else 0.0
        ),
        "codec_dense_agreement": (
            sum(bool(row["codec_matches_dense"]) for row in rows) / len(rows) if rows else 0.0
        ),
        "codec_pixel_agreement": (
            sum(bool(row["codec_matches_pixel"]) for row in rows) / len(rows) if rows else 0.0
        ),
        "pixel_reuse_ratio_mean_active": _mean_or_none(
            [
                float(row["pixel_reuse_ratio_mean_active"])
                for row in rows
                if row["pixel_reuse_ratio_mean_active"] is not None
            ]
        ),
        "codec_reuse_ratio_mean_active": _mean_or_none(
            [
                float(row["codec_reuse_ratio_mean_active"])
                for row in rows
                if row["codec_reuse_ratio_mean_active"] is not None
            ]
        ),
        "pair_selection_jaccard_mean": _mean_or_none(
            [
                float(row["pair_selection_jaccard_mean"])
                for row in rows
                if row["pair_selection_jaccard_mean"] is not None
            ]
        ),
        "items": [
            {
                "item_id": row["item_id"],
                "group": row["group"],
                "dense_correct": row["dense"]["correct"],
                "pixel_correct": row["pixel_cached"]["correct"],
                "codec_correct": row["codec_cached"]["correct"],
                "pixel_choice_index": row["pixel_cached"]["choice_index"],
                "codec_choice_index": row["codec_cached"]["choice_index"],
                "codec_thresholds": row["codec_thresholds"],
                "pair_selection_jaccard_mean": row["pair_selection_jaccard_mean"],
                "codec_extract_s": row["codec_extract_s"],
                "codec_score_source": row["codec_score_source"],
                "codec_score_units": row["codec_score_units"],
                "score_pair_reduction": row["score_pair_reduction"],
            }
            for row in rows
        ],
    }
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")


def _validate_codec_score_args(
    *,
    codec_score_source: CodecScoreSource,
    motion_weight: float,
    residual_weight: float,
) -> None:
    if not np.isfinite(motion_weight):
        raise ValueError("--motion-weight must be finite")
    if not np.isfinite(residual_weight):
        raise ValueError("--residual-weight must be finite")
    if motion_weight < 0.0:
        raise ValueError("--motion-weight must be non-negative")
    if residual_weight < 0.0:
        raise ValueError("--residual-weight must be non-negative")
    if (
        codec_score_source is CodecScoreSource.FUSED
        and motion_weight == 0.0
        and residual_weight == 0.0
    ):
        raise ValueError("--codec-score-source=fused requires at least one positive fusion weight")


def _codec_score_units_for_run(
    *,
    codec_score_source: CodecScoreSource,
    fusion_mode: FuseMode,
    motion_weight: float,
    residual_weight: float,
    normalize_fusion_inputs: bool,
) -> str:
    return codec_score_units(
        codec_score_source,
        fusion_mode=fusion_mode,
        motion_weight=motion_weight,
        residual_weight=residual_weight,
        normalize_inputs=normalize_fusion_inputs,
    )


def _validate_no_windowed_items(items: list[Any]) -> None:
    windowed = [
        item.item_id
        for item in items
        if item.start_seconds is not None or item.end_seconds is not None
    ]
    if windowed:
        raise ValueError(
            "codec score extraction for windowed clips is not implemented; "
            "clear start_seconds/end_seconds or add extractor windowing before running "
            f"these items: {windowed}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST_PATH)
    parser.add_argument("--model-path", type=Path, default=DEFAULT_MODEL_PATH)
    parser.add_argument("--frame-count", type=int, default=8)
    parser.add_argument("--max-tokens", type=int, default=32)
    parser.add_argument(
        "--calibration-mode",
        choices=("pooled", "per-item"),
        default="per-item",
    )
    parser.add_argument(
        "--calibration-source",
        choices=("live-pixel", "artifact"),
        default="live-pixel",
    )
    parser.add_argument(
        "--codec-score-source",
        choices=CODEC_SCORE_SOURCE_CHOICES,
        default="novel_coded",
        help=(
            "Continuous codec score source. 'novel_coded' preserves the Phase 1.29 "
            "intra|cbf default; 'fused' uses repo-local motion/residual fusion."
        ),
    )
    parser.add_argument(
        "--fusion-mode",
        choices=FUSION_MODE_CHOICES,
        default="weighted",
        help="Fusion mode used only when --codec-score-source=fused.",
    )
    parser.add_argument(
        "--motion-weight",
        type=float,
        default=1.0,
        help="Motion weight used only when --codec-score-source=fused.",
    )
    parser.add_argument(
        "--residual-weight",
        type=float,
        default=1.0,
        help="Residual weight used only when --codec-score-source=fused.",
    )
    parser.add_argument(
        "--no-normalize-fusion-inputs",
        action="store_true",
        help="Disable percentile normalization before motion/residual fusion.",
    )
    parser.add_argument(
        "--reference-summary",
        type=Path,
        default=Path("research/experiments/2026/artifacts/phase1_57/qwen_8f_dev30.json"),
    )
    parser.add_argument(
        "--statistic",
        choices=[statistic.value for statistic in BlockStatistic],
        default=DEFAULT_PLANNER.statistic.value,
    )
    parser.add_argument("--static-threshold", type=float, default=DEFAULT_PLANNER.static_threshold)
    parser.add_argument(
        "--shifted-threshold", type=float, default=DEFAULT_PLANNER.shifted_threshold
    )
    parser.add_argument(
        "--pixel-change-threshold",
        type=float,
        default=DEFAULT_PLANNER.pixel_change_threshold,
    )
    parser.add_argument("--top-k", type=int, default=DEFAULT_PLANNER.top_k)
    parser.add_argument("--reuse-classes", default="static,shifted")
    parser.add_argument("--max-age", type=int, default=None)
    parser.add_argument("--output-path", type=Path, default=DEFAULT_OUTPUT_PATH)
    parser.add_argument("--summary-path", type=Path, default=DEFAULT_SUMMARY_PATH)
    parser.add_argument("--feature-cache-dir", type=Path, default=DEFAULT_FEATURE_CACHE_DIR)
    parser.add_argument(
        "--precompute-cache-path",
        type=Path,
        default=None,
        help="Optional JSON cache for decoded pixel classes and codec score grids.",
    )
    parser.add_argument(
        "--refresh-precompute-cache",
        action="store_true",
        help="Rebuild --precompute-cache-path instead of loading existing cached items.",
    )
    parser.add_argument("--no-feature-replay", action="store_true")
    parser.add_argument("--allow-dirty", action="store_true")
    args = parser.parse_args()

    codec_score_source = CodecScoreSource(args.codec_score_source)
    fusion_mode = cast(FuseMode, args.fusion_mode)
    normalize_fusion_inputs = not bool(args.no_normalize_fusion_inputs)
    _validate_codec_score_args(
        codec_score_source=codec_score_source,
        motion_weight=float(args.motion_weight),
        residual_weight=float(args.residual_weight),
    )

    _load_runtime_modules()
    assert runner is not None
    assert mx is not None

    runner._ensure_clean_git_tree(allow_dirty=bool(args.allow_dirty))
    manifest = runner._load_manifest(args.manifest)
    if manifest.benchmark != "videomme":
        raise ValueError(
            f"Phase 1.29 probe supports VideoMME manifests only, got {manifest.benchmark!r}"
        )
    environment = runner._environment_record(args.model_path)

    planner_config = PlannerConfig(
        statistic=BlockStatistic(args.statistic),
        static_threshold=args.static_threshold,
        shifted_threshold=args.shifted_threshold,
        pixel_change_threshold=args.pixel_change_threshold,
        top_k=args.top_k,
    )
    reuse_classes = runner._parse_reuse_classes(args.reuse_classes)
    max_age = runner._validate_max_age(args.max_age)
    reference_map = (
        _load_reference_map(args.reference_summary)
        if args.calibration_source == "artifact"
        else None
    )

    items = runner._load_items_by_id("videomme", item_ids=manifest.item_ids)
    precomputed = _precompute_items(
        items=items,
        manifest_path=args.manifest,
        frame_count=args.frame_count,
        planner_config=planner_config,
        calibration_source=args.calibration_source,
        reference_summary=args.reference_summary,
        reference_map=reference_map,
        precompute_cache_path=args.precompute_cache_path,
        refresh_precompute_cache=bool(args.refresh_precompute_cache),
        codec_score_source=codec_score_source,
        fusion_mode=fusion_mode,
        motion_weight=float(args.motion_weight),
        residual_weight=float(args.residual_weight),
        normalize_fusion_inputs=normalize_fusion_inputs,
    )
    thresholds_by_item = _thresholds_by_item(precomputed, calibration_mode=args.calibration_mode)

    model, processor = runner._load_model(args.model_path)
    model_content_hash = runner.model_content_sha256(args.model_path)

    rows: list[dict[str, Any]] = []
    for prepared in precomputed:
        sample = runner._prepare_sample(
            model, processor, prepared.item, frame_count=args.frame_count
        )
        if sample.active_boxes != prepared.active_boxes:
            raise ValueError(f"active-box mismatch on {prepared.item.item_id}")
        features, feature_cache_hit = runner._compute_cached_features_with_replay(
            model,
            sample,
            model_path=args.model_path,
            model_content_hash=model_content_hash,
            use_feature_replay=not bool(args.no_feature_replay),
            feature_cache_dir=args.feature_cache_dir,
        )

        codec_thresholds = thresholds_by_item[prepared.item.item_id]
        codec_classifications = [
            classify_score_grid(score_pair, thresholds=codec_thresholds)
            for score_pair in prepared.codec_score_pairs
        ]

        pixel_selection = _mix_features_from_classifications(
            sample,
            features,
            classifications=prepared.pixel_classifications,
            reuse_classes=reuse_classes,
            max_age=max_age,
        )
        codec_selection = _mix_features_from_classifications(
            sample,
            features,
            classifications=codec_classifications,
            reuse_classes=reuse_classes,
            max_age=max_age,
        )

        dense = runner._generate_response(
            model,
            processor,
            sample,
            cached_features=None,
            max_tokens=args.max_tokens,
        )
        pixel_cached = runner._generate_response(
            model,
            processor,
            sample,
            cached_features=pixel_selection.features,
            max_tokens=args.max_tokens,
        )
        codec_cached = runner._generate_response(
            model,
            processor,
            sample,
            cached_features=codec_selection.features,
            max_tokens=args.max_tokens,
        )

        dense_choice = runner.extract_choice(str(dense["text"]), prepared.item.candidates)
        pixel_choice = runner.extract_choice(str(pixel_cached["text"]), prepared.item.candidates)
        codec_choice = runner.extract_choice(str(codec_cached["text"]), prepared.item.candidates)
        jaccards = [
            _masked_jaccard(pixel_mask, codec_mask, active_mask)
            for pixel_mask, codec_mask, active_mask in zip(
                pixel_selection.allowed_masks,
                codec_selection.allowed_masks,
                pixel_selection.active_masks,
                strict=True,
            )
        ]

        rows.append(
            {
                "item_id": prepared.item.item_id,
                "benchmark": prepared.item.benchmark,
                "group": prepared.item.group,
                "video_path": str(prepared.item.video_path),
                "feature_cache_hit": feature_cache_hit,
                "frame_count": args.frame_count,
                "total_frames": prepared.total_frames,
                "codec_extract_s": prepared.codec_extract_s,
                "codec_score_source": codec_score_source.value,
                "codec_score_units": _codec_score_units_for_run(
                    codec_score_source=codec_score_source,
                    fusion_mode=fusion_mode,
                    motion_weight=float(args.motion_weight),
                    residual_weight=float(args.residual_weight),
                    normalize_fusion_inputs=normalize_fusion_inputs,
                ),
                "score_pair_reduction": SCORE_PAIR_REDUCTION,
                "score_projection_version": SCORE_PROJECTION_VERSION,
                "active_box_policy": ACTIVE_BOX_POLICY,
                "target_shares": {
                    "static": float(prepared.target_shares[0]),
                    "shifted": float(prepared.target_shares[1]),
                    "novel": float(prepared.target_shares[2]),
                },
                "fusion": {
                    "mode": fusion_mode,
                    "motion_weight": float(args.motion_weight),
                    "residual_weight": float(args.residual_weight),
                    "normalize_inputs": normalize_fusion_inputs,
                    "residual_extractor": RESIDUAL_EXTRACTOR_LABEL,
                },
                "codec_thresholds": {
                    "static": codec_thresholds.static_threshold,
                    "shifted": codec_thresholds.shifted_threshold,
                },
                "dense": {
                    **dense,
                    "choice_index": dense_choice,
                    "correct": dense_choice == prepared.item.answer_index
                    if dense_choice is not None
                    else False,
                    "parse_failure": dense_choice is None,
                },
                "pixel_cached": {
                    **pixel_cached,
                    "choice_index": pixel_choice,
                    "correct": pixel_choice == prepared.item.answer_index
                    if pixel_choice is not None
                    else False,
                    "parse_failure": pixel_choice is None,
                },
                "codec_cached": {
                    **codec_cached,
                    "choice_index": codec_choice,
                    "correct": codec_choice == prepared.item.answer_index
                    if codec_choice is not None
                    else False,
                    "parse_failure": codec_choice is None,
                },
                "pixel_matches_dense": (
                    pixel_choice == dense_choice
                    if pixel_choice is not None and dense_choice is not None
                    else False
                ),
                "codec_matches_dense": (
                    codec_choice == dense_choice
                    if codec_choice is not None and dense_choice is not None
                    else False
                ),
                "codec_matches_pixel": (
                    codec_choice == pixel_choice
                    if codec_choice is not None and pixel_choice is not None
                    else False
                ),
                "pixel_reuse_ratio_mean_active": _mean_or_none(
                    pixel_selection.active_reused_ratios
                ),
                "codec_reuse_ratio_mean_active": _mean_or_none(
                    codec_selection.active_reused_ratios
                ),
                "pixel_reuse_ratio_mean_raw": _mean_or_none(pixel_selection.raw_reused_ratios),
                "codec_reuse_ratio_mean_raw": _mean_or_none(codec_selection.raw_reused_ratios),
                "pair_selection_jaccard_mean": _mean_or_none(jaccards),
                "pair_selection_jaccards": jaccards,
            }
        )

        del features
        gc.collect()
        mx.clear_cache()

    _write_results(args.output_path, rows)
    _write_summary(
        args.summary_path,
        rows=rows,
        environment=environment,
        manifest_path=args.manifest,
        frame_count=args.frame_count,
        calibration_mode=args.calibration_mode,
        calibration_source=args.calibration_source,
        codec_score_source=codec_score_source,
        fusion_mode=fusion_mode,
        motion_weight=float(args.motion_weight),
        residual_weight=float(args.residual_weight),
        normalize_fusion_inputs=normalize_fusion_inputs,
        precompute_cache_path=args.precompute_cache_path,
        planner_config=planner_config,
        reuse_classes=reuse_classes,
        max_age=max_age,
    )
    print(f"Wrote {args.output_path}")
    print(f"Wrote {args.summary_path}")


if __name__ == "__main__":
    main()
