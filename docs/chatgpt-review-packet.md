# ChatGPT Review Packet

Use this packet for the next deep external review pass.

Goal:

- tighten the scientific contract
- find literature or framing gaps
- improve the near-term experiment plan before we execute

## Context

Source-of-truth files:

- [AGENTS.md](../AGENTS.md)
- [PLAN.md](../PLAN.md)
- [docs/methodology/performance.md](methodology/performance.md)
- [docs/methodology/timing-harness.md](methodology/timing-harness.md)
- [docs/clip-policy.md](clip-policy.md)
- [paper/framing.md](../paper/framing.md)
- [research/decision-log.md](../research/decision-log.md)
- [research/experiments/2026/2026-04-13-phase-0_5-feasibility.md](../research/experiments/2026/2026-04-13-phase-0_5-feasibility.md)
- [docs/literature-map.md](literature-map.md)
- [docs/external-feedback-validation.md](external-feedback-validation.md)

Important constraints:

- Track A and Track B must stay separate
- imported seed material is not local proof
- target machine is an M3 MacBook Air with 16 GB unified memory
- initial model order is Qwen2.5-VL-3B, Gemma 4 E4B, then Qwen2.5-VL-7B
- clips stay local; no git-checked media and no git LFS

## Highest-Value Questions

1. Audit our scientific contract for Track A and Phase 0.5/1.
   What ambiguities, hidden degrees of freedom, or weak preregistration points still remain, and how would you tighten them before we run anything?

2. Review our timing methodology like a hostile systems reviewer.
   What Apple-silicon or MLX-specific confounds, harness bugs, or measurement traps are still likely to invalidate Track B claims?

3. Pressure-test our literature framing against the closest adjacent work.
   What key papers or threads are still missing, and how should we crisply differentiate our repo from CoPE-VideoLM, CodecSight, ToMe/FastV-style pruning, and machine-oriented codec work?

4. Given our current claim boundary, what are the 5 strongest likely reviewer attacks on the paper story, and how should we preempt each one in experiments, writing, or claim scoping?

5. Critique our local corpus plan.
   What is the best near-term reproducible clip set for low-motion, egomotion, screen content, and high-detail stress cases without using LFS, and what important buckets are we still missing?

6. Design the strongest minimal Phase 1 experiment suite for this laptop.
   Specify exact clip buckets, prompt families, sample sizes, threshold sweeps, refresh-interval sweeps, and failure analyses needed to make the result interpretable.

7. We now plan Qwen first and Gemma second.
   What model-family-specific pitfalls should we expect when comparing reuse behavior across these two architectures, and what separate acceptance bands would you pre-register for each?

8. Review our decision log and imported-claim hygiene.
   Which imported claims still risk leaking into the future paper as if locally verified, and what should be demoted, reworded, or explicitly tested next?

9. Among our future horizons, which are the most evidence-adjacent and paper-useful now versus too speculative to emphasize?
   Rank screen-content specialization, compute-denial robustness, multi-reference stabilization, machine-oriented sidecars, sensor-fusion timelines, and AI-native codecs, and justify the ranking with citations.

10. What statistics should we actually use for our likely experiments?
    Recommend concrete tests, confidence intervals, and minimum useful sample sizes for agreement, accuracy deltas, per-bucket failures, and paired timing comparisons.

## Short Version

If time is limited, ask for answers to:

- `1`
- `3`
- `5`
- `6`

first.
