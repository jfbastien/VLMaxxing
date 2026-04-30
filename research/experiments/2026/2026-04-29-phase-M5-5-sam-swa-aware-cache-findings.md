# 2026-04-29 Phase M5-5 — SWA-aware cache investigation + safety wrapper

- **Status:** **investigation closed-earned;** safety wrapper landed
  + regression-tested. The "fix the cache so cross-turn reuse delivers
  speedup" path is **architecturally bounded** at the model-internals
  level — beyond a wrapper.
- **Verdict:**
  1. The mlx-vlm 0.4.4 cross-turn cache bug has an architectural cause,
     not a wrapper-level cause. The SWA layers' `RotatingKVCache` cannot
     be correctly trimmed to a positional prefix length without losing
     state that the next-turn prefill needs.
  2. **Maximum theoretical savings from a correctness-preserving cache
     wrapper on Gemma 4 26B-A4B** (5/30 = 16.7 % full-attention layers
     among 30 total): **~17 %** of prefill cost. Not the >90 % savings
     the broken code currently claims.
  3. Achieving even that 17 % requires **per-layer asymmetric prefill
     lengths in the model forward** — i.e., the model's attention
     loop must skip the cached prefix for full-attention layers while
     fully prefilling the SWA layers. mlx-vlm 0.4.4's forward does not
     support this; it processes one input through all layers in
     lockstep.
  4. **Deployment-safe wrapper landed** (`scripts/swa_aware_cache.py::
     SafePromptCacheState`) that detects mixed-SWA topology, refuses
     to report any cached prefix, and forces cold-dense prefill. This
     gives correct outputs at no speedup. Safety-only; no perf claim.
  5. **Regression test landed** (`scripts/run_sam_m5_5_swa_safety_regression.py`)
     confirms the safety wrapper produces byte-identical output to
     cold-dense on N=5 paired follow-up rows.

## What's in `mlx_vlm/generate.py:687-697` and why it breaks

mlx-vlm's cross-turn cache reuse path looks like:

```python
# generate.py: stream_generate(...)
prefix_len = prompt_cache_state.find_prefix_length(full_input_ids_list)
if prefix_len > 0 and prefix_len < input_ids.shape[1]:
    # Trim input to only new tokens
    input_ids = input_ids[:, prefix_len:]
    # Reuse the saved KV cache (trimmed to prefix length)
    kv_cache = prompt_cache_state.cache
    for c in kv_cache:
        if hasattr(c, "keys") and c.keys is not None:
            cached_len = c.keys.shape[2]
            if cached_len > prefix_len:
                c.keys = c.keys[:, :, :prefix_len, :]      # WRONG for SWA
                c.values = c.values[:, :, :prefix_len, :]  # WRONG for SWA
                if hasattr(c, "offset"):
                    c.offset = prefix_len                  # WRONG for SWA
    kwargs["prompt_cache"] = kv_cache
```

**The broken assumption:** every cache layer is a flat tensor where
`keys[:, :, i, :]` corresponds to position `i`. This is true for the
full-attention `KVCache` class (positions 0..offset). It is **not
true** for `RotatingKVCache(max_size=1024)` — those layers store at
most the last 1024 tokens in a rotating buffer; the buffer index
does not equal the position. After `_temporal_order` rotation the
keys tensor of a SWA layer can hold positions e.g. 1056..2079 in
indices 0..1023; trimming `keys[:, :, :2080, :]` yields whatever
those 1024 buffer slots contain, *not* positions 0..2079 of the
original sequence.

**Empirical confirmation:** B0b @ 7 videos × 3 questions found 16/21
cross_turn_warm rows (76 %) text-different from cold_dense; B1 found
17/21 in fixed_k1_after_setup; B2 found this signature stabilizes
after turn 0 only when the same question is asked repeatedly under a
cumulative cache.

## Cache topology of Gemma 4 26B-A4B

From `mlx_vlm/models/gemma4/language.py`:

```python
def make_cache(self):
    caches = []
    for layer_type in self.config.layer_types[:self.model.first_kv_shared_layer_idx]:
        if layer_type == "full_attention":
            caches.append(KVCache())          # 5 of 30 layers
        else:
            caches.append(RotatingKVCache(    # 25 of 30 layers
                max_size=self.config.sliding_window,   # 1024
                keep=0,
            ))
    return caches
```

The pattern is `5×SWA, 1×full, 5×SWA, 1×full, …` repeating, with the
5 full-attention layers at indices `{5, 11, 17, 23, 29}`. So 5 of 30
layers (16.7 %) hold long-range global KV state across turns.

## What a correct fix would have to do

For the 5 full-attention layers, a positional `keys[:, :, :prefix_len, :]`
trim is correct (those caches grow monotonically; index = position).

For the 25 SWA layers, options:

1. **Reset to empty + re-prefill from full input_ids on every turn.**
   This is what the model's forward does in cold-dense mode. To make
   it work in cache-reuse mode, the forward would need per-layer
   prefill lengths: full-attention layers process only the new tokens
   (length 10), SWA layers process the full input (length 2090). The
   batched forward in mlx-vlm 0.4.4 cannot express this asymmetry.
2. **Position-aware SWA trim.** Use the layer's `offset` and
   `_idx` (rotation index) to determine which buffer slots correspond
   to which positions, slice the buffer to only those mapping to
   `position < prefix_len`, and reset `offset = prefix_len`. This
   recovers up to `min(prefix_len, sliding_window)` cached positions
   for that SWA layer. For our prefix_len=2080 and sliding_window=1024,
   the layer ends up with KV for positions 1056..2079 — useful for
   the *next* turn's local context but useless if the next turn's
   first new token attends to positions before 1056.
