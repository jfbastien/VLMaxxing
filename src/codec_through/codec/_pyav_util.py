"""PyAV decode helpers shared across VLMaxxing's codec surfaces.

Ported from a predecessor prototype's robust reformat helper. Under
Metal/MLX memory pressure PyAV's sws_scale path can intermittently
return `EAGAIN` on `frame.to_ndarray(...)`; a short back-off plus
explicit `gc.collect()` typically clears the allocator and the retry
succeeds. Without it, pixel-diff and codec extraction both fail
sporadically on the same clips they would normally decode fine.
"""

from __future__ import annotations

import gc
import time
from typing import TYPE_CHECKING

import av
import numpy as np

if TYPE_CHECKING:  # pragma: no cover
    from av.video.frame import VideoFrame


_MAX_ATTEMPTS = 8
_BASE_BACKOFF_S = 0.02


def robust_reformat(frame: VideoFrame, *, format: str) -> np.ndarray:
    """Call `frame.to_ndarray(format=...)` with EAGAIN-tolerant retry.

    Retries up to 8 times with linear back-off (20 ms → 160 ms) and a
    `gc.collect()` between attempts. Re-raises the last BlockingIOError
    if the allocator never clears.
    """
    last_err: av.error.BlockingIOError | None = None
    for attempt in range(_MAX_ATTEMPTS):
        try:
            return frame.to_ndarray(format=format)
        except av.error.BlockingIOError as exc:
            last_err = exc
            gc.collect()
            time.sleep(_BASE_BACKOFF_S * (attempt + 1))
    assert last_err is not None
    raise last_err
