from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

ArmName = Literal["pruned_q0", "dense_q0"]


@dataclass(frozen=True, slots=True)
class SessionArmMetrics:
    arm_name: ArmName
    session_id: str
    video_id: str
    duration: str
    split: str
    stream_correct: int
    cold_correct: int
    q0_stream_correct: int
    q0_cold_correct: int
    follow_up_stream_correct: int
    follow_up_cold_correct: int
    stream_total_ms: float
    cold_total_ms: float
    parse_failures: int
    degenerates: int

    @property
    def delta_correct(self) -> int:
        return self.stream_correct - self.cold_correct

    @property
    def q0_delta_correct(self) -> int:
        return self.q0_stream_correct - self.q0_cold_correct

    @property
    def follow_up_delta_correct(self) -> int:
        return self.follow_up_stream_correct - self.follow_up_cold_correct

    @property
    def slack_vs_3x_ms(self) -> float:
        return self.cold_total_ms - (3.0 * self.stream_total_ms)


@dataclass(frozen=True, slots=True)
class SessionPair:
    session_id: str
    video_id: str
    duration: str
    split: str
    pruned_q0: SessionArmMetrics
    dense_q0: SessionArmMetrics


@dataclass(frozen=True, slots=True)
class PolicyResult:
    name: str
    deployable: bool
    description: str
    dense_sessions: tuple[str, ...]
    n_sessions: int
    n_queries: int
    stream_correct: int
    cold_correct: int
    delta_correct: int
    q0_stream_correct: int
    q0_cold_correct: int
    q0_delta_correct: int
    follow_up_stream_correct: int
    follow_up_cold_correct: int
    follow_up_delta_correct: int
    stream_total_ms: float
    cold_total_ms: float
    speedup_cold_over_stream: float
    slack_vs_3x_ms: float
    parse_failures: int
    degenerates: int
    strict_pass: bool
    rescue_pass: bool
    format_pass: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "deployable": self.deployable,
            "description": self.description,
            "dense_sessions": list(self.dense_sessions),
            "n_sessions": self.n_sessions,
            "n_queries": self.n_queries,
            "stream_correct": self.stream_correct,
            "cold_correct": self.cold_correct,
            "delta_correct": self.delta_correct,
            "accuracy_delta": self.delta_correct / self.n_queries,
            "q0_stream_correct": self.q0_stream_correct,
            "q0_cold_correct": self.q0_cold_correct,
            "q0_delta_correct": self.q0_delta_correct,
            "follow_up_stream_correct": self.follow_up_stream_correct,
            "follow_up_cold_correct": self.follow_up_cold_correct,
            "follow_up_delta_correct": self.follow_up_delta_correct,
            "follow_up_accuracy_delta": self.follow_up_delta_correct
            / (self.n_queries - self.n_sessions),
            "stream_total_ms": self.stream_total_ms,
            "cold_total_ms": self.cold_total_ms,
            "speedup_cold_over_stream": self.speedup_cold_over_stream,
            "slack_vs_3x_ms": self.slack_vs_3x_ms,
            "parse_failures": self.parse_failures,
            "degenerates": self.degenerates,
            "strict_pass": self.strict_pass,
            "rescue_pass": self.rescue_pass,
            "format_pass": self.format_pass,
        }


@dataclass(frozen=True, slots=True)
class FrontierPoint:
    delta_correct: int
    accuracy_delta: float
    slack_vs_3x_ms: float
    speedup_cold_over_stream: float
    stream_total_ms: float
    cold_total_ms: float
    dense_sessions: tuple[str, ...]
    strict_pass: bool
    rescue_pass: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "delta_correct": self.delta_correct,
            "accuracy_delta": self.accuracy_delta,
            "slack_vs_3x_ms": self.slack_vs_3x_ms,
            "speedup_cold_over_stream": self.speedup_cold_over_stream,
            "stream_total_ms": self.stream_total_ms,
            "cold_total_ms": self.cold_total_ms,
            "dense_sessions": list(self.dense_sessions),
            "strict_pass": self.strict_pass,
            "rescue_pass": self.rescue_pass,
        }


def _load_jsonl_rows(path: Path) -> list[dict[str, Any]]:
    rows = []
    for line in path.read_text().splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def _group_rows_by_session(path: Path) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in _load_jsonl_rows(path):
        grouped.setdefault(str(row["session_id"]), []).append(row)
    return grouped


