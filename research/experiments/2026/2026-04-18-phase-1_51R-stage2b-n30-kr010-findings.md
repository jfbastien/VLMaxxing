---
Phase: 1.51R
Stage: 2b — n=30 at kr=0.10 with instrumentation (duration-bucketed)
State: LANDED 2026-04-18 — aggressive-kr partial-repro framing corrected; accuracy is NOT preserved at full power
Links: [Stage 3 findings](2026-04-18-phase-1_51R-stage3-max-tokens-findings.md), [Stage 1/2 findings](2026-04-18-phase-1_51R-stage1-n30-findings.md), [prereg](2026-04-17-phase-1_51-novelty-pruning-gemma-prereg.md)
---

## TL;DR

Stage 2b ran the kr=0.10 cell at n=30 on `videomme_dev_v1` with the full
token-count instrumentation landed in Task #89. Two findings — one that
confirms prior work, one that **corrects an over-confident claim** from
the n=5 Stage 2 tranche.

**Confirmed (speed):** pruned generate is 2.62× faster mean, 2.69×
per-token. End-to-end 1.12× (vision tower dominates remainder). Matches
Stage 3's prefill-savings prediction for kr=0.10 on an 8-frame clip with
2048 visual tokens.

**Corrected (accuracy):** pruned accuracy is **0.30 (-10pp vs dense 0.40)**
at n=30 — not the 0.40 "=dense" we reported from the n=5 Stage 2 tranche.
kr=0.10 is NOT accuracy-preserving on Gemma 4-E4B-4bit with the `none`
anchor. The n=5 reading was small-sample luck on short items.

## Aggregate — n=30, videomme_dev_v1, anchor=none, kr=0.10, mt=32

| metric                              | value         |
|-------------------------------------|---------------|
| dense accuracy                      | 0.400         |
| pruned accuracy                     | **0.300**     |
| agreement                           | 0.467         |
| end-to-end speedup (mean)           | 1.122×        |
| generate speedup (mean)             | 2.619×        |
| per-token generate speedup          | **2.690×**    |
| mean kept tokens / clip             | 200 (out of 2048 visual) |
| effective keep ratio                | 0.098         |
| dense prompt tokens                 | 2181          |
| pruned prompt tokens                | 333           |
| dense generation tokens (mean)      | 21.0          |
| pruned generation tokens (mean)     | 21.6          |

Differential-generation confound is near zero at the aggregate level —
dense and pruned emit nearly the same number of tokens on average, so
the raw `generate_speedup` of 2.62× is almost identical to the
confound-cleaned `per_token_generate_speedup` of 2.69×. Unlike the n=5
Stage 2 run where one outlier drove the gap, the n=30 mean is clean.

## Duration-bucketed breakdown

| bucket | n  | dense | pruned | Δacc   | agree | e2e    | gen    | per-token gen | d_toks | p_toks |
|--------|----|-------|--------|--------|-------|--------|--------|---------------|--------|--------|
| short  | 10 | 0.400 | 0.300  | −10pp  | 0.300 | 1.356× | 2.631× | 12.52× *      | 17.0   | 23.0   |
| medium | 10 | 0.400 | 0.400  | **=0** | 0.700 | 1.267× | 2.712× | 2.712×        | 23.0   | 23.0   |
| long   | 10 | 0.400 | 0.200  | **−20pp** | 0.400 | 1.062× | 2.981× | 5.267×        | 23.0   | 18.7   |

\* `per_token` on short is inflated by a handful of items where dense
emitted a very short answer (1–2 tokens) and pruned ran to the 32-tok
cap, making the per-item ratio numerically large. Not the clean
metric on this bucket — trust `gen` mean, which is confound-averaged.

**The headline finding** is the asymmetry across buckets. Medium
content preserves accuracy perfectly at kr=0.10; long content collapses
by 20pp; short content drops 10pp with high disagreement. This is
consistent with the kr=0.10 mechanism: keeping 1/10 tokens per frame is
sufficient when the question is spatially local within a frame but
insufficient when the question requires integrating information across
the longer temporal horizon that "long" items carry.

## What Stage 2b changes about our claims

### Corrected from prior reports

- **kr=0.10 is NOT "paper-grade accuracy preservation."** Stage 2 n=5
  showed pruned=0.40 (= dense), but n=30 shows pruned=0.30 (−10pp).
  The correct framing is: *aggressive prefill pruning with an uninformed
  anchor trades ~10pp accuracy for 2.6× generate speedup on videomme_dev*.
- **kr=0.10 is an exploratory operating point, not a headline.** The
  prereg grid was {0.3, 0.4, 0.5, 0.6, 0.7}; kr=0.10 was added
  post-hoc during Stage 2. Keeping it in the results table is fine;
  treating it as the paper number is not.
- **The duration-bucketed story becomes the paper-interesting finding.**
  Medium content at kr=0.10 is a genuine 2.7× speedup without accuracy
  loss — this is a narrow but real slice of the distribution. The long
  bucket reveals where the mechanism breaks, which is valuable for
  scope-of-applicability claims.

### Confirmed from Stage 1/2/3

- **Speedup mechanism reproduces at full power.** 2.69× per-token
  generate speedup at kr=0.10 is consistent with Stage 3's matched-token
  measurement of 3.82× at n=5. The gap (3.82 → 2.69) reflects real
  distribution-level variance across items rather than n=5 sampling.
- **the pre-release source's 1.8× e2e on VideoMME does not reproduce.** Our e2e is 1.12×
  because vision-tower fixed cost dominates the remaining wall-clock
  budget. Consistent with Stage 1 n=30 at kr=0.50 (e2e 1.00×).

