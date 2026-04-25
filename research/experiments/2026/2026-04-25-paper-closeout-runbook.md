---
date: 2026-04-25
parent:
  - paper/priority.md
  - research/experiments/registry.md
status: live execution runbook for the remaining paper-closeout queue
---

# Paper Closeout Runbook (2026-04-25)

This file is the operational queue for the remaining paper-critical runs that
can execute **without further coding**.

Preflight status is recorded in:

- `research/experiments/2026/artifacts/paper_closeout_preflight.json`

Current readiness:

- `1.30Z`: ready
- `1.30AA`: ready
- `1.55F`: ready
- `1.55G`: ready
- `1.58`: **blocked** locally; bf16 checkpoint missing at
  `/Users/jfb/models/Qwen2.5-VL-7B-Instruct`

One-command queue runner:

```bash
uv run python scripts/run_paper_closeout_queue.py
```

Dry-run / plan print:

```bash
uv run python scripts/run_paper_closeout_queue.py --dry-run
```

The shell wrappers are intentionally **resumable**:

- if a heavy arm already has both its primary JSONL and summary JSON, the
  wrapper reuses that arm and reruns only the cheap analysis step
- this matters immediately for `1.30Z`, where a completed cold control can be
  reused instead of paying the long-bucket cold cost again

## Priority order

1. **1.30Z** — long-bucket confirmation of the `kr_Q0 = 0.67` candidate
2. **1.30AA** — full measured, no-splice duration-conditioned union rerun
3. **1.55F** — Q3 from repaired post-Q2 state
4. **1.55G** — medium-bucket replication of the 1.55D K=1 point
5. **1.58** — only if the bf16 checkpoint is available

This order is intentional:

- `1.30Z` gates whether `1.30Y` was a real candidate or just residual-pair
  overfitting
- `1.30AA` is the only run in this queue that can produce a publishable local
  bridge number
- `1.55F` is the highest-value adaptive follow-up because it directly tests the
  Q3 state-source hypothesis exposed by `1.55E`
- `1.55G` strengthens the scope of the best current C-PERSIST rescue point

If every runnable item passes and `1.30AA` is unlocked, the remaining wall-clock
budget for the whole queue is roughly **11-15 hours** on the current laptop:

- `1.30Z`: `~3.5-5.0 h`
- `1.30AA`: `~5.5-7.5 h`
- `1.55F`: `~60-75 min`
- `1.55G`: `~1.7-2.2 h`

## Commands

Run from repo root.

### 1.30Z

```bash
./scripts/run_phase1_30Z_long_q0_kr067.sh
```

Primary artifact checks:

- `.../phase1_30Z_long_q0_kr067_20260424/pair_summary.json`
- `.../per_clip_buckets.json`

What to inspect:

- `accuracy_delta_streaming_minus_cold`
- `amortized_speedup_cold_over_streaming`
- `streaming_parse_failures`
- `degenerate_fraction`
- `streaming_follow_up_vision_pruning_active_fraction`

Interpretation:

- if speed/accuracy passes and format is clean, launch `1.30AA`
- if format fails, stop the duration-conditioned bridge lane
- if follow-up pruning activity is near zero, rename the policy family in docs
  to Q0 admission + K-cache reuse

### 1.30AA

Run only if `1.30Z` passes its long-bucket gate.

```bash
./scripts/run_phase1_30AA_duration_conditioned_union.sh
```

Primary artifact checks:

- `.../phase1_30AA_duration_conditioned_union/pair_summary.json`
- `.../per_clip_buckets.json`

What to inspect:

- `accuracy_delta_streaming_minus_cold`
- `amortized_speedup_cold_over_streaming`
- `streaming_parse_failures`
- `degenerate_fraction`
- `streaming_follow_up_vision_pruning_active_fraction`

Interpretation:

- this is the first no-splice bridge number in the 1.30 queue
- do not report the result as joint follow-up pruning unless the
  image-token-activity fields support that

### 1.55F

```bash
./scripts/run_phase1_55F_q3_post_q2_state.sh
```

Primary artifact checks:

- `.../phase1_55F_q3_post_q2_state/pair_metrics_k1_n7.json`
- `.../summary_k1_n7.json`

What to inspect:

- `paired_correctness_diffs`
- `paired_choice_diffs`
- `q_index_breakdown.q3.*`
- `speedup_all_query_median_cold_over_session_follow_up`

Interpretation:

- if Q3 mismatches collapse relative to `1.55E`, the failure mechanism was
  largely cache-source selection
- if Q3 still collapses, the next move should be risk gating, not another
  cache-source tweak

### 1.55G

```bash
./scripts/run_phase1_55G_k1_medium_replication.sh
```

Primary artifact checks:

- `.../phase1_55G_k1_medium_replication/pair_metrics_k1_n10.json`
- `.../summary_k1_n10.json`

What to inspect:

- `paired_correctness_diffs`
- `paired_choice_diffs`
- `speedup_all_query_median_cold_over_session_follow_up`
- pathological follow-up rows in `session_k1_n10.jsonl`

Interpretation:

- this is a scope test for `1.55D K=1`, not a new mechanism story

## Documentation rules after each run

After every completed experiment:

1. append the results to the phase note
2. update `research/decision-log.md` if the lane narrows, reopens, or closes
3. update `research/experiments/registry.md`
4. update `paper/priority.md` and paper-facing docs only if the result changes
   the claim boundary

## Non-runnable item

### 1.58

Blocked locally until:

- `/Users/jfb/models/Qwen2.5-VL-7B-Instruct` exists
- RSS feasibility is rechecked for the bf16 path

Do not spend MLX wall-clock on 1.58 until those prerequisites are true.
