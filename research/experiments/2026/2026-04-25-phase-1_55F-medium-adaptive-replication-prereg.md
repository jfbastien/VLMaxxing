---
phase: 1.55F-medium
date: 2026-04-25
parent:
  - research/experiments/2026/2026-04-25-phase-1_55F-q3-post-q2-state-findings.md
  - research/experiments/2026/2026-04-25-phase-1_55G-k1-medium-replication-findings.md
status: preregistered 2026-04-25. Medium-bucket replication of the landed 1.55F adaptive policy.
---

# 1.55F-medium — Adaptive Q3 post-Q2 state on the medium bucket

## Why this prereg exists

`1.55F` landed the strongest C-PERSIST recovery point: with `Q1` cold,
`Q2` `K=1`, `Q3` `K=0` from the post-Q2 repaired state, n=21 paired
short-bucket queries returned 0/21 paired diffs, 0/7 Q3 pathology, and
24.91× same-class follow-up speedup at 1.44 GB peak RSS. That dominates
fixed `K=1` (1.55D) on every dimension.

`1.55G` showed fixed `K=1` survives the medium bucket cleanly (n=30,
0/30 paired diffs, 10.76× speedup). That gives us the prior expectation
that the same regime will not push the model into fresh basin behavior.

The remaining unanswered question is whether the *adaptive* policy
(post-Q2 state for Q3) generalizes from short to medium. The cheapest
direct test is a fixed-tranche replication.

## Protocol

- Model: `Qwen2.5-VL-7B-Instruct-4bit`
- Regime: 20-frame persistent-KV medium-bucket VideoMME session
- Clips: `320,354,364,380,407,408,426,484,486,531`
  (same tranche as `1.55G` so paired comparison against the fixed-`K=1`
  point is exact)
- Queries: 3 per clip, session path vs matched cold baseline
- Session policy:
  - `Q1`: cold (`K=0`)
  - `Q2`: `K=1` selective re-prefill
  - `Q3`: `K=0` with `q3_cache_source=post_q2_repaired`
- Runner: `scripts/run_kv_selective_reprefill_v2.py`
- Wrapper: `scripts/run_phase1_55F_medium_adaptive_replication.sh` (to
  be authored — copy `run_phase1_55F_q3_post_q2_state.sh` and substitute
  the medium-bucket video IDs and output dir)

Estimated runtime:

- session + baseline per clip: similar pacing to `1.55G K=1` (~6-7 min
  per clip on the 8100-token-prefill medium tranche; the K=0 Q3 path is
  the cheap leg, not the dominant cost)
- 10 clips × ~6-7 min = `~60-75 min` session+baseline
- prefill is the dominant cost
- paired analysis: `<1 min`
- **total: ~60-75 min**

## Hypotheses

### H1 — medium-bucket fidelity stays at or near `1.55F`'s short-bucket result

Acceptance:

- paired correctness diffs `<= 2/30`
- paired choice diffs `<= 3/30`

Failure:

- paired correctness diffs `>= 5/30`, or
- paired choice diffs `>= 6/30`

This is the same gate as `1.55G H1` (the fixed-`K=1` medium test) — we
hold the adaptive policy to the same fidelity bar that fixed-`K=1`
already cleared on this same tranche.

### H1' — exact 1.55F-style match survives the medium-bucket extension

Acceptance:

- paired correctness diffs `= 0/30`
- paired choice diffs `= 0/30`

This is the stronger sub-gate. If H1' passes, the combined adaptive-policy
picture becomes **n=51 paired short+medium queries with 0 observed
drift** — matching the rule-of-three upper bound on the diff rate at
≈ 5.7%. Combined with the ~25× speedup, this is paper-headline material.

### H2 — Q3 basin recurrence remains absent on medium

Acceptance:

- pathological-like Q3 outputs `<= 1/10`
- pathological-like follow-up outputs `<= 2/20`

Failure:

- pathological-like Q3 outputs `>= 3/10`, or
- pathological-like follow-up outputs `>= 4/20`

If `1.55F`'s `0/7` Q3 pathology was a short-bucket coincidence, this
is where it would surface.

### H3 — adaptive speedup remains meaningfully above fixed `K=1`

Acceptance:

- `speedup_all_query_median_cold_over_session_follow_up >= 15.0×`

Failure:

- `< 12.0×`

The fixed-`K=1` medium-bucket result was 10.85×; we want clear evidence
that adaptive is materially faster than fixed on the same tranche, not
just within-noise comparable. Expected: the K=0 Q3 path saves ~6-15 s
per Q3 (no tail re-prefill), which on a 2-Q-follow-up median should
push the speedup well past the 1.55G fixed-`K=1` line.

### H4 — memory remains within the local operating envelope

Acceptance:

- `peak_rss_gb <= 5.0`

Failure:

- `peak_rss_gb > 5.0`

`1.55F` short measured `1.44 GB`; `1.55G` fixed-`K=1` medium measured
`6.10 GB`. The K=0 Q3 path is expected to keep less state alive than
fixed K=1, so the true number is likely between 1.5 and 4 GB on
medium. The 5.0 GB ceiling gives margin.

### H5 — the medium tranche stays above the signal floor

Acceptance:

- baseline accuracy `>= 0.40`

Reuses the `1.55G` floor; we already know this tranche cleared 0.533.

## Decision rules

- If H1/H2/H3/H4/H5 pass, the adaptive C-PERSIST policy upgrades from
  short-only to **short+medium**.
- If H1' passes, the combined claim becomes "n=51 paired adaptive runs
  with 0 observed drift and ~20–25× follow-up speedup."
- If H1 fails but H2 passes, the adaptive recovery is regime-bounded
  (short-only); the paper should scope the claim accordingly.
- If H2 fails, the post-Q2 state strategy does not generalize; revert
  to fixed `K=1` for medium and explicitly scope the adaptive claim.

## Interpretation rules

- Paper-facing claim: keep "no observed paired drift" wording with the
  appropriate rule-of-three upper bound.
- Direct comparison against `1.55G` (same tranche, fixed `K=1`) in the
  paper table; both points belong because `1.55G` is the no-coordination
  baseline and `1.55F-medium` is the adaptive improvement.
- Use the new paired-bootstrap-CI analyzer for fidelity claims.

## Curation note

The medium tranche is identical to `1.55G`'s. Each video has ≥3
questions in the parquet (already verified for `1.55G`).

## Execution

Pending. Wrapper authoring is ~5 minutes (one-line edits from the
short-bucket wrapper). Tranche curation is none (reuses 1.55G's).
Estimated total session: ~70 min compute + ~5 min setup.

## Result

Pending.

## Interpretation

Pending.
