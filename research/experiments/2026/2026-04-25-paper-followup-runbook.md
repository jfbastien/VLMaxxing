---
date: 2026-04-25
parent:
  - research/experiments/2026/2026-04-25-paper-closeout-runbook.md
  - paper/priority.md
  - research/experiments/registry.md
status: live execution runbook for the post-closeout follow-up queue
---

# Paper Follow-up Runbook (2026-04-25)

This is the operational queue **after** the first closeout queue landed:

- `1.30Z` finished and falsified `kr_Q0 = 0.67`
- `1.30AA` is dead for that policy and should not be revived unchanged
- `1.55G` upgraded K=1 selective re-prefill from short-only to short+medium
- `1.55F` was blocked by a runner bug, which is now fixed in `1b7c05a`

The next queue is therefore:

1. `1.55F` — mechanism
2. `1.55I` — long-regime scope
3. `1.55H` — 32f depth boundary
4. `1.30AB` — long-Q0 boundary sweep
5. `1.30AE` — conditional full-union rerun using the smallest passing `1.30AB` rate

`1.58` remains **blocked locally**. The current laptop has 16 GB unified
memory and the local autonomous-run policy caps safe runs at roughly `10 GB`
RSS, so the bf16 lane belongs on a larger-memory machine.

Preflight status is written to:

- `research/experiments/2026/artifacts/paper_followup_preflight.json`

One-command queue runner:

```bash
uv run python scripts/run_paper_followup_queue.py --auto-commit
```

Dry-run / plan print:

```bash
uv run python scripts/run_paper_followup_queue.py --dry-run
```

Preflight only:

```bash
uv run python scripts/preflight_remaining_paper_experiments.py \
  --output research/experiments/2026/artifacts/paper_followup_preflight.json
```

Operational policy for this machine:

- run **sequentially only**
- keep the default `9000 MB` RSS guards
- let the queue continue past an isolated failure unless `--strict` is chosen
- use `--start-at <phase>` to resume after an interruption

Artifact policy for this queue:

- the already-landed `1.55D`, `1.55E`, and `1.55G` artifacts have been
  refreshed with paired bootstrap CIs and `paired_queries_*.jsonl` rows, so
  the historical K=1 / adaptive evidence now has item-level paired support
- `1.55F`, `1.55I`, and `1.55H` now emit both `pair_metrics_*.json` **and**
  `paired_queries_*.jsonl`
- those pair metrics include paired bootstrap CIs for all-query,
  follow-up-only, and Q3-only accuracy deltas
- keep the paired JSONL artifacts; they are the paper-facing answer-pair / raw-link substrate

## Priority order and expected runtime

1. **1.55F** — `~60–75 min`
   Why: highest-leverage causal experiment; tests whether the Q3 failure was
   about inherited cache state rather than adaptive repair itself.
2. **1.55I** — `~60–90 min`
   Why: highest-value scope expansion; can turn C-PERSIST K=1 into a
   short+medium+long result.
3. **1.55H** — `~1.5–2.0 h`
   Why: depth-boundary probe; separates regime breadth from prefix-depth
   robustness.
4. **1.30AB sweep** — `~2.0–3.0 h` total across four candidates
   Why: only honest way to revive a deployable 1.30 bridge after `1.30Z`
   killed `kr_Q0=0.67`.
5. **1.30AE** — `~5.5–7.5 h`, conditional on a passing `1.30AB` candidate
   Why: first no-splice full-union bridge rerun after the original `1.30AA`
   policy died.

Expected wall-clock:

- `~10–14 h` if a `1.30AB` candidate passes and unlocks `1.30AE`
- `~4.5–7 h` if every `1.30AB` candidate fails and `1.30AE` is skipped

## Commands

### Full follow-up queue

```bash
uv run python scripts/run_paper_followup_queue.py --auto-commit
```

### Manual `1.55F`

```bash
./scripts/run_phase1_55F_q3_post_q2_state.sh
```

Inspect:

- `.../phase1_55F_q3_post_q2_state/pair_metrics_k1_n7.json`
- `.../phase1_55F_q3_post_q2_state/paired_queries_k1_n7.jsonl`
- `.../phase1_55F_q3_post_q2_state/summary_k1_n7.json`

Key questions:

- do Q3 pathological outputs collapse relative to `1.55E`?
- does fidelity tighten back toward `1.55D K=1`?
- does the follow-up median stay no slower than the landed `1.55D` reference?

### Manual `1.55I`

```bash
./scripts/run_phase1_55I_k1_long_replication.sh
```

Inspect:

- `.../phase1_55I_k1_long_replication/pair_metrics_k1_n7.json`
- `.../phase1_55I_k1_long_replication/paired_queries_k1_n7.jsonl`
- `.../phase1_55I_k1_long_replication/summary_k1_n7.json`

Key questions:

- does K=1 remain inside the long-bucket fidelity band?
- is long-bucket baseline above the signal floor?
- does the repaired frontier extend from short+medium to all three duration regimes?

### Manual `1.55H`

```bash
./scripts/run_phase1_55H_k1_32f_short_probe.sh
```

Inspect:

- `.../phase1_55H_k1_32f_short_probe/pair_metrics_k1_n7.json`
- `.../phase1_55H_k1_32f_short_probe/paired_queries_k1_n7.jsonl`
- `.../phase1_55H_k1_32f_short_probe/summary_k1_n7.json`

Key questions:

- does K=1 survive the 32f depth boundary?
- if it fails, is the failure drift-dominated or pathology-dominated?

### Manual `1.30AB`

```bash
./scripts/run_phase1_30AB_long_q0_candidate.sh 0.75
./scripts/run_phase1_30AB_long_q0_candidate.sh 0.80
./scripts/run_phase1_30AB_long_q0_candidate.sh 0.85
./scripts/run_phase1_30AB_long_q0_candidate.sh 0.90
```

Inspect each candidate’s:

- `pair_summary.json`
- `paired_queries.jsonl`
- `per_clip_buckets.json`

Choose the **smallest** rate that satisfies:

- `accuracy_delta_streaming_minus_cold >= -0.10`
- `amortized_speedup_cold_over_streaming >= 3.0×`
- `streaming_parse_failures = 0`
- `streaming_degenerate_count = 0`

### Manual `1.30AE`

Run only if `1.30AB` finds at least one passing long-Q0 rate.

```bash
./scripts/run_phase1_30AE_duration_conditioned_union_candidate.sh 0.80
```

Interpretation rule:

- if `streaming_follow_up_vision_pruning_active_fraction < 0.10`, this is a
  **Q0 admission + K-cache reuse** result, not a follow-up-pruning result

## Analysis-only follow-up

No MLX time required:

```bash
uv run python scripts/build_per_item_drift_summary.py
```

This refreshes:

- `research/experiments/2026/artifacts/phase1_61_per_item_drift_summary.json`

That artifact is the current paper-ready source for the per-item-drift table:

- `1.30` V-only Q0 drift
- `1.42` Gemma MVBench identity drift
- `1.55A` persistent-KV attractor distribution

## Not in this queue

- **1.30AC** — cache-invalidated follow-up pruning. Worth doing if we want a
  real follow-up-pruning mechanism claim, but it needs a driver change first.
- **1.58** — larger-memory-machine only.
- **Matched Qwen/Gemma drift probes** — explanation-strength work, not a local
  blocking item for the next queue.
- **1.29 runtime decoder integration / scale-out-style matched baselines** — needed
  for systems-venue strength, but outside this immediate local paper closeout.
