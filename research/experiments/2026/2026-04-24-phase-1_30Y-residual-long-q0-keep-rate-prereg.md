---
phase: 1.30Y
date: 2026-04-24
parent:
  - research/experiments/2026/2026-04-24-phase-1_30X-q0-admission-frontier-findings.md
  - research/experiments/2026/2026-04-24-phase-1_30W-q0-dense-followup-pruned-full-findings.md
status: preregistered 2026-04-24. Residual long-session Q0 keep-rate scout.
---

# 1.30Y — Residual long-session Q0 keep-rate scout

## Why this prereg exists

`1.30X` tightened the streaming-bridge problem substantially.

Within the current `1.30` / `1.30W` endpoint family:

- a simple deployable duration policy (`dense_on_medium_short`) already
  passes the rescue band on speed/accuracy
- the only remaining format failures under that policy are two long
  sessions:
  - `videomme:long:783-2`
  - `videomme:long:847-3`

The immediate offline follow-up is even narrower:

- forcing those two sessions onto the existing `1.30W` dense-Q0 family
  makes the policy format-clean,
- but the aggregate speedup only reaches `2.9943×`

So the open question is no longer "can dense Q0 fix the residual long
format failures?" We already know it can.

The question is:

**can a cheaper long-session Q0 keep-rate preserve the clean behavior on
those two binding sessions while shaving the last ~0.006× needed for the
full policy to clear `3.0×`?**

## Scope

Scout only the two binding sessions with a matched cold baseline:

- manifest:
  `research/benchmark_manifests/videomme_long_residual_parse_v1.toml`
- model: `Qwen2.5-VL-7B-Instruct-4bit`
- frame count: `8`
- max tokens: `32`

Arms:

1. `cold_dense`
2. `streaming_q0_kr100_followup_kr050`
3. `streaming_q0_kr075_followup_kr050`
4. `streaming_q0_kr067_followup_kr050`

All streaming arms keep follow-ups at `kr=0.50` and differ only in the
Q0 keep-rate.

## Hypotheses

### H_format_075

`kr_Q0 = 0.75` preserves the clean-format behavior of the dense-Q0
reference on the two binding sessions:

- parse failures `= 0`
- degenerates `= 0`

### H_accuracy_075

`kr_Q0 = 0.75` stays within one query of the dense-Q0 reference on this
2-session scout:

- all-query correctness loss vs `kr_Q0 = 1.0` `>= -1/6`

This is intentionally a narrow scout criterion. The purpose is not to
re-prove the full bridge; it is to see whether the residual-format fix
admits a cheaper Q0 regime.

### H_speed_075

`kr_Q0 = 0.75` lowers the mean first-query wall-clock relative to
`kr_Q0 = 1.0` on the same 2-session scout.

### H_format_067

`kr_Q0 = 0.67` is the more aggressive candidate:

- parse failures `= 0`
- degenerates `= 0`

### H_accuracy_067

`kr_Q0 = 0.67` also stays within one query of the dense-Q0 reference:

- all-query correctness loss vs `kr_Q0 = 1.0` `>= -1/6`

## Decision rules

- If `0.75` passes format + accuracy and clearly reduces Q0 wall-clock,
  promote `0.75` to a **full long-bucket continuation** candidate.
- If `0.67` also passes, prefer `0.67` as the stronger long-bucket
  candidate.
- If both fail, do **not** launch a full long-bucket rerun. Record the
  scout as evidence that the residual format-clean near-miss still needs
  fully dense Q0 on the binding long sessions.

## Interpretation rules

- This is a **bridge-repair scout**, not a paper claim by itself.
- Success here only justifies a longer-bucket continuation.
- Failure here is still informative: it would mean the residual long
  sessions are not fixable by a cheap first-query keep-rate relaxation,
  which sharply narrows the remaining plausible 1.30Y/1.30Z space.

## Execution plan

Planned output directory:

- `research/experiments/2026/artifacts/phase1_30Y_residual_long_q0_keep_rate_20260424/`

Runner:

- `scripts/run_phase1_30_scaleout_streaming.py`

No code changes are required for this scout; the runner already supports
per-query Q0 / follow-up keep-rate overrides.
