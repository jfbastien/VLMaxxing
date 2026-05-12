#!/usr/bin/env python3
"""Run one Gemma Track B sparse-ViT arm for Phase 1.63G."""

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
from mlx_vlm.utils import prepare_inputs
from PIL import Image

# Avoid IOGPU state-inconsistency panics under allocation churn
# (CVE-2026-28834-class GPU-driver race, unpatched on macOS 26.3).
mx.set_memory_limit(12 * 1024**3)

from codec_through.answers import extract_choice  # noqa: E402
from codec_through.codec.continuous_score import (  # noqa: E402
    CodecScoreSource,
    project_macroblock_metadata_to_token_grid,
    sparse_sample_indices,
)
from codec_through.codec.h264_metadata import H264MetadataExtractor  # noqa: E402
from codec_through.codec.onevision_patchification import FuseMode  # noqa: E402
from codec_through.memory_guard import check_rss_guard, rss_mb  # noqa: E402
from codec_through.pruned_vision_tower import PruneConfig, patch_vision_tower  # noqa: E402
from codec_through.video_decode import _count_frames  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]
RUNNER_PATH = REPO_ROOT / "scripts" / "run_benchmark_track_a.py"
DEFAULT_MODEL_PATH = Path.home() / "models" / "gemma-4-e4b-it-4bit"
GEMMA_SOFT_GRID_SHAPE = (16, 16)
GEMMA_PATCH_SIZE = 16
GEMMA_POOLING_KERNEL_SIZE = 3
GEMMA_PATCH_GRID_SHAPE = (
    GEMMA_SOFT_GRID_SHAPE[0] * GEMMA_POOLING_KERNEL_SIZE,
    GEMMA_SOFT_GRID_SHAPE[1] * GEMMA_POOLING_KERNEL_SIZE,
)
GEMMA_IMAGE_SIZE = GEMMA_PATCH_GRID_SHAPE[0] * GEMMA_PATCH_SIZE
GEMMA_TOKEN_BLOCK = GEMMA_PATCH_SIZE
CODEC_SCORE_SOURCE_CHOICES: tuple[str, ...] = tuple(source.value for source in CodecScoreSource)
FUSION_MODE_CHOICES: tuple[FuseMode, ...] = ("weighted", "sum", "max", "geomean")


@dataclass(frozen=True, slots=True)
class GemmaCodecGeometry:
    image_size: int
    soft_grid_shape: tuple[int, int]
    patch_grid_shape: tuple[int, int]
    patch_size: int
    pooling_kernel_size: int
    max_patches: int

    @property
    def soft_tokens_per_frame(self) -> int:
        return self.soft_grid_shape[0] * self.soft_grid_shape[1]

    @property
    def real_patches_per_frame(self) -> int:
        return self.patch_grid_shape[0] * self.patch_grid_shape[1]


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
    name = "_phase1_63g_gemma_runner"
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


def _resize_square_with_active_box(
    frame: Any,
    active_box: tuple[int, int, int, int],
    *,
    size: int = GEMMA_IMAGE_SIZE,
) -> tuple[Any, tuple[int, int, int, int]]:
    """Resize the shared 560-square benchmark frame to Gemma's fixed canvas.

    ``run_benchmark_track_a._decode_uniform_frames`` already returns a square
    padded frame plus the active content box. Re-letterboxing the square would
    lose that content box, so we scale the frame and box together.
    """

    width, height = frame.size
    if width != height:
        raise ValueError(f"expected square benchmark frame before Gemma resize, got {frame.size}")
    scale = size / width
    resized = frame.resize((size, size), Image.Resampling.BICUBIC)
    left, top, right, bottom = active_box
    scaled_box = (
        max(0, min(size, round(left * scale))),
        max(0, min(size, round(top * scale))),
        max(0, min(size, round(right * scale))),
        max(0, min(size, round(bottom * scale))),
    )
    if scaled_box[0] >= scaled_box[2] or scaled_box[1] >= scaled_box[3]:
        raise ValueError(f"scaled active box is empty: {scaled_box}")
    return resized, scaled_box


def _build_prompt(processor: Any, frames: list[Any], question: str) -> dict[str, Any]:
    messages = [
        {
            "role": "user",
            "content": [*({"type": "image"} for _ in frames), {"type": "text", "text": question}],
        }
    ]
    rendered = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    return cast(dict[str, Any], prepare_inputs(processor, images=frames, prompts=rendered))


