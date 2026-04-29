---
date: 2026-04-26
parent:
  - research/experiments/2026/2026-04-25-paper-followup-runbook.md
  - paper/priority.md
  - research/experiments/registry.md
status: live execution runbook for the adaptive-C-PERSIST breadth + 1.30 mechanism queue
---

# Paper Adaptive + Mechanism Runbook (2026-04-26)

This queue starts **after** the 2026-04-25 follow-up queue landed:

- `1.55F` adaptive short PASS (`0/21`, `24.91×`, `1.44 GB`)
- `1.55I` fixed `K=1` long PASS (`0/21`, `11.24×`)
- `1.55H` fixed `K=1` 32f PASS (`0/21`, `20.37×`)
- `1.30AB` long-Q0 sweep FAILS across `kr_Q0 ∈ {0.75, 0.80, 0.85, 0.90}`
- `1.30AE` is therefore dead for the current cache-reuse family

The next batch is therefore:

1. `1.55F-medium` — adaptive breadth
2. `1.55F-long` — adaptive breadth
3. `1.55F-32f` — adaptive depth
4. `1.55J` — fixed `K=1` sampler-variation scout
5. `1.30AC` — true follow-up-pruning mechanism test
6. `1.30AD` — instrumented `1.30W` rerun for paper locking

`1.58` remains blocked locally. The laptop still has 16 GB unified memory
and the autonomous-run policy still caps safe runs near `9-10 GB` RSS.

Preflight status is written to:

- `research/experiments/2026/artifacts/paper_adaptive_mechanism_preflight.json`

One-command queue runner:

```bash
uv run python scripts/run_paper_adaptive_mechanism_queue.py --auto-commit
```

Dry-run / plan print:

```bash
uv run python scripts/run_paper_adaptive_mechanism_queue.py --dry-run
```

Preflight only:

```bash
uv run python scripts/preflight_remaining_paper_experiments.py \
  --output research/experiments/2026/artifacts/paper_adaptive_mechanism_preflight.json
```

Operational policy for this machine:

- run **sequentially only**
- keep the default `9000 MB` RSS guards
- let the queue continue past an isolated failure unless `--strict` is chosen
- use `--start-at <phase>` to resume after an interruption

Expected wall-clock with the default cold-reuse settings:

- `~10.5–14 h` for the full queue
- add `~4–5 h` only if you intentionally force fresh cold reruns for `1.30AC`
  or `1.30AD`

## Why this queue exists

### 1.55F-medium

Why: this is the highest-value extension of the strongest single-cell result in
the repo. If it passes, adaptive C-PERSIST stops being "short only" and becomes
at least a short+medium claim.

Expected outcome: likely PASS. Fixed `K=1` already survived the same tranche,
and the repaired-state adaptive path was materially stronger than fixed `K=1`
on short.

Interpretation:

- PASS means adaptive C-PERSIST breadth is growing, not just fixed-K breadth.
- FAIL means the adaptive advantage is regime-sensitive and must be scoped.

### 1.55F-long

Why: this is the highest-value scope upgrade after medium. If it passes, the
adaptive lane becomes short+medium+long at 20f.

Expected outcome: plausible PASS, but long-bucket baseline competence is lower
and that needs to be interpreted honestly if the run lands.

Interpretation:

- PASS means adaptive C-PERSIST is genuinely three-regime at 20f.
- FAIL means long bucket is a scope boundary for adaptive reuse even though
  fixed `K=1` survives there.

### 1.55F-32f

Why: this is the adaptive depth-boundary probe. It asks whether the repaired
adaptive state survives the 32f short regime, not just the 20f cells.

Expected outcome: likely PASS, with a larger speedup than 20f if prefill-
dominance scaling keeps holding.

Interpretation:

- PASS means adaptive C-PERSIST survives both scope and depth stress.
- FAIL means the adaptive path is more depth-sensitive than the fixed `K=1`
  path.

### 1.55J

Why: fixed `K=1` has the best breadth/depth evidence, but all landed K=1
cells are greedy-decoding cells. `1.55J` reruns the original short-bucket K=1
cell with deterministic `temperature=0.7` sampling so we can distinguish a
robust paired-fidelity result from a greedy-only artifact.

Expected outcome: likely PASS, but this is exactly the reviewer objection worth
testing. If one or two paired choices move, the fixed lane remains useful but
the paper should call the result sampler-conditioned.

Interpretation:

- strict PASS plus the `>=14/21` session-correctness floor means fixed `K=1`
  short-bucket fidelity is not visibly greedy-only.
- primary PASS with strict miss means sampler variation moves individual answers
  but does not break the repaired-frontier claim.
- FAIL means the fixed `K=1` breadth claim needs a sampler-conditioned caveat.

### 1.30AC

Why: the existing 1.30 family never actually pruned follow-ups under cache
reuse. `1.30AC` is the first run that makes follow-up pruning mechanically
active by resetting the cache between queries.

