#!/usr/bin/env python3
"""Phase 1.51V Qwen cross-architecture driver.

Runs one Qwen arm at a time:

- unpatched reference: dense Qwen vision tower
- V-patched arm: Qwen vision tower pruned after layer L at keep-rate kr_V

The driver measures decode, processor, vision-tower wall-clock, generate
wall-clock, end-to-end wall-clock, and answer accuracy. It intentionally
mirrors the summary fields already used by the Gemma-side 1.51V analyses so
the same paper tables and comparison scripts can consume the output.
"""

from __future__ import annotations

import argparse
import gc
import importlib.util
import json
import sys
import time
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import mlx.core as mx
import numpy as np
from mlx_vlm import generate, load

# Avoid IOGPU state-inconsistency panics under allocation churn
# (CVE-2026-28834-class GPU-driver race, unpatched on macOS 26.3).
mx.set_memory_limit(12 * 1024**3)
from mlx_vlm.utils import prepare_inputs  # noqa: E402

from codec_through.answers import extract_choice  # noqa: E402
from codec_through.codec.continuous_score import (  # noqa: E402
    CodecScoreSource,
    project_macroblock_metadata_to_token_grid,
    sparse_sample_indices,
)
from codec_through.codec.h264_metadata import H264MetadataExtractor  # noqa: E402
from codec_through.codec.onevision_patchification import FuseMode  # noqa: E402
from codec_through.memory_guard import check_rss_guard, rss_mb  # noqa: E402
from codec_through.qwen_pruned_vision_tower import (  # noqa: E402
    QwenVisionPruneConfig,
    patch_qwen_vision_tower,
)
from codec_through.qwen_vision_pruning import (  # noqa: E402
    pool_token_grid_to_merged_groups,
    qwen_groups_per_frame,
)
from codec_through.video_decode import _count_frames  # noqa: E402

QWEN_BENCHMARK_FRAME_SIZE = 560
# Each token block at this size already corresponds to one Qwen merged-group:
# (spatial_merge_size=2 * patch_size=14)^2 = 28*28 pixels, so the 20x20 token
# grid is at merged-group resolution and we flatten with spatial_merge_size=1
# instead of pooling again.
QWEN_BLOCK_SIZE = 28
QWEN_GROUP_FLATTEN_STRIDE = 1
CODEC_SCORE_SOURCE_CHOICES: tuple[str, ...] = tuple(source.value for source in CodecScoreSource)
FUSION_MODE_CHOICES: tuple[FuseMode, ...] = ("weighted", "sum", "max", "geomean")

REPO_ROOT = Path(__file__).resolve().parents[1]
RUNNER_PATH = REPO_ROOT / "scripts" / "run_benchmark_track_a.py"
DEFAULT_MODEL_PATH = Path.home() / "models" / "Qwen2.5-VL-7B-Instruct-4bit"


@dataclass(frozen=True, slots=True)
class StageTimings:
    decode_ms: float
    processor_ms: float
    vision_ms: float
    generate_ms: float
    end_to_end_ms: float


@dataclass(frozen=True, slots=True)
class ItemResult:
    item_id: str
    benchmark: str
    group: str
    correct: bool
    parse_failure: bool
    choice_index: int | None
    answer_index: int
    text: str
    timings: StageTimings
    prompt_tokens: int
    generation_tokens: int
    prompt_tps: float
    generation_tps: float
    kept_groups: int
    total_groups: int
    kept_groups_per_frame: list[int]
    peak_memory_gb: float


def _load_runner_module() -> Any:
    name = "_phase1_51v_qwen_runner"
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


def _build_prompt(processor: Any, frames: list[Any], question: str) -> dict[str, Any]:
    messages = [
        {
            "role": "user",
            "content": [*({"type": "image"} for _ in frames), {"type": "text", "text": question}],
        }
    ]
    rendered = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    return cast(dict[str, Any], prepare_inputs(processor, images=frames, prompts=rendered))