def _prepare_item(
    runner: Any,
    processor: Any,
    item: Any,
    *,
    frame_count: int,
) -> tuple[dict[str, Any], float, float, list[tuple[int, int, int, int]]]:
    if hasattr(processor, "image_processor"):
        if hasattr(processor.image_processor, "do_resize"):
            processor.image_processor.do_resize = False
        if hasattr(processor.image_processor, "do_image_splitting"):
            processor.image_processor.do_image_splitting = False

    t0 = time.perf_counter_ns()
    frames, active_boxes = runner._decode_uniform_frames(
        item.video_path,
        frame_count=frame_count,
        start_seconds=item.start_seconds,
        end_seconds=item.end_seconds,
    )
    converted = [
        _resize_square_with_active_box(frame, active_box)
        for frame, active_box in zip(frames, active_boxes, strict=True)
    ]
    frames = [frame for frame, _active_box in converted]
    gemma_active_boxes = [active_box for _frame, active_box in converted]
    decode_ms = (time.perf_counter_ns() - t0) / 1_000_000

    t1 = time.perf_counter_ns()
    raw = _build_prompt(processor, frames, item.question)
    processor_ms = (time.perf_counter_ns() - t1) / 1_000_000
    return raw, decode_ms, processor_ms, gemma_active_boxes


def _gemma_codec_geometry(model: Any) -> GemmaCodecGeometry:
    vision_tower = model.vision_tower
    patch_size = int(getattr(vision_tower, "patch_size", GEMMA_PATCH_SIZE))
    pooling_kernel_size = int(
        getattr(vision_tower, "pooling_kernel_size", GEMMA_POOLING_KERNEL_SIZE)
    )
    default_output_length = int(
        getattr(
            vision_tower,
            "default_output_length",
            GEMMA_SOFT_GRID_SHAPE[0] * GEMMA_SOFT_GRID_SHAPE[1],
        )
    )
    max_patches = int(
        getattr(vision_tower, "max_patches", default_output_length * pooling_kernel_size**2)
    )
    soft_grid_shape = GEMMA_SOFT_GRID_SHAPE
    patch_grid_shape = (
        soft_grid_shape[0] * pooling_kernel_size,
        soft_grid_shape[1] * pooling_kernel_size,
    )
    real_patches = patch_grid_shape[0] * patch_grid_shape[1]
    if patch_size != GEMMA_PATCH_SIZE:
        raise ValueError(
            f"Gemma codec path expected patch_size={GEMMA_PATCH_SIZE}, got {patch_size}"
        )
    if pooling_kernel_size != GEMMA_POOLING_KERNEL_SIZE:
        raise ValueError(
            f"Gemma codec path expected pooling_kernel_size={GEMMA_POOLING_KERNEL_SIZE}, "
            f"got {pooling_kernel_size}"
        )
    if real_patches > max_patches:
        raise ValueError(
            f"Gemma codec path needs {real_patches} real patches but "
            f"model max_patches={max_patches}"
        )
    return GemmaCodecGeometry(
        image_size=patch_grid_shape[0] * patch_size,
        soft_grid_shape=soft_grid_shape,
        patch_grid_shape=patch_grid_shape,
        patch_size=patch_size,
        pooling_kernel_size=pooling_kernel_size,
        max_patches=max_patches,
    )


def _validate_gemma_placeholders(
    model: Any,
    raw: dict[str, Any],
    *,
    frame_count: int,
    geometry: GemmaCodecGeometry | None = None,
) -> None:
    geometry = geometry or _gemma_codec_geometry(model)
    input_ids = np.asarray(raw["input_ids"], dtype=np.int64).reshape(-1)
    image_token_id = int(model.config.image_token_id)
    observed = int((input_ids == image_token_id).sum())
    expected = frame_count * geometry.soft_tokens_per_frame
    if observed != expected:
        raise RuntimeError(
            f"Gemma placeholder-count mismatch: processor emitted {observed} "
            f"image tokens for {frame_count} frames; driver assumed {expected} "
            f"({frame_count} x {geometry.soft_grid_shape[0]}x{geometry.soft_grid_shape[1]})."
        )


