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

Run date:

- 2026-04-13

Decode and sampling:

- decode backend: `pyav`
- sampling mode: `contiguous_window`
- Xiph windows: frames `0-7`
- same clip ids and prompt texts as Phase `0.5`

Conditions:

- `A0`: dense direct generation
- `A1`: unchanged dense features routed through `cached_image_features`
- `A2`: deliberately perturbed cached features

Perturbation policy:

- Qwen: zero one frame segment after splitting the concatenated cached features by `image_grid_thw`
- Gemma: zero cached image features directly

Repetition count:

- `10` per condition per prompt response

Artifact:

- [phase0_75.json](artifacts/phase0_75.json)

## Result

Accepted.

Key outcomes:

- on all `4` preregistered prompt responses per model, `A0 == A1` exactly across all `10` repetitions
- prefill logits for `A0` and `A1` matched exactly with `max_abs_diff = 0.0` on both models
- perturbed-cache logits moved strongly on every sample:
  - Qwen minimum `A0` versus `A2` logit diff: `27.73`
  - Gemma minimum `A0` versus `A2` logit diff: `49.5`
- perturbed text often changed, but not always; the logit probe was the stronger liveness signal

Observed but not interpreted as a systems claim:

- cached-path latencies were often lower than dense latencies
- this note does **not** present that as Track B evidence because dense vision encode still happened to produce the cached features

## Interpretation

The cache-path identity control passed cleanly.

What got stronger:

- the local Track A substrate is trustworthy on both Qwen 3B and Gemma E4B
- later planner-driven disagreements can be attributed to reuse policy rather than to a broken cache interface

What changed in repo status:

- `cache-path identity equivalence for Track A` is now locally validated instead of merely a prerequisite hypothesis

What remains out of scope:

- real skipped compute
- broader benchmark claims beyond these local controls

## Links

- [PLAN.md](../../../PLAN.md)
- [docs/methodology/preprocessing.md](../../../docs/methodology/preprocessing.md)
- [research/experiments/2026/2026-04-13-phase-0_5-feasibility.md](2026-04-13-phase-0_5-feasibility.md)
- [phase0_75.json](artifacts/phase0_75.json)
