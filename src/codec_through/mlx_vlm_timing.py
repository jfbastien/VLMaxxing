"""Pure timing helpers that mirror MLX-VLM prompt-prefill behavior."""

from __future__ import annotations

from collections.abc import MutableMapping
from typing import Any


def chunked_prefill_steps(seq_len: int, *, prefill_step_size: int = 2048) -> int:
    """Return how many prompt-prefill chunks MLX-VLM will process.

    Mirrors ``mlx_vlm.generate.generate_step``: prompts at or below
    ``prefill_step_size`` use the single-shot path; longer prompts process all
    but the final token in chunks.
    """
    if seq_len <= 0:
        raise ValueError(f"seq_len must be positive, got {seq_len}")
    if seq_len <= prefill_step_size:
        return 1
    remaining = seq_len
    steps = 0
    while remaining > 1:
        n_to_process = min(prefill_step_size, remaining - 1)
        remaining -= n_to_process
        steps += 1
    return steps


def prefill_shape_key(seq_len: int, *, prefill_step_size: int = 2048) -> tuple[int, int]:
    """Shape key used by local warmup diagnostics."""
    return (seq_len, chunked_prefill_steps(seq_len, prefill_step_size=prefill_step_size))


def register_prefill_shape_observation(
    counts: MutableMapping[tuple[int, int], int],
    *,
    seq_len: int,
    n_warmup: int,
    prefill_step_size: int = 2048,
) -> dict[str, Any]:
    """Record warmup + measured calls for one prompt shape.

    The returned metadata is intentionally about the pruned measured call. A
    prior same-shape item makes the measured call later than ``n_warmup + 1``;
    that distinction is important when interpreting MLX cold-shape timing.
    """
    if n_warmup < 0:
        raise ValueError(f"n_warmup must be nonnegative, got {n_warmup}")
    key = prefill_shape_key(seq_len, prefill_step_size=prefill_step_size)
    prior_calls = int(counts.get(key, 0))
    measured_call_index = prior_calls + n_warmup + 1
    counts[key] = measured_call_index
    return {
        "pruned_shape_key": list(key),
        "pruned_prior_call_count_for_shape": prior_calls,
        "pruned_measured_call_index_for_shape": measured_call_index,
    }