def _build_arm_metrics(
    *,
    arm_name: ArmName,
    streaming_jsonl: Path,
    cold_jsonl: Path,
) -> dict[str, SessionArmMetrics]:
    streaming_rows = _group_rows_by_session(streaming_jsonl)
    cold_rows = _group_rows_by_session(cold_jsonl)
    if set(streaming_rows) != set(cold_rows):
        raise ValueError(
            "streaming and cold session ids differ: "
            f"{sorted(set(streaming_rows) ^ set(cold_rows))[:5]}"
        )

    metrics: dict[str, SessionArmMetrics] = {}
    for session_id in sorted(streaming_rows):
        s_rows = sorted(streaming_rows[session_id], key=lambda row: int(row["q_index"]))
        c_rows = sorted(cold_rows[session_id], key=lambda row: int(row["q_index"]))
        if len(s_rows) != len(c_rows):
            raise ValueError(f"session {session_id} has mismatched row counts")
        if [int(row["q_index"]) for row in s_rows] != [int(row["q_index"]) for row in c_rows]:
            raise ValueError(f"session {session_id} has mismatched q_index ordering")

        for s_row, c_row in zip(s_rows, c_rows, strict=True):
            for key in ("session_id", "video_id", "duration", "split", "item_id", "q_index"):
                if s_row.get(key) != c_row.get(key):
                    raise ValueError(
                        f"session {session_id} mismatch on {key}: "
                        f"{s_row.get(key)!r} != {c_row.get(key)!r}"
                    )

        q0_stream = s_rows[0]
        q0_cold = c_rows[0]
        follow_up_stream = s_rows[1:]
        follow_up_cold = c_rows[1:]
        metrics[session_id] = SessionArmMetrics(
            arm_name=arm_name,
            session_id=session_id,
            video_id=str(q0_stream["video_id"]),
            duration=str(q0_stream["duration"]),
            split=str(q0_stream["split"]),
            stream_correct=sum(int(bool(row["correct"])) for row in s_rows),
            cold_correct=sum(int(bool(row["correct"])) for row in c_rows),
            q0_stream_correct=int(bool(q0_stream["correct"])),
            q0_cold_correct=int(bool(q0_cold["correct"])),
            follow_up_stream_correct=sum(int(bool(row["correct"])) for row in follow_up_stream),
            follow_up_cold_correct=sum(int(bool(row["correct"])) for row in follow_up_cold),
            stream_total_ms=sum(float(row["end_to_end_ms"]) for row in s_rows),
            cold_total_ms=sum(float(row["end_to_end_ms"]) for row in c_rows),
            parse_failures=sum(int(bool(row.get("parse_failure", False))) for row in s_rows),
            degenerates=sum(int(bool(row.get("degenerate", False))) for row in s_rows),
        )
    return metrics


def load_session_pairs(
    *,
    pruned_streaming_jsonl: Path,
    pruned_cold_jsonl: Path,
    dense_streaming_jsonl: Path,
    dense_cold_jsonl: Path,
) -> dict[str, SessionPair]:
    pruned = _build_arm_metrics(
        arm_name="pruned_q0",
        streaming_jsonl=pruned_streaming_jsonl,
        cold_jsonl=pruned_cold_jsonl,
    )
    dense = _build_arm_metrics(
        arm_name="dense_q0",
        streaming_jsonl=dense_streaming_jsonl,
        cold_jsonl=dense_cold_jsonl,
    )
    if set(pruned) != set(dense):
        raise ValueError(
            "pruned and dense session ids differ: "
            f"{sorted(set(pruned) ^ set(dense))[:5]}"
        )

    session_pairs: dict[str, SessionPair] = {}
    for session_id in sorted(pruned):
        pruned_arm = pruned[session_id]
        dense_arm = dense[session_id]
        for key in ("video_id", "duration", "split"):
            if getattr(pruned_arm, key) != getattr(dense_arm, key):
                raise ValueError(
                    f"session {session_id} metadata mismatch on {key}: "
                    f"{getattr(pruned_arm, key)!r} != {getattr(dense_arm, key)!r}"
                )
        session_pairs[session_id] = SessionPair(
            session_id=session_id,
            video_id=pruned_arm.video_id,
            duration=pruned_arm.duration,
            split=pruned_arm.split,
            pruned_q0=pruned_arm,
            dense_q0=dense_arm,
        )
    return session_pairs


