---
date: 2026-04-26
status: planning note; not in the default adaptive-mechanism queue
related:
  - research/experiments/2026/2026-04-21-phase-1_30-sam-streaming-reproduction-prereg.md
  - research/experiments/2026/2026-04-24-phase-1_30W-q0-dense-followup-pruned-full-findings.md
  - research/experiments/2026/2026-04-25-phase-1_30AB-long-q0-sweep-findings.md
---

# Deployment Baseline Plan

## Position

Deployment baselines are worth doing, but they should not be mixed into the
adaptive C-PERSIST closeout queue. The issue is not wall-clock cost; it is fair
protocol design. The local paper now has a strong mechanism/efficiency story,
while deployment baselines answer a different question: "would a simpler
streaming policy get similar utility under the same online constraints?"

The right compromise is to stage a separate deployment-baseline batch after the
adaptive queue. That keeps the current C-PERSIST closure clean and lets the
baseline protocol be preregistered without rushing the comparison.

## Baselines

### D1 — Low-FPS dense

Question: can a dense model with fewer uniformly sampled frames match the
session policies?

Implementation cost: low. Existing runners already support `--frame-count`.

Recommended cells:

- VideoMME dev+holdout full union, 4f cold dense
- optionally 2f cold dense if 4f is near the accuracy envelope

Estimated runtime:

- `~2-3 h` for 4f full union
- `~2-3 h` additional for 2f full union

Value:

- high reviewer-defense value because it tests the simplest "just use fewer
  frames" objection
- directly comparable against the landed 8f cold reference

Interpretation:

- if low-FPS dense preserves accuracy, some first-pass C-VISION claims need a
  "low-FPS dense is also competitive" caveat
- if it fails, the paper gains a clean baseline defense

### D2 — Screenshot polling

Question: would periodic single-frame or few-frame polling be enough for the
same user-facing session?

Implementation cost: medium. VideoMME does not provide online query timestamps,
so a naive screenshot-polling baseline risks becoming just another low-FPS
uniform-frame baseline. A fair protocol needs an explicit time model:

- fixed cadence over the video before each query, or
- last available frame before a simulated query timestamp, or
- a full-clip polling cache with per-query retrieval

Estimated runtime after implementation:

- `~3-5 h` per policy point

Value:

- high for systems venues
- moderate for the current arXiv-style mechanism paper unless the protocol is
  very clean

### D3 — SimpleStream-like recency

Question: can a recency window over recent frames match the session policies?

Implementation cost: medium to high. Recency is natural in online streaming,
but VideoMME questions often refer to whole-clip content. A recency-only policy
can be unfairly weak or unfairly strong depending on where the answer evidence
appears.

Estimated runtime after implementation:

- `~3-5 h` per policy point

Value:

- high for a systems-venue follow-up
- not required to close the current C-PERSIST mechanism story

## Recommendation

Do not add deployment baselines to the current adaptive-mechanism queue. Add a
separate deployment-baseline queue after `1.55F-medium/long/32f`, `1.55J`,
`1.30AC`, and `1.30AD` land.

First deployment queue:

1. low-FPS dense 4f full union
2. low-FPS dense 2f full union only if 4f is competitive
3. protocol design review for screenshot polling and recency

This gives the paper an honest answer to the cheapest baseline objection before
we spend time on harder online baselines whose fairness depends on design
choices rather than code alone.
