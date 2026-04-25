---
phase: 1.30Z
date: 2026-04-25
parent:
  - research/experiments/2026/2026-04-24-phase-1_30Y-residual-long-q0-keep-rate-findings.md
  - research/experiments/2026/2026-04-24-phase-1_30X-q0-admission-frontier-findings.md
status: preregistered 2026-04-25. Long-bucket continuation of the 1.30Y `kr_Q0 = 0.67` candidate.
---

# 1.30Z — Long-bucket `kr_Q0 = 0.67` continuation

## Why this prereg exists

`1.30Y` was intentionally selection-biased: it only touched the two long
sessions that `1.30X` had already identified as the residual format failures.
That was enough to choose a candidate, not enough to support a claim.

The next paper-relevant question is therefore narrower and cleaner:

**does the promoted long-session candidate (`kr_Q0 = 0.67`,
`kr_followup = 0.50`) stay inside the rescue / format band on the full long
bucket, or was the residual-pair scout only post-hoc curve fitting?**

This phase exists to answer that generalization question before any
duration-conditioned full-union rerun.

## Protocol

- Model: `Qwen2.5-VL-7B-Instruct-4bit`
- Regime: VideoMME `8f`, dev+holdout long bucket only
- Manifest:
  `research/benchmark_manifests/videomme_long_dev_holdout_v1.toml`
- Arms:
  1. `cold_dense`
  2. `streaming_q0_kr067_followup_kr050`
- Runner:
  `scripts/run_phase1_30_sam_streaming.py`
- Wrapper:
  `scripts/run_phase1_30Z_long_q0_kr067.sh`

Estimated runtime on the current laptop:

- cold arm: `~2.5–3.5 h`
- streaming arm: `~1.0–1.5 h`
- paired analysis: `<1 min`
- total: `~3.5–5.0 h`

## Mechanistic instrumentation

This rerun must not rely on naming alone. We now log per-query image-token reuse:

- `image_token_count`
- `image_token_prefix_hit`
- `image_tokens_recomputed`
- `vision_pruning_active`

Primary mechanistic readout:

- `streaming_follow_up_vision_pruning_active_fraction`

Interpretation:

- the committed cold control predates this instrumentation; that is acceptable
  because the analyzer reads follow-up image-token activity from the
  **streaming** rows only
- if `vision_pruning_active_fraction < 0.10`, the follow-up "pruned" path is
  effectively negligible under prompt-cache reuse and the result should be
  described as a **Q0 admission + K-cache reuse** experiment, not as joint V+K
  follow-up pruning evidence
- if `vision_pruning_active_fraction >= 0.10`, follow-up vision pruning is
  materially active on long sessions and the bridge interpretation can continue
  to mention a real vision-leg component on follow-ups

## Hypotheses

### H1 — rescue band survives on the full long bucket

Acceptance:

- long-bucket `Δacc >= -0.10`
- paired amortized speedup `>= 3.0×`

Failure:

- `Δacc < -0.10`, or
- speedup `< 3.0×`

### H2 — format stays clean on the full long bucket

Acceptance:

- parse failures `= 0`
- degenerates `= 0`

Failure:

- any parse failure, or
- any degenerate row

### H3 — residual-pair generalization is not a thermal mirage

Acceptance:

- long-bucket correctness is not worse than the dense-Q0 long reference from
  `1.30W` by more than `1/18`

Failure:

- long-bucket correctness drops by `>= 2/18` relative to the `1.30W` long
  reference

This is a deliberately weak consistency check. The point is to reject the
worst-case "the two-session scout happened to be lucky" story, not to demand
long-bucket parity.

### H4 — follow-up vision activity is measurable or explicitly absent

Acceptance:

- the paired summary emits the follow-up image-token activity fields, and
- those fields support one of two clean interpretations:
  1. `vision_pruning_active_fraction >= 0.10`, so follow-up pruning is
     materially active, or
  2. `vision_pruning_active_fraction < 0.10`, so follow-up pruning is
     effectively bypassed and the policy should be renamed/described accordingly

Failure:

- missing instrumentation fields, or
- internally inconsistent image-token activity fields

## Decision rules

- If H1 and H2 pass, launch `1.30AA`.
- If H2 fails, stop the duration-conditioned bridge lane and record the result
  as a negative on long-bucket format generalization.
- If H1 fails narrowly but H2 passes, treat the result as a bounded negative
  and do not promote the splice from `1.30Y`.
- H4 does not gate continuation by itself, but it **does** gate the wording of
  the result and the interpretation of 1.30W/1.30AA.

## Interpretation rules

- This is the first unbiased test of the `kr_Q0 = 0.67` candidate. It is the
  only result that can validate or kill the 1.30Y scout.
- A pass here is still not a paper number by itself; it only licenses the
  full-union rerun.
- A fail here closes the "cheaper long Q0" rescue lane inside the current
  protocol family.

## Execution

Pending.

## Result

Pending.

## Interpretation

Pending.
