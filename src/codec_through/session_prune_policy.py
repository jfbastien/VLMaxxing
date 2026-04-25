from __future__ import annotations

VALID_DURATIONS = ("short", "medium", "long")


def _normalize_duration(duration: str | None) -> str | None:
    if duration is None:
        return None
    normalized = str(duration).strip().lower()
    if not normalized:
        return None
    if normalized not in VALID_DURATIONS:
        raise ValueError(f"duration must be one of {VALID_DURATIONS}, got {duration!r}")
    return normalized


def keep_rate_for_query(
    *,
    q_index: int,
    default_keep_rate: float,
    first_query_keep_rate: float | None,
    follow_up_keep_rate: float | None,
) -> float:
    """Resolve a query-position-conditioned keep rate.

    The streaming bridge needs one simple adaptive admission baseline:
    dense on Q0, pruned on follow-ups. This helper keeps the policy
    selection logic pure and testable outside the MLX runtime.
    """

    if q_index < 0:
        raise ValueError(f"q_index must be non-negative, got {q_index}")
    if q_index == 0 and first_query_keep_rate is not None:
        return float(first_query_keep_rate)
    if q_index > 0 and follow_up_keep_rate is not None:
        return float(follow_up_keep_rate)
    return float(default_keep_rate)


def keep_rate_for_session_query(
    *,
    q_index: int,
    duration: str | None,
    default_keep_rate: float,
    first_query_keep_rate: float | None,
    follow_up_keep_rate: float | None,
    first_query_keep_rate_short: float | None = None,
    first_query_keep_rate_medium: float | None = None,
    first_query_keep_rate_long: float | None = None,
) -> float:
    """Resolve a keep rate with optional duration-specific Q0 overrides.

    The 1.30 bridge work now needs a duration-conditioned full-union rerun:
    dense Q0 on short/medium, cheaper Q0 on long, and a shared follow-up
    policy. Keep that logic pure here so the MLX runner stays easy to audit.
    """

    normalized_duration = _normalize_duration(duration)
    resolved_first_query_keep_rate = first_query_keep_rate
    if normalized_duration == "short" and first_query_keep_rate_short is not None:
        resolved_first_query_keep_rate = float(first_query_keep_rate_short)
    elif normalized_duration == "medium" and first_query_keep_rate_medium is not None:
        resolved_first_query_keep_rate = float(first_query_keep_rate_medium)
    elif normalized_duration == "long" and first_query_keep_rate_long is not None:
        resolved_first_query_keep_rate = float(first_query_keep_rate_long)

    return keep_rate_for_query(
        q_index=q_index,
        default_keep_rate=default_keep_rate,
        first_query_keep_rate=resolved_first_query_keep_rate,
        follow_up_keep_rate=follow_up_keep_rate,
    )
