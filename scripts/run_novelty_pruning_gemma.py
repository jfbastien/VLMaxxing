#!/usr/bin/env python3
"""Phase 1.51R novelty-pruning on Gemma 4 for VideoMME (claim #11 big-numbers).

Drives the one end-to-end path that was not yet wired: decoded frames →
pixel-novelty → per-anchor-arm keep mask → shortened input_ids + gathered
visual features → mlx-vlm generate(). Because Gemma 4's vision tower runs
in full regardless, the ~1.8× speedup claim rests entirely on LLM-prefill
shortening (which phase 1.50 measured at 70-78% of end-to-end wall-clock
on Qwen 2.5-VL-7B-4bit at 8 frames × 560×560; Gemma's smaller vision
tower shifts the ratio further toward prefill-dominance).

Architecture:
- Loads Gemma 4 via ``mlx_vlm.load``.
- For each manifest item: decodes 8 frames uniformly, runs the processor
  to get the 280-placeholder-per-image ``input_ids`` (matches
  Gemma4Processor.image_seq_length=280), computes pixel novelty at 14×20,
  calls :func:`compute_keep_mask` per anchor arm, and then
  :func:`prune_image_placeholders` to shorten the prompt.
- Two generation paths run per item:
  * **dense baseline** — standard mlx-vlm generate() with no pruning,
    as the wall-clock reference.
  * **pruned** — shortened ``input_ids`` + ``cached_image_features`` that
    only contain the retained token indices.
- Records per-item wall-clock (prefill, generation, total) and accuracy.

Anchor-arm support in v0:
- ``none`` (top-K novelty) — no features needed.
- ``gemma_structural`` (corners + center) — positional only.
- ``nuwa_pillar`` — uses vision-tower output features.
- ``max_min_diversity`` — uses vision-tower output features.
- ``cls_attention`` — **NOT SUPPORTED in v0**. Requires Gemma vision-tower
  attention instrumentation that has not been landed. Use at your own risk.

Usage:
    uv run python scripts/run_novelty_pruning_gemma.py \\
        --manifest research/benchmark_manifests/videomme_dev_v1.toml \\
        --anchor-arm none --keep-rate 0.5 \\
        --output research/experiments/2026/artifacts/phase1_51R_dev/none_kr50.jsonl \\
        --summary research/experiments/2026/artifacts/phase1_51R_dev/none_kr50_summary.json

Preregistration:
    research/experiments/2026/2026-04-17-phase-1_51-novelty-pruning-gemma-prereg.md

Relationship to Qwen Track A:
This is a **fresh** driver — it does NOT reuse
``_mix_qwen_features`` / ``_mix_gemma_features`` / planner-based reuse.
1.51R is a frame-level LLM-prefill shortener, not a block-level temporal
router. The two mechanisms compose multiplicatively (that's phase 1.52)
but stay independent at the code level.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import time
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast

import av
import mlx.core as mx
import numpy as np
from mlx_vlm import generate, load  # type: ignore[import-untyped]
from mlx_vlm.utils import prepare_inputs  # type: ignore[import-untyped]
from PIL import Image

from codec_through.answers import extract_choice
from codec_through.novelty_pruning import (
    ANCHOR_ARMS,
    AnchorArm,
    NoveltyPruneConfig,
    compute_keep_mask,
    compute_pixel_novelty,
    prune_image_placeholders,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
RUNNER_PATH = REPO_ROOT / "scripts" / "run_benchmark_track_a.py"

DEFAULT_MODEL_PATH = Path.home() / "models" / "gemma-4-e4b-it-4bit"
GEMMA_IMAGE_SIZE = 224  # Gemma 4's processor hard-codes this (processor_config.json).
GEMMA_GRID_SHAPE = (14, 20)  # 14×20 = 280 soft tokens per image (image_seq_length).


def _load_runner_module() -> Any:
    name = "_gemma_novelty_runner"
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
class PrefillTiming:
    decode_ms: float
    novelty_ms: float
    mask_ms: float
    prune_ms: float
    vision_ms: float
    generate_ms: float
    total_ms: float


@dataclass(frozen=True, slots=True)
class ItemResult:
    item_id: str
    benchmark: str
    group: str
    anchor_arm: AnchorArm
    keep_rate: float
    n_frames: int
    tokens_per_frame: int
    kept_tokens_total: int
    kept_per_frame: list[int]
    dense_text: str
    pruned_text: str
    dense_correct: bool
    pruned_correct: bool
    dense_parse_failure: bool
    pruned_parse_failure: bool
    agreement: bool
    answer_index: int
    dense_choice: int | None
    pruned_choice: int | None
    dense_timing: PrefillTiming
    pruned_timing: PrefillTiming
    metadata: dict[str, Any] = field(default_factory=dict)


def _letterbox_224(frame: Image.Image) -> Image.Image:
    """Resize + center-pad to 224×224 (Gemma's native input size)."""
    width, height = frame.size
    scale = min(GEMMA_IMAGE_SIZE / width, GEMMA_IMAGE_SIZE / height)
    resized = frame.resize(
        (max(1, round(width * scale)), max(1, round(height * scale))),
        Image.Resampling.BICUBIC,
    )
    canvas = Image.new("RGB", (GEMMA_IMAGE_SIZE, GEMMA_IMAGE_SIZE), color=(0, 0, 0))
    offset_x = (GEMMA_IMAGE_SIZE - resized.width) // 2
    offset_y = (GEMMA_IMAGE_SIZE - resized.height) // 2
    canvas.paste(resized, (offset_x, offset_y))
    return canvas


def _decode_uniform_frames(
    video_path: Path,
    *,
    frame_count: int,
    start: float | None,
    end: float | None,
) -> tuple[list[Image.Image], np.ndarray]:
    """Decode the whole video, uniformly sample ``frame_count`` frames,
    letterbox each to 224×224, and return (PIL frames, float32 pixel stack)."""
    all_frames: list[Image.Image] = []
    with av.open(str(video_path)) as container:
        for frame in container.decode(video=0):
            timestamp = float(frame.time) if frame.time is not None else None
            if start is not None and timestamp is not None and timestamp < start:
                continue
            if end is not None and timestamp is not None and timestamp > end:
                break
            all_frames.append(frame.to_image().convert("RGB"))  # type: ignore[no-untyped-call]
    if len(all_frames) < frame_count:
        raise ValueError(f"video has {len(all_frames)} frames but requested {frame_count}")
    indices = np.linspace(0, len(all_frames) - 1, frame_count, dtype=int).tolist()
    selected = [_letterbox_224(all_frames[i]) for i in indices]
    stack = np.stack([np.asarray(f, dtype=np.float32) for f in selected], axis=0)
    return selected, stack


def _build_prompt(processor: Any, frames: list[Image.Image], question: str) -> dict[str, Any]:
    messages = [
        {
            "role": "user",
            "content": [*({"type": "image"} for _ in frames), {"type": "text", "text": question}],
        }
    ]
    rendered = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    raw = prepare_inputs(processor, images=frames, prompts=rendered)
    return raw


def _mean_token_attention_proxy(features: np.ndarray) -> np.ndarray:
    """Proxy CLS-attention: per-token L2 norm of vision features.

    Used only if the caller requests ``cls_attention`` before Gemma vision-
    tower attention instrumentation lands. Documented as a proxy; the
    results should not be treated as a faithful cls_attention measurement.
    """
    norms = np.linalg.norm(features, axis=-1)
    return norms.astype(np.float32)


def _run_generate(
    model: Any,
    processor: Any,
    *,
    input_ids: mx.array,
    pixel_values: mx.array,
    mask: mx.array,
    extra: dict[str, mx.array],
    cached_image_features: mx.array | None,
    max_tokens: int,
) -> tuple[str, float]:
    """Invoke mlx-vlm ``generate`` and return (text, wall_ms)."""
    t0 = time.perf_counter_ns()
    mx.random.seed(42)
    kwargs = dict(extra)
    if cached_image_features is not None:
        kwargs["cached_image_features"] = cached_image_features
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
    return str(response.text), elapsed_ms


def _compute_vision_features(model: Any, pixel_values: mx.array) -> mx.array:
    """Run Gemma's vision_tower + embed_vision to produce (1, F*280, hidden)."""
    features = model.vision_tower(pixel_values)
    features = model.embed_vision(features)
    mx.eval(features)
    return cast(mx.array, features)


def _process_one_item(
    model: Any,
    processor: Any,
    runner: Any,
    item: Any,
    *,
    anchor_arm: AnchorArm,
    keep_rate: float,
    frame_count: int,
    max_tokens: int,
) -> ItemResult:
    # --- Stage 1: decode ---
    t_stage = time.perf_counter_ns()
    frames, pixel_stack = _decode_uniform_frames(
        item.video_path,
        frame_count=frame_count,
        start=item.start_seconds,
        end=item.end_seconds,
    )
    decode_ms = (time.perf_counter_ns() - t_stage) / 1_000_000

    # --- Stage 2: processor → input_ids ---
    raw = _build_prompt(
        processor, frames, runner._multiple_choice_prompt(item.question, item.candidates)
    )
    input_ids_np = np.asarray(raw["input_ids"], dtype=np.int64).reshape(-1)
    pixel_values = mx.array(raw["pixel_values"])
    mask = mx.array(raw["attention_mask"])
    extra = {
        k: mx.array(v)
        for k, v in raw.items()
        if k not in {"input_ids", "pixel_values", "attention_mask"}
    }

    # --- Stage 3: novelty ---
    t_stage = time.perf_counter_ns()
    novelty = compute_pixel_novelty(pixel_stack, grid_shape=GEMMA_GRID_SHAPE)
    novelty_ms = (time.perf_counter_ns() - t_stage) / 1_000_000

    # --- Stage 4: vision encode (needed for both dense + feature-using arms) ---
    t_stage = time.perf_counter_ns()
    vision_features = _compute_vision_features(model, pixel_values)
    vision_ms = (time.perf_counter_ns() - t_stage) / 1_000_000
    vision_np = np.asarray(vision_features, dtype=np.float32)  # (1, F*280, hidden)
    hidden = vision_np.shape[-1]
    per_token_features = vision_np.reshape(
        frame_count, GEMMA_GRID_SHAPE[0] * GEMMA_GRID_SHAPE[1], hidden
    )

    # --- Stage 5: keep mask ---
    t_stage = time.perf_counter_ns()
    cfg = NoveltyPruneConfig(
        anchor_arm=anchor_arm,
        keep_rate=keep_rate,
        grid_shape=GEMMA_GRID_SHAPE,
    )
    cls_proxy = None
    if anchor_arm == "cls_attention":
        cls_proxy = _mean_token_attention_proxy(per_token_features)
    keep_mask = compute_keep_mask(
        novelty,
        config=cfg,
        features=per_token_features if anchor_arm in ("nuwa_pillar", "max_min_diversity") else None,
        cls_attention=cls_proxy,
    )
    mask_ms = (time.perf_counter_ns() - t_stage) / 1_000_000

    # --- Stage 6: prune input_ids + gather features ---
    t_stage = time.perf_counter_ns()
    image_token_id = int(model.config.image_token_id)
    pruned = prune_image_placeholders(input_ids_np, keep_mask, image_token_id=image_token_id)
    pruned_input_ids = mx.array(pruned.input_ids[None, :])  # (1, new_seq_len)
    gathered_features = vision_features[:, mx.array(pruned.feature_indices), :]
    mx.eval(gathered_features)
    prune_ms = (time.perf_counter_ns() - t_stage) / 1_000_000

    # --- Stage 7: dense baseline generate ---
    dense_input_ids = mx.array(raw["input_ids"])
    t_stage = time.perf_counter_ns()
    dense_text, dense_generate_ms = _run_generate(
        model,
        processor,
        input_ids=dense_input_ids,
        pixel_values=pixel_values,
        mask=mask,
        extra=extra,
        cached_image_features=vision_features,
        max_tokens=max_tokens,
    )
    dense_total_ms = (time.perf_counter_ns() - t_stage) / 1_000_000

    # --- Stage 8: pruned generate ---
    # Pruned mask: same attention_mask slots minus the dropped image positions.
    # We regenerate the mask by taking the attention_mask row and selecting kept columns.
    attn_np = np.asarray(raw["attention_mask"], dtype=np.int32).reshape(-1)
    # Boolean selector for kept tokens: non-image tokens always kept; image tokens per keep_mask.
    image_token_positions = np.asarray(input_ids_np == image_token_id)
    placeholder_keep = np.zeros(input_ids_np.shape[0], dtype=bool)
    flat_keep = keep_mask.reshape(-1)
    placeholder_keep[image_token_positions] = flat_keep
    survivor = np.where(image_token_positions, placeholder_keep, True)
    pruned_attn = attn_np[survivor]
    pruned_mask = mx.array(pruned_attn[None, :])

    t_stage = time.perf_counter_ns()
    pruned_text, pruned_generate_ms = _run_generate(
        model,
        processor,
        input_ids=pruned_input_ids,
        pixel_values=pixel_values,
        mask=pruned_mask,
        extra=extra,
        cached_image_features=gathered_features,
        max_tokens=max_tokens,
    )
    pruned_total_ms = (time.perf_counter_ns() - t_stage) / 1_000_000

    dense_choice = extract_choice(dense_text, item.candidates)
    pruned_choice = extract_choice(pruned_text, item.candidates)
    dense_parse_failure = dense_choice is None
    pruned_parse_failure = pruned_choice is None

    return ItemResult(
        item_id=item.item_id,
        benchmark=item.benchmark,
        group=item.group,
        anchor_arm=anchor_arm,
        keep_rate=keep_rate,
        n_frames=frame_count,
        tokens_per_frame=GEMMA_GRID_SHAPE[0] * GEMMA_GRID_SHAPE[1],
        kept_tokens_total=int(keep_mask.sum()),
        kept_per_frame=pruned.kept_per_frame.tolist(),
        dense_text=dense_text,
        pruned_text=pruned_text,
        dense_correct=(dense_choice is not None and dense_choice == item.answer_index),
        pruned_correct=(pruned_choice is not None and pruned_choice == item.answer_index),
        dense_parse_failure=dense_parse_failure,
        pruned_parse_failure=pruned_parse_failure,
        agreement=(
            dense_choice is not None and pruned_choice is not None and dense_choice == pruned_choice
        ),
        answer_index=item.answer_index,
        dense_choice=dense_choice,
        pruned_choice=pruned_choice,
        dense_timing=PrefillTiming(
            decode_ms=decode_ms,
            novelty_ms=0.0,
            mask_ms=0.0,
            prune_ms=0.0,
            vision_ms=vision_ms,
            generate_ms=dense_generate_ms,
            total_ms=dense_total_ms,
        ),
        pruned_timing=PrefillTiming(
            decode_ms=decode_ms,
            novelty_ms=novelty_ms,
            mask_ms=mask_ms,
            prune_ms=prune_ms,
            vision_ms=vision_ms,
            generate_ms=pruned_generate_ms,
            total_ms=pruned_total_ms,
        ),
    )


def _summarize(records: list[ItemResult]) -> dict[str, Any]:
    if not records:
        return {"n_items": 0}
    dense_acc = sum(1 for r in records if r.dense_correct) / len(records)
    pruned_acc = sum(1 for r in records if r.pruned_correct) / len(records)
    agreement = sum(1 for r in records if r.agreement) / len(records)
    mean_kept = float(np.mean([r.kept_tokens_total for r in records]))
    dense_generate_ms = [r.dense_timing.generate_ms for r in records]
    pruned_generate_ms = [r.pruned_timing.generate_ms for r in records]
    speedup = (
        float(np.mean(dense_generate_ms) / np.mean(pruned_generate_ms))
        if pruned_generate_ms and np.mean(pruned_generate_ms) > 0
        else 0.0
    )
    return {
        "n_items": len(records),
        "dense_accuracy": dense_acc,
        "pruned_accuracy": pruned_acc,
        "agreement": agreement,
        "mean_kept_tokens_total": mean_kept,
        "tokens_per_frame_baseline": records[0].tokens_per_frame,
        "n_frames": records[0].n_frames,
        "effective_keep_ratio": mean_kept / (records[0].n_frames * records[0].tokens_per_frame),
        "mean_dense_generate_ms": float(np.mean(dense_generate_ms)),
        "mean_pruned_generate_ms": float(np.mean(pruned_generate_ms)),
        "median_dense_generate_ms": float(np.median(dense_generate_ms)),
        "median_pruned_generate_ms": float(np.median(pruned_generate_ms)),
        "generate_speedup_mean": speedup,
        "mean_dense_vision_ms": float(np.mean([r.dense_timing.vision_ms for r in records])),
        "dense_parse_failures": sum(1 for r in records if r.dense_parse_failure),
        "pruned_parse_failures": sum(1 for r in records if r.pruned_parse_failure),
    }


def _load_manifest_items(runner: Any, manifest_path: Path) -> list[Any]:
    payload = tomllib.loads(manifest_path.read_text())
    benchmark = payload["benchmark"]
    item_ids = payload["item_ids"]
    return runner._load_items_by_id(benchmark, item_ids)


def _record_payload(record: ItemResult) -> dict[str, Any]:
    return {
        "item_id": record.item_id,
        "benchmark": record.benchmark,
        "group": record.group,
        "anchor_arm": record.anchor_arm,
        "keep_rate": record.keep_rate,
        "n_frames": record.n_frames,
        "tokens_per_frame": record.tokens_per_frame,
        "kept_tokens_total": record.kept_tokens_total,
        "kept_per_frame": record.kept_per_frame,
        "dense_text": record.dense_text,
        "pruned_text": record.pruned_text,
        "dense_correct": record.dense_correct,
        "pruned_correct": record.pruned_correct,
        "dense_parse_failure": record.dense_parse_failure,
        "pruned_parse_failure": record.pruned_parse_failure,
        "agreement": record.agreement,
        "answer_index": record.answer_index,
        "dense_choice": record.dense_choice,
        "pruned_choice": record.pruned_choice,
        "dense_timing_ms": {
            "decode": record.dense_timing.decode_ms,
            "vision": record.dense_timing.vision_ms,
            "generate": record.dense_timing.generate_ms,
            "total": record.dense_timing.total_ms,
        },
        "pruned_timing_ms": {
            "decode": record.pruned_timing.decode_ms,
            "novelty": record.pruned_timing.novelty_ms,
            "mask": record.pruned_timing.mask_ms,
            "prune": record.pruned_timing.prune_ms,
            "vision": record.pruned_timing.vision_ms,
            "generate": record.pruned_timing.generate_ms,
            "total": record.pruned_timing.total_ms,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--n-items", type=int, default=0, help="Cap items (0 = all)")
    parser.add_argument("--frame-count", type=int, default=8)
    parser.add_argument(
        "--anchor-arm",
        type=str,
        choices=list(ANCHOR_ARMS),
        required=True,
    )
    parser.add_argument("--keep-rate", type=float, required=True)
    parser.add_argument("--max-tokens", type=int, default=32)
    parser.add_argument("--model-path", type=Path, default=DEFAULT_MODEL_PATH)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    args = parser.parse_args()

    if not args.model_path.exists():
        raise SystemExit(f"model path missing: {args.model_path}")
    if args.anchor_arm == "cls_attention":
        print(
            "WARNING: cls_attention v0 uses a per-token L2-norm proxy; not a "
            "faithful attention signal. Gate any promotion on Gemma attention "
            "instrumentation landing.",
            file=sys.stderr,
        )

    runner = _load_runner_module()
    items = _load_manifest_items(runner, args.manifest)
    if not items:
        raise SystemExit("no items loaded from manifest")
    if args.n_items > 0:
        items = items[: args.n_items]

    print(f"loading model: {args.model_path}")
    model, processor = load(str(args.model_path))

    args.output.parent.mkdir(parents=True, exist_ok=True)
    records: list[ItemResult] = []
    with args.output.open("w") as out_f:
        for idx, item in enumerate(items):
            try:
                record = _process_one_item(
                    model,
                    processor,
                    runner,
                    item,
                    anchor_arm=cast(AnchorArm, args.anchor_arm),
                    keep_rate=args.keep_rate,
                    frame_count=args.frame_count,
                    max_tokens=args.max_tokens,
                )
            except Exception as exc:
                print(f"[{idx + 1}/{len(items)}] {item.item_id}: FAILED {exc!r}", file=sys.stderr)
                raise
            records.append(record)
            out_f.write(json.dumps(_record_payload(record)) + "\n")
            out_f.flush()
            print(
                f"[{idx + 1:3d}/{len(items)}] {item.item_id:<40s} "
                f"dense={record.dense_correct} pruned={record.pruned_correct} "
                f"agree={record.agreement} "
                f"kept={record.kept_tokens_total}/"
                f"{record.n_frames * record.tokens_per_frame} "
                f"dense_gen={record.dense_timing.generate_ms:.0f}ms "
                f"pruned_gen={record.pruned_timing.generate_ms:.0f}ms"
            )

    summary = {
        "manifest": str(args.manifest),
        "model_path": str(args.model_path),
        "anchor_arm": args.anchor_arm,
        "keep_rate": args.keep_rate,
        "frame_count": args.frame_count,
        "max_tokens": args.max_tokens,
        **_summarize(records),
    }
    args.summary.parent.mkdir(parents=True, exist_ok=True)
    args.summary.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")

    print(
        f"\n=== 1.51R {args.anchor_arm} keep_rate={args.keep_rate} "
        f"dense_acc={summary.get('dense_accuracy', 0):.3f} "
        f"pruned_acc={summary.get('pruned_accuracy', 0):.3f} "
        f"agreement={summary.get('agreement', 0):.3f} "
        f"generate_speedup={summary.get('generate_speedup_mean', 0):.2f}×"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
