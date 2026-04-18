# Phase 1.51R Stage 6 — kr=0.25 gemma_structural n=30 findings

**Status:** findings 2026-04-18. Closes Task #107. Completes the 8-frame
gemma_structural × kr matrix (0.50 / 0.33 / 0.25). Third independent
quantitative validation of the arithmetic ceiling model.

## Result (landed)

**Aggregate (n=30, VideoMME dev, Gemma 4-E4B-4bit, 8 frames,
anchor_arm=gemma_structural, kr=0.25, max_tokens=32):**

| metric                             | value       |
|------------------------------------|------------:|
| end_to_end_speedup_mean            | **1.067×**  |
| generate_speedup_mean              | 1.610×      |
| per_token_generate_speedup_mean    | 1.687×      |
| dense_accuracy                     | 0.400       |
| pruned_accuracy                    | **0.267**   |
| Δacc                               | **-0.133**  |
| agreement                          | 0.500       |
| mean_kept_tokens_total             | 512 / 2048  |
| effective_keep_ratio               | 0.250       |
| mean_pruned_mask_ms                | 0.36        |
| mean_pruned_novelty_ms             | 12.7        |

**Per-bucket (n=10 each):**

| bucket | e2e (observed) | gen    | per_tok | Δacc    | dense_acc | pruned_acc | agreement |
|--------|---------------:|-------:|--------:|--------:|----------:|-----------:|----------:|
| short  |     **1.165×** | 1.532× |  5.825× | -0.100  | 0.400     | 0.300      | 0.600     |
| medium |     **1.147×** | 1.665× |  3.586× | -0.100  | 0.400     | 0.300      | 0.500     |
| long   |     **1.033×** | 1.683× |  1.484× | -0.200  | 0.400     | 0.200      | 0.400     |

## Predictions vs observations

Pre-registered in `2026-04-18-stage6-kr-sweep-predicted-ceilings.md`
**before** Stage 6 kr=0.25 ran. Initial projection used
gemma_structural/none per-token ratio 0.641 at kr=0.50.

| bucket    | predicted ceiling | observed e2e | |Δ|    |
|-----------|------------------:|-------------:|------:|
| short     |           1.157×  |      1.165×  | 0.008 |
| medium    |           1.119×  |      1.147×  | 0.028 |
| long      |           1.029×  |      1.033×  | 0.004 |
| aggregate |           1.099×  |      1.067×  | 0.032 |

**The ceiling model is once again quantitatively predictive.** Short
and long hit predicted to within 1%. Medium overshoots prediction by
2.8%, consistent with the observation that the
gemma_structural/none ratio increases as kr decreases (0.641 @ kr=0.50,
0.672 @ kr=0.33, now 0.743 @ kr=0.25). Aggregate undershoots by ~3%,
same envelope as kr=0.33.

**Updated ratio table** (measured):

| kr    | gemma_structural per_tok | anchor=none per_tok | ratio |
|-------|-------------------------:|--------------------:|------:|
| 0.50  |                   1.116× |              1.740× | 0.641 |
| 0.33  |                   1.411× |              2.10×* | 0.672 |
| 0.25  |                   1.687× |              2.270× | 0.743 |

*anchor=none kr=0.33 is interpolated from Stage 3 sweep.

The ratio **increases monotonically as kr decreases**: structural
anchor's overhead (anchor-score compute + bias toward structured
tokens) is a fixed absolute cost; it becomes a smaller fraction of
per-token speedup as the prune gets more aggressive.

## Hypothesis decisions

- **H1 (kr=0.25 aggregate ≤ 1.12×)** — **EARNED**. 1.067× is inside
  the ceiling-predicted band [1.05×, 1.12×] and well below the 1.18×
  falsification threshold.
- **H2 (Δacc in [-0.14, -0.05])** — **EARNED (band edge)**. Aggregate
  Δacc = -0.133. Long bucket at -0.20 is outside H2 at per-bucket
  granularity; aggregate is inside the band. Accuracy cost monotonic
  in kr: 0.50 (-0.033) → 0.33 (-0.067) → 0.25 (-0.133).
- **H3 (long-bucket e2e ≤ 1.06×)** — **EARNED**. 1.033× against
  predicted 1.029×. D continues to bind on long.
