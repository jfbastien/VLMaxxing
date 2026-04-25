---
phase: 1.30AB
date: 2026-04-25
parent:
  - research/experiments/2026/2026-04-25-phase-1_30Z-long-q0-kr067-findings.md
  - research/experiments/2026/2026-04-24-phase-1_30W-q0-dense-followup-pruned-full-findings.md
status: preregistered 2026-04-25. Long-bucket Q0 keep-rate boundary sweep after 1.30Z falsified kr_Q0=0.67.
---

# 1.30AB — Long-bucket Q0 keep-rate boundary sweep

## Why this prereg exists

`1.30Z` falsified the first duration-conditioned long-bucket candidate:
`kr_Q0 = 0.67` lands `Δacc = -0.130` on the full long bucket, even though it
keeps the format clean and still clears `3.12×`.

That result closes the original `1.30AA` policy family, but it does **not**
prove that every long-bucket Q0 admission policy fails. The next falsifiable
question is narrower:

**Where is the long-bucket Q0 keep-rate boundary at which the rescue band
returns, if it returns at all, when follow-ups stay on the same cache-reuse
path?**

This phase answers that with a fixed-rate sweep:
`kr_Q0 ∈ {0.75, 0.80, 0.85, 0.90}`.

## Protocol

- Model: `Qwen2.5-VL-7B-Instruct-4bit`
- Regime: VideoMME 8f, dev+holdout **long bucket only**
- Manifest: `research/benchmark_manifests/videomme_long_dev_holdout_v1.toml`
- Cold reference: reuse the landed `1.30Z` cold control from
  `research/experiments/2026/artifacts/phase1_30Z_long_q0_kr067_20260424/`
- Streaming family:
  - `Q0`: one of `0.75`, `0.80`, `0.85`, `0.90`
  - `Q2/Q3`: configured at `kr=0.50`, but expected to remain cache-served
    unless instrumentation proves otherwise
- Runner: `scripts/run_phase1_30_sam_streaming.py`
- Wrapper: `scripts/run_phase1_30AB_long_q0_candidate.sh <rate>`
- Analysis: `scripts/analyze_phase1_30_sam_streaming_pair.py`

Estimated runtime:

- each rate: `~25–45 min` with reused cold control
- full 4-rate sweep: `~2.0–3.0 h`

## Hypotheses

### H1 — at least one long-Q0 rate re-enters the rescue band

Acceptance:

- there exists a candidate with:
  - `accuracy_delta_streaming_minus_cold >= -0.10`
  - `amortized_speedup_cold_over_streaming >= 3.0×`
  - `parse_failures = 0`
  - `degenerate_fraction = 0`

Failure:

- no candidate meets all of the above

### H2 — the smallest passing rate is the deployable candidate

Acceptance:

- choose the **smallest** rate that passes H1 for the follow-on `1.30AE`
  union rerun

This is a design rule, not a science claim. The paper-facing argument should
prefer the cheapest passing Q0 rate, not the prettiest point estimate.

### H3 — follow-up pruning remains inactive unless measured otherwise

Acceptance:

- if `streaming_follow_up_vision_pruning_active_fraction < 0.10`, write the
  lane as **Q0 admission + K-cache reuse**

Failure / reopen trigger:

- if activity is `>= 0.10`, the mechanistic interpretation changes and the
  paper may discuss an active follow-up-pruning component

## Decision rules

- If H1 fails for all rates, the current `1.30` lane stays a **boundary result**
  and `1.30AE` should not run.
- If H1 passes for one or more rates, run `1.30AE` with the **smallest**
  passing rate.
- If H3 keeps reporting inactivity, the paper must continue to describe this
  family as **Q0 admission + K-cache reuse**, not as follow-up vision pruning.

## Interpretation rules

- This sweep is a boundary search, not a new mechanism claim.
- Do not treat monotonicity as guaranteed. Even though higher keep-rates are
  expected to be safer, every candidate is measured explicitly.
- `1.30Y` remains a selection-biased scout; only `1.30AB` and `1.30AE`
  produce paper-claimable evidence.

## Execution

Pending.

## Result

Pending.

## Interpretation

Pending.
