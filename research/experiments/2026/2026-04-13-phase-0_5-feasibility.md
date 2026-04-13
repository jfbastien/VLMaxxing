# Phase 0.5 Feasibility And Determinism

## Preregistration

Hypothesis:

- the local MLX-VLM stack on this machine exposes enough of the Qwen2.5-VL-3B vision path to support Track A feature substitution experiments

Track:

- A

Primary metric:

- ability to run dense baseline twice with deterministic outputs on the same clip/prompt pair

Secondary metrics:

- feature-cache interface availability
- parseable benchmark outputs
- warm and cold latency sanity

Unit of analysis:

- per prompt on a small local clip subset

Comparison:

- dense baseline run 1 versus dense baseline run 2
- dense baseline versus a deliberately modified cached-feature path when the interface allows it

Acceptance band:

- deterministic or effectively deterministic baseline on repeated runs
- required feature-substitution hooks are reachable

Rejection band:

- runtime does not expose the needed cached-feature or equivalent interface
- repeated dense baselines disagree enough to pollute Track A interpretation

Inconclusive:

- interface exists but fails intermittently
- determinism depends on conditions we do not yet understand

## Execution

Pending.

## Result

Pending.

## Interpretation

Pending.

## Links

- [PLAN.md](../../../PLAN.md)
- [docs/methodology/performance.md](../../../docs/methodology/performance.md)
- [docs/methodology/timing-harness.md](../../../docs/methodology/timing-harness.md)
