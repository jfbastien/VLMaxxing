# Phase 1.45: Benchmark Parser and Contrast Diagnostics

## Preregistration

Objective:

- diagnose the current TOMATO versus MVBench contrast on the existing local
  benchmark artifacts before spending more runtime budget on larger reruns

Claim register targets:

- `WP-2.5`
- `WP-2.6`

Reproduction mode:

- generalized reproduction support analysis

Track:

- A

Hypotheses:

- re-scoring the current local benchmark artifacts under a loose
  `parse-failure -> A` policy will not materially change the local TOMATO or
  MVBench summaries because the saved local runs already had zero parse
  failures
- the apparent `+1` cached-over-dense edge on the `54`-item MVBench hosted
  slice will not survive a paired significance check
- direct predecessor artifact inspection will show why `100%` agreement is not
  a safe headline target for strict-parser local reproduction

Acceptance band:

- local strict-versus-loose rescoring is identical or nearly identical because
  parse failures stay at `0`
- the MVBench aggregate difference is shown to be statistically indistinguishable
  from zero under an exact paired test
- the note produces a concrete next-step order for benchmark follow-up

Rejection band:

- local rescoring materially changes the current local summaries, implying that
  the saved benchmark artifacts themselves were not parser-stable
- the analysis cannot be reproduced from checked-in artifacts alone

Notes:

- this is an artifact-analysis phase, not a new model run
- coarse reuse-bin analysis still uses the current raw `reuse_ratio_mean`
  values, which are not yet pad-masked and therefore remain exploratory

## Execution

Run date:

- 2026-04-14

Artifact:

- [phase1_45_benchmark_diagnostics.json](artifacts/phase1_45_benchmark_diagnostics.json)

Historical command. The diagnostic script was removed from the OSS release tree;
the checked artifact below is retained as the durable record:

```bash
uv run python <removed-pre-release-diagnostic-script> \
  --output research/experiments/2026/artifacts/phase1_45_benchmark_diagnostics.json
```

Inputs:

- local TOMATO subset:
  [phase1_4_run_b_subset30.json](artifacts/phase1_4_run_b_subset30.json)
- local MVBench subset:
  [phase1_5_run_b_subset54.json](artifacts/phase1_5_run_b_subset54.json)
- predecessor TOMATO results: pre-release imported artifact, removed from the
  OSS tree and summarized in [docs/reproduction-status.md](../../../docs/reproduction-status.md)
- predecessor MVBench results: pre-release imported artifact, removed from the
  OSS tree and summarized in [docs/reproduction-status.md](../../../docs/reproduction-status.md)

## Result

Preregistration outcome:

- Accepted

Observed outcome:

- local strict-versus-loose rescoring was identical on both benchmark slices:
  - TOMATO `30`-item subset:
    - strict agreement `0.833`
    - loose agreement `0.833`
    - dense parse failures `0`
    - cached parse failures `0`
  - MVBench `54`-item subset:
    - strict agreement `0.870`
    - loose agreement `0.870`
    - dense parse failures `0`
    - cached parse failures `0`
- the apparent `+1` cached edge on MVBench is sampling noise:
  - cached improves dense on `3` items
  - cached regresses against dense on `2` items
  - exact paired test `p = 1.0`
- Wilson `95%` intervals make the current benchmark uncertainty explicit:
  - TOMATO dense `0.300`, CI `[0.167, 0.479]`
  - TOMATO cached `0.233`, CI `[0.118, 0.409]`
  - TOMATO agreement `0.833`, CI `[0.664, 0.927]`
  - MVBench dense `0.630`, CI `[0.496, 0.746]`
  - MVBench cached `0.648`, CI `[0.515, 0.762]`
  - MVBench agreement `0.870`, CI `[0.756, 0.936]`
- predecessor artifact inspection shows suspiciously perfect agreement:
  - TOMATO saved run:
    - `1,484 / 1,484` agreement
    - dense accuracy `329 / 1,484 = 0.222`
    - cached accuracy `329 / 1,484 = 0.222`
    - `1,155` items are both wrong while still marked `match = true`
    - the preserved JSON is lossy:
      it records only `split`, `gt`, `bl_correct`, `ca_correct`, `match`, and
      `reuse`, so the checked-in artifact does not let this repo audit the
      parsed dense or cached answer letters directly
  - MVBench saved run:
    - `160 / 160` agreement
    - dense accuracy `64 / 160 = 0.400`
    - cached accuracy `64 / 160 = 0.400`
    - `96` items are both wrong while still marked `match = true`
- coarse raw reuse-bin summaries do not yet explain the benchmark contrast cleanly:
  - TOMATO high raw-reuse bin `0.85-1.0`: agreement `0.857` on `21` items
  - MVBench high raw-reuse bin `0.85-1.0`: agreement `0.850` on `20` items
  - MVBench stays broadly similar across the current raw bins, while TOMATO has
    small-N instability in the lower-reuse bins

## Interpretation

Three things are now established.

First, the saved local TOMATO and MVBench subsets show no evidence of
parser-driven differences.

- strict and loose local rescoring are identical
- both local slices had zero parse failures
- future local disagreement analysis should therefore focus on planner
  behavior, subset composition, and preprocessing, not on the tested local
  parser choice

Second, the predecessor `100%` agreement headline is not a safe strict-parser
target for this repo.

- the predecessor audit already documented `option A` fallback on parse failure
- direct inspection of the saved predecessor benchmark JSON shows perfect dense
  versus cached agreement together with large numbers of both-wrong matched
  items
- on TOMATO, the checked-in saved artifact does not preserve parsed baseline or
  cached answer letters at all, so parser inflation remains plausible but
  cannot be quantified directly from the preserved JSON alone
- without raw predecessor generations, this repo cannot quantify exactly how
  much of the saved `100%` is parser inflation versus genuine method stability
- that uncertainty is now part of the reproduction contract and should stay
  explicit in future notes

Third, the current TOMATO versus MVBench contrast is real, but the cause is not
yet isolated.

- the contrast is not explained by the tested local parser choice on these
  saved subsets
- the current raw reuse bins are still exploratory because the benchmark runner
  reports reuse over padded frames
- the right next controls are therefore benchmark-path identity, pad-masked
  reuse accounting, and targeted TOMATO diagnosis on the disagreement items

## Consequences

- stop describing the MVBench `+1` cached edge as evidence for improvement
- stop treating imported `100%` agreement as the main benchmark target under
  strict parsing
- treat the current local benchmark lane as honest-but-weaker evidence that
  still needs causal diagnosis before larger reruns

## Links

- [docs/claim-register.md](../../../docs/claim-register.md)
- [docs/reproduction-status.md](../../../docs/reproduction-status.md)
- [docs/benchmark-setup.md](../../../docs/benchmark-setup.md)
