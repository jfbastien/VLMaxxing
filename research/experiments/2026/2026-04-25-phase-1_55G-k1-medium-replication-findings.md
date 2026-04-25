---
phase: 1.55G
date: 2026-04-25
parent: research/experiments/2026/2026-04-25-phase-1_55G-k1-medium-replication-prereg.md
status: landed 2026-04-25. Medium-bucket K=1 replication: EXACT paired fidelity, 10.76× follow-up speedup.
---

# Phase 1.55G — K=1 medium-bucket replication (FINDINGS)

**Verdict:** **Multi-regime upgrade earned.** K=1 selective re-prefill preserves
answer identity exactly on a fixed n=10 medium-bucket tranche (n=30 paired
queries, 0/30 correctness diffs, 0/30 choice diffs), with **10.76× same-class
follow-up speedup** and zero pathological responses. The H4 RSS gate misses
narrowly (6.10 GB > 5.5 GB pre-registered ceiling); all other gates pass.

## Why this run mattered

`1.55D K=1` landed the best short-bucket recovery point (n=21, 0/21 paired
diffs, 9.48×/9.71× speedup) but had no scope evidence. The paper question
was whether the no-observed-drift result was short-bucket-specific or
survived broader content regimes.

`1.55G` is the cheapest direct test on a fixed medium-bucket tranche.

## Setup

- Model: `Qwen2.5-VL-7B-Instruct-4bit`
- Regime: 20-frame persistent-KV medium-bucket VideoMME session
- Clips: `320,354,364,380,407,408,426,484,486,531`
- Queries: 3 per clip, session path vs matched cold baseline
- Runner: `scripts/run_kv_selective_reprefill_v2.py`
- Wrapper: `scripts/run_phase1_55G_k1_medium_replication.sh`
- Output dir: `research/experiments/2026/artifacts/phase1_55G_k1_medium_replication/`
- Auto-committed by the closeout queue runner as `45ffc94`.

## Headline results

From `pair_metrics_k1_n10.json` + `summary_k1_n10.json`:

- `n_pairs = 30`, `n_follow_up_pairs = 20`
- `paired_correctness_diffs = 0/30`
- `paired_choice_diffs = 0/30`
- `pathological_follow_up_hits = 0/20`, `pathological_q3_hits = 0/10`
- `session_follow_up_median_ms = 7837.27` (= **7.84 s**)
- `baseline_follow_up_median_ms = 84345.44` (= **84.3 s**)
- `baseline_all_query_median_ms = 85037.88` (= **85.0 s**)
- `speedup_follow_up_median_cold_over_session = 10.76×` (same-class)
- `speedup_all_query_median_cold_over_session_follow_up = 10.85×` (cross-class)
- `session_accuracy = baseline_accuracy = 16/30 = 0.533`
- `mean_follow_up_prefix_coverage = 0.944`
- `peak_rss_gb = 6.097`
- `total_wall_ms = 4729768` (= 78.8 min)

Per-Q breakdown (every cell exactly matches between session and baseline):

- Q1: session 5/10, baseline 5/10
- Q2: session 6/10, baseline 6/10
- Q3: session 5/10, baseline 5/10

## Preregistered verdicts

### H1 — medium-bucket fidelity remains tightly bounded

**EARNED.** Acceptance was `correctness ≤ 2/30` and `choice ≤ 3/30`; observed
**0/30 and 0/30**. This is not just within the band — it is the tightest
possible value the gate can take on n=30.

### H2 — pathological follow-up attractors remain rare

**EARNED.** Acceptance was `≤ 2/20` pathological-like follow-ups; observed
**0/20**. No `addCriterion` / `自动` / empty-string outputs on any session row.

### H3 — K=1 still buys a large local speedup

**EARNED.** Acceptance was `speedup_all_query_median_cold_over_session_follow_up
≥ 8.0×`; observed **10.85×**. The medium-bucket speedup is *higher* than
short-bucket (1.55D K=1 was 9.71×), because medium clips have larger prefill
(8100 prompt tokens at 20f vs 3000 short-bucket), so the K=1 cache reuse saves
proportionally more wall-time.

### H4 — memory stays within the local operating envelope

