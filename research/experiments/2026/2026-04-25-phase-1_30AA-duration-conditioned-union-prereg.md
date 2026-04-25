---
phase: 1.30AA
date: 2026-04-25
parent:
  - research/experiments/2026/2026-04-25-phase-1_30Z-long-q0-kr067-prereg.md
  - research/experiments/2026/2026-04-24-phase-1_30W-q0-dense-followup-pruned-full-findings.md
status: preregistered 2026-04-25. Duration-conditioned full-union rerun for the local streaming bridge.
---

# 1.30AA — Duration-conditioned full-union rerun

## Why this prereg exists

The `1.30X` replay and the `1.30Y` scout are useful, but neither is a paper
number:

- `1.30X` is an offline frontier replay and includes oracle upper bounds
- `1.30Y` is explicitly selection-biased and only supports candidate choice

The first publishable bridge result in this family must therefore be a fresh,
fully measured union rerun with **no cross-run splice**.

## Policy under test

- short Q0: `kr = 1.0`
- medium Q0: `kr = 1.0`
- long Q0: `kr = 0.67`
- all follow-ups: `kr = 0.50`

This is the smallest deployable policy family consistent with the current
evidence:

- `1.30W` proved dense Q0 fixes the first-query damage exactly
- `1.30Y` promoted `kr_Q0 = 0.67` as the first cheaper long-session candidate
  that stayed clean on the residual pair
- `1.30Z` is the generalization gate for the long bucket

## Protocol

- Model: `Qwen2.5-VL-7B-Instruct-4bit`
- Regime: VideoMME `8f`, dev+holdout full union
- Manifests:
  - `research/benchmark_manifests/videomme_dev_v1.toml`
  - `research/benchmark_manifests/videomme_holdout_v1.toml`
- Arms:
  1. `cold_dense`
  2. `streaming_duration_conditioned`
- Runner:
  `scripts/run_phase1_30_sam_streaming.py`
- Wrapper:
  `scripts/run_phase1_30AA_duration_conditioned_union.sh`

Estimated runtime on the current laptop:

- cold arm: `~4–5 h`
- streaming arm: `~1.5–2.5 h`
- paired analysis: `<1 min`
- total: `~5.5–7.5 h`

## Hypotheses

### H1 — the duration-conditioned policy earns the rescue bridge

Acceptance:

- all-query `Δacc >= -0.10`
- paired amortized speedup `>= 3.0×`

Failure:

- `Δacc < -0.10`, or
- speedup `< 3.0×`

### H2 — the duration-conditioned policy stays format-clean

Acceptance:

- parse failures `= 0`
- degenerates `= 0`

Failure:

- any parse failure, or
- any degenerate row

### H3 — first-query safety remains stratified exactly as intended

Acceptance:

- short Q0 and medium Q0 are exactly dense by construction
- long Q0 is the only non-dense first-query leg

Operational check:

- the emitted row metadata shows the intended per-duration Q0 keep-rates
  (`1.0/1.0/0.67`)

Failure:

- any duration slice receives the wrong Q0 keep-rate

### H4 — follow-up vision activity is explicit

Acceptance:

- the paired summary emits the follow-up image-token activity fields
- if `vision_pruning_active_fraction < 0.10`, the result is written as
  **Q0 admission + K-cache reuse**, not "pruned follow-ups"
- if `vision_pruning_active_fraction >= 0.10`, the result may mention an
  active follow-up pruning component

This hypothesis is about interpretability, not promotion.

## Decision rules

- H1 + H2 passing earns the first measured, no-splice local bridge result in
  this family.
- H1 passing but H2 failing keeps the lane open as a bounded near-miss, not a
  paper-grade bridge.
- H1 failing closes the current duration-conditioned policy family and shifts
  the next move to either longer sessions or a genuinely different endpoint
  family.

## Interpretation rules

- This is the only experiment in the 1.30 queue that can replace the
  `1.30Y` splice with a publishable number.
- The result should always be described as a **duration-conditioned Q0
  admission** policy first.
- Any mention of follow-up pruning should be conditioned on the logged
  `image_tokens_recomputed` / `vision_pruning_active` evidence.

## Execution

Pending.

## Result

Pending.

## Interpretation

Pending.
