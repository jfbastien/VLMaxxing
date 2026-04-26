---
phase: 1.30AD
date: 2026-04-25
parent:
  - research/experiments/2026/2026-04-24-phase-1_30W-q0-dense-followup-pruned-full-findings.md
  - research/experiments/2026/2026-04-25-phase-1_30Z-long-q0-kr067-findings.md
status: preregistered 2026-04-25. Wrapper landed 2026-04-26; ready to run.
---

# 1.30AD — 1.30W full-union rerun under image-token instrumentation

## Why this prereg exists

`1.30W` (full-union dense Q0 + cache-reused follow-ups, n=171) is the
strongest landed 1.30 lane result: cold 0.561 vs streaming 0.503
(Δacc=−0.058, "bounded near-miss"), exact Q0 parity, format-clean,
2.79× speedup. It is the published number for the 1.30 lane.

**But 1.30W was run before the new image-token instrumentation existed.**
Its `streaming_follow_up_pruning_instrumented_n = 0` row in the pair_summary
means we have no measurement of what `vision_pruning_active_fraction`
actually was for the published 1.30W result. The paper currently treats
1.30W as the reference point for "Q0 admission + K-cache reuse" framing,
but that framing is *inferred* from 1.30Z's measurement on the long
bucket only.

`1.30Z` measured `active_fraction = 0.0` exactly across n=36 long-bucket
follow-ups. That measurement is consistent with the inference for 1.30W,
but it isn't the same data. A peer reviewer can ask: "you say the published
1.30W result is Q0 admission + K-cache reuse; show me the
`vision_pruning_active_fraction` measurement from 1.30W." Currently the
answer is "we can only infer it."

`1.30AD` is the rerun that closes that loop.

## Protocol

- Model: `Qwen2.5-VL-7B-Instruct-4bit` (same as 1.30W)
- Regime: VideoMME 8f, dev+holdout full union (n=57 sessions / 171 queries)
  — IDENTICAL to 1.30W
- Streaming policy:
  - `Q0`: `kr=1.0` (dense, same as 1.30W)
  - `Q1`/`Q2`: `kr=0.50` (same nominal config as 1.30W)
- Cold reference: reuse the landed 1.30W cold control if image-token
  fields match the new analyzer's expectations; else rerun cold dense
- Runner: `scripts/run_phase1_30_sam_streaming.py` (now emits
  `image_token_count`, `image_token_prefix_hit`, `image_tokens_recomputed`,
  `vision_pruning_active` per row)
- Wrapper: `scripts/run_phase1_30AD_instrumented_w_rerun.sh`
- Analysis: `scripts/analyze_phase1_30_sam_streaming_pair.py`
  (existing — reads instrumentation from streaming rows)

Estimated runtime:

- if cold arm reused: streaming-only ~1.5-2.5 h
- if cold rerun: cold ~4-5 h + streaming ~1.5-2.5 h = ~5.5-7.5 h
- analysis: <1 min

## Hypotheses

### H1 — 1.30W's accuracy is reproducible

Acceptance:

- `accuracy_delta_streaming_minus_cold` is within `±0.030` of 1.30W's
  `−0.0585` (i.e. observed Δ ∈ `[−0.088, −0.029]`)

Failure:

- observed Δ outside that band — 1.30W's published number was
  thermally / order-of-execution sensitive

This gate is the basic reproducibility check. With n=171, paired-bootstrap
CI on the observed Δ should be within `±0.04`, so a `±0.030` reproducibility
band is reasonable.

### H2 — 1.30W's mechanism is mechanically Q0 admission + K-cache reuse

Acceptance:

- `streaming_follow_up_vision_pruning_active_fraction < 0.10`
- `streaming_follow_up_all_image_tokens_reused_fraction > 0.90`

Failure:

- otherwise (would be a surprising result; the wrapper config is identical
  to 1.30Z's follow-up config which measured `0.0` activity)

This locks the paper-facing claim that 1.30W is Q0 admission, not
follow-up V-pruning.

### H3 — 1.30W stays format-clean

Acceptance:

- `streaming_parse_failures = 0`
- `streaming_degenerate_count = 0`

This is just a sanity check that the published number was repeatable in
the format dimension.

### H4 — bootstrap CIs reproduce

Acceptance:

- `accuracy_delta_streaming_minus_cold_ci95` is within `±0.05` of 1.30W's
  `[−0.117, 0.000]`

Lighter gate than H1; just confirms the paired-bootstrap analyzer
behaves consistently.

## Decision rules

- If H1 + H2 + H3 + H4 pass, the paper's 1.30W reference becomes a
  fully-instrumented number. The "Q0 admission + K-cache reuse" framing
  is locked with a measurement, not just an inference.
- If H1 fails (reproducibility miss), the published 1.30W number needs
  an asterisk and the paper should report both runs.
- If H2 fails (different active fraction), the framing is wrong and the
  paper needs a fundamental rewrite.

## Interpretation rules

- This rerun is a paper-locking experiment, not a science-discovery one.
  Its purpose is to make the existing 1.30W result peer-review-defensible
  against the "show me the measurement" objection.
- Bootstrap CIs for `accuracy_delta`, `q0_accuracy_delta`, and
  `follow_up_accuracy_delta` should all be reported.

## Curation note

Reuses the 1.30W manifest (`videomme_dev_v1.toml` + `videomme_holdout_v1.toml`),
identical to the would-have-been 1.30AA scope.

## Execution

Ready to run. The wrapper defaults to reusing the landed `1.30W` cold
control because the mechanism instrumentation is read from streaming rows
only; `PHASE1_30AD_RERUN_COLD=1` forces a stricter cold rerun if wanted.
Estimated total session: ~1.5-2.5 h compute with cold reuse.

## Result

Pending.

## Interpretation

Pending.
