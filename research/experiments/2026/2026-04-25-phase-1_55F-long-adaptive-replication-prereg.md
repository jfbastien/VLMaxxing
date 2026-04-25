---
phase: 1.55F-long
date: 2026-04-25
parent:
  - research/experiments/2026/2026-04-25-phase-1_55F-q3-post-q2-state-findings.md
  - research/experiments/2026/2026-04-25-phase-1_55I-k1-long-replication-findings.md
status: preregistered 2026-04-25. Long-bucket replication of the landed 1.55F adaptive policy after 1.55I confirmed long-bucket K=1 works.
---

# 1.55F-long — Adaptive Q3 post-Q2 state on the long bucket

## Why this prereg exists

`1.55F` (short-bucket adaptive) dominates `1.55D K=1` on the same
short-bucket tranche on every dimension: 0/21 paired diffs, 24.91×
same-class follow-up speedup (vs 9.71× cross-class for K=1), 1.44 GB
peak RSS (vs 4.886 GB for K=1).

`1.55I` (long-bucket fixed K=1) just landed clean: 0/21 paired diffs,
11.24× speedup, 0 pathological. So the long bucket is well-behaved
under fixed K=1, which is the necessary precondition for the adaptive
policy to make sense there.

The natural extension: apply the adaptive Q1-cold / Q2-K=1 / Q3-K=0-
from-post-Q2-state policy to the same 7-clip long-bucket tranche
1.55I used. If it passes, the adaptive C-PERSIST claim becomes
three-regime as well.

## Protocol

- Model: `Qwen2.5-VL-7B-Instruct-4bit`
- Regime: 20-frame persistent-KV long-bucket VideoMME session
- Clips: `669,711,712,737,756,758,794` (same 7-clip tranche as `1.55I`,
  for exact paired comparison against the fixed-`K=1` long-bucket point)
- Queries: 3 per clip, session path vs matched cold baseline
- Session policy:
  - `Q1`: cold (`K=0`)
  - `Q2`: `K=1` selective re-prefill
  - `Q3`: `K=0` with `q3_cache_source=post_q2_repaired`
- Runner: `scripts/run_kv_selective_reprefill_v2.py`
- Wrapper: `scripts/run_phase1_55F_long_adaptive_replication.sh` (to be
  authored — copy `run_phase1_55F_q3_post_q2_state.sh` and substitute
  the long-bucket video IDs and output dir)

Estimated runtime:

- session per clip: ~3 min (Q1 ~70s + Q2 ~15s + Q3 <1s, similar to 1.55F
  short)
- baseline per clip: ~4 min (3 × ~80s long-bucket cold)
- 7 clips × ~7 min = `~50 min` session+baseline
- paired analysis: `<1 min`
- **total: ~50-65 min** (slightly faster than `1.55I` because Q3 is
  near-free under K=0+post_q2)

## Hypotheses

### H1 — long-bucket adaptive fidelity remains tightly bounded

Acceptance:

- paired correctness diffs `<= 2/21`
- paired choice diffs `<= 3/21`

Failure:

- paired correctness diffs `>= 4/21`, or
- paired choice diffs `>= 5/21`

### H1' — exact 1.55F-style match survives the long-bucket extension

Acceptance:

- paired correctness diffs `= 0/21`
- paired choice diffs `= 0/21`

If H1' passes, the adaptive C-PERSIST picture becomes:

- 1.55F (short, n=21): 0/21
- 1.55F-medium (medium, n=30, pending): 0/30
- 1.55F-long (long, n=21): 0/21
- **combined: n=72 paired with 0 observed drift, ~20-25× follow-up speedup**

That is the strongest C-PERSIST claim the paper can support.

### H2 — Q3 basin recurrence remains absent on long

Acceptance:

- pathological-like Q3 outputs `<= 1/7`
- pathological-like follow-up outputs `<= 2/14`

Failure:

- pathological-like Q3 outputs `>= 3/7`, or
- pathological-like follow-up outputs `>= 4/14`

If `1.55F`'s `0/7` Q3 pathology was a short-bucket coincidence and the
long-bucket basin is closer to the persistent-KV cliff, this is where
it surfaces.

### H3 — adaptive speedup remains meaningfully above fixed K=1 long-bucket

Acceptance:

- `speedup_all_query_median_cold_over_session_follow_up >= 16.0×`

Failure:

- `< 12.0×`

Reference: `1.55I K=1` long-bucket landed `11.24×`. The adaptive policy
should clearly exceed this; expected ~18-22× given that `1.55F` short
hit 24.91× vs `1.55D K=1` short's 9.71× (`2.6×` ratio).

### H4 — memory remains within the local operating envelope

Acceptance:

- `peak_rss_gb <= 5.0`

Failure:

- `peak_rss_gb > 5.0`

`1.55F` short measured 1.44 GB; `1.55I` long fixed-K=1 measured 5.94 GB.
The long-bucket adaptive should sit between those; 5.0 GB ceiling gives
margin.

### H5 — long tranche stays above the signal floor

Acceptance:

- baseline accuracy `>= 0.30`

`1.55I` measured 0.333; baseline accuracy at this regime is the lowest
in the C-PERSIST series, but still informative.

## Decision rules

- If H1/H2/H3/H4/H5 pass, the adaptive C-PERSIST policy is confirmed
  three-regime. Combined with H1' from `1.55F` (already earned) and a
  pending pass for `1.55F-medium`, this would close the adaptive
  scope claim at n=72 paired across all three duration regimes.
- If H1' passes, the paper headline tightens to
  "adaptive C-PERSIST: 0/72 paired drift on n=72 short+medium+long
  VideoMME at 20f, ~20-25× follow-up speedup."
- If H1 fails but H2 passes, the adaptive policy is regime-bounded;
  scope the headline to short+medium and quote 1.55F-long as a long-
  bucket boundary result.
- If H2 fails, the adaptive policy is *not* basin-tolerant on long;
  this would be a surprising and publishable mechanism finding —
  long-bucket basin is more dangerous than the short-bucket basin.

## Interpretation rules

- Direct comparison against `1.55I K=1` (same tranche, fixed `K=1`)
  in the paper table.
- Cross-regime comparison against `1.55F` (short adaptive) and
  `1.55F-medium` (medium adaptive, when it lands) for prefill-
  dominance scaling consistency.
- Use the new paired-bootstrap-CI analyzer for fidelity claims.

## Curation note

The long tranche is identical to `1.55I`'s. Each video has ≥3 questions
in the parquet (already verified for `1.55I`).

## Execution

Pending. Wrapper authoring is ~5 minutes. Tranche curation is none.
Estimated total session: ~55 min compute + ~5 min setup.

Doc-only this round; not auto-runnable from the current AFK queue
without explicit approval.

## Result

Pending.

## Interpretation

Pending.
