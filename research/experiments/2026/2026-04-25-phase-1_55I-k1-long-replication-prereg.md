---
phase: 1.55I
date: 2026-04-25
parent: research/experiments/2026/2026-04-25-phase-1_55G-k1-medium-replication-findings.md
status: preregistered 2026-04-25. Long-bucket K=1 replication at 20f after 1.55G earned the multi-regime upgrade.
---

# 1.55I — K=1 long-bucket replication

## Why this prereg exists

`1.55D K=1` (n=21 short) and `1.55G K=1` (n=30 medium) both landed
zero observed paired drift with ~9.5–10.8× follow-up speedup. With
short + medium combined at n=51 paired queries / 0/51 diffs / 0/34
pathological follow-up responses / 0/17 pathological Q3 responses, the natural next scope question is whether the
landed K=1 fixed-tail policy survives on the long bucket where
persistent-KV is most stressed.

`1.55I` is the long-bucket counterpart of `1.55G`. Its scientific
purpose is to determine whether the C-PERSIST K=1 recovery story is
two-regime (short+medium) or full three-regime (short+medium+long).

## Protocol

- Model: `Qwen2.5-VL-7B-Instruct-4bit`
- Regime: 20-frame persistent-KV long-bucket VideoMME session
- Clips: `669,711,712,737,756,758,794`
  - chosen from the existing `videomme_long_dev_holdout_v1.toml` pool
  - each passes the `≥3 questions in the parquet` requirement enforced by
    `_questions_for_video_id`
- Queries: 3 per clip, session path vs matched cold baseline
- Session policy:
  - `Q1`: cold (`K=0`)
  - `Q2/Q3`: selective re-prefill with `K=1`
- Runner: `scripts/run_kv_selective_reprefill_v2.py`
- Wrapper: `scripts/run_phase1_55I_k1_long_replication.sh`

Estimated runtime:

- session + baseline per clip: ~6-9 min (long clips have larger
  prefills than medium)
- 7 clips × ~7-9 min = `~50-65 min` session+baseline
- prefill is the dominant cost; expected `total_wall_ms` `~3500-4500 s`
  (compare 1.55G at 20f-medium total 4730 s on 10 clips)
- paired analysis: `<1 min`
- **total: ~60-75 min** (faster than 1.55G because of fewer clips,
  partly offset by larger long-bucket prefills)

## Hypotheses

### H1 — long-bucket fidelity remains tightly bounded

Acceptance:

- paired correctness diffs `<= 2/21`
- paired choice diffs `<= 3/21`

Failure:

- paired correctness diffs `>= 4/21`, or
- paired choice diffs `>= 5/21`

This is intentionally tighter than 1.55G's gate because n=21 is half
the size; we want to detect drift that would have been hidden at small n.

### H1' — exact match still survives on the long bucket

Acceptance:

- paired correctness diffs `= 0/21`
- paired choice diffs `= 0/21`

This is the stronger sub-gate. If H1' passes, the combined picture
becomes **n=72 paired short+medium+long with 0 observed drift** — a
genuinely multi-regime no-observed-drift result.

### H2 — pathological follow-up attractors remain rare

Acceptance:

- pathological-like follow-up outputs `<= 2/14`
- pathological-like Q3 outputs `<= 1/7`

Failure:

- pathological-like follow-up outputs `>= 4/14`, or
- pathological-like Q3 outputs `>= 3/7`

The long bucket is the regime closest to the persistent-KV basin onset,
so basin-style failures are the most likely failure mode here.

### H3 — K=1 still preserves a meaningful local speedup

Acceptance:

- `speedup_all_query_median_cold_over_session_follow_up >= 6.0×`

Failure:

- `< 4.0×`

This is intentionally looser than 1.55G's `≥8.0×` gate because long
clips have proportionally larger Q1 prefill cost, which compresses the
amortized speedup ratio. The paper-actionable threshold is "still
materially faster than cold," not parity with the medium-bucket point.

### H4 — memory remains within the local operating envelope

Acceptance:

- `peak_rss_gb <= 7.5`

Failure:

- `peak_rss_gb > 7.5`

The 1.55G H4 ceiling at 5.5 GB was retroactively too tight (actual:
6.10 GB). The long-bucket prefill is larger again; raising the gate to
7.5 GB gives a realistic budget while staying inside the 9 GB safe-RSS
guard.

### H5 — the long tranche is above the signal floor

Acceptance:

- baseline accuracy `>= 0.30`

Failure:

- baseline accuracy `< 0.30`

The signal floor is intentionally lower than 1.55G's 0.40 because long-
bucket VideoMME accuracy on Qwen 7B-4bit is known to be weaker (1.30Z
landed cold accuracy 0.481 across all-bucket queries; long-only is
expected to be lower). A 0.30 floor still rules out vacuous slices.

## Decision rules

- If H1/H2/H3/H4/H5 pass, C-PERSIST K=1 upgrades from two-regime
  (short+medium) to three-regime (short+medium+long). The combined
  paper claim becomes n=72 paired queries with 0/72 (or near-zero)
  drift and ~7-10× follow-up speedup.
- If H1' passes, the multi-regime result tightens to "0 observed drift
  on n=72 short+medium+long," matching the rule-of-three upper bound on
  the diff rate at ≈ 4.1%.
- If H1 fails but H2 passes, the result is "K=1 saves time but introduces
  some drift on long-bucket"; the paper should scope the recovery claim
  explicitly to short+medium.
- If H2 fails, the long bucket is materially closer to the persistent-KV
  basin and the paper should not generalize K=1 to long-bucket
  deployment without an explicit risk-gating mechanism.
- If H5 fails, treat as a low-signal probe rather than a fidelity claim.

## Interpretation rules

- Compare against both 1.55D K=1 short and 1.55G K=1 medium directly.
- Use the new paired-metrics analyzer for all fidelity claims (the same
  one used by 1.55D/G).
- The paper-facing claim should remain "no observed paired drift" with
  the appropriate rule-of-three upper bound on the combined diff rate
  unless n materially increases beyond ~50.

## Curation note

The long tranche is now fixed to `669,711,712,737,756,758,794`. This keeps the
run inside the existing `1.30Z` long-manifest pool while avoiding an extra
on-the-fly curation step during the autonomous queue.

## Execution

Pending. Wrapper authored and tranche fixed; ready to queue.

## Result

Pending.

## Interpretation

Pending.
