---
phase: 1.30Z
date: 2026-04-25
parent: research/experiments/2026/2026-04-25-phase-1_30Z-long-q0-kr067-prereg.md
status: landed 2026-04-25. FAIL rescue gate. 1.30Y residual scout falsified; duration-conditioned admission lane closed at kr_Q0=0.67.
---

# Phase 1.30Z — Long-bucket `kr_Q0 = 0.67` continuation (FINDINGS)

**Verdict:** **`1.30Y` was selection-biased; the long-bucket generalization
test fails the rescue gate.** Δacc = −0.130 on n=18 long sessions / 54 paired
queries, well past the −0.10 acceptance threshold. The duration-conditioned
admission policy at `kr_Q0 = 0.67 + kr_followup = 0.50` is closed in this
configuration. Format-clean, speed-pass, but the accuracy cost is not in band.

## Why this run mattered

`1.30Y` promoted `kr_Q0 = 0.67` from a residual-pair scout to a real
long-bucket candidate after 5/6 success on the two long sessions that
`1.30X` had flagged as residual format failures. That selection-on-DV
choice meant `1.30Y` could only ever support candidate selection, not a
generalization claim.

`1.30Z` is the unbiased long-bucket continuation that gates whether the
candidate generalizes. It also gates the entire downstream `1.30AA`
duration-conditioned union rerun.

## Setup

- Model: `Qwen2.5-VL-7B-Instruct-4bit`
- Regime: VideoMME 8f, dev+holdout long bucket only (n=18 sessions)
- Manifest: `research/benchmark_manifests/videomme_long_dev_holdout_v1.toml`
- Arms: `cold_dense` (reused, already committed) and
  `streaming_q0_kr067_followup_kr050`
- Runner: `scripts/run_phase1_30_sam_streaming.py`
- Wrapper: `scripts/run_phase1_30Z_long_q0_kr067.sh`
- Output dir:
  `research/experiments/2026/artifacts/phase1_30Z_long_q0_kr067_20260424/`
- Auto-committed by the closeout queue runner as `6df2369`.

## Headline results

From `pair_summary.json`:

- `n_paired_queries = 54`, `n_paired_sessions = 18`, `pass_complete_pairing = true`
- `cold_accuracy = 26/54 = 0.481`
- `streaming_accuracy = 19/54 = 0.352`
- **`accuracy_delta_streaming_minus_cold = −0.130`**
- `accuracy_delta_streaming_minus_cold_ci95 = [−0.278, +0.019]`
- `q0_accuracy_delta = −0.111` (n=18), CI95 = `[−0.333, +0.111]`
- `follow_up_accuracy_delta = −0.139` (n=36), CI95 = `[−0.278, 0.000]`
- `amortized_speedup_cold_over_streaming = 3.12×`
- `streaming_parse_failures = 0`, `degenerate_count = 0`, `degenerate_fraction = 0.0`

Mechanism instrumentation (the new image-token-activity fields):

- `streaming_follow_up_pruning_instrumented_n = 36/36` (all rows have it)
- `streaming_follow_up_vision_pruning_active_count = 0/36`
- **`streaming_follow_up_vision_pruning_active_fraction = 0.0`**
- `streaming_follow_up_all_image_tokens_reused_fraction = 1.0`
- `streaming_follow_up_mean_image_tokens_recomputed = 0.0`

This is the first measurement (not inference, measurement) that the
`kr_followup = 0.50` config is mechanically a no-op under prompt-cache
reuse. **Every** image token on every follow-up is cache-served.

## Preregistered verdicts

### H1 — rescue band survives on the full long bucket

**FAIL.** Acceptance: Δacc ≥ −0.10 *and* speedup ≥ 3.0×. Observed:
Δacc = **−0.130** (FAILS by 3pp), speedup 3.12× (passes). The CI upper bound
just nicks 0 (`+0.019`), but the point estimate is unambiguously below the
threshold. The 1.30Y two-session scout was indeed post-hoc curve fitting on
the long bucket.

### H2 — format stays clean on the full long bucket

**PASS.** 0 parse failures, 0 degenerate rows, 0 refresh events. The Q0
admission decision at `kr=0.67` does not push the model into pathological
output space; only the answer accuracy slips.

