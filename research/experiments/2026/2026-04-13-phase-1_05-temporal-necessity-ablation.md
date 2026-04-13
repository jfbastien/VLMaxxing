# Phase 1.05: Temporal-Necessity Ablation

## Preregistration

Hypothesis:

- at least one currently passing middle-required v2 item is answerable from
  `frame 0` alone or from `first+last` frames alone, which would mean the
  current local suite still contains prompt-prior or endpoint-solvable
  contamination

Track:

- A-supporting measurement

Primary metrics:

- dense accuracy on the ablation runner
- `frame 0`-only accuracy
- `first+last` accuracy
- count of middle-required items that remain correct without the middle frames

Secondary metrics:

- per-item contradiction cases between dense success and ablated success
- bucket concentration of contaminated items

Unit of analysis:

- prompt-bank item

Model:

- `Qwen2.5-VL-3B-Instruct-4bit`

Prompt bank:

- `research/prompt_bank/local_suite_v2.toml`

Sampling mode:

- `contiguous_window` for dense
- `frame 0` and `first+last` ablations for the reduced conditions

Acceptance band:

- at least one dense-correct item with `requires_middle_frames = true` also
  stays correct under `frame 0`-only or `first+last`

Rejection band:

- no dense-correct middle-required item stays correct under either reduced
  condition

Inconclusive:

- parse failures dominate the reduced conditions
- runtime instability prevents a clean full-suite run

Notes:

- this is a suite-diagnostics experiment, not a method-quality claim
- a positive result weakens the suite headline and identifies which items
  should be excluded from the discriminating set for later sweeps

## Execution

Run date:

- 2026-04-13

Artifact:

- [phase1_05.json](artifacts/phase1_05.json)

Execution notes:

- the first attempt overlapped with a stale earlier ablation worker and was
  discarded
- the kept artifact comes from sequential single-worker `2`-item chunk runs so
  the suite-diagnostics pass did not overlap model-heavy workers
- the ablation also exposed prompt-bank metadata drift; the item-level outputs
  were unchanged, and the summary below uses the corrected metadata now checked
  into `local_suite_v2.toml`

## Result

Accepted.

Summary:

- dense accuracy: `12/12 = 1.000`
- `frame 0`-only accuracy: `10/12 = 0.833`
- `first+last` accuracy: `10/12 = 0.833`
- middle-required items after metadata correction: `4`
- contaminated middle-required items: `2`
  - `syn2_mid_color_flash`
  - `syn2_mid_text_flash_word`
- discriminating middle-required items that still fail without the middle:
  - `syn2_mid_color_ever_green`
  - `syn2_mid_text_ever_bravo`

Metadata fixes triggered by the ablation:

- `syn2_flicker_change_type`, `syn2_flicker_layout`, and
  `syn2_small_object_motion` were mislabeled as not solvable from first and
  last frames
- `syn2_color_swap_event` was mislabeled as requiring middle frames even though
  the clip endpoints already reveal the event

Most important contradiction:

- on the same `synthetic_mid_text_flash` clip, dense and the ablated runs show
  that `syn2_mid_text_flash_word` can be answered as `BRAVO` without the middle
  frames, while `syn2_mid_text_ever_bravo` fails without the middle frames
- that means the former item is contaminated by prompt structure or text prior,
  while the latter remains a useful temporal-necessity item

## Interpretation

The v2 suite is better than v1, but its raw `11/12` cached headline still
overcounts true cache safety.

What the ablation proved:

- the suite now has two genuinely discriminating middle-dependent items
- the first canonical cached failure, `syn2_mid_text_ever_bravo`, remains real
- at least two apparent v2 passes are not trustworthy as temporal evidence

What got weaker:

- `syn2_mid_color_flash` and `syn2_mid_text_flash_word` should not be used as
  primary threshold-sweep items until they are rewritten or replaced
- the broader v2 pass count should not be interpreted as if all middle-required
  items were visually grounded

Immediate consequence:

- use the discriminating subset, not the full v2 headline, when choosing the
  next threshold and refresh experiments
- add more divergence-capable items, especially natural-video items, before
  treating the local Track A suite as a strong reproduction substrate

## Links

- [research/prompt_bank/local_suite_v2.toml](../../prompt_bank/local_suite_v2.toml)
- [research/experiments/2026/2026-04-13-track-a-local-pilot-v2.md](2026-04-13-track-a-local-pilot-v2.md)
