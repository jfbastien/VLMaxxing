"""SWA-aware safety wrapper for mlx-vlm cross-turn cache reuse.

Investigation result (see
`research/experiments/2026/2026-04-29-phase-M5-5-sam-swa-aware-cache-findings.md`):

mlx-vlm 0.4.4's `PromptCacheState` cross-turn reuse path
(`generate.py:687-697`) does an unconditional
`keys[:, :, :prefix_len, :]` trim across all layers' KV caches. For
Gemma 4 26B-A4B's text tower, 25 of 30 layers are
`RotatingKVCache(max_size=1024)` (sliding-window attention) and 5 are
`KVCache()` (full attention). The trim is correct for the 5 full-
attention layers and silently corrupts the 25 SWA layers (their
rotating buffer doesn't have a positional `keys[:, :, :N, :]` slice).

There is no purely-wrapper-level fix that delivers both correctness
and speedup for this architecture: the SWA layers store at most the
last `sliding_window` tokens, and reusing their state across turns
requires either (a) re-prefilling them from the full original input
ids on each turn (no speedup vs cold dense, since the prefill cost is
dominated by SWA layers in lockstep with full-attention layers), or
(b) modifying the model forward to support asymmetric per-layer
cached prefix lengths (model-internal change).

This module provides a **safety wrapper** -- not a perf fix. Two
helpers:

  * `is_mixed_swa_topology(model)` -- True if the model has any
    `RotatingKVCache` layer (Gemma 4 26B-A4B does).
  * `safe_run_dense(harness, ...)` -- forces a cold-dense run by
    refusing to pass `prompt_cache_state`. Same answer as cold dense,
    no speedup, no broken-cache footgun.

Use this for any deployment scenario on Gemma 4 26B-A4B / mlx-vlm
0.4.4 where the alternative is a silently-corrupted answer.
"""

from __future__ import annotations

from typing import Any


def is_mixed_swa_topology(model: Any) -> bool:
    """Return True if the model's text-tower configuration has any
    sliding-window attention layer."""
    cfg = getattr(model, "config", None)
    if cfg is None:
        return False
    text_cfg = getattr(cfg, "text_config", cfg)
    layer_types = getattr(text_cfg, "layer_types", None)
    if layer_types is None:
        return False
    for layer_type in layer_types:
        if isinstance(layer_type, str) and "sliding" in layer_type.lower():
            return True
    return False


def cache_topology_summary(model: Any) -> dict[str, Any]:
    """Return a dict describing the model's KV cache topology."""
    cfg = getattr(model, "config", None)
    if cfg is None:
        return {"layer_types": "unknown"}
    text_cfg = getattr(cfg, "text_config", cfg)
    layer_types = getattr(text_cfg, "layer_types", None)
    sliding_window = getattr(text_cfg, "sliding_window", None)
    if layer_types is None:
        return {
            "n_layers": getattr(text_cfg, "num_hidden_layers", 0),
            "sliding_window": sliding_window,
            "layer_types": "uniform",
        }
    return {
        "n_layers": len(layer_types),
        "sliding_window": sliding_window,
        "layer_types": list(layer_types),
        "n_sliding": sum(1 for t in layer_types if "sliding" in str(t).lower()),
        "n_full": sum(1 for t in layer_types if "full" in str(t).lower()),
    }


class SafePromptCacheState:
    """Drop-in replacement for `mlx_vlm.generate.PromptCacheState` that
    NEVER reports a cached prefix and stores nothing.

    When passed to `stream_generate(..., prompt_cache_state=...)`, the
    library's prefix-match check (`find_prefix_length`) returns 0,
    which causes the broken trim block to be skipped. The model then
    runs a full cold-dense prefill -- correct, but no speedup.

    This is the deployment-safe path for Gemma 4 26B-A4B on mlx-vlm
    0.4.4 until either the upstream library fixes SWA-aware trim or a
    custom model wrapper supports asymmetric per-layer caches.
    """

    def __init__(self) -> None:
        self.cache = None
        self.token_ids = None

    def find_prefix_length(self, new_ids: list) -> int:
        return 0

    def update(self, token_ids: list, kv_cache: list) -> None:
        # Intentionally do nothing -- never persist cache state.
        return None
