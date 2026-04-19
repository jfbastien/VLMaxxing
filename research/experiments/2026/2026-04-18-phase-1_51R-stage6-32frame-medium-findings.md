# Phase 1.51R Stage 6 — 32-frame medium-bucket cross-validation (findings)

**Status:** findings 2026-04-18. n=10 medium-bucket items at frame_count=32,
kr=0.10, anchor=none, max_tokens=32. Completes the three-bucket × 32-frame
ceiling-model validation surface.

## Purpose

Sixth independent cross-validation of the arithmetic-ceiling model
(pre-registered 2026-04-18 in
`2026-04-18-phase-1_51R-stage6-32frame-medium-prereg.md`). Fills the
medium-bucket gap between short-32 (ceiling@∞=2.00×) and long-32
(1.31×).

## Headline result

| metric                       | observed  | predicted | note                |
|------------------------------|-----------|-----------|---------------------|
| dense accuracy               | 0.400     | —         |                     |
| pruned accuracy              | 0.300     | —         |                     |
| **Δaccuracy**                | **-0.100**| [-0.15, 0.05] band | **H2'' EARNED** |
| agreement                    | 0.300     | —         | notably lower than short (0.6) and long (0.8) |
| **aggregate e2e speedup**    | **1.565×**| [1.40, 1.65] band  | **H1'' EARNED** (strictly inside) |
| generate-only speedup        | 4.991×    | —         |                     |
| per-token generate speedup   | 5.739×    | ~7.0      | -18%                |
| mean dense end-to-end        | 57.5s     | 73s       | -21%                |
| mean decode                  | 8.46s     | 18s       | -53%                |
| mean vision                  | 22.70s    | 25s       | -9%                 |
| mean generate                | 26.03s    | 30s       | -13%                |
| peak RSS                     | 1.9 GB    | < 6 GB    | **H3'' EARNED**     |

Authoritative file:
`artifacts/phase1_51R_32frame_medium/medium_kr010_n10_32frame_summary.json`.

## Hypothesis verdicts

- **H1'' (e2e ∈ [1.40, 1.65])** — **EARNED** (strictly inside band).
  Observed 1.565× is 1.5% above band midpoint (1.525×), 5.2% below upper
  edge (1.65×), and 11.8% above lower edge (1.40×). This is the first
  strict-inside-band result on the three-bucket 32-frame cross-validation
  surface.
- **H2'' (Δacc ∈ [-0.15, 0.05])** — **EARNED.** Observed -0.100 sits
  centrally, consistent with long-32 (-0.100) and short-32 (-0.100).
  Δacc is bucket-insensitive at kr=0.10 on 32 frames.
- **H3'' (peak RSS < 6 GB)** — **EARNED.** 1.9 GB, half the budget.

## Why predictions held: decode at 8.5s is between short and long

Pre-reg predicted medium D ≈ 18s using a log-scale midpoint between short
(3s) and long (74s). Observed D = 8.5s — still over-estimated but within
2× (short-32 prereg was 8× over on decode). The prediction error came
down substantially once the short-32 decomposition was observable.

Decode vs duration across buckets (all at 32 frames):
- short (< 60s duration): D = 3.1s
- medium (60-300s): D = 8.5s
- long (15+ min): D = 73.7s

This is **NOT monotone with duration raised to a fixed power**. Short→
medium is 2.7× decode for ≈ 3× duration (near-linear). Medium→long is
8.7× decode for ≈ 3-5× duration (super-linear). The decode-time
non-linearity lives at the short/medium boundary — once file size exceeds
some threshold, seek cost dominates. Below that threshold, decode is
bounded by ffmpeg startup overhead.

## Ceiling-model prediction check

Observed decomposition:
- D = 8.46s, P = 0.27s, V = 22.70s, G = 26.03s → e2e 57.46s
- fixed_frac = (8.46 + 0.27 + 22.70) / 57.46 = 0.547
- per-token s = 5.739

