from types import SimpleNamespace

import mlx.core as mx
import numpy as np

from codec_through.qwen_selective_reprefill import (
    compute_qwen_reprefill_plan,
    qwen_image_tokens_per_frame,
    qwen_language_model_logits,
    qwen_pixel_rows_per_frame,
)


def test_qwen_image_tokens_per_frame() -> None:
    grid = np.array([[1, 4, 4], [1, 4, 4]])
    assert qwen_image_tokens_per_frame(grid, spatial_merge_size=2) == (4, 4)


def test_qwen_pixel_rows_per_frame() -> None:
    grid = np.array([[1, 4, 4], [2, 4, 4]])
    assert qwen_pixel_rows_per_frame(grid) == (16, 32)


def test_compute_qwen_reprefill_plan() -> None:
    image_token_id = 99
    input_ids = [1, image_token_id, image_token_id, image_token_id, image_token_id]
    input_ids += [image_token_id, image_token_id, image_token_id, image_token_id, 2, 3]
    grid = np.array([[1, 4, 4], [1, 4, 4]])
    plan = compute_qwen_reprefill_plan(
        input_ids=input_ids,
        image_grid_thw=grid,
        reprefill_k=1,
        image_token_id=image_token_id,
        spatial_merge_size=2,
    )
    assert plan.trunc_token_idx == 5
    assert plan.prefix_image_count == 1
    assert plan.tail_image_count == 1
    assert plan.prefix_image_tokens == 4
    assert plan.tail_image_tokens == 4
    assert plan.prefix_pixel_rows == 16
    assert plan.tail_pixel_rows == 16
    assert plan.prefix_prompt_tokens == 5
    assert plan.tail_prompt_tokens == len(input_ids) - 5


def test_qwen_language_model_logits_accepts_wrapper_or_tensor() -> None:
    logits = mx.array([[[1.0, 2.0]]], dtype=mx.float32)
    wrapped = SimpleNamespace(logits=logits)
    assert qwen_language_model_logits(wrapped).tolist() == logits.tolist()
    assert qwen_language_model_logits(logits).tolist() == logits.tolist()
