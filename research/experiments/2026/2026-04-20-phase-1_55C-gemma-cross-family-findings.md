# Phase 1.55C — Gemma 4-E4B-4bit cross-family probe (FINDINGS)

**Date:** 2026-04-20.
**Parent:** `2026-04-20-phase-1_55C-gemma-cross-family-prereg.md`.
**Verdict:** **INFRASTRUCTURE-FALSIFIED (not scientifically falsified).**
The prereg is not actionable with the current mlx-vlm driver. This
findings doc documents the falsification surface and the path to
actionability.

## Headline

Gemma 4 uses a mixed attention topology: 4 of every 5 transformer
layers use **sliding-window attention** (`RotatingKVCache`,
`max_size=512`); 1 of every 5 uses full attention (`KVCache`). At
realistic video prefills (20 frames ≈ 5120 image tokens + prompt),
sliding-window layers have rotated ~10× past their 512-token cap.

mlx-vlm's `PromptCacheState` prefix-reuse code
(`mlx_vlm/generate.py:689-697`) performs a **naive physical-position
truncation**:

```python
for c in kv_cache:
    if hasattr(c, "keys") and c.keys is not None:
        cached_len = c.keys.shape[2]
        if cached_len > prefix_len:
            c.keys = c.keys[:, :, :prefix_len, :]
            c.values = c.values[:, :, :prefix_len, :]
            if hasattr(c, "offset"):
                c.offset = prefix_len
```

This is **semantically correct for `KVCache` (contiguous linear KV)**
but **semantically incorrect for `RotatingKVCache` once rotation has
begun** (offset ≥ max_size). Post-rotation, physical position 0 is not
temporal token 0; `_temporal_order` maps physical → temporal but is
only invoked on multi-token concat updates, not during the
`_update_in_place` decode path. `RotatingKVCache.is_trimmable()`
returns `self.offset < self.max_size` — i.e., False once rotated —
but the mlx-vlm code **does not consult `is_trimmable()`** before
mutating `c.keys`. The result is **silent corruption of sliding-layer
KV** on prefix reuse; no exception, just wrong-answer output.

Concrete numbers: at Gemma's 256-tokens-per-frame geometry (verified
2026-04-18), 20 frames = 5120 image tokens. `max_size=512` means the
4 sliding-attention layers per group have rotated
⌊5120/512⌋ = 10 full rotations before generation even begins. The
first `prefix_len` physical positions are therefore the most recently
overwritten slots (not the earliest temporal tokens).

**Gate #2 from the prereg — "Verification that mlx-vlm's
`PromptCacheState` + `find_prefix_length` work correctly with Gemma's
attention" — is FALSIFIED at realistic video prefill depths.**

## Evidence

- `mlx_lm/models/cache.py:410-549`: `RotatingKVCache` implementation.
  `_update_in_place` rotates in-place when `_idx == max_size` (line
  498-499); `state` property returns raw physical buffer without
  temporal reorder (line 520-525); `is_trimmable` guards that trim is
  only sound pre-rotation (line 542-543).
- `mlx_vlm/generate.py:689-697`: naive prefix truncation, type-blind.
- `mlx_vlm/models/gemma4/language.py:613-627`: `Model.make_cache()`
  instantiates `RotatingKVCache(max_size=config.sliding_window,
  keep=0)` for every `layer_type == "sliding_attention"`.
- `mlx_vlm/models/gemma4/config.py:81-114`: `sliding_window=512`,
  `sliding_window_pattern=5` (4 sliding + 1 full, repeating).
- Phase 1.57 memory (2026-04-18): Gemma 4-E4B emits 256 image tokens
  per frame (16×16 grid). Validated at 8/16/32f in the Qwen/Gemma
  feature-drift probe.
- Phase 1.55A landed numbers for Qwen 7B at 20f: 5600 image tokens
  prefilled, speedup 134×, prefix 0.993. Qwen uses only `KVCache` per
  Qwen-VL-2.5 architecture — no sliding-window, no rotation, so
  prefix truncation is sound there. That is why 1.55A worked.

## Why this was not caught earlier

The Phase 1.55C prereg (2026-04-20) flagged gate #2 as "may not hold
across image tokens without custom handling" but framed it as a
potential interleaved-attention issue. The **actual** hazard turned
out to be sliding-window rotation, which is orthogonal to the
multimodal interleave concern. The prereg's 30-min implementation
estimate was based on an assumed drop-in compatibility that does not
hold.

## What IS and IS NOT falsified

**FALSIFIED:** The prereg's implicit assumption that mlx-vlm's
`PromptCacheState` is drop-in compatible with Gemma 4's attention at
video prefill depths.

**NOT FALSIFIED (still scientifically open):**
- H1-Gemma (speedup): untested. The speedup question would need the
  fixed driver to answer.
- H2-Gemma.{3B-match, 7B-match, novel-geometry}: untested. The
  three-way failure-geometry sort is the scientific payload; it
  cannot be answered with a driver that silently corrupts the KV
  state on 4/5 of Gemma's layers.