def evaluate_policy(
    *,
    session_pairs: dict[str, SessionPair],
    name: str,
    deployable: bool,
    description: str,
    choose_arm: Any,
) -> PolicyResult:
    dense_sessions: list[str] = []
    n_sessions = len(session_pairs)
    n_queries = 0
    stream_correct = 0
    cold_correct = 0
    q0_stream_correct = 0
    q0_cold_correct = 0
    follow_up_stream_correct = 0
    follow_up_cold_correct = 0
    stream_total_ms = 0.0
    cold_total_ms = 0.0
    parse_failures = 0
    degenerates = 0

    for session_id in sorted(session_pairs):
        pair = session_pairs[session_id]
        arm_name = choose_arm(pair)
        if arm_name not in ("pruned_q0", "dense_q0"):
            raise ValueError(f"policy {name} chose unsupported arm {arm_name!r}")
        arm = pair.pruned_q0 if arm_name == "pruned_q0" else pair.dense_q0
        if arm_name == "dense_q0":
            dense_sessions.append(session_id)
        n_queries += 3
        stream_correct += arm.stream_correct
        cold_correct += arm.cold_correct
        q0_stream_correct += arm.q0_stream_correct
        q0_cold_correct += arm.q0_cold_correct
        follow_up_stream_correct += arm.follow_up_stream_correct
        follow_up_cold_correct += arm.follow_up_cold_correct
        stream_total_ms += arm.stream_total_ms
        cold_total_ms += arm.cold_total_ms
        parse_failures += arm.parse_failures
        degenerates += arm.degenerates

    delta_correct = stream_correct - cold_correct
    speedup = cold_total_ms / stream_total_ms
    strict_pass = abs(delta_correct / n_queries) <= 0.05 and speedup >= 3.0
    rescue_pass = (delta_correct / n_queries) >= -0.10 and speedup >= 3.0
    format_pass = parse_failures == 0 and degenerates == 0
    return PolicyResult(
        name=name,
        deployable=deployable,
        description=description,
        dense_sessions=tuple(dense_sessions),
        n_sessions=n_sessions,
        n_queries=n_queries,
        stream_correct=stream_correct,
        cold_correct=cold_correct,
        delta_correct=delta_correct,
        q0_stream_correct=q0_stream_correct,
        q0_cold_correct=q0_cold_correct,
        q0_delta_correct=q0_stream_correct - q0_cold_correct,
        follow_up_stream_correct=follow_up_stream_correct,
        follow_up_cold_correct=follow_up_cold_correct,
        follow_up_delta_correct=follow_up_stream_correct - follow_up_cold_correct,
        stream_total_ms=stream_total_ms,
        cold_total_ms=cold_total_ms,
        speedup_cold_over_stream=speedup,
        slack_vs_3x_ms=cold_total_ms - (3.0 * stream_total_ms),
        parse_failures=parse_failures,
        degenerates=degenerates,
        strict_pass=strict_pass,
        rescue_pass=rescue_pass,
        format_pass=format_pass,
    )


def duration_policy(
    dense_durations: set[str],
) -> Any:
    def choose_arm(pair: SessionPair) -> ArmName:
        return "dense_q0" if pair.duration in dense_durations else "pruned_q0"

    return choose_arm


def q0_gain_oracle(pair: SessionPair) -> ArmName:
    if pair.dense_q0.q0_stream_correct > pair.pruned_q0.q0_stream_correct:
        return "dense_q0"
    return "pruned_q0"


def session_gain_oracle(pair: SessionPair) -> ArmName:
    if pair.dense_q0.stream_correct > pair.pruned_q0.stream_correct:
        return "dense_q0"
    return "pruned_q0"


def _frontier_point_from_choices(
    *,
    session_pairs: dict[str, SessionPair],
    chosen_arms: dict[str, ArmName],
) -> FrontierPoint:
    stream_total_ms = 0.0
    cold_total_ms = 0.0
    delta_correct = 0
    dense_sessions: list[str] = []
    for session_id in sorted(session_pairs):
        pair = session_pairs[session_id]
        arm_name = chosen_arms[session_id]
        arm = pair.pruned_q0 if arm_name == "pruned_q0" else pair.dense_q0
        if arm_name == "dense_q0":
            dense_sessions.append(session_id)
        stream_total_ms += arm.stream_total_ms
        cold_total_ms += arm.cold_total_ms
        delta_correct += arm.delta_correct

    n_queries = 3 * len(session_pairs)
    speedup = cold_total_ms / stream_total_ms
    accuracy_delta = delta_correct / n_queries
    strict_pass = abs(accuracy_delta) <= 0.05 and speedup >= 3.0
    rescue_pass = accuracy_delta >= -0.10 and speedup >= 3.0
    return FrontierPoint(
        delta_correct=delta_correct,
        accuracy_delta=accuracy_delta,
        slack_vs_3x_ms=cold_total_ms - (3.0 * stream_total_ms),
        speedup_cold_over_stream=speedup,
        stream_total_ms=stream_total_ms,
        cold_total_ms=cold_total_ms,
        dense_sessions=tuple(dense_sessions),
        strict_pass=strict_pass,
        rescue_pass=rescue_pass,
    )


