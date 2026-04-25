from __future__ import annotations


def reprefill_k_for_query(
    *,
    q_index: int,
    default_reprefill_k: int,
    q2_reprefill_k: int | None,
    q3_reprefill_k: int | None,
) -> int:
    """Resolve a position-conditioned selective re-prefill policy.

    Q1 is always cold (`0`). Q2 and Q3 may override the default fixed-K
    setting independently, allowing adaptive policies like "K=1 on Q2,
    K=0 on Q3" without changing the underlying reprefill mechanism.
    """

    if q_index < 0:
        raise ValueError(f"q_index must be non-negative, got {q_index}")
    if default_reprefill_k < 0:
        raise ValueError(f"default_reprefill_k must be non-negative, got {default_reprefill_k}")
    for name, value in (("q2_reprefill_k", q2_reprefill_k), ("q3_reprefill_k", q3_reprefill_k)):
        if value is not None and value < 0:
            raise ValueError(f"{name} must be non-negative, got {value}")

    if q_index == 0:
        return 0
    if q_index == 1 and q2_reprefill_k is not None:
        return int(q2_reprefill_k)
    if q_index == 2 and q3_reprefill_k is not None:
        return int(q3_reprefill_k)
    return int(default_reprefill_k)