- H3-Gemma (prefix coverage): untested.
- H4-Gemma (RSS ≤ 8 GB): untested.

All H1-H4 remain preregistered for re-run once a correctness-
preserving driver is available.

## Path to actionability

Three options, ranked by effort and correctness:

### Option A: Fork `PromptCacheState` to be cache-type-aware (~2-4 h)

Modify `mlx_vlm/generate.py:689-697` to branch on cache instance:

```python
for c in kv_cache:
    if isinstance(c, KVCache):
        # Current code: safe for linear caches
        ...
    elif isinstance(c, RotatingKVCache):
        if c.is_trimmable():
            # Pre-rotation: naive slice is correct
            ...
        else:
            # Post-rotation: KV at these positions is the sliding
            # window over the PRIOR prefill; by sliding-attention
            # semantics it still approximates the last-512 tokens
            # of that prefill. If the new prefill shares a long
            # prefix, the sliding window over shared+new is close
            # to the sliding window over the new prefill alone.
            # Correct behavior: DO NOT truncate; keep the cache
            # as-is, rely on the new decode's attention mask to
            # handle the sliding.
            pass
```

Open correctness question for option A: the post-rotation sliding
window contains K/V computed against the PRIOR prefix's RoPE
positions. On reuse with a new (partially-matching) prefix, the RoPE
indexing for the retained window is from the prior run. Whether
Gemma's RoPE positioning invariant survives this is non-trivial. A
small smoke test (same prefix → same output, differing prefix in
shared region → accuracy ≥ baseline) is required before trusting
results.

### Option B: Disable cache reuse on sliding layers, reuse only the 1/5 full-attention layers (~1 h)

Simpler correctness: pass a filtered cache list to `prompt_cache`
containing only the full-attention layers; sliding layers get fresh
`RotatingKVCache()` each turn and re-prefill from scratch. Loses most
of the speedup (re-prefill dominates), so H1-Gemma would measure a
much smaller speedup than 1.55A's 130×. Changes the scientific
question from "persistent-KV fidelity across families" to "partial-
layer persistent-KV fidelity" — paper-wise, a different claim.

### Option C: Prefill-depth ≤ 512 tokens (~0 h driver work, but useless)

Any prefill that fits in one sliding window (max ~1-2 frames of video
or a text-only prompt) avoids rotation entirely. This is the only
option where the current mlx-vlm driver produces correct output on
Gemma. For a VLM video benchmark this is a non-starter; at 2 frames
the task itself degenerates.

## Recommended disposition

1. **Do NOT run 1.55C with the current driver.** It would produce
   garbage outputs that look plausible (Gemma is still a capable
   model; it will emit clean letter tokens on many single-shot queries
   even with corrupted sliding-layer KV). This is the worst possible
   outcome for a fidelity probe — silent wrong-answer at the
   experimental layer.
2. **Keep 1.55C preregistered.** The scientific question (cross-
   family parametrization of the 3-D decomposition) remains the right
   next experiment IF a correctness-preserving driver is built.
3. **Defer 1.55C behind 1.55D.** Phase 1.55D selective re-prefill
   (preregistered 2026-04-20) is on Qwen, where `KVCache` is the only
   cache type and prefix truncation is sound; it can proceed
   immediately and directly addresses the fidelity-recovery gap from
   1.55A's temperature probes. 1.55C can return to the queue after
   1.55D lands, either as (a) option-A fork work with a smoke test
   or (b) a re-prereg with Gemma 2 (which is non-sliding) as the
   cross-family target instead.

## Implication for the paper

Claim #14 (3-D decomposition) remains Qwen-family-only for this
draft. The paper should **declare cross-family generalization as an
open question**, not as an unrun experiment the authors "plan" to
do. An explicit footnote citing Gemma 4's sliding-window
incompatibility with mlx-vlm's current prefix-truncation contract is
appropriate — it communicates both the scientific boundary and the
infrastructure-side reason.

## Next steps

1. **1.55D selective re-prefill** (preregistered, P1, this is now the
   top-priority experiment). No driver blocker; known-compatible on
   Qwen. Targets Δacc ≤ −0.15 at K=4 on 7B-20f with ≥ 15× speedup
   retained.
2. **1.55C deferred** pending either driver fork (option A) or prereg
   rescope (Gemma 2 cross-family replacement). Not on the critical
   path for this paper.

## Artifact paths

- Findings doc: this file.
- Source evidence:
  - `mlx_lm/models/cache.py:410-549` (RotatingKVCache)
  - `mlx_vlm/generate.py:689-697` (naive prefix truncation)
  - `mlx_vlm/models/gemma4/language.py:613-627` (Gemma cache assembly)
  - `mlx_vlm/models/gemma4/config.py:81-114` (sliding_window=512)

No experimental artifacts (session/baseline JSONL) because no
experiment was run — the pre-run driver verification step surfaced
the blocker.
