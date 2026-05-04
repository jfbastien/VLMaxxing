"""Bucketing helpers for session / streaming protocol experiments.

The paper's session-style experiments need a stable way to summarize paired
baseline-vs-streaming outcomes without burying the raw per-query records.
These helpers keep the policy explicit and testable:

- ``degenerate`` means the streaming arm failed to emit a usable multiple-choice
  answer or emitted a known pathological marker.
- ``clean`` means the streaming arm stayed behaviorally aligned with the cold
  baseline on the same query.
- ``mixed`` covers the remaining non-degenerate disagreements.
"""

from __future__ import annotations

from collections.abc import Iterable

DEFAULT_DEGENERATE_MARKERS: tuple[str, ...] = (
    "addCriterion",
    "自动生成",  # "auto-generated"; observed unrepaired C-PERSIST basin marker.
)


def is_degenerate_response(
    *,
    text: str,
    parse_failure: bool,
    markers: Iterable[str] = DEFAULT_DEGENERATE_MARKERS,
) -> bool:
    """Return True when the response should count as degenerate.

    For this repo's multiple-choice evaluation, parse failure is already a
    strong enough degeneracy signal. Marker checks keep the same pathological
    strings visible even if a future parser were to become more permissive.
    """

    if parse_failure:
        return True
    return any(marker in text for marker in markers)


def classify_streaming_pair(
    *,
    cold_choice: str | None,
    cold_correct: bool,
    streaming_choice: str | None,
    streaming_correct: bool,
    streaming_parse_failure: bool,
    streaming_text: str,
    markers: Iterable[str] = DEFAULT_DEGENERATE_MARKERS,
) -> str:
    """Bucket a cold-vs-streaming pair as clean, mixed, or degenerate."""

    if is_degenerate_response(
        text=streaming_text,
        parse_failure=streaming_parse_failure,
        markers=markers,
    ):
        return "degenerate"

    if cold_choice == streaming_choice and cold_correct == streaming_correct:
        return "clean"

    return "mixed"
