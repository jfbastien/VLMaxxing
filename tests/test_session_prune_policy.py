from __future__ import annotations

import pytest

from codec_through.session_prune_policy import keep_rate_for_query


def test_keep_rate_defaults_without_overrides() -> None:
    assert (
        keep_rate_for_query(
            q_index=0,
            default_keep_rate=0.5,
            first_query_keep_rate=None,
            follow_up_keep_rate=None,
        )
        == 0.5
    )
    assert (
        keep_rate_for_query(
            q_index=2,
            default_keep_rate=0.5,
            first_query_keep_rate=None,
            follow_up_keep_rate=None,
        )
        == 0.5
    )


def test_keep_rate_uses_query_position_overrides() -> None:
    assert (
        keep_rate_for_query(
            q_index=0,
            default_keep_rate=0.5,
            first_query_keep_rate=1.0,
            follow_up_keep_rate=0.5,
        )
        == 1.0
    )
    assert (
        keep_rate_for_query(
            q_index=1,
            default_keep_rate=0.5,
            first_query_keep_rate=1.0,
            follow_up_keep_rate=0.5,
        )
        == 0.5
    )


def test_keep_rate_rejects_negative_query_index() -> None:
    with pytest.raises(ValueError, match="q_index must be non-negative"):
        keep_rate_for_query(
            q_index=-1,
            default_keep_rate=0.5,
            first_query_keep_rate=1.0,
            follow_up_keep_rate=0.5,
        )
