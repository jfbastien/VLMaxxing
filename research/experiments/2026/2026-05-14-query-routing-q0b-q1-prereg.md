# 2026-05-14 query-routing Q0b/Q1 implementation prereg

Status: **preregistered / implemented, not yet measured**.

This note records the first executable branch for the query-aware visual
routing follow-on paper. It intentionally stops at Q0b and Q1. QuoTA-style
scalar-query allocation, repair passes, one-step active escalation, and
cost-model calibration are deferred until these gates say the operator idea is
worth pursuing.

## Hypotheses

H0b. Harness separation is valid.

- Dense-equivalent replay (`prune_placeholders=none`,
  `vision_tower_keep_rate=1.0`) must match the dense reference on paired
  choice, parse status, and accuracy.
- C-VISION-only replay (`prune_placeholders=none`,
  `vision_tower_keep_rate<1.0`, `vision_tower_score_mode=rlt_topk`) must
  keep dense prompt placeholders while exposing encoder kept/valid ledgers.
- Falsify: dense-equivalence fails, placeholder bypass is missing, encoder
  ledgers are absent for C-VISION rows, or source pairing is incomplete.

H1. Q1 typed evidence operators are only worth pursuing if they beat trivial
matched-budget controls.

- Primary local target: MVBench dev (`moving_attribute` +
  `object_interaction` are the motivation buckets, but full-manifest rows are
  retained to expose negative transfer).
- Arms implemented for the first branch:
  `redundancy_topk` at kr=0.5, higher-K RLT at kr=0.7,
  `rlt_topk_static_floor` with stride 4, `fixed_uniform`, and
  `random_valid_position` with seeds 11/23/37.
- Accept for proceed-to-Q2: a typed operator improves the primary pooled
  target against fixed/random/higher-K controls at matched budget without
  failing aggregate parse or quality gates.
- Falsify standalone operator direction: fixed/random/higher-K matches or
  beats the typed operator, or Q0b shows the issue is budget/admission-only.

## Implemented commands

Autonomous local launch, MVBench-first:

```bash
scripts/run_rlt_query_routing_first_branch.sh
```

Broader local sweep after MVBench survives:

```bash
QUERY_ROUTING_BENCHMARKS=mvbench,tomato,videomme \
  scripts/run_rlt_query_routing_first_branch.sh --max-planned-hours 80
```

Local M3 setup is the same paper setup used for the Round-17 through Round-20
Gemma experiments: `$HOME/models/gemma-4-e4b-it-4bit` with 8 frames and
Gemma 4 E4B / mlx-vlm. The local model directory was confirmed on 2026-05-14.

M5 is not the first query-routing discovery machine. The first paper-2 branch
should run on the same local E4B substrate first, because Q0b/Q1 are
publish-or-kill diagnostics rather than a scale-confirmation result. If Q0b/Q1
survive on M3 and a later M5 replication is desired, use the same wrapper with
`GEMMA_MODEL_PATH` set to Sam's verified local Gemma-family model directory and
record the exact model id/config in the run note. Do not assume another user's
home directory and do not switch model families for this paper.

The separate VLMaxxing+RLT M5 scale-confirmation queue is
`scripts/run_rlt_m5_scale_confirmation.sh`; it intentionally does not pass
query-routing flags.

## New infrastructure

- `scripts/analyze_gemma_full_composition.py` now accepts four direct-pair
  arm kinds: `dense_equivalent`, `rlt_admission_only`, `rlt_cvision_only`, and
  `rlt_admission_plus_rlt_cvision`.
- The analyzer hard-fails missing placeholder ledgers and hard-fails missing
  encoder kept/valid ledgers for C-VISION rows.
- Paired outputs include correctness taxonomy, parse taxonomy,
  placeholder reduction, vision reduction, and both dense/composed metadata.
- `scripts/run_novelty_pruning_gemma.py` adds Q1 C-VISION score modes:
  `rlt_topk_static_floor`, `fixed_uniform`, and `random_valid`.
- `src/codec_through/query_routing.py` contains deterministic operator
  arithmetic and the Q1 smoke-testable budget ledgers.
- `scripts/run_rlt_followup_queue.py` adds `--run-query-routing-q0b`,
  `--run-query-routing-q1`, and `--query-routing-benchmarks`.
- Queue summaries include `paper_feedback` so the supervisor constrains what
  the paper is allowed to say without editing paper files.
- Q1 is gated on the complete Q0b diagnostic grid, not just the
  dense-equivalence smoke. The grid must include dense-equivalent,
  admission-only, C-VISION-only at kr=0.5/1.0, and full composition at
  kr=0.5/0.7/0.85/1.0 for each requested benchmark.
- Q1 emits an aggregate typed-vs-control verdict. Static-floor (the first
  typed operator) must beat matched-budget redundancy/fixed/random controls on
  the preregistered target before the supervisor permits a "proceed to Q2b"
  scalar-query baseline claim.

## Expected result

The likely positive outcome is not yet a standalone paper claim. The expected
best case is: Q0b proves the harness, static-floor or higher-K improves
MVBench attribute/interaction failures more than fixed/random, and the queue
earns a narrow "proceed to scalar-query baseline" verdict. The WOW only
becomes paper-grade after Q2b shows typed evidence operators beat scalar
query-budget allocation under total-cost accounting.

The likely negative outcome is also useful: if fixed/random/higher-K matches
the typed operator, the query-aware paper should pivot toward budget
scheduling or stay as a VLMaxxing appendix.
