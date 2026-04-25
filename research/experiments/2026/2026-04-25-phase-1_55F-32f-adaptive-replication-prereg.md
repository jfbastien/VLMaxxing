---
phase: 1.55F-32f
date: 2026-04-25
parent:
  - research/experiments/2026/2026-04-25-phase-1_55F-q3-post-q2-state-findings.md
  - research/experiments/2026/2026-04-25-phase-1_55H-k1-32f-short-probe-findings.md
status: preregistered 2026-04-25. 32f short-bucket adaptive replication after 1.55H confirmed depth boundary holds.
---

# 1.55F-32f — Adaptive Q3 post-Q2 state on the 32f short-bucket depth boundary

## Why this prereg exists

`1.55F` (20f short adaptive) dominated `1.55D K=1` on every dimension
(0/21 paired diffs, 24.91× speedup, 1.44 GB peak). `1.55H` (32f short
fixed K=1) just landed clean: 0/21, 20.37× speedup, 5.82 GB peak.

The natural depth × policy intersection is **32f short with the
adaptive policy**. Expected speedup from prefill-dominance scaling:
20.37× × (24.91/9.71) ≈ **52×**. If this lands at even 30-40×, it would
be the strongest single-cell efficiency result in the paper.

## Protocol

- Model: `Qwen2.5-VL-7B-Instruct-4bit`
- Regime: **32-frame** persistent-KV short-bucket VideoMME session
- Clips: `037,100,116,120,158,160,210` (same 7-clip tranche as 1.55D
  short, 1.55F short, 1.55H 32f short — exact paired comparison
  against the fixed-K=1 32f point)
- Queries: 3 per clip, session path vs matched cold baseline
- Session policy:
  - `Q1`: cold (`K=0`)
  - `Q2`: `K=1` selective re-prefill
  - `Q3`: `K=0` with `q3_cache_source=post_q2_repaired`
- Runner: `scripts/run_kv_selective_reprefill_v2.py`
- Wrapper: `scripts/run_phase1_55F_32f_short_adaptive_replication.sh`
  (to be authored — copy `run_phase1_55F_q3_post_q2_state.sh` and
  substitute `--frame-count 32` plus output dir)

Estimated runtime:

- session per clip: ~2.5 min (Q1 ~135s + Q2 ~9s + Q3 <1s, similar to
  1.55F short scaling pattern)
- baseline per clip: ~6.7 min (3 × ~135s 32f cold queries)
- 7 clips × ~9 min = `~65 min` session+baseline
- paired analysis: `<1 min`
- **total: ~65-90 min** (slower than 1.55F at 20f because baseline
  prefills are ~135s vs ~80s)

## Hypotheses

### H1 — 32f adaptive fidelity remains tightly bounded

Acceptance:

- paired correctness diffs `<= 2/21`
- paired choice diffs `<= 3/21`

Failure:

- paired correctness diffs `>= 4/21`, or
- paired choice diffs `>= 5/21`

### H1' — exact 1.55F-style match survives the 32f depth boundary

Acceptance:

- paired correctness diffs `= 0/21`
- paired choice diffs `= 0/21`

If H1' passes, the adaptive C-PERSIST claim closes the depth-boundary
question with the same `0/n` pattern that has held across all four
prior C-PERSIST K=1 cells.

### H2 — Q3 basin recurrence remains absent at 32f depth

Acceptance:

- pathological-like Q3 outputs `<= 1/7`
- pathological-like follow-up outputs `<= 2/14`

The 32f depth was the most-feared basin trigger; 1.55H showed it doesn't
fire under K=1. This gate verifies the same for adaptive.

### H3 — adaptive speedup remains meaningfully above fixed K=1 32f

Acceptance:

- `speedup_all_query_median_cold_over_session_follow_up >= 30.0×`

Failure:

- `< 22.0×` (i.e. not meaningfully above 1.55H's 19.90×)

Reference: 1.55H K=1 32f short measured 19.90× cross-class. Adaptive
should push past this. The 1.55F (20f) / 1.55D (20f) ratio was 2.57×;
applied to 1.55H's 19.90× gives an expected ~51×, but H3 at 30× is a
safer floor that admits some scaling deviation.

### H4 — memory remains within the local single-run envelope

Acceptance:

- `peak_rss_gb <= 6.0`

Failure:

- `peak_rss_gb > 6.0`

`1.55F` (20f) measured 1.44 GB; `1.55H` (32f K=1) measured 5.82 GB. The
adaptive variant should sit between those; 6.0 GB ceiling matches 1.55H's
landed value with margin.

### H5 — 32f short tranche stays above the signal floor

Acceptance:

- baseline accuracy `>= 0.40`

`1.55H` measured 0.857; trivially passes. Including for completeness.

## Decision rules

- If H1/H2/H3/H4/H5 pass, the adaptive C-PERSIST policy is confirmed
  across **20f short × medium × long PLUS 32f short**. Combined with
  pending 1.55F-medium and 1.55F-long, this would close the adaptive
  scope claim at n=93+ paired with 0 observed drift.
- If H1' passes, the paper headline tightens dramatically: "adaptive
  C-PERSIST: 0/n paired drift at ~30-50× follow-up speedup across four
  regimes" becomes the new headline.
- If H1 fails but H2/H3 pass, the 32f depth admits some adaptive drift
  but the speedup story holds; scope the adaptive claim accordingly.
- If H2 fails, the post-Q2 state strategy is sensitive to depth
  specifically; this would be a clean mechanism finding (basin
  inheritance is depth-modulated, not just regime-modulated).
- If H3 fails (i.e., adaptive isn't materially faster than fixed K=1 at
  32f), the per-Q3 K=0 path's relative advantage shrinks at higher
  prefill cost — also publishable as a frontier characterization.

## Interpretation rules

- Direct comparison against `1.55H K=1` (same tranche, fixed `K=1`,
  32f) in the paper table.
- Cross-depth comparison against `1.55F` (20f short adaptive) for
  prefill-dominance scaling.
- Use the new paired-bootstrap-CI analyzer for fidelity claims.

## Curation note

The 7-clip tranche is identical to all four prior C-PERSIST short-bucket
runs. Each video has ≥3 questions in the parquet (verified for 1.55D /
1.55F / 1.55H).

## Execution

Pending. Wrapper authoring is ~5 minutes (one-line edits from
`run_phase1_55F_q3_post_q2_state.sh`: change `--frame-count 20` to
`--frame-count 32` and update the output dir). Tranche curation is
none. Estimated total session: ~70-90 min compute + ~5 min setup.

Doc-only this round; not auto-runnable from the current AFK queue
without explicit approval.

## Result

Pending.

## Interpretation

Pending.