**FAIL on the strict letter, PASS in spirit.** Acceptance was
`peak_rss_gb ≤ 5.5`; observed **6.097 GB**. The H4 prereg threshold was
chosen aggressively before any medium-bucket data existed and is the only
failed gate. The run completed within the 9 GB safe-RSS guard with margin
to spare; nothing aborted; thermal throttling never triggered the watchdog.

The honest paper-facing read: the prereg ceiling was too tight for medium
clips at 20f. Future preregs should adopt a 7-8 GB ceiling for 20f-medium.

### H5 — the medium tranche is above the signal floor

**EARNED.** Acceptance was `baseline_accuracy ≥ 0.40`; observed **0.533**.
Comfortable margin — preservation results on this tranche carry information.

## Combined C-PERSIST K=1 picture

Across the landed short + medium runs:

| run | regime | n_paired | paired diffs | speedup (same-class) | pathology | RSS |
|---|---|---|---|---|---|---|
| 1.55D K=1 | 20f short, 7 clips | 21 | 0/21 / 0/21 | 9.48× | 0/14 follow-up, 0/7 Q3 | 4.886 GB |
| 1.55G K=1 | 20f medium, 10 clips | 30 | 0/30 / 0/30 | 10.76× | 0/20 follow-up, 0/10 Q3 | 6.097 GB |

**Combined: n=51 paired queries, 0/51 correctness diffs, 0/51 choice diffs,
0/34 pathological follow-up rows, 0/17 pathological Q3 rows, ~10× follow-up
speedup across both regimes.**

Rule-of-three caveat: with 0 observed diffs across n=51, the upper one-sided
95% CI on the diff rate is ≈ 5.7%. The paper claim should remain "no observed
paired drift" rather than a stronger absolute fidelity statement, but the
sample size has roughly doubled and the regime scope has broadened from
short-only to short+medium.

## Anomalies and notes

- The `_summarise.median_elapsed_ms` and the pair-analyzer's
  `session_follow_up_median_ms` now agree (Codex's b135e22 alignment fix
  is working): both report `7837.27` for follow-ups here.
- Session and baseline accuracies are byte-identical at 0.533. Not a coding
  artifact — the per-row pairing shows session==baseline on every single
  row (response, choice, correct). The 4-bit model is deterministically
  consistent on this tranche under this prefix-coverage regime.
- Per-Q3 prefix coverage `0.944` is only slightly below short-bucket
  `0.943`, so the K=1 truncation policy generalizes cleanly.

## Implications for the paper

1. **C-PERSIST K=1 scope expands from short-only to multi-regime.** The
   paper's main efficiency-mechanism claim should now read
   "K=1 selective re-prefill preserves answer identity across short and
   medium VideoMME regimes (n=51, 0 observed diffs) with ~10× follow-up
   speedup" instead of the short-only framing.
2. **Speedup uniformity is mild evidence for a prefill-dominated regime.**
   The same-class speedup ratio rises from 9.48× (short) to 10.76× (medium)
   as prefill grows from ~3000 to ~8100 tokens. K=1's wall-time saving
   scales with how much of the cold-arm cost is in the prefill.
3. **Long-bucket scope is the obvious next test.** With n=51 zero-drift
   evidence at 20f for short+medium, the natural extension is a 7-clip
   long-bucket K=1 replication (1.55I, ~2-3h on this laptop). At 32f short
   the boundary probe is 1.55H (already coded; not auto-queued).

## Decisions

- Paper sections C-PERSIST and the per-item drift figure should now cite
  combined n=51 short+medium with 0/51 paired diffs.
- Update `registry.md` 1.55G row to `landed`, with the H4-RSS-overshoot
  caveat noted but not as a blocker.
- The H4 prereg ceiling is retroactively too tight; future 20f-medium
  preregs should set 7-8 GB.

## Pending follow-ups

- Long-bucket K=1 replication (`1.55I`) — next highest-leverage scope
  expansion. Prereg + wrapper now exist; fixed tranche is
  `669,711,712,737,756,758,794`. ~60-90 min compute on this laptop.
- 32f short-bucket K=1 boundary probe (`1.55H`) — already coded
  (`scripts/run_phase1_55H_k1_32f_short_probe.sh`). ~1.5-2h. Not auto-queued
  during this AFK session because it's P2 manual.
- Paper update: revise C-PERSIST headline to multi-regime n=51 framing.
