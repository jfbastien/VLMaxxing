# FastV × Temporal Feature Reuse: Composition Implementation Plan

Author: Claude, 2026-04-16 (phase 1.23 scouting)

This document is the implementation-scouting output for composing FastV-style
decoder-side token pruning with this repo's training-free temporal feature
reuse on the Qwen 2.5-VL MLX stack. No code has been written or benchmarked
for FastV in this repo as of 2026-04-16.

## Why compose

Temporal reuse (our method) reduces compute **at the encoder side**: the
vision encoder runs only on non-redundant blocks per frame, and reused
features are mixed in after encode. FastV reduces compute **at the decoder
side**: after layer K of the LLM, the lowest-attention-score vision tokens
are dropped so subsequent layers run on a shorter sequence.

These are orthogonal axes of reduction. A first-order cost model
suggests they may stack, but the arithmetic is only approximate until
measured on the same MLX path:

- Temporal reuse at 0.7 active-reuse ratio cuts pre-decode vision-token
  compute by ~30% (order-of-magnitude estimate from our measured
  `mean_active_reuse`).
- FastV at K=2, R=50% cuts post-layer-K decoder compute by ~50% on the
  vision-token columns only (reported by the FastV paper on
  LLaVA-1.5).
- Together: order-of-magnitude ~15% of the dense-all-frames
  all-tokens baseline in vision compute columns. This is NOT a
  measured result.

This is a historical composition scout. Current claim status lives in
`paper/claim-matrix.md`; do not treat this plan as an active release gate.

## Current repo state (encoder-side)

- Vision encoder runs per frame (with temporal reuse caching dense features
  per block); the mixed feature tensor is concatenated and fed to the LLM
  as vision tokens.
- Token count per frame after spatial merge: configurable via
  `qwen_merged_token_counts`. A single 560×560 frame at spatial_merge=2
  produces 20×20/4 = 100 tokens.
- Mixing happens before the LLM call in
  `scripts/run_benchmark_track_a.py::_mix_qwen_features`. The LLM sees a
  single flat vision-token sequence; temporal reuse is invisible to the
  decoder.

## FastV hook site

From scouting the mlx-vlm source (v0.1.x, April 2026):

- Target function:
  `.venv/lib/python3.12/site-packages/mlx_vlm/models/qwen2_5_vl/language.py::Qwen2Model.__call__`
  (~line 250-253: the `for layer, c in zip(self.layers, cache):` loop).
- FastV requires two changes at this site:
  1. After layer K, compute mean attention score over vision-token
     positions (requires the attention mask from `merge_input_ids_with_image_features`
     threaded into this scope — currently NOT plumbed there).
  2. Remove lowest-scoring vision tokens from `h`, update `mask` and
     `position_ids`, and run layers K+1..N on the reduced sequence.
- Qwen 2.5-VL uses 3-D MRoPE position IDs (`(3, batch, seq)`), so position
  surgery is non-trivial.

## Blocker: no attention-score introspection

`Attention.__call__` returns only the projected output. Internally it
dispatches to `mx.fast.scaled_dot_product_attention`, a fused Metal kernel
that does NOT surface softmax weights. There is no exposed hook; no flag
that says "also return the scores."

A FastV implementation therefore requires replacing the fused SDPA path
at layers K-1 (so we have scores to sort on before dropping) with an
explicit `softmax(Q @ K.T / sqrt(d)) @ V` path that materializes the
attention matrix. That is a patch to the mlx-vlm attention class, not
just an mlx-vlm user-level config.

**Classification**: requires mlx-vlm fork with attention API additions.
**Effort**: 1–2 weeks engineering, including KV cache bookkeeping for
dropped tokens.

## No prior art

As of 2026-04-16, the mlx-vlm issue tracker has no open or closed issues
about attention-score introspection or FastV-style token dropping. The
mlx-lm tracker has none either. No community fork exposes this. Starting
from scratch.

## One-clip smoke test (pre-integration)

Before investing in the fork work, run a single-clip pilot to validate
the mechanism fires without corrupting output:

- Take one item from the existing TOMATO or MVBench slice with a known
  correct dense answer at 8 frames.
- Implement FastV K=2, R=50% (drop the bottom half of vision tokens by
  attention score after layer 2) inside a local mlx-vlm fork.
- Run the prompt twice: stock and FastV.
- Assert answer match AND peak memory / wall-clock prefill reduction
  roughly consistent with the expected 50% vision-token cut.

If the smoke passes, proceed to slice-level evaluation against the
matched fresh-token-equivalent budget on dev. If the smoke fails (answer
changes or no measurable compute reduction), FastV composition may not
be viable on the MLX path without deeper integration (fused attention
kernel with score output, or a torch-side re-implementation).

## Integration with temporal reuse

Once FastV is wired into the decoder path, composition with temporal
reuse requires no additional code: temporal reuse already operates on
the encoder side before the LLM sees any tokens, so FastV sees whatever
mixed vision-token sequence the encoder produces. The two axes stack.

What does need to change:

- `effective_fresh_frames` (our Track A proxy) no longer represents the
  full compute axis. We need a new metric like
  `effective_vision_token_flops = fresh_encoder_fraction × (1 - fastv_drop_rate × (N - K) / N)`
  or the directly-measured prefill FLOPs from a MLX instrumentation hook.
- Calibration and Pareto axes must be extended to track the new metric.
- Holdout discipline reruns all TOMATO + MVBench with the composed
  pipeline before any claim.

## Go / no-go gates before starting FastV work

- TOMATO N=30 enlargement (phase 1.20) confirms or rejects the current
  0.267-tie holdout win. If confirmed with N=30 and tighter CIs,
  temporal reuse alone has a paper claim and FastV composition is
  optional. If rejected, FastV becomes the primary path.
- Stage E Track B timing harness lands first so we have ground-truth
  measured compute rather than proxy budgets when making composition
  claims.
- Operator review of this plan before investing engineering time.

## Summary

- Hook site known: `mlx_vlm/models/qwen2_5_vl/language.py::Qwen2Model.__call__`.
- Attention-score introspection absent: requires mlx-vlm fork.
- Effort estimate: 1–2 weeks including KV/position bookkeeping.
- Smoke test is a one-clip before/after; cheap to run once the fork lands.
- No prior art to build on; starting from scratch.
- Composition story stacks naturally with temporal reuse; no
  encoder-side changes required.
