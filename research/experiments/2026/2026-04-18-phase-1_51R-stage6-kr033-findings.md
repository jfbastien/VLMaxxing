# Phase 1.51R Stage 6 — kr=0.33 gemma_structural n=30 findings

**Status:** findings 2026-04-18. Task #107 (partial — kr=0.25 still to
run). Tests the pre-registered ceiling predictions from
`2026-04-18-stage6-kr-sweep-predicted-ceilings.md`.

## Result (landed)

**Aggregate (n=30, VideoMME dev, Gemma 4-E4B-4bit, 8 frames,
anchor_arm=gemma_structural, kr=0.33, max_tokens=32):**

| metric                             | value       |
|------------------------------------|------------:|
| end_to_end_speedup_mean            | **1.046×**  |
| generate_speedup_mean              | 1.347×      |
| per_token_generate_speedup_mean    | 1.411×      |
| dense_accuracy                     | 0.400       |
| pruned_accuracy                    | **0.333**   |
| Δacc                               | **-0.067**  |
| agreement                          | 0.633       |
| mean_kept_tokens_total             | 672 / 2048  |
| effective_keep_ratio               | 0.328       |
| mean_pruned_mask_ms                | 0.38        |
| mean_pruned_novelty_ms             | 13.0        |

**Per-bucket (n=10 each):**

| bucket | e2e (observed) | per_tok | Δacc    | dense_acc | pruned_acc |
|--------|---------------:|--------:|--------:|----------:|-----------:|
| short  |     **1.090×** | 7.904×  | **0.000** | 0.400     | 0.400     |
| medium |     **1.101×** | 2.739×  | -0.100  | 0.400     | 0.300     |
| long   |     **1.025×** | 1.259×  | -0.100  | 0.400     | 0.300     |

## Predictions vs observations

Pre-registered in `2026-04-18-stage6-kr-sweep-predicted-ceilings.md`
**before** Stage 6 kr=0.33 ran. The projection used
gemma_structural/none per-token ratio (0.641) measured at kr=0.50
and applied it to Stage 3 anchor=none kr=0.33 (interpolated 2.10×).

| bucket    | predicted ceiling | observed e2e | |Δ|    |
|-----------|------------------:|-------------:|------:|
| short     |           1.126×  |      1.090×  | 0.036 |
| medium    |           1.096×  |      1.101×  | 0.005 |
| long      |           1.023×  |      1.025×  | 0.002 |
| aggregate |           1.080×  |      1.046×  | 0.034 |

**The arithmetic ceiling model is quantitatively predictive.**
Medium + long buckets hit the ceiling within 0.5%. Aggregate and
short undershoot by ~3%, consistent with anchor-specific overhead
(0.4ms mask + 13ms novelty per item).

Per-token speedup projection was 1.35×; observed 1.411×. The
gemma_structural/none ratio at kr=0.33 was 1.411/2.10 ≈ **0.672**
vs 0.641 at kr=0.50 — slightly less punishing at lower kr. Updating
the projection for kr=0.25: 2.27 × 0.672 ≈ 1.53× per_tok, ceiling
≈ 1.12× aggregate.

## Hypothesis decisions

- **H1 (kr=0.33 aggregate ≤ 1.10×)** — **EARNED**. 1.046× is inside
  the ceiling-predicted band [0.98×, 1.12×] and below the 1.15×
  falsification threshold.
- **H2 (Δacc in [-0.10, -0.033])** — **EARNED at aggregate**
  (-0.067). Per-bucket: short over-performed (0.000), medium/long
  at the band edge (-0.100).
- **H3 (long-bucket e2e ≤ 1.05× — D binds)** — **EARNED**.
  Observed long 1.025× against predicted 1.023×. D is the constraint,
  as ceiling analysis requires.

## Short-bucket finding — candidate earned win

**Short bucket: Δacc = 0.000 at e2e = 1.090× and per_tok = 7.904×.**

This is a candidate publishable operating point alongside the Stage
2b kr=0.10 medium-bucket earned win:

