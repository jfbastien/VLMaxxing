# Methodology: Temporal Coverage Metrics

Date: 2026-04-16
Parent: [pareto-reporting.md](pareto-reporting.md),
[../literature-map-2026-04-16.md](../literature-map-2026-04-16.md)

The 2026-04-16 audits raised the "budget placement over time" theory:
two policies with similar effective fresh budget can behave differently
if one spends fresh tokens around the decisive event and the other
spends them in the wrong part of the clip. This document defines the
metrics we will instrument to test that theory, starting with phase
1.31 (failure predictor) and extending into sticky-dynamic /
projector-group evaluations (phases 1.26 / 1.27).

## Problem statement

Our current scalar metric `effective_fresh_frames` captures total
fresh budget but not placement. It cannot distinguish:

- cached policy A: refresh concentrated on frames 4–5 (the motion
  event), with high reuse on frames 1–3 and 6–8
- cached policy B: refresh uniformly scattered across all 8 frame
  pairs

Both may report the same `mean_active_reuse`, but A captures the
event-window evidence while B dilutes it across inactive frames.

TOMATO is explicitly designed to resist single-frame / few-frame
answers, so evidence is temporally concentrated by construction.
TempCompass suppresses single-frame shortcuts via conflicting-video
pairs. Both benchmarks suggest *when* refresh happens is at least as
important as *how much*.

## Metrics to log

### 1. Per-frame fresh-token histogram

Per item, per policy, log the fraction of blocks marked fresh
(= not reused) at each frame pair index 1..N-1.

```
fresh_by_frame = [
  fraction_fresh_at_pair(i) for i in 1..N-1
]
# expected shape: (num_items, N-1)
```

This is already implicit in the per-frame `raw_reused_ratios` and
`active_reused_ratios` already logged; we just need to persist the
PER-FRAME array, not only the mean.

### 2. Longest stale run per token

For each block index b, compute the longest consecutive run of
frames during which that block was reused. A large longest-stale-run
means a specific spatial block accumulated stale state across most
of the clip.

```
for b in 0..num_blocks-1:
  longest_stale[b] = max_consecutive_reuses(reuse_decisions_per_frame[b])
```

Report the per-item `max(longest_stale)` and the per-block
distribution (histogram bucket edges at 2, 4, 8 frames).

### 3. Onset-refresh recall

If per-item critical frames are known (e.g., TOMATO direction items
where the decisive motion is in frames 3–4), report the fraction of
critical-frame pairs where refresh happened (≥ some active-region
threshold of novel blocks).

- **Requires** per-item critical-frame annotation. Deferred to a
  separate annotation pass; proxy version: use the frame-pair with
  maximum per-pair change metric as the "inferred critical window"
  and report refresh there.

### 4. Temporal coverage entropy (or Gini)

Entropy of the per-frame fresh-block count distribution. Low entropy
→ refresh concentrated in a few frames; high entropy → uniformly
scattered.

```
p_i = fresh_blocks_at_frame_i / sum_fresh_blocks_across_clip
entropy = -sum(p_i * log(p_i))  # 0 to log(N-1)
```

### 5. Event-window overlap (oracle)

When an event-window annotation exists (TempCompass has these
implicitly via conflict pairs; TOMATO direction has implicit
direction-change frames), report:

```
refresh_in_event_window / total_refresh_budget
```

i.e., fraction of our fresh-budget spent in the annotated event
window. High overlap = good placement; low overlap = wasted budget.

## How these enter the pipeline

### Data-logging change (proposed)

`scripts/run_benchmark_track_a.py::_mix_qwen_features` already
returns `raw_reused_ratios` and `active_reused_ratios` per
frame-pair. We extend the returned payload with:

- `per_pair_fresh_active`: list[float] (== 1 - active_reused_ratios)
- `per_block_reuse_run_histogram`: list[int] length 9 (histogram
  bucket edges at runs of 1, 2, 3, 4, 5, 6, 7, 8+)

`_write_summary` aggregates these per item into the saved JSONL and
summary.

### Analysis change (proposed)

`scripts/pareto_analysis.py::analyze` gets a new `--with-placement`
flag that reads the per-pair distributions from the cached jsonls
and computes:

- median / variance of per-pair fresh budget
- median / max longest-stale-run
- entropy

Output extends the Pareto JSON.

### Phase 1.31 (failure predictor) consumes these

The failure predictor logistic regression adds features:

- per-pair fresh variance
- longest-stale-run max
- coverage entropy

as candidate predictors of `disagree_with_dense`.

## Methodology rule update

Once placement instrumentation (the data-logging changes above)
lands, Pareto candidate reports **should** include the 2-axis
skyline (acc, fresh) AND a placement summary (median longest-stale,
coverage entropy) alongside. Policies with similar fresh budget but
different placement profiles should be flagged; they may behave
differently on holdout.

Until instrumentation lands (pending as of 2026-04-16), this rule is
aspirational rather than mandatory. Phase 1.31 failure predictor
will be the first phase to cite placement metrics from new
instrumentation; earlier phases can continue reporting the scalar
`effective_fresh_frames` alone.

## Links

- [docs/research-strategy-post-codecsight.md](../research-strategy-post-codecsight.md)
- [phase 1.31 failure predictor prereg](../../research/experiments/2026/2026-04-16-phase-1_31-failure-predictor.md)
- [2026-04-16 audit decision-log row on budget placement](../../research/decision-log.md)
