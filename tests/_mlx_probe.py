"""Runtime probe for MLX Metal usability.

``pytest.importorskip("mlx.core")`` is the natural way to gate Apple-only
tests, but on some hosts (notably sandboxes without Metal device access)
importing ``mlx.core`` triggers an ObjC ``NSRangeException`` during
``mlx::core::metal::Device`` construction that calls ``abort()``. Because
the abort happens in C++, Python's exception machinery (including
``importorskip``) cannot catch it — pytest crashes mid-collection and no
tests from any module after the crash point get to run.

This helper sidesteps the issue by performing the import + a minimal
tensor-creation call in a subprocess. A clean exit means MLX is usable;
any other outcome (non-zero, SIGABRT, timeout) is treated as unusable and
the caller should skip the test module.
"""

from __future__ import annotations

import subprocess
import sys

_PROBE_SNIPPET = "import mlx.core as mx; mx.random.key(0)"

_cached_result: bool | None = None


def mlx_is_usable(timeout_s: float = 10.0) -> bool:
    """Return True if ``mlx.core`` imports and initializes Metal cleanly.

    Result is cached per-process so the subprocess spawn is paid at most
    once per pytest session.
    """
    global _cached_result
    if _cached_result is not None:
        return _cached_result
    try:
        completed = subprocess.run(
            [sys.executable, "-c", _PROBE_SNIPPET],
            capture_output=True,
            timeout=timeout_s,
        )
    except subprocess.TimeoutExpired:
        _cached_result = False
        return False
    _cached_result = completed.returncode == 0
    return _cached_result
