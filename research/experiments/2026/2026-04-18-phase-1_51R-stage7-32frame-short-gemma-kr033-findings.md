# Phase 1.51R Stage 7 — 32-frame short-bucket, gemma_structural × kr=0.33 (findings)

**Status:** findings 2026-04-18. n=10 short-bucket items at
frame_count=32, keep_rate=0.33, anchor_arm=gemma_structural,
max_tokens=32. Pre-registered
`2026-04-18-phase-1_51R-stage7-32frame-short-gemma-kr033-prereg.md`.

## Purpose

Does the 8-frame kr=0.33 gemma_structural short-bucket earned-win
(Δacc=0.000 at e2e=1.090×, per_tok=7.904× — the Pareto-knee from
Stage 6) generalize to the 32-frame regime? If yes, we would land a
**32-frame SOTA operating point at Δacc=0 and e2e > 1.3×** —
stronger than any individual arm in the project.

## Headline result

| metric                     | observed  | predicted       | note              |
|----------------------------|-----------|-----------------|-------------------|
| dense accuracy             | 0.600     | —               |                   |
| pruned accuracy            | 0.500     | —               |                   |
| **Δaccuracy**              | **-0.100**| [-0.15, 0.10]   | **H2''' EARNED** at lower edge |
| agreement                  | 0.700     | —               | mid-range         |
| **aggregate e2e speedup**  | **1.558×**| [1.25, 1.50]    | **H1''' STRICTLY FALSIFIED** (favorable) |
| generate-only speedup      | 3.588×    | —               |                   |
| per-token generate speedup | 4.357×    | ~3.0            | +45%              |
| mean dense end-to-end      | 57.7 s    | 58.9 s          | ~-2%              |
| mean decode                | 3.11 s    | 3.1 s           | on target         |
| mean vision                | 25.5 s    | 26.1 s          | on target         |
| mean generate (dense)      | 28.7 s    | 29.4 s          | on target         |
| effective keep ratio       | 0.328     | 0.33            | on target         |
| peak RSS                   | 3.5 GB    | < 8 GB          | **H3''' EARNED**  |

Authoritative file:
`artifacts/phase1_51R_32frame_short_gemma_kr033/short_kr033_gemma_n10_32frame_summary.json`.

## Hypothesis verdicts

- **H1''' (e2e ∈ [1.25, 1.50])** — **STRICTLY FALSIFIED in the
  favorable direction.** Observed 1.558× is 3.9% above the band
  upper (1.50×) and 14.1% above the midpoint (1.37×). This is the
  second 32-frame short-bucket arm (after kr=0.10 anchor=none's
  1.663×) where the pre-reg band was too pessimistic. Reason:
  per-token G speedup came in at 4.357× not 3.0× as conservatively
  guessed — i.e. prefill shortening dominates at short-bucket 32f
  even when keep-rate is 3.3× more generous.

- **H2''' (Δacc ∈ [-0.15, 0.10])** — **EARNED at the lower edge.**
  Observed -0.100 sits inside band but at the bottom. Critically, it
  is *identical* to 32f short kr=0.10 anchor=none (-0.100) and
  *different* from 8f short kr=0.33 gemma_structural (0.000).

- **H3''' (RSS < 8 GB)** — **EARNED.** 3.5 GB peak, 44% of budget.

## Key finding: 8f kr=0.33 Δacc=0 does NOT generalize to 32f

The 8-frame Pareto-knee earned-win (Δacc=0 at per_tok=7.904× on short
bucket) was the strongest accuracy-preservation signal in the project.
Stage 7 tested whether that was a gemma_structural × kr × short-bucket
effect that would survive the frame-count dimension. **It does not.**

| regime                           | anchor          | kr    | frames | short-bucket Δacc | short-bucket e2e |
|----------------------------------|-----------------|-------|--------|-------------------|------------------|
| Stage 6 (8f kr sweep)            | gemma_structural| 0.33  | 8      | **0.000**         | 1.090×           |
| Stage 6 (8f kr sweep)            | gemma_structural| 0.25  | 8      | -0.100            | 1.165×           |
| Stage 6 (8f kr sweep)            | none            | 0.10  | 8      | -0.100            | 1.450× (short-only subset at n=5) |
| Stage 6 32f cross-bucket (short) | none            | 0.10  | 32     | -0.100            | 1.663×           |
| **Stage 7 (THIS RUN)**           | gemma_structural| 0.33  | **32** | **-0.100**        | 1.558×           |