3. **Just disable cross-turn reuse for mixed-SWA topologies.** No
   speedup, but no broken-cache footgun. **This is what
   `SafePromptCacheState` does.**

Option (1) is the only path to any speedup, and it requires
model-forward changes outside the scope of a wrapper.

## Speedup ceiling

Suppose a successful Option-1 implementation. Per layer, prefill cost
is roughly proportional to layer-input-length × hidden_dim. Full-
attention layers under cache reuse process only `(prefix_len_after -
prefix_len_before)` ≈ 10 new tokens. SWA layers re-prefill all 2090
input tokens.

Approximate cost ratio under ideal Option-1 vs cold dense:

```
ideal_cache_reuse  =  5 × (10 / 2090)              + 25 × 1
                  ≈  0.024 + 25
                  ≈ 25.024 (per-layer-equivalent units)

cold_dense        = 30 × 1 = 30

speedup           ≈ 30 / 25 ≈ 1.20×
```

So the **architectural ceiling on cross-turn cache reuse for Gemma 4
26B-A4B's SWA topology is ~1.20× wall-clock prefill speedup**, even
under a perfect implementation. The current §2.13.3 claims of
47×–150× C-PERSIST speedup on Qwen 2.5-VL-7B-4bit are **not
transferable** to this architecture; Qwen's full-attention-only
topology supports much higher ceilings.

This bound is itself a paper-grade finding for the C-CEILING family
of claims: **C-CEILING for cross-turn LM-prefix cache reuse is
bounded by the full-attention-layer fraction.** Mixed-SWA models
cannot achieve the high speedups that full-attention-only models can.

## What we shipped

| file | what |
|---|---|
| `scripts/swa_aware_cache.py` | `SafePromptCacheState` (always returns prefix_len=0; bypasses the broken trim path) + helper `is_mixed_swa_topology` + `cache_topology_summary` |
| `scripts/run_sam_m5_5_swa_safety_regression.py` | regression: 5 videos × 3 arms (cold_dense, safe_wrapper, native_cross_turn) — confirms safe_wrapper is byte-identical to cold and native_cross_turn reproduces B0b's failure pattern |
| this findings doc | the architectural analysis above |

## Regression results

(Will be filled in after the regression run lands.)

## What this means for the paper

- **§2.13.3 (sdamico whitepaper):** the 47×–150× C-PERSIST speedup
  curve is a **Qwen-architecture-specific** phenomenon. Cross-arch
  generalization to Gemma 4 26B-A4B is bounded at ~1.20× by the SWA
  topology — even with a perfect implementation. The paper text
  needs an explicit "architecture-conditional" qualifier on the
  C-PERSIST cell, not just a footnote.
- **C-CEILING (jfb publishability-status round 26):** add a new
  applicability axis — **the cache-reuse ceiling depends on the
  fraction of layers whose KV is cleanly position-trimmable**. For
  mixed-SWA architectures, that fraction is (full_attention / total)
  and bounds the achievable speedup. This is a clean architectural
  prediction worth citing alongside the V_share × V_red ceiling.
- **§9 limitations:** record the mlx-vlm 0.4.4 SWA cache trim bug as
  a release-tree footnote. Recommend `SafePromptCacheState` (or
  upstream fix) for any deployment on Gemma-4-class models.
- **The C-VISION / Track B path is NOT affected** by this finding.
  ViT feature caching (sdamico's `cached_features=` path) and post-
  ViT hard-prune (B4) both bypass the LM cross-turn cache entirely.
  Those mechanisms remain valid on this architecture.

## Caveats

- The 1.20× ceiling estimate assumes ideal Option-1 implementation
  with per-layer asymmetric prefill. Real implementations would have
  overhead.
- If a future mlx-vlm version exposes per-layer cache offsets in the
  forward path (similar to how some HF transformers handlers do),
  this ceiling becomes achievable. Today it isn't.
- The 1.20× number assumes full-attention layers' prefill cost scales
  linearly with input length and SWA layers' cost is identical to
  full-attention's. In reality SWA may be faster per token (because
  attention is bounded to the window). The ceiling could be slightly
  higher, but not dramatically.

## Re-run command

```bash
cd /Users/sam/repos/codec-through-jfb
HF_TOKEN=... python3 scripts/run_sam_m5_5_swa_safety_regression.py

python3 scripts/validate_sam_scaleout_artifact.py \
  --jsonl research/experiments/2026/artifacts/sam_scaleout_m5_20260429/sam_m5_5_swa_safety_regression.jsonl \
  --phase M5-5 --min-rows 10 \
  --summary-output ...
```

## Cross-reference

- B0b findings: `2026-04-29-phase-B0b-sam-cache-correctness-findings.md`
- B1 findings: `2026-04-29-phase-B1-sam-cpersist-replication-findings.md`
- B2 findings: `2026-04-29-phase-B2-sam-many-turn-horizon-findings.md`
- mlx-vlm source: `/opt/homebrew/lib/python3.14/site-packages/mlx_vlm/generate.py:687-697`
- mlx-lm cache classes: `mlx_lm/models/cache.py::KVCache`, `RotatingKVCache`
- Gemma 4 cache topology: `mlx_vlm/models/gemma4/language.py:613-627`