def _per_frame_codec_token_grids(
    item: Any,
    *,
    frame_count: int,
    active_boxes: list[tuple[int, int, int, int]],
    geometry: GemmaCodecGeometry,
    codec_score_source: CodecScoreSource,
    fusion_mode: FuseMode,
    motion_weight: float,
    residual_weight: float,
    normalize_fusion_inputs: bool,
) -> tuple[list[np.ndarray], float]:
    """Compute per-sampled-frame codec scores on Gemma's pre-pool patch grid."""

    if item.start_seconds is not None or item.end_seconds is not None:
        raise ValueError(
            f"codec score extraction for windowed clips is not implemented for "
            f"{item.item_id}; clear start_seconds/end_seconds before running Gemma Track B"
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
            canvas_size=geometry.image_size,
            active_box=active_box,
            token_block=geometry.patch_size,
            mode=fusion_mode,
            motion_weight=motion_weight,
            residual_weight=residual_weight,
            normalize_inputs=normalize_fusion_inputs,
        )
        expected_shape = geometry.patch_grid_shape
        if token_grid.shape != expected_shape:
            raise ValueError(
                f"Gemma codec score grid for {item.item_id} has shape {token_grid.shape}, "
                f"expected {expected_shape}"
            )
        token_grids.append(np.clip(token_grid, a_min=0.0, a_max=None).astype(np.float32))

    return token_grids, float(extract_s)


def _stack_gemma_codec_score_grid(
    codec_grids: list[np.ndarray],
    *,
    geometry: GemmaCodecGeometry,
) -> np.ndarray:
    """Flatten and pad per-frame patch score grids into Gemma encoder [B, L] form."""

    if not codec_grids:
        raise ValueError("cannot stack an empty Gemma codec score grid list")
    flattened: list[np.ndarray] = []
    for index, grid in enumerate(codec_grids):
        array = np.asarray(grid, dtype=np.float32)
        if array.shape != geometry.patch_grid_shape:
            raise ValueError(
                f"Gemma codec score grid at frame {index} has shape {array.shape}, "
                f"expected {geometry.patch_grid_shape}"
            )
        if not np.all(np.isfinite(array)):
            raise ValueError(f"Gemma codec score grid at frame {index} contains non-finite values")
        if np.any(array < 0.0):
            raise ValueError(f"Gemma codec score grid at frame {index} contains negative values")
        flat = array.reshape(-1)
        if flat.shape[0] > geometry.max_patches:
            raise ValueError(
                f"Gemma codec score grid at frame {index} has {flat.shape[0]} patches, "
                f"exceeding max_patches={geometry.max_patches}"
            )
        if flat.shape[0] < geometry.max_patches:
            flat = np.pad(flat, (0, geometry.max_patches - flat.shape[0]), constant_values=0.0)
        flattened.append(flat)
    return np.stack(flattened, axis=0).astype(np.float32, copy=False)


