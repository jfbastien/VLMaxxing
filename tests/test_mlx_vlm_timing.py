from __future__ import annotations

import pytest

from codec_through.mlx_vlm_timing import (
    chunked_prefill_steps,
    register_prefill_shape_observation,
)


def test_chunked_prefill_steps_matches_mlx_vlm_boundary() -> None:
    assert chunked_prefill_steps(686) == 1
    assert chunked_prefill_steps(2048) == 1
    assert chunked_prefill_steps(2225) == 2
    assert chunked_prefill_steps(1573, prefill_step_size=1500) == 2
    assert chunked_prefill_steps(2225, prefill_step_size=4096) == 1


def test_chunked_prefill_steps_rejects_empty_prompt() -> None:
    with pytest.raises(ValueError, match="seq_len must be positive"):
        chunked_prefill_steps(0)


def test_register_prefill_shape_observation_counts_repeated_shapes() -> None:
    counts: dict[tuple[int, int], int] = {}

    first = register_prefill_shape_observation(counts, seq_len=1417, n_warmup=1)
    second = register_prefill_shape_observation(counts, seq_len=1417, n_warmup=1)
    third = register_prefill_shape_observation(counts, seq_len=2225, n_warmup=0)

    assert first == {
        "pruned_shape_key": [1417, 1],
        "pruned_prior_call_count_for_shape": 0,
        "pruned_measured_call_index_for_shape": 2,
    }
    assert second == {
        "pruned_shape_key": [1417, 1],
        "pruned_prior_call_count_for_shape": 2,
        "pruned_measured_call_index_for_shape": 4,
    }
    assert third == {
        "pruned_shape_key": [2225, 2],
        "pruned_prior_call_count_for_shape": 0,
        "pruned_measured_call_index_for_shape": 1,
    }
    assert counts == {(1417, 1): 4, (2225, 2): 1}