- **H4 (short-bucket accuracy holds at kr=0.25)** — **NOT EARNED**.
  Short Δacc = -0.10 at kr=0.25 vs Δacc = 0.000 at kr=0.33. The
  kr=0.33 short-bucket candidate earned-win does **not** extend to
  kr=0.25.

## Key observation: kr=0.33 is the sweet spot

The full Stage 6 sweep locates the Pareto knee:

| kr    | aggregate e2e | aggregate Δacc | short Δacc | short per_tok |
|-------|--------------:|---------------:|-----------:|--------------:|
| 0.50  |        0.992× |         -0.033 |       N/A  | —             |
| 0.33  |     **1.046×** |     **-0.067** | **0.000**  | **7.904×**    |
| 0.25  |        1.067× |         -0.133 |     -0.100 | 5.825×        |

kr=0.25 earns a slightly larger aggregate e2e (1.067× vs 1.046×) but
at 2× the accuracy cost. **The Pareto-optimal operating point for
an earned win on 8-frame Gemma 4-E4B-4bit is kr=0.33 short-bucket**
(Δacc=0 at per_tok=7.904×, e2e=1.090×). The research-grade finding
survives this second kr probe.

## Comparison: full 1.51R Stage results so far

| stage | anchor            | kr    | agg e2e | agg per_tok | agg Δacc | notes                          |
|-------|-------------------|-------|--------:|------------:|---------:|--------------------------------|
| 2b    | none              | 0.10  | 1.229×  | 6.83×       | -0.100   | Stage 2b earned medium-bucket  |
| 5a    | nuwa_pillar       | 0.50  | 0.963×  | ~1.05×      | -0.167   | REJECTED (geometry mismatch)   |
| 5b    | max_min_diversity | 0.50  | 1.00×   | 1.12×       | -0.033   | mixed (expensive mask)         |
| 5c    | gemma_structural  | 0.50  | 0.992×  | 1.116×      | -0.033   | paper default                  |
| 6     | gemma_structural  | 0.33  | 1.046×  | 1.411×      | -0.067   | **short-bucket earned win**    |
| **6** | **gemma_structural** | **0.25** | **1.067×** | **1.687×** | **-0.133** | **ceiling-predicted** |

## Arithmetic-ceiling status

The ceiling model has now been quantitatively validated at **three
independent kr operating points** (Stage 2b kr=0.10 anchor=none,
Stage 6 kr=0.33 gemma_structural, Stage 6 kr=0.25 gemma_structural).
Per-bucket predicted ceilings are within ≤3% of observed across all
three. **The ceiling model graduates from heuristic to quantitative
prediction.**

This has implications for the paper framing:
- Paper claim 5 is earned at per-token level (per_tok speedup is what
  the mechanism literally delivers; 1.69× at kr=0.25 without
  architectural change).
- The "Sam 1.8× e2e gap" is a regime gap, not a mechanism gap — the
  ceiling analysis makes this quantitative and pre-registers when
  matched regime will or won't produce Sam-like numbers.

## Next actions

1. **Mark Task #107 complete.**
2. **Update decision-log** with kr=0.25 prediction confirmation and
   Pareto-knee identification.
3. **Update claim-matrix row 11** with kr=0.25 numbers and the
   kr=0.33-short-bucket = Pareto knee finding.
4. **Decide 32-frame regime-match smoke.** Task #109 is cheap (n=1);
   run before 1.51V implementation to clear the runway.
5. **Begin 1.51V implementation (Task #108).** Vision-tower pruning
   is the only mechanism lever left to lift the ceiling (reduces V,
   which binds short + medium).

## Cross-references

- `2026-04-18-stage6-kr-sweep-predicted-ceilings.md` — pre-registered
  predictions (written before observation).
- `2026-04-18-phase-1_51R-stage6-kr033-findings.md` — kr=0.33 findings.
- `2026-04-18-arithmetic-ceiling-findings.md` — underlying
  decomposition and ceiling formula.
- `artifacts/phase1_51R_dev/stage6_gemma_structural_kr025_n30_summary.json`
  — authoritative summary numbers.
- `2026-04-18-phase-1_51V-implementation-design.md` — next-step
  implementation plan for lifting the ceiling beyond what 1.51R can
  reach.
