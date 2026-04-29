# Phase 1.32: FastV Composition Pilot

## Preregistration

Objective:

- demonstrate that our encoder-side temporal cached method composes
  multiplicatively with FastV's decoder-internal attention-score
  token pruning on Qwen 2.5-VL MLX.
- This is the strongest-orthogonal-axis composition available to us
  (see phase 1.23 research): encoder-side × decoder-internal = no
  signal overlap, no code path overlap.

Claim register targets:

- Paper claim 5: "training-free temporal routing composes with
  other training-free token reduction methods."

Reproduction mode:

- method-composition; major code change; phase 1.23 scouting
  identified the MLX-vlm fork requirement.

Track: A composition + Track B prep.

Gating: requires ~1-2 weeks of mlx-vlm forking to expose per-layer
attention scores (currently hidden behind
`mx.fast.scaled_dot_product_attention`). Deferred until phases
1.26, 1.27, 1.28 are stable and there's engineering bandwidth for
the fork.

Hypotheses:

- **H1 (orthogonal gain)**: composition gives ≥ 1.5× token reduction
  beyond cached alone at matched cached_accuracy.
- **H2 (accuracy-preserving)**: at FastV K=2, R=50% composed with
  our `max_abs(8,32) static+shifted age=4 + sticky-dynamic`,
  cached_accuracy on TOMATO motion holdout is within 1 item of the
  cached-only result.

Acceptance band:

- token reduction measurable and > 1.2× beyond cached baseline
- cached_accuracy drop ≤ 1 item on N=15

Rejection band:

- FastV composition destroys accuracy (≥ 3 items drop) — signal
  overlap is larger than predicted, or the dropped tokens carry
  our critical-span information

Inconclusive:

- fork incomplete; cannot measure attention scores

## Code change (large)

Per phase 1.23 scouting:

1. Fork mlx-vlm at commit TBD
2. In `mlx_vlm/models/qwen2_5_vl/language.py::Qwen2Model.__call__`
   layer loop: at layer K, replace fused SDPA with explicit
   softmax(Q @ K.T / sqrt(d)) @ V that materializes attention scores
3. After layer K, drop lowest-R% vision-token columns from h, mask,
   position_ids. Handle MRoPE 3D position surgery.
4. Update KV cache bookkeeping: dropped tokens never got added.
5. Expose `fastv_k: int` and `fastv_r: float` as runner CLI flags.

## Execution

Pending phase 1.26/1.27/1.28 and fork completion.

## Result

Pending.

## Interpretation

Pending.

## Links

- [phase 1.23 FastV scouting](2026-04-15-phase-1_23-fastv-composition-scouting.md)
- historical FastV composition sketch from phase 1.23, removed from the
  release tree as non-claim-bearing planning material
- Pre-release CodecSight strategy notes are preserved in git history; current
  release-facing positioning is in [paper/framing.md](../../../paper/framing.md)
  and [docs/related-work-table.md](../../../docs/related-work-table.md).
