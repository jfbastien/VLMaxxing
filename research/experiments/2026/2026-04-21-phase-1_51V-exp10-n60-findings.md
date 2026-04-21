---
phase: 1.51V
date: 2026-04-21
parent: research/experiments/2026/2026-04-21-phase-1_51V-exp10-n60-prereg.md
prior:
  - research/experiments/2026/2026-04-21-phase-1_51V-holdout-findings.md
  - research/experiments/2026/2026-04-21-phase-1_51V-session3-findings.md
status: findings (EXP10 n=60 H_stack re-check — preregistered NULL at pooled regime)
tracking: task #152
---

# 1.51V EXP10 n=60 findings — H_stack composition on pooled VideoMME dev+holdout

## TL;DR

**Preregistered NULL.** On the pooled 60-item VideoMME manifest the
V+novelty stack lands at **E2E 1.042×**, far below both the 1.10×
primary gate and the 1.08× partial-confirm gate. The ceiling model
reproduces the observation to within 0.2pp: the n=60 pooled regime is
**decode-dominated** (fixed fraction 0.875 vs dev n=30's 0.79), so
LLM-side pruning on top of V-only cannot deliver the composition lift
the dev n=30 half promised. Mechanism intact; regime binds.

Decision-matrix verdict: **H_stack NULL at pooled regime — close the
reopener; remove from `priority.md` should-do list.** The paper's
three-contribution spine (C-CEILING / C-PERSIST / C-VISION) does not
gain a "stacks multiplicatively" appendix. The ceiling-bounded
composition story remains the honest narrative.

## Four-hypothesis adjudication

| Hypothesis | Gate | Observed | Verdict |
|-----------|------|----------|---------|
| H_exp10n60_e2e (primary)     | paired sum-ratio E2E ≥ 1.10× (partial ≥ 1.08×) | **1.042×** | **NULL** (below 1.08× by 3.8pp) |
| H_exp10n60_thermal (process) | \|decode Δ\| < max(0.02 × decode_ms(ref), 100 ms) | 2040 ms abs (3.07% rel), gate 1328 ms | **FAIL** (arm B hotter than ref) |
| H_exp10n60_agreement (secondary) | ≥ 0.65 | **0.650** (exactly at threshold) | **PASS** |
| H_exp10n60_accuracy (secondary)  | Δ ∈ [−0.10, +0.05] | **−0.017** (0.400 → 0.383 within arm B) | **PASS** |

`priority.md` should-do-#1 promotion rule (independent check):
- ≥ 4pp E2E lift over V-alone: **2.6pp** (arm A 1.0159× → arm B 1.0420×) → **FAILS**
- agreement ≥ 0.75: **0.65** → **FAILS**
- acc within −0.067 vs V-only: pruned 0.400 → 0.383 = −0.017 → **PASSES**

Both decision matrices agree: H_stack does **not** promote. 1/3 gates pass.

## Measured numbers

Paired within-run sum-ratios (driver-computed `end_to_end_speedup_mean`):

| Arm                               | E2E      | generate | per-token generate | agreement | pruned_acc | dense_acc |
|-----------------------------------|----------|----------|--------------------|-----------|------------|-----------|
| A — V-only reference (kr_V=0.50, kr_LLM=1.0) | 1.0159×  | 1.146×   | 1.146×             | 0.933     | 0.400      | 0.400     |
| B — V+novelty (kr_V=0.50, kr_LLM=0.30)       | 1.0420×  | 1.575×   | 1.446×             | 0.650     | 0.383      | 0.400     |

Effective kept tokens arm B: 608 / 2048 = 29.7% (matches target 0.30).

Decode and thermal numbers (mean ms, n=60):

| Quantity | Arm A | Arm B | Δ (B − A) |
|----------|-------|-------|-----------|
| mean_decode_ms          | 66 396 | 68 436 | +2 040 (+3.07%) |
| mean_dense_end_to_end_ms | 81 858 | 82 431 | +573 |
| mean_pruned_end_to_end_ms | 80 576 | 79 107 | −1 469 |
| mean_dense_vision_ms    | 5 124  | 4 736  | −388 |
| mean_dense_generate_ms  | 10 227 | 9 160  | −1 067 |
| mean_pruned_generate_ms | 8 921  | 5 814  | −3 107 |

Arm B ran ~3% hotter on the decode axis, exceeding the 2% revised
thermal gate. Direction is ADVERSE — hotter arm B inflates its dense
denominator slightly and thereby under-states its own E2E ratio by a
few tenths of a percent. Thermal-corrected E2E estimate (substituting
arm A's decode into arm B's composition): 1.043×. Does NOT cross 1.08×.

## Ceiling explanation — why the pooled regime binds

Arm B ceiling arithmetic (per claim 13 / C-CEILING):

```
fixed_frac   = (decode + vision + processor) / e2e_dense
             = (66396 + 4736 + 99) / 82431
             = 0.875
generate_frac = 1 − fixed_frac = 0.125
s_per_token   = 1.446  (observed arm B)

E2E_ceiling  = 1 / (fixed_frac + generate_frac / s_per_token)
             = 1 / (0.875 + 0.125 / 1.446)
             = 1 / 0.961
             = 1.041×
```

Observed arm B E2E is **1.042×**, matching the ceiling to within 0.2pp.
**The regime is compute-bounded on decode; the mechanism is at its
arithmetic ceiling.**

Contrast with dev n=30 at the same configuration (claim 11 stage 6,
kr=0.33 short-bucket):
- Dev fixed_frac ≈ 0.79 (decode was ~12 s / item, e2e ~25 s / item).
- Same `s_per_token ≈ 1.45` would have predicted `1 / (0.79 + 0.21/1.45) = 1.115×`.
- Dev actually landed ~1.11×, ceiling-consistent.

**Regime comparison is the finding**: the same mechanism produces
1.11× dev / 1.042× pooled-n=60 not because the mechanism changed but
because `fixed_frac` moved from 0.79 to 0.875. LLM-side pruning cannot
clear 1.08× when decode is 87% of wall-clock — the arithmetic forbids it.

## V_share drop between dev and pooled

| Cell                  | n  | decode_ms | e2e_dense_ms | V_share (vision / e2e) |
|-----------------------|----|-----------|---------------|-------------------------|
| VideoMME 8f dev       | 30 | ~12 000   | ~25 000       | 15.2%                   |
| VideoMME 8f holdout   | 30 | ~14 000   | ~31 000       | 15.45%                  |
| VideoMME 8f pooled    | 60 | 66 396    | 81 858        | **6.26%**               |

V_share dropped 2.4× in the pooled run vs either n=30 half measured
separately. Root cause hypothesis: session thermal state and/or item
ordering concentrated long-decode items. The pooled mean decode
(66 s / item) is 5× either half's mean. This is a measurement-state
artifact, not a manifest composition artifact — dev 8f and holdout 8f
were merged with no item substitution.

**Implication for C-CEILING:** scatter-back ceiling wording in
`claim-matrix.md:59-71` ("V_share governs 1.51V gains") is a
**per-run V_share**, not a universal per-benchmark property. Long
sessions with warm decoders produce higher fixed_frac; conclusions
about ceiling headroom must be stated with respect to the run-state
V_share, not a prior V_share measurement.

## Pre-registered prediction vs observed

Prereg (`2026-04-21-phase-1_51V-exp10-n60-prereg.md:42`) predicted:

> Weighted-mean prediction from the two n=30 landings:
> `(30 × 1.11 + 30 × 1.064) / 60 = 1.087×`.

**Observed 1.042× is 4.5pp BELOW the weighted-mean prediction.** The
prereg explicitly contemplated this as a possibility (see the third
decision-matrix row: "< 1.08×: H_stack NULL at pooled regime — close
the reopener"), motivated by the hypothesis that a single pooled run
could reveal regime artifacts invisible in two separate n=30 cells.
That hypothesis is earned on the downside: pooled measurement is
NOT a simple weighted mean of sub-pool measurements when the pooled
run shifts thermal / decode state.

## What this changes

1. **`priority.md` should-do #1 (EXP10 n=60 H_stack) → CLOSE as NULL.**
   No paper-reopener. Remove from active should-do queue.
2. **`claim-matrix.md` row 15 (C-VISION)** — add an H_stack n=60
   sub-row documenting the closed-null status. The V-only holdout
   trifecta (VideoMME 8f CLEAN, MVBench 8f CLOSED-ADVISORY, TOMATO 8f
   EARNED-ADVISORY) remains the paper-grade C-VISION evidence and is
   unaffected.
3. **`decision-log.md`** — append closed-null entry for the H_stack
   composition-appendix claim.
4. **Paper narrative** — composition is ceiling-bounded, not
   unbounded. The three-contribution spine stays exactly as framed;
   what does NOT land is an appendix arguing "H_stack composes
   multiplicatively". The composition-appendix framing is replaced
   with a regime-conditional ceiling statement: "stacking V-pruning
   and novelty-pruning composes when the regime is generate-bound;
   in decode-bound pooled-video regimes, the arithmetic ceiling
   (fixed_frac > 0.85) caps E2E below the partial-confirm threshold."
5. **Priority.md should-do #3 (cross-arch Qwen C-VISION probe)**
   remains the next priority — a second architecture on the
   scatter-back ceiling is a much stronger lift than chasing the
   pooled composition appendix.

## Non-reopen conditions

H_stack could be reopened if:
- a *thermally clean* decode-balanced VideoMME pool (decode_ms / e2e <
  0.75) produces ≥ 1.10× E2E; OR
- the arithmetic ceiling model is invalidated by a new cross-regime
  cell.

Neither is on the current should-do queue; both are low-leverage vs
the cross-architecture probe and the 1.29 codec-native slice.

## Artifacts

- `research/experiments/2026/artifacts/phase1_51V_exp10_n60/exp10n60_a_vonly_ref.{jsonl,log,_summary.json}`
- `research/experiments/2026/artifacts/phase1_51V_exp10_n60/exp10n60_b_vplus_novelty030.{jsonl,log,_summary.json}`
- `research/benchmark_manifests/videomme_combined_v1_n60.toml`
- `scripts/run_phase1_51V_exp10_n60.sh`

Total runtime: ~181 min (arm A 5505 s / 91.8 min, arm B 5345 s /
89.1 min). Queue-log provenance:
`phase1_51V_exp10_n60/queue.log` 06:00:24Z → 09:01:14Z.
