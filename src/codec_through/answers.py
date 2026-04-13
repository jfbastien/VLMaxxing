"""Helpers for parsing benchmark-style multiple-choice model outputs."""

from __future__ import annotations

import re
from collections.abc import Sequence

LETTER_PATTERN = re.compile(r"\b([A-Z])\b")
CLAUSE_TERMINATOR_PATTERN = re.compile(r"[.!?\n]")


def extract_choice(response: str, candidates: Sequence[str]) -> int | None:
    """Return the parsed answer index or ``None`` if parsing failed.

    The original benchmark scripts in ``codec-through-sam`` defaulted to option A
    on parse failure. That can hide real disagreement. This version fails closed.
    """

    normalized = response.strip().upper()
    for index in range(len(candidates)):
        letter = chr(ord("A") + index)
        if normalized.startswith(letter):
            return index

    first_clause = CLAUSE_TERMINATOR_PATTERN.split(normalized, maxsplit=1)[0]
    candidate_letters = {
        ord(match.group(1)) - ord("A")
        for match in LETTER_PATTERN.finditer(first_clause)
        if 0 <= (ord(match.group(1)) - ord("A")) < len(candidates)
    }
    if len(candidate_letters) == 1:
        return next(iter(candidate_letters))
    if len(candidate_letters) > 1:
        return None

    lowered = response.lower()
    matching_candidates = [
        index for index, candidate in enumerate(candidates) if candidate.lower() in lowered
    ]
    if len(matching_candidates) == 1:
        return matching_candidates[0]

    return None
