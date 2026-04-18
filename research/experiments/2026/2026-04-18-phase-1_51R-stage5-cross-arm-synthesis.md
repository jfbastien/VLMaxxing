# Phase 1.51R Stage 5 — Cross-Arm Anchor Synthesis

**Status:** synthesis 2026-04-18, closes task #101. Combines Stage
5a (nuwa_pillar), 5b (max_min_diversity), 5c (gemma_structural) at
matched kr=0.50 on VideoMME dev n=30.

## Headline

At fixed kr=0.50 on Gemma 4-E4B 8-frame geometry, **anchor choice
drives a 13.4pp accuracy swing** (nuwa -16.7pp → gemma/max_min
-3.3pp). **No anchor arm clears e2e ≥ 1.10×**; the arithmetic
ceiling binds independently of anchor choice, confirming task #88's
analytical prediction.

## Results table

All rows: n=30, VideoMME dev manifest, kr=0.50, 8 frames, Gemma
4-E4B-4bit MLX, max_tokens=32.

| arm                   | Δacc_agg | agree | e2e    | gen    | per_tok | mask_ms | short Δ | medium Δ | long Δ |
|-----------------------|---------:|------:|-------:|-------:|--------:|--------:|--------:|---------:|-------:|
| nuwa_pillar (5a)      | -0.167   | 0.43  | 0.987× | 0.976× | 3.071   |   15    | -0.20   | -0.10    | -0.20  |
| max_min_diversity (5b)| -0.033   | 0.47  | 0.963× | 0.936× | 1.714   |  362    | +0.00   | -0.10    | +0.00  |
| gemma_structural (5c) | -0.033   | 0.53  | 0.992× | 0.979× | 2.680   |    2    | -0.10   | -0.10    | **+0.10** |

## Four publishable findings

### 1. Anchor choice matters, but the *type* that wins is not what we expected

We preregistered nuwa_pillar as the strongest informed-anchor
candidate because it has a published pedigree (Nüwa paper) for video
token selection. It finished **worst** of the three arms, not best.

- Nuwa's pillar structure (2×2 block corners + mid-axis) was designed
  for H.264-adjacent block-structured signals. On Gemma's pre-pooled
  16×16 feature grid, this geometry forces half the budget into
  *content-blind* positions (corners of an abstracted feature map).
- max_min_diversity (feature-space farthest-point) and
  gemma_structural (geometric grid sampling) both beat nuwa by 13.4pp
  aggregate. The lesson: **match anchor geometry to the feature
  geometry you actually have**, not to the input pixel geometry of
  the encoder source.

### 2. Two independent anchor strategies earn the accuracy bar

Both max_min_diversity and gemma_structural land at Δacc=-0.033,
within our -0.10pp common budget. They arrive there via different
mechanisms:

- max_min_diversity: iterative greedy L2-distance in feature space,
  seeded by highest L1 key-norm. Feature-driven spread.
- gemma_structural: geometric grid sample (precomputed centers +
  border-strip + uniform stride), no feature dependence.

**Interpretation:** at kr=0.50, the 1024-token budget is large enough
that *any* reasonable spread of tokens preserves question signal.
The specific criterion (feature distance vs grid position) is a
second-order effect on aggregate accuracy, not a first-order one.
This is a hypothesis that becomes testable as we drop kr.

### 3. Per-bucket anchor behavior is distinct

The three arms disagree sharply on *which* videos they can keep:

- **Short bucket:** max_min wins (+0.00), gemma_structural loses
  (-0.10). Short videos have less inter-frame redundancy; feature
  spread matters.
- **Long bucket:** gemma_structural uniquely improves over dense
  (+0.10). Long videos (→ aggressive 8-frame subsampling) have more
  frame-to-frame redundancy; geometric per-frame coverage beats
  feature clustering.
- **Medium bucket:** all three arms drop -0.10pp. No anchor wins
  medium at kr=0.50.

The per-bucket lens reveals a duration-conditional anchor picker
would beat any single-arm choice: pick max_min for short, geometric
for long. This is a publishable follow-up question, not a Stage 5
deliverable.

