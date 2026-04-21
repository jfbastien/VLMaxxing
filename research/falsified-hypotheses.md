# Falsified Hypotheses Ledger

Date: 2026-04-16
Parent: [decision-log.md](decision-log.md), [PLAN.md](../PLAN.md)

This is the rejected-hypothesis companion to
[decision-log.md](decision-log.md). Decision-log rows are dated
status changes (adopted / weakened / killed / pending). This file
is the queryable ledger of hypotheses that the data **explicitly
rejected** — what was tested, what the rejection looks like, and
what the rejection rules out for future work.

The 2026-04-16 audit recommendation: "make negatives queryable by
agents" (borrowing from MLGym / MLE-bench process discipline). Each
entry should be self-contained enough that a future agent or reader
can understand what was tried and why it failed without reading
the full phase note.

## Schema

Each entry has:

- **id**: `falsified_YYYY-MM-DD_short-name`
- **hypothesis**: one-sentence statement of the tested hypothesis
- **rejected by**: phase id + metric + magnitude
- **rejection band**: what the prereg said would count as rejection
- **scope of rejection**: what future work this rules out vs
  what remains open
- **link**: primary phase note

## Entries

### falsified_2026-04-14_no-refresh-static-reuse-on-tomato

- **hypothesis**: default static-position reuse with no refresh and
  no max_age maintains TOMATO direction accuracy.
- **rejected by**: phase 1.49 TOMATO direction refresh sweep.
  Cached=0.2 at no-refresh vs dense=0.8 on 5-item subset.
- **rejection band**: holdout cached accuracy below dense-same-run.
- **scope of rejection**: rules out "naive no-refresh same-position
  reuse is sufficient for TOMATO motion." Does NOT rule out
  bounded-age or refresh-interval variants.
- **link**: [phase 1.49](experiments/2026/2026-04-14-phase-1_49-tomato-direction-refresh-sweep.md)

### falsified_2026-04-14_mean-planner-default-thresholds-on-motion

- **hypothesis**: default `mean` planner with static_threshold=3,
  shifted_threshold=8 is competitive on motion benchmarks.
- **rejected by**: phase 1.6 + phase 1.7 + phase 1.10 show that
  `mean` planner with default thresholds is dominated by `max_abs`
  at matched budget, on both TOMATO and MVBench motion dev.
- **rejection band**: cached accuracy lower than the best alternative
  statistic at matched effective_fresh_frames.
- **scope of rejection**: rules out `mean + defaults` as a SOTA
  target. Does NOT rule out `mean` with retuned thresholds.
- **link**: [phase 1.10](experiments/2026/2026-04-14-phase-1_10-planner-grid-tomato-motion-dev.md)

### falsified_2026-04-16_mvbench-phase1-11-grid-winners-on-holdout

- **hypothesis**: any of the 5 phase-1.11 MVBench motion dev Pareto
  winners (`max_abs(16,64)` noage/age4, `max_abs(8,32)` noage,
  `top_k_mean` noage, `cpf` noage) survives MVBench motion holdout
  at matched fresh-frame budget.
- **rejected by**: phase 1.12. All 5 cached policies strictly
  dominated by some dense-N baseline on holdout; pareto_candidate_count
  = 0.
- **rejection band**: per phase 1.12 preregistration — "every
  dev-selected policy is strictly dominated."
- **scope of rejection**: rules out these specific policies as
  MVBench holdout survivors. Does NOT rule out the broader
  statistic family; phase 1.12.B showed that a grid-hole policy
  (`max_abs(8,32) age=4`) does survive.
- **link**: [phase 1.12](experiments/2026/2026-04-14-phase-1_12-grid-winners-holdout.md)

### falsified_2026-04-16_iso-frame-coverage-on-mvbench-holdout

- **hypothesis** (phase 1.28 H1 on MVBench holdout): doubling frame
  count from 8 to 16 at the same policy improves cached_accuracy
  because the saved budget buys more temporal coverage.
