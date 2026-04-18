# Phase 1.51V: Vision-Tower Pruning (Gemma + VideoMME)

**Status:** preregistration 2026-04-18. Scheduled after 1.51R Stage 5
anchor-arm comparison completes. Surfaces a mechanism that 1.51R
cannot reach by construction — 1.51R prunes **visual tokens before
the LLM** while 1.51V would prune *within* the Gemma vision tower
itself. The two phases attack different parts of the end-to-end
latency breakdown.

## Motivation

The 1.51R pilot and Stages 1–5 established a clean arithmetic ceiling
on end-to-end speedup: `e2e ≤ (D + P + V + G) / (D + P + V + G/s)` where
`D = decode`, `P = processor`, `V = vision-tower forward pass`,
`G = LLM prefill+generate`, and `s = per-phase speedup`. Measured on
Gemma 4-E4B-4bit 8-frame VideoMME dev n=30 (Stage 2b, ceiling analysis):
fixed-fraction = 0.714 aggregate, ceiling@∞ = 1.462× aggregate. Sam's
1.8× target is arithmetically unreachable at this 8-frame geometry
without also touching `V` (short/medium) or `D` (long).

Per-bucket fixed fractions: short 0.568, medium 0.663, long 0.912.
1.51V attacks V, which sits at 37.7% of short-bucket e2e and 10.8% of
medium-bucket e2e; for long-bucket V contributes only 4.8%, so 1.51V
does not help long.

Phase 1.51V tests whether vision-tower-internal pruning (SigLIP-style
token dropping inside the encoder) can reduce `V` meaningfully and
lift the end-to-end ceiling above the 1.20× plateau that 1.51R is
fundamentally bounded by.

## Preregistration

### Objective

Prune visual tokens *inside* Gemma's vision tower at early layers,
measure the effect on `V` (vision-tower wall-clock) and on downstream
accuracy, and quantify whether the combined 1.51R + 1.51V pipeline
reaches Sam's 1.8× e2e target on VideoMME at a fixed accuracy
tolerance.

### Why this is the right follow-up to 1.51R

- 1.51R has **mechanistically correct prefill savings** but a
  **hard arithmetic ceiling** on e2e because `V` is fixed cost. This
  is not an implementation bug; it is a geometry fact.
- On larger models the ceiling is looser because `G` dominates; we
  are on a 4-bit quantized 4B-param model, so `V / (D+V+G)` is a
  larger fraction of total latency than on the 7B+ models in Sam's
  measurements.
- 1.51V is the only path to `V` reduction without swapping the vision
  tower, and it composes cleanly with 1.51R's prefill savings.

### Claim register targets

