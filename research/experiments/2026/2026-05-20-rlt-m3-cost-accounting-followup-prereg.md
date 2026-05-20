# 2026-05-20 RLT/Gemma M3 cost-accounting follow-up preregistration

## Status

Executed extended tier in commit `352170d`.

Executable:

```bash
scripts/run_rlt_m3_cost_accounting_followup.sh --dry-run
```

Default artifact root:

```text
research/experiments/2026/artifacts/rlt_m3_cost_accounting_followup/
```

Primary result artifact:

```text
research/experiments/2026/artifacts/rlt_m3_cost_accounting_followup/cost_model_fit_n19.json
```

## Execution Result

The extended queue completed all `28` planned commands (`queue_summary.json`:
`completed=true`, `tier=extended`). It adds eight rows to the previous
`n=11` Gemma cost-accounting table and refits the prefill+vision stage model at
`n=19`.

### Preregistered Verdicts

- **Stage-cost calibration accepted.** The prefill+vision ceiling keeps
  `R^2=0.97097`, mean absolute relative error `1.72%`, and max absolute
  relative error `7.85%` across rows spanning observed `0.984x-1.779x` E2E.
  The weaker prefill-only fit (`R^2=0.333`, MARE `5.48%`) confirms that the
  model needs the stage decomposition rather than token count alone.
- **VideoMME-short keep-rate bracket accepted for timing and parsed-choice
  fidelity, inconclusive for quality tradeoff.** `kr=0.3` lands `1.133x`
  E2E; `kr=0.7` lands `1.121x`; both are `20/20` parsed-choice identical to
  dense with `0.000` accuracy delta and zero parse-failure delta. The expected
  "lower keep-rate causes churn" pattern did not appear at `n=20`, so this is
  not a resolved quality Pareto curve.
- **MVBench hosted extension is timing evidence only.** `kr=0.3` and `kr=0.7`
  both preserve aggregate accuracy point estimate at `+0.019`, but choice
  agreement is only `0.630`, parse-failure delta is `+2`, and four buckets fail
  the bucket-quality gate.
- **Composition extension is boundary evidence only.** VideoMME-short
  composition reaches `1.145x` with `0.75` choice agreement and `-0.050`
  accuracy delta; TOMATO composition reaches `1.065x` with `0.533` choice
  agreement and `+0.067` accuracy delta. Both support the cost model; neither
  is a raw-output-identity row.

### Row Summary

| row | n | E2E | predicted | relative error | accuracy delta | choice agreement | interpretation |
|---|---:|---:|---:|---:|---:|---:|---|
| VideoMME-short no admission | 20 | `1.009x` | `1.010x` | `-0.1%` | `0.000` | `1.000` | denominator control |
| VideoMME-short admission `kr=0.7` | 20 | `1.121x` | `1.129x` | `-0.8%` | `0.000` | `1.000` | parsed-choice clean |
| VideoMME-short admission `kr=0.3` | 20 | `1.133x` | `1.140x` | `-0.6%` | `0.000` | `1.000` | parsed-choice clean |
| VideoMME-short composition `kr=0.5` | 20 | `1.145x` | `1.139x` | `+0.5%` | `-0.050` | `0.750` | timing/boundary |
| MVBench hosted no admission | 54 | `1.030x` | `1.030x` | `-0.0%` | `0.000` | `1.000` | raw-output control |
| MVBench hosted admission `kr=0.7` | 54 | `1.198x` | `1.205x` | `-0.6%` | `+0.019` | `0.630` | timing only |
| MVBench hosted admission `kr=0.3` | 54 | `1.207x` | `1.210x` | `-0.3%` | `+0.019` | `0.630` | timing only |
| TOMATO composition `kr=0.5` | 30 | `1.065x` | `1.107x` | `-3.8%` | `+0.067` | `0.533` | timing/boundary |

### Interpretation Update

No more M3 MLX is needed for this closeout. The useful next local step is
documentation and paper framing: describe the result as stage-cost accounting
with explicit paired-fidelity gates, not as query-aware routing or universal
random-pruning superiority.

