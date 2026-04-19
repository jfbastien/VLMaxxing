# Phase 1.55A-3B-32f — Saturation-mapping test (PREREG)

**Status:** preregistration, 2026-04-20. Third 3B cross-arch point,
per 3B-24f decision rule (shifted-ramp verdict → queue 32f 3B to map
the full shifted curve).

**Parent:** `2026-04-20-phase-1_55A-3b-24f-boundary-findings.md`
(3B at 24f: Δacc = −0.190, shifted-ramp sub-outcome, clean-letter
drift with no basin collapse).

## Purpose

Two mechanistic hypotheses are live after the 3B 2-point (20f+24f)
evidence. A third data point at 32f (~12.9k prefill tokens) resolves
them:

1. **Shape-shared ramp hypothesis:** 3B ramp has the same
   monotonic-saturating shape as 7B's, just shifted to longer prefill.
   7B saturates at Δacc ≈ −0.43 (24f and 32f identical). If 3B shares
   the shape, 32f 3B should sit at Δacc ≤ −0.35 (near or at saturation).
2. **Different-saturation hypothesis:** 3B's failure mode
   (clean-letter drift, no basin collapse) has a structurally
   different ceiling. 4 letters × chance ≈ 25% correct as a lower
   bound; if 3B never saturates the `addCriterion` basin, its ceiling
   on wrong-letter drift is higher than 7B's. Could plateau at
   Δacc ≈ −0.20 to −0.25 or drift smoothly without saturating.

Resolving this distinguishes **"same mechanism, shifted threshold"**
from **"qualitatively different failure geometry across capacities"**.

## Protocol

Identical to 1.55A-3B-24f but with `--frame-count 32`.
- `--model-path ~/models/Qwen2.5-VL-3B-Instruct-4bit`
- `--frame-count 32`
- Same 7 short-bucket VideoMME clips × 3 Qs = 21 queries per mode.
- Temperature 0 (greedy).

## Hypotheses

### H1-3B-32 — speedup continues to scale with prefill

Follow-up speedup > 130× (3B speedup curve so far 136× @ 20f → 154× @
24f; extrapolation: ~170-180× @ 32f). Median follow-up ≤ 600 ms.

### H2-3B-32 — fidelity outcome (three pre-registered alternatives)

Δacc measured against 3B cold-start baseline at 32f. Three sub-
outcomes:

- **H2-3B-32.saturated (Δacc ≤ −0.35):** 3B ramp is shape-shared with
  7B; 3B saturates at a similar deep-loss level, just a few frame
  counts later. Implies unified mechanism with capacity-dependent
  threshold. Consistent with 7B extrapolation.
- **H2-3B-32.mid-ramp (Δacc ∈ (−0.35, −0.20]):** 3B is still climbing
  the ramp at 32f; saturation point (if any) is >32f. Mechanism shape
  may be gradual on 3B where 7B was abrupt.
- **H2-3B-32.plateaued (Δacc ∈ (−0.25, −0.10]):** 3B saturation limit
  is shallower than 7B's — the clean-letter-drift failure mode has a
  structurally different ceiling. Implies 3B ramp and 7B ramp
  differ in kind, not just in threshold. This would be the most
  surprising mechanistic finding — would upgrade claim #14 to
  "failure geometry, not just threshold, is architecture-dependent".

### H3-3B-32 — prefix coverage ≥ 0.99

Trivial; same driver path.

### H4-3B-32 — peak RSS

Expected ≤ 5.5 GB (3B 24f was 1.48 GB; 32f adds ~30% KV — but
measurement window may differ; treat 5.5 GB as a loose upper bound).

## Runtime budget

Expected ~40 min (3B 24f was 31 min; 32f adds ~30% prefill; 7B 32f
added ~40% over 24f).

## Decision rule

Post-run interpretation:

- **saturated** → shape-shared ramp confirmed. Claim #14 simplifies:
  "capacity-modulated threshold with shared saturation geometry". Next
  mechanism probe becomes the 7B/20f temperature probe (attractor
  basin identity vs saturation-value differences).
- **mid-ramp** → 3B ramp may not saturate at all in reachable prefill
  regime; queue 3B/40f if computationally feasible, or treat 3B as
  "progressively degrading" qualitatively distinct from 7B. Temperature
  probe still queued.
- **plateaued** → 3B saturation limit is shallower than 7B's; failure
  geometry IS architecture-specific beyond just the threshold. Paper
  story upgrades to "capacity-dependent threshold × architecture-
  dependent ceiling".

In all three cases, the 7B/20f temperature probe becomes the next
experiment — it addresses an independent question (greedy-argmax
commit vs distribution-collapse on 7B) that the 3B curve cannot
resolve.

## Falsifiers for the experiment itself

- If H1-3B-32 speedup < 130× — the 3B speedup curve has plateaued
  earlier than 7B's; prefill-dominance weakens on smaller decoder.
- If H3-3B-32 prefix < 0.99 — driver regression; run is compromised.
- If H4-3B-32 peak RSS > 6 GB — unexpected memory growth; investigate.

## Artifacts

Will land to `research/experiments/2026/artifacts/phase1_55A_3b_32f_saturation/`.
