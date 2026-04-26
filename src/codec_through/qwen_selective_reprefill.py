"""Qwen-specific helpers for selective re-prefill experiments.

The stock mlx-vlm prompt-cache path only knows how to trim token ids. That is
fine for full-prefix reuse, but not for partial multimodal reuse where the
shared prefix ends inside the image block. This module keeps the dangerous
geometry and cache math explicit and reusable.
"""

from __future__ import annotations

import time
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, cast

import mlx.core as mx
import numpy as np
from mlx_lm.models.cache import trim_prompt_cache
from mlx_vlm.generate import make_sampler
from mlx_vlm.models.cache import make_prompt_cache


@dataclass(frozen=True, slots=True)
class QwenReprefillPlan:
    trunc_token_idx: int
    prefix_image_count: int
    tail_image_count: int
    prefix_image_tokens: int
    tail_image_tokens: int
    prefix_pixel_rows: int
    tail_pixel_rows: int
    prefix_prompt_tokens: int
    tail_prompt_tokens: int


@dataclass(frozen=True, slots=True)
class QwenPromptSlice:
    input_ids: mx.array
    mask: mx.array
    pixel_values: mx.array
    image_grid_thw: mx.array
    position_ids: mx.array


def qwen_language_model_logits(output: Any) -> mx.array:
    """Normalize mlx-vlm Qwen language-model returns to a logits tensor."""
    if hasattr(output, "logits"):
        return cast(mx.array, output.logits)
    return cast(mx.array, output)


def _qwen_slice_has_images(*, model: Any, prompt: QwenPromptSlice) -> bool:
    image_rows = int(prompt.image_grid_thw.shape[0])
    pixel_rows = int(prompt.pixel_values.shape[0])
    if image_rows == 0:
        if pixel_rows != 0:
            raise ValueError(
                "text-only Qwen prompt slice must not carry pixel rows when image_grid_thw is empty"
            )
        prompt_ids = np.asarray(prompt.input_ids.tolist(), dtype=np.int64).reshape(-1)
        for token_name in ("image_token_id", "video_token_id"):
            token_id = getattr(model.config, token_name, None)
            if token_id is not None and np.any(prompt_ids == int(token_id)):
                raise ValueError(
                    "text-only Qwen prompt slice still contains image/video marker tokens"
                )
        return False
    if pixel_rows == 0:
        raise ValueError("Qwen prompt slice has image_grid_thw entries but no pixel rows")
    return True


def _qwen_get_input_embeddings_for_slice(*, model: Any, prompt: QwenPromptSlice) -> Any:
    if _qwen_slice_has_images(model=model, prompt=prompt):
        return model.get_input_embeddings(
            prompt.input_ids,
            prompt.pixel_values,
            mask=prompt.mask,
            image_grid_thw=prompt.image_grid_thw,
        )
    return model.get_input_embeddings(
        prompt.input_ids,
        None,
        mask=prompt.mask,
    )


def _as_int_array(values: Sequence[Sequence[int]] | np.ndarray) -> np.ndarray:
    array = np.asarray(values, dtype=np.int64)
    if array.ndim != 2 or array.shape[1] != 3:
        raise ValueError(f"expected grid_thw shape [n, 3], got {array.shape}")
    return array


def _as_int_vector(values: Sequence[int] | np.ndarray) -> np.ndarray:
    return np.asarray(values, dtype=np.int64).reshape(-1)


