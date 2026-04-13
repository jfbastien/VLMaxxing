# Phase 0.5 Feasibility And Determinism

## Preregistration

Hypothesis:

- the local MLX-VLM stack on this machine exposes enough of the Qwen2.5-VL-3B vision path to support Track A feature substitution experiments

Track:

- A

Primary metric:

- bit-identical output strings across repeated dense runs on the same clip/prompt pair

Secondary metrics:

- API DAG step pass or fail status
- feature-cache interface availability
- parseable benchmark outputs
- warm and cold latency sanity

Unit of analysis:

- per prompt on fixed manifest clip ids

Models:

- `Qwen2.5-VL-3B-Instruct-4bit`
- `gemma-4-e4b-it-4bit`

Clip set:

- `xiph_akiyo_cif`
- `xiph_news_cif`

Prompt set:

- `Describe the scene in one sentence.`
- `What changes over time in this clip?`

Seed and repetitions:

- temperature `0`
- fixed backend seed where the runtime exposes one
- `N=50` dense repetitions for the determinism check on `xiph_akiyo_cif`

API DAG:

1. `import mlx_vlm` and the local generate/load path succeed
2. loading the local Qwen model succeeds
3. dense generation with no cached features succeeds
4. the same dense generation repeated `N=50` times is bit-identical
5. if the runtime exposes a cached-feature path, an intentionally altered cached-feature input changes the output

Comparison:

- dense baseline run 1 versus dense baseline run 2
- dense baseline versus a deliberately modified cached-feature path when the interface allows it

Acceptance band:

- API DAG steps `1-4` pass for Qwen
- dense output strings are bit-identical across all `N=50` repeated runs
- if step `5` is supported by the runtime, the altered cached-feature path changes the output

Rejection band:

- runtime does not expose the needed cached-feature or equivalent interface
- repeated dense baselines are not bit-identical

Inconclusive:

- any API DAG step fails intermittently at least once in 10 identical retries
- Qwen passes but Gemma does not, or vice versa
- determinism depends on backend conditions we do not yet understand

## Execution

Run date:

- 2026-04-13

Decode and sampling:

- decode backend: `pyav`
- sampling mode: `contiguous_window`
- Xiph windows: frames `0-7`
- Qwen preprocessing: exact `28 px` block multiples with target height `252 px`
- Gemma preprocessing: native `352x288` input preserved because the geometry is already aligned to `16 px`

Determinism probe:

- `50` dense repetitions on `xiph_akiyo_cif`
- prompt: `Describe the scene in one sentence.`
- models: `Qwen2.5-VL-3B-Instruct-4bit`, `gemma-4-e4b-it-4bit`

Cache-liveness probe:

- used `synthetic_color_swap`, frames `18-29`
- multiple-choice probe chosen because it is easier to force a visible cache-path effect than the low-motion Xiph prompts
- Qwen perturbation: zero one frame segment inside concatenated cached features
- Gemma perturbation: zero cached image features

Artifact:

- [phase0_5.json](artifacts/phase0_5.json)

## Result

Accepted overall, with a Qwen step-5 caveat.

Key outcomes:

- both Qwen 3B and Gemma E4B passed API DAG steps `1-4`
- both dense baselines were bit-identical across all `50` preregistered repeats
- Qwen determinism sample latency: `p50 4389 ms`, `p95 4900 ms`
- Gemma determinism sample latency: `p50 7345 ms`, `p95 8167 ms`
- Qwen cache-liveness probe kept the one-letter output unchanged but shifted prefill logits by `29.95`
- Gemma cache-liveness probe changed both text and prefill logits (`46.5` max-abs diff)

Strict preregistration caveat:

- Qwen did not satisfy the strict step-`5` text-change criterion on the chosen probe
- Gemma did satisfy step `5` directly
- the stronger cross-model cache-path conclusion therefore comes from Phase `0.75`, which was explicitly designed for that control

Representative dense outputs:

- Qwen on `xiph_akiyo_cif`: `A woman wearing a pink jacket and white shirt is sitting in front of a blue screen.`
- Gemma on `xiph_news_cif`: `The scene depicts a formal presentation setting featuring a man and a woman standing beside a large screen ...`

## Interpretation

The phase hypothesis held.

What got stronger:

- the local MLX-VLM path is deterministic enough to support Track A work on this machine
- both model families expose a usable cached-feature control path, but Qwen step `5`
  in this note should be read as logit-level liveness rather than a text-level
  semantic change

Important nuance:

- for Qwen, cache-path liveness was strongest in logits rather than final text on the chosen probe
- that means Phase `0.5` should be read mainly as a feasibility and determinism gate, not as the repo's final cache-control argument

What this does not prove:

- any sparse execution or latency win
- that open-ended prompts are semantically strong; this phase only validated the substrate

## Links

- [PLAN.md](../../../PLAN.md)
- [docs/methodology/performance.md](../../../docs/methodology/performance.md)
- [docs/methodology/timing-harness.md](../../../docs/methodology/timing-harness.md)
- [phase0_5.json](artifacts/phase0_5.json)
