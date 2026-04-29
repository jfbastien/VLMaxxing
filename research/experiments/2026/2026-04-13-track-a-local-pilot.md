# Track A Local Pilot

## Preregistration

Hypothesis:

- Qwen2.5-VL-3B will preserve most answers on the scored synthetic local suite
  under same-position cached-feature reuse, with static-only reuse staying safer
  than static-plus-shifted reuse

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
- per-bucket failures

Unit of analysis:

- prompt response

Model:

- `Qwen2.5-VL-3B-Instruct-4bit`

Prompt bank:

- `research/prompt_bank/local_suite_v1.toml`

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

- `static_only_default` stays within `1` answer of dense accuracy and agreement
  stays at or above `0.75`

Rejection band:

- even `static_only_default` drops more than `3` answers or agreement falls
  below `0.5`

Inconclusive:

- dense baseline accuracy is too poor to interpret the reuse comparison, or
  parse failures dominate a bucket

Notes:

- this is a local pilot, not the full threshold sweep promised later in Phase 1
- no Track B timing or speedup claims are allowed from this run

## Execution

Run date:

- 2026-04-13

Main execution:

- model: `Qwen2.5-VL-3B-Instruct-4bit`
- prompt bank: `local_suite_v1`
- decode backend: `pyav`
- sampling mode: `contiguous_window`
- synthetic windows: frames `18-29`
- preprocessing: Qwen-aligned resize to exact `28 px` multiples with target height `252 px`
- thresholds: default `(3, 8)`

Runtime debugging before the final pilot run:

1. a single long-lived `12`-item pilot process hit a Metal GPU timeout
2. the first `6` items and the last `6` items both succeeded in isolation
3. a one-item cold run and a two-item chunk both succeeded
4. a four-item cold chunk still timed out
5. the final stable execution mode on this machine was `2`-item chunked subprocesses

This is an operational constraint, not a semantic result.

Artifact:

- [track_a_pilot.json](artifacts/track_a_pilot.json)

## Result

Accepted under the pilot band.

Summary:

- dense accuracy: `10/12 = 0.833`
- static-only accuracy: `10/12 = 0.833`
- static-plus-shifted accuracy: `10/12 = 0.833`
- dense versus static-only agreement: `1.0`
- dense versus static-plus-shifted agreement: `1.0`
- dense versus static-only kappa: `1.0`
- dense versus static-plus-shifted kappa: `1.0`
- parse failures: `0` in all conditions

Items dense got wrong, and cached conditions matched:

- `syn_affine_motion`: predicted `C`, correct `A`
- `syn_cut_event`: predicted `C`, correct `A`

All other `10` items were correct in all three conditions.

Selected reuse means:

- `synthetic_fullframe_flicker`: `0.0185`
- `synthetic_scene_cut`: `0.9091`
- `synthetic_color_swap`: `0.9899`
- `synthetic_screen_ocr`: about `0.996`

## Interpretation

The narrow pilot hypothesis held.

What got stronger:

- on this scored synthetic suite, default same-position reuse preserved every dense answer under both `STATIC`-only and `STATIC+SHIFTED` conditions
- the local Qwen Track A path is now scientifically usable for threshold sweeps and refresh-interval studies

Important limitation:

- the dense baseline itself missed two event-centric questions
- the current scored suite does not yet include divergence-capable items where
  dense and cached would be expected to separate if reuse were too aggressive
- the pilot is synthetic-only and does not yet include scored natural-video items
- this pilot therefore supports **answer stability relative to the dense path**
  more strongly than it supports broad semantic adequacy or pre-release-source-level
  reproduction

Operational finding:

- on this fanless M3 Air, the Qwen synthetic pilot was not stable as one long-lived process
- chunked subprocess execution was required to avoid Metal GPU timeouts
- that is a runtime-shaping fact about this machine and stack, not evidence about the reuse method itself

What should happen next:

- threshold sweep on the hard buckets
- refresh-interval drift study
- more event-sensitive natural clips once the local synthetic contract is stable

## Links

- [PLAN.md](../../../PLAN.md)
- [docs/methodology/performance.md](../../../docs/methodology/performance.md)
- [research/prompt_bank/local_suite_v1.toml](../../prompt_bank/local_suite_v1.toml)
- [track_a_pilot.json](artifacts/track_a_pilot.json)
