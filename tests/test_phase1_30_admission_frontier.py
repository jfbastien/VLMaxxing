from __future__ import annotations

from codec_through.phase1_30_admission_frontier import (
    SessionArmMetrics,
    SessionPair,
    build_policy_suite,
    compute_exact_frontier,
    evaluate_policy,
)


def _pair(
    *,
    session_id: str,
    duration: str,
    pruned_stream: int,
    dense_stream: int,
    cold_correct: int = 3,
    pruned_stream_ms: float,
    dense_stream_ms: float,
    pruned_cold_ms: float = 300.0,
    dense_cold_ms: float = 300.0,
    pruned_q0_stream: int | None = None,
    dense_q0_stream: int | None = None,
) -> SessionPair:
    pruned_q0_stream = pruned_stream if pruned_q0_stream is None else pruned_q0_stream
    dense_q0_stream = dense_stream if dense_q0_stream is None else dense_q0_stream
    pruned = SessionArmMetrics(
        arm_name="pruned_q0",
        session_id=session_id,
        video_id=session_id,
        duration=duration,
        split="holdout",
        stream_correct=pruned_stream,
        cold_correct=cold_correct,
        q0_stream_correct=pruned_q0_stream,
        q0_cold_correct=1,
        follow_up_stream_correct=pruned_stream - pruned_q0_stream,
        follow_up_cold_correct=cold_correct - 1,
        stream_total_ms=pruned_stream_ms,
        cold_total_ms=pruned_cold_ms,
        parse_failures=0,
        degenerates=0,
    )
    dense = SessionArmMetrics(
        arm_name="dense_q0",
        session_id=session_id,
        video_id=session_id,
        duration=duration,
        split="holdout",
        stream_correct=dense_stream,
        cold_correct=cold_correct,
        q0_stream_correct=dense_q0_stream,
        q0_cold_correct=1,
        follow_up_stream_correct=dense_stream - dense_q0_stream,
        follow_up_cold_correct=cold_correct - 1,
        stream_total_ms=dense_stream_ms,
        cold_total_ms=dense_cold_ms,
        parse_failures=0,
        degenerates=0,
    )
    return SessionPair(
        session_id=session_id,
        video_id=session_id,
        duration=duration,
        split="holdout",
        pruned_q0=pruned,
        dense_q0=dense,
    )


def test_duration_policy_mix_prefers_matching_duration() -> None:
    session_pairs = {
        "s1": _pair(
            session_id="s1",
            duration="long",
            pruned_stream=1,
            dense_stream=2,
            pruned_stream_ms=60.0,
            dense_stream_ms=90.0,
            pruned_q0_stream=0,
            dense_q0_stream=1,
        ),
        "s2": _pair(
            session_id="s2",
            duration="short",
            pruned_stream=2,
            dense_stream=2,
            pruned_stream_ms=60.0,
            dense_stream_ms=90.0,
            pruned_q0_stream=1,
            dense_q0_stream=1,
        ),
    }
    result = next(
        item for item in build_policy_suite(session_pairs) if item.name == "dense_on_long"
    )
    assert result.dense_sessions == ("s1",)
    assert result.delta_correct == -2


def test_oracle_q0_gain_only_switches_q0_regressions() -> None:
    session_pairs = {
        "s1": _pair(
            session_id="s1",
            duration="long",
            pruned_stream=1,
            dense_stream=1,
            pruned_stream_ms=60.0,
            dense_stream_ms=90.0,
            pruned_q0_stream=0,
            dense_q0_stream=1,
        ),
        "s2": _pair(
            session_id="s2",
            duration="short",
            pruned_stream=2,
            dense_stream=3,
            pruned_stream_ms=60.0,
            dense_stream_ms=90.0,
            pruned_q0_stream=1,
            dense_q0_stream=1,
        ),
    }
    result = next(
        item for item in build_policy_suite(session_pairs) if item.name == "oracle_q0_gain"
    )
    assert result.dense_sessions == ("s1",)


def test_exact_frontier_finds_best_rescue_point() -> None:
    session_pairs = {
        "s1": _pair(
            session_id="s1",
            duration="long",
            pruned_stream=1,
            dense_stream=2,
            cold_correct=2,
            pruned_stream_ms=110.0,
            dense_stream_ms=95.0,
            pruned_q0_stream=0,
            dense_q0_stream=1,
        ),
        "s2": _pair(
            session_id="s2",
            duration="short",
            pruned_stream=2,
            dense_stream=2,
            cold_correct=2,
            pruned_stream_ms=90.0,
            dense_stream_ms=130.0,
            pruned_q0_stream=1,
            dense_q0_stream=1,
        ),
    }
    frontier = compute_exact_frontier(session_pairs)
    assert frontier["best_rescue"] is not None
    assert frontier["best_rescue"].dense_sessions == ("s1",)
    assert frontier["best_accuracy_at_or_above_3x"] is not None
    assert frontier["best_accuracy_at_or_above_3x"].dense_sessions == ("s1",)


def test_evaluate_policy_reports_format_and_gate_status() -> None:
    session_pairs = {
        "s1": _pair(
            session_id="s1",
            duration="medium",
            pruned_stream=2,
            dense_stream=3,
            pruned_stream_ms=80.0,
            dense_stream_ms=90.0,
        )
    }
    result = evaluate_policy(
        session_pairs=session_pairs,
        name="dense_all",
        deployable=True,
        description="dense",
        choose_arm=lambda pair: "dense_q0",
    )
    assert result.format_pass
    assert result.strict_pass
    assert result.rescue_pass
