# Phase 0.75: Cache-Path Identity Control

## Preregistration

Hypothesis:

- the cached-feature interface is semantically equivalent to the direct dense
  path when fed unchanged dense features

Track:

- A

Primary metric:

- exact output-string identity between direct dense generation and
  dense-through-cache generation

Secondary metrics:

- parse success
- clause-level answer extraction stability when the output format permits it

Unit of analysis:

- prompt response

Models:

- `mlx-community/Qwen2.5-VL-3B-Instruct-4bit`
- `mlx-community/gemma-4-e4b-it-4bit`

Gemma visual token budget:

- `280` for the initial pilot unless a later preregistration says otherwise

Clips:

- `xiph_akiyo_cif`
- `xiph_news_cif`

Sampling mode:

- `contiguous_window`

Prompts:

- `Describe the scene in one sentence.`
- `What changes over time in this clip?`

Conditions:

- `A0`: direct dense generation
- `A1`: dense features routed back through the cache path unchanged
- `A2`: deliberately perturbed cached features to verify the cache path is live

Acceptance band:

- `A0 == A1` exactly on every preregistered prompt response
- `A2` changes at least one response or intermediate feature comparison,
  proving that the cache path is not a no-op

Rejection band:

- any stable `A0 != A1` mismatch under unchanged dense features

Inconclusive rule:

- the interface exists but fails intermittently, or `A2` does not show that the
  path is active

Repetition count:

- `N = 10` per condition after Phase 0.5 determinism has already passed

Notes:

- this is a control experiment, not a reuse experiment
- if this fails, do not interpret later planner-driven disagreements as method
  failures

## Execution

Not run yet.

## Result

Pending.

## Interpretation

Pending.

## Links

- [PLAN.md](../../../../PLAN.md)
- [docs/methodology/preprocessing.md](../../../../docs/methodology/preprocessing.md)
- [research/experiments/2026/2026-04-13-phase-0_5-feasibility.md](2026-04-13-phase-0_5-feasibility.md)
