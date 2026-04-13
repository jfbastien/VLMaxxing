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

Pending.

## Result

Pending.

## Interpretation

Pending.

## Links

- [PLAN.md](../../../PLAN.md)
- [docs/methodology/performance.md](../../../docs/methodology/performance.md)
- [docs/methodology/timing-harness.md](../../../docs/methodology/timing-harness.md)
