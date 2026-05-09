# Query-Aware Visual Routing: Research Seed

Status: self-standing handoff note for a future paper/branch. Do not implement
on the current RLT/VLMaxxing closure branch.

Audience: an expert scientist who has not read this repo. The goal is to give
enough context to run an extensive literature and experiment-design pass, then
bring back a concrete query-aware visual-routing proposal.

Evidence labels:

- `reproduced here`: measured in this repo with checked scripts/artifacts.
- `imported result`: from cited literature, not reproduced in this repo.
- `hypothesis`: proposed next work.

## One-Sentence Thesis

Video VLM acceleration should be planned from the question. Motion-only routing
is an excellent cheap default, but the query decides whether the model needs
motion evidence, static appearance detail, endpoint frames, object relations,
or a repair pass. This is visual query planning.

## Why This Exists

VLMaxxing is this repo's training-free anti-recomputation project for video
VLMs. The current paper centers on three axes:

- **C-CEILING**: arithmetic ceiling discipline. End-to-end speedup survives
  only in proportion to the dense runtime share a method actually reduces.
- **C-VISION**: first-pass vision-tower compute reduction. The vision tower
  processes only selected visual positions, then scatter-back preserves prompt
  geometry for the language model.
- **C-PERSIST**: after-ingest same-video follow-up reuse. The expensive prefix
  is paid once; later questions reuse state.

The query-aware idea comes from a sharp C-VISION/RLT result. We used RLT
motion scores as the C-VISION scorer on Gemma 4 E4B / MLX-VLM. RLT is cheap:
it scores raw frames before the model runs. The competing max-min diversity
scorer is much more expensive because it works over encoder hidden states.

Local preliminary facts, all reproduced here:

- RLT-as-C-VISION at `keep_rate=0.5` lands positive n=30 E2E cells on
  VideoMME, TOMATO, and MVBench.
- RLT's scorer cost is tens of milliseconds per item; max-min diversity costs
  seconds per item. RLT reaches the same speed class as max-min at roughly two
  orders of magnitude lower scorer cost.
- Direct RLT full composition is high-upside but bucket-conditional. The
  dev+holdout pooled speed frontier is strong, including an MVBench
  direct-composition row at `1.842x` E2E, but quality is not uniformly clean.
- Bucket-specific rescue by raising keep-rate to `0.85` recovers MVBench
  `object_interaction`, but pooled rescue still has bucket failures:
  VideoMME `long`/`medium`, TOMATO `direction`/`rotation`, and MVBench
  `action_localization`/`moving_attribute`.
- `moving_attribute` is the sharpest example, not a universal law. On the dev
  slice, `moving_attribute` stayed at dense accuracy `0.833`, composed accuracy
  `0.333`, and `Delta acc = -0.50` even when its keep-rate was raised to `1.0`.
  On the disjoint holdout slice, however, `moving_attribute` was clean at the
  base `keep_rate=0.5`. The failure is item/content-class variance, not proof
  that the whole bucket is deterministically unrecoverable.

That last point is the discovery. Motion-only routing is excellent when motion
is the evidence, but the query can ask for something else: static appearance,
endpoint state, object identity, object relations, or a localized action cue.
Raising K inside the same motion policy sometimes recovers a class and
sometimes does not. The next method should not be "keep more motion tokens."
It should be "plan the visual evidence from the query."

Relevant local source files:

- Current paper framing: `paper/framing.md`
- RLT follow-up prereg/results ledger:
  `research/experiments/2026/2026-05-08-rlt-followup-next-prereg.md`
- Decision ledger:
  `research/decision-log.md`
- Follow-up queue:
  `scripts/run_rlt_followup_queue.py`
- Full-composition analyzer:
  `scripts/analyze_gemma_full_composition.py`

## Definitions

### VLMaxxing / C-VISION

`VLMaxxing` is the repo's name for a family of training-free video-VLM
efficiency techniques. The part relevant here is `C-VISION`: reduce vision
tower work by selecting a subset of valid encoder positions per frame, then
scatter-back the skipped positions so the language-model prompt geometry is
unchanged.

The core C-VISION principle:

```text
E2E speedup is bounded by the share of runtime owned by vision compute and by
how much of that vision compute is actually removed.
```

This is not just a token-count story. It is a measured-work story. If decode or
generation dominates, even a large visual reduction yields only a small E2E
gain. If vision dominates, the same visual reduction becomes a large user-facing
speedup.

### RLT

RLT, "Don't Look Twice: Faster Video Transformers with Run-Length
Tokenization" (NeurIPS 2024), identifies repeated same-location patches across
time before model inference. It is cheap because it operates on raw patches,
not encoder hidden states. Imported RLT result: the paper reports faster video
transformer training/inference by removing repeated token runs while preserving
accuracy on action-recognition/video tasks.

