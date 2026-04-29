# Claim #11 — novelty-pruning reproduction log (detailed stage history)

**Purpose.** Claim-matrix row 11 accumulated ~2500 words of
stage-by-stage narrative covering Phase 1.51R novelty-pruning on
Gemma 4-E4B-4bit + VideoMME. Codex round-21 flagged that row as
overloaded. This log holds the full stage narrative; claim-matrix
row 11 now carries a compressed digest + pointer here.

**Provenance.** Extracted 2026-04-19 from `paper/claim-matrix.md`
pre-compression. No new facts; formatting and ordering only.

## Stage 1 — the pre-release source's reference kr, n=30 null (2026-04-18)

- **Configuration:** kr=0.5, anchor=none, n=30 VideoMME dev.
- **Result:** aggregate e2e=1.00×, gen=1.01× — **preregistered
  NULL** at the pre-release source's implicit operating point. Full statistical power
  at n=30.

## Stage 2b — kr=0.10 with Task #89 instrumentation (2026-04-18)

- **Configuration:** kr=0.10, anchor=none, n=30 VideoMME dev.
- **Result:** aggregate pruned_acc=0.30 vs dense_acc=0.40 (**-10pp,
  NOT accuracy-preserving**); e2e=1.12×, gen=2.62×, per-token
  gen=2.69×.
- **Confound check.** diff-gen confound ≈0 at n=30 (dense tokens
  21.0, pruned tokens 21.6 — within noise).
- **Per-bucket asymmetry — paper-interesting finding.** Medium
  items preserve accuracy (Δacc=0, gen=2.71×, agreement=0.70);
  short -10pp; long -20pp.
- **Correction.** The earlier n=5 kr=0.10 "pruned_acc=dense" from
  Stage 2 was small-sample luck on short items.

## Stage 3 — kr × max_tokens grid (n=5 subset, 2026-04-18)

- **Purpose.** Resolve the diff-gen confound.
- **Result.** At matched tokens, prefill-only gen speedups are
  monotone in kr:
  - kr=0.10: 3.82×
  - kr=0.25: 1.83×
  - kr=0.50: 1.01×
  - kr=0.75: 0.69×
- **Instrumentation lands (commit 6f389ca):** per-item
  `generated_tokens` + `per_token_generate_speedup_mean`.
- **bf16 fix (commit 469570c):** unblocks feature-dependent arms.

## Arithmetic ceiling analysis (Task #88, 2026-04-18)

- **Observed e2e 1.229× vs ceiling 1.213×** at observed per-token
  G speedup 6.83× — within 2%.
- **Ceiling@∞ = 1.462×** (even with s→∞, aggregate cannot exceed).
- **Fixed cost D+P+V = 71.4% of e2e.** Decode 66.9%, vision 15.2%.
- **Long items:** D alone = 85.7% of e2e, ceiling@∞ 1.098×.
- **Implication.** the pre-release source's 1.8× is arithmetically unreachable on
  long-video items without touching D (sparser frame sampling or
  faster decoder — Phase 1.54 territory). Phase 1.51V is the
  short/medium lever.

## Stage 5 — anchor ablation at kr=0.50 n=30 (2026-04-18)

- **nuwa_pillar:** Δacc=-0.167 **REJECTED**.
- **max_min_diversity:** Δacc=-0.033 earned.
- **gemma_structural:** Δacc=-0.033 earned + highest agreement
  (0.53) + unique long-bucket lift (+0.10 vs dense) + 180× cheaper
  mask compute (2ms vs 362ms).
- **Paper default anchor = gemma_structural.**
- **Cross-arm.** Anchor choice drives a 13.4pp aggregate Δacc
  swing at matched kr. No anchor arm clears e2e ≥ 1.10× at
  kr=0.50 (ceiling predicted, confirmed across four independent
  runs).

## Stage 6 — gemma_structural kr sweep (2026-04-18)

### kr=0.33 n=30

- Aggregate e2e=1.046×, pruned_acc=0.333, dense_acc=0.400
  (Δacc=-0.067), per_tok=1.411×, agreement=0.633.
- Per-bucket: **short Δacc=0.000 at e2e=1.090× and per_tok=7.904×
  — candidate earned win**. Medium Δacc=-0.100 e2e=1.101×.
  Long Δacc=-0.100 e2e=1.025× (exactly at D-ceiling).
- Predictions matched observations within 0.5% on medium+long and
  3% on short+aggregate — **second quantitative validation** of
  the ceiling model.