## Paper framing updates

**Claim update for claim-matrix row 11 (1.51R OPERATING-POINT-SENSITIVE
PARTIAL REPRODUCTION):** kr=0.10 headline should now read
"2.62× generate speedup with −10pp accuracy on the aggregate, with
medium-length items preserving accuracy at 2.71× and long items
collapsing by 20pp." This is stronger science than the previous
"exploratory positive" framing because it explicitly names the slice
of the distribution where the mechanism works.

**The operating-point story for the paper:** kr=0.10 is pareto-dominant
on the medium bucket (2.7× speedup, Δacc=0). On long content it is
pareto-dominated (−20pp accuracy, only 1.06× e2e). A duration-aware
admission policy that uses kr=0.10 only on medium content and kr≥0.50
on long content would capture the speedup while avoiding the accuracy
cliff. This is a natural next experiment (Stage 6: duration-routing).

## Next experiments

### P0 — Stage 5 (ANCHOR-ARM KR PIVOT): run promotable anchors at kr=0.50 n=30
The Stage 2b result reopens the anchor-arm question as the next science
rather than a confirmation step. Does an informed anchor (nuwa_pillar,
max_min_diversity, gemma_structural) preserve accuracy better than
`none` at a less-aggressive kr where we know the budget is generous
enough for anchor + novelty-fill to both contribute?

Stage 5 pivots from the previously planned kr=0.10 comparison because:
- nuwa_pillar's default anchor floor (64 tokens/frame) exceeds the
  kr=0.10 budget (25/frame), making the arm infeasible at kr=0.10
  without changing its reference config (which would defeat the
  comparison with the method it adapts, arxiv 2602.02951).
- kr=0.50 is the pre-release source's reference operating point and is inside the prereg
  grid {0.3, 0.4, 0.5, 0.6, 0.7}.
- The Stage 1 n=30 baseline at kr=0.50 with `none` (pruned=0.40,
  agreement~0.47) is the apples-to-apples reference that anchor
  accuracy must beat to be promotable.

- Stage 5a: nuwa_pillar at kr=0.50 n=30
- Stage 5b: max_min_diversity at kr=0.50 n=30
- Stage 5c: gemma_structural at kr=0.50 n=30

### P1 — Stage 6: duration-aware routing
Two-armed admission policy that uses kr=0.10 on medium-length items
and kr=0.50 on long items. Predicted outcome (not promised): same
aggregate accuracy as dense with 2× aggregate speedup. This is a
"routing" contribution, not a mechanism contribution, but it's the
natural consequence of the duration-bucketed finding.

### P1 — Stage 7: kr=0.75 accuracy-bump at n=30
Stage 3 showed +20pp accuracy on n=5 at kr=0.75. Still unfalsified at
n=30. If it replicates, it's a novel finding (intermediate-pruning-as-
regularization); if noise, drop.

### P2 — Stage 8: nuwa_pillar at kr=0.30 n=30
Smallest kr at which nuwa_pillar has non-trivial novelty-fill share
(budget=76, floor=64, novelty-fill=12). Tests whether the anchor
structure contributes at near-floor budgets.

## Runtime estimates (benchmark compute only)

| stage                     | n  | arms | kr     | mt | ~wall-clock | notes                          |
|---------------------------|----|------|--------|----|-------------|--------------------------------|
| 5a nuwa_pillar kr=0.50    | 30 | 1    | 0.50   | 32 | ~35 min     | same hardware as Stage 2b      |
| 5b max_min_diversity      | 30 | 1    | 0.50   | 32 | ~35 min     | feature-dependent arm          |
| 5c gemma_structural       | 30 | 1    | 0.50   | 32 | ~30 min     | no feature dependency          |
| 6 duration-routing        | 30 | 1    | mix    | 32 | ~35 min     | needs routing driver (TBD)     |
| 7 kr=0.75 accuracy bump   | 30 | 1    | 0.75   | 32 | ~35 min     |                                |
| 8 nuwa_pillar kr=0.30     | 30 | 1    | 0.30   | 32 | ~35 min     | floor-sensitive cell           |

Total remaining Stage 5 runtime: ~1.7h benchmark wall-clock.
Total Stage 5–8 runtime: ~3.5h benchmark wall-clock.

Implementation time for Stage 6 routing driver is not included — the
driver doesn't yet exist; estimates apply to the benchmark runs once
the driver lands.

## Bug note: feature-path bf16 (2026-04-18)

Launching Stage 5a on nuwa_pillar hit a pre-existing bug in
`scripts/run_novelty_pruning_gemma.py` line 429: `np.asarray(mx_array,
dtype=np.float32)` fails on Gemma's bf16 vision features because MLX
exposes bf16 via buffer-protocol with `item_size=2, format='B'`, which
numpy refuses to coerce. Fix routed through `mx.float32` first, matching
the pre-release predecessor pattern preserved in git history.
Committed in same branch pre-Stage 5a.

## Artifacts

- `artifacts/phase1_51R_dev/stage2b_none_kr010_n30.{jsonl,log,_summary.json}`
  — 30 items, full instrumentation
- `artifacts/phase1_51R_dev/stage5a_smoke/nuwa_pillar_kr050_smoke.{jsonl,log,_summary.json}`
  — single-item smoke that validated the bf16 fix (dense=1, pruned=0 on
  1 item; agreement=0, e2e=1.17×, gen=1.38× — smoke only, not science).
- `scripts/run_novelty_pruning_gemma.py` — bf16 fix at line 428–434.
