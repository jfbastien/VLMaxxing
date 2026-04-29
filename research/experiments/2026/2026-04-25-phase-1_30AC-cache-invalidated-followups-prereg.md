---
phase: 1.30AC
date: 2026-04-25
parent: research/experiments/2026/2026-04-25-phase-1_30Z-long-q0-kr067-findings.md
status: preregistered 2026-04-25. Driver change and wrapper landed 2026-04-26; ready to run.
---

# 1.30AC — Cache-invalidated follow-ups (true V-only follow-up pruning test)

## Why this prereg exists

`1.30Z` produced the first quantitative measurement that the
`kr_followup = 0.50` config in the 1.30 streaming lane is mechanically
a **no-op** under prompt-cache reuse:

- `streaming_follow_up_vision_pruning_active_fraction = 0.0`
- `streaming_follow_up_all_image_tokens_reused_fraction = 1.0`

Every image token on every long-bucket follow-up was cache-served
because the Qwen pruning wrapper scatters compact representations back
to the original sequence length, so input_ids are byte-identical
between dense Q0 and pruned-config follow-ups. Prefix matching covers
all image tokens → no recomputation → no actual vision pruning fires.

This means the 1.30 lane has been measuring **Q0 admission + K-cache
reuse**, NOT "follow-up vision pruning." Every existing 1.30 paper
claim about V-pruning on follow-ups is either reframable as Q0
admission OR mechanistically untested. The only experiment that can
produce a legitimate "follow-up vision pruning" claim is one where the
follow-up vision tower **actually fires** — i.e., where the prompt
cache is invalidated between queries so each follow-up rebuilds image
embeddings from the configured pruning policy.

`1.30AC` is that experiment.

## Required driver change

`scripts/run_phase1_30_scaleout_streaming.py` now exposes the required flag:

```
--reset-cache-between-queries
    Reset the PromptCacheState to a fresh instance before each query
    Q1, Q2, ... so per-query vision-tower configuration actually
    activates instead of being suppressed by prefix-cache reuse.
```

Implementation: in the inner per-query loop, when this flag is set,
the runner now does `state = PromptCacheState()` and
`frame_cache.clear()` before each follow-up query, and records
`reset_cache_between_queries=true` in the row + summary outputs.

This flag is intentionally orthogonal to `--drift-refresh-policy` —
that flag was the motivation for the existing per-session cache reset,
but it operates at the session level. The new flag operates at the
per-query level and explicitly disables the K-cache-reuse path.

The wrapper also runs a one-seed smoke before the full arm unless
`PHASE1_30AC_SKIP_SMOKE=1` is set. The smoke validator requires both
follow-up rows to show:

- `reset_cache_between_queries=true`
- `refresh_reason=per_query_reset`
- `prefix_hit=0`
- `image_tokens_recomputed == image_token_count`
- `vision_pruning_active=true`

Failure on any condition aborts before the full `~5-6 h` streaming run.

## Protocol

- Model: `Qwen2.5-VL-7B-Instruct-4bit`
- Regime: VideoMME 8f, **dev+holdout full union** (`n=57` sessions /
  `171` queries) — same scope as `1.30W` and the would-have-been
  `1.30AA`
- Streaming policy:
  - `Q0`: `kr=1.0` (dense)
  - `Q1`/`Q2`: `kr=0.50` (the configured pruning that previously fired
    nominally but was suppressed by cache reuse)
- Cold reference: reuse landed `1.30W` cold control if available, or
  rerun (fresh cold dense Q0 + dense follow-ups; ~4-5h)
- Runner: `scripts/run_phase1_30_scaleout_streaming.py` with
  `--reset-cache-between-queries`
- Wrapper: `scripts/run_phase1_30AC_cache_invalidated_followups.sh`
- Analysis: `scripts/analyze_phase1_30_scaleout_streaming_pair.py`
  (existing analyzer reads `vision_pruning_active` from streaming rows;
  no analyzer change needed)

Estimated runtime:

- if cold arm reused from `1.30W`: streaming-only `~5-6h` because every
  query is now a fresh cold-start vision-tower run
- if cold rerun also: `~9-11h` total

## Hypotheses

### H1 — follow-up vision pruning is now mechanistically active

Acceptance:

- `streaming_follow_up_vision_pruning_active_fraction >= 0.90`
  (the kr=0.50 config fires on at least 90% of follow-ups, expected
  ~100% under explicit cache invalidation)
- `streaming_follow_up_mean_image_tokens_recomputed > 0`
- `streaming_follow_up_all_image_tokens_reused_fraction <= 0.10`

Failure:

- `streaming_follow_up_vision_pruning_active_fraction < 0.90`
  (the new flag did not actually disable cache reuse; bug in driver
  change)

This is a *plumbing* gate, not a science gate. It just verifies that
the new flag does what its name says.

### H2 — follow-up vision pruning either helps or hurts; and we measure which

Two acceptable outcomes (paper-relevant either way):

**H2a (helpful):** with V-pruning mechanically active on follow-ups,
the streaming arm achieves:
- `accuracy_delta >= -0.10` (rescue band)
- `amortized_speedup_cold_over_streaming >= 2.0×`

This would be the first true "follow-up vision pruning helps" result
in the repo and would re-open the C-VISION composition story.

**H2b (hurtful):** with V-pruning mechanically active, the streaming
arm has worse fidelity than 1.30W's cache-reuse-only baseline:

- `accuracy_delta < -0.10`, OR
- `amortized_speedup` actually drops because the per-query vision pass
  costs more than the saved tokens

Either H2a or H2b is publishable as a clean mechanism finding.

### H3 — format clean

Acceptance:

- `streaming_parse_failures = 0`
- `streaming_degenerate_count = 0`

## Decision rules

- If H1 fails, the driver change is broken; fix and rerun.
- If H1 passes and H2a passes, the C-VISION story revives a "follow-up
  vision pruning helps" lane, separate from the Q0 admission lane.
- If H1 passes and H2b is observed, the C-VISION composition story has
  empirical evidence that joint V+K pruning ≠ V-alone + K-alone — the
  composition is non-additive in a measurable sense, which is itself
  paper-relevant.
- Either way, the paper gains a true mechanism reference for "follow-up
  vision pruning" instead of a mechanistically-untested claim.

## Interpretation rules

- This is the only experiment in the 1.30 family that can produce
  paper-claimable evidence about follow-up V-pruning. All previous
  1.30* runs were measuring Q0 admission + K-cache reuse.
- The cost-benefit of cache invalidation must be reported transparently:
  per-query vision tower passes are expensive on long-context Qwen 7B,
  so even a fidelity-preserving result here may not yield wall-time
  speedup.

## Pending follow-ups

- After 1.30AC lands, consider 1.30AD (the symmetric experiment: full
  union with kr_Q0=1.0 everywhere AND new instrumentation, no flag
  change) as a clean baseline to compare against. 1.30AD locks the
  published 1.30W number's mechanism story.

## Execution

Ready to run. The wrapper defaults to reusing the landed `1.30W` cold
control and allows `PHASE1_30AC_RERUN_COLD=1` if a stricter cold rerun
is desired later.

## Result

Pending.

## Interpretation

Pending.
