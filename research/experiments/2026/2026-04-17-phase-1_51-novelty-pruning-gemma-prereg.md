# Phase 1.51 — Novelty-pruning visual tokens on Gemma 4-E4B (big-numbers SOTA lane)

Date: 2026-04-17
State: **pilot landed 2026-04-18 as preregistered null** on VideoMME long
n=1 (end-to-end 1.01× vs ≥1.8× target). Scale-up (Stage 1 n=30) running;
see pilot-findings note below. Mechanism verified correct (agreement +
exact kept-token count); null is due to decode + vision dominance in
the (D, V, G) share for Gemma 4-E4B.
Parent: `paper/claim-matrix.md` claim #11 (novelty-pruning big numbers on Gemma). Claim #10 (composition) is tested separately in phase 1.52R, which does gate on both 1.42 + 1.51R.

## Pilot amendment (2026-04-18)

First GPU run of the driver after the 2026-04-18 bounded-decode fix
+ Gemma geometry correction (16×16 post-pool, not 14×20) returned
**1.01× end-to-end speedup** and **1.12× generate-only** on a single
long-duration VideoMME item. Full analysis and per-stage timings in
`research/experiments/2026/2026-04-18-phase-1_51R-pilot-findings.md`.

Key arithmetic: end-to-end speedup is bounded above by
`(D + V + G) / (D + V + G/s)` where `D = decode_ms`, `V = vision_ms`,
`G = generate_ms`, and `s` is the generate-only speedup. On the pilot
item `D = 22.8s, V = 4.9s, G = 5.1s`, so even `s = ∞` only yields
1.18× end-to-end. The 1.8× target is **unreachable at these stage
shares on Gemma 4-E4B + long VideoMME items**, independent of which
anchor arm or keep rate is chosen; the mechanism cannot touch D or V.

Stages 1-3 (n=30 scale-up, kr-aggressiveness sweep, max_tokens
sensitivity) will put error bars on the null and check whether any
subset of (duration bucket, kr, max_tokens) reaches the preregistered
1.8× gate. Expected outcome: preregistered NO-REPRO on E4B for
claim #11 headline, with the negative result itself publishable as
evidence that the pre-release source's mechanism is model-scale-sensitive.

## Round-18 amendment (2026-04-17)

Prior framing said this phase was blocked on phase 1.42
`_mix_gemma_features`. Codex round-18 caught that this framing is
inconsistent with the phase 1.42 design note (§Critical re-read,
line 62) which says novelty-pruning "does not require
`_mix_gemma_features` at all" — it's a fresh per-frame
token-drop path at the LLM prefill input. This prereg is updated
to match. See also the pre-release reproduction lane prereg
(`research/experiments/2026/2026-04-17-scaleout-reproduction-lane-prereg.md`)
which assigns phase 1.51R the "reproduction" role; the extension
work on TOMATO/MVBench stays under phase 1.51 (now "1.51E" for
extension).
Sibling: `research/experiments/2026/2026-04-17-phase-1_42-gemma-architecture-topology-prereg.md`
(same model, orthogonal architecture-fidelity axis)

## Motivation

Claim #10 in the paper matrix is currently deferred because we
have no measured spatial-pruning result. the pre-release source's sibling project
reports 4-5× end-to-end speedups on Gemma 4 26B (M5 Max) by
dropping visual tokens from the LLM prefill based on a per-frame
novelty score. Codex round-15 explicitly flagged that
**absorbing this axis is where the "big numbers" the user wants
live** — temporal reuse on Qwen has a ceiling of ~22 % end-to-end
on M3 Air (analytical bound derived from phase 1.50 dense baseline,
NOT a measured speedup); prefill-token reduction is the only path
to multiplicative gains because **prefill is 70-78 % of per-item
wall time** at 8-frame × 560 × 560 geometry.

**Why Gemma 4 and not Qwen for the pruning phase:** Qwen 2.5-VL
uses M-RoPE-V on its LLM backbone: the rotary embedding frequency
for vision tokens is tied to the 2D grid position. Dropping a
visual token changes the remaining tokens' effective positions
mid-sequence, which breaks the RoPE-V assumption. Gemma 4 uses
standard 1D RoPE on the LLM backbone and learned 2D positional
embeddings on the (post-pool) visual tokens, so dropping a token
at the LLM input is a first-class operation: the LLM sees a
shorter sequence and the remaining tokens retain their learned
positional embeddings.

This is why the novelty-pruning phase lives on Gemma first. Qwen
composition with pruning is a separate future-work item that
needs either an M-RoPE-V-safe token-drop strategy or a re-indexing
trick (both are open research questions; see the pre-release source §4).

## Hypothesis

H1 (end-to-end speedup): Novelty-pruning Gemma 4 visual tokens at
**50 % keep rate** (keep the 50 % most novel tokens per frame,
drop the rest before LLM prefill) achieves ≥ 1.8× wall-clock
speedup on TOMATO motion N=30 vs Gemma-dense-8. Target:
≥ 2 × (the pre-release source's 4-5 × on the 26 B model doesn't directly translate
at half the depth and quarter the weights; we budget conservative).

