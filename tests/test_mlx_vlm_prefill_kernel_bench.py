from __future__ import annotations

import platform

import pytest

from tests._mlx_probe import mlx_is_usable


def _mlx_prefill_skip_reason() -> str | None:
    if platform.system() != "Darwin":
        return (
            "MLX/MLX-VLM prefill benchmark tests require macOS/Darwin; "
            "Linux CI intentionally omits MLX."
        )
    if not mlx_is_usable():
        return (
            "mlx.core not usable on this macOS host (import or Metal-init fails); "
            "see tests/_mlx_probe.py"
        )
    return None


_skip_reason = _mlx_prefill_skip_reason()
if _skip_reason is not None:
    pytest.skip(_skip_reason, allow_module_level=True)

from scripts.benchmark_mlx_vlm_prefill_kernel import (  # noqa: E402
    _measurement_plan,
    _substrate_verdict,
)


def test_measurement_plan_keeps_nested_order_without_shuffle() -> None:
    plan = _measurement_plan(
        seq_lens=[128, 256],
        prefill_step_sizes=[64, 512],
        repeats=2,
        shuffle=False,
        seed=1,
    )

    assert plan == [
        {"seq_len": 128, "prefill_step_size": 64, "repeat_idx": 0},
        {"seq_len": 128, "prefill_step_size": 64, "repeat_idx": 1},
        {"seq_len": 128, "prefill_step_size": 512, "repeat_idx": 0},
        {"seq_len": 128, "prefill_step_size": 512, "repeat_idx": 1},
        {"seq_len": 256, "prefill_step_size": 64, "repeat_idx": 0},
        {"seq_len": 256, "prefill_step_size": 64, "repeat_idx": 1},
        {"seq_len": 256, "prefill_step_size": 512, "repeat_idx": 0},
        {"seq_len": 256, "prefill_step_size": 512, "repeat_idx": 1},
    ]


def test_measurement_plan_shuffle_is_seeded_and_preserves_cells() -> None:
    ordered = _measurement_plan(
        seq_lens=[128, 256, 512],
        prefill_step_sizes=[64, 512],
        repeats=2,
        shuffle=False,
        seed=7,
    )
    shuffled_a = _measurement_plan(
        seq_lens=[128, 256, 512],
        prefill_step_sizes=[64, 512],
        repeats=2,
        shuffle=True,
        seed=7,
    )
    shuffled_b = _measurement_plan(
        seq_lens=[128, 256, 512],
        prefill_step_sizes=[64, 512],
        repeats=2,
        shuffle=True,
        seed=7,
    )

    assert shuffled_a == shuffled_b
    assert shuffled_a != ordered
    assert sorted(shuffled_a, key=lambda row: tuple(row.items())) == sorted(
        ordered, key=lambda row: tuple(row.items())
    )


def test_substrate_verdict_uses_warm_min_ms_per_token() -> None:
    verdict = _substrate_verdict(
        {
            "1573@2048": {
                "seq_len": 1573,
                "prefill_step_size": 2048,
                "chunked": False,
                "min_ms": 7865.0,
                "min_ms_per_token": 5.0,
            },
            "2188@2048": {
                "seq_len": 2188,
                "prefill_step_size": 2048,
                "chunked": True,
                "min_ms": 4360.0,
                "min_ms_per_token": 2.0,
            },
        }
    )

    assert verdict["verdict"] == "chunked_path_lower_latency_despite_more_tokens"
    assert verdict["presentation_metric"] == "min_ms_per_token"
    assert verdict["single_shot_key"] == "1573@2048"
    assert verdict["chunked_key"] == "2188@2048"
    assert verdict["single_minus_chunked_min_ms"] == 3505.0
    assert verdict["single_over_chunked_ms_per_token_ratio"] == 2.5
