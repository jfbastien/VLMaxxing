# Phase 1.3: Cross-Check Real-Video Slice

## Preregistration

Claim register target:

- `WP-2.4`

Reproduction mode:

- generalized reproduction

Objective:

- build and evaluate a small scored real-video slice on the predecessor
  cross-check clips before attempting benchmark-native TOMATO or MVBench runs

Hypothesis:

- the drafted cross-check real-video slice will produce a usable dense baseline
  and default same-position reuse will preserve most dense answers, but the
  middle-dependent cut items may expose localized failures

Track:

- A

Primary metrics:

- dense accuracy
- dense-versus-cached agreement
- cached accuracy under `STATIC`-only and `STATIC+SHIFTED`

Secondary metrics:

- parse failures
- temporal-necessity ablation on the middle-required items
- critical-pair reuse ratios on the cached runs

Unit of analysis:

- scored item

Acceptance band:

- dense accuracy is at least `4/6`
- parse failures remain `0`
- at least one middle-required item fails the temporal ablation
- cached accuracy stays within one item of dense accuracy

Rejection band:

- dense baseline is too weak to interpret the slice
- prompt parsing fails repeatedly
- cached accuracy drops by two or more items against dense

Inconclusive:

- the dense baseline is usable but the drafted items still prove too
  prompt-prior or endpoint-solvable to function as a meaningful real-video slice

Prompt bank:

- [crosscheck_slice_v1.toml](../../prompt_bank/crosscheck_slice_v1.toml)
- successor rewrite: [crosscheck_slice_v2.toml](../../prompt_bank/crosscheck_slice_v2.toml)

Notes:

- this slice uses the predecessor cross-check clips for reproduction value, not
  for stable final paper evidence
- if the slice is promising, a later stable-corpus counterpart should be built
  on Xiph or other reproducible public clips

## Execution

Run date:

- 2026-04-13

Artifacts:

- first draft ablation:
  [phase1_3_temporal_ablation.json](artifacts/phase1_3_temporal_ablation.json)
- endpoint-oriented rewrite:
  [track_a_crosscheck_slice_v2.json](artifacts/track_a_crosscheck_slice_v2.json)

## Result

Run 1: `crosscheck_slice_v1`

Preregistration outcome:

- Inconclusive

Observed outcome:

- dense accuracy landed at `4/6`
- parse failures remained `0`
- one drafted middle-required talking-head item was contaminated by endpoint or
  prompt effects
- the other drafted middle-required talking-head item missed in the dense
  baseline, so the slice did not end up with a reliable middle-event core

Run 2: `crosscheck_slice_v2`

Preregistration outcome:

- Accepted with caveat

Observed outcome:

- dense accuracy: `6/6`
- `STATIC`-only accuracy: `6/6`
- `STATIC+SHIFTED` accuracy: `6/6`
- dense-versus-cached agreement: `1.0` for both cached conditions
- parse failures: `0`
- execution required `chunk_size = 1` on this machine; `chunk_size = 2`
  triggered the same Metal GPU timeout class seen elsewhere with larger natural
  windows

Caveat:

- the accepted v2 slice is endpoint-oriented scene-fact evaluation on natural
  video, not a middle-dependent temporal-event slice
- it is therefore a narrow generalized reproduction of `WP-2.4`, not a full
  replacement for the larger pre-release source quality suite

## Interpretation

This experiment family did two useful things.

First, the v1 draft falsified the idea that "natural video" automatically makes
the middle-event items good. The talking-head cut questions were too weak and
had to be rewritten or dropped. That is valuable negative evidence, and it kept
the repo from over-reading a bad slice.

Second, the v2 rewrite gives a clean first real-video Track A result on the
predecessor cross-check corpus. On this endpoint-oriented `6`-item slice,
default same-position reuse preserved every dense answer under both cached
conditions. That is still narrow evidence, but it is real natural-video
evidence rather than synthetic-only evidence.

The operational chunk-size finding also matters. Natural-video `720p`
cross-check windows are heavy enough on this M3 Air that `chunk_size = 2`
remains unstable, while `chunk_size = 1` completes cleanly. That means later
real-video and benchmark-native Track A work should treat chunk size as part of
the declared execution contract on this machine.

## Links

- [docs/claim-register.md](../../../docs/claim-register.md)
- [research/prompt_bank/crosscheck_slice_v1.toml](../../prompt_bank/crosscheck_slice_v1.toml)
- [research/prompt_bank/crosscheck_slice_v2.toml](../../prompt_bank/crosscheck_slice_v2.toml)
- [2026-04-13-phase-1_0b-matched-content-redundancy.md](2026-04-13-phase-1_0b-matched-content-redundancy.md)