- **rejected by**: phase 1.28 MVBench holdout cell. cached_accuracy
  at 16 frames = 0.667 (IDENTICAL to 8-frame result), fresh budget
  rises from 4.59 to 8.58. Pareto-dominated by dense-8 (0.733 at
  8 frames).
- **rejection band**: cached_accuracy at 16 frames is not higher
  than at 8 frames.
- **scope of rejection**: rules out "more frames always helps at
  matched policy" on MVBench motion holdout. Does NOT rule out
  "more frames helps with a more-aggressive policy at iso fresh
  budget." Phase 1.28 H1 at iso-budget (tighter thresholds at 16
  frames targeting fresh~4) is still open.
- **link**: [phase 1.28 MVBench holdout](experiments/2026/2026-04-15-phase-1_28-iso-token-budget-coverage.md)

### falsified_2026-04-16_sticky-dynamic-alone-on-tomato-motion-dev

- **hypothesis** (phase 1.26 H1): adding sticky-dynamic
  (CodecSight §3.2 GOP-style mask accumulation) to the TOMATO
  dev winner `max_abs(8,32) static+shifted age=4` recovers the
  direction item that the vanilla policy misses.
- **rejected by**: phase 1.26 cells 1 and 2. Both `sticky_window=4`
  and `sticky_window=8` reduce cached accuracy from 0.400 to
  0.333 AND raise fresh-frame budget (from 3.99 to 4.33 or 4.65).
- **rejection band**: cached accuracy below vanilla baseline at
  equal-or-higher budget.
- **scope of rejection**: rules out sticky-dynamic **alone** as a
  repair mechanism on TOMATO motion dev at N=15. Does NOT rule
  out sticky on MVBench (phase 1.26.B PASSES; see overturn entry
  below) or sticky+projector-group-completion (phase 1.27). Supports
  the "budget-placement-not-quantity" hypothesis: adding forward-
  accumulating dynamic flags does not help if the initial classifier
  misses the critical motion.
- **link**: [phase 1.26](experiments/2026/2026-04-16-phase-1_26-sticky-dynamic-planner.md)

### overturned_2026-04-16_sticky-dynamic-universally-useless

- **original concern** (phase 1.26 H2 as originally preregistered):
  if sticky fails TOMATO dev, it likely also fails MVBench holdout
  because the mechanism is assumed universal.
- **overturned by**: phase 1.26.B single-shot on MVBench motion
  holdout. `max_abs(8,32) static+shifted age=4 sticky_window=4`
  achieves cached=0.733 (up from vanilla 0.667), agreement=1.000
  (item-identical to dense-8), fresh=5.10. Strict Pareto win vs
  dense-8 at 64% budget.
- **scope of overturn**: sticky-dynamic IS a benchmark-conditional
  mechanism. It hurts TOMATO direction-style failures (classifier
  misses critical motion entirely) and helps MVBench motion-style
  patterns (classifier detects motion intermittently; sticky
  latches it consistently). The "budget-placement-over-time" theory
  remains supported: sticky succeeds when placement is improved,
  fails when placement isn't the bottleneck.
- **link**: [phase 1.26.B section in phase 1.26 note](experiments/2026/2026-04-16-phase-1_26-sticky-dynamic-planner.md)

### falsified_2026-04-17_novelty-magnitude-as-universal-frame-budget-axis

