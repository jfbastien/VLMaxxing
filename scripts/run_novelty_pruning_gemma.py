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
  to get the 256-placeholder-per-image ``input_ids`` (runtime-verified
  2026-04-18 as 16×16, NOT the stale 280/14×20 that
  ``Gemma4Processor.image_seq_length`` advertises), computes pixel novelty
  at 16×16, calls :func:`compute_keep_mask` per anchor arm, and then
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
- ``cls_attention_proxy`` — **NOT a faithful attention measurement**.
  v0 substitutes a per-token L2-norm signal because real Gemma vision-tower
  attention instrumentation has not landed. Results from this arm are
  **excluded from winner promotion** (see PROMOTABLE_ARMS in
  src/codec_through/novelty_pruning.py). Kept in the grid to anchor the
  literature baseline and to sanity-check the proxy itself.

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
import gc
import importlib.util
import json
import sys
import time
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast

import mlx.core as mx
import numpy as np
from mlx_vlm import generate, load  # type: ignore[import-untyped]
from mlx_vlm.utils import prepare_inputs  # type: ignore[import-untyped]
from PIL import Image

from codec_through.answers import extract_choice
from codec_through.memory_guard import check_rss_guard, rss_mb
from codec_through.novelty_pruning import (
    ANCHOR_ARMS,
    AnchorArm,
    NoveltyPruneConfig,
    compute_keep_mask,
    compute_pixel_novelty,
    prune_image_placeholders,
)
from codec_through.video_decode import decode_uniform_frames

REPO_ROOT = Path(__file__).resolve().parents[1]
RUNNER_PATH = REPO_ROOT / "scripts" / "run_benchmark_track_a.py"

DEFAULT_MODEL_PATH = Path.home() / "models" / "gemma-4-e4b-it-4bit"
# 512×512 is divisible by 16 (the observed post-pool grid side). The earlier
# 224 constant was indivisible by 20 (the pre-2026-04-18 assumed grid side);
# 560 was divisible by both 14 and 20 but not by 16, so with the now-corrected
# grid of (16, 16) it would again fail the divisibility check in
# compute_pixel_novelty. 2026-04-18 runtime probe on
# mlx-community/gemma-4-e4b-it-4bit: `prepare_inputs` emits exactly 256
# placeholders per image across two frames in two separate runs — that is 16×16,
# not the 14×20 (= 280) that `processor.image_seq_length` reports. The attribute
# is stale / decorative; trust the observed emission.
GEMMA_IMAGE_SIZE = 512
GEMMA_GRID_SHAPE = (16, 16)  # 256 soft tokens per image, runtime-verified.
# Anchor arms that actually need per-token vision features. Others skip the
# (1, F*280, hidden) host-float32 mirror, which saved ~1–2 GB per item on the
# 2026-04-18 OOM repro without changing any science.
_FEATURE_DEPENDENT_ARMS: frozenset[AnchorArm] = frozenset(
    {"nuwa_pillar", "max_min_diversity", "cls_attention_proxy"}
)


def _clear_runtime_state() -> None:
    """Release MLX cache + Python GC between back-to-back generate() calls.

    Observed 2026-04-18: without this, peak RSS during the second (pruned)
    generate included prefill + kv-cache tensors from the first (dense)
    generate still in the MLX allocator pool. Matches the cleanup pattern
    in scripts/run_benchmark_track_a.py:1083 which this driver had been
    missing.
    """
    gc.collect()
    mx.clear_cache()