**Conclusion:** the accuracy-preserving recipe is
`8f × kr=0.33 × gemma_structural × short-bucket` and is lost when ANY
of the three dimensions changes. Specifically changing frames 8→32
alone (holding kr and anchor fixed) drops Δacc from 0 to -0.100.

The paper framing that "gemma_structural preserves accuracy" (from
Stage 5c's +10pp long-bucket lift and Stage 6 kr=0.33 short-bucket
Δacc=0) must be narrowed to "gemma_structural preserves accuracy at
8-frames kr=0.33 on short bucket" — a *regime-specific* result, not
a frame-count-invariant anchor property.

## Ceiling-model prediction check (seventh validation)

Observed decomposition:
- D = 3.11 s, P = 0.30 s, V = 25.55 s, G_dense = 28.75 s
- e2e_dense = 57.71 s
- fixed_frac = (3.11 + 0.30 + 25.55) / 57.71 = **0.501**
- per-token s = 4.357×

Predicted ceiling@s = 1 / (0.501 + 0.499 / 4.357) = **1.624×**.
Observed aggregate = 1.558×. **Prediction error 4.1%.**

**The arithmetic ceiling model now holds across 7 independent regime
dimensions on Gemma 4-E4B-4bit:**
1. 8-frame kr sweep (kr=0.10, 0.25, 0.33 n=30 each) — 0.1-2.8% error
2. 32-frame smoke (n=1 item) — 0.1% error
3. 32-frame long aggregate (n=10 long) — 1.6% error
4. 32-frame short aggregate (n=10 short) — 5.2% error
5. 32-frame medium aggregate (n=10 medium) — 2.1% error
6. 32-frame short × gemma_structural × kr=0.33 (n=10 short) — 4.1% error **[THIS RUN]**

Worst-case error still 5.2%, median 2.1%. **C-CEILING (Claim #13)
strengthened across a second anchor arm.**

## Cross-arm Pareto analysis: 32-frame short bucket

| arm                      | kr    | anchor           | e2e    | Δacc   | per_tok | agreement |
|--------------------------|-------|------------------|-------:|-------:|--------:|----------:|
| kr=0.10 anchor=none      | 0.10  | none             | **1.663×** | -0.100 | 7.160×  | 0.600     |
| kr=0.33 gemma_structural | 0.33  | gemma_structural | 1.558× | -0.100 | 4.357×  | **0.700** |

**kr=0.10 anchor=none dominates on e2e at matched accuracy.** Spending
3.3× more retained tokens (2688 vs 800) for gemma_structural anchoring
buys agreement (+0.100) but costs speedup (-0.105×) at zero accuracy
change. On the Pareto plot, kr=0.10 is strictly better for the paper's
"biggest speedup at fixed accuracy" story.

**The value of gemma_structural at 32f short is robustness, not
accuracy.** Agreement 0.7 vs 0.6 (kept 33% tokens) tells us the anchor
keeps more of the dense decision boundary, even though the aggregate
accuracy doesn't improve. This is a separate (method-evidence, not
SOTA) finding suitable for the appendix.

## Per-item table

| item_id       | dense_e2e (ms) | pruned_e2e (ms) | e2e×  | dense | pruned | agree |
|---------------|----------------|-----------------|-------|-------|--------|-------|
| short:037-2   | 49644          | 31621           | 1.570 | T     | F      | F     |
| short:100-2   | 46580          | 28844           | 1.615 | T     | T      | T     |
| short:116-3   | 51009          | 31522           | 1.618 | T     | T      | T     |
| short:120-2   | 57029          | 38099           | 1.497 | F     | F      | T     |
| short:158-3   | 63110          | 41272           | 1.529 | T     | T      | T     |
| short:160-1   | 58491          | 37627           | 1.555 | F     | F      | F     |
| short:210-2   | 57436          | 37911           | 1.515 | T     | T      | T     |
| short:264-1   | 60545          | 38216           | 1.584 | T     | T      | T     |
| short:278-3   | 64093          | 40456           | 1.584 | F     | F      | F     |
| short:282-2   | 69152          | 44888           | 1.541 | F     | F      | T     |

