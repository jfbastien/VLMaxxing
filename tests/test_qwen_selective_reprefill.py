from types import SimpleNamespace

import numpy as np
import pytest

from tests._mlx_probe import mlx_is_usable

if not mlx_is_usable():
    pytest.skip(
        "mlx.core not usable on this host (import or Metal-init fails); see tests/_mlx_probe.py",
        allow_module_level=True,
    )

import mlx.core as mx

from codec_through.qwen_selective_reprefill import (
    QwenPromptSlice,
    common_prefix_token_count,
    compute_qwen_reprefill_plan,
    compute_qwen_token_cut_plan,
    generate_qwen_tail_with_explicit_positions,
    make_qwen_prefix_cache,
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


def test_common_prefix_token_count_stops_at_first_difference() -> None:
    assert common_prefix_token_count([1, 2, 3, 4], [1, 2, 9, 4]) == 2
    assert common_prefix_token_count([1, 2], [1, 2, 3]) == 2


def test_compute_qwen_token_cut_plan_after_full_image_block() -> None:
    image_token_id = 99
    input_ids = [1, image_token_id, image_token_id, image_token_id, image_token_id]
    input_ids += [image_token_id, image_token_id, image_token_id, image_token_id, 2, 3]
    grid = np.array([[1, 4, 4], [1, 4, 4]])
    plan = compute_qwen_token_cut_plan(
        input_ids=input_ids,
        image_grid_thw=grid,
        trunc_token_idx=9,
        image_token_id=image_token_id,
        spatial_merge_size=2,
    )
    assert plan.prefix_image_count == 2
    assert plan.tail_image_count == 0
    assert plan.prefix_image_tokens == 8
    assert plan.tail_image_tokens == 0
    assert plan.prefix_pixel_rows == 32
    assert plan.tail_pixel_rows == 0
    assert plan.prefix_prompt_tokens == 9
    assert plan.tail_prompt_tokens == 2


def test_compute_qwen_token_cut_plan_rejects_mid_frame_cut() -> None:
    image_token_id = 99
    input_ids = [1, image_token_id, image_token_id, image_token_id, image_token_id]
    input_ids += [image_token_id, image_token_id, image_token_id, image_token_id, 2, 3]
    grid = np.array([[1, 4, 4], [1, 4, 4]])
    with pytest.raises(ValueError, match="splits an image-frame token block"):
        compute_qwen_token_cut_plan(
            input_ids=input_ids,
            image_grid_thw=grid,
            trunc_token_idx=7,
            image_token_id=image_token_id,
            spatial_merge_size=2,
        )


class _FakeStoppingCriteria:
    def __init__(self) -> None:
        self.eos_token_id: int | None = None

    def reset(self, eos_token_id: int) -> None:
        self.eos_token_id = eos_token_id

    def __call__(self, token: int) -> bool:
        return token == self.eos_token_id


class _FakeTokenizer:
    def __init__(self) -> None:
        self.stopping_criteria = _FakeStoppingCriteria()

    def decode(self, tokens: list[int], skip_special_tokens: bool = True) -> str:
        return " ".join(str(token) for token in tokens)


class _FakeEmbedTokens:
    def __call__(self, input_ids: mx.array) -> mx.array:
        return mx.zeros((1, int(input_ids.shape[1]), 4), dtype=mx.float32)


class _FakeInnerModel:
    def __init__(self) -> None:
        self.embed_tokens = _FakeEmbedTokens()


class _FakeLanguageModel:
    def __init__(self) -> None:
        self.model = _FakeInnerModel()
        self._position_ids = None
        self._rope_deltas = None
        self.calls: list[dict[str, object]] = []

    def make_cache(self) -> list[object]:
        return []

    def __call__(
        self,
        input_ids: mx.array,
        *,
        inputs_embeds: mx.array | None = None,
        mask: mx.array | None = None,
        cache: list[object] | None = None,
        position_ids: mx.array | None = None,
    ) -> mx.array:
        self.calls.append(
            {
                "input_shape": tuple(input_ids.shape),
                "inputs_embeds_shape": None
                if inputs_embeds is None
                else tuple(inputs_embeds.shape),
                "position_shape": None if position_ids is None else tuple(position_ids.shape),
            }
        )
        seq_len = (
            int(inputs_embeds.shape[1]) if inputs_embeds is not None else int(input_ids.shape[1])
        )
        logits = np.zeros((1, seq_len, 4), dtype=np.float32)
        logits[0, -1, 2] = 1.0
        return mx.array(logits)


class _FakeQwenModel:
    def __init__(self) -> None:
        self.language_model = _FakeLanguageModel()
        self.config = SimpleNamespace(eos_token_id=2, image_token_id=99, video_token_id=100)
        self.pixel_values_seen: list[object] = []

    def get_input_embeddings(
        self,
        input_ids: mx.array,
        pixel_values: mx.array | None = None,
        **kwargs: object,
    ) -> SimpleNamespace:
        self.pixel_values_seen.append(pixel_values)
        if pixel_values is None:
            self.language_model._position_ids = None
            self.language_model._rope_deltas = None
        return SimpleNamespace(inputs_embeds=self.language_model.model.embed_tokens(input_ids))


def test_generate_qwen_tail_with_explicit_positions_supports_text_only_tail() -> None:
    model = _FakeQwenModel()
    processor = SimpleNamespace(tokenizer=_FakeTokenizer())
    tail = QwenPromptSlice(
        input_ids=mx.array([[5, 6]], dtype=mx.int32),
        mask=mx.array([[1, 1]], dtype=mx.int32),
        pixel_values=mx.zeros((0, 3), dtype=mx.float32),
        image_grid_thw=mx.zeros((0, 3), dtype=mx.int32),
        position_ids=mx.zeros((1, 3, 2), dtype=mx.int32),
    )

    result = generate_qwen_tail_with_explicit_positions(
        model=model,
        processor=processor,
        prompt_cache=[],
        tail=tail,
        full_prompt_tokens=10,
        max_tokens=8,
    )

    assert model.pixel_values_seen == [None]
    assert result["tail_prompt_tokens"] == 2
    assert result["prefix_hit"] == 8
    assert result["text"] == ""


def test_generate_qwen_tail_with_explicit_positions_accepts_sampler_args() -> None:
    model = _FakeQwenModel()
    processor = SimpleNamespace(tokenizer=_FakeTokenizer())
    tail = QwenPromptSlice(
        input_ids=mx.array([[5, 6]], dtype=mx.int32),
        mask=mx.array([[1, 1]], dtype=mx.int32),
        pixel_values=mx.zeros((0, 3), dtype=mx.float32),
        image_grid_thw=mx.zeros((0, 3), dtype=mx.int32),
        position_ids=mx.zeros((1, 3, 2), dtype=mx.int32),
    )

    result = generate_qwen_tail_with_explicit_positions(
        model=model,
        processor=processor,
        prompt_cache=[],
        tail=tail,
        full_prompt_tokens=10,
        max_tokens=0,
        temperature=0.1,
        top_p=0.95,
        min_p=0.0,
    )

    assert model.pixel_values_seen == [None]
    assert result["generation_tokens"] == 0


def test_make_qwen_prefix_cache_supports_text_only_prefix() -> None:
    model = _FakeQwenModel()
    prefix = QwenPromptSlice(
        input_ids=mx.array([[5, 6]], dtype=mx.int32),
        mask=mx.array([[1, 1]], dtype=mx.int32),
        pixel_values=mx.zeros((0, 3), dtype=mx.float32),
        image_grid_thw=mx.zeros((0, 3), dtype=mx.int32),
        position_ids=mx.zeros((1, 3, 2), dtype=mx.int32),
    )

    prompt_cache, elapsed_ms = make_qwen_prefix_cache(model=model, prefix=prefix)

    assert isinstance(prompt_cache, list)
    assert elapsed_ms >= 0.0
    assert model.pixel_values_seen == [None]


def test_generate_qwen_tail_with_explicit_positions_rejects_empty_grid_with_image_markers() -> None:
    model = _FakeQwenModel()
    processor = SimpleNamespace(tokenizer=_FakeTokenizer())
    tail = QwenPromptSlice(
        input_ids=mx.array([[99, 5]], dtype=mx.int32),
        mask=mx.array([[1, 1]], dtype=mx.int32),
        pixel_values=mx.zeros((0, 3), dtype=mx.float32),
        image_grid_thw=mx.zeros((0, 3), dtype=mx.int32),
        position_ids=mx.zeros((1, 3, 2), dtype=mx.int32),
    )

    with pytest.raises(ValueError, match="still contains image/video marker tokens"):
        generate_qwen_tail_with_explicit_positions(
            model=model,
            processor=processor,
            prompt_cache=[],
            tail=tail,
            full_prompt_tokens=2,
            max_tokens=8,
        )