### kr=0.25 n=30

- Aggregate e2e=1.067×, pruned_acc=0.267, dense_acc=0.400
  (Δacc=-0.133), per_tok=1.687×, agreement=0.500.
- Per-bucket: short e2e=1.165× Δacc=-0.100; medium e2e=1.147×
  Δacc=-0.100; long e2e=1.033× Δacc=-0.200.
- Predictions within 0.8% (short, long) to 2.8% (medium) —
  **third quantitative ceiling-model validation**.
- **kr=0.33 short-bucket earned-win does NOT extend to kr=0.25**
  (Δacc slips from 0.000 to -0.100).

### Pareto knee

**8f × kr=0.33 × gemma_structural × short-bucket** (Δacc=0.000 at
per_tok=7.904×, e2e=1.090×) is the Pareto-knee earned-win
operating point on 8-frame Gemma 4-E4B-4bit VideoMME.

gemma_structural/anchor=none per-token ratio rises monotonically
as kr tightens (0.641 at kr=0.50, 0.672 at kr=0.33, 0.743 at
kr=0.25). The 8-frame kr × gemma_structural matrix is now closed.

## Stage 6 — 32-frame regime-match validation (2026-04-18)

### Long pilot (n=10, kr=0.10, anchor=none)

- **H1 (e2e ∈ [1.5, 2.0]) FALSIFIED** (observed 1.234×, below band).
- **H2 (Δacc ∈ [-0.15, -0.05]) EARNED** (-0.100).
- **H3 (RSS < 12GB) EARNED** (5.3 GB).
- Aggregate fixed_frac on long-32 = 0.762 → ceiling@s=6.788 =
  1.254× predicted vs 1.234× observed (**1.6% error**).
- Smoke item 669-1 (e2e=1.439×) was outlier; items 2-10 cluster
  [1.155×, 1.331×].
- **Ceiling@∞ on mean long-32 item = 1.312×** — token pruning
  cannot exceed this regardless of s on our pipeline.
- **Phase 1.54 is the load-bearing lane** for aggregate SOTA on
  long bucket. the pre-release source's 1.8× long claim is NOT reproducible if
  wall-clock includes video decode; generate-only speedup 5.02×
  exceeds 1.8× — scope-definition, not mechanism failure.

### Short-bucket cross-validation (n=10, kr=0.10, anchor=none)

- **H1' (e2e ∈ [1.40, 1.55]) STRICTLY FALSIFIED in favorable
  direction** — observed 1.663× is 7.3% above band upper.
- **H2' (Δacc ∈ [-0.15, 0.05]) EARNED** at -0.100.
- **H3' (RSS < 8GB) EARNED** at 4.6 GB.
- Decomposition: D=3.09s (pre-reg predicted 26s — 8× over-estimate),
  V=26.1s, G=29.4s, fixed_frac=0.500, per_tok=7.160×, ceiling@s=7.16
  = 1.754× predicted vs 1.663× observed (**5.2% error**).
- **Ceiling model now validated across 5 independent regimes**
  (8-frame kr sweep 0.1–2.8% + smoke 0.1% + long-32 1.6% +
  short-32 5.2%). C-CEILING graduates to standalone publishable
  analytical claim independent of any specific SOTA arm.
- Short-32 at 1.663× / Δacc=-0.100 is a new Pareto operating
  point distinct from 8f kr=0.33 short (1.09× / Δacc=0): +52%
  additional speedup for 10pp accuracy cost.
- Short-32 is already at its decode floor — Phase 1.54 does not
  lift short-bucket.

### Medium-bucket cross-validation (n=10, kr=0.10, anchor=none)

- **H1'' (e2e ∈ [1.40, 1.65]) EARNED (strictly inside band)** at
  1.565×.
