# Whitepaper Claim Register

This file freezes the imported whitepaper targets that this repo is trying to
reproduce.

It exists because the imported whitepaper markdown contains internal
inconsistencies. Without a frozen claim register, "did we reproduce the
whitepaper?" is ambiguous.

Canonical imported reference:

- [seed/whitepaper/whitepaper.md](../seed/whitepaper/whitepaper.md)

Repo rule:

- use this register, not ad hoc readings of the imported whitepaper, when
  deciding whether a claim is reproduced, partially reproduced, or still
  imported-only

## Current Imported Inconsistencies

The imported whitepaper still contains conflicting statements that matter for
reproduction planning:

- TOMATO delta:
  - abstract says `Δ = -1.1%` on a `90`-question run
  - benchmark section later reports `+0.0%` plus `100%` agreement on the full
    `1,484`-question TOMATO evaluation
- MVBench delta:
  - abstract says `Δ = +2.5%`
  - benchmark section later reports `+0.0%` and `100%` agreement on the saved
    `160`-question local run
- frame count:
  - benchmark sections describe `8` frames per video
  - limitations section says memory constraints reduced some evaluations to
    `4` frames per video in some settings

Until a cleaner upstream source exists, this repo treats the benchmark sections
and directly inspected predecessor artifacts as more specific than the abstract
wording.

Important runtime distinction:

- mechanism sections in the imported whitepaper use Qwen `3B` on
  `PyTorch/MPS float32`
- benchmark sections in the imported whitepaper use Qwen `7B` via `mlx-vlm`
- benchmark reproduction caveats in this repo should therefore focus on subset
  policy, quantization, package versions, and preprocessing rather than on a
  generic `MLX versus PyTorch` mismatch

## Frozen Reproduction Targets

| Claim id | Imported target | Current canonical reading | Scope in this repo |
| --- | --- | --- | --- |
| `WP-2.1` | Exact repeated-image identity | repeated encodes of the same image should produce identical vision features | direct local reproduction target |
| `WP-2.2` | Locality under partial change | a localized perturbation should damage nearby tokens much more than far-field tokens | direct local reproduction target |
| `WP-2.3` | Localized motion preserves embeddings | small within-block shifts should keep token similarity high | direct local reproduction target |
| `WP-2.4` | Scored real-video slice | a small real-video end-to-end quality slice should largely preserve dense answers under caching | generalized local reproduction target |
| `WP-2.5` | TOMATO agreement | local reproduction aims at a documented subset or partial reproduction on the available hardware, not an implied exact rerun of the full upstream setup | generalized local reproduction target |
| `WP-2.6` | MVBench agreement | local reproduction aims at a documented subset or partial reproduction on the available hardware | generalized local reproduction target |
| `WP-3.1` | Default thresholds `(3, 8)` | use these as the default imported planner thresholds unless a preregistered sweep says otherwise | direct local reproduction target |
| `WP-3.3` | Refresh-interval drift tolerance | imported `14`-frame tolerance remains external until local sweep exists | direct local reproduction target |
| `WP-4` | Q-table pre-filter correlation | useful supporting reproduction target, not the first milestone | deferred reproduction target |
| `WP-5` | Compression and speed stackup | out of scope until Track B evidence exists on this stack | explicitly gated |

## Strict Versus Generalized Reproduction

This repo distinguishes two valid reproduction modes:

- strict reproduction:
  - same model family and precision path
  - same clip or benchmark assets
  - same or equivalent evaluation cardinality
  - close numerical agreement
- generalized reproduction:
  - same method family
  - same content classes or benchmark structure
  - local hardware-aware subset or precision changes stated explicitly
  - claim framed as "method works on our stack" rather than "exact rerun"

Given the current Apple M3 Air `16 GB` target, generalized reproduction is the
default for TOMATO and MVBench unless proven otherwise.

## Usage

When writing experiment notes or plan updates:

1. cite the relevant `WP-*` claim id
2. state whether the run is strict or generalized reproduction
3. if the imported target is inconsistent, say which canonical reading was used
