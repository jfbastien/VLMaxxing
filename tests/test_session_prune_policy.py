from __future__ import annotations

import pytest

from codec_through.session_prune_policy import (
    keep_rate_for_query,
    keep_rate_for_session_query,
)


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


def test_keep_rate_for_session_query_uses_duration_specific_q0_override() -> None:
    assert (
        keep_rate_for_session_query(
            q_index=0,
            duration="long",
            default_keep_rate=0.5,
            first_query_keep_rate=1.0,
            follow_up_keep_rate=0.5,
            first_query_keep_rate_long=0.67,
        )
        == 0.67
    )
    assert (
        keep_rate_for_session_query(
            q_index=0,
            duration="short",
            default_keep_rate=0.5,
            first_query_keep_rate=1.0,
            follow_up_keep_rate=0.5,
            first_query_keep_rate_long=0.67,
        )
        == 1.0
    )


def test_keep_rate_for_session_query_uses_follow_up_override_after_q0() -> None:
    assert (
        keep_rate_for_session_query(
            q_index=2,
            duration="long",
            default_keep_rate=0.5,
            first_query_keep_rate=1.0,
            follow_up_keep_rate=0.4,
            first_query_keep_rate_long=0.67,
        )
        == 0.4
    )


def test_keep_rate_for_session_query_rejects_unknown_duration() -> None:
    with pytest.raises(ValueError, match="duration must be one of"):
        keep_rate_for_session_query(
            q_index=0,
            duration="weird",
            default_keep_rate=0.5,
            first_query_keep_rate=1.0,
            follow_up_keep_rate=0.5,
        )