- **H2'' (Δacc ∈ [-0.15, 0.05]) EARNED** at -0.100.
- **H3'' (RSS < 6GB) EARNED** at 1.9 GB.
- Decomposition: D=8.46s (14.7% of e2e, between short's 5.2% and
  long's 56.9%), V=22.70s, G=26.03s, fixed_frac=0.547,
  per_tok=5.739×, ceiling@s=5.74=1.598×.
- **Prediction error 2.1%** — first strict-inside-band H1 earn on
  the series.
- **Δacc is bucket-invariant at -0.100 across all three 32-frame
  buckets at kr=0.10.**
- Ceiling model validated across **6 independent regime dimensions**
  (8-frame kr sweep 0.1–2.8% + smoke 0.1% + long-32 1.6% + short-32
  5.2% + medium-32 2.1%) with median 1.6% and worst-case 5.2%.

### Cross-bucket 32-frame aggregate (n=30 dev split)

- **e2e = 1.389× time-weighted at Δacc=-0.100** —
  **DEV-ONLY indicative number, NOT a paper headline.**
- Holdout tranche has not been run. **Per-bucket numbers are the
  primary reportable results.**
- *Methodology note (Codex round-21, 2026-04-19):* an earlier
  revision reported 1.487× using a mean of per-bucket speedup
  ratios; the correct aggregate is `sum(dense_e2e) /
  sum(pruned_e2e)` across the 30 items (2458.03s / 1769.88s =
  1.389×). The ratio-average was biased +7% upward because it
  gave equal weight to fast (short 589s total) and slow (long
  1294s total) buckets.
- Decode non-linearity lives at medium/long boundary — short→medium
  near-linear with duration, medium→long super-linear (seek-
  dominated).

## Stage 7 — 32f short-bucket gemma_structural × kr=0.33 n=10 (2026-04-18)

- **Purpose.** Test whether the 8f kr=0.33 gemma_structural
  short-bucket earned-win (Δacc=0 at 1.090×) generalizes to 32f.
- **Does not.** Observed e2e=1.558× Δacc=-0.100 agreement=0.700
  per_tok=4.357×, fixed_frac=0.501, ceiling@s=4.36=1.624×
  (4.1% error — **seventh** ceiling-model regime validation).
- **H1''' [1.25, 1.50] strictly falsified favorably** (1.558× above
  1.50× by 3.9%); **H2''' [-0.15, 0.10] earned at lower edge**.
- **The accuracy-preservation recipe `8f × kr=0.33 ×
  gemma_structural × short-bucket` is regime-specific** — changing
  frames 8→32 alone drops Δacc from 0 to -0.100.
- **Paper framing narrowed:** gemma_structural's reliable
  contribution is **agreement** (+0.100 at matched accuracy on 32f
  short), not aggregate accuracy.
- **32f short-bucket Pareto:** kr=0.10 anchor=none (1.663×/-0.100)
  strictly dominates kr=0.33 gemma_structural (1.558×/-0.100).

## Overall verdict for claim #11

- **DURATION-CONDITIONAL PARTIAL REPRODUCTION.**
- the pre-release source's 1.8× e2e does **not** reproduce at the pre-release source's implicit operating
  point (Stage 1 kr=0.5: 1.00×).
- Aggressive pruning (kr=0.10) gives e2e=1.12× aggregate on 8f,
  1.389× on 32f (time-weighted), at -10pp accuracy aggregate.
- **Medium-bucket** slice at kr=0.10 is the narrow earned-win
  (Δacc=0 at 2.71× gen).
- **Short-bucket kr=0.33 gemma_structural** at 8f is the
  Pareto-knee earned-win (Δacc=0 at 1.09×).
- **Arithmetic ceiling (C-CEILING, claim #13)** graduates to a
  standalone publishable analytical claim: the token-pruning
  speedup is bounded by `1/(fixed_frac + (1-fixed_frac)/s)` with
  ≤5.2% median error across 7 regimes.
- **Paper fallback:** publish as "duration-conditional partial
  reproduction + pre-registered null at the pre-release source's kr" with the
  duration × kr grid as the headline figure and C-CEILING as the
  analytical contribution.

## Authoritative artifacts

- `artifacts/phase1_51R_dev/stage2b_none_kr010_n30.jsonl` + summary
- `artifacts/phase1_51R_dev/stage5_{nuwa_pillar,max_min_diversity,gemma_structural}_kr050_n30_*`
- `artifacts/phase1_51R_dev/stage6_gemma_structural_kr{033,025}_n30_*`
- `artifacts/phase1_51R_32frame_{pilot,short,medium}/*`
- `artifacts/phase1_51R_32frame_short_gemma_kr033/*`
- `artifacts/arithmetic_ceiling/*`

## Cross-references

- `paper/claim-matrix.md` row 11 (digest)
- `paper/claim-matrix.md` row 13 (C-CEILING — standalone claim)
- `paper/publishability-status.md` §headline-claims
- `research/decision-log.md` rows 71–91 (stage-by-stage decisions)
- `research/experiments/2026/2026-04-18-phase-1_51R-stage{2b,5,6,7}-*.md`