Our use of RLT is not a reproduction of RLT's original VideoMAE/action
recognition setup. It is a transfer test: use RLT's raw-frame motion prior as
the scorer inside C-VISION and, separately, as a prompt-admission policy for a
video VLM.

### Query-Aware Visual Routing

Query-aware visual routing is a proposed next method family. It treats the
question as a query plan input:

- dynamic-action question: prioritize motion/delta/RLT evidence.
- static-attribute question: preserve keyframe or endpoint appearance detail.
- object-interaction question: preserve object-pair coverage plus motion.
- temporal-order question: preserve begin/middle/end temporal anchors.
- low-confidence or high-risk question: trigger a repair pass with more static
  detail or higher resolution.

The output is a visual evidence plan: frame selection, resolution selection,
token budget, static-detail floor, motion budget, and optional repair policy.

## Database Query Planning Analogy

The analogy is useful and dangerous.

Useful: SQL is declarative. The user specifies what they want; the database
optimizer chooses access paths, join orders, and physical operators based on
predicates and costs. A video question is also declarative. The user asks for a
fact; the VLM runtime chooses what visual evidence to retrieve and compute.

Dangerous: database query plans preserve exact semantics. Visual routing only
preserves answer fidelity statistically. Therefore every query-aware routing
method needs paired accuracy, parse-failure, and E2E gates. A plan that is fast
but silently changes answers is not a valid plan.

Mapping:

| Database optimizer | Query-aware visual routing |
|---|---|
| predicate | question phrase / task type |
| table statistics | frame/token redundancy statistics |
| index scan | cheap motion/RLT pass |
| join order | order of visual evidence acquisition |
| System R-style static plan | choose the initial evidence mix from query class and cost |
| Eddies-style adaptive routing | repair pass or re-ordering after low confidence |
| cost model | E2E latency model with vision/decode/generate shares |
| exact answer | paired VLM fidelity target |

This suggests a paper frame: **visual evidence planning for VLMs**. The runtime
should choose a plan, not a fixed pruning rule.

## Core Hypotheses

### H1: Query type predicts the right visual evidence mix

`moving_attribute` fails because the query asks for static appearance bound to
motion, while RLT primarily preserves temporal change. A query-aware planner
that adds endpoint/static-detail evidence should recover this bucket at a lower
budget than globally raising keep-rate.

Falsification: fixed static coverage or random valid-token selection matches
the query-aware planner on `moving_attribute` at the same budget.

### H2: Motion-first, query-repair is cheaper than query-aware everywhere

RLT is so cheap that it should remain the first-stage default. The planner
should only pay for text-guided or high-resolution detail when the query is
likely to need it.

Falsification: always-on query-aware scoring is needed to recover quality, or
the repair gate fires so often that it becomes dense-by-another-name.

### H3: Static-detail floors repair a different failure class than higher K

Raising RLT K keeps more of the same motion-ranked evidence. A static-detail
floor reserves evidence that motion ranking may never surface.

Falsification: raising RLT K and adding a static-detail floor produce the same
per-item repairs and the same errors.

### H4A: Structured evidence plans beat scalar token scores

A single scalar token score cannot express "keep endpoint frame at higher
resolution, keep object-pair coverage, and keep motion deltas elsewhere."
Query-aware routing should choose a structured plan.

Falsification: a strong scalar query-aware scorer, such as FlashVLM-style
text-guided token scoring, matches or beats structured plans on paired fidelity
under the same valid-position budget, including fixed and random coverage
controls.

### H4B: Planner benefit survives total-cost accounting

An evidence plan is only useful if the quality it recovers is worth the scorer,
planner, repair, and re-prefill costs it adds. The unit of comparison is the
full measured runtime, not just mask quality.

Falsification: the structured planner recovers quality but loses E2E to a
simpler policy such as higher fixed RLT K, fixed static coverage, or dense
fallback after all costs are counted.

## Candidate Experiments

All experiments should use the same rigor as the current RLT/VLMaxxing branch:
paired dense/sparse rows, valid-position budgeting, hard shape failures,
bootstrap confidence intervals, parse-failure deltas, and disjoint holdout
manifests.

### Q1: Static/Delta Explore-Then-Select

Run a small grid of static-keyframe budget versus delta/RLT budget. Select the
allocation from query type.

Accept if `moving_attribute` improves over fixed RLT `keep_rate=0.5` and
`0.85` at equal or lower average token budget.

Falsify if the selected allocation does not beat the best fixed allocation on
holdout.

### Q2: Endpoint Detail Floor

For questions containing words such as `begin`, `end`, `first`, `last`,
`color`, `shape`, `material`, `state`, `stationary`, or `moving object`, keep
endpoint frames and a small uniform static-detail floor, then apply RLT
elsewhere.

