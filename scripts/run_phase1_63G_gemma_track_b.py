#!/usr/bin/env python3
"""Run one Gemma Track B sparse-ViT arm for Phase 1.63G."""

from __future__ import annotations

import argparse
import gc
import hashlib
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
from mlx_vlm import load, stream_generate
from mlx_vlm.utils import prepare_inputs
from PIL import Image

# Avoid IOGPU state-inconsistency panics under allocation churn
# (CVE-2026-28834-class GPU-driver race, unpatched on macOS 26.3).
mx.set_memory_limit(12 * 1024**3)

from codec_through.answers import extract_choice  # noqa: E402
from codec_through.memory_guard import check_rss_guard, rss_mb  # noqa: E402
from codec_through.pruned_vision_tower import PruneConfig, patch_vision_tower  # noqa: E402
from codec_through.rlt_masks import (  # noqa: E402
    RLTMaskConfig,
    compute_rlt_keep_mask_from_frames,
    fixed_budget_rlt_score_mask,
    fixed_budget_rlt_score_mask_for_positions,
    mask_summary,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
RUNNER_PATH = REPO_ROOT / "scripts" / "run_benchmark_track_a.py"
DEFAULT_MODEL_PATH = Path.home() / "models" / "gemma-4-e4b-it-4bit"
GEMMA_IMAGE_SIZE = 512
GEMMA_GRID_SHAPE = (16, 16)
SCHEMA_VERSION = "phase1_63g_gemma_track_b_v4"


@dataclass(frozen=True, slots=True)
class StageTimings:
    decode_ms: float
    processor_ms: float
    vision_ms: float
    multimodal_prefill_ms: float
    text_generation_ms: float
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
    metadata: dict[str, Any]


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


def _letterbox_square(frame: Any, size: int = GEMMA_IMAGE_SIZE) -> Any:
    width, height = frame.size
    scale = min(size / width, size / height)
    resized = frame.resize(
        (max(1, round(width * scale)), max(1, round(height * scale))),
        Image.Resampling.BICUBIC,
    )
    canvas = Image.new("RGB", (size, size), color=(0, 0, 0))
    canvas.paste(resized, ((size - resized.width) // 2, (size - resized.height) // 2))
    return canvas


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
) -> tuple[dict[str, Any], list[Any], float, float]:
    if hasattr(processor, "image_processor"):
        if hasattr(processor.image_processor, "do_resize"):
            processor.image_processor.do_resize = False
        if hasattr(processor.image_processor, "do_image_splitting"):
            processor.image_processor.do_image_splitting = False

    t0 = time.perf_counter_ns()
    frames, _active_boxes = runner._decode_uniform_frames(
        item.video_path,
        frame_count=frame_count,
        start_seconds=item.start_seconds,
        end_seconds=item.end_seconds,
    )
    frames = [_letterbox_square(frame) for frame in frames]
    decode_ms = (time.perf_counter_ns() - t0) / 1_000_000

    t1 = time.perf_counter_ns()
    raw = _build_prompt(processor, frames, item.question)
    processor_ms = (time.perf_counter_ns() - t1) / 1_000_000
    return raw, frames, decode_ms, processor_ms


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
    multimodal_prefill_ms: float
    text_generation_ms: float
    prompt_time_source: str
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
    first_yield_ns: int | None = None
    last_response: Any | None = None
    text = ""
    mx.random.seed(42)
    for response in stream_generate(
        model,
        processor,
        "",
        input_ids=input_ids,
        pixel_values=pixel_values,
        mask=mask,
        max_tokens=max_tokens,
        temperature=0.0,
        **kwargs,
    ):
        if first_yield_ns is None:
            first_yield_ns = time.perf_counter_ns()
        text += str(response.text)
        last_response = response
    elapsed_ms = (time.perf_counter_ns() - t0) / 1_000_000
    if first_yield_ns is None or last_response is None:
        return GenerateStats(
            text=text,
            elapsed_ms=elapsed_ms,
            multimodal_prefill_ms=0.0,
            text_generation_ms=elapsed_ms,
            prompt_time_source="stream_generate_no_yield",
            prompt_tokens=0,
            generation_tokens=0,
            prompt_tps=0.0,
            generation_tps=0.0,
            peak_memory_gb=0.0,
        )
    multimodal_prefill_ms = (first_yield_ns - t0) / 1_000_000
    return GenerateStats(
        text=text,
        elapsed_ms=elapsed_ms,
        multimodal_prefill_ms=multimodal_prefill_ms,
        text_generation_ms=max(0.0, elapsed_ms - multimodal_prefill_ms),
        prompt_time_source="stream_generate_first_yield_wall_clock",
        prompt_tokens=int(getattr(last_response, "prompt_tokens", 0)),
        generation_tokens=int(getattr(last_response, "generation_tokens", 0)),
        prompt_tps=float(getattr(last_response, "prompt_tps", 0.0)),
        generation_tps=float(getattr(last_response, "generation_tps", 0.0)),
        peak_memory_gb=float(getattr(last_response, "peak_memory", 0.0)),
    )


def _stage_ms_from_tps(*, tokens: int, tokens_per_second: float, stage: str) -> float:
    if tokens == 0:
        return 0.0
    if tokens_per_second <= 0.0:
        raise ValueError(
            f"cannot derive {stage} timing: tokens={tokens}, tokens_per_second={tokens_per_second}"
        )
    return float(tokens / tokens_per_second * 1000.0)


def _artifact_hash(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _max_min_diversity_indices(features: np.ndarray, keep_count: int) -> np.ndarray:
    if features.ndim != 2:
        raise ValueError(f"features must be [N, D], got {features.shape}")
    n, _dim = features.shape
    if keep_count <= 0:
        raise ValueError("keep_count must be positive")
    if keep_count >= n:
        return np.arange(n, dtype=np.int64)
    norms_l1 = np.linalg.norm(features, ord=1, axis=1)
    chosen: list[int] = [int(np.argmax(norms_l1))]
    chosen_set = {chosen[0]}
    min_sq_dist = np.full(n, np.inf, dtype=np.float64)
    while len(chosen) < keep_count:
        diff = features - features[chosen[-1]]
        sq_dist = np.sum(diff * diff, axis=1)
        min_sq_dist = np.minimum(min_sq_dist, sq_dist)
        candidate_scores = min_sq_dist.copy()
        for idx in chosen_set:
            candidate_scores[idx] = -np.inf
        next_idx = int(np.argmax(candidate_scores))
        chosen.append(next_idx)
        chosen_set.add(next_idx)
    return np.asarray(chosen, dtype=np.int64)


def _max_min_diversity_mask_for_positions(
    hidden_states: mx.array,
    positions: mx.array,
    *,
    keep_rate: float,
) -> tuple[np.ndarray, list[int]]:
    hidden_np = np.array(hidden_states.astype(mx.float32))
    pos_np = np.array(positions)
    if hidden_np.ndim != 3:
        raise ValueError(f"hidden_states must be [B, L, D], got {hidden_np.shape}")
    if pos_np.shape[:2] != hidden_np.shape[:2] or pos_np.shape[-1] != 2:
        raise ValueError(
            f"positions shape {pos_np.shape} does not match hidden_states {hidden_np.shape}"
        )
    rows, row_len, _dim = hidden_np.shape
    keep = np.zeros((rows, row_len), dtype=bool)
    valid_counts: list[int] = []
    kept_counts: list[int] = []
    for row_idx in range(rows):
        xy = pos_np[row_idx]
        valid = (xy[:, 0] >= 0) & (xy[:, 1] >= 0)
        valid_indices = np.flatnonzero(valid)
        valid_count = int(valid_indices.size)
        if valid_count <= 0:
            raise ValueError(f"row {row_idx} has no valid encoder positions")
        keep_count = max(1, int(valid_count * keep_rate))
        selected_local = _max_min_diversity_indices(hidden_np[row_idx, valid_indices], keep_count)
        keep[row_idx, valid_indices[selected_local]] = True
        valid_counts.append(valid_count)
        kept_counts.append(keep_count)
    if len(set(kept_counts)) != 1:
        raise ValueError(f"max_min_diversity must keep uniform K across rows; got {kept_counts}")
    return keep, valid_counts


def _rlt_config_from_args(args: argparse.Namespace) -> RLTMaskConfig:
    return RLTMaskConfig(
        threshold=args.rlt_threshold,
        tubelet_size=args.rlt_tubelet_size,
        image_size=(args.rlt_image_size, args.rlt_image_size),
        patch_size=16,
        grid_shape=None,
        normalize_mode="imagenet",
        pixel_scale="uint8",
        first_tubelet_mode="full_grid",
        window_min_keep=args.rlt_per_frame_min_keep,
        ordering="time_major",
    )


def _schema_row(args: argparse.Namespace) -> dict[str, Any]:
    payload = {
        "manifest": str(args.manifest),
        "model_path": str(args.model_path),
        "frame_count": args.frame_count,
        "max_tokens": args.max_tokens,
        "warmup_items": getattr(args, "warmup_items", 0),
        "vision_tower_layer": args.vision_tower_layer,
        "vision_tower_keep_rate": args.vision_tower_keep_rate,
        "vision_tower_score_mode": args.vision_tower_score_mode,
        "rlt_config": (
            _rlt_config_from_args(args).as_dict()
            if args.vision_tower_score_mode == "rlt_topk"
            else None
        ),
    }
    return {
        "kind": "schema",
        "schema_version": SCHEMA_VERSION,
        "artifact_config_hash": _artifact_hash(payload),
        "artifact_payload": payload,
        "timing_split": "stream_generate_first_yield_wall_clock",
    }


def _clear_runtime_state() -> None:
    gc.collect()
    mx.clear_cache()


def _load_manifest_items(runner: Any, manifest_path: Path) -> list[Any]:
    payload = tomllib.loads(manifest_path.read_text())
    return cast(list[Any], runner._load_items_by_id(payload["benchmark"], payload["item_ids"]))


def _load_output_rows_for_resume(path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    schema: dict[str, Any] | None = None
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if not stripped:
                continue
            payload = json.loads(stripped)
            if payload.get("kind") == "schema":
                schema = payload
            elif payload.get("kind") in (None, "item"):
                rows.append(payload)
            else:
                raise ValueError(f"unexpected row kind in {path}: {payload.get('kind')!r}")
    if schema is None:
        raise ValueError(f"{path} is missing schema row")
    return schema, rows


def _record_payload(record: ItemResult) -> dict[str, Any]:
    return {
        "kind": "item",
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
            "multimodal_prefill": record.timings.multimodal_prefill_ms,
            "multimodal_prefill_ms": record.timings.multimodal_prefill_ms,
            "text_generation": record.timings.text_generation_ms,
            "text_generation_ms": record.timings.text_generation_ms,
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
        "metadata": record.metadata,
    }


def _timing_from_payload(row: dict[str, Any], key: str) -> float:
    timings = row.get("timing_ms")
    if not isinstance(timings, dict):
        raise ValueError(f"missing timing_ms in {row.get('item_id')}")
    value = timings.get(key)
    if value is None:
        raise ValueError(f"missing timing_ms.{key} in {row.get('item_id')}")
    return float(value)


def _summarize_payload_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {"n_items": 0}
    return {
        "n_items": len(rows),
        "dense_accuracy": sum(1 for row in rows if row.get("correct")) / len(rows),
        "dense_parse_failures": sum(1 for row in rows if row.get("parse_failure")),
        "mean_decode_ms": float(np.mean([_timing_from_payload(row, "decode") for row in rows])),
        "mean_processor_ms": float(
            np.mean([_timing_from_payload(row, "processor") for row in rows])
        ),
        "mean_dense_vision_ms": float(
            np.mean([_timing_from_payload(row, "vision") for row in rows])
        ),
        "mean_dense_multimodal_prefill_ms": float(
            np.mean([_timing_from_payload(row, "multimodal_prefill_ms") for row in rows])
        ),
        "mean_dense_text_generation_ms": float(
            np.mean([_timing_from_payload(row, "text_generation_ms") for row in rows])
        ),
        "mean_dense_generate_ms": float(
            np.mean([_timing_from_payload(row, "generate") for row in rows])
        ),
        "mean_dense_end_to_end_ms": float(
            np.mean([_timing_from_payload(row, "end_to_end") for row in rows])
        ),
        "mean_dense_prompt_tokens": float(np.mean([row.get("prompt_tokens", 0) for row in rows])),
        "mean_dense_generation_tokens": float(
            np.mean([row.get("generation_tokens", 0) for row in rows])
        ),
        "mean_dense_prompt_tps": float(np.mean([row.get("prompt_tps", 0.0) for row in rows])),
        "mean_dense_generation_tps": float(
            np.mean([row.get("generation_tps", 0.0) for row in rows])
        ),
        "mean_peak_memory_gb": float(np.mean([row.get("peak_memory_gb", 0.0) for row in rows])),
        "mean_kept_groups": float(np.mean([row.get("kept_groups", 0) for row in rows])),
        "mean_total_groups": float(np.mean([row.get("total_groups", 0) for row in rows])),
        "mean_effective_keep_rate": float(
            np.mean(
                [
                    float(row.get("kept_groups", 0)) / float(row.get("total_groups", 1))
                    for row in rows
                    if float(row.get("total_groups", 0)) > 0.0
                ]
            )
        ),
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
        "mean_dense_multimodal_prefill_ms": float(
            np.mean([record.timings.multimodal_prefill_ms for record in records])
        ),
        "mean_dense_text_generation_ms": float(
            np.mean([record.timings.text_generation_ms for record in records])
        ),
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
    parser.add_argument(
        "--resume",
        action="store_true",
        help=(
            "Append to an existing JSONL with the same artifact_config_hash and skip "
            "completed item_ids. This is required for autonomous follow-up sweeps."
        ),
    )
    parser.add_argument("--rss-guard-mb", type=int, default=0)
    parser.add_argument(
        "--warmup-items",
        type=int,
        default=0,
        help=(
            "Run this many discarded items through decode, vision, and generation "
            "before recording measurements. Used to avoid item-0 MLX JIT timing "
            "contamination in autonomous sparse-vision sweeps."
        ),
    )
    parser.add_argument("--vision-tower-layer", type=int, default=2)
    parser.add_argument("--vision-tower-keep-rate", type=float, default=1.0)
    parser.add_argument(
        "--vision-tower-score-mode",
        choices=("magnitude", "rlt_topk", "max_min_diversity"),
        default="magnitude",
        help=(
            "Sparse-vision token scorer. 'magnitude' is the existing hidden-state "
            "L2 scorer; 'rlt_topk' ranks tokens by RLT same-position motion scores "
            "and keeps a fixed K per frame for the scatter-back wrapper; "
            "'max_min_diversity' is the expensive feature-dependent comparator."
        ),
    )
    parser.add_argument("--rlt-threshold", type=float, default=0.1)
    parser.add_argument("--rlt-tubelet-size", type=int, default=2)
    parser.add_argument("--rlt-image-size", type=int, default=224)
    parser.add_argument("--rlt-per-frame-min-keep", type=int, default=1)
    args = parser.parse_args()
    if args.warmup_items < 0:
        raise SystemExit("--warmup-items must be nonnegative")

    runner = _load_runner_module()
    runner._ensure_clean_git_tree(allow_dirty=args.allow_dirty)
    items = _load_manifest_items(runner, args.manifest)
    if args.n_items > 0:
        items = items[: args.n_items]
    if not items:
        raise SystemExit("no items loaded from manifest")

    schema_row = _schema_row(args)
    existing_rows: list[dict[str, Any]] = []
    completed_item_ids: set[str] = set()
    if args.resume and args.output.exists() and args.output.stat().st_size > 0:
        existing_schema, existing_rows = _load_output_rows_for_resume(args.output)
        if existing_schema.get("artifact_config_hash") != schema_row["artifact_config_hash"]:
            raise SystemExit(
                "refusing to resume because artifact_config_hash changed: "
                f"existing={existing_schema.get('artifact_config_hash')} "
                f"current={schema_row['artifact_config_hash']}"
            )
        completed_item_ids = {str(row["item_id"]) for row in existing_rows}
        print(
            f"[resume] loaded {len(existing_rows)} completed rows from {args.output}; "
            f"skipping {len(completed_item_ids)} item_ids"
        )
    pending_items = [item for item in items if item.item_id not in completed_item_ids]
    if args.resume and not pending_items:
        summary = _summarize_payload_rows(existing_rows)
        summary.update(
            {
                "schema_version": SCHEMA_VERSION,
                "manifest": str(args.manifest),
                "model_path": str(args.model_path),
                "frame_count": args.frame_count,
                "n_frames": args.frame_count,
                "max_tokens": args.max_tokens,
                "warmup_items": args.warmup_items,
                "vision_tower_patched": args.vision_tower_keep_rate < 1.0,
                "vision_tower_layer": (
                    args.vision_tower_layer if args.vision_tower_keep_rate < 1.0 else None
                ),
                "vision_tower_keep_rate": (
                    args.vision_tower_keep_rate if args.vision_tower_keep_rate < 1.0 else None
                ),
                "vision_tower_score_mode": (
                    args.vision_tower_score_mode if args.vision_tower_keep_rate < 1.0 else None
                ),
                "rlt_config": (
                    _rlt_config_from_args(args).as_dict()
                    if args.vision_tower_keep_rate < 1.0
                    and args.vision_tower_score_mode == "rlt_topk"
                    else None
                ),
                "rss_guard_mb": args.rss_guard_mb if args.rss_guard_mb > 0 else None,
                "final_rss_mb": None,
                "resume": True,
                "resumed_existing_rows": len(existing_rows),
                "new_rows": 0,
            }
        )
        args.summary.parent.mkdir(parents=True, exist_ok=True)
        args.summary.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
        print(f"[resume] all {len(existing_rows)} rows already complete; summary refreshed")
        return 0

    model, processor = cast(tuple[Any, Any], load(str(args.model_path)))
    if getattr(model.config, "model_type", None) != "gemma4":
        raise SystemExit(
            f"run_phase1_63G_gemma_track_b.py supports gemma4 only; got "
            f"{getattr(model.config, 'model_type', None)!r}"
        )

    vt_patched = args.vision_tower_keep_rate < 1.0
    if args.vision_tower_score_mode in {"rlt_topk", "max_min_diversity"} and not vt_patched:
        raise SystemExit(
            "--vision-tower-score-mode rlt_topk/max_min_diversity requires "
            "--vision-tower-keep-rate < 1.0"
        )
    rlt_config = _rlt_config_from_args(args)
    rlt_keep_holder: dict[str, Any] = {}
    if vt_patched:
        keep_mask_fn: Any | None = None
        if args.vision_tower_score_mode in {"rlt_topk", "max_min_diversity"}:

            def keep_mask_fn(hidden_states: mx.array, positions: mx.array) -> mx.array:
                if args.vision_tower_score_mode == "rlt_topk":
                    if "rlt_result" not in rlt_keep_holder:
                        raise RuntimeError("RLT result was not prepared before vision_tower call")
                    rlt_result = rlt_keep_holder["rlt_result"]
                    pos_np = np.array(positions)
                    valid_counts = ((pos_np[:, :, 0] >= 0) & (pos_np[:, :, 1] >= 0)).sum(axis=1)
                    mask_np = fixed_budget_rlt_score_mask_for_positions(
                        rlt_result,
                        positions=pos_np,
                        keep_rate=args.vision_tower_keep_rate,
                    )
                    rlt_keep_holder["last_valid_counts"] = [int(value) for value in valid_counts]
                else:
                    mask_np, valid_count_list = _max_min_diversity_mask_for_positions(
                        hidden_states,
                        positions,
                        keep_rate=args.vision_tower_keep_rate,
                    )
                    rlt_keep_holder["last_valid_counts"] = valid_count_list
                rlt_keep_holder["last_mask_np"] = mask_np
                mask = mx.array(mask_np)
                expected = (int(hidden_states.shape[0]), int(hidden_states.shape[1]))
                if tuple(mask.shape) != expected:
                    raise ValueError(
                        f"RLT keep mask shape {tuple(mask.shape)} does not match "
                        f"vision hidden_states rows/tokens {expected}"
                    )
                return mask

        patch_vision_tower(
            model,
            PruneConfig(
                layer_idx=args.vision_tower_layer,
                keep_rate=args.vision_tower_keep_rate,
            ),
            keep_mask_fn=keep_mask_fn,
        )

    if args.rss_guard_mb > 0:
        check_rss_guard(args.rss_guard_mb, stage="post_model_load")

    tokens_per_frame = int(
        getattr(model.vision_tower, "max_patches", GEMMA_GRID_SHAPE[0] * GEMMA_GRID_SHAPE[1])
    )
    total_groups = args.frame_count * tokens_per_frame
    kept_per_frame = (
        max(1, int(tokens_per_frame * args.vision_tower_keep_rate))
        if vt_patched
        else tokens_per_frame
    )
    kept_groups = args.frame_count * kept_per_frame

    def prepare_sparse_scorer_for_frames(frames: list[Any], metadata: dict[str, Any]) -> None:
        if not vt_patched:
            return
        rlt_keep_holder.pop("last_mask_np", None)
        if args.vision_tower_score_mode == "max_min_diversity":
            metadata.update(
                {
                    "feature_scorer_policy": "max_min_diversity_fixed_k",
                    "feature_scorer_domain": "gemma_internal_encoder_positions",
                }
            )
            return
        if args.vision_tower_score_mode != "rlt_topk":
            return
        rlt_result = compute_rlt_keep_mask_from_frames(frames, config=rlt_config)
        projected_placeholder_mask = fixed_budget_rlt_score_mask(
            rlt_result,
            out_grid_shape=GEMMA_GRID_SHAPE,
            keep_rate=args.vision_tower_keep_rate,
        )
        rlt_keep_holder["rlt_result"] = rlt_result
        metadata.update(
            {
                "rlt_config": rlt_config.as_dict(),
                "rlt_mask_policy": "rlt_score_topk_fixed_k",
                "rlt_mask_domain": (
                    "gemma_internal_encoder_positions_from_letterboxed_frames_resized_224_imagenet"
                ),
                "rlt_summary": mask_summary(rlt_result),
                "rlt_score_grid_shape": list(rlt_result.config.resolved_grid_shape()),
                "rlt_placeholder_projected_keep_rate": float(
                    projected_placeholder_mask.sum() / projected_placeholder_mask.size
                ),
            }
        )

    def record_sparse_scorer_after_vision(metadata: dict[str, Any]) -> tuple[int, int, list[int]]:
        if not (vt_patched and args.vision_tower_score_mode in {"rlt_topk", "max_min_diversity"}):
            return kept_groups, total_groups, [kept_per_frame] * args.frame_count
        last_mask = rlt_keep_holder.get("last_mask_np")
        if last_mask is None:
            raise RuntimeError(
                f"{args.vision_tower_score_mode} keep_mask_fn did not run inside vision_tower"
            )
        last_mask_np = np.asarray(last_mask, dtype=bool)
        actual_kept_per_frame = [int(row.sum()) for row in last_mask_np]
        if len(set(actual_kept_per_frame)) != 1:
            raise RuntimeError(
                f"{args.vision_tower_score_mode} scorer must emit uniform per-frame K; got "
                f"{actual_kept_per_frame}"
            )
        valid_counts = [
            int(value) for value in cast(list[int], rlt_keep_holder["last_valid_counts"])
        ]
        metadata.update(
            {
                "gemma_encoder_positions_per_frame": int(last_mask_np.shape[1]),
                "gemma_encoder_valid_positions_per_frame": valid_counts,
                "gemma_encoder_kept_per_frame": actual_kept_per_frame,
                "sparse_budget_domain": "valid_encoder_positions",
                **(
                    {"rlt_budget_domain": "valid_encoder_positions"}
                    if args.vision_tower_score_mode == "rlt_topk"
                    else {"feature_budget_domain": "valid_encoder_positions"}
                ),
            }
        )
        return int(last_mask_np.sum()), int(sum(valid_counts)), actual_kept_per_frame

    for warmup_item in items[: args.warmup_items]:
        _clear_runtime_state()
        warm_raw, warm_frames, _decode_ms, _processor_ms = _prepare_item(
            runner,
            processor,
            warmup_item,
            frame_count=args.frame_count,
        )
        warm_metadata: dict[str, Any] = {}
        prepare_sparse_scorer_for_frames(warm_frames, warm_metadata)
        warm_features, _vision_ms = _compute_gemma_features(model, warm_raw)
        _run_generate(
            model,
            processor,
            raw=warm_raw,
            cached_image_features=warm_features,
            max_tokens=args.max_tokens,
        )
        _clear_runtime_state()

    record_rows: list[dict[str, Any]] = list(existing_rows)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    output_mode = "a" if args.resume and existing_rows else "w"
    with args.output.open(output_mode) as handle:
        if output_mode == "w":
            handle.write(json.dumps(schema_row, sort_keys=True) + "\n")
        for item in pending_items:
            raw, frames, decode_ms, processor_ms = _prepare_item(
                runner,
                processor,
                item,
                frame_count=args.frame_count,
            )
            item_metadata: dict[str, Any] = {
                "vision_tower_score_mode": args.vision_tower_score_mode,
            }
            prepare_sparse_scorer_for_frames(frames, item_metadata)
            features, vision_ms = _compute_gemma_features(model, raw)
            actual_kept_groups, actual_total_groups, actual_kept_per_frame = (
                record_sparse_scorer_after_vision(item_metadata)
            )
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
                    multimodal_prefill_ms=stats.multimodal_prefill_ms,
                    text_generation_ms=stats.text_generation_ms,
                    generate_ms=stats.elapsed_ms,
                    end_to_end_ms=decode_ms + processor_ms + vision_ms + stats.elapsed_ms,
                ),
                prompt_tokens=stats.prompt_tokens,
                generation_tokens=stats.generation_tokens,
                prompt_tps=stats.prompt_tps,
                generation_tps=stats.generation_tps,
                kept_groups=actual_kept_groups,
                total_groups=actual_total_groups,
                kept_groups_per_frame=actual_kept_per_frame,
                peak_memory_gb=stats.peak_memory_gb,
                metadata=item_metadata,
            )
            row = _record_payload(record)
            record_rows.append(row)
            handle.write(json.dumps(row, sort_keys=True) + "\n")
            handle.flush()
            _clear_runtime_state()
            if args.rss_guard_mb > 0:
                check_rss_guard(args.rss_guard_mb, stage=f"post_item:{item.item_id}")

    summary = _summarize_payload_rows(record_rows)
    summary.update(
        {
            "schema_version": SCHEMA_VERSION,
            "manifest": str(args.manifest),
            "model_path": str(args.model_path),
            "frame_count": args.frame_count,
            "n_frames": args.frame_count,
            "max_tokens": args.max_tokens,
            "warmup_items": args.warmup_items,
            "vision_tower_patched": vt_patched,
            "vision_tower_layer": args.vision_tower_layer if vt_patched else None,
            "vision_tower_keep_rate": args.vision_tower_keep_rate if vt_patched else None,
            "vision_tower_score_mode": args.vision_tower_score_mode if vt_patched else None,
            "rlt_config": (
                rlt_config.as_dict()
                if vt_patched and args.vision_tower_score_mode == "rlt_topk"
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