def _log_model_weight_summary(model: Any) -> None:
    """Print a summary of loaded weight dtypes so quantized-vs-fallback load
    is measurable rather than guessed.

    Codex round-21 post-mortem noted that the driver silently accepted
    whatever ``mlx_vlm.load`` returned. If a path mis-names a 4-bit model
    and load() falls back to float16, the model is ~2× larger than
    expected and the OOM blame lands in the wrong place. A cheap dtype
    histogram at load time lets future debugging start from evidence.
    """
    try:
        from collections import Counter

        dtype_counts: Counter[str] = Counter()
        total_params = 0
        for _, weight in model.parameters().items() if hasattr(model, "parameters") else []:
            if isinstance(weight, mx.array):
                dtype_counts[str(weight.dtype)] += 1
                total_params += int(np.prod(weight.shape))
        if dtype_counts:
            summary = ", ".join(f"{k}={v}" for k, v in dtype_counts.most_common())
            print(f"[model weight dtypes] {summary}; total_params={total_params:,}")
        else:
            print("[model weight dtypes] unavailable (model.parameters() returned empty)")
    except Exception as exc:  # noqa: BLE001 — diagnostic-only, must never fail the run
        print(f"[model weight dtypes] probe failed: {exc!r}")


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
class StageTimings:
    """Per-branch wall-clock breakdown in milliseconds.

    ``end_to_end_ms`` is the headline: wall-clock from video-path handoff
    through final generated text, summing all stages that actually ran on
    this branch. Use this for the Sam-whitepaper ≥ 1.8× speedup claim;
    ``generate_ms`` alone understates the denominator (it misses decode,
    processor, novelty, vision, mask, prune). Reporting both lets us
    separate "how much we save on generate" from "how much we save
    end-to-end after paying the overhead of pruning itself."
    """

    decode_ms: float
    processor_ms: float
    novelty_ms: float
    mask_ms: float
    prune_ms: float
    vision_ms: float
    generate_ms: float
    end_to_end_ms: float


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
    dense_timing: StageTimings
    pruned_timing: StageTimings
    dense_prompt_tokens: int = 0
    pruned_prompt_tokens: int = 0
    dense_generation_tokens: int = 0
    pruned_generation_tokens: int = 0
    dense_prompt_tps: float = 0.0
    pruned_prompt_tps: float = 0.0
    dense_generation_tps: float = 0.0
    pruned_generation_tps: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


def _letterbox_square(frame: Image.Image, size: int = GEMMA_IMAGE_SIZE) -> Image.Image:
    """Resize + center-pad to ``size``×``size`` preserving aspect ratio."""
    width, height = frame.size
    scale = min(size / width, size / height)
    resized = frame.resize(
        (max(1, round(width * scale)), max(1, round(height * scale))),
        Image.Resampling.BICUBIC,
    )
    canvas = Image.new("RGB", (size, size), color=(0, 0, 0))
    offset_x = (size - resized.width) // 2
    offset_y = (size - resized.height) // 2
    canvas.paste(resized, (offset_x, offset_y))
    return canvas


def _decode_and_letterbox(
    video_path: Path,
    *,
    frame_count: int,
    start: float | None,
    end: float | None,
) -> tuple[list[Image.Image], np.ndarray]:
    """Decode ``frame_count`` uniformly-spaced frames, letterbox to the Gemma
    square, and return (PIL frames, float32 pixel stack).

    Memory is O(frame_count). The previous implementation buffered every
    decoded frame into a Python list before subsampling, which blew past
    50 GB RSS on a 15-min VideoMME clip (2026-04-18 OOM). The shared utility
    in :mod:`codec_through.video_decode` never materializes non-target
    frames.
    """
    selected = decode_uniform_frames(
        video_path,
        frame_count=frame_count,
        start_seconds=start,
        end_seconds=end,
    )
    letterboxed = [_letterbox_square(f) for f in selected]
    stack = np.stack([np.asarray(f, dtype=np.float32) for f in letterboxed], axis=0)
    return letterboxed, stack


def _build_prompt(processor: Any, frames: list[Image.Image], question: str) -> dict[str, Any]:
    messages = [
        {
            "role": "user",
            "content": [*({"type": "image"} for _ in frames), {"type": "text", "text": question}],
        }
    ]
    rendered = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    raw = prepare_inputs(processor, images=frames, prompts=rendered)
    return cast(dict[str, Any], raw)


def _mean_token_attention_proxy(features: np.ndarray) -> np.ndarray:
    """Proxy CLS-attention: per-token L2 norm of vision features.

    Used only if the caller requests ``cls_attention_proxy`` before Gemma vision-
    tower attention instrumentation lands. Documented as a proxy; the
    results should not be treated as a faithful cls_attention measurement.
    """
    norms = np.linalg.norm(features, axis=-1)
    return cast(np.ndarray, norms.astype(np.float32))