Accept if `moving_attribute` improves with less added budget than the
group-level `0.85` rescue.

Falsify if gains require nearly dense visual budget.

### Q3: RLT + Static Coverage Floor

Union RLT top-K motion positions with a low-rate static coverage floor sampled
over low-motion regions.

Accept if this repairs attribute and interaction flips with less than 10-15%
added visual tokens.

Falsify if it mostly helps unrelated groups or erases C-VISION E2E gains.

### Q4: Query-Aware Scorer Head-To-Head

Compare these under the same valid-position K:

- RLT score
- text-guided relevance score
- CLIP query-frame similarity
- fixed uniform coverage
- random valid-token selection
- static-detail floor plus RLT

Accept if query-aware scoring specifically improves `moving_attribute` and
`object_interaction`.

Falsify if random or fixed coverage matches it. The token-pruning literature
warns this is a real possibility.

### Q5: Adaptive Repair Gate

Run cheap RLT first. Trigger static-detail re-prefill only when query class plus
answer uncertainty predicts attribute risk.

Accept if repair fires on less than 40% of MVBench items and recovers most
RLT-induced `moving_attribute` drift.

Falsify if the guard has weak predictive value or repair fires so often that
the method is effectively dense.

### Q6: Visual Query Planner Cost Model

Build a simple optimizer that predicts E2E from:

- decode cost
- vision share
- vision reduction
- scorer cost
- prompt/prefill chunking regime
- expected repair probability

Accept if the cost model predicts chosen-plan E2E within 5-10% across held-out
plans.

Falsify if query-conditioned generation length or substrate effects dominate
the cost model without a usable correction.

This is secondary scope. A cost model makes the paper stronger, but the first
paper can stand on Q1-Q5 if the measured policy beats fixed/random coverage and
simple scalar scorers under total-cost accounting.

## What Would Make This A Separate Paper

The standalone paper is not "RLT, but query-aware." It is:

> Video VLM inference should be planned like a query: the question determines
> which visual evidence is worth computing.

Potential claims:

1. Motion-only routing is a strong default but fails predictably on static
   attribute questions.
2. A lightweight query planner can choose among motion, static, endpoint, and
   repair evidence plans.
3. Structured evidence plans beat scalar token scores on the failure classes
   where scalar scores lack the right inductive bias.
4. Query-aware routing should report dense-paired fidelity, not only token
   reduction, because visual pruning is approximate query processing rather
   than exact query optimization.

The first target is modest: recover MVBench `moving_attribute` without giving
up the RLT/C-VISION speed story. The larger target is a general visual query
planner for frozen VLM runtimes.

## Guardrails

- Do not tune on one dev slice and call it solved. Use disjoint holdout
  manifests early.
- Include random and fixed-coverage baselines. Query-aware methods must beat
  simple coverage under the same valid-position K.
- Separate scorer cost from vision cost. A query-aware scorer that costs
  seconds per item may lose even if its mask is better.
- Keep C-VISION and prompt admission separate until direct composition is
  measured.
- Do not claim database-style exactness. This is approximate visual evidence
  planning with measured answer-fidelity gates.
- Track per-bucket results. Aggregate accuracy can hide the exact class the
  planner is supposed to repair.

## Literature Starting Points

### This repo / VLMaxxing

- `paper/framing.md`: current paper story and contribution boundaries.
- `paper/claim-matrix.md`: current claim status.
- `research/experiments/2026/2026-05-08-rlt-followup-next-prereg.md`:
  RLT/VLMaxxing queue, hypotheses, and Round-19 interpretation.
- `research/decision-log.md`: adopted/weakened/killed ideas.

Interpretation: VLMaxxing supplies the systems frame and the measured failure
that motivates query-aware planning. It is unpublished local work; label all
of its numbers `reproduced here`, not imported literature.

### RLT