## Motivation

The `2026-05-19/20` Gemma run made the closeout claim sharper: end-to-end
speedup follows the runtime stages that are actually shortened. The strongest
clean row is VideoMME-short random-valid C-VISION plus RLT placeholder
admission at `kr=0.5`: `1.098x` E2E with parsed-choice agreement `20/20` and
`0.000` accuracy delta. That row is the safest M3 target for a small Pareto
check.

This follow-up is deliberately **not** a query-aware-routing experiment. It
does not run text routing, active repair, Q0b/Q1/Q1b/Q1c, or learned routing.
It only asks whether the stage-cost model remains calibrated when we move the
admission keep-rate around the clean VideoMME-short operating point.

## Core Tier

Run VideoMME-short with:

- dense reference;
- random-valid C-VISION with admission disabled;
- random-valid C-VISION with RLT placeholder admission at `kr=0.3`;
- random-valid C-VISION with RLT placeholder admission at `kr=0.7`;
- paired full-composition analyzer for each non-dense row;
- paired cost-model analyzer for each non-dense row;
- cost-model refit that combines the existing `n=11` rows with the new rows.

Existing `kr=0.5` is already present in
`research/experiments/2026/artifacts/rlt_query_routing_cost_accounting/videomme_short/`.
The new `kr=0.3` and `kr=0.7` rows bracket that operating point.

### Core Hypothesis

Lower admission keep-rate should reduce multimodal-prefill cost more than
`kr=0.5` but should increase answer churn or parse risk. Higher admission
keep-rate should preserve answers better than `kr=0.5` but should give less
speed. The prefill+vision stage-cost model should predict E2E speedup within
the existing tolerance.

### Core Acceptance

Accept the cost-model calibration if every new VideoMME-short row has absolute
relative E2E prediction error `<= 0.08`.

Promote a row as a fidelity-clean operating point only if:

- parsed-choice agreement remains `1.000`;
- accuracy delta is `0.000` on the `n=20` slice;
- parse-failure delta is zero;
- bucket/e2e gates pass in `analyze_gemma_full_composition.py`.

Otherwise, keep the row as timing evidence only.

### Core Rejection

Reject the keep-rate Pareto hypothesis if:

- E2E speed does not move monotonically with measured placeholder/prefill
  reduction;
- any new row misses the stage-cost prediction by more than `8%` absolute
  relative error under clean timing provenance;
- the `kr=0.7` row is not at least as stable as `kr=0.3`.

### Core Inconclusive

Mark inconclusive if timing follows the model but `n=20` quality is too coarse
to separate neighboring keep-rates, or if M3 thermal drift dominates the paired
ABBA run.

## Extended Tier

Set:

```bash
M3_FOLLOWUP_TIER=extended scripts/run_rlt_m3_cost_accounting_followup.sh --dry-run
```

The extended tier adds:

- MVBench hosted-dev random-valid C-VISION admission bracket at `kr=0.3` and
  `kr=0.7`;
- TOMATO motion-dev RLT composition at `kr=0.5`;
- VideoMME-short RLT composition at `kr=0.5`.

These are reviewer-response cells, not blockers. Use them only if we need a
broader cost-model stress test before M5.

## Resource Budget

- Core tier full run: about `1.3 h` expected on the M3-class local setup.
- Extended tier full run: about `4.0 h` expected.
- Smoke: set `N_ITEMS=1`; the launcher lowers expected-item and bootstrap
  counts automatically.

The wrapper keeps `MLX_MEMORY_LIMIT_GB=12`, `RSS_GUARD_MB=9000`, `8` frames,
and ABBA pairing. It scope-locks command-line overrides so this cannot silently
turn into query routing or a broad composition queue.

## Interpretation Rules

- Do not describe any new row as "lossless" unless raw output identity is
  audited separately. The default fidelity gate is parsed-choice identity.
- Do not convert a timing row with bucket-quality failures into a paper
  headline.
- Do not tune query-aware policies based on these results on this branch.
- If the model fit weakens, update the closeout note and decision log; a
  falsification is useful science here.