- Paper claim 11 ("novelty-pruning visual tokens before LLM prefill
  delivers end-to-end speedup on Gemma 4") — 1.51V would lift the
  arithmetic-ceiling-constrained partial reproduction toward a full
  reproduction by reducing the dominant fixed-cost term.
- Paper claim 5 ("real sparse execution converts proxy gain into
  measured speedup") — vision-tower pruning is a local sparse
  execution path that doesn't require a streaming harness.

### Reproduction mode

- method-development; composes with 1.51R's existing infrastructure.
  The pruning decision is made *before* the vision tower forward
  pass begins, using the same pixel-diff novelty signal 1.51R
  already computes.

### Track: A (same planner, deeper intervention)

### Gating

Runs after 1.51R Stage 5 completes. Independent of 1.42 and 1.52R.
Same compute profile as 1.51R stages — sequential on the MLX queue;
no concurrency with 5a/5b/5c.

### Hypotheses

- **H1 (V reduction is real)**: pruning 50% of visual tokens at the
  first vision-tower transformer layer reduces `V` wall-clock by
  ≥ 35% on a Gemma 4-E4B-4bit 8-frame clip. We expect <50% because
  the per-layer FLOPs savings are offset by the first layer's
  non-token-parallel overhead and the fact that the projector and
  embed_vision layers still run on the reduced-length output.
- **H2 (accuracy cost is bounded)**: 50%-token-pruning at layer 1
  costs no more than 10pp absolute accuracy on VideoMME N=30, which
  is the same accuracy-cost budget 1.51R runs at its winning
  operating point. Below this bar the mechanism is not viable.
- **H3 (1.51V + 1.51R composition clears Sam's target)**: composed
  pipeline at 1.51V @ 50% tokens + 1.51R @ kr=0.50 reaches e2e ≥ 1.5×
  on VideoMME N=30 with combined accuracy cost ≤ 15pp. 1.8× is the
  stretch target; 1.5× is the "ceiling lifted substantially above
  the 1.51R 1.20× plateau" acceptance threshold.
- **H4 (deeper pruning earns more)**: pruning at layer 6 instead of
  layer 1 gives better accuracy at matched V-reduction (pruned
  later = more information preserved for the pruning decision).

### Acceptance band

- H1: `V` wall-clock reduction ≥ 35% at 50% token pruning, measured
  on the same 30 items as 1.51R Stage 2b.
- H2: `pruned_accuracy ≥ dense_accuracy − 0.10` on VideoMME N=30 at
  50% tokens layer 1.
- H3: composed 1.51V + 1.51R reaches e2e ≥ 1.5× with combined
  accuracy cost ≤ 15pp.
- H4: layer-6 pruning beats layer-1 pruning by ≥ 3pp accuracy at
  matched V-reduction.

### Rejection band

- H1: `V` reduction < 15% at 50% token pruning (overhead swamps
  savings — vision-tower pruning is not worth the complexity).
- H2: `pruned_accuracy` drops by > 20pp (mechanism destroys the
  vision tower's ability to answer, regardless of speedup).
- H3: composed pipeline e2e < 1.2× (composition does not stack;
  1.51V is dominated by 1.51R-alone).
- H4: no layer-position effect observable at n=30 (token position
  inside the tower doesn't matter — simplifies the mechanism but
  also removes a research dimension).

### Inconclusive

- MLX on M3 Air cannot measure the V term with ≤ 5% jitter at the
  per-item scale we need for H1. Escalate to larger-n runs or move
  to a machine with a more predictable MLX kernel queue.
- Gemma 4-E4B's vision tower emits exactly 256 tokens per frame
  (16×16 post-pool grid; task #66 token-geometry finding). If the
  projector assumes a fixed token count, pruning must be followed
  by a pad-to-original-length step, which changes H1's arithmetic —
  document and re-derive H1 if this constraint is confirmed.

### Design notes

1. Pruning decision: use the same 1.51R pixel-novelty mask,
   intersected with a `top-k-per-frame` selector tuned to the
   50%-token target. Sharing the signal means we do not need a
   separate training pass for 1.51V.
2. Implementation path: subclass the Gemma `vision_tower` with a
   hook that applies the keep mask after layer `L` (configurable,
   default `L=1`). Verify activations shapes at each layer boundary.
3. Composition with 1.51R: apply 1.51V's mask *inside* the vision
   tower, and 1.51R's mask *to the output of the vision tower*. The
   two masks can be different — 1.51V runs on layer-1 features,
   1.51R runs on layer-N post-pool features.
4. Instrumentation: extend the Task #89 per-item timing fields with
   `vision_tower_ms_dense`, `vision_tower_ms_pruned`, and a
   `vision_pruned_tokens` count analogous to `kept_tokens_total`.

### Execution plan

1. Pilot: 1 VideoMME item at layer-1 50%-token prune. Verify shapes
   flow; compare the layer-1 output to dense under the same input.
2. Dev tranche: 1.51V alone at layer ∈ {1, 6, 12} × keep_rate ∈
   {0.25, 0.50, 0.75} on n=5 items. Measures H1 / H4 cheaply.
3. n=30 at the winning (layer, kr) cell on VideoMME dev.
4. 1.51V + 1.51R composed: the winning 1.51V cell × 1.51R kr=0.50
   at n=30. Measures H3.
5. Holdout: single-shot N=30 if the composed pipeline clears H3.

### Runtime estimates (benchmark compute only)

| stage                        | scope                     | ~wall-clock  | notes                                          |
|------------------------------|---------------------------|--------------|------------------------------------------------|
| pilot                        | 1 item                    | ~2 min       | shapes + smoke                                 |
| 1.51V alone, dev tranche     | 9 cells × 5 items         | ~2 h         | layer × kr grid                                |
| 1.51V alone, n=30            | 1 cell × 30 items         | ~40 min      | winning cell                                   |
| 1.51V + 1.51R composed       | 1 cell × 30 items         | ~40 min      | winning composed cell                          |
| holdout (optional)           | 1 cell × 30 items         | ~40 min      | only if composed clears H3                     |

Total runtime: ~4 h benchmark wall-clock (pilot + all dev + n=30 +
composed + holdout).

### Links

- Phase 1.51R stages 1–3 findings — the arithmetic-ceiling argument
  that motivates 1.51V.
- Phase 1.51R Stage 2b findings — the n=30 picture that shows the
  ceiling is reached even at aggressive kr.
- Task #87 (this prereg).
- Task #88 (arithmetic-ceiling empirical validation + paper figure) —
  the ceiling figure will be a natural home for 1.51V results.
- Sam whitepaper §4 (where vision-tower acceleration is discussed in
  passing; Sam's own pipeline does not prune inside the vision tower
  but acknowledges the arithmetic).

### Result

Pending.

### Interpretation

Pending.
