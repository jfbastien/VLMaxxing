"""Resident-set-size (RSS) safety net for long-running benchmark drivers.

Introduced 2026-04-18 after a 1.51R novelty-pruning pilot on a 16GB M3 Air
was killed by the macOS kernel at ~50 GB RSS (swap thrash + eventual OOM).
Root cause was fixed in commit 1e01a3b (bounded 2-pass video decode +
inter-generate cache clears), but a cheap trip-wire in user-space lets
future runs abort with a clear diagnostic before the kernel does anything
drastic.

Kept deliberately MLX-free so it can be imported from any driver regardless
of accelerator availability, and so unit tests can exercise it on any host.
"""

from __future__ import annotations

import resource


def rss_mb() -> float:
    """Return resident-set size of the current process in MiB.

    Normalizes the macOS/Linux difference for ``ru_maxrss`` (macOS returns
    bytes, Linux returns kibibytes) by reading the magnitude: anything over
    1 GB worth of raw units is assumed to be bytes, otherwise kibibytes.
    That heuristic is safe as long as one of the two assumptions is true on
    the host, which it always is for supported POSIX platforms.
    """
    usage = resource.getrusage(resource.RUSAGE_SELF)
    raw = float(usage.ru_maxrss)
    return raw / (1024 * 1024) if raw > 1e9 else raw / 1024


def check_rss_guard(threshold_mb: int, *, stage: str) -> None:
    """Raise ``RuntimeError`` if RSS exceeds ``threshold_mb`` MiB.

    Called at well-defined stage boundaries (after model load, after each
    benchmark item) so a runaway driver aborts in Python with a readable
    message rather than getting SIGKILL'd by the OS.

    ``threshold_mb <= 0`` disables the guard (default). The ``stage`` string
    is included in the error message to locate where the blow-up happened.
    """
    if threshold_mb <= 0:
        return
    current_mb = rss_mb()
    if current_mb > threshold_mb:
        raise RuntimeError(
            f"RSS guard tripped at {stage}: {current_mb:.0f} MiB "
            f"> threshold {threshold_mb} MiB. Abort before OOM."
        )
