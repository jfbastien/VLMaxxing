---
date: 2026-04-27
phase: 1.55F-16f
status: preregistered; not yet run
related:
  - research/experiments/2026/2026-04-25-phase-1_55F-q3-post-q2-state-prereg.md
  - research/experiments/2026/2026-04-27-adaptive-mechanism-queue-findings.md
---

# Phase 1.55F-16f — Adaptive C-PERSIST Frame-Budget Interpolation

## Question

Does the adaptive post-Q2-state policy remain stable at 16 frames on the same
short tranche where it already passed at 20f and 32f?

This is not a headline-seeking experiment. It fills the interpolation point so
the C-PERSIST curve is not only anchored by high-depth cells.

## Protocol

- Model: `Qwen2.5-VL-7B-Instruct-4bit`.
- Videos: the same 7 short VideoMME clips used by 1.55F and 1.55D:
  `037,100,116,120,158,160,210`.
- Frame count: 16.
- Sampler: greedy decoding in both arms (`temperature=0.0`) with
  `max_tokens=32`.
- Session policy:
  - Q1: dense cold
  - Q2: selective re-prefill with `K=1`
  - Q3: `K=0` from the repaired post-Q2 cache state
- Baseline: cold dense on each query at 16f.
- Analyzer: `scripts/analyze_selective_reprefill_pairs.py`.

## Gates

- **H1_fidelity**: paired correctness diffs ≤ 2/21 and paired choice diffs
  ≤ 3/21.
- **H1_exact**: paired correctness diffs = 0/21 and choice diffs = 0/21.
  This is a stricter reporting tier, not required for H1.
- **H2_pathology**: Q3 pathological-like outputs ≤ 1/7 and follow-up
  pathological-like outputs ≤ 2/14.
- **H3_speed**: all-query cold median over session follow-up median ≥ 14×.
  This is intentionally below the 20f-short adaptive point but above a
  "nominally passes while hiding a non-monotone curve" threshold.
- **H4_memory**: peak RSS ≤ 5.5 GB. If H1-H3 pass and RSS is ≤ 9 GB but
  >5.5 GB, report this as a science PASS with a too-tight memory gate, matching
  the 1.55F-long / 1.55F-32f precedent.
- **H5_signal_floor**: baseline accuracy ≥ 0.40.

## Interpretation

- PASS H1-H3: adaptive C-PERSIST is stable at the 16f interpolation point and
  the paper can draw a smoother frame-depth curve.
- FAIL H1/H2: the adaptive policy has a non-monotone frame-budget boundary,
  which is scientifically important because 20f/32f already passed.
- FAIL H3 only: fidelity survives but the speedup curve is not monotone in
  frame count; report as a systems boundary rather than a fidelity boundary.

## Runtime

Expected wall time: ~35-60 min on the local 16 GB M3 laptop.