def compute_exact_frontier(
    session_pairs: dict[str, SessionPair],
) -> dict[str, FrontierPoint | None]:
    @dataclass(slots=True)
    class State:
        slack_ms: float
        choices: dict[str, ArmName]

    best: dict[int, State] = {0: State(slack_ms=0.0, choices={})}
    for session_id in sorted(session_pairs):
        pair = session_pairs[session_id]
        next_best: dict[int, State] = {}
        for delta_so_far, state in best.items():
            for arm_name, arm in (
                ("pruned_q0", pair.pruned_q0),
                ("dense_q0", pair.dense_q0),
            ):
                delta = delta_so_far + arm.delta_correct
                slack_ms = state.slack_ms + arm.slack_vs_3x_ms
                existing = next_best.get(delta)
                if existing is None or slack_ms > existing.slack_ms:
                    choices = dict(state.choices)
                    choices[session_id] = arm_name
                    next_best[delta] = State(slack_ms=slack_ms, choices=choices)
        best = next_best

    frontier_by_delta: dict[int, FrontierPoint] = {}
    for delta_correct, state in best.items():
        frontier_by_delta[delta_correct] = _frontier_point_from_choices(
            session_pairs=session_pairs,
            chosen_arms=state.choices,
        )

    strict_candidates = [
        point for point in frontier_by_delta.values() if point.strict_pass
    ]
    rescue_candidates = [
        point for point in frontier_by_delta.values() if point.rescue_pass
    ]
    return {
        "best_strict": max(strict_candidates, key=lambda point: point.accuracy_delta, default=None),
        "best_rescue": max(rescue_candidates, key=lambda point: point.accuracy_delta, default=None),
        "best_speed_at_or_above_rescue_floor": max(
            (
                point
                for point in frontier_by_delta.values()
                if point.accuracy_delta >= -0.10
            ),
            key=lambda point: point.speedup_cold_over_stream,
            default=None,
        ),
        "best_accuracy_at_or_above_3x": max(
            (
                point
                for point in frontier_by_delta.values()
                if point.speedup_cold_over_stream >= 3.0
            ),
            key=lambda point: point.accuracy_delta,
            default=None,
        ),
    }


def build_policy_suite(session_pairs: dict[str, SessionPair]) -> list[PolicyResult]:
    results = [
        evaluate_policy(
            session_pairs=session_pairs,
            name="all_pruned_q0",
            deployable=True,
            description="Original 1.30 streaming stack: pruned Q0 and pruned follow-ups.",
            choose_arm=lambda pair: "pruned_q0",
        ),
        evaluate_policy(
            session_pairs=session_pairs,
            name="all_dense_q0",
            deployable=True,
            description="1.30W boundary policy: dense Q0, pruned follow-ups.",
            choose_arm=lambda pair: "dense_q0",
        ),
    ]
    duration_sets = [
        {"short"},
        {"medium"},
        {"long"},
        {"short", "medium"},
        {"short", "long"},
        {"medium", "long"},
    ]
    for dense_durations in duration_sets:
        tag = "_".join(sorted(dense_durations))
        results.append(
            evaluate_policy(
                session_pairs=session_pairs,
                name=f"dense_on_{tag}",
                deployable=True,
                description=(
                    "Dense Q0 only on duration bucket(s): "
                    + ", ".join(sorted(dense_durations))
                    + "."
                ),
                choose_arm=duration_policy(dense_durations),
            )
        )
    results.extend(
        [
            evaluate_policy(
                session_pairs=session_pairs,
                name="oracle_q0_gain",
                deployable=False,
                description=(
                    "Upper bound: choose dense Q0 only on sessions where it "
                    "improves Q0 correctness."
                ),
                choose_arm=q0_gain_oracle,
            ),
            evaluate_policy(
                session_pairs=session_pairs,
                name="oracle_session_gain",
                deployable=False,
                description=(
                    "Upper bound: choose dense Q0 only on sessions where it "
                    "improves total session correctness."
                ),
                choose_arm=session_gain_oracle,
            ),
        ]
    )
    return results


def analyze_admission_frontier(
    *,
    pruned_streaming_jsonl: Path,
    pruned_cold_jsonl: Path,
    dense_streaming_jsonl: Path,
    dense_cold_jsonl: Path,
) -> dict[str, Any]:
    session_pairs = load_session_pairs(
        pruned_streaming_jsonl=pruned_streaming_jsonl,
        pruned_cold_jsonl=pruned_cold_jsonl,
        dense_streaming_jsonl=dense_streaming_jsonl,
        dense_cold_jsonl=dense_cold_jsonl,
    )
    policies = build_policy_suite(session_pairs)
    frontier = compute_exact_frontier(session_pairs)
    return {
        "phase": "1.30X",
        "n_sessions": len(session_pairs),
        "n_queries": 3 * len(session_pairs),
        "policy_results": [result.to_dict() for result in policies],
        "exact_frontier": {
            key: (point.to_dict() if point is not None else None)
            for key, point in frontier.items()
        },
    }