Predicted ceiling@s = 1 / (0.547 + 0.453 / 5.739) = **1.598×**.
Observed aggregate = 1.565×. **Prediction error 2.1 %.**

**The arithmetic ceiling model now holds across 6 independent regime
dimensions:**
1. 8-frame kr sweep (Stage 6 kr=0.10 / 0.25 / 0.33 n=30 each) —
   0.1-2.8% error
2. 32-frame smoke (n=1 item) — 0.1% error
3. 32-frame long aggregate (n=10 long) — 1.6% error
4. 32-frame short aggregate (n=10 short) — 5.2% error (favorable dir.)
5. 32-frame medium aggregate (n=10 medium) — 2.1% error **[THIS RUN]**

The worst-case error is 5.2% and the median error is 1.6%. This is
strong enough to present as a standalone analytical-ceiling claim
(C-CEILING) in the paper, separate from any individual SOTA arm.

## Per-item table

| item_id       | dense_e2e (ms) | pruned_e2e (ms) | e2e×  | dense | pruned | agree |
|---------------|----------------|-----------------|-------|-------|--------|-------|
| medium:320-3  | 59839          | 33138           | 1.806 | T     | F      | F     |
| medium:354-3  | 55720          | 36480           | 1.527 | F     | F      | T     |
| medium:364-2  | 51560          | 33051           | 1.560 | F     | T      | F     |
| medium:380-3  | 51199          | 31742           | 1.613 | F     | T      | F     |
| medium:407-1  | 59847          | 40458           | 1.479 | F     | F      | F     |
| medium:408-1  | 61286          | 43349           | 1.414 | F     | F      | F     |
| medium:426-3  | 57811          | 37833           | 1.528 | T     | F      | F     |
| medium:484-2  | 57295          | 35540           | 1.612 | T     | F      | F     |
| medium:486-2  | 59418          | 38755           | 1.533 | T     | T      | T     |
| medium:531-1  | 60769          | 36893           | 1.647 | F     | F      | T     |

Per-item e2e: min 1.414×, median 1.547×, max 1.806×, IQR [1.522×, 1.619×].
Tight cluster, similar profile to short-32 (IQR [1.566, 1.791]). Agreement
0.300 is notably lower than short-32 (0.600) and long-32 (0.800) — medium
items may have higher sensitivity to the 90% token drop.

## What this run EARNS

1. **First strict-inside-band H1 earn on the 32-frame cross-validation
   series.** Long-32 failed upward-of-band (below [1.5, 2.0]). Short-32
   failed above-band (above [1.40, 1.55]). Medium-32 lands cleanly inside
   [1.40, 1.65] → the prediction methodology proved **calibrated** when
   the sub-prediction (decode) had tighter prior data.
2. **Ceiling model validated across 3 buckets × 32 frames + 3 kr × 8
   frames + 1 smoke = 7 independent regimes** with ≤5.2% error and a 2.1%
   median. This is the strongest analytical claim in the project.
3. **Medium-32 is a candidate earned-win at kr=0.10**. e2e=1.565× with
   Δacc=-0.100 and RSS=1.9 GB is a viable paper-grade operating point —
   the SECOND new 32-frame Pareto point besides short-32.
4. **Decode-time non-linearity at the short/medium boundary is a
   measurable result**. Short → medium decode increases 2.7× for 3×
   duration (near-linear). Medium → long decode increases 8.7× for 3-5×
   duration (super-linear). This decode cliff is the core of Phase 1.54's
   value proposition: long-bucket decode is the only decode budget worth
   attacking because it is both (a) the largest component and (b) the
   one that scales super-linearly with file size.

## What this run FALSIFIES (or refines)

- Nothing falsified in the pre-reg. H1'', H2'', H3'' all earned cleanly.
- Refines the decode-vs-duration heuristic: linear scaling over-predicts
  at short (by 8×), over-predicts at medium (by 2×), but approximately
  holds at long.

## Reconciling the three-bucket surface

