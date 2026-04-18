"""Tests for :mod:`codec_through.memory_guard`.

The guard is the last line of defense against a repeat of the 2026-04-18
50GB OOM incident. Keep it MLX-free and deterministic so these tests run
on any host.
"""

from __future__ import annotations

import pytest

from codec_through import memory_guard


def test_rss_mb_positive() -> None:
    mb = memory_guard.rss_mb()
    assert mb > 0, "resident set size must be positive on any live process"
    # 100 TiB is a conservative ceiling that would only be hit if we
    # mis-scaled the unit heuristic; catches bytes-vs-kB regressions.
    assert mb < 100 * 1024 * 1024


def test_check_rss_guard_disabled_when_threshold_nonpositive() -> None:
    # Both zero and negative must be no-ops regardless of current RSS.
    memory_guard.check_rss_guard(0, stage="test_noop_zero")
    memory_guard.check_rss_guard(-1, stage="test_noop_negative")


def test_check_rss_guard_passes_when_under_threshold() -> None:
    # Pick a ceiling well above any sane test-process RSS (1 PiB worth of MiB).
    memory_guard.check_rss_guard(1 << 30, stage="test_pass")


def test_check_rss_guard_trips_when_above_threshold() -> None:
    with pytest.raises(RuntimeError, match=r"RSS guard tripped at test_trip"):
        memory_guard.check_rss_guard(1, stage="test_trip")


def test_check_rss_guard_error_includes_stage_and_values() -> None:
    with pytest.raises(RuntimeError) as excinfo:
        memory_guard.check_rss_guard(1, stage="after_item_7")
    message = str(excinfo.value)
    assert "after_item_7" in message
    assert "threshold 1 MiB" in message
    assert "Abort before OOM" in message
