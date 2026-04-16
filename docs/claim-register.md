# Whitepaper Claim Register

This file freezes the imported whitepaper targets that this repo is trying to
reproduce.

It exists because the imported whitepaper markdown contains internal
inconsistencies. Without a frozen claim register, "did we reproduce the
whitepaper?" is ambiguous.

Canonical imported references:

- **Original whitepaper**: [seed/whitepaper/whitepaper.md](../seed/whitepaper/whitepaper.md)
  — the frozen target this repo was initially built against.
- **Revised whitepaper (2026-04-16)**: [seed/whitepaper/whitepaper-revised-2026-04-16.md](../seed/whitepaper/whitepaper-revised-2026-04-16.md)
  — adds VideoMME, Gemma 4 cross-arch, wall-clock, strict-parse audit,
  and an expanded comparison table. Imported as seed provenance per
  [research/experiments/2026/2026-04-16-seed-audit-revised-whitepaper.md](../research/experiments/2026/2026-04-16-seed-audit-revised-whitepaper.md).

The repo is canonically targeting **both**: the original WP-2.1 through
WP-5 claims remain active, PLUS the new WP-2.7 through WP-5.1 claims
from the revised whitepaper (registered below). Claims from the revised
whitepaper are treated with the same "useful hypotheses, not trusted
claims" epistemics as the original.

Repo rule:

- use this register, not ad hoc readings of either whitepaper, when
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
| | | | |
| **From revised whitepaper (2026-04-16)** | | | |
| `WP-2.7` | VideoMME evaluation (Qwen 100% on 300q; Gemma 4 90%/−3.3% on 60q) | local reproduction requires VideoMME lane + at minimum Qwen evaluation at 32 frames | generalized reproduction target |
| `WP-2.8` | Strict-parse audit (413 Qwen items, 0 parse failures, byte-identical) | our local parser already shows 0 failures on our saved slices (30 TOMATO + 54 MVBench = 84 items); scaling to 413+ is the remaining step | generalized reproduction target |
| `WP-2.9` | Cross-architecture generalization (windowed attention → exact; global attention → approximate) | requires a second architecture family (Gemma 4 4B on M3 Air is the candidate; not a direct reproduction of sam's 26B) | generalized reproduction target |
| `WP-2.10` | Thinking-amplification finding (agreement drops from 82% → 58% with thinking enabled on Gemma 4) | requires Gemma 4 thinking-on/off comparison | deferred reproduction target |
| `WP-4.1` | Wall-clock throughput (M5 Max: 6.0× ViT, 4.2× E2E, 130 fps on 32-frame conferencing) | NOT directly reproducible on M3 Air 16GB; a local Track B harness would produce different absolute numbers on different hardware | generalized reproduction target (hardware-conditioned) |
| `WP-5.1` | Composition projection (~175× with TurboQuant) | projected, not measured, even by sam; explicitly marked as future work in their §5 | explicitly gated |

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
