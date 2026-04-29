---
phase: 1.30Z
date: 2026-04-24
parent:
  - research/experiments/2026/2026-04-24-phase-1_30Y-residual-long-q0-keep-rate-findings.md
  - research/experiments/2026/2026-04-24-phase-1_30X-q0-admission-frontier-findings.md
status: preregistered 2026-04-24. Long-bucket continuation of the promoted `kr_Q0 = 0.67` candidate.
---

# 1.30Z — Long-bucket continuation for `kr_Q0 = 0.67`

## Why this prereg exists

`1.30Y` answered the residual-pair question decisively enough to justify
the next rung of evidence.

On the two binding long sessions from `1.30X`:

- `kr_Q0 = 0.75` failed on format
- `kr_Q0 = 0.67` stayed clean and improved the pair from `4/6` to `5/6`

That is enough to promote `0.67` from a residual scout candidate to a
**long-bucket continuation** candidate.

The purpose of this phase is to determine whether that cheaper-Q0
behavior survives across the whole long bucket strongly enough to justify
the final, more expensive duration-conditioned union rerun.

## Scope

- manifest:
  `research/benchmark_manifests/videomme_long_dev_holdout_v1.toml`
- model: `Qwen2.5-VL-7B-Instruct-4bit`
- frame count: `8`
- max tokens: `32`

Arms:

1. `cold_dense_long`
2. `streaming_q0_kr067_followup_kr050_long`

## Hypotheses

### H_long_format

The long-bucket candidate remains format-clean:

- parse failures `= 0`
- degenerates `= 0`

### H_long_accuracy

The long-bucket candidate stays within a bounded loss band against the
matched cold long baseline:

- `Δacc_long >= -0.10`

This is intentionally a rescue-band gate, not a strict-equality gate.
The candidate only needs to be good enough to remain viable for the full
composite policy.

### H_composite_rescue

When the new long-bucket `0.67` measurements are combined with the
already-landed medium/short dense-Q0 results from `1.30W`, the composite
policy reaches:

- `Δacc_all >= -0.10`
- speedup `>= 3.0×`
- parse failures `= 0`
- degenerates `= 0`

## Decision rules

- If `H_long_format` and `H_composite_rescue` pass:
  promote this policy to a **full duration-conditioned union rerun**
  candidate.
- If `H_long_format` fails:
  stop the cheaper-long-Q0 continuation; the residual-pair scout did not
  generalize.
- If `H_long_format` passes but `H_composite_rescue` still fails:
  the candidate is informative but not enough; reassess whether a full
  union rerun is worth the thermal risk.

## Interpretation rules

- Passing this phase is **not** yet the paper claim.
- It only earns the right to spend the larger wall-clock on a full union
  duration-conditioned rerun.
- The composite calculation must be labeled explicitly as a splice using
  landed medium/short results from `1.30W` until a fresh duration-
  conditioned full-union run exists.

## Execution plan

Planned output directory:

- `research/experiments/2026/artifacts/phase1_30Z_long_q0_kr067_20260424/`

Runner:

- `scripts/run_phase1_30_scaleout_streaming.py`

No code changes are required for this long-only continuation.
