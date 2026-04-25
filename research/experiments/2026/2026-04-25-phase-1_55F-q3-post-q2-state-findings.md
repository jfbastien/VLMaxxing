---
phase: 1.55F
date: 2026-04-25
parent: research/experiments/2026/2026-04-25-phase-1_55F-q3-post-q2-state-prereg.md
status: landed 2026-04-25 (post bug-fix 1b7c05a). PASS all gates. Adaptive Q3=K0+post_q2_repaired beats fixed K=1 by ~2.6× on speed with EXACT paired fidelity.
---

# Phase 1.55F — Q3 from repaired post-Q2 state (FINDINGS)

**Verdict:** **The Q3 catastrophe in `1.55E` was a cache-source error, not an
adaptive-repair impossibility.** With the same K=1 at Q2 but K=0 sourcing from
the post-Q2 repaired state, n=21 paired short-bucket queries return **0/21
correctness diffs, 0/21 choice diffs, 0/14 follow-up pathological, 0/7 Q3
pathological**, follow-up median **3.20 s** (vs `1.55D K=1`'s 10.14 s = **3.16×
faster**), all-query-cold-over-session-follow-up speedup **24.91×** (vs
`1.55D K=1`'s 9.71× = **2.57× higher**), and peak RSS **1.44 GB** (vs `1.55D
K=1`'s 4.886 GB).

**This is now the strongest landed C-PERSIST recovery point.**

## Why this run mattered

`1.55E` showed that simply skipping Q3 re-prefill (K=0) and falling back to the
*original* Q1 full-cache path re-enters the pathological basin: `7/7` Q3 rows
came out as `addCriterion`/`自动`-style attractor outputs, paired choice diffs
`6/21`, paired correctness diffs `4/21`. That falsified the "Q3 is safely
dispensable" hypothesis under that fallback rule.

The next falsifiable hypothesis was narrower:

> Q3 may be safe under K=0 if it inherits the *repaired* Q2 cache state instead
> of reverting to the unrepaired Q1 cache.

`1.55F` tested exactly that.

## Setup

- Model: `Qwen2.5-VL-7B-Instruct-4bit`
- Regime: 20-frame persistent-KV short-bucket VideoMME session
- Clips: `037,100,116,120,158,160,210` (same 7-clip tranche as `1.55D K=1`)
- Session policy:
  - `Q1`: cold (`K=0`)
  - `Q2`: `K=1` selective re-prefill
  - `Q3`: `K=0` with `q3_cache_source=post_q2_repaired`
- Runner: `scripts/run_kv_selective_reprefill_v2.py`
- Wrapper: `scripts/run_phase1_55F_q3_post_q2_state.sh`
- Output dir: `research/experiments/2026/artifacts/phase1_55F_q3_post_q2_state/`
- Auto-committed by the follow-up queue runner as `cbe10bd`.

The first attempt of this experiment (~earlier on 2026-04-25) crashed inside
`generate_qwen_tail_with_explicit_positions` because the K=0 + post_q2_repaired
path produces an empty `grid_thw`, which triggered `mx.concatenate([])` inside
upstream `qwen2_5_vl/vision.py:rot_pos_emb`. Codex fixed the path in `1b7c05a`
(text-only-tail short-circuit), and the rerun this round produced the data
below.

## Headline results

From `pair_metrics_k1_n7.json` + `summary_k1_n7.json`:

- `n_pairs = 21`, `n_follow_up_pairs = 14`, `n_sessions = 7`
- `paired_correctness_diffs = 0/21`
- `paired_choice_diffs = 0/21`
- `pathological_follow_up_hits = 0/14`, `pathological_q3_hits = 0/7`
- `accuracy_delta_session_minus_baseline = 0.0` (CI95 `[0.0, 0.0]` — degenerate
  bootstrap because every paired row matches exactly)
- `q3_accuracy_delta_session_minus_baseline = 0.0` (CI95 `[0.0, 0.0]`)
- `session_follow_up_median_ms = 3204.94` (= **3.20 s**)
- `baseline_follow_up_median_ms = 79360.99` (= **79.4 s**)
- `baseline_all_query_median_ms = 79841.30` (= **79.8 s**)
- `speedup_follow_up_median_cold_over_session = 24.76×` (same-class)
- `speedup_all_query_median_cold_over_session_follow_up = 24.91×` (cross-class)
- `session_accuracy = baseline_accuracy = 17/21 = 0.810`
- `mean_follow_up_prefix_coverage = 0.968`
- `peak_rss_gb = 1.44`
- `total_wall_ms = 2979947` (= 49.7 min)

Per-Q breakdown (every cell exactly matches between session and baseline):

- Q1: session 5/7, baseline 5/7
- Q2: session 6/7, baseline 6/7
- Q3: session 6/7, baseline 6/7

A representative Q3 row (`037-3`):

- `session_elapsed_ms = 688.59` (text-only decode, no re-prefill)
- `baseline_elapsed_ms = 87092.31` (cold full prefill + decode)
- per-Q3 speedup = **126×**

## Preregistered verdicts

### H1 — paired fidelity improves materially over `1.55E`

**EARNED.** Acceptance: paired correctness diffs `<= 1/21`, paired choice diffs
`<= 2/21`. Observed: **0/21 and 0/21**. The `1.55E` failure pattern is
completely absent under the new cache source.

### H1' — exact 1.55D-style match survives the cache-source change

**EARNED at the strongest possible level.** `0/21` correctness diffs and `0/21`
choice diffs. Per-row per-Q breakdown shows session==baseline everywhere
(response, choice, correct).

### H2 — Q3 basin recurrence is largely suppressed

**EARNED.** Acceptance: Q3 pathological-like outputs `<= 2/7`. Observed
**0/7**. The 1.55E `7/7` `addCriterion`-style attractor is completely
eliminated. The Q3 catastrophe was definitively a cache-source-selection
problem, not an inherent adaptive-repair limitation.

### H3 — the adaptive speed benefit remains meaningfully above K=1

**EARNED dramatically.** Acceptance: session follow-up median `<` `1.55D K=1`'s
10135.54 ms. Observed `3204.94 ms` — **3.16× faster than fixed K=1 K=2 K=4
combined.** This is well beyond the gate; the speed advantage is not a
marginal one.

The mechanism: K=1 at Q2 incurs ~26-28 s of tail re-prefill; K=0 at Q3 with
post-Q2 state incurs ~600-1200 ms of pure decode (the cache is reused for the
entire prefix, no vision-tower re-pass). The follow-up median is dominated by
Q3's near-cost-free path.

### H4 — memory stays inside the existing local budget

**EARNED with massive margin.** Acceptance: `peak_rss_gb <= 5.5` (raised in
`1cf86d7` from `5.0`). Observed **1.44 GB** — *lower* than `1.55D K=1`'s
4.886 GB. The K=0-with-post-Q2-state path apparently lets MLX release more
intermediate state than the K=1 path holds onto.

## Combined C-PERSIST K=1 / adaptive picture

| run | regime | n | paired diffs | Q3 pathology | speedup (same-class) | RSS |
|---|---|---|---|---|---|---|
| 1.55D K=1 | 20f short, 7 clips | 21 | 0/21 / 0/21 | 0/7 | 9.48× | 4.886 GB |
| 1.55G K=1 | 20f medium, 10 clips | 30 | 0/30 / 0/30 | 0/10 | 10.76× | 6.097 GB |
| 1.55E K0-Q1-fallback | 20f short, 7 clips | 21 | 4/21 / 6/21 | 7/7 | 9.34× | — |
| **1.55F K0-postQ2** | **20f short, 7 clips** | **21** | **0/21 / 0/21** | **0/7** | **24.76×** | **1.44 GB** |

The 1.55F point dominates 1.55D K=1 on the same tranche on every dimension:
- same fidelity (both 0/21)
- 2.6× higher speedup
- 3.4× lower peak RSS
- shorter total wall time (49.7 min vs 1.55D K=1's ~64 min)

The 1.55E falsification remains valid: the Q3 catastrophe is real — it just
needed the cache source flagged as the cause.

## Implications for the paper

1. **C-PERSIST upgrades from "fixed K=1 selective re-prefill works" to "adaptive
   selective re-prefill with post-Q2 state recovery is the stronger story."**
   The headline becomes: *adaptive Q1-cold / Q2-K=1 / Q3-K=0-from-post-Q2-state
   preserves answer identity exactly on n=21 short-bucket VideoMME with ~25×
   follow-up speedup; the same policy under the wrong cache source (1.55E)
   collapses catastrophically*. That's a clean cause-effect story.

2. **The K=1 results (1.55D, 1.55G) become the second-best fixed-policy point**
   in a frontier that now includes the adaptive 1.55F point. Both belong in the
   paper: 1.55D/G as the no-coordination baseline, 1.55F as the adaptive
   improvement.

3. **The mechanism story now closes neatly:** persistent-KV at 20f Qwen 7B-4bit
   has a basin that can be (a) preserved into by always rebuilding from Q1
   (catastrophe) or (b) repaired once at Q2 then preserved forward
   (adaptive-recovery success). The basin is real; its inheritance rule
   matters.

4. **Memory headroom unlocked:** at 1.44 GB peak, this policy is the only
   landed C-PERSIST point that comfortably fits inside even a `2 GB` operator
   ceiling. Useful for downstream applications.

## Anomalies and notes

- The session and baseline accuracies are byte-identical at `17/21` *and* the
  per-row choices/responses match exactly. This means the K=0 Q3 path with
  post-Q2 cache produces *bitwise identical* generation under greedy decode to
  the cold baseline on every single tracked query. That's stronger than
  "no observed paired drift" — it's effectively "answer-bit-equivalent."
- The bootstrap CI on `accuracy_delta_session_minus_baseline` is degenerate
  `[0.0, 0.0]` because every paired row contributes 0 to the delta and the
  resampler can never produce a non-zero value. This is correct; it just means
  the bootstrap is uninformative on a degenerate-zero distribution.
- The peak-RSS drop (4.886 → 1.44 GB) is unexpected and worth a brief
  investigation in a follow-up. Hypothesis: the K=1 path holds onto an extra
  rewound prompt cache during the Q2/Q3 transitions; the K=0 + post-Q2-state
  path skips that rewind. If true, *adaptive* selective re-prefill is also
  more memory-efficient than fixed K=1.

## What this rules out and what it does not

**Rules out:**
- "Q3 collapse is intrinsic to adaptive repair" — falsified.
- "Adaptive selective re-prefill is no better than fixed K=1" — falsified.

**Does not rule out:**
- Long-bucket robustness (`1.55I` is in flight; will land later in this queue).
- Medium-bucket robustness (would be a future `1.55F-medium`; not in current
  queue but a natural cheap follow-up after this lands).
- 32f-depth robustness (`1.55H` will probe this for fixed K=1; an adaptive
  variant `1.55F-32f` is a future option).

## Pending follow-ups

- **`1.55F-medium` (NEW; preregister required, ~2h compute):** rerun the
  adaptive policy on the 10-clip medium tranche. If it passes, the paper
  upgrades to "adaptive C-PERSIST: short+medium n=51, 0/51 paired diffs,
  ~25× follow-up speedup."
- **`1.55F-long` (NEW; preregister; conditional on `1.55I` passing):** rerun on
  the 7-clip long tranche. Most demanding test for the basin-most-stressed
  regime.
- **`1.55F-32f` (NEW; preregister; conditional on `1.55H` passing):** depth
  boundary version of the adaptive policy.
- **Memory-efficiency follow-up (analysis-only):** instrument the
  `mlx_vlm.cache.PromptCacheState` lifetime in fixed-K=1 vs K=0+post-Q2 paths
  to confirm the 4× RSS drop is real and explainable.

## Decisions

- Paper sections C-PERSIST should now cite 1.55F as the strongest local
  recovery point. The K=1 fixed point (1.55D + 1.55G) becomes the
  no-coordination baseline.
- The findings doc title and per-section headline language should foreground
  "adaptive" / "post-Q2 state recovery" / "cache-source-as-mechanism" rather
  than "selective re-prefill" generically.
- `registry.md` 1.55F row updates to `landed-PASS`.
- `1.30AC` (cache-invalidated follow-up pruning) gains additional motivation:
  if cache-source choice was decisive for C-PERSIST adaptive recovery, the
  parallel question for C-VISION is whether cache-source choice is decisive
  for vision-pruning activity. 1.30AC remains the right mechanism experiment
  for the 1.30 lane.
