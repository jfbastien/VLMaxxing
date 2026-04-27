# Phase 1.55K — Adaptive C-PERSIST Temperature Sweep (PREREG)

## Question

Is the adaptive C-PERSIST headline limited to greedy decoding, or does paired
stability survive practical non-greedy sampling?

## Policy

Use the 1.55F adaptive policy on the same seven short-bucket clips:

- Q2: `K=1`
- Q3: `K=0`
- Q3 cache source: `post_q2_repaired`
- frame count: 20
- max tokens: 32
- sampler: same temperature/top-p/min-p for session and baseline arms

Default temperatures: `0.5, 0.7, 1.0, 1.5`. The landed greedy 1.55F cell is
included as a `T=0.0` reference when present.

## Gates

For every non-greedy temperature:

- H1-fidelity: paired correctness diffs <= 2/21 and paired choice diffs <= 3/21.
- H2-format: follow-up pathological-like responses <= 2/14.

Strict exact-match temperatures are reported separately and are not required for
the main sampler-stability gate.

## Interpretation

If H1/H2 hold across the sweep, adaptive C-PERSIST is not merely a greedy-path
artifact. If the sweep cliffs at higher temperature, the paper should state the
sampler boundary explicitly rather than claiming broad sampler invariance.