- Stage 2b kr=0.10 medium: Δacc=0 at per_tok=2.71×, e2e=1.267×
  (larger e2e gain, less aggressive per-token speedup).
- Stage 6 kr=0.33 short: Δacc=0 at per_tok=7.904×, e2e=1.090×
  (smaller e2e gain, higher per-token speedup).

Both preserve accuracy. The short-bucket result has the higher
generate-only speedup but the lower e2e speedup because short items
have small D+V (decoded quickly, fewer frames to encode).

**Caveat.** n=10 per bucket is small; accuracy floor is ±0.10 at
bucket level. This is promotable to claim matrix only with n≥30 at
matched cell on a holdout. Stage 6 kr=0.25 provides adjacent evidence;
if kr=0.25 short also holds accuracy, the short-bucket story is
robust.

## Comparison: 1.51R Stage results so far

| stage | anchor            | kr    | e2e    | per_tok | Δacc    | notes                          |
|-------|-------------------|-------|-------:|--------:|--------:|--------------------------------|
| 2b    | none              | 0.10  | 1.229× | 6.83×   | -0.100  | Stage 2b earned medium-bucket  |
| 5a    | nuwa_pillar       | 0.50  | 0.963× | ~1.05×  | -0.167  | REJECTED (geometry mismatch)   |
| 5b    | max_min_diversity | 0.50  | 1.00×  | 1.12×   | -0.033  | mixed (expensive mask)         |
| 5c    | gemma_structural  | 0.50  | 0.992× | 1.116×  | -0.033  | paper default                  |
| **6** | **gemma_structural** | **0.33** | **1.046×** | **1.411×** | **-0.067** | **ceiling-predicted** |
| 6     | gemma_structural  | 0.25  | (pending) | —     | —       | queued                         |

## Key observations

1. **kr swept from 0.50 → 0.33 does what the ceiling says it must.**
   Aggregate e2e moves from 0.992× to 1.046×, per_tok from 1.116× to
   1.411×. Accuracy degrades monotonically from -0.033 to -0.067.
2. **gemma_structural holds short-bucket accuracy at a lower kr than
   anchor=none would.** Stage 2b kr=0.10 short was +0.10 (noise); at
   kr=0.33 structural keeps accuracy nailed to dense.
3. **The ceiling analysis from task #88 continues to predict observed
   outcomes within 3% at matched s.** This is now two independent
   validations (Stage 2b → ceiling analysis → Stage 6 pre-registered
   projection → observed at 3% error).
4. **Agreement 0.633 is the highest across all anchor×kr cells
   measured at n=30.** Higher than Stage 5c (0.533) and Stage 5b.
   Structural anchor with a moderate kr aligns with dense decisions
   the best.

## Next actions

1. **Launch Stage 6 kr=0.25 n=30 with gemma_structural.** Closes the
   8-frame kr × gemma_structural matrix. Expected: e2e ≈ 1.10×,
   Δacc ≈ -0.10 to -0.12.
2. **After kr=0.25 lands, decide Stage 6 32-frame feasibility smoke.**
   If short-bucket accuracy hold is robust across kr=0.33 and 0.25,
   this becomes a second-tier finding regardless of 32-frame outcome.
3. **Update claim-matrix row 11** with kr=0.33 results + short-bucket
   finding flag.
4. **Update decision-log** with the ceiling-prediction confirmation.

## Cross-references

- `research/experiments/2026/2026-04-18-stage6-kr-sweep-predicted-ceilings.md`
  — pre-registered predictions (written before observation).
- `research/experiments/2026/2026-04-18-arithmetic-ceiling-findings.md`
  — underlying decomposition and ceiling formula.
- `research/experiments/2026/2026-04-18-phase-1_51R-stage5-cross-arm-synthesis.md`
  — Stage 5 paper default + kr=0.50 reference.
- `research/experiments/2026/artifacts/phase1_51R_dev/stage6_gemma_structural_kr033_n30_summary.json`
  — authoritative summary numbers.
