from __future__ import annotations


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