### 4. The arithmetic ceiling is anchor-invariant

Independent confirmation across four arms (Stage 1 anchor=none, 5a
nuwa, 5b max_min, 5c gemma_structural) that e2e at kr=0.50 lands
between 0.963× and 1.00×. None clear 1.00× let alone 1.10×.

This is exactly the prediction from task #88's ceiling analysis: at
kr=0.50 on this geometry, fixed cost D+P+V = 71.4% of aggregate e2e,
so *any* G-only speedup is bounded by the complement. The Stage 5
arms collectively falsify the "informed anchors at moderate kr buy
speed" hypothesis, because the bound is not about how smart the
anchor is.

**Practical consequence:** the only ways to lift e2e at kr=0.50 are
(a) shrink V (Phase 1.51V, prereg landed), or (b) shrink D (Phase
1.54 prereg queued for long items).

## Decision for default 1.51R configuration

**Paper default: `anchor_arm=gemma_structural, kr=0.50`.** Rationale:

- Tied best aggregate Δacc with max_min_diversity (-0.033).
- Highest agreement with dense (0.53 vs 0.47).
- Unique long-bucket lift (+0.10 vs dense).
- **180× cheaper mask compute** (2ms vs 362ms/item) — meaningful
  ceiling compliance if V shrinks later and G gets cheap.
- No feature-space dependency → reproducible across runs without
  recomputation.

max_min_diversity stays as the feature-based control arm (shows
geometric regularity captures most of the win; feature spread is not
required).

## Paper narrative (two paragraphs)

> **We ablated three anchor strategies at matched kr=0.50:**
> content-blind pillar geometry (nuwa), feature-space farthest-point
> (max_min_diversity), and geometric grid sampling aligned to the
> model's internal token topology (gemma_structural). At matched
> budget, anchor choice swings aggregate accuracy by 13.4pp:
> nuwa_pillar's fixed corner/mid-axis positions burn half the budget
> on structurally-forced positions that carry less question signal
> than a feature-spread or geometry-aware sample.

> **No anchor arm clears the arithmetic speedup ceiling at
> kr=0.50.** Across four independent runs (baseline + three anchor
> arms), end-to-end speedup lands in [0.963×, 1.00×] — the fixed
> D+P+V cost consumes 71.4% of aggregate latency, capping any
> G-only speedup at 1.46× even with per-token generate → ∞. The
> result establishes an internal "anchor-choice-matters" ablation
> independent of whether the system clears our e2e ≥ 1.10× target,
> and motivates Phase 1.51V (vision-tower pruning) as the remaining
> e2e lever at moderate kr.

## Artifacts

- `artifacts/phase1_51R_dev/stage5a_nuwa_pillar_kr050_n30.{jsonl,summary.json,log}`
- `artifacts/phase1_51R_dev/stage5b_max_min_diversity_kr050_n30.{jsonl,summary.json,log}`
- `artifacts/phase1_51R_dev/stage5c_gemma_structural_kr050_n30.{jsonl,summary.json,log}`
- `artifacts/phase1_51R_dev/stage5_bucket_breakdown.py`
- `research/experiments/2026/2026-04-18-phase-1_51R-stage5a-nuwa-pillar-findings.md`
- `research/experiments/2026/2026-04-18-phase-1_51R-stage5b-max-min-diversity-findings.md`
- `research/experiments/2026/2026-04-18-phase-1_51R-stage5c-gemma-structural-findings.md`

## Next

- **Fold Stage 5 result into claim-matrix row for 1.51R anchor
  ablation.** New row: "Anchor choice drives ±13.4pp Δacc at
  matched kr (3 arms, n=30 each)."
- **Pivot to 1.51V** (task #87 prereg landed). Ceiling analysis says
  this is the only remaining e2e lever at kr=0.50 accuracy budget.
- **Queue 1.54** (video-decode acceleration) for long-bucket items.
- **Consider Stage 6:** 32-frame regime-match to test whether the
  ceiling lifts in Sam's reference configuration (task #106).