@dataclass(frozen=True, slots=True)
class GenerateStats:
    """Generation metrics returned by mlx-vlm that are orthogonal to our
    stage timings. Used to disentangle prefill-attention savings from
    differential generation length (task #89 confound, 2026-04-18).
    """

    text: str
    elapsed_ms: float
    prompt_tokens: int
    generation_tokens: int
    prompt_tps: float
    generation_tps: float


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
) -> GenerateStats:
    """Invoke mlx-vlm ``generate`` and return generation stats + wall_ms."""
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
    return GenerateStats(
        text=str(response.text),
        elapsed_ms=elapsed_ms,
        prompt_tokens=int(getattr(response, "prompt_tokens", 0)),
        generation_tokens=int(getattr(response, "generation_tokens", 0)),
        prompt_tps=float(getattr(response, "prompt_tps", 0.0)),
        generation_tps=float(getattr(response, "generation_tps", 0.0)),
    )


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
    # Shared: both branches pay this cost once per item (the frames are the
    # same input stream regardless of whether we prune). Attributed to both
    # end_to_end sums below so the headline speedup is apples-to-apples.
    t_stage = time.perf_counter_ns()
    frames, pixel_stack = _decode_and_letterbox(
        item.video_path,
        frame_count=frame_count,
        start=item.start_seconds,
        end=item.end_seconds,
    )
    decode_ms = (time.perf_counter_ns() - t_stage) / 1_000_000

    # --- Stage 2: processor (tokenize + pixel prep) ---
    # Shared: the processor output feeds both branches. Timing this explicitly
    # so the dense end-to-end isn't under-reported — codex round-19 flagged
    # that previously-untimed stages hid overhead the pruned branch actually
    # pays.
    t_stage = time.perf_counter_ns()
    raw = _build_prompt(
        processor, frames, runner._multiple_choice_prompt(item.question, item.candidates)
    )
    processor_ms = (time.perf_counter_ns() - t_stage) / 1_000_000
    input_ids_np = np.asarray(raw["input_ids"], dtype=np.int64).reshape(-1)
    image_token_id_check = int(model.config.image_token_id)
    observed_placeholders = int((input_ids_np == image_token_id_check).sum())
    expected_placeholders = frame_count * GEMMA_GRID_SHAPE[0] * GEMMA_GRID_SHAPE[1]
    if observed_placeholders != expected_placeholders:
        raise RuntimeError(
            f"Gemma placeholder-count mismatch: processor emitted"
            f" {observed_placeholders} image-tokens for {frame_count} frames,"
            f" driver assumed {expected_placeholders}"
            f" (F={frame_count} × grid {GEMMA_GRID_SHAPE[0]}×{GEMMA_GRID_SHAPE[1]}"
            f" = {GEMMA_GRID_SHAPE[0] * GEMMA_GRID_SHAPE[1]}/frame). Adjust"
            f" GEMMA_GRID_SHAPE to match the observed emission before running"
            f" the pilot."
        )
    pixel_values = mx.array(raw["pixel_values"])
    mask = mx.array(raw["attention_mask"])
    extra = {
        k: mx.array(v)
        for k, v in raw.items()
        if k not in {"input_ids", "pixel_values", "attention_mask"}
    }

    # --- Stage 3: novelty (pruned branch only) ---
    t_stage = time.perf_counter_ns()
    novelty = compute_pixel_novelty(pixel_stack, grid_shape=GEMMA_GRID_SHAPE)
    novelty_ms = (time.perf_counter_ns() - t_stage) / 1_000_000

    # --- Stage 4: vision encode (shared; both branches need embeddings) ---
    t_stage = time.perf_counter_ns()
    vision_features = _compute_vision_features(model, pixel_values)
    vision_ms = (time.perf_counter_ns() - t_stage) / 1_000_000

    # --- Stage 5: keep mask (pruned branch only) ---
    # Only feature-dependent arms pay the host float32 mirror of the full
    # (1, F*280, hidden) tensor. For ``none`` and ``gemma_structural`` the
    # mirror is ~60 MB of wasted memory per item (Gemma 4's hidden ≈ 2560
    # at F=8). Gating it here cost 0 information and was flagged by codex
    # as part of the 2026-04-18 OOM post-mortem.
    t_stage = time.perf_counter_ns()
    per_token_features: np.ndarray | None = None
    cls_proxy = None
    if anchor_arm in _FEATURE_DEPENDENT_ARMS:
        vision_np = np.asarray(vision_features, dtype=np.float32)
        hidden = vision_np.shape[-1]
        per_token_features = vision_np.reshape(
            frame_count, GEMMA_GRID_SHAPE[0] * GEMMA_GRID_SHAPE[1], hidden
        )
        del vision_np
        if anchor_arm == "cls_attention_proxy":
            cls_proxy = _mean_token_attention_proxy(per_token_features)
    cfg = NoveltyPruneConfig(
        anchor_arm=anchor_arm,
        keep_rate=keep_rate,
        grid_shape=GEMMA_GRID_SHAPE,
    )
    keep_mask = compute_keep_mask(
        novelty,
        config=cfg,
        features=per_token_features if anchor_arm in ("nuwa_pillar", "max_min_diversity") else None,
        cls_attention=cls_proxy,
    )
    mask_ms = (time.perf_counter_ns() - t_stage) / 1_000_000

    # --- Stage 6: prune input_ids + gather features (pruned branch only) ---
    t_stage = time.perf_counter_ns()
    image_token_id = int(model.config.image_token_id)
    pruned = prune_image_placeholders(input_ids_np, keep_mask, image_token_id=image_token_id)
    pruned_input_ids = mx.array(pruned.input_ids[None, :])  # (1, new_seq_len)
    gathered_features = vision_features[:, mx.array(pruned.feature_indices), :]
    mx.eval(gathered_features)
    prune_ms = (time.perf_counter_ns() - t_stage) / 1_000_000

    # --- Stage 7: dense baseline generate ---
    dense_input_ids = mx.array(raw["input_ids"])
    dense_stats = _run_generate(
        model,
        processor,
        input_ids=dense_input_ids,
        pixel_values=pixel_values,
        mask=mask,
        extra=extra,
        cached_image_features=vision_features,
        max_tokens=max_tokens,
    )
    dense_text = dense_stats.text
    dense_generate_ms = dense_stats.elapsed_ms
    # Release MLX kv-cache + Python refs before the pruned pass. Without this,
    # the 2026-04-18 pilot had both generate() branches' prefill tensors
    # resident simultaneously on a 16 GB Mac — peak RSS exceeded 50 GB.
    _clear_runtime_state()

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

    pruned_stats = _run_generate(
        model,
        processor,
        input_ids=pruned_input_ids,
        pixel_values=pixel_values,
        mask=pruned_mask,
        extra=extra,
        cached_image_features=gathered_features,
        max_tokens=max_tokens,
    )
    pruned_text = pruned_stats.text
    pruned_generate_ms = pruned_stats.elapsed_ms

    # End-to-end wall-clocks. Both branches pay decode + processor + vision +
    # generate; only the pruned branch pays novelty + mask + prune. Dense does
    # NOT pay novelty/mask/prune, so attributing those to dense_end_to_end
    # would inflate dense's denominator and deflate the speedup. Keep each
    # branch's end_to_end sum restricted to stages that branch actually ran.
    dense_end_to_end_ms = decode_ms + processor_ms + vision_ms + dense_generate_ms
    pruned_end_to_end_ms = (
        decode_ms + processor_ms + novelty_ms + vision_ms + mask_ms + prune_ms + pruned_generate_ms
    )

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
        dense_timing=StageTimings(
            decode_ms=decode_ms,
            processor_ms=processor_ms,
            novelty_ms=0.0,
            mask_ms=0.0,
            prune_ms=0.0,
            vision_ms=vision_ms,
            generate_ms=dense_generate_ms,
            end_to_end_ms=dense_end_to_end_ms,
        ),
        pruned_timing=StageTimings(
            decode_ms=decode_ms,
            processor_ms=processor_ms,
            novelty_ms=novelty_ms,
            mask_ms=mask_ms,
            prune_ms=prune_ms,
            vision_ms=vision_ms,
            generate_ms=pruned_generate_ms,
            end_to_end_ms=pruned_end_to_end_ms,
        ),
        dense_prompt_tokens=dense_stats.prompt_tokens,
        pruned_prompt_tokens=pruned_stats.prompt_tokens,
        dense_generation_tokens=dense_stats.generation_tokens,
        pruned_generation_tokens=pruned_stats.generation_tokens,
        dense_prompt_tps=dense_stats.prompt_tps,
        pruned_prompt_tps=pruned_stats.prompt_tps,
        dense_generation_tps=dense_stats.generation_tps,
        pruned_generation_tps=pruned_stats.generation_tps,
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
    dense_e2e_ms = [r.dense_timing.end_to_end_ms for r in records]
    pruned_e2e_ms = [r.pruned_timing.end_to_end_ms for r in records]
    generate_speedup = (
        float(np.mean(dense_generate_ms) / np.mean(pruned_generate_ms))
        if pruned_generate_ms and np.mean(pruned_generate_ms) > 0
        else 0.0
    )
    # HEADLINE: end-to-end wall-clock speedup — this is the claim-#11 metric.
    # Includes novelty + mask + prune overhead on the pruned branch so the
    # ratio is apples-to-apples against dense's decode+processor+vision+
    # generate. Codex round-19 flagged that the previous single "speedup"
    # metric (now exposed as `generate_speedup_mean`) understated the pruned
    # denominator and would over-report the headline by the ratio of generate
    # time to end-to-end time.
    end_to_end_speedup = (
        float(np.mean(dense_e2e_ms) / np.mean(pruned_e2e_ms))
        if pruned_e2e_ms and np.mean(pruned_e2e_ms) > 0
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
        "generate_speedup_mean": generate_speedup,
        "mean_dense_end_to_end_ms": float(np.mean(dense_e2e_ms)),
        "mean_pruned_end_to_end_ms": float(np.mean(pruned_e2e_ms)),
        "median_dense_end_to_end_ms": float(np.median(dense_e2e_ms)),
        "median_pruned_end_to_end_ms": float(np.median(pruned_e2e_ms)),
        "end_to_end_speedup_mean": end_to_end_speedup,
        "mean_decode_ms": float(np.mean([r.dense_timing.decode_ms for r in records])),
        "mean_processor_ms": float(np.mean([r.dense_timing.processor_ms for r in records])),
        "mean_dense_vision_ms": float(np.mean([r.dense_timing.vision_ms for r in records])),
        "mean_pruned_novelty_ms": float(np.mean([r.pruned_timing.novelty_ms for r in records])),
        "mean_pruned_mask_ms": float(np.mean([r.pruned_timing.mask_ms for r in records])),
        "mean_pruned_prune_ms": float(np.mean([r.pruned_timing.prune_ms for r in records])),
        "dense_parse_failures": sum(1 for r in records if r.dense_parse_failure),
        "pruned_parse_failures": sum(1 for r in records if r.pruned_parse_failure),
        "mean_dense_prompt_tokens": float(np.mean([r.dense_prompt_tokens for r in records])),
        "mean_pruned_prompt_tokens": float(np.mean([r.pruned_prompt_tokens for r in records])),
        "mean_dense_generation_tokens": float(np.mean([r.dense_generation_tokens for r in records])),
        "mean_pruned_generation_tokens": float(np.mean([r.pruned_generation_tokens for r in records])),
        "mean_dense_generation_tps": float(np.mean([r.dense_generation_tps for r in records])),
        "mean_pruned_generation_tps": float(np.mean([r.pruned_generation_tps for r in records])),
        # Per-token generation speedup, corrected for differential token count.
        # Total generate wall-clock / total tokens generated, dense vs pruned.
        # This is the "pure prefill-attention" effect — the raw generate_speedup
        # conflates this with differential generation length (task #89 confound).
        "per_token_generate_speedup_mean": _per_token_speedup(records),
    }


