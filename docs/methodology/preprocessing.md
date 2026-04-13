# Preprocessing Contract

This file freezes the preprocessing choices that can otherwise quietly distort
temporal-reuse results.

It exists because preprocessing is part of the scientific method here, not a
mere implementation detail.

## Scope

Every decision-worthy experiment must log:

- decode backend
- colorspace conversion
- resize policy
- padding policy
- whether padded regions are excluded from reuse accounting
- frame sampling mode

If one of these is left implicit, the result is provisional.

## Decode Backends

Treat these as different conditions:

- `ffmpeg-software`
- `ffmpeg-videotoolbox`
- `pyav`
- any later custom or MLX-native path

Do not mix them inside one trend line without saying so.

Current repo rule:

- Track A pilot work may start with `ffmpeg-software`
- Track B timing claims must clearly separate temp-image reference paths from
  in-memory decode paths

## Color And Pixel Domain

Current default working domain:

- decode to RGB for the pixel-diff baseline

Why:

- the current Track A planner is an RGB proxy for decoded-frame change
- this matches what the current model path actually consumes after decode

What this does not mean:

- RGB diff is not codec metadata
- RGB diff is not a literal `MV=0 + CBF=0` test

Later codec-side work must say exactly when it stops using this proxy.

## Resize Policy

Current default policy for local bring-up:

- preserve aspect ratio
- constrain the longer side to the processor-compatible working size
- only pad when the downstream processor or model path requires it

Do not stretch frames anisotropically for the main science path.

## Padding Policy

Square padding is dangerous for this project because it creates trivially static
border regions.

Current rule:

- if padding is present, reuse metrics must exclude padded blocks from the main
  reported reuse ratio
- if a helper still emits padded frames, record both:
  - raw reuse ratio over all blocks
  - masked reuse ratio over the active image region

Until masked accounting exists end to end, padded-frame reuse ratios are only
bring-up signals, not paper-grade evidence.

## Sampling Modes

Sampling mode is a first-class experiment variable.

Use one of these exact names:

- `contiguous_window`
- `uniform_global`

Definitions:

- `contiguous_window`: adjacent or near-adjacent frames from a local temporal
  span; this is the default for mechanism experiments and anything codec-like
- `uniform_global`: evenly sampled frames across a longer clip; use this only
  for benchmark comparability or explicit ablations

Do not combine these into one claim.

Current repo rule:

- Phase 0.5, Phase 0.75, Phase 1.0, and the initial Track A pilot use
  `contiguous_window`
- `uniform_global` is benchmark-comparability mode and must be labeled as such

## Output Paths

Current helper split:

- `src/codec_through/ffmpeg.extract_frames(...)` is reference/debug only
- `src/codec_through/ffmpeg.extract_frames_single_pass(...)` is better for
  mechanism work, but still uses temp PNGs and is not a clean timing path

Track B requirement:

- timing-sensitive runs need an in-memory decode path

## Prompt And Answer-Key Contract

Prompt text and answer keys are part of preprocessing in the broad sense: they
define what the model is being asked to preserve.

Use versioned prompt banks under:

- [research/prompt_bank](../../research/prompt_bank/)

If a prompt bank changes, the experiment note must name the new version.

## Minimum Record Per Experiment

Each experiment note should state:

- decode backend
- colorspace
- resize rule
- padding rule
- whether reuse accounting was pad-masked
- sampling mode
- prompt-bank version
