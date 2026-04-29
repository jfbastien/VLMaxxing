---
phase: 1.30AE
date: 2026-04-25
parent:
  - research/experiments/2026/2026-04-25-phase-1_30AB-long-q0-sweep-prereg.md
  - research/experiments/2026/2026-04-25-phase-1_30Z-long-q0-kr067-findings.md
status: preregistered 2026-04-25. Conditional full-union rerun using the smallest 1.30AB long-Q0 rate that passes the long-bucket rescue band.
---

# 1.30AE — Duration-conditioned full-union rerun with a sweep-selected long-Q0 rate

## Why this prereg exists

`1.30AA` is closed for the original policy family because `1.30Z` showed that
`kr_Q0 = 0.67` does not generalize on the long bucket.

The only scientifically honest way to revive a no-splice full-union bridge is:

1. find a long-bucket Q0 keep rate that actually survives the full long-only
   gate (`1.30AB`)
2. rerun the **entire** dev+holdout union fresh with that selected rate

This phase is that second step.

## Protocol

- Model: `Qwen2.5-VL-7B-Instruct-4bit`
- Regime: VideoMME 8f, full dev+holdout union (`n=57` sessions / `171` queries)
- Cold arm: dense first query everywhere
- Streaming arm:
  - short Q0: `kr=1.0`
  - medium Q0: `kr=1.0`
  - long Q0: **smallest `1.30AB` rate that passes the long-only gate**
  - follow-ups: configured at `kr=0.50`, but interpreted by measured activity
- Runner: `scripts/run_phase1_30_scaleout_streaming.py`
- Wrapper:
  `scripts/run_phase1_30AE_duration_conditioned_union_candidate.sh <selected_rate>`
- Analysis: `scripts/analyze_phase1_30_scaleout_streaming_pair.py`

Estimated runtime:

- cold full union: `~4–5 h`
- streaming full union: `~1.5–2.5 h`
- analysis: `<1 min`
- total: `~5.5–7.5 h`

## Hypotheses

### H1 — the selected duration-conditioned union lands inside the rescue band

Acceptance:

- `accuracy_delta_streaming_minus_cold >= -0.10`
- `amortized_speedup_cold_over_streaming >= 3.0×`

Failure:

- `accuracy_delta_streaming_minus_cold < -0.10`, or
- `amortized_speedup_cold_over_streaming < 3.0×`

### H2 — the rerun stays format-clean

Acceptance:

- `streaming_parse_failures = 0`
- `streaming_degenerate_count = 0`
- `n_paired_queries = 171`
- `n_paired_sessions = 57`

Failure:

- any format failure, or incomplete pairing

### H3 — follow-up mechanism labeling stays measurement-driven

Acceptance:

- if `streaming_follow_up_vision_pruning_active_fraction < 0.10`, write the
  result as **Q0 admission + K-cache reuse**

Failure / relabel trigger:

- if follow-up activity is `>= 0.10`, the result may be described as having an
  active follow-up-pruning component

## Decision rules

- Run only if `1.30AB` produces at least one passing long-Q0 candidate.
- Use the **smallest** passing `1.30AB` rate.
- If H1 + H2 pass, `1.30AE` becomes the first measured no-splice local bridge
  result in the 1.30 family.
- If H1 fails, keep the 1.30 lane as a boundary result and do **not** narrate
  the selected rate as a success just because it passed long-only.

## Interpretation rules

- This run is the only paper-claimable union rerun after `1.30Z`. Cross-run
  splices from `1.30Y` remain non-evidence.
- The mechanism label follows the activity instrumentation, not the intended
  CLI flag.
- Even a clean pass still belongs to the **Q0 admission + K-cache reuse**
  story unless the instrumentation proves otherwise.

## Execution

Pending.

## Result

Pending.

## Interpretation

Pending.
