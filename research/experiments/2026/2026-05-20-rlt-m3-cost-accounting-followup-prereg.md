# 2026-05-20 RLT/Gemma M3 cost-accounting follow-up preregistration

## Status

Preregistered launcher; not yet executed as a full MLX run in this note.

Executable:

```bash
scripts/run_rlt_m3_cost_accounting_followup.sh --dry-run
```

Default artifact root:

```text
research/experiments/2026/artifacts/rlt_m3_cost_accounting_followup/
```

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
