# 2026-05-09 Query-Aware Visual Routing Plan

Status: hypothesis and design note only. Do not implement on the RLT/VLMaxxing
closure branch.

## Motivation

Round-19 RLT/VLMaxxing full-composition rescue left one sharp failure mode:
MVBench `moving_attribute` did not recover when both prompt admission and
C-VISION keep-rate were raised to `0.85`. That falsifies the simple rescue
hypothesis "motion-only RLT just needs more K." The better hypothesis is that
attribute questions need a different visual evidence plan: static appearance
detail, endpoint frames, and object-bound coverage, not only temporal change.

## Research Hypothesis

Query-aware visual routing treats the question as an optimizer input. Instead
of selecting a fixed global K or a fixed motion policy, the runtime chooses a
visual evidence plan from predicates in the query:

- dynamic-action predicates: prioritize RLT/delta/motion evidence.
- static-attribute predicates: preserve endpoint/keyframe detail and static
  spatial coverage.
- interaction predicates: reserve object-pair coverage plus motion evidence.
- temporal-order predicates: allocate across begin/middle/end and preserve time
  order.

This is analogous to database query planning: SQL states the desired result,
and the optimizer chooses access paths from predicates and cost estimates. For
VLMs the "access path" is not an index scan or join order; it is the mix of
frames, resolutions, token budgets, static floors, and repair passes. The
analogy is useful only if we keep the difference explicit: database plans must
preserve exact semantics, while visual evidence plans preserve answer fidelity
statistically and therefore need paired accuracy and parse-failure gates.

## Relevant Prior Work

- RLT / Don't Look Twice (NeurIPS 2024): cheap pre-model temporal redundancy
  detection by comparing same-location patches over time. Strong fit for action
  and motion saliency; weak by construction for static appearance evidence.
- Static or Dynamic (Shi et al., EMNLP 2025): query-adaptive token selection
  for VideoQA. It explores allocations between key frames that preserve spatial
  detail and delta frames that capture temporal changes, then chooses an
  allocation with a query-aware attention metric. This is the closest published
  match to our `moving_attribute` failure.
- Q-Frame (ICCV 2025): query-aware frame selection plus multi-resolution
  adaptation using a text-image matching network. This motivates endpoint and
  high-resolution detail protection for questions about color, shape, or object
  state.
- QTSplus (arXiv 2025/2026): query-aware token selection with cross-attention
  scoring and instance-specific retention budgets. This supports dynamic K,
  not just dynamic ranking.
- PruneVid (ACL Findings 2025): combines temporal/static redundancy reduction
  with query-relevant pruning. This is a direct composition template: use cheap
  redundancy first, then query-conditioned rescue.
- SparseVLM (ICML 2025): text-guided training-free visual token sparsification.
  Useful as a text-relevance baseline, especially for in-LLM token scoring.
- FastV (ECCV 2024): attention-based late visual-token pruning after early
  layers. Useful as a generic plug-and-play pruning baseline, but it does not
  solve pre-vision routing by itself.
- Token Pruning in MLLMs: Are We Solving the Right Problem? (ACL Findings
  2025): important guardrail. It argues that attention/language-guided pruning
  claims can be misleading and that random/fixed baselines must be tested.
- System R access path selection (SIGMOD 1979) and Eddies (SIGMOD Record
  2000): database analogies for static cost-based planning and adaptive
  runtime routing.

## Candidate Experiments For A Future Branch

### Q1: Static/Delta Explore-Then-Select

Run a small grid of static-keyframe budget versus delta/RLT budget and select
the allocation from query type. Accept if `moving_attribute` recovers over fixed
RLT `keep_rate=0.5` and `0.85` at equal or lower average token budget. Falsify
if the selected allocation does not beat the best fixed allocation on holdout.

### Q2: Endpoint Detail Floor

For queries containing begin/end/color/shape/material/state predicates, keep
endpoint frames and a small uniform static-detail floor, then apply RLT
elsewhere. Accept if `moving_attribute` improves with less added budget than
the group-level `0.85` rescue. Falsify if gains require nearly dense visual
budget.

### Q3: RLT + Static Coverage Floor

Union RLT top-K motion positions with a small static coverage floor sampled
over low-motion regions. Accept if it repairs attribute and interaction flips
with less than 10-15% added visual tokens. Falsify if it mostly helps unrelated
groups or erases C-VISION E2E gains.

### Q4: Query-Aware Scorer Head-To-Head

Compare RLT score, text-guided relevance, CLIP query-frame similarity, random
valid-token selection, and fixed coverage under the same valid-position K.
Accept if query-aware scoring specifically improves `moving_attribute` and
`object_interaction`. Falsify if random or fixed coverage matches it.

### Q5: Adaptive Repair Gate

Run cheap RLT first; trigger static-detail re-prefill only when query class plus
low answer margin predicts attribute risk. Accept if repair fires on less than
40% of MVBench items and recovers most RLT-induced `moving_attribute` drift.
Falsify if the guard is weak or repair fires so often that it is dense by
another name.

## Synergy With The Current RLT/VLMaxxing Branch

The current branch should close the RLT story with disjoint holdout replication
and M5 scale checks. Its artifacts are still useful for the query-aware branch:

- per-bucket failure labels define the first target (`moving_attribute`).
- RLT scorer cost defines the cheap first-stage plan.
- direct-composition analyzers define the fidelity/E2E gates.
- holdout manifests prevent query-aware tuning from inheriting dev-slice luck.

Do not claim query-aware recovery from the current branch. The only current
claim is that Round-19 identified a falsifiable failure class and a plausible
next method family.