def qwen_image_tokens_per_frame(
    grid_thw: Sequence[Sequence[int]] | np.ndarray,
    *,
    spatial_merge_size: int,
) -> tuple[int, ...]:
    if spatial_merge_size <= 0:
        raise ValueError("spatial_merge_size must be positive")
    grid = _as_int_array(grid_thw)
    merge_area = spatial_merge_size**2
    tokens = []
    for t, h, w in grid.tolist():
        prod = int(t) * int(h) * int(w)
        if prod % merge_area != 0:
            raise ValueError(f"grid product {prod} is not divisible by merge area {merge_area}")
        tokens.append(prod // merge_area)
    return tuple(tokens)


def qwen_pixel_rows_per_frame(
    grid_thw: Sequence[Sequence[int]] | np.ndarray,
) -> tuple[int, ...]:
    grid = _as_int_array(grid_thw)
    return tuple(int(t) * int(h) * int(w) for t, h, w in grid.tolist())


def compute_qwen_reprefill_plan(
    *,
    input_ids: Sequence[int] | np.ndarray,
    image_grid_thw: Sequence[Sequence[int]] | np.ndarray,
    reprefill_k: int,
    image_token_id: int,
    spatial_merge_size: int,
) -> QwenReprefillPlan:
    ids = np.asarray(input_ids, dtype=np.int64).reshape(-1)
    if reprefill_k <= 0:
        raise ValueError("reprefill_k must be > 0")

    per_frame_tokens = qwen_image_tokens_per_frame(
        image_grid_thw,
        spatial_merge_size=spatial_merge_size,
    )
    per_frame_pixels = qwen_pixel_rows_per_frame(image_grid_thw)
    n_frames = len(per_frame_tokens)
    if reprefill_k >= n_frames:
        raise ValueError(f"reprefill_k={reprefill_k} must be < n_frames={n_frames}")

    image_positions = np.flatnonzero(ids == int(image_token_id))
    total_image_tokens = int(sum(per_frame_tokens))
    if len(image_positions) != total_image_tokens:
        raise ValueError(
            f"image token count mismatch: found {len(image_positions)} markers but "
            f"grid implies {total_image_tokens}"
        )

    prefix_image_count = n_frames - reprefill_k
    prefix_image_tokens = int(sum(per_frame_tokens[:prefix_image_count]))
    prefix_pixel_rows = int(sum(per_frame_pixels[:prefix_image_count]))
    tail_image_tokens = total_image_tokens - prefix_image_tokens
    tail_pixel_rows = int(sum(per_frame_pixels[prefix_image_count:]))
    trunc_token_idx = int(image_positions[prefix_image_tokens])

    return QwenReprefillPlan(
        trunc_token_idx=trunc_token_idx,
        prefix_image_count=prefix_image_count,
        tail_image_count=reprefill_k,
        prefix_image_tokens=prefix_image_tokens,
        tail_image_tokens=tail_image_tokens,
        prefix_pixel_rows=prefix_pixel_rows,
        tail_pixel_rows=tail_pixel_rows,
        prefix_prompt_tokens=trunc_token_idx,
        tail_prompt_tokens=int(ids.size - trunc_token_idx),
    )


def common_prefix_token_count(
    left_input_ids: Sequence[int] | np.ndarray,
    right_input_ids: Sequence[int] | np.ndarray,
) -> int:
    left = _as_int_vector(left_input_ids)
    right = _as_int_vector(right_input_ids)
    shared = min(left.size, right.size)
    index = 0
    while index < shared and int(left[index]) == int(right[index]):
        index += 1
    return int(index)


def compute_qwen_token_cut_plan(
    *,
    input_ids: Sequence[int] | np.ndarray,
    image_grid_thw: Sequence[Sequence[int]] | np.ndarray,
    trunc_token_idx: int,
    image_token_id: int,
    spatial_merge_size: int,
) -> QwenReprefillPlan:
    """Build a reusable prompt-slice plan from an arbitrary token cut.

    This is stricter than a raw token trim: if the cut falls inside an image
    frame's token block, we hard-fail. That keeps cache reuse geometry explicit
    for follow-up experiments like 1.55F where Q3 should reuse the repaired
    Q2 visual state without silently bisecting the multimodal image segment.
    """

    ids = _as_int_vector(input_ids)
    if trunc_token_idx < 0 or trunc_token_idx > int(ids.size):
        raise ValueError(f"trunc_token_idx must be in [0, {ids.size}], got {trunc_token_idx}")

    per_frame_tokens = qwen_image_tokens_per_frame(
        image_grid_thw,
        spatial_merge_size=spatial_merge_size,
    )
    per_frame_pixels = qwen_pixel_rows_per_frame(image_grid_thw)
    image_positions = np.flatnonzero(ids == int(image_token_id))
    total_image_tokens = int(sum(per_frame_tokens))
    if len(image_positions) != total_image_tokens:
        raise ValueError(
            f"image token count mismatch: found {len(image_positions)} markers but "
            f"grid implies {total_image_tokens}"
        )

    prefix_image_tokens = int(sum(1 for pos in image_positions if int(pos) < trunc_token_idx))
    cumulative_tokens = 0
    prefix_image_count = 0
    for frame_tokens in per_frame_tokens:
        if cumulative_tokens + int(frame_tokens) <= prefix_image_tokens:
            cumulative_tokens += int(frame_tokens)
            prefix_image_count += 1
            continue
        break
    if cumulative_tokens != prefix_image_tokens:
        raise ValueError(
            "trunc_token_idx splits an image-frame token block; "
            f"prefix_image_tokens={prefix_image_tokens} does not align to "
            f"whole-frame boundaries {per_frame_tokens}"
        )

    prefix_pixel_rows = int(sum(per_frame_pixels[:prefix_image_count]))
    return QwenReprefillPlan(
        trunc_token_idx=int(trunc_token_idx),
        prefix_image_count=prefix_image_count,
        tail_image_count=len(per_frame_tokens) - prefix_image_count,
        prefix_image_tokens=prefix_image_tokens,
        tail_image_tokens=total_image_tokens - prefix_image_tokens,
        prefix_pixel_rows=prefix_pixel_rows,
        tail_pixel_rows=int(sum(per_frame_pixels[prefix_image_count:])),
        prefix_prompt_tokens=int(trunc_token_idx),
        tail_prompt_tokens=int(ids.size - trunc_token_idx),
    )


def slice_qwen_prompt_for_reprefill(
    *,
    input_ids: mx.array,
    mask: mx.array,
    pixel_values: mx.array,
    image_grid_thw: mx.array,
    position_ids: mx.array,
    plan: QwenReprefillPlan,
) -> tuple[QwenPromptSlice, QwenPromptSlice]:
    prefix = QwenPromptSlice(
        input_ids=input_ids[:, : plan.trunc_token_idx],
        mask=mask[:, : plan.trunc_token_idx],
        pixel_values=pixel_values[: plan.prefix_pixel_rows],
        image_grid_thw=image_grid_thw[: plan.prefix_image_count],
        position_ids=position_ids[:, :, : plan.trunc_token_idx],
    )
    tail = QwenPromptSlice(
        input_ids=input_ids[:, plan.trunc_token_idx :],
        mask=mask[:, plan.trunc_token_idx :],
        pixel_values=pixel_values[plan.prefix_pixel_rows :],
        image_grid_thw=image_grid_thw[plan.prefix_image_count :],
        position_ids=position_ids[:, :, plan.trunc_token_idx :],
    )
    return prefix, tail


def compute_qwen_position_ids(
    *,
    model: Any,
    input_ids: mx.array,
    image_grid_thw: mx.array,
    mask: mx.array,
) -> mx.array:
    position_ids, _rope_deltas = model.language_model.get_rope_index(
        input_ids,
        image_grid_thw,
        None,
        mask,
    )
    return cast(mx.array, position_ids)


def make_qwen_prefix_cache(
    *,
    model: Any,
    prefix: QwenPromptSlice,
) -> tuple[list[Any], float]:
    prompt_cache = make_prompt_cache(model.language_model)
    t0 = time.perf_counter_ns()
    embeddings = _qwen_get_input_embeddings_for_slice(model=model, prompt=prefix)
    logits = qwen_language_model_logits(
        model.language_model(
            prefix.input_ids,
            inputs_embeds=embeddings.inputs_embeds,
            mask=prefix.mask,
            cache=prompt_cache,
            position_ids=prefix.position_ids,
        )
    )
    mx.eval(logits)
    elapsed_ms = (time.perf_counter_ns() - t0) / 1_000_000
    return prompt_cache, elapsed_ms


def rewind_qwen_prefix_cache(
    *,
    prompt_cache: list[Any],
    appended_prompt_tokens: int,
    appended_generation_tokens: int,
) -> None:
    trim_prompt_cache(
        prompt_cache,
        int(appended_prompt_tokens) + int(appended_generation_tokens),
    )


def generate_qwen_tail_with_explicit_positions(
    *,
    model: Any,
    processor: Any,
    prompt_cache: list[Any],
    tail: QwenPromptSlice,
    full_prompt_tokens: int,
    max_tokens: int,
    temperature: float = 0.0,
    top_p: float = 1.0,
    min_p: float = 0.0,
) -> dict[str, Any]:
    mx.random.seed(42)
    sampler = make_sampler(temp=temperature, top_p=top_p, min_p=min_p)
    tokenizer = processor.tokenizer if hasattr(processor, "tokenizer") else processor
    tokenizer.stopping_criteria.reset(model.config.eos_token_id)

    t0 = time.perf_counter_ns()
    embeddings = _qwen_get_input_embeddings_for_slice(model=model, prompt=tail)
    prefill_outputs = qwen_language_model_logits(
        model.language_model(
            tail.input_ids,
            inputs_embeds=embeddings.inputs_embeds,
            mask=tail.mask,
            cache=prompt_cache,
            position_ids=tail.position_ids,
        )
    )
    prefill_logprobs = prefill_outputs[:, -1, :] - mx.logsumexp(prefill_outputs[:, -1, :])
    next_token = sampler(prefill_logprobs)
    mx.eval(next_token)
    prompt_ms = (time.perf_counter_ns() - t0) / 1_000_000

    generated: list[int] = []
    gen_start_ns = time.perf_counter_ns()
    last_position_ids = tail.position_ids[:, :, -1:]
    while len(generated) < max_tokens:
        token = int(next_token.item())
        if tokenizer.stopping_criteria(token):
            break
        generated.append(token)
        step_position_ids = last_position_ids + len(generated)
        logits = qwen_language_model_logits(
            model.language_model(
                mx.array([[token]], dtype=tail.input_ids.dtype),
                cache=prompt_cache,
                position_ids=step_position_ids,
            )
        )
        logprobs = logits[:, -1, :] - mx.logsumexp(logits[:, -1, :])
        next_token = sampler(logprobs)
        mx.eval(next_token)
        if len(generated) % 256 == 0:
            mx.clear_cache()
    generation_ms = (time.perf_counter_ns() - gen_start_ns) / 1_000_000
    text = tokenizer.decode(generated, skip_special_tokens=True).strip()

    total_ms = prompt_ms + generation_ms
    prompt_tps = full_prompt_tokens / (prompt_ms / 1000) if prompt_ms > 0 else 0.0
    generation_tps = len(generated) / (generation_ms / 1000) if generation_ms > 0 else 0.0
    return {
        "text": text,
        "elapsed_ms": total_ms,
        "prompt_tokens": full_prompt_tokens,
        "tail_prompt_tokens": int(tail.input_ids.shape[1]),
        "generation_tokens": len(generated),
        "prompt_tps": prompt_tps,
        "generation_tps": generation_tps,
        "peak_memory_gb": mx.get_peak_memory() / 1e9,
        "prefix_hit": int(full_prompt_tokens - int(tail.input_ids.shape[1])),
        "input_len": int(full_prompt_tokens),
        "prefix_coverage": (
            (full_prompt_tokens - int(tail.input_ids.shape[1])) / full_prompt_tokens
            if full_prompt_tokens > 0
            else 0.0
        ),
        "prefill_ms": prompt_ms,
        "generation_ms": generation_ms,
    }