- [Don't Look Twice: Faster Video Transformers with Run-Length Tokenization,
  NeurIPS 2024](https://proceedings.neurips.cc/paper_files/paper/2024/hash/3181db351fd3ced43cd589b0b572675d-Abstract-Conference.html)
- [Hugging Face paper page](https://huggingface.co/papers/2411.05222)

Use: cheap pre-model motion/redundancy prior. Boundary: not query-aware and
not designed to preserve static appearance details when motion saliency is low.

### Query-aware video/token selection

- [Static or Dynamic: Towards Query-Adaptive Token Selection for Video Question
  Answering, EMNLP 2025](https://aclanthology.org/2025.emnlp-main.545/)

Most directly relevant. It explicitly separates static keyframe detail from
dynamic delta evidence and chooses allocation from the query.

- [Q-Frame: Query-aware Frame Selection and Multi-Resolution Adaptation for
  Video-LLMs, ICCV 2025](https://arxiv.org/abs/2506.22139)

Relevant for endpoint/high-resolution detail: question relevance can choose
which frames deserve more pixels.

- [Seeing the Forest and the Trees: Query-Aware Tokenizer for Long-Video
  Multimodal Language Models / QTSplus](https://arxiv.org/abs/2511.11910)

Relevant for query-conditioned token budgets and temporal-order preservation.

- [PruneVid: Visual Token Pruning for Efficient Video Large Language Models,
  ACL Findings 2025](https://aclanthology.org/2025.findings-acl.1024/)

Relevant because it combines temporal/static redundancy reduction with
query-relevant pruning.

- [SparseVLM: Visual Token Sparsification for Efficient Vision-Language Model
  Inference, ICML 2025](https://arxiv.org/abs/2410.04417)

Useful text-guided training-free baseline, especially for in-LLM scoring.

- [An Image is Worth 1/2 Tokens After Layer 2 / FastV, ECCV
  2024](https://arxiv.org/abs/2403.06764)

Generic plug-and-play visual token pruning baseline. It is likely not enough
for pre-vision evidence planning, but it is a necessary comparator.

- [Token Pruning in Multimodal Large Language Models: Are We Solving the Right
  Problem?, ACL Findings 2025](https://aclanthology.org/2025.findings-acl.802/)

Guardrail paper. Treat its critique as mandatory: compare against random and
fixed coverage, and be skeptical of attention/language-guided scores unless
they beat simple baselines under matched evaluation.

- [Frame-Voyager: Learning to Query Frames for Video Large Language Models,
  ICLR 2025 / arXiv 2410.03226](https://arxiv.org/abs/2410.03226)

Use: venue-backed evidence that frame selection should be conditioned on the
textual query and can be learned from Video-LLM loss rankings. Boundary:
trained frame-combination selection, not training-free token routing or a
pre-vision C-VISION scorer. This is the closest prior to the "evidence plan"
idea; the proposed paper must explain why costed, training-free token/frame
planning is different from a learned frame-combination policy.

- [M-LLM Based Video Frame Selection for Efficient Video Understanding, CVPR
  2025 / arXiv 2502.19680](https://arxiv.org/abs/2502.19680)

Use: trained query-adaptive frame selector with spatial and temporal
pseudo-labeling. Boundary: frame-level selection with extra model/scorer cost,
not structured token-budget planning inside C-VISION.

- [FlashVLM: Text-Guided Visual Token Selection for Large Multimodal Models,
  arXiv 2512.20561](https://arxiv.org/abs/2512.20561)

Use: text-guided scalar visual-token scoring baseline. Boundary:
under-submission preprint; cite as preprint only. It is a key H4A comparator
because a strong scalar token scorer could falsify the need for structured
evidence plans.

### Database query planning analogy

- [Access Path Selection in a Relational Database Management System, SIGMOD
  1979 / System R](https://research.ibm.com/publications/access-path-selection-in-a-relational-database-management-system)
- [Eddies: Continuously Adaptive Query Processing, SIGMOD Record
  2000](https://sigmodrecord.org/2000/06/08/eddies-continuously-adaptive-query-processing/)

Use these for framing, not for overclaiming. The analogy is "choose access
paths from predicates and costs"; the key difference is that visual plans are
approximate and must be empirically gated.

## Handoff Questions For The Next Scientist

1. What is the cleanest taxonomy of video questions for visual evidence
   planning: motion, static attribute, object relation, temporal order,
   counting, scene context, or something else?
2. Which query-aware prior is cheapest enough to run before the vision tower:
   lexical rules, CLIP frame matching, lightweight text-image scoring, or a
   small frozen classifier?
3. Can a static-detail floor repair `moving_attribute` without dense fallback?
4. Are there public benchmarks with enough attribute/object-binding questions
   to test this beyond MVBench?
5. Which baselines are mandatory to avoid the "random pruning is competitive"
   critique?
6. Can the planner be expressed as a costed policy tree, like a database query
   plan, with a measured E2E model?
7. What minimal result would justify a standalone paper instead of a
   VLMaxxing appendix?

## Near-Term Recommendation

The current RLT/VLMaxxing branch has already run disjoint holdout replication.
Before forking implementation, finish any desired M5 scorer-transfer scale
check. Then fork a query-aware branch with a narrow first target:

```text
Recover static/detail-sensitive failures under pooled composition by adding
query-conditioned static detail to RLT C-VISION, while preserving most of the
RLT speedup and beating fixed/random coverage controls. Use MVBench
moving_attribute as the first stress test, not as the only target.
```

If that lands, the research direction is strong enough for its own paper.
