from __future__ import annotations

import pytest

from codec_through.selective_reprefill_policy import reprefill_k_for_query


def test_q1_is_always_cold() -> None:
    assert (
        reprefill_k_for_query(
            q_index=0,
            default_reprefill_k=1,
            q2_reprefill_k=1,
            q3_reprefill_k=0,
        )
        == 0
    )


def test_query_position_overrides_default() -> None:
    assert (
        reprefill_k_for_query(
            q_index=1,
            default_reprefill_k=1,
            q2_reprefill_k=2,
            q3_reprefill_k=0,
        )
        == 2
    )
    assert (
        reprefill_k_for_query(
            q_index=2,
            default_reprefill_k=1,
            q2_reprefill_k=2,
            q3_reprefill_k=0,
        )
        == 0
    )


def test_default_applies_when_no_override_exists() -> None:
    assert (
        reprefill_k_for_query(
            q_index=3,
            default_reprefill_k=1,
            q2_reprefill_k=2,
            q3_reprefill_k=0,
        )
        == 1
    )


def test_negative_values_fail() -> None:
    with pytest.raises(ValueError, match="q_index must be non-negative"):
        reprefill_k_for_query(
            q_index=-1,
            default_reprefill_k=1,
            q2_reprefill_k=1,
            q3_reprefill_k=0,
        )
    with pytest.raises(ValueError, match="default_reprefill_k must be non-negative"):
        reprefill_k_for_query(
            q_index=1,
            default_reprefill_k=-1,
            q2_reprefill_k=1,
            q3_reprefill_k=0,
        )
    with pytest.raises(ValueError, match="q3_reprefill_k must be non-negative"):
        reprefill_k_for_query(
            q_index=2,
            default_reprefill_k=1,
            q2_reprefill_k=1,
            q3_reprefill_k=-1,
        )