### H3 — residual-pair generalization is not a thermal mirage

**FAIL.** The n=18 long-bucket correctness drops by ~7 percentage points
relative to dense-Q0 long reference; well past the prereg "≥2/18" failure
threshold.

### H4 — follow-up vision activity is measurable or explicitly absent

**PASS in the explicitly-absent sense.** The instrumentation worked: all 36
streaming follow-up rows record `vision_pruning_active=false` and
`image_tokens_recomputed=0`. This forces the runbook's relabeling rule:
**this lane must be reported as "Q0 admission + K-cache reuse," NOT as
"follow-up vision pruning."** The `kr_followup = 0.50` configuration was
present but never fired.

## Decision rules applied

- H1 fails → **the duration-conditioned admission policy at `kr_Q0=0.67` is
  closed in this configuration.**
- H2 passes → format-clean negative, not a degenerate-output crash.
- The closeout-queue gate `should_launch_130aa = pass_rescue and pass_format`
  evaluated to False → 1.30AA correctly skipped (saved ~6 hours of MLX
  compute on a doomed-by-policy run). The queue logic worked as designed.

## Implications for the paper

1. **The 1.30 lane reverts to its pre-`1.30Y` state.** The best landed
   bridge result remains `1.30W` (full-union dense Q0 + cache-reused
   follow-ups, n=171, Δ=−0.058, "bounded near-miss"). `1.30AA`'s
   duration-conditioned union rerun does not run.

2. **The "follow-up vision pruning" framing is now empirically untenable
   for the 1.30 lane.** Mechanistic instrumentation on n=36 long-bucket
   follow-ups shows `vision_pruning_active_fraction = 0.0` exactly. Any
   paper text that implies V-pruning helps follow-ups must be revised
   to "Q0 admission + K-cache reuse" framing.

3. **A peer reviewer's most natural objection — "is the 1.30Y promotion
   real or selection-bias?" — is now answered.** The long-bucket
   continuation falsifies the candidate. This is itself a publishable
   methodological win on selection-on-DV discipline.

## Anomalies and notes

- The cold arm reused was generated before the new image-token
  instrumentation existed. That is acceptable here because the analyzer
  reads pruning activity only from streaming rows (verified: all 36
  streaming follow-ups are instrumented).
- Q0 cold accuracy (10/18 = 0.556) is much higher than streaming Q0
  accuracy (8/18 = 0.444). The 2-clip difference at Q0 is the dominant
  contribution to Δacc. The follow-up arm suffers a similar but smaller
  hit (Δ=−0.139 there). Both effects compose to the headline −0.130.

## What this rules out and what it does not

**Rules out:** the `kr_Q0 = 0.67` choice as a deployable long-bucket Q0
admission policy in the current 1.30 family.

**Does not rule out:**
- Less aggressive long-bucket Q0 keep-rates (e.g. `kr_Q0 ∈ {0.75, 0.80, 0.85}`)
  may yet land inside the rescue band. This is the natural follow-up
  (`1.30AB`).
- A genuine vision-pruning-on-follow-ups arm where the cache is invalidated
  between queries so the `kr=0.50` config actually fires (`1.30AC`).
- Higher-frame setups where the cost of dense Q0 makes a small Q0 admission
  cut essential.

## Pending follow-ups

- **`1.30AB`** (preregistered, ~4h compute): finer-grained long-Q0
  keep-rate sweep at `kr_Q0 ∈ {0.75, 0.80, 0.85, 0.90}`, otherwise identical
  to 1.30Z. Locates the boundary where the rescue band returns.
- **`1.30AC`** (preregister + small driver change): force cache invalidation
  between follow-ups so `kr_followup = 0.50` is mechanically active. Tests
  whether vision pruning on follow-ups, when actually enabled, helps or
  hurts. This is the only experiment in the 1.30 family that can produce a
  legitimate "follow-up vision pruning" claim.
- **Paper edits** (no compute): revise C-VISION / 1.30 narrative to use
  "Q0 admission + K-cache reuse" wording everywhere, citing the
  `vision_pruning_active_fraction = 0.0` measurement from this run.
