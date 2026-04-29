---
phase: 1.41
date: 2026-04-21
parent: research/experiments/2026/2026-04-21-phase-1_41-qwen-videomme-16f-holdout-prereg.md
prior:
  - research/experiments/2026/2026-04-21-phase-1_41-qwen-videomme-16f-holdout-findings.md
  - research/experiments/2026/2026-04-19-phase-1_41-qwen-videomme-16f-findings.md
  - research/experiments/2026/2026-04-18-phase-1_41-qwen-videomme-baseline-findings.md
status: prereg (Qwen 7B 8f VideoMME holdout n=30 — close the paired-holdout hole)
tracking: autonomous session 2026-04-21 dynamic-loop diagnostic
---

# 1.41 Qwen 8f VideoMME holdout — prereg (paired-holdout closer)

## Motivation

The 16f-holdout findings doc explicitly flagged this run as a
non-goal: "No paired Qwen 8f holdout run — prereg specified the
comparison against 8f holdout for H2, but the test still clearly
falsifies against 8f dev" (`...16f-holdout-findings.md:95`). The H2
falsification stands on dev-vs-holdout; this run closes the paired
same-split comparison (holdout 8f vs holdout 16f) that the original
prereg's H2 actually asked for.

Three things it can tell us:

1. Does the non-monotone 8f→16f shape exist at all on holdout? Dev
   shows 8f long 0.300 → 16f long 0.100 (−20pp). Holdout 16f long
   landed at 0.900. If holdout 8f long is also ≥ 0.80, the shape
   is genuinely absent on holdout. If it's, say, 0.50, then holdout
   shows an *uptick* with more frames — still falsifies the dev
   framing but in the opposite direction.
2. It pairs the H2 gate on a single item draw instead of
   cross-split, which is the cleaner test.
3. It strengthens claim #8 (VideoMME breadth gate on Qwen 7B) to
   dev+holdout at both 8f and 16f.

This run is a **diagnostic**, not a gate. No headline cell flips on
the outcome.

## Pre-registered predictions

**H1 (aggregate plausibility)**: holdout 8f `dense_acc ∈ [0.45, 0.75]`.
Rationale: dev 8f landed 0.533; holdout 16f landed 0.700. Holdout
items are disjoint, small-n, and bucket distribution matches. Wide
window because we now have evidence the holdout split is easier than
dev on long and harder on short at 16f — 8f outcome is not tightly
predicted. **Falsification:** < 0.40 or > 0.80.

**H2 (paired-holdout shape)**: `long_acc(holdout 8f)` compared to
`long_acc(holdout 16f) = 0.900`. Three sub-outcomes:
- H2a: `long_acc(holdout 8f) < 0.800` → holdout has an 8f→16f long
  uptick; dev non-monotone (−20pp) is an *inverted* shape on holdout.
- H2b: `long_acc(holdout 8f) ∈ [0.800, 0.950]` → holdout is flat or
  near-ceiling at 8f already; no 8f→16f effect either way.
- H2c: `long_acc(holdout 8f) > 0.950` → holdout 8f *exceeds*
  holdout 16f on long → supports the "16f long regresses" shape
  on the same split. Would partially rehabilitate dev's dev-only
  framing.

We publish whichever sub-outcome lands. **No falsification gate**:
this is a diagnostic designed to characterize a shape we already know
is item-draw-dependent.

**H3 (short/medium not broken)**: holdout 8f `short_acc ∈ [0.40, 0.95]`
AND `medium_acc ∈ [0.30, 0.90]`. Wide band — just asking for "not
broken". **Falsification:** either bucket < 0.20.

**H4 (agreement to identity cache bit-faithful)**: `agreement = 1.000`.
Rationale: bit-identity has held at 8f dev, 16f dev, 16f holdout;
should hold at 8f holdout. **Falsification:** agreement < 1.000.

**H5 (RSS headroom)**: peak RSS ≤ 10 GB. Rationale: 16f holdout
was 7.23 GB; 8f is strictly less prefill, so headroom is generous.
**Falsification:** > 11 GB.

## Decision matrix

| H1 | H2 sub-outcome | Claim-matrix action |
|----|----------------|---------------------|
| pass | H2a (uptick) | Non-monotone shape is **item-draw-reversing**; paper softens further to "dev shows 8f→16f drop on long; holdout shows the opposite — frame-scaling shape is item-draw-dependent, not a stable property of this model." |
| pass | H2b (flat near ceiling) | No 8f→16f effect on holdout; paper reads "the shape did not replicate on holdout (holdout long flat ~0.85 at both frame counts)". |
| pass | H2c (drop replicates) | Paired-holdout drop **does** reproduce; paper recovers some strength: "dev-only framing applies to short/medium; long-bucket drop replicates on holdout." |
| fail | any | Small-n artifact; no claim flip. Note sampling variance. |

## Configuration

Mirrors 16f holdout invocation, only `--frame-count` changes:

```
model-path        $QWEN_7B_4BIT_MODEL_PATH
benchmark         videomme
manifest          research/benchmark_manifests/videomme_holdout_v1.toml
frame-count       8
cache-mode        identity
max-tokens        32
output            research/experiments/2026/artifacts/phase1_41_qwen_videomme_8f_holdout/dense_n30.jsonl
summary           research/experiments/2026/artifacts/phase1_41_qwen_videomme_8f_holdout/dense_n30_summary.json
```

## Runtime

Dev 8f ran at 16 min wall-clock (n=30). Holdout has the same n=30 and
matched-bucket composition; expect ~15-20 min. Well within autonomous
budget.

## Non-goals

- No pruning arm.
- No thermal pairing (dense-only identity-cache).
- No 32f holdout.
- No H2 falsification gate (this is diagnostic by design — no
  sub-outcome flips headline cells).
