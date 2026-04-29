# Phase 1.55A-3B-24f — Boundary-shift test (PREREG)

**Status:** preregistration, 2026-04-19. Second mechanism probe after
3B 20f showed H2-3B.matched (no ramp at matched prefill).

**Parent:** `2026-04-19-phase-1_55A-3b-crossarch-findings.md` (3B at
20f: Δacc = −0.048, no basin collapse).

## Purpose

The 3B 20f probe falsified pure prefill-length-intrinsic mechanism —
at the same ~8.1k-token prefill that collapses 7B to 2-basin dominance,
3B is clean. But does 3B have a ramp at all, or is the mechanism
genuinely 7B-specific?

24f on 3B targets the **boundary-shift hypothesis**: if 3B has a
capacity-dependent ramp boundary, it may appear at a longer prefill
length. 24f ≈ 9.7k tokens (the prefill where 7B saturates to single
attractor).

## Protocol

Identical to 1.55A-3B 20f but with `--frame-count 24`.
- `--model-path "$HOME/models/Qwen2.5-VL-3B-Instruct-4bit"`
- `--frame-count 24`
- Same 7 short-bucket VideoMME clips × 3 Qs = 21 queries per mode.
- Temperature 0 (greedy).

## Hypotheses

### H1-3B-24 — speedup follows prefill-dominance

Follow-up speedup > 80× (3B decode stays fast; prefill grows ~20%
over 20f). Median follow-up ≤ 600 ms.

### H2-3B-24 — fidelity outcome (three alternatives)

Δacc measured against 3B cold-start baseline at 24f. Three sub-
outcomes (pre-registered):

- **H2-3B-24.matched (Δacc ∈ [−0.05, 0.05]):** 3B still shows no ramp
  at 9.7k prefill — ramp boundary is at least this far on 3B OR does
  not exist. Strongly confirms 7B-specificity.
- **H2-3B-24.shifted-ramp (Δacc ∈ (−0.30, −0.05)):** 3B has a ramp,
  just shifted to longer prefill. Mechanism is prefill-length
  modulated by model capacity. Queue 32f 3B to map the full shifted
  curve.
- **H2-3B-24.shifted-saturation (Δacc ≤ −0.30):** 3B collapses hard
  at 24f, possibly to a different attractor basin. Check whether the
  3B basin is addCriterion (same attractor) or a different token.
  Queue basin-decomposition analysis.

### H3-3B-24 — prefix coverage ≥ 0.99

Trivial; same driver path.

### H4-3B-24 — peak RSS

Expected ≤ 4.5 GB (3B at 20f was 3.93 GB; 24f adds ~20% KV).

## Runtime budget

Expected ~33 min (3B 20f was 27 min; 20% more prefill ≈ 20% more wall
time). First-query ~67 s, 21 queries × ~50% overlap ≈ 2000 s.

## Decision rule

Post-run interpretation:
- **matched** → 24f 3B clean → ramp is genuinely 7B-specific.
  Move to 7B/20f temperature probe as next discriminator
  (greedy-commit vs distribution-collapse).
- **shifted-ramp** → prefill-length mechanism is capacity-modulated.
  Queue 32f 3B to map full curve; then temperature probe for basin
  origin.
- **shifted-saturation** → 3B has a cliff at 24f. Inspect basin
  decomposition:
  - If addCriterion basin present → attractor is architecturally
    shared even across model sizes (unlikely given 20f absence).
  - If different attractor → attractor basins are model-specific;
    each model has its own corrupt-decode basin.

## Artifacts

Will land to `research/experiments/2026/artifacts/phase1_55A_3b_24f_boundary/`.
