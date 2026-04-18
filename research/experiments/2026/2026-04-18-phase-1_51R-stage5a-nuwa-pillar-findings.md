# Phase 1.51R Stage 5a — nuwa_pillar @ kr=0.50 n=30 Findings

**Status:** findings 2026-04-18, task #91. First Stage 5 anchor-arm
result. Negative — nuwa_pillar does not recover the aggregate
accuracy gap at kr=0.50.

## Prereg hypothesis

Informed anchor selection (nuwa_pillar: 2×2 grid-center + corners +
mid-axis) preserves more question-relevant tokens than plain top-k
novelty, and at kr=0.50 (Sam's reference point, inside the prereg
{0.3..0.7} band) should *recover* the -10pp aggregate accuracy drop
seen at kr=0.10 anchor=none. Falsification: nuwa_pillar at kr=0.50
produces aggregate accuracy within 3pp of dense, and e2e speedup
> 1.10×.

## Result

**Aggregate (n=30):**
- dense_accuracy: 0.400
- pruned_accuracy: 0.233 (**Δacc = -0.167**, WORSE than anchor=none @ kr=0.10's -0.100)
- agreement: 0.43
- e2e_speedup: 0.987× (slower than dense)
- gen_speedup: 0.976× (slower)
- per_token_gen_speedup: 1.157× (marginal)
- kept_tokens_total: 1024 / 2048 (exact; mechanism verified)

**Per-bucket (n=10 each):**

| bucket | dense_acc | pruned_acc | Δacc   | agreement | e2e    | gen    | per_tok |
|--------|----------:|-----------:|-------:|----------:|-------:|-------:|--------:|
| short  | 0.400     | 0.200      | -0.200 | 0.50      | 0.981× | 0.967× | 6.025×  |
| medium | 0.400     | 0.300      | -0.100 | 0.50      | 0.979× | 0.943× | 2.169×  |
| long   | 0.400     | 0.200      | -0.200 | 0.30      | 1.001× | 1.018× | 1.018×  |
| **all**| 0.400     | 0.233      | -0.167 | 0.43      | 0.987× | 0.976× | 3.071×  |

## Hypothesis status: REJECTED

- Aggregate accuracy drops MORE than the kr=0.10 baseline
  (-16.7pp vs -10pp), not less.
- e2e speedup is 0.987× — below 1.0×, the arm is net SLOWER.
- Every duration bucket is worse with nuwa_pillar at kr=0.50 than
  the corresponding bucket with anchor=none at kr=0.10 (short -20pp
  vs -10pp; medium -10pp vs 0; long -20pp vs -20pp).

## Comparison with Stage 1 (anchor=none, kr=0.50, n=30)

| metric            | stage 1 (none, kr=0.5) | stage 5a (nuwa, kr=0.5) |
|-------------------|------------------------|--------------------------|
| e2e_speedup       | 1.00×                  | 0.987×                   |
| gen_speedup       | 1.01×                  | 0.976×                   |
| aggregate accuracy shift | (reported null)  | -0.167                   |

The switch from anchor=none to nuwa_pillar at the same kr=0.50 buys
*no* speedup and *costs* accuracy. Nüwa-structured anchoring is
doing worse than the preserved-structure-plus-top-k-novelty baseline.

## Interpretation

**Why does nuwa_pillar hurt accuracy?**
- Nuwa's "pillar" structure forces 2×2 grid anchors (16 per frame at
  16×16 geometry, × 8 frames = 128 anchors) plus per-frame mid-axis.
  This geometry is designed for H.264-adjacent block-structured
  signals, not for the information-content of Gemma's visual tokens.
- With only 1024 budget at kr=0.50 (128 kept/frame), the mandatory
  64-anchor floor per frame (from nuwa's corner + mid-axis policy)
  consumes half the budget with positions chosen for structural
  reasons, not visual salience. The remaining 64 tokens of
  novelty-fill are competing against 64 structurally-forced tokens
  that may be low-novelty backgrounds.
- Net effect: we keep 50% of tokens but they are less
  question-relevant than the Stage 2b (anchor=none, kr=0.10) keep
  pattern even though the latter keeps far fewer tokens.

**Why no speedup?**
- Per-token generate is 3.07× (matches Stage 3 monotone-in-kr
  finding: kr=0.50 ≈ 1.01× at matched tokens, here higher because
  pruned path runs to max_tokens more often).
- But aggregate e2e is bounded by the arithmetic ceiling at
  kr=0.50. Stage 1 already showed this (e2e=1.00×). Stage 5a
  reconfirms: changing the anchor arm at the same kr does not
  change the ceiling.

## Consequences for the paper

1. **The aggregate -10pp gap at kr=0.10 anchor=none is not
   recoverable via nuwa_pillar at kr=0.50.** One anchor arm down,
   two remaining (max_min_diversity, gemma_structural).
2. **No anchor arm will clear the arithmetic ceiling at kr=0.50.**
   Stage 1 + Stage 5a both e2e ≈ 1.00×. This is not an accident:
   the ceiling analysis (task #88) predicts e2e @ kr=0.50 ≈ 1.00×
   independent of anchor choice because V+D dominates at this
   kr. Only more aggressive pruning (kr ≤ 0.25) can lift e2e, and
   that buys the accuracy collapse Stage 2b documented.
3. **The paper's earned-claim lane narrows further.** If Stage 5b
   (max_min_diversity) and Stage 5c (gemma_structural) also fail,
   the 1.51R narrative is "duration-conditional partial repro
   bounded by the arithmetic ceiling; anchor-selection ablation
   shows informed selection does not recover accuracy at Sam's
   reference kr=0.50." Medium-bucket kr=0.10 anchor=none remains
   the only earned operating point.

## Artifacts

- `artifacts/phase1_51R_dev/stage5a_nuwa_pillar_kr050_n30.jsonl` —
  30 items.
- `artifacts/phase1_51R_dev/stage5a_nuwa_pillar_kr050_n30_summary.json` —
  aggregate stats.
- `artifacts/phase1_51R_dev/stage5a_nuwa_pillar_kr050_n30.log` — run log.
- `artifacts/phase1_51R_dev/stage5_bucket_breakdown.py` — per-bucket
  analysis script.

## Next

- Stage 5b: max_min_diversity @ kr=0.50 n=30 (launched in same
  MLX queue; ~40 min).
- Stage 5c: gemma_structural @ kr=0.50 n=30 (after 5b; ~40 min).
- Decision after Stage 5c: if both arms also reject the recovery
  hypothesis, close Stage 5 with a cross-arm findings doc and
  proceed to Phase 1.51V as the next mechanism.
