---
phase: 1.55G
date: 2026-04-25
parent: research/experiments/2026/2026-04-24-phase-1_55D-selective-reprefill-v2-k1-findings.md
status: preregistered 2026-04-25. Medium-bucket replication of the 1.55D K=1 point.
---

# 1.55G — K=1 medium-bucket replication

## Why this prereg exists

`1.55D K=1` is currently the strongest local recovery point, but it is still
short-bucket-only. The paper needs to know whether the observed no-drift slice
is narrowly local or whether it survives at least one broader regime.

The cheapest direct test is a medium-bucket replication on a fixed tranche.

## Protocol

- Model: `Qwen2.5-VL-7B-Instruct-4bit`
- Regime: 20-frame persistent-KV medium-bucket VideoMME session
- Clips:
  `320,354,364,380,407,408,426,484,486,531`
- Queries: 3 per clip, session path vs matched cold baseline
- Session policy:
  - `Q1`: cold
  - `Q2/Q3`: selective re-prefill with `K=1`
- Runner:
  `scripts/run_kv_selective_reprefill_v2.py`
- Wrapper:
  `scripts/run_phase1_55G_k1_medium_replication.sh`

Estimated runtime:

- session + baseline: `~100–130 min`
- paired analysis: `<1 min`
- total: `~1.7–2.2 h`

## Hypotheses

### H1 — medium-bucket fidelity remains tightly bounded

Acceptance:

- paired correctness diffs `<= 2/30`
- paired choice diffs `<= 3/30`

Failure:

- paired correctness diffs `>= 5/30`, or
- paired choice diffs `>= 6/30`

### H2 — pathological follow-up attractors remain rare

Acceptance:

- pathological-like follow-up outputs `<= 2/20`

Failure:

- pathological-like follow-up outputs `>= 5/20`

### H3 — K=1 still buys a large local speedup

Acceptance:

- `speedup_all_query_median_cold_over_session_follow_up >= 8.0×`

Failure:

- `< 6.0×`

### H4 — memory stays within the local operating envelope

Acceptance:

- `peak_rss_gb <= 5.5`

Failure:

- `peak_rss_gb > 5.5`

The RSS threshold is slightly looser than the short-bucket tranche because the
medium clips are longer and more heterogeneous.

### H5 — the medium tranche is above the signal floor

Acceptance:

- baseline accuracy `>= 0.40`

Failure:

- baseline accuracy `< 0.40`

This guards against a vacuous "preserved" result on a slice that is too weak to
say much about fidelity preservation.

## Decision rules

- If H1/H2/H3/H4/H5 pass, `1.55D K=1` upgrades from a short-only strong point to a
  multi-regime recovery result.
- If H5 fails, treat the run as a low-signal scope probe rather than as
  evidence for preservation.
- If H1 fails but H2/H3 pass, the result is still useful: recovery is real but
  regime-bounded, and the paper should scope the claim to short/medium rather
  than speak generically.
- If H2 fails, the short-bucket result is likely regime-specific and the paper
  should not generalize K=1 beyond the observed tranche.

## Interpretation rules

- This is a scope test, not a mechanism discovery run.
- Use the new paired metrics JSON to report all fidelity claims.
- If the medium result is materially weaker, do not merge it rhetorically into
  the short-bucket point; report it as a boundary.

## Execution

Pending.

## Result

Pending.

## Interpretation

Pending.