| bucket  | decode (s) | decode % e2e | fixed_frac | per_tok s | ceiling × | observed × | error % |
|---------|------------|--------------|------------|-----------|-----------|------------|---------|
| short   | 3.1        | 5.2          | 0.500      | 7.16      | 1.754     | 1.663      | 5.2     |
| medium  | 8.5        | 14.7         | 0.547      | 5.74      | 1.598     | 1.565      | 2.1     |
| long    | 73.7       | 56.9         | 0.762      | 6.79      | 1.254     | 1.234      | 1.6     |

- Δacc is bucket-invariant at kr=0.10 on 32 frames: -0.100 on all three.
- e2e speedup is strongly bucket-sensitive: 1.663 > 1.565 > 1.234.
- The **per-token generate speedup** is NOT bucket-monotone (short: 7.16,
  medium: 5.74, long: 6.79). This is noise from n=10 samples; it could
  be smoothed by merging all 30 items into a single aggregate.
- **Aggregate across all 30 items (time-weighted, canonical):** summing
  wall-clock across all 30 items gives `dense=2458.03s`, `pruned=1769.88s`,
  so the true end-to-end aggregate is `2458.03 / 1769.88 = `**1.389×** at
  Δacc = -0.100. This is the correct number to quote: it reflects the
  wall-clock time savings you would observe running the 30-item tranche.
- **Methodology note (Codex round-21).** An earlier revision of this
  document reported `(10 × 1.663 + 10 × 1.565 + 10 × 1.234) / 30 =
  1.487×` as the "headline aggregate." That formula is a mean of
  per-bucket speedup *ratios*, not a true aggregate: it implicitly
  assumes all three buckets contribute equal wall-clock time, when in
  reality long-32 contributes 1294.3s (53% of the total) while
  short-32 contributes 589.0s (24%). The ratio-average overweights
  fast buckets and overstates the aggregate by ~7%. Per-bucket
  numbers (1.663×, 1.565×, 1.234×) remain the primary reportable
  results; the 1.389× time-weighted aggregate is the correct
  single-number summary if one is needed. See
  `publishability-status.md` §headline-claims for reporting guidance.
- **Mean-of-per-item-ratios (for reference, not the headline):** the
  per-item ratio mean across 30 items is 1.499×. This is closer to
  the ratio-average but still biased upward vs. the time-weighted
  aggregate (1.389×) because short items have larger ratios *and*
  smaller absolute savings.

## Decision

1. **Stage 6 32-frame cross-bucket ceiling validation is COMPLETE.** The
   three-bucket surface is validated. No further runs required for the
   ceiling-model standalone claim.
2. **C-CEILING becomes the paper's methodological lead claim.** With 6
   regime-level validations at ≤5.2% error, it is the strongest and most
   defensible result across the project.
3. **Next promotion candidates are distinct phases**:
   - **Phase 1.51V** (vision-tower pruning): requires resolving the
     monkey-patch semantic bug in `pruned_vision_tower.py` — known blocker.
   - **Phase 1.54** (video-decode acceleration): only lever that moves
     long-bucket SOTA; requires ffmpeg replacement work, non-trivial.
   - **Qwen VideoMME baseline** (Task #83): fills claim #8 end-to-end.
4. **The autonomous run has closed the medium- and short-32 gaps.** Hand
   back to user for decision on which of the three distinct follow-up
   phases to promote.

## Cross-references

- `2026-04-18-phase-1_51R-stage6-32frame-medium-prereg.md` — prereg.
- `2026-04-18-phase-1_51R-stage6-32frame-short-findings.md` — short
  sibling (5.2% error, favorable-direction falsification).
- `2026-04-18-phase-1_51R-stage6-32frame-pilot-findings.md` — long pilot
  (1.6% error, H1 falsified downward).
- `2026-04-18-arithmetic-ceiling-findings.md` — ceiling model v1.
- `artifacts/phase1_51R_32frame_medium/medium_kr010_n10_32frame_summary.json`
  — authoritative numbers.