Expected outcome: follow-up pruning should finally become active; whether that
helps is genuinely uncertain. My expectation is that this will be more valuable
as a mechanism clarification than as a positive latency result, because forcing
per-query vision passes is expensive.

The wrapper runs a one-seed smoke before the full arm. That smoke hard-fails if
follow-up rows do not show `prefix_hit=0`, all image tokens recomputed, and
`vision_pruning_active=true`. This prevents a full run from silently repeating
the inactive-follow-up-pruning path.

Note: `vision_pruning_active=false` is correct when a follow-up keep rate is
`1.0`; the field means "pruning actually happened," not merely "the reset flag
fired." `1.30AC` sets follow-up keep rate to `0.50`, so active rows should be
true.

Interpretation:

- If activation fails, the driver change is wrong.
- If activation passes and accuracy/speed stay acceptable, the follow-up-
  pruning story revives.
- If activation passes and fidelity or speed worsens, that is still strong
  science: it says the cache-reuse family was hiding the true cost of active
  follow-up pruning.

### 1.30AD

Why: this is paper locking, not discovery. It measures the mechanism of the
published `1.30W` reference point under the new instrumentation.

Expected outcome: likely reproduce `1.30W` within a narrow band and confirm
that follow-up pruning activity is negligible.

Interpretation:

- PASS means the paper can state `1.30W` as **Q0 admission + K-cache reuse**
  from a direct measurement.
- FAIL means the published 1.30W line needs a reproducibility or framing
  footnote.

## Commands

### Full queue

```bash
uv run python scripts/run_paper_adaptive_mechanism_queue.py --auto-commit
```

### Manual `1.55F-medium`

```bash
./scripts/run_phase1_55F_medium_adaptive_replication.sh
```

Inspect:

- `.../phase1_55F_medium_adaptive_replication/pair_metrics_k1_n10.json`
- `.../phase1_55F_medium_adaptive_replication/paired_queries_k1_n10.jsonl`
- `.../phase1_55F_medium_adaptive_replication/summary_k1_n10.json`

### Manual `1.55F-long`

```bash
./scripts/run_phase1_55F_long_adaptive_replication.sh
```

Inspect:

- `.../phase1_55F_long_adaptive_replication/pair_metrics_k1_n7.json`
- `.../phase1_55F_long_adaptive_replication/paired_queries_k1_n7.jsonl`
- `.../phase1_55F_long_adaptive_replication/summary_k1_n7.json`

### Manual `1.55F-32f`

```bash
./scripts/run_phase1_55F_32f_short_adaptive_replication.sh
```

Inspect:

- `.../phase1_55F_32f_short_adaptive_replication/pair_metrics_k1_n7.json`
- `.../phase1_55F_32f_short_adaptive_replication/paired_queries_k1_n7.jsonl`
- `.../phase1_55F_32f_short_adaptive_replication/summary_k1_n7.json`

### Manual `1.55J`

```bash
./scripts/run_phase1_55J_k1_sampler_variation.sh
```

Inspect:

- `.../phase1_55J_k1_sampler_variation/pair_metrics_k1_n7.json`
- `.../phase1_55J_k1_sampler_variation/paired_queries_k1_n7.jsonl`
- `.../phase1_55J_k1_sampler_variation/summary_k1_n7.json`

### Manual `1.30AC`

```bash
./scripts/run_phase1_30AC_cache_invalidated_followups.sh
```

Inspect:

- `.../phase1_30AC_cache_invalidated_followups/pair_summary.json`
- `.../phase1_30AC_cache_invalidated_followups/paired_queries.jsonl`
- `.../phase1_30AC_cache_invalidated_followups/per_clip_buckets.json`

Key mechanism questions:

- `streaming_follow_up_vision_pruning_active_fraction >= 0.90`?
- `streaming_follow_up_all_image_tokens_reused_fraction <= 0.10`?
- once active, is follow-up pruning helpful or hurtful under matched budgets?

### Manual `1.30AD`

```bash
./scripts/run_phase1_30AD_instrumented_w_rerun.sh
```

Inspect:

- `.../phase1_30AD_instrumented_w_rerun/pair_summary.json`
- `.../phase1_30AD_instrumented_w_rerun/paired_queries.jsonl`
- `.../phase1_30AD_instrumented_w_rerun/per_clip_buckets.json`

Key paper-locking questions:

- does `Δacc` stay within `±0.030` of landed `1.30W`?
- is follow-up pruning activity still `< 0.10`?
- is the rerun still format-clean?

## Not in this queue

- `1.58` — larger-memory-machine only.
- `1.30AB@0.95` — optional boundary-polish point if we later decide the
  `0.90 → 1.00` transition needs one more measured point.
- matched Qwen/Gemma drift probes — high-value explanation work, but separate
  from this immediate queue.
- `1.29` runtime decoder integration / scale-out-style matched baselines — systems-
  venue work, not this local paper-closeout batch.