def _per_frame_codec_token_grids(
    item: Any,
    *,
    frame_count: int,
    active_boxes: list[tuple[int, int, int, int]],
    codec_score_source: CodecScoreSource,
    fusion_mode: FuseMode,
    motion_weight: float,
    residual_weight: float,
    normalize_fusion_inputs: bool,
) -> tuple[list[np.ndarray], float]:
    """Compute per-sampled-frame token-grid codec scores and the extraction wall-time.

    Uses the same sparse_sample_indices contract as the Phase 1.29 probe so
    Track B codec scoring is consistent with Track A. For each sampled frame
    we read its H264 macroblock metadata and project to the Qwen token grid
    via the existing continuous_score helper. Anchor handling is implicit in
    the score source: novel_coded marks I-frames maximally novel, so frame 0
    typically scores high. We do not force a separate full-frame anchor.

    The active_boxes argument must match the decoder's per-frame square-pad
    geometry so codec scores align with the same canvas regions the model
    sees in pixel space.
    """

    if item.start_seconds is not None or item.end_seconds is not None:
        raise ValueError(
            f"codec score extraction for windowed clips is not implemented for "
            f"{item.item_id}; clear start_seconds/end_seconds before running Track B"
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

    t0 = time.perf_counter_ns()
    extractor = H264MetadataExtractor(str(item.video_path), max_frames=sampled[-1] + 1)
    frame_metadata_by_index: dict[int, Any] = {}
    sampled_set = set(sampled)
    for index, metadata in enumerate(extractor.iter_frames()):
        if index in sampled_set:
            frame_metadata_by_index[index] = metadata
        if index >= sampled[-1]:
            break
    extract_s = (time.perf_counter_ns() - t0) / 1_000_000_000

    if len(frame_metadata_by_index) != frame_count:
        raise ValueError(
            f"H264MetadataExtractor missed sampled frames for {item.item_id}; "
            f"wanted {frame_count}, got {len(frame_metadata_by_index)}"
        )

    token_grids: list[np.ndarray] = []
    for sampled_index, active_box in zip(sampled, active_boxes, strict=True):
        metadata = frame_metadata_by_index[sampled_index]
        token_grid = project_macroblock_metadata_to_token_grid(
            metadata.macroblocks,
            source=codec_score_source,
            macroblock_size=extractor.mb_size,
            frame_width=extractor.width,
            frame_height=extractor.height,
            canvas_size=QWEN_BENCHMARK_FRAME_SIZE,
            active_box=active_box,
            token_block=QWEN_BLOCK_SIZE,
            mode=fusion_mode,
            motion_weight=motion_weight,
            residual_weight=residual_weight,
            normalize_inputs=normalize_fusion_inputs,
        )
        # Codec scores must be non-negative; clamp tiny negatives from bicubic
        # rounding so the strict non-negative gate downstream is not tripped by
        # numerical noise.
        token_grid = np.clip(token_grid, a_min=0.0, a_max=None)
        token_grids.append(np.asarray(token_grid, dtype=np.float32))

    return token_grids, float(extract_s)


def _prepare_item(
    runner: Any,
    processor: Any,
    item: Any,
    *,
    frame_count: int,
) -> tuple[dict[str, Any], float, float, list[tuple[int, int, int, int]]]:
    t0 = time.perf_counter_ns()
    frames, active_boxes = runner._decode_uniform_frames(
        item.video_path,
        frame_count=frame_count,
        start_seconds=item.start_seconds,
        end_seconds=item.end_seconds,
    )
    decode_ms = (time.perf_counter_ns() - t0) / 1_000_000

    t1 = time.perf_counter_ns()
    raw = _build_prompt(processor, frames, item.question)
    processor_ms = (time.perf_counter_ns() - t1) / 1_000_000
    return raw, decode_ms, processor_ms, active_boxes


def _compute_qwen_features(
    model: Any, raw: dict[str, Any]
) -> tuple[mx.array, float, dict[str, Any] | None]:
    image_grid_thw = mx.array(raw["image_grid_thw"])
    pixel_values = mx.array(raw["pixel_values"])
    dtype = model.vision_tower.patch_embed.proj.weight.dtype
    t0 = time.perf_counter_ns()
    features = model.vision_tower(
        pixel_values.astype(dtype),
        image_grid_thw,
        output_hidden_states=False,
    )
    mx.eval(features)
    vision_ms = (time.perf_counter_ns() - t0) / 1_000_000
    prune_info = getattr(model.vision_tower, "last_prune_info", None)
    return cast(mx.array, features), vision_ms, prune_info


@dataclass(frozen=True, slots=True)
class GenerateStats:
    text: str
    elapsed_ms: float
    prompt_tokens: int
    generation_tokens: int
    prompt_tps: float
    generation_tps: float
    peak_memory_gb: float


def _run_generate(
    model: Any,
    processor: Any,
    *,
    raw: dict[str, Any],
    cached_image_features: mx.array,
    max_tokens: int,
) -> GenerateStats:
    input_ids = mx.array(raw["input_ids"])
    pixel_values = mx.array(raw["pixel_values"])
    mask = mx.array(raw["attention_mask"])
    kwargs = {
        key: mx.array(value)
        for key, value in raw.items()
        if key not in {"input_ids", "pixel_values", "attention_mask"}
    }
    kwargs["cached_image_features"] = cached_image_features
    t0 = time.perf_counter_ns()
    mx.random.seed(42)
    response = generate(
        model,
        processor,
        "",
        input_ids=input_ids,
        pixel_values=pixel_values,
        mask=mask,
        max_tokens=max_tokens,
        temperature=0.0,
        **kwargs,
    )
    elapsed_ms = (time.perf_counter_ns() - t0) / 1_000_000
    return GenerateStats(
        text=str(response.text),
        elapsed_ms=elapsed_ms,
        prompt_tokens=int(getattr(response, "prompt_tokens", 0)),
        generation_tokens=int(getattr(response, "generation_tokens", 0)),
        prompt_tps=float(getattr(response, "prompt_tps", 0.0)),
        generation_tps=float(getattr(response, "generation_tps", 0.0)),
        peak_memory_gb=float(getattr(response, "peak_memory", 0.0)),
    )


def _clear_runtime_state() -> None:
    gc.collect()
    mx.clear_cache()


def _load_manifest_items(runner: Any, manifest_path: Path) -> list[Any]:
    payload = tomllib.loads(manifest_path.read_text())
    return cast(list[Any], runner._load_items_by_id(payload["benchmark"], payload["item_ids"]))


def _record_payload(record: ItemResult) -> dict[str, Any]:
    return {
        "item_id": record.item_id,
        "benchmark": record.benchmark,
        "group": record.group,
        "correct": record.correct,
        "parse_failure": record.parse_failure,
        "choice_index": record.choice_index,
        "answer_index": record.answer_index,
        "text": record.text,
        "timing_ms": {
            "decode": record.timings.decode_ms,
            "processor": record.timings.processor_ms,
            "vision": record.timings.vision_ms,
            "generate": record.timings.generate_ms,
            "end_to_end": record.timings.end_to_end_ms,
        },
        "prompt_tokens": record.prompt_tokens,
        "generation_tokens": record.generation_tokens,
        "prompt_tps": record.prompt_tps,
        "generation_tps": record.generation_tps,
        "kept_groups": record.kept_groups,
        "total_groups": record.total_groups,
        "kept_groups_per_frame": record.kept_groups_per_frame,
        "peak_memory_gb": record.peak_memory_gb,
    }


def _summarize(records: list[ItemResult]) -> dict[str, Any]:
    if not records:
        return {"n_items": 0}
    dense_end_to_end = [record.timings.end_to_end_ms for record in records]
    dense_generate = [record.timings.generate_ms for record in records]
    return {
        "n_items": len(records),
        "dense_accuracy": sum(1 for record in records if record.correct) / len(records),
        "dense_parse_failures": sum(1 for record in records if record.parse_failure),
        "mean_decode_ms": float(np.mean([record.timings.decode_ms for record in records])),
        "mean_processor_ms": float(np.mean([record.timings.processor_ms for record in records])),
        "mean_dense_vision_ms": float(np.mean([record.timings.vision_ms for record in records])),
        "mean_dense_generate_ms": float(np.mean(dense_generate)),
        "mean_dense_end_to_end_ms": float(np.mean(dense_end_to_end)),
        "median_dense_generate_ms": float(np.median(dense_generate)),
        "median_dense_end_to_end_ms": float(np.median(dense_end_to_end)),
        "mean_dense_prompt_tokens": float(np.mean([record.prompt_tokens for record in records])),
        "mean_dense_generation_tokens": float(
            np.mean([record.generation_tokens for record in records])
        ),
        "mean_dense_prompt_tps": float(np.mean([record.prompt_tps for record in records])),
        "mean_dense_generation_tps": float(np.mean([record.generation_tps for record in records])),
        "mean_peak_memory_gb": float(np.mean([record.peak_memory_gb for record in records])),
        "mean_kept_groups": float(np.mean([record.kept_groups for record in records])),
        "mean_total_groups": float(np.mean([record.total_groups for record in records])),
        "mean_effective_keep_rate": float(
            np.mean([record.kept_groups / record.total_groups for record in records])
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--n-items", type=int, default=0, help="0 = all manifest items")
    parser.add_argument("--frame-count", type=int, default=8)
    parser.add_argument("--max-tokens", type=int, default=32)
    parser.add_argument("--model-path", type=Path, default=DEFAULT_MODEL_PATH)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--allow-dirty", action="store_true")
    parser.add_argument("--rss-guard-mb", type=int, default=0)
    parser.add_argument("--vision-tower-layer", type=int, default=2)
    parser.add_argument("--vision-tower-keep-rate", type=float, default=1.0)
    parser.add_argument(
        "--score-mode",
        type=str,
        default="magnitude_norm",
        choices=("magnitude_norm", "uniform_random", "codec_grid"),
        help=(
            "How to rank merged-token groups at the prune layer. "
            "'magnitude_norm' is the default 1.51V Qwen scorer "
            "(L2 norm of group-mean hidden state). "
            "'uniform_random' is the 1.51VC competitor-positioning baseline "
            "(deterministic-seeded random scores at matched keep-rate). "
            "'codec_grid' ranks groups by a per-item codec-derived score grid "
            "set via --codec-score-source."
        ),
    )
    parser.add_argument(
        "--score-seed",
        type=int,
        default=42,
        help="Seed for --score-mode uniform_random (ignored otherwise).",
    )
    parser.add_argument(
        "--codec-score-source",
        type=str,
        default=None,
        choices=CODEC_SCORE_SOURCE_CHOICES,
        help=(
            "When --score-mode=codec_grid, which OV-3 codec score source to use. "
            "Choices: novel_coded (intra|cbf), motion, residual, fused."
        ),
    )
    parser.add_argument(
        "--fusion-mode",
        type=str,
        default="weighted",
        choices=FUSION_MODE_CHOICES,
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
    args = parser.parse_args()
    if args.score_mode == "codec_grid" and args.codec_score_source is None:
        parser.error("--score-mode=codec_grid requires --codec-score-source")
    if args.score_mode != "codec_grid" and args.codec_score_source is not None:
        parser.error("--codec-score-source requires --score-mode=codec_grid")

    runner = _load_runner_module()
    runner._ensure_clean_git_tree(allow_dirty=args.allow_dirty)
    items = _load_manifest_items(runner, args.manifest)
    if args.n_items > 0:
        items = items[: args.n_items]
    if not items:
        raise SystemExit("no items loaded from manifest")

    model, processor = cast(tuple[Any, Any], load(str(args.model_path)))
    if getattr(model.config, "model_type", None) != "qwen2_5_vl":
        raise SystemExit(
            f"run_phase1_51V.py currently supports qwen2_5_vl only; got "
            f"{getattr(model.config, 'model_type', None)!r}"
        )

    vt_patched = args.vision_tower_keep_rate < 1.0
    if vt_patched:
        patch_qwen_vision_tower(
            model,
            QwenVisionPruneConfig(
                layer_idx=args.vision_tower_layer,
                keep_rate=args.vision_tower_keep_rate,
                score_mode=args.score_mode,
                score_seed=args.score_seed,
                codec_score_source=args.codec_score_source,
            ),
        )

    codec_score_source = (
        CodecScoreSource(args.codec_score_source) if args.codec_score_source is not None else None
    )
    fusion_mode = cast(FuseMode, args.fusion_mode)
    normalize_fusion_inputs = not bool(args.no_normalize_fusion_inputs)

    if args.rss_guard_mb > 0:
        check_rss_guard(args.rss_guard_mb, stage="post_model_load")

    results: list[ItemResult] = []
    args.output.parent.mkdir(parents=True, exist_ok=True)
    codec_extract_total_s = 0.0
    with args.output.open("w") as handle:
        for item in items:
            raw, decode_ms, processor_ms, active_boxes = _prepare_item(
                runner,
                processor,
                item,
                frame_count=args.frame_count,
            )
            if vt_patched and codec_score_source is not None:
                codec_grids, codec_extract_s = _per_frame_codec_token_grids(
                    item,
                    frame_count=args.frame_count,
                    active_boxes=active_boxes,
                    codec_score_source=codec_score_source,
                    fusion_mode=fusion_mode,
                    motion_weight=float(args.motion_weight),
                    residual_weight=float(args.residual_weight),
                    normalize_fusion_inputs=normalize_fusion_inputs,
                )
                codec_extract_total_s += codec_extract_s
                merged_group_scores = pool_token_grid_to_merged_groups(
                    codec_grids, spatial_merge_size=QWEN_GROUP_FLATTEN_STRIDE
                )
                model.vision_tower.set_codec_score_grid(merged_group_scores)
            features, vision_ms, prune_info = _compute_qwen_features(model, raw)
            stats = _run_generate(
                model,
                processor,
                raw=raw,
                cached_image_features=features,
                max_tokens=args.max_tokens,
            )
            choice_index = extract_choice(stats.text, item.candidates)
            parse_failure = choice_index is None
            grid = np.asarray(raw["image_grid_thw"], dtype=np.int64)
            total_groups = sum(qwen_groups_per_frame(grid, spatial_merge_size=2))
            kept_groups = int(prune_info["kept_groups"]) if prune_info is not None else total_groups
            kept_groups_per_frame = (
                list(prune_info["kept_groups_per_frame"])
                if prune_info is not None
                else list(qwen_groups_per_frame(grid, spatial_merge_size=2))
            )
            record = ItemResult(
                item_id=item.item_id,
                benchmark=item.benchmark,
                group=item.group,
                correct=choice_index is not None and choice_index == item.answer_index,
                parse_failure=parse_failure,
                choice_index=choice_index,
                answer_index=item.answer_index,
                text=stats.text,
                timings=StageTimings(
                    decode_ms=decode_ms,
                    processor_ms=processor_ms,
                    vision_ms=vision_ms,
                    generate_ms=stats.elapsed_ms,
                    end_to_end_ms=decode_ms + processor_ms + vision_ms + stats.elapsed_ms,
                ),
                prompt_tokens=stats.prompt_tokens,
                generation_tokens=stats.generation_tokens,
                prompt_tps=stats.prompt_tps,
                generation_tps=stats.generation_tps,
                kept_groups=kept_groups,
                total_groups=total_groups,
                kept_groups_per_frame=kept_groups_per_frame,
                peak_memory_gb=stats.peak_memory_gb,
            )
            results.append(record)
            handle.write(json.dumps(_record_payload(record)) + "\n")
            handle.flush()
            _clear_runtime_state()
            if args.rss_guard_mb > 0:
                check_rss_guard(args.rss_guard_mb, stage=f"post_item:{item.item_id}")

    summary = _summarize(results)
    summary.update(
        {
            "manifest": str(args.manifest),
            "model_path": str(args.model_path),
            "frame_count": args.frame_count,
            "n_frames": args.frame_count,
            "max_tokens": args.max_tokens,
            "vision_tower_patched": vt_patched,
            "vision_tower_layer": args.vision_tower_layer if vt_patched else None,
            "vision_tower_keep_rate": args.vision_tower_keep_rate if vt_patched else None,
            "score_mode": args.score_mode if vt_patched else None,
            "score_seed": args.score_seed
            if vt_patched and args.score_mode == "uniform_random"
            else None,
            "codec_score_source": args.codec_score_source if vt_patched else None,
            "codec_fusion_mode": (
                args.fusion_mode if vt_patched and args.codec_score_source == "fused" else None
            ),
            "codec_motion_weight": (
                float(args.motion_weight)
                if vt_patched and args.codec_score_source == "fused"
                else None
            ),
            "codec_residual_weight": (
                float(args.residual_weight)
                if vt_patched and args.codec_score_source == "fused"
                else None
            ),
            "codec_normalize_fusion_inputs": (
                normalize_fusion_inputs
                if vt_patched and args.codec_score_source == "fused"
                else None
            ),
            "codec_extract_total_s": (
                float(codec_extract_total_s) if codec_score_source is not None else None
            ),
            "codec_extract_mean_s_per_item": (
                float(codec_extract_total_s / len(results))
                if codec_score_source is not None and results
                else None
            ),
            "rss_guard_mb": args.rss_guard_mb if args.rss_guard_mb > 0 else None,
            "final_rss_mb": rss_mb(),
        }
    )
    args.summary.parent.mkdir(parents=True, exist_ok=True)
    args.summary.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
