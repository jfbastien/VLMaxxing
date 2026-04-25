---
phase: 1.55H
date: 2026-04-25
parent:
  - research/experiments/2026/2026-04-24-phase-1_55D-selective-reprefill-v2-k1-findings.md
  - research/experiments/2026/2026-04-19-phase-1_55A-32f-frame-scaling-findings.md
status: preregistered 2026-04-25. Short-bucket 32f boundary probe for K=1 selective re-prefill.
---

# 1.55H — K=1 short-bucket 32f boundary probe

## Why this prereg exists

`1.55D K=1` earned a strong short-bucket result at `20f`, but the paper still
needs a sharper answer to the obvious reviewer question:

**does the repaired K=1 policy survive after the Qwen 7B persistent-KV lane has
crossed into the known 32f long-context basin region, or is the recovery point
itself only a 20f-local phenomenon?**

`1.55G` broadens by content regime at the same frame depth. `1.55H` broadens by
frame depth on the same short tranche. Together they turn "good-looking point"
into a real operating envelope.

## Protocol

- Model: `Qwen2.5-VL-7B-Instruct-4bit`
- Regime: 32-frame persistent-KV short-bucket VideoMME session
- Clips: `037,100,116,120,158,160,210`
- Queries: 3 per clip, session path vs matched cold baseline
- Session policy:
  - `Q1`: cold
  - `Q2/Q3`: selective re-prefill with `K=1`
- Runner:
  `scripts/run_kv_selective_reprefill_v2.py`
- Wrapper:
  `scripts/run_phase1_55H_k1_32f_short_probe.sh`

Estimated runtime:

- session + baseline: `~90–120 min`
- paired analysis: `<1 min`
- total: `~1.5–2.0 h`

## Hypotheses

### H1 — K=1 remains materially better than the raw 32f persistent-KV path

Acceptance:

- paired correctness diffs `<= 3/21`
- paired choice diffs `<= 4/21`

Failure:

- paired correctness diffs `>= 6/21`, or
- paired choice diffs `>= 7/21`

This is intentionally weaker than the `20f` short-bucket bar. At `32f` the
question is boundary-mapping, not demanding exact equality first.

### H2 — pathological follow-up attractors are not the dominant mode

Acceptance:

- pathological-like follow-up outputs `<= 3/14`

Failure:

- pathological-like follow-up outputs `>= 7/14`

### H3 — K=1 still preserves a large local speedup

Acceptance:

- `speedup_all_query_median_cold_over_session_follow_up >= 8.0×`

Failure:

- `< 6.0×`

### H4 — memory remains within the local single-run envelope

Acceptance:

- `peak_rss_gb <= 6.5`

Failure:

- `peak_rss_gb > 6.5`

## Decision rules

- If H1/H2/H3/H4 pass, selective re-prefill broadens from a 20f-only short
  point to a cross-depth short-bucket recovery result.
- If H1 narrows but H2/H3 pass, the scientific result is still useful: K=1
  remains a repair, but the envelope tightens sharply with frame depth.
- If H2 fails, the current K=1 recovery story should be scoped explicitly to
  shallower frame counts and should not be generalized across long-context
  depth.

## Interpretation rules

- Compare against both `1.55D K=1` and the raw `1.55A 32f` basin result.
- This is a boundary probe, not a new adaptive-policy claim.
- If `1.55G` passes and `1.55H` fails, the paper should frame the recovery
  envelope as **content-broadened but depth-bounded**.

## Execution

Pending.

## Result

Pending.

## Interpretation

Pending.