H2 (quality preservation): At 50 % keep rate, cached accuracy is
within 0.10 of Gemma-dense-8. Justification: at 8 frames × 256
visual tokens/frame (validated 16×16 grid on the current MLX
driver path) × 50 % = 1,024 visual tokens prefilled instead of
2,048 — prefill cost drops ~50 %
(prefill is O(N²) attention so the drop is bigger than 50 % in
FLOPs, but at these sizes we're compute-bound not memory-bound,
so wall-clock gain scales closer to N).

H3 (anchor preservation): Adding an anchor-preservation rule
(keep the 10 % of tokens with lowest first-layer attention self-
similarity, regardless of novelty score) reclaims some of the
quality drop without meaningfully reducing speedup. Target:
cached accuracy improves by ≥ 0.03 with anchor preservation vs
pure novelty at matched keep rate.

## Method

**Phase A — pruning implementation:**

1. Hook Gemma's visual-token stream *after* the post-ViT pool
   (where the 2D positional embeddings are applied, before the
   tokens enter the LLM backbone). This is the natural drop
   point because (a) tokens are already at their final LLM-input
   shape, (b) positional embeddings are already baked in, so
   dropping doesn't require any re-positioning, (c) the LLM just
   sees a shorter visual-prefix sequence.
2. Novelty score per visual token: per-token pixel-diff score
   from the existing planner pipeline, aggregated over the
   spatial block that projects to each post-pool visual token.
   (At the current Gemma benchmark path, 560×560 square-padded
   frames map to a validated 16×16 token grid, so each token
   aligns to a 35×35 block for the novelty-grid projection.
   Earlier 14×20 / 280-token notes were stale metadata and are
   not used by the runner.)
3. Keep-rule: `keep if (novelty_rank < k * keep_rate) OR
   (anchor_flag == True)`. `anchor_flag` depends on the anchor
   variant (see grid below).
4. No training. Pure inference-time drop.

**Phase B — anchor-variant ablation grid (dev):**

Anchor variants, preregistered, with literature mapping (see
separate prior-art brief, 2026-04-17, for the review and
citations):

- `none`: no anchor preservation — pure novelty-rank keep-rate
  baseline (FastV-like; arxiv 2403.06764).
- `cls_attention_proxy`: rank all tokens by a *proxy* for ViT
  CLS-attention — Gemma's post-pool visual stream does not
  expose true attention from a CLS/start-of-vision token, so in
  the reference implementation (`src/codec_through/novelty_pruning.py`)
  this arm accepts a caller-provided per-token score vector and
  ranks by it (FasterVLM / HiPrune family, arxiv 2412.01818 /
  2508.00553). Because this is a proxy, not a faithful attention
  measurement on Gemma, the arm is *excluded from winner promotion*
  via `PROMOTABLE_ARMS`; it runs as a literature-comparison
  baseline only, and its cells never advance to paper-grade
  holdout. This was formerly spelled `cls_attention`; renamed
  2026-04-17 to prevent readers from over-interpreting the name
  as a true CLS-attention measurement.
- `nuwa_pillar`: partition the 2D post-pool grid into an M×M
  coarse lattice; within each cell hard-preserve the 25 %
  highest-L2-key-norm tokens as "pillars"; the remaining
  budget goes to novelty-ranked tokens. Adapts Nüwa's
  pillar/collector structure (arxiv 2602.02951).
- `max_min_diversity`: seed first "pivot" as the token with
  largest L1 key-norm, then iteratively add the token that
  maximizes the minimum feature-space distance from all prior
  pivots until budget is met. VLM-Pruner family (arxiv
  2512.02700). No positional floor; content-driven spatial
  diversity.
- `gemma_structural`: Gemma-specific structural anchor arm —
  hard-preserve the four spatial-corner tokens and the center
  token of each frame (5 tokens/frame × 8 frames = 40 tokens)
  regardless of novelty rank. This is the spirit of IVC-Prune
  (arxiv id=46LbXtFgBm) adapted to Gemma's learned-2D-positional
  regime (Gemma lacks the RoPE-V rotation spectrum IVC-Prune
  exploits on Qwen-family models).

Keep-rate grid: {0.3, 0.4, 0.5, 0.6, 0.7}. 5 anchors × 5 keep
rates = 25 cells on the dev tranche; paper-grade holdout runs
the single winning cell.

**Optional composable arm (PoRe):** arxiv 2508.17807 reports a
position-reweighting correction that is orthogonal to anchor
choice. If time allows, cross with the winning anchor arm at
matched keep rate to test multiplicative stacking (this is
out-of-scope for phase 1.51 holdout but worth recording here
as a phase-1.52 candidate axis).

**Phase C — paper-grade holdout:**

Single winning cell from dev tranche → single-shot on
holdout N=30 on both TOMATO and MVBench. Metrics:

- cached accuracy (with pruning)
- dense accuracy (no pruning, same model)
- wall-clock speedup factor
- prefill token count reduction
- prefill time reduction in seconds
- peak memory delta

## Accept / reject gates (preregistered)

