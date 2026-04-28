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

from codec_through.answers import extract_choice
from codec_through.memory_guard import check_rss_guard, rss_mb
from codec_through.pruned_vision_tower import PruneConfig, patch_vision_tower

REPO_ROOT = Path(__file__).resolve().parents[1]
RUNNER_PATH = REPO_ROOT / "scripts" / "run_benchmark_track_a.py"
DEFAULT_MODEL_PATH = Path.home() / "models" / "gemma-4-e4b-it-4bit"
GEMMA_IMAGE_SIZE = 512
GEMMA_GRID_SHAPE = (16, 16)


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
) -> tuple[dict[str, Any], float, float]:
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
    return raw, decode_ms, processor_ms


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
    args = parser.parse_args()

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

    vt_patched = args.vision_tower_keep_rate < 1.0
    if vt_patched:
        patch_vision_tower(
            model,
            PruneConfig(
                layer_idx=args.vision_tower_layer,
                keep_rate=args.vision_tower_keep_rate,
            ),
        )

    if args.rss_guard_mb > 0:
        check_rss_guard(args.rss_guard_mb, stage="post_model_load")

    tokens_per_frame = GEMMA_GRID_SHAPE[0] * GEMMA_GRID_SHAPE[1]
    total_groups = args.frame_count * tokens_per_frame
    kept_per_frame = (
        max(1, int(tokens_per_frame * args.vision_tower_keep_rate))
        if vt_patched
        else tokens_per_frame
    )
    kept_groups = args.frame_count * kept_per_frame

    results: list[ItemResult] = []
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w") as handle:
        for item in items:
            raw, decode_ms, processor_ms = _prepare_item(
                runner,
                processor,
                item,
                frame_count=args.frame_count,
            )
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
            "vision_tower_patched": vt_patched,
            "vision_tower_layer": args.vision_tower_layer if vt_patched else None,
            "vision_tower_keep_rate": args.vision_tower_keep_rate if vt_patched else None,
            "rss_guard_mb": args.rss_guard_mb if args.rss_guard_mb > 0 else None,
            "final_rss_mb": rss_mb(),
        }
    )
    args.summary.parent.mkdir(parents=True, exist_ok=True)
    args.summary.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
