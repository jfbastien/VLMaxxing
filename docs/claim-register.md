# Imported Pre-release Claim Register

This file freezes the imported pre-release source targets that this repo may
reproduce, generalize, or keep explicitly imported-only.

It exists because the pre-release source markdown contains internal
inconsistencies. Without a frozen claim register, "did we reproduce the
pre-release source?" is ambiguous.

Canonical imported references:

- **Original pre-release source**: the frozen target this repo was initially built
  against.
- **Revised pre-release source (2026-04-16)**: adds VideoMME, Gemma 4 cross-arch,
  wall-clock, strict-parse audit, and an expanded comparison table. Imported
  and audited in
  [2026-04-16-pre-release-source-audit.md](../research/experiments/2026/2026-04-16-pre-release-source-audit.md).

The raw imported-source files are intentionally absent from the release tree.
This register is the durable source of truth for imported pre-release targets
only; git history preserves the raw imports for forensic review. Paper-facing
claims live in `paper/claim-matrix.md`, phase state lives in
`research/experiments/registry.md`, and local reproduction/import status lives
in `docs/reproduction-status.md`.

This register covers two imported target sets:

- the original WP-2.1 through WP-5 targets
- the revised-source WP-2.7 through WP-5.1 targets registered below

Imported targets are planning targets, not trusted local claims, until this
repo either reproduces them locally, generalizes them with explicit caveats, or
marks them imported-only.

Repo rule:

- use this register, not ad hoc readings of either pre-release source, when
  deciding whether a claim is reproduced, partially reproduced, or still
  imported-only

## Current Imported Inconsistencies

The pre-release source still contains conflicting statements that matter for
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

- mechanism sections in the pre-release source use Qwen `3B` on
  `PyTorch/MPS float32`
- benchmark sections in the pre-release source use Qwen `7B` via `mlx-vlm`
- benchmark reproduction caveats in this repo should therefore focus on subset
  policy, quantization, package versions, and preprocessing rather than on a
  generic `MLX versus PyTorch` mismatch

## Frozen Reproduction Targets

### Original Pre-release Source

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
| `WP-5` | Compression and speed stackup | partial local measured sparse-execution evidence now exists, but the imported compression/speed stackup remains unreproduced | explicitly gated |

### Revised Pre-release Source (2026-04-16)

Claim ID stability: the `WP-*` IDs are semantic labels assigned at import time,
not mirrors of the pre-release source's section numbers. Source sections may
renumber across revisions. For example, source §2.10 was thinking amplification
at import time, but the latest revision uses that section number for hard
spatial pruning. The IDs below are frozen to the registered meaning; newly
imported source claims get new `WP-*` IDs.

| Claim id | Imported target | Current canonical reading | Scope in this repo |
| --- | --- | --- | --- |
| `WP-2.7` | VideoMME evaluation (Qwen 100% on 300q; Gemma 4 90%/−3.3% on 60q) | local VideoMME Qwen lane is now reproduced in generalized form across 8f/16f/32f dev plus 16f holdout; the imported Gemma 26B/60q target remains scale-out evidence, not a strict local reproduction | generalized reproduction target, partially closed locally |
| `WP-2.8` | Strict-parse audit (413 Qwen items, 0 parse failures, byte-identical) | local parser evidence has 0 failures on saved slices (84 exact items plus about 60 motion items with approximate checks); the imported 413-item strict audit remains unreproduced | generalized reproduction target |
| `WP-2.9` | Cross-architecture generalization — **scoped to spectrum, not binary**. The pre-release source §2.7 groups InternVL3 with all-global but §2.9 and §2.10 group it with windowed-attention in the same document (lines 171 / 243). The empirical data (Qwen 100% byte-identical, InternVL3 95% strict, Gemma 4 88% byte-identical) supports a spectrum conditioned on attention-window fraction and pretraining, not a topology-determined binary. | generalized local evidence now exists on Gemma 4 E4B: TOMATO motion passes answer-fidelity gating, MVBench preserves aggregate accuracy but fails strict agreement, and 1.57 Gemma feature-drift geometry shows higher adjacent-frame cosine than Qwen. This is not a strict 26B reproduction. | generalized reproduction target — **scoped, partially closed locally** |
| `WP-2.12` | EgoSchema low-reuse robustness (pre-release source: N=100 Qwen, 100% byte-identical at 29.9% mean token reuse) | This is the imported counterexample to "caching only helps high-reuse content." Local N=30 reproduction on Qwen2.5-VL-7B 4-bit would close the long-form/low-reuse robustness gap; phase 1.43 is preregistered but blocked on the EgoSchema loader and manifest. | blocked phase 1.43 |
| `WP-4.2` | Combined temporal+spatial pipeline, end-to-end measured, 4–5× sustained across 32/64/128 frames (pre-release scale-out source, Gemma 4 26B on M5 Max) | The imported scale-out target is measured rather than projected, but it remains unreproduced locally. Current Qwen2.5-VL-7B 4-bit streaming/composition bridge evidence is bounded, negative-to-near-miss evidence, not a strict reproduction of the imported Gemma 26B/M5 Max scale-out claim. | deferred strict reproduction; bounded local bridge evidence exists |
| `WP-2.10` | Thinking-amplification finding (agreement drops with thinking enabled on Gemma 4) | Requires Gemma 4 thinking-on/off comparison. Supplementary to WP-2.9. | deferred reproduction target |
| `WP-2.11` | Hard spatial pruning (Gemma 4 with token reduction) | new in latest source revision; not in our original import. Local C-VISION now supplies bounded related evidence through measured Gemma sparse-vision execution, but broad sparse-backend and sparse LM prefill remain open. | related local evidence exists; strict imported target remains gated |
| `WP-4.1` | Wall-clock throughput (M5 Max: 6.0× ViT, 4.2× E2E, 130 fps on 32-frame conferencing) | Not directly reproducible on M3 Air 16GB; the local measured sparse-execution harness now provides hardware-conditioned boundary evidence, not the imported M5 throughput claim | generalized reproduction target (hardware-conditioned) |
| `WP-5.1` | Composition projection (~175× with TurboQuant) | projected, not measured, even by the pre-release source; explicitly marked as future work in source §5 | explicitly gated |

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