def _per_token_speedup(records: list[ItemResult]) -> float:
    dense_tok = float(sum(r.dense_generation_tokens for r in records))
    pruned_tok = float(sum(r.pruned_generation_tokens for r in records))
    dense_ms = float(sum(r.dense_timing.generate_ms for r in records))
    pruned_ms = float(sum(r.pruned_timing.generate_ms for r in records))
    if dense_tok <= 0 or pruned_tok <= 0 or pruned_ms <= 0:
        return 0.0
    dense_ms_per_tok = dense_ms / dense_tok
    pruned_ms_per_tok = pruned_ms / pruned_tok
    return dense_ms_per_tok / pruned_ms_per_tok if pruned_ms_per_tok > 0 else 0.0


def _load_manifest_items(runner: Any, manifest_path: Path) -> list[Any]:
    payload = tomllib.loads(manifest_path.read_text())
    benchmark = payload["benchmark"]
    item_ids = payload["item_ids"]
    return cast(list[Any], runner._load_items_by_id(benchmark, item_ids))


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
            "processor": record.dense_timing.processor_ms,
            "vision": record.dense_timing.vision_ms,
            "generate": record.dense_timing.generate_ms,
            "end_to_end": record.dense_timing.end_to_end_ms,
        },
        "pruned_timing_ms": {
            "decode": record.pruned_timing.decode_ms,
            "processor": record.pruned_timing.processor_ms,
            "novelty": record.pruned_timing.novelty_ms,
            "mask": record.pruned_timing.mask_ms,
            "prune": record.pruned_timing.prune_ms,
            "vision": record.pruned_timing.vision_ms,
            "generate": record.pruned_timing.generate_ms,
            "end_to_end": record.pruned_timing.end_to_end_ms,
        },
        "dense_prompt_tokens": record.dense_prompt_tokens,
        "pruned_prompt_tokens": record.pruned_prompt_tokens,
        "dense_generation_tokens": record.dense_generation_tokens,
        "pruned_generation_tokens": record.pruned_generation_tokens,
        "dense_prompt_tps": record.dense_prompt_tps,
        "pruned_prompt_tps": record.pruned_prompt_tps,
        "dense_generation_tps": record.dense_generation_tps,
        "pruned_generation_tps": record.pruned_generation_tps,
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
    parser.add_argument(
        "--rss-guard-mb",
        type=int,
        default=0,
        help=(
            "If non-zero, abort with a non-zero exit if resident-set size "
            "(in MiB) exceeds this value after model load or after any item. "
            "Safety net against a 2026-04-18-style 50GB OOM. Default 0 = off."
        ),
    )
    args = parser.parse_args()

    if not args.model_path.exists():
        raise SystemExit(f"model path missing: {args.model_path}")
    if args.anchor_arm == "cls_attention_proxy":
        print(
            "WARNING: cls_attention_proxy uses a per-token L2-norm proxy, not "
            "real first-layer attention. This arm is EXCLUDED from winner "
            "promotion (see PROMOTABLE_ARMS in codec_through.novelty_pruning). "
            "Re-enable promotion only after Gemma vision-tower attention "
            "instrumentation is landed.",
            file=sys.stderr,
        )

    runner = _load_runner_module()
    items = _load_manifest_items(runner, args.manifest)
    if not items:
        raise SystemExit("no items loaded from manifest")
    if args.n_items > 0:
        items = items[: args.n_items]

    print(f"loading model: {args.model_path}")
    print(f"[rss before load] {rss_mb():.0f} MiB")
    model, processor = load(str(args.model_path))
    _log_model_weight_summary(model)
    print(f"[rss after load] {rss_mb():.0f} MiB")
    check_rss_guard(args.rss_guard_mb, stage="after_model_load")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    records: list[ItemResult] = []
    with args.output.open("w") as out_f:
        for idx, item in enumerate(items):
            _clear_runtime_state()
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
                f"dense_e2e={record.dense_timing.end_to_end_ms:.0f}ms "
                f"pruned_e2e={record.pruned_timing.end_to_end_ms:.0f}ms "
                f"dense_gen={record.dense_timing.generate_ms:.0f}ms "
                f"pruned_gen={record.pruned_timing.generate_ms:.0f}ms "
                f"dense_toks={record.dense_generation_tokens} "
                f"pruned_toks={record.pruned_generation_tokens} "
                f"rss={rss_mb():.0f}MiB"
            )
            check_rss_guard(args.rss_guard_mb, stage=f"after_item_{idx + 1}")

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
        f"end_to_end_speedup={summary.get('end_to_end_speedup_mean', 0):.2f}× "
        f"(generate_only={summary.get('generate_speedup_mean', 0):.2f}×)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
