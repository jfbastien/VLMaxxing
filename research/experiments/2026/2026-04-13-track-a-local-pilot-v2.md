# Track A Local Pilot V2

## Preregistration

Hypothesis:

- the repaired synthetic Track A suite will remain stable under conservative
  same-position reuse, while providing more meaningful pressure through
  temporal-necessity items and stronger clip semantics than the original v1
  pilot

Track:

- A

Primary metrics:

- baseline accuracy
- modified-path accuracy
- baseline-versus-modified agreement
- Cohen's kappa on parsed multiple-choice outputs

Secondary metrics:

- parse-failure count
- mean reused ratio
- critical-span reused ratio on items with `critical_pair_indices`
- per-item prefill-logit drift

Unit of analysis:

- prompt response

Model:

- `Qwen2.5-VL-3B-Instruct-4bit`

Prompt bank:

- `research/prompt_bank/local_suite_v2.toml`

Sampling mode:

- `contiguous_window`

Preprocessing:

- decode backend: `pyav`
- colorspace: RGB
- no padding
- Qwen-aligned resize to exact `28 px` block multiples with target height
  `252 px`

Conditions:

- `dense`: direct dense generation
- `static_only_default`: reuse only `STATIC` blocks under default thresholds `(3, 8)`
- `static_shifted_default`: reuse `STATIC` and `SHIFTED` blocks under default thresholds `(3, 8)`

Acceptance band:

- dense accuracy stays at or above `0.75`
- `static_only_default` stays within `1` answer of dense accuracy
- dense-versus-static agreement stays at or above `0.75`

Rejection band:

- dense accuracy drops below `0.5`
- even `static_only_default` drops more than `3` answers or agreement falls
  below `0.5`

Inconclusive:

- parse failures dominate a bucket
- the repaired suite still contains visibly invalid clip-question pairings
- runtime instability prevents a clean full-pilot run

Notes:

- this experiment is still a local pilot, not the whitepaper's real-video or
  benchmark path
- the aim is to upgrade the suite quality before further sweeps, not to claim a
  headline reproduction

## Execution

Run date:

- 2026-04-13

Artifact:

- [track_a_pilot_v2.json](artifacts/track_a_pilot_v2.json)

Runtime notes:

- first full-pilot attempt hit the same Metal GPU timeout class seen earlier on
  this machine
- the immediate rerun with the same chunked-subprocess harness succeeded
- treat this as continuing evidence that the Qwen local harness remains runtime
  constrained on this fanless M3 Air

## Result

Accepted under the pilot band, with a real controlled failure.

Summary:

- dense accuracy: `12/12 = 1.000`
- static-only accuracy: `11/12 = 0.917`
- static-plus-shifted accuracy: `11/12 = 0.917`
- dense versus static-only agreement: `11/12 = 0.917`
- dense versus static-plus-shifted agreement: `11/12 = 0.917`
- dense versus static-only kappa: `0.867`
- dense versus static-plus-shifted kappa: `0.867`
- parse failures: `0` in all conditions
- middle-required items in the suite: `5`

Single controlled failure:

- `syn2_mid_text_ever_bravo`
  - dense answer: `A` (correct)
  - static-only answer: `B` (wrong)
  - static-plus-shifted answer: `B` (wrong)
  - static critical-span reused ratio mean: `0.981`
  - shifted critical-span reused ratio mean: `0.991`

Diagnostic finding after the follow-up temporal-necessity ablation:

- the raw `11/12` cached headline overcounts true cache safety
- on the same `synthetic_mid_text_flash` clip, the cached path still answers
  `syn2_mid_text_flash_word` correctly with `BRAVO`, but the ablation later
  showed that this item is answerable without the middle frames
- the paired existential item, `syn2_mid_text_ever_bravo`, fails without the
  middle frames and also fails under caching
- that contradiction is strong evidence that some apparent v2 passes are driven
  by prompt structure or textual prior rather than grounded temporal evidence
- the follow-up note
  [2026-04-13-phase-1_05-temporal-necessity-ablation.md](2026-04-13-phase-1_05-temporal-necessity-ablation.md)
  should be read before using this pilot as a discriminating benchmark

Interpretive contrast with the v1 pilot:

- v1 produced perfect dense-versus-cached agreement on a synthetic suite that
  could not clearly force divergence
- v2 produces one real dense-versus-cached failure on a middle-dependent OCR
  item while keeping the dense baseline itself clean

## Interpretation

The repaired suite is scientifically stronger than v1.

What got stronger:

- the local scored suite now contains at least one divergence-capable item
- dense accuracy is strong enough to interpret reuse failures rather than
  blaming weak baseline semantics
- critical-span reuse reporting surfaced why clip-wide average reuse alone is
  insufficient
- the follow-up ablation separated the v2 suite into contaminated items and a
  smaller discriminating subset

What got weaker:

- default same-position reuse under the current `(3, 8)` thresholds is not
  universally safe, even in the `STATIC`-only condition
- middle-dependent OCR events are an early failure bucket on this local stack
- the raw `11/12` cached accuracy should not be treated as the discriminating
  suite headline because at least two middle-required passes survive without the
  middle frames

Practical consequence:

- threshold sweeps and refresh-interval work should prioritize the
  discrimination-safe subset, then add more natural-video event items before
  broader aggregate reporting

What this still does not prove:

- real-video or benchmark-native reproduction
- any Track B sparse-execution or speedup claim

## Links

- [PLAN.md](../../../PLAN.md)
- [docs/reproduction-status.md](../../../docs/reproduction-status.md)
- [research/prompt_bank/local_suite_v2.toml](../../prompt_bank/local_suite_v2.toml)