def _compute_gemma_features(model: Any, raw: dict[str, Any]) -> tuple[mx.array, float]:
    pixel_values = mx.array(raw["pixel_values"])
    t0 = time.perf_counter_ns()
    features = model.vision_tower(pixel_values)
    features = model.embed_vision(features)
    mx.eval(features)
    vision_ms = (time.perf_counter_ns() - t0) / 1_000_000
    return cast(mx.array, features), vision_ms


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
    return {
        "n_items": len(records),
        "dense_accuracy": sum(1 for record in records if record.correct) / len(records),
        "dense_parse_failures": sum(1 for record in records if record.parse_failure),
        "mean_decode_ms": float(np.mean([record.timings.decode_ms for record in records])),
        "mean_processor_ms": float(np.mean([record.timings.processor_ms for record in records])),
        "mean_dense_vision_ms": float(np.mean([record.timings.vision_ms for record in records])),
        "mean_dense_generate_ms": float(
            np.mean([record.timings.generate_ms for record in records])
        ),
        "mean_dense_end_to_end_ms": float(
            np.mean([record.timings.end_to_end_ms for record in records])
        ),
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
    )
    parser.add_argument(
        "--score-seed",
        type=int,
        default=42,
        help="Seed for --score-mode uniform_random.",
    )
    parser.add_argument(
        "--codec-score-source",
        type=str,
        default=None,
        choices=CODEC_SCORE_SOURCE_CHOICES,
        help="When --score-mode=codec_grid, which H.264 score source to use.",
    )
    parser.add_argument(
        "--fusion-mode",
        type=str,
        default="weighted",
        choices=FUSION_MODE_CHOICES,
    )
    parser.add_argument("--motion-weight", type=float, default=1.0)
    parser.add_argument("--residual-weight", type=float, default=1.0)
    parser.add_argument("--no-normalize-fusion-inputs", action="store_true")
    args = parser.parse_args()
    if args.score_mode == "codec_grid" and args.codec_score_source is None:
        parser.error("--score-mode=codec_grid requires --codec-score-source")
    if args.score_mode != "codec_grid" and args.codec_score_source is not None:
        parser.error("--codec-score-source requires --score-mode=codec_grid")
    if args.vision_tower_keep_rate >= 1.0 and args.score_mode != "magnitude_norm":
        parser.error(
            "--score-mode other than magnitude_norm requires --vision-tower-keep-rate < 1.0"
        )

    runner = _load_runner_module()
    runner._ensure_clean_git_tree(allow_dirty=args.allow_dirty)
    items = _load_manifest_items(runner, args.manifest)
    if args.n_items > 0:
        items = items[: args.n_items]
    if not items:
        raise SystemExit("no items loaded from manifest")

    model, processor = cast(tuple[Any, Any], load(str(args.model_path)))
    if getattr(model.config, "model_type", None) != "gemma4":
        raise SystemExit(
            f"run_phase1_63G_gemma_track_b.py supports gemma4 only; got "
            f"{getattr(model.config, 'model_type', None)!r}"
        )
    geometry = _gemma_codec_geometry(model)
    print(
        "[phase1_63G] gemma_geometry "
        f"image_size={geometry.image_size} "
        f"soft_grid={geometry.soft_grid_shape[0]}x{geometry.soft_grid_shape[1]} "
        f"patch_grid={geometry.patch_grid_shape[0]}x{geometry.patch_grid_shape[1]} "
        f"patch_size={geometry.patch_size} "
        f"pooling_kernel={geometry.pooling_kernel_size} "
        f"max_patches={geometry.max_patches}",
        flush=True,
    )

    vt_patched = args.vision_tower_keep_rate < 1.0
    if vt_patched:
        patch_vision_tower(
            model,
            PruneConfig(
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

    tokens_per_frame = geometry.real_patches_per_frame
    total_groups = args.frame_count * tokens_per_frame
    kept_per_frame = (
        max(1, int(tokens_per_frame * args.vision_tower_keep_rate))
        if vt_patched
        else tokens_per_frame
    )
    kept_groups = args.frame_count * kept_per_frame

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
            _validate_gemma_placeholders(
                model,
                raw,
                frame_count=args.frame_count,
                geometry=geometry,
            )
            if vt_patched and codec_score_source is not None:
                codec_grids, codec_extract_s = _per_frame_codec_token_grids(
                    item,
                    frame_count=args.frame_count,
                    active_boxes=active_boxes,
                    geometry=geometry,
                    codec_score_source=codec_score_source,
                    fusion_mode=fusion_mode,
                    motion_weight=float(args.motion_weight),
                    residual_weight=float(args.residual_weight),
                    normalize_fusion_inputs=normalize_fusion_inputs,
                )
                codec_extract_total_s += codec_extract_s
                score_grid = _stack_gemma_codec_score_grid(codec_grids, geometry=geometry)
                model.vision_tower.encoder.set_codec_score_grid(score_grid)
            features, vision_ms = _compute_gemma_features(model, raw)
            stats = _run_generate(
                model,
                processor,
                raw=raw,
                cached_image_features=features,
                max_tokens=args.max_tokens,
            )
            choice_index = extract_choice(stats.text, item.candidates)
            record = ItemResult(
                item_id=item.item_id,
                benchmark=item.benchmark,
                group=item.group,
                correct=choice_index is not None and choice_index == item.answer_index,
                parse_failure=choice_index is None,
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
                kept_groups_per_frame=[kept_per_frame] * args.frame_count,
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
            "gemma_image_size": geometry.image_size,
            "gemma_soft_grid_shape": list(geometry.soft_grid_shape),
            "gemma_patch_grid_shape": list(geometry.patch_grid_shape),
            "gemma_patch_size": geometry.patch_size,
            "gemma_pooling_kernel_size": geometry.pooling_kernel_size,
            "gemma_encoder_max_patches": geometry.max_patches,
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