- **Accept pruning-alone claim (#11 pre-req):** Single-cell
  holdout achieves (a) ≥ 1.8× end-to-end speedup, (b) cached
  accuracy within 0.10 of Gemma-dense-8 on at least one benchmark,
  (c) at least one anchor variant outperforms `none` by ≥ 0.03
  accuracy at matched keep rate. All three conditions together
  earn claim #11 (pruning-alone prefill reduction) a measured
  entry. This does **not** earn claim #10 (composition) — that
  requires phase 1.52.
- **Reject pruning-alone claim:** Speedup < 1.3× OR accuracy drop
  > 0.15 at best cell. Either failure mode means the pruning path
  does not deliver big numbers on M3 Air at this geometry and we
  publish the negative result as a limitation for claim #11.
- **Compose with temporal reuse (phase 1.52 scope):** If this
  phase passes, phase 1.52 runs Planner 2.0 temporal reuse AND
  novelty-pruning together, measures whether the speedup factor
  multiplies (1.8× temporal × 1.8× pruning = 3.2× target vs 1.5×
  if only additive). Do NOT claim multiplicative composition
  (claim #10) in this phase's writeup — that's 1.52's question.

## Runtime estimate

Wall-clock only (infrastructure impl time excluded):

| Stage | Duration estimate |
|---|---|
| Phase A smoke (single-item, verify keep-rate 0.5 matches spec) | 10 min |
| Phase B dev tranche: 25 cells × 10-item TOMATO dev × 30 s/item (Gemma) | ~2 hr |
| Phase B dev tranche on MVBench (optional; TOMATO selects winner) | +~2 hr |
| Phase C TOMATO holdout single winner (cached + dense) | 30 min |
| Phase C MVBench holdout single winner (cached + dense) | 30 min |
| Track B wall-clock run for winner (both benchmarks) | 30 min |
| **Total if TOMATO dev selects winner** | **~4 hr** |
| **Total with cross-benchmark dev validation** | **~6 hr** |

## Paper-grade artifacts (expected)

- `research/experiments/2026/artifacts/phase1_51_gemma_tomato_motion_dev_v2_prune_grid/*.json`
  (25 cells)
- `research/experiments/2026/artifacts/phase1_51_gemma_tomato_motion_holdout_v2_winner/*.json`
  (single winner)
- `research/experiments/2026/artifacts/phase1_51_gemma_mvbench_motion_holdout_v2_winner/*.json`
  (single winner)
- `results/track_b/gemma_prune_tomato_n30.json` (wall-clock)
- `results/track_b/gemma_prune_mvbench_n30.json` (wall-clock)

## Status

- 2026-04-17: Gemma 4-E4B verified to load; `mlx-vlm==0.4.4`
  exposes the gemma4_vision encoder and the post-pool token
  stream is accessible via the model's `vision_tower` submodule.
  Anchor prior-art research (IVC-Prune / Nüwa / PPE / FastV /
  VisionZip / SparseVLM) commissioned separately (agent
  `a82bb92f2cd8d3da3` on 2026-04-17); the anchor grid above
  will be refined once that brief returns.
- Phase A implementation: NOT STARTED. Does NOT share integration
  with phase 1.42; this is a fresh path at the LLM prefill input
  (see phase 1.42 design note §Critical re-read). Can land in
  parallel with 1.42 smoke.
- Phase B dev tranche: NOT STARTED. Needs Phase A code + VideoMME
  videos unpacked.
- Phase C holdout: NOT STARTED. Blocked on Phase B.

## Why this is THE SOTA phase

Phase 1.50's dense Track B baseline shows that **prefill is
70–78 % of per-item wall time** at 8-frame × 560 × 560 geometry on
M3 Air. That phase-share decomposition *caps* any vision-cache-
only speedup at ≈ 20–23 % of end-to-end: the vision-encode +
cacheable-fraction of prefill is the only budget temporal reuse
can touch. This is a **ceiling derived from dense timing shares,
not a measured sparse-execution result** — no sparse-execution
path has measured an actual end-to-end speedup yet (claim #5
remains prospective per `paper/claim-matrix.md`).

For the "BIG NUMBERS" the paper needs, the contribution has to
come from **reducing the prefill-token count itself**, not only
from reusing vision features. Phase 1.51 is the first queued phase
that attacks prefill token count directly by dropping visual
tokens before the LLM sees them.

If this phase passes, the matched-budget story becomes (all
numbers pending measurement, none pre-claimed as earned):

- Temporal reuse alone (Qwen): ceiling ≤ 23 % end-to-end, sparse
  execution unmeasured. Claim #5 (sparse-execution speedup)
  remains prospective in `paper/claim-matrix.md`.
- Novelty-pruning alone (Gemma): 50–80 % end-to-end speedup at
  matched accuracy — this phase's hypothesis, **not** yet a
  measurement. Success gates a new paper claim (pruning-alone
  prefill reduction; see `paper/claim-matrix.md` claim #11 when
  added).
- Combined (phase 1.52): multiplicative-vs-additive-vs-interference
  is the gate preregistered in phase 1.52; nothing is pre-claimed.

Big numbers live in prefill reduction. This phase gates the
pruning-alone branch of that; phase 1.52 gates the composition
branch.