- **hypothesis** (phase 1.34 paper claim #9 direct test): pixel-
  novelty-magnitude frame selection is a universal drop-in
  substitute for temporal coverage when spending a frame budget.
  If true, cached's advantage over uniform dense could be explained
  purely by "smart frame selection" that the cached policy does
  implicitly.
- **rejected by**: phase 1.34 full 2×3 grid N=30 (TOMATO +
  MVBench motion holdout v2, N ∈ {4,6,8}). Novelty-ranked dense
  never exceeds cached base policy at equal-or-lower effective
  fresh-frame budget on either benchmark. On TOMATO, novelty
  UNDER-performs uniform dense by 0.100 absolute at N=6 and N=8
  (no-worse at N=4). On MVBench, novelty helps by +0.067 at N=4
  but saturates at 0.567 for N≥6 while uniform climbs to 0.633 —
  so even with MVBench's higher pixel→feature correlation, novelty
  ranking caps the information ceiling at low-budget gain.
- **rejection band**: per phase 1.34 prereg — "if cached still
  beats novelty-ranked dense-N at matched N, the advantage cannot
  be attributed to frame selection." Passed on both benchmarks.
- **scope of rejection**: rules out "novelty-magnitude ranking
  explains cached's edge" AND "novelty magnitude is a replacement
  for temporal coverage at arbitrary budget." Does NOT rule out
  "novelty ranking helps at low-budget, heterogeneous content"
  (MVBench N=4 is direct evidence for this narrower claim). The
  narrower claim motivates the content-class taxonomy in
  `docs/application-taxonomy.md`.
- **link**: [phase 1.34](experiments/2026/2026-04-17-phase-1_34-novelty-ranked-dense.md)

### falsified_2026-04-18_nuwa-pillar-recovers-aggregate-accuracy-at-kr050

- **hypothesis** (phase 1.51R Stage 5a prereg): informed anchor
  selection using nuwa_pillar (2×2 block corners + mid-axis,
  derived from the Nüwa paper for video token selection) preserves
  more question-relevant tokens than plain top-k novelty, and at
  kr=0.50 should recover the -10pp aggregate accuracy drop seen
  at Stage 2b kr=0.10 anchor=none.
- **rejected by**: phase 1.51R Stage 5a n=30 on VideoMME dev.
  Aggregate Δacc=-0.167 — WORSE than kr=0.10 anchor=none's -0.10,
  not better. Per-bucket: short -0.20, medium -0.10, long -0.20.
  e2e 0.987× (net slower than dense).
- **rejection band**: prereg was Δacc within -0.03pp of dense
  AND e2e > 1.10×. Missed both.
- **scope of rejection**: rules out nuwa's H.264-adjacent
  pillar geometry as a working anchor for Gemma 4's pre-pooled
  16×16 feature grid. Does NOT rule out informed anchors
  generally — Stage 5b max_min_diversity and Stage 5c
  gemma_structural both earn the accuracy bar at the same kr.
  The lesson: match anchor geometry to the feature geometry you
  actually have, not to the encoder source pixel geometry. Pillar
  corner + mid-axis positions burn half the budget on
  content-blind positions in a feature grid that has already
  pooled away the pixel-block structure.
- **link**: [Stage 5a findings](experiments/2026/2026-04-18-phase-1_51R-stage5a-nuwa-pillar-findings.md)

### falsified_2026-04-18_any-anchor-arm-clears-e2e-1.1x-at-kr050

- **hypothesis** (implicit in Stage 5 prereg): at least one of the
  three informed anchor arms (nuwa_pillar, max_min_diversity,
  gemma_structural) delivers end-to-end speedup ≥ 1.10× at
  kr=0.50 on Gemma 4-E4B 8-frame VideoMME. The working assumption
  was that smart anchoring would unlock the "both bars cleared"
  operating point.
- **rejected by**: four independent n=30 runs at kr=0.50 — Stage 1
  (anchor=none), Stage 5a (nuwa_pillar), Stage 5b
  (max_min_diversity), Stage 5c (gemma_structural). All four
  aggregate e2e land in [0.963×, 1.00×]. None clear 1.00×, let
  alone 1.10×.
- **rejection band**: any anchor arm aggregate e2e > 1.10× at
  kr=0.50. All four fell below 1.00×.
- **scope of rejection**: rules out "smart anchoring lifts e2e at
  moderate kr" as a mechanism independent of the arithmetic
  ceiling. Confirms task #88's ceiling prediction: at kr=0.50 on
  this geometry, fixed cost D+P+V = 71.4% of aggregate e2e, so
  *any* G-only speedup is capped at 1.46× even with s=∞. The
  binding constraint is not anchor smartness.
- **implication**: the remaining e2e levers at kr=0.50 are
  non-G: phase 1.51V (touches V) and phase 1.54 (touches D).
  1.51R alone cannot clear 1.10× at moderate kr without regime
  change (more frames, larger model — see Stage 6 regime-match
  prereg).
- **link**: [Stage 5 cross-arm synthesis](experiments/2026/2026-04-18-phase-1_51R-stage5-cross-arm-synthesis.md)

### falsified_2026-04-14_static-position-same-position-reuse-matches-whitepaper

- **hypothesis**: naive same-position STATIC+SHIFTED reuse
  reproduces the whitepaper's 100% TOMATO and MVBench agreement
  claims on our local Qwen 7B MLX 4-bit stack.
- **rejected by**: phase 1.4 (TOMATO 30-item, 0.833 agreement) and
  phase 1.5 (MVBench 54-item, 0.870 agreement).
- **rejection band**: agreement ≥ 0.95 on the local slice.
- **scope of rejection**: rules out the imported "100% agreement"
  claim as a realistic local target. Does NOT rule out
  method-improvement claims at matched budget (which is now our
  path).
- **link**: [phase 1.5](experiments/2026/2026-04-13-phase-1_5-mvbench-benchmark-subset.md)

### falsified_2026-04-22_codec-or-aggregate-matches-pixel-diff

- **hypothesis**: codec-native H.264 macroblock labels (STATIC /
  SHIFTED / NOVEL from skip / intra|cbf / else), max-OR-aggregated
  across the native-rate span between each pair of sparse-sampled
  8 frames and resampled to Qwen's 28px token grid, agree with
  Phase 1.57 pixel-diff class shares to within max |Δ| < 10pp per
  class — i.e., codec labels are a drop-in replacement for pixel-
  diff in the Track A planner path.
- **rejected by**: phase 1.29 short-bucket pilot (n=5 short-bucket
  VideoMME items, 2026-04-22) — **100% NOVEL on every sparse pair
  of every item**; mean aggregate Δ vs 1.57 pixel-diff reference
  = −0.496 / −0.042 / +**0.538** (STATIC / SHIFTED / NOVEL).
  max|Δ| = **0.538**, five times the gate.
- **rejection band**: mean-aggregate max|Δ| < 0.10 across n≥5.
  Observed 0.538.
- **scope of rejection**: rules out **MAX-over-span aggregation**
  as the reduction rule for codec→sparse-frame label mapping. Root
  cause: at 30 fps short clips, ~250-400 native frames per sparse-
  pair span contain many I-frames, so every macroblock position
  accumulates at least one `intra_flag`/CBF bit, locking the max
  to NOVEL. Does NOT rule out (a) threshold-fraction aggregation
  rules, (b) continuous codec-score with planner re-thresholding,
  (c) native-rate codec-through per Sam-streaming protocol (task
  #155 prereg). The upstream `H264MetadataExtractor` and
  `classify_blocks_h264` are correct at native rate (task #114
  regression tests pass); the falsification is an aggregation-
  design choice, not an extractor bug.
- **link**: [1.29 short-bucket pilot findings](experiments/2026/2026-04-22-phase-1_29-codec-native-short-bucket-pilot-findings.md)

## Additions process

When a new phase registers a rejection:

1. Fill in the schema fields above.
2. Link to the phase note.
3. Link from the phase note back to this ledger if the phase
   produced a rejection (so readers can navigate both directions).
4. Don't delete entries when later evidence overturns them; add a
   new dated entry that notes the overturn and why.