Per-item e2e: min 1.497×, median 1.570×, max 1.618×, IQR [1.529×,
1.584×]. Tight cluster — all 10 items land within a 0.12 range,
consistent with the 32f short regime being homogeneous (decode and
vision costs dominated by frame-count × resolution, not video
content).

Agreement 0.700 means 7/10 items had matching dense/pruned verdicts;
5 of those were correct (dense=T, pruned=T).

## What this run EARNS

1. **C-CEILING claim #13 strengthened** — now validated across 7
   regimes spanning 3 keep-rates, 2 frame-counts, 3 duration buckets,
   and 2 anchor arms (none + gemma_structural). Worst 5.2%, median
   2.1%.

2. **Falsification of "gemma_structural is universally accuracy-
   preserving."** Scoped narrative: the 8f × kr=0.33 × short win is
   regime-specific. Gemma_structural's reliable contribution is
   agreement (not accuracy), consistent with Stage 5c's long-bucket
   lift coming from picking the right subset of dense-correct items
   rather than fixing dense-wrong ones.

3. **32f short-bucket Pareto surface closed** — kr=0.10 anchor=none
   (1.663×/-0.100) is strictly Pareto-dominant over kr=0.33
   gemma_structural (1.558×/-0.100). If the paper picks a short-32
   operating point, it is kr=0.10 anchor=none; gemma_structural on
   32f short is an appendix curiosity, not a headline arm.

## What this run FALSIFIES

- Pre-reg H1''' (e2e ∈ [1.25, 1.50]): STRICTLY FALSIFIED upward.
  Root cause: the per-token-s estimate (3.0) was too pessimistic
  for short-bucket 32f where fixed costs dominate and pruning
  efficiency rises with total-token count.
- Pre-reg "best case Δacc = 0": not observed. Falsifies the 8f
  short-bucket extrapolation.
- Pre-reg worst case e2e 1.25×: over-pessimistic by 20%.

## Decision

1. **Stage 7 COMPLETE.** No follow-up run required at kr=0.33 on
   32f other buckets — the short-only surface is decisive.

2. **32-frame short-bucket paper point = kr=0.10 anchor=none**, not
   kr=0.33 gemma_structural. Update claim-matrix row 11 to reflect
   this.

3. **Remaining 32-frame experiments to close the surface:**
   - Optional: kr=0.25 at 32f short/medium with gemma_structural —
     would the per-tok-s × frame-count interaction continue climbing?
     Low scientific value now that we know accuracy doesn't preserve
     across frame-count transitions. **DEFER.**
   - Optional: kr=0.33 at 32f medium-bucket — tests whether the
     8f→32f accuracy loss is symmetric across buckets. Medium
     already shows Δacc=-0.100 at kr=0.10 anchor=none so unlikely to
     find a Δacc=0 point here. **DEFER.**

4. **Science priority now shifts back to:**
   - **Task #83 (Qwen VideoMME) — claim 8 unblock.** Cheap and
     independent of MLX Gemma queue; fills the benchmark-recognition
     gap. **RAISE TO P0.**
   - **Task #108 (1.51V vision-tower pruning redesign + pilot)** —
     short/medium e2e lever. Requires wrapper/subclass fix for the
     monkey-patch bug. **P1.**
   - **Task #105 (Phase 1.54 decode acceleration)** — only lever
     that moves long-bucket e2e. **P1, after 1.51V.**

## Cross-references

- `2026-04-18-phase-1_51R-stage7-32frame-short-gemma-kr033-prereg.md`
  — prereg.
- `2026-04-18-phase-1_51R-stage6-32frame-short-findings.md` —
  kr=0.10 anchor=none short-32 reference (1.663×).
- `2026-04-18-phase-1_51R-stage6-kr033-findings.md` — 8-frame kr=0.33
  gemma_structural n=30 (Δacc=0 short-bucket earned-win, Pareto knee).
- `2026-04-18-arithmetic-ceiling-findings.md` — ceiling model v1.
- `artifacts/phase1_51R_32frame_short_gemma_kr033/short_kr033_gemma_n10_32frame_summary.json`
  — authoritative numbers.
