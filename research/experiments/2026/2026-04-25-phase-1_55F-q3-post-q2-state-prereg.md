---
phase: 1.55F
date: 2026-04-25
parent:
  - research/experiments/2026/2026-04-24-phase-1_55E-q2-mandatory-q3-optional-findings.md
  - research/experiments/2026/2026-04-24-phase-1_55D-selective-reprefill-v2-k1-findings.md
status: preregistered 2026-04-25. Q3-from-post-Q2 repaired-state selective re-prefill.
---

# 1.55F — Q3 from repaired post-Q2 state

## Why this prereg exists

`1.55E` answered one adaptive question cleanly:

- `Q2` is the rescue point
- `Q3` is not safely dispensable if it falls back to the original
  `Q1` full-cache path

That negative does **not** kill adaptive repair in general. It isolates a more
precise next hypothesis:

**Q3 may be safe without a fresh tail re-prefill if it reuses the repaired Q2
visual state, instead of reverting to the unrepaired Q1 cache.**

This phase tests exactly that causal alternative.

## Protocol

- Model: `Qwen2.5-VL-7B-Instruct-4bit`
- Regime: 20-frame persistent-KV short-bucket VideoMME session
- Clips: `037,100,116,120,158,160,210`
- Queries: 3 per clip, session path vs matched cold baseline
- Session policy:
  - `Q1`: cold
  - `Q2`: `K=1` selective re-prefill
  - `Q3`: `K=0`, but cache source = `post_q2_repaired`
- Runner:
  `scripts/run_kv_selective_reprefill_v2.py`
- Wrapper:
  `scripts/run_phase1_55F_q3_post_q2_state.sh`

Estimated runtime:

- session + baseline: `~60–75 min`
- paired analysis: `<1 min`
- total: `~60–75 min`

## Hypotheses

### H1 — paired fidelity improves materially over 1.55E

Acceptance:

- paired correctness diffs `<= 1/21`
- paired choice diffs `<= 2/21`

Failure:

- paired correctness diffs `>= 3/21`, or
- paired choice diffs `>= 4/21`

This is intentionally weaker than the fixed-K `1.55D` bar. The point is not
to prove equality first; it is to test whether the Q3 catastrophe was caused by
the wrong cache source.

### H2 — Q3 basin recurrence is largely suppressed

Acceptance:

- Q3 pathological-like outputs `<= 2/7`

Failure:

- Q3 pathological-like outputs `>= 4/7`

### H3 — the adaptive speed benefit remains meaningfully above K=1

Acceptance:

- session follow-up median is lower than the landed `1.55D K=1` follow-up
  median (`10.136 s`)

Failure:

- session follow-up median is not lower than `1.55D K=1`

### H4 — memory stays inside the existing local budget

Acceptance:

- `peak_rss_gb <= 5.0`

Failure:

- `peak_rss_gb > 5.0`

## Decision rules

- If H1 + H2 + H3 + H4 pass, `1.55F` becomes the new best adaptive point and
  directly tightens the C-PERSIST recovery story.
- If H2 passes but H1 only narrows rather than clears, the scientific result is
  still useful: the Q3 failure mechanism was mostly state-source selection, not
  "adaptive is impossible."
- If H2 fails, the Q3 catastrophe is not explained by fallback-to-Q1 alone and
  the next move should be risk-gated admission rather than another cache-source
  variant.

## Interpretation rules

- Compare directly against both `1.55D K=1` and `1.55E`.
- Use the new paired metrics, not prose-only summaries, for speed and fidelity.
- The paper-facing claim should stay at "no observed drift" unless the sample
  size increases materially.

## Execution

Pending.

## Result

Pending.

## Interpretation

Pending.
