# 2026-05-14 query-routing Q0b/Q1 implementation prereg

Status: **Q0b/Q1/Q1b measured; Q1c admission-scheduler follow-up implemented,
not yet measured**.

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

## 2026-05-15 Q0b/Q1 result

Outcome: **Q1 falsified the first typed-operator branch, but not the broader
planner question.**

Q0b showed the harness is sound:

- Dense-equivalent replay matched dense exactly on 30/30 MVBench dev items
  (`accuracy_delta=0.000`, choice agreement `1.000`).
- C-VISION-only replay at `vision_keep_rate=1.0` also matched dense exactly
  while exercising the patched C-VISION path.
- Full `kr=1.0` still harmed the same three target items as admission-only,
  because prompt admission remained active. This points at prompt-admission
  scheduling / interaction, not a C-VISION oracle failure.

Q1 then ran C-VISION-only operators at matched budget. The controls beat the
typed operators:

- `fixed_uniform`: `1.283x` E2E, aggregate `Delta acc=-0.033`.
- `random_valid(seed=11)`: `1.254x` E2E, aggregate `Delta acc=0.000`.
- Best typed branch (`rlt_topk_static_floor`, stride 4): aggregate
  `Delta acc=-0.200`, target-pool `Delta acc=-0.333`.
- RLT redundancy at higher K (`kr=0.7`) improved quality but was still slower
  and no better than the best fixed/random controls.

The queue correctly set `proceed_to_q2_scalar_query_baseline=false`. That
falsifies the current static-floor / redundancy-top-k typed operator branch.
It does **not** falsify query planning in general because Q1 did not test:
class-conditional policy selection, endpoint anchors, admission-on/off
scheduling for the coverage controls, global frame-token allocation, scalar
query allocation, or one-step active repair.

## Q1b follow-up preregistration

Q1b is a narrow post-negative diagnostic. It is not a planner launch and does
not authorize QuoTA, active repair, or full cost-model work. It asks whether
the Q1 negative result still leaves measurable headroom for simple planning.

H1b. Endpoint anchoring has headroom.

- Arm: `rlt_topk_endpoint_anchor`, C-VISION-only, `kr=0.5`.
- Mechanism: keep first and last frames dense, then spend the remaining
  video-level encoder-position budget by RLT score.
- Runtime note: unlike Q1's strict per-frame K operators, this uses the
  variable-K C-VISION wrapper path: rows with different K are run separately
  through the remaining vision-tower layers and scatter-backed in original
  order. Total wall-clock is therefore part of the result, not assumed.
- Accept: target-pool accuracy delta at least the best matched control and
  E2E speedup > 1.0.
- Falsify: target-pool delta below `random_valid(seed=11)` or no positive E2E.

H2b. The best coverage control is admission-sensitive.

- Arms: `random_valid(seed=11)` and `fixed_uniform` with prompt admission
  toggled on (`prune_placeholders=rlt`) at the same C-VISION budget.
- Accept admission as useful only if it preserves the best control's
  target-pool delta while improving E2E.
- Falsify: admission reintroduces the moving_attribute/object_interaction
  harms seen in Q0b.

H3b. A tiny class-conditional dense fallback can repair the control failure.

- Arms: `random_valid(seed=11)` and `fixed_uniform` C-VISION-only with
  `group_vision_keep_rates=action_localization=1.0`.
- Motivation: the best Q1 control's remaining aggregate loss was concentrated
  in one action_localization flip, not in the original target groups.
- Accept: aggregate accuracy delta improves or stays flat versus the base
  control, parse delta stays clean, and E2E remains > `1.10x`.
- Falsify: dense fallback does not improve quality or collapses speed.

Q1b outputs are diagnostic only. A positive result earns a fresh held-out
planner experiment; a negative result leaves query routing as a VLMaxxing
appendix and points future work at learned/scalar query allocation instead of
hand-built typed operators.

## 2026-05-18 Q1b result

Outcome: **static vision-mask scoring is closed for this branch; admission
scheduling remains open.**

Q1b tested the three holes Q1 had left open:

- `rlt_topk_endpoint_anchor`: `1.184x` E2E, aggregate
  `Delta acc=-0.200`, target-pool `Delta acc=-0.250`. This failed in the same
  range as the previous typed masks, so endpoint anchoring is not the missing
  C-VISION scorer.
- `fixed_uniform + admission`: `1.457x` E2E, aggregate
  `Delta acc=-0.167`, target-pool `Delta acc=-0.417`. The CI excludes zero
  on aggregate accuracy loss.
- `random_valid(seed=11) + admission`: `1.458x` E2E, aggregate
  `Delta acc=-0.067`, target-pool `Delta acc=-0.250`.
- `fixed_uniform + actionloc_dense`: `1.197x` E2E, aggregate
  `Delta acc=0.000`.
- `random_valid(seed=11) + actionloc_dense`: `1.140x` E2E, aggregate
  `Delta acc=+0.033`.

Interpretation: Q1's random/fixed controls were not winning because random
coverage is intrinsically smart. They were winning because prompt admission
was off. When prompt admission is turned on, the same content-concentrated
damage returns, especially `moving_attribute`. The next small experiment is
therefore not another static vision-mask scorer. It is an admission scheduler:
keep coverage-first C-VISION, disable prompt admission by default, and admit
only low-risk groups.

## Q1c admission-scheduler preregistration

Q1c is a narrow exploratory dev follow-up. It is still not a QuoTA run, not a
repair-pass run, and not a full planner. It asks whether the already-measured
Q1/Q1b rows contain a real policy frontier: can prompt admission be used as a
scheduled physical operator instead of an always-on pruning step?

The design is coverage-first:

- C-VISION scorer: `random_valid(seed=11)`.
- C-VISION default keep-rate: `kr=0.5`.
- Prompt admission default: disabled via global `--prune-placeholders none`.
- Prompt admission enabled only for preregistered low-risk groups via
  `group_prune_placeholders=fine_grained_action=rlt,moving_direction=rlt`.

Important implementation detail: RLT prompt admission is thresholded, not
fixed-K. Therefore `--keep-rate 1.0` is **not** a no-admission setting for
`prune_placeholders=rlt`; Q1c needs explicit group-level placeholder-pruning
scheduling.

H1c. Safe admission beats the Q1 random coverage baseline.

- Arm: `query_q1c_mvbench_random_seed11_safe_admission`.
- Accept: aggregate accuracy delta and target-pool delta are at least as good
  as Q1 `random_valid(seed=11)`, parse delta remains clean, and E2E is higher
  than Q1 `random_valid(seed=11)`.
- Falsify: any accuracy/target regression relative to Q1 random coverage, or
  no E2E improvement.

H2c. Safe admission composes with the action-localization dense fallback.

- Arm:
  `query_q1c_mvbench_random_seed11_safe_admission_actionloc_dense`.
- Difference from H1c: add
  `group_vision_keep_rates=action_localization=1.0`.
- Accept: aggregate accuracy delta and target-pool delta are at least as good
  as Q1b `random_valid(seed=11) + actionloc_dense`, parse delta remains clean,
  and E2E is higher than that Q1b dense-fallback baseline.
- Falsify: the dense fallback removes the admission speed gain, or safe
  admission reintroduces target-bucket damage.

Decision rule: if either arm passes, run exactly one held-out confirmation
using the winning policy before changing the paper-2 status. If both fail,
query routing remains an appendix negative result; the next serious revival
must use a qualitatively different mechanism such as scalar query allocation
or one-step active repair.
