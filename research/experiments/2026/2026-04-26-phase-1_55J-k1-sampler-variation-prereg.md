---
phase: 1.55J
date: 2026-04-26
parent:
  - research/experiments/2026/2026-04-24-phase-1_55D-selective-reprefill-v2-k1-findings.md
  - research/experiments/2026/2026-04-25-phase-1_55G-k1-medium-replication-findings.md
  - research/experiments/2026/2026-04-25-phase-1_55I-k1-long-replication-findings.md
  - research/experiments/2026/2026-04-25-phase-1_55H-k1-32f-short-probe-findings.md
status: preregistered 2026-04-26. Wrapper and sampler-capable v2 tail generator landed; ready to run.
---

# 1.55J — K=1 sampler-variation scout

## Motivation

Fixed `K=1` selective re-prefill has become the strongest breadth result
in the C-PERSIST lane: short, medium, long, and 32f-short all show no
observed paired drift under greedy decoding. That is not enough to rule
out a sampler-path artifact. The earlier 1.55A persistent-KV basin
showed sampler-side robustness, so the repaired K=1 lane needs at least
one matched non-greedy scout before the paper leans on the fixed-lane
claim too hard.

This phase reruns the original 1.55D short tranche under deterministic
temperature sampling. The sampler uses `temperature=0.7` rather than a
near-greedy low temperature because the point of the phase is a substantive
sampler perturbation, not another effectively greedy replay.

## Configuration

- Model: Qwen2.5-VL-7B-Instruct-4bit
- Videos: same seven short clips as 1.55D K=1
  (`037,100,116,120,158,160,210`)
- Frame count: `20`
- Policy: fixed `K=1` selective re-prefill on Q2 and Q3
- Sampler: `temperature=0.7`, `top_p=0.95`, `min_p=0.0`
- Runner: `scripts/run_kv_selective_reprefill_v2.py`
- Wrapper: `scripts/run_phase1_55J_k1_sampler_variation.sh`
- Output: `research/experiments/2026/artifacts/phase1_55J_k1_sampler_variation/`

## Hypotheses

### H1 — fidelity under non-greedy sampling

Primary acceptance:

- paired correctness diffs `<= 1/21`
- paired choice diffs `<= 2/21`

Strict sub-gate:

- paired correctness diffs `= 0/21`
- paired choice diffs `= 0/21`

Interpretation:

- strict pass: the K=1 short result is not visibly sampler-conditioned
  on this tranche
- primary pass but strict miss: K=1 remains useful but the paper should
  state that sampler variation can move individual choices
- primary fail: fixed K=1 is greedy-conditioned; do not claim sampler
  robustness for the repaired lane

### H2 — no pathological follow-up basin

Acceptance:

- pathological follow-up hits `<= 1/14`
- pathological Q3 hits `<= 1/7`

Failure:

- either count exceeds its threshold

This separates ordinary sampler choice drift from the original
persistent-KV basin behavior.

### H3 — speed remains in the repaired-frontier band

Acceptance:

- same-class follow-up speedup `>= 8.0x`

Failure:

- same-class follow-up speedup `< 6.0x`

Sampling should not materially change the prefill work. A speed miss
would indicate a runner or measurement issue rather than a scientific
sampler effect.

### H4 — local memory remains within the 16 GB laptop envelope

Acceptance:

- peak RSS `<= 5.5 GB`

Failure:

- peak RSS `> 7.0 GB`

### H5 — signal floor

Acceptance:

- session correctness `>= 14/21`

Failure:

- session correctness `< 14/21`

This prevents a vacuous paired-drift pass where both the baseline and session
arms collapse to low-signal sampled outputs.

## Runtime

Expected `~60-90 min` on the current 16 GB M3 laptop.

## Result

Pending.
