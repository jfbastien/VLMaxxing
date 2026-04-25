---
phase: 1.30W
date: 2026-04-24
parent:
  - research/experiments/2026/2026-04-23-phase-1_30-rootcause-findings.md
  - research/experiments/2026/2026-04-23-phase-1_30V-adaptive-vleg-findings.md
status: preregistered 2026-04-24. Short-scout admission-policy rescue for the 1.30 streaming bridge.
---

# 1.30W — Dense Q0 admission, session-reuse follow-ups (short scout)

## Why this prereg exists

Phase 1.30 root-cause decomposition and the 1.30V fixed-rate rescue both
say the same thing:

- the bridge failure is dominated by the **Q0 V-leg** at `L=2, kr_V=0.50`,
- fixed-rate softening to `kr_V ∈ {0.67, 0.75}` still fails the Q0 gate,
- the next credible rescue is **admission**, not another blind fixed-rate
  rerun.

The simplest admission policy is query-positioned:

- **Q0 dense**
- **Q2/Q3 on the same session-reuse follow-up path used by the original 1.30 stack**

This scout tests whether that minimal policy is enough to restore the
short-scout streaming bridge to a paper-relevant accuracy band while
keeping meaningful amortized speedup.

## Arms

Same short-scout manifest as the 1.30 root-cause work:

- `research/benchmark_manifests/videomme_dev_v1_short_only.toml`

Two arms only:

1. `cold_dense` — no cache reuse, no pruning
2. `streaming_q0_dense_followup_pruned_off` — cache reuse on, Q0 keep-rate
   `1.0`, Q2/Q3 keep-rate `0.50`, no hard reset

Wording discipline for the resulting write-up:

- until the image-token activity logs exist, describe this as **dense-Q0
  admission plus the session-reuse follow-up path**
- do **not** imply that follow-up vision pruning is materially active just from
  the configured keep-rate alone

Model:

- `Qwen2.5-VL-7B-Instruct-4bit`

## Hypotheses

### H1-Q0 (Q0 admission removes the first-query loss)

First-query accuracy matches `cold_dense` within the short-scout
budget:

- `Δacc_q0 >= -0.05`

**Interpretation if PASS:** the admission policy fixes the dominant term
identified by 1.30 root-cause.

### H2-all (overall bridge rescue)

All-query accuracy lands within a narrowed rescue band:

- `Δacc_all >= -0.10` versus `cold_dense`

This is intentionally weaker than the original 1.30 paper budget
(`±0.05`) because this is a scout, not a paper-promotion run.

**Interpretation if PASS:** Q0 admission alone may be enough to reopen a
full paired rerun.

### H3-followup (follow-up pruning stays tolerable once Q0 is dense)

Follow-up accuracy lands at or above the dense-streaming short-scout
surface:

- `follow_up_acc >= 0.55`

`0.55` is the observed `streaming_dense_off` q23 accuracy from the
1.30 root-cause scout.

**Interpretation if PASS:** the remaining gap after Q0 admission is no
worse than the already-measured K-only term.

### H4-speed (bridge still matters as a system)

Amortized end-to-end speedup versus `cold_dense` remains:

- `>= 2.5×`

**Interpretation if PASS:** the rescue is still a deployment-relevant
bridge rather than a semantic-only patch.

### H5-format (no new degeneration)

- parse failures `= 0`
- degenerate fraction `<= 0.10`

## Decision rules

- **H1 + H2 + H4 PASS**: promote to a full dev+holdout paired rerun as
  the first serious 1.30 rescue lane.
- **H1 PASS but H2 FAIL**: Q0 admission helps but is insufficient; the
  remaining problem is follow-up pruning or V×K state interaction.
- **H1 FAIL**: even dense Q0 is not enough under this harness; stop
  treating Q0 admission as the main rescue path.
- **H4 FAIL**: the rescue may be semantically interesting but not a
  deployment bridge.

## Runtime estimate

- cold dense short scout: ~15 min
- streaming positioned-policy short scout: ~8-10 min
- pair analysis: ~1 min

Total: **~25-30 min**

## Reproduction

Run:

```bash
bash scripts/run_phase1_30_q0_admission_scout.sh
```

Artifacts land under:

`research/experiments/2026/artifacts/phase1_30W_q0_dense_followup_pruned_short/`
