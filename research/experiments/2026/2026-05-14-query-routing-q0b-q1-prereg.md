# 2026-05-14 query-routing Q0b/Q1 implementation prereg

Status: **Q0b/Q1/Q1b measured; Q1c admission-scheduler follow-up implemented,
not yet measured; active-repair confidence probe measured and underpowered;
offline class-conditional/text admission simulations measured; CPU cost-model
and transfer audits added; hosted-dev breadth sweep and broader codec-motion
follow-up not yet measured**.

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

## 2026-05-19 design-space update

External review and local artifact audits sharpened the mechanism story:

- The Q1/Q1b static-mask result is now aligned with recent token-pruning
  critiques: strong fixed/random controls are mandatory, and static
  structured scores often collapse toward random.
- The Q1b prompt-admission harm is real, but the harmed item sets are not
  globally disjoint from typed-mask harms. The sharper claim is mechanism
  specificity: admission adds new `moving_attribute` harms that the
  admission-off random coverage row avoided.
- The `moving_attribute` failure is not a simple first-frame/temporal-anchor
  failure. RLT threshold admission retains the first tubelet by construction.
  The better working hypothesis is motion-role disambiguation: queries asking
  which visible object is moving or stationary are brittle when prompt visual
  placeholders are removed. A 2026-05-19 lexical smoke found this signal is
  present but weak at small N, so it is a hypothesis generator, not a
  scheduler.
- Codec metadata is a plausible runtime selectivity signal for admission
  scheduling. It is content-conditional rather than query-conditional, so it
  belongs after Q1c and a breadth sweep, not inside the current Q1c lane.

### Hosted-dev breadth sweep preregistration

The five-bucket MVBench motion slice is too narrow for a general static-mask
verdict. The repo already contains
`research/benchmark_manifests/mvbench_hosted_dev_v1.toml`, a 54-item hosted
slice with 18 buckets and 3 items per bucket. The hosted sweep reuses Q0b/Q1
only:

```bash
scripts/run_rlt_query_routing_hosted_sweep.sh
```

Implementation guard: expected item counts are derived from the manifest for
MVBench/TOMATO full-manifest runs. VideoMME remains special-cased through
`--cvision-n-items` because its default combined manifest intentionally
contains 60 items while many cells run 30.

Hypothesis H4c. The static-mask negative result generalizes beyond the five
motion buckets.

- Accept negative verdict: no typed Q1 operator beats fixed/random controls on
  aggregate accuracy at positive E2E on the hosted slice.
- Revive condition: a typed operator wins aggregate quality over controls
  without parse regression and with E2E > 1.0, or a coherent bucket family
  shows typed wins that motivate a query/content-conditional router.
- Interpretation caveat: 18 buckets x 3 items improves breadth, not per-bucket
  power. Bucket rows are descriptive only unless followed by a larger slice.

### Codec-motion smoke preregistration

The codec-motion probe is CPU-only and does not run a VLM:

```bash
./.venv/bin/python scripts/analyze_mvbench_codec_motion.py \
  --manifest research/benchmark_manifests/mvbench_motion_dev_v2.toml \
  --max-items-per-group 5 \
  --max-frames 20 \
  --output /tmp/mvbench_codec_motion.json
```

Hypothesis H5c. H.264 motion/residual metadata is a cheap selectivity signal
for admission scheduling.

- Accept as a signal, not a model claim: bucket means separate the admission-
  sensitive buckets from admission-safe buckets by a large margin, and
  extraction cost is small enough to justify a sidecar/runtime scheduler.
- Falsify: motion/residual means do not separate buckets, are dominated by
  codec artifacts such as GOP/I-frame layout, or extraction cost is too high
  without sidecars.
- Next if positive: implement codec-conditioned admission scheduling as a
  separate branch with random/fixed and Q1c as controls. This must be framed
  against CodecSight/CoStream and CoPE-VideoLM: codec-guided VLM pruning now
  exists, so novelty is conditional admission planning and robust physical
  operator selection, not "first codec signal."

2026-05-19 bounded smoke: `--max-items-per-group 1 --max-frames 4` ran
CPU-only and wrote `/private/tmp/codec_motion_smoke.json`. It reported
`n_items=5`, honored item-level `start`/`end` windows, and showed the expected
ordering: moving_direction 0.000 and moving_attribute 0.015 mean motion
magnitude versus action/object/fine-grained buckets at 0.051-0.728. Per-frame
extraction was roughly 2-4 ms on short/no-window examples and 52 ms on one
segment-windowed object_interaction example because the current probe decodes
up to the requested window. This is only a smoke, but it validates the probe,
keeps H5c alive, and flags seeking/indexing as an engineering item before any
large codec scan.

2026-05-19 validation note: a later Claude summary reported N=30 per-item
correlations between H.264 motion/residual metrics and admission damage, and
concluded codec-conditioned admission scheduling was dead. Local artifact audit
did **not** find a committed N=30 codec-correlation artifact; the only observed
codec artifact in this branch is the small smoke described above. Therefore
H5c remains **unmeasured at full N**, not falsified. Before implementing a
codec-conditioned VLM router, run the full CPU-only scan and join per-item
codec metrics to Q1b/Q1c paired rows by item id.

2026-05-19 follow-up CPU smoke: `--max-items-per-group 2 --max-frames 8`
wrote `/private/tmp/mvbench_codec_motion_2x8.json` with `n_items=10`.
Item ids matched the MVBench manifest form needed for later joins. Bucket
means still separate the low-motion synthetic buckets from action/object
clips: moving_direction `0.0208`, moving_attribute `0.0733`, action_localization
`0.7353`, object_interaction `0.8387`, fine_grained_action `3.2538` mean motion
magnitude. This keeps codec features alive as a cheap descriptive side signal,
but it still does not establish per-item prediction of admission damage.

### H6 active-repair confidence-probe preregistration

Active repair is a different mechanism from static query planning. It does
not try to predict unsafe admission before seeing the answer. It asks whether
the cheap first pass exposes enough uncertainty to decide when to retry with
the dense/no-admission path.

Implemented launch surface:

```bash
scripts/run_rlt_query_routing_active_repair_probe.sh
```

This wrapper re-runs the Q1b admission-on cells with first generated-token
confidence capture enabled, then runs
`scripts/analyze_gemma_active_repair_confidence.py` separately for the
`random_seed11 + admission_on`, `fixed_uniform + admission_on`, and pooled
admission-on paired rows. The pooled row is supportive only unless the
per-arm directions agree, because both arms reuse the same MVBench items. It
does **not** implement an in-run repair policy. It simulates thresholded retry
from paired dense/composed
artifacts and charges each retry as:

```text
active_item_ms = composed_pass_ms + dense_retry_ms
```

The analyzer records and accounts for confidence-capture overhead. The
composed pass keeps its confidence overhead because the gate needs that signal;
the dense retry subtracts dense-side confidence-capture overhead because a
live dense retry would not compute another gate. If the capture-overhead fields
are missing or non-finite, the analyzer fails rather than silently using
polluted timings.

The default wrapper uses a fresh artifact directory and therefore plans the
full RLT/Q0b/Q1/Q1b dependency chain. A dry-run on 2026-05-19 planned roughly
12.6-25.3 hours. Operators may set `ARTIFACT_DIR` to an existing compatible
artifact directory to reuse completed non-logprob dependencies, but the
logprob-capture schema intentionally forces fresh Gemma admission rows.

For the immediate publish-or-kill signal, use the targeted launcher instead:

```bash
scripts/run_rlt_query_routing_active_repair_targeted.sh
```

This script intentionally bypasses the broad queue dependency chain and runs
ten commands: shared dense/no-admission baseline, exact-Q1 random-valid
admission-off same-run baseline (`keep_rate=1.0`, `prune_placeholders=none`,
`vision_tower_keep_rate=0.5`, `vision_tower_score_mode=random_valid`,
`vision_random_seed=11`), random-valid baseline paired analyzer, random-valid
admission-on composed arm, random-valid paired analyzer, fixed-uniform
admission-on composed arm, fixed-uniform paired analyzer, two per-arm
confidence-frontier analyzers, and one pooled confidence-frontier analyzer. It
writes to
`research/experiments/2026/artifacts/rlt_query_routing_active_repair_targeted`
by default. This is the launch path to use before spending 12-25 hours on the
full wrapper. The extra same-run baseline adds roughly one admission-off
composed pass plus one CPU analysis step relative to the earlier eight-command
version; this is intentional because it removes the stale `1.254x` comparison
from the targeted verdict.

Smoke path:

```bash
N_ITEMS=1 scripts/run_rlt_query_routing_active_repair_targeted.sh
```

With `N_ITEMS>0`, the launcher writes to
`research/experiments/2026/artifacts/rlt_query_routing_active_repair_targeted_smoke`,
sets `--n-items`, lowers `--expected-items` to the smoke count, sets
`--bucket-min-n 1`, uses `--n-bootstrap 50` for the paired analyzer, and uses
`ACTIVE_REPAIR_N_BOOTSTRAP=100` for the confidence analyzer. Do not reuse the
smoke artifact directory for paper tables.

Primary signal:

- Margin field: `composed_first_generated_top2_margin` by default for future
  analyzer runs. The initial targeted H6 report used
  `composed_first_generated_candidate_top2_margin`; a CPU-only reanalysis
  below showed that full-vocabulary margin is the better diagnostic for this
  artifact because several admission failures start with non-answer-format
  tokens rather than low A/B/C/D separation. Candidate-letter margin remains
  available through `--margin-field` for answer-choice-specific audits.
- The wrapper rejects dense-side margin fields. Repair gating can only use
  composed-side first-pass confidence.
- Alternative fields may be explored only if preregistered before a long run
  (for example selected-vs-best-alternative margin).
- Repair action: retry when margin is at or below threshold.

H6a. The cheap pass knows when it was harmed.

- Accept exploratory signal: per-arm `harmed_count >= 5`,
  `preserved_correct_count >= 10`, AUC point `>=0.70`, item-cluster bootstrap
  lower 95% CI `>=0.65`, and matching direction across the random-valid and
  fixed-uniform admission-on arms. The pooled analysis uses an item-cluster
  bootstrap and is supportive, not independent `n=60` evidence, because both
  arms reuse the same 30 MVBench items. The analyzer has a stricter mechanical
  gate of at least three harmed rows and three preserved-correct rows before
  AUC can pass at all, both in aggregate and within every pooled source arm;
  lower event counts are reported as underpowered and cannot produce a viable
  threshold.
- Falsify: AUC lower 95% CI `<0.60`, no harmed items, no preserved-correct
  items, missing/non-finite margin fields, or disagreement in per-arm
  direction that makes the pooled number uninterpretable.
- Inconclusive: AUC point in `(0.60, 0.70)`, AUC point high but lower CI
  `<0.65`, harmed count below five per arm, pooled pass with one arm failing,
  or a threshold frontier that changes when a single harmed item is removed.

H6b. A one-step retry frontier is viable under full cost accounting.

- Accept exploratory frontier: at least one threshold achieves
  `accuracy_delta_vs_dense >= -0.02`, `speedup_dense_over_active >= 1.0`,
  `retry_rate <= 0.50`, `harmed_retried >= 2`, and the AUC class-count gate.
  The targeted launcher now
  provides `BASELINE_REPAIR_PAIRED` by default from a same-run
  `random_valid(seed=11)` admission-off baseline, so viable thresholds must
  also match that no-retry baseline's accuracy delta within `0.02` and beat
  its dense-normalized speedup. If the baseline rows include confidence-capture
  fields, the analyzer subtracts them from both the dense and composed
  denominators because an admission-off no-retry baseline would not compute a
  repair gate. The broad wrapper, which does not generate a same-run baseline,
  keeps the conservative `1.254x` standalone floor.
- Falsify: no threshold satisfies both fidelity and speed after charging the
  composed pass plus dense retry.
- Important anti-claim: a positive H6b result is a **retrospective paired-row
  simulation**, not a deployed repair operator. A live repair run needs
  explicit `repair_triggered`, `repair_reason`, `repaired_correct`, and
  `repaired_end_to_end_ms` fields before paper claims.

Novelty boundary:

- Confidence cascades and uncertainty-guided multimodal systems exist (for
  example FrugalGPT/RouteLLM-style cascades and confidence-token routing).
  Query-aware visual allocation also exists: Q-Frame, QuoTA, SparseVILA,
  Q-Zoom, FastVID, SpecVLM, and SToP are relevant comparators. The narrower
  claim here is within one frozen VLM runtime: run the same model cheaply
  first, then retry only uncertain rows with the dense/no-admission physical
  operator, with paired fidelity gates and full E2E cost accounting.
- Do not call this "self-correction". A retry earns its claim only by buying
  additional visual evidence or recomputation. Blind self-revision is a
  different literature.
- First-token margin is a routing feature, not yet a calibrated confidence
  mechanism. Confidence-token work reports that raw token probabilities can be
  weaker than learned confidence signals; H6 tests whether the cheap signal is
  sufficient in this narrow physical-operator setting.

Prior-art anchors checked for this branch:

- Q-Frame, arXiv:2506.22139: training-free query-aware frame selection and
  multi-resolution adaptation.
- QuoTA, arXiv:2503.08689: query-oriented frame/token assignment via CoT query
  decomposition.
- SparseVILA, arXiv:2510.17777: decouples visual sparsity across prefill and
  decoding, including query-aware retrieval.
- Q-Zoom, arXiv:2604.06912: query-aware coarse-to-fine adaptive perception
  with trained modules.
- FastVID, arXiv:2503.11187: dynamic density pruning for Video LLMs.
- SpecVLM, arXiv:2508.16201: speculative decoding with video-token pruning.
- SToP, arXiv:2604.20937: MCQA can hide fine-grained pruning failures; sink
  tokens matter for grounded video understanding.
- Learning to Route LLMs with Confidence Tokens, arXiv:2410.13284: confidence
  routing exists and raw token probabilities are not the strongest known
  confidence mechanism.

### 2026-05-19 Pareto Audit And Editor Notes

Artifact audit over the Q0b/Q1/Q1b cells shows useful positive points and one
retracted timing artifact that should guide the paper-facing language:

- `query_q0b_cvision_only_mvbench_kr100`: retract the prior `1.177x` E2E
  language. Re-audit showed the analysis paired a May 15 composed file against
  an older May 14 dense reference, baking machine-state drift into the
  dense/composed ratio. Mechanistically this cell has `vision_reduction=0.0`,
  `placeholder_reduction=0.0`, keeps all valid encoder positions, and therefore
  saves no work. It remains useful only as an exact-choice / dense-equivalence
  systems check, not as a speedup claim. The analyzer now supports
  `--dense-source composed-jsonl-same-run`, and query-routing launchers use
  that mode for future timing-sensitive analyses. Historical Q0b/Q1/Q1b
  analysis JSONs produced before this fix should not be used for speedup
  claims without reanalysis.
- `query_q1_mvbench_random_seed11`: `1.254x` E2E, `Delta acc=0.000`, fidelity
  pass, but choice agreement is only `0.733` and the bucket gate fails from one
  action-localization loss at `n=6`. Treat this as a strong Pareto/exploratory
  point, not an exact-fidelity headline.
- `query_q1b_mvbench_random_seed11_actionloc_dense`: `1.140x` E2E,
  `Delta acc=+0.033`, fidelity pass, and no action-localization bucket harm.
  This is the accuracy-side positive point, not the speed headline.
- Oracle bucket routing over already-run fidelity-pass cells can reach about
  `1.287x` E2E and `Delta acc=+0.033` by choosing the fastest nonnegative
  policy per MVBench bucket. Anti-claim: MVBench category labels are benchmark
  metadata. This is an upper bound on what a real router could exploit, not a
  deployable policy.

Paper-editor note, not paper text: the honest story is now "static typed
vision-mask scoring failed; robust/dumb coverage and dense-equivalent
C-VISION paths are the positive controls; active repair tests whether the
model's own cheap-pass confidence can turn the speed frontier into an adaptive
runtime policy." Do not bury the negative result. It is what justifies moving
from static physical-operator selection to adaptive execution.

2026-05-19 MLX smoke result: `N_ITEMS=1
scripts/run_rlt_query_routing_active_repair_targeted.sh` completed after a
logprob conversion bug was fixed, then completed again after the same-run
dense-source and active-repair v2 analyzer fixes. Dense,
`random_valid(seed=11)+admission_off`, `random_valid(seed=11)+admission_on`,
and `fixed_uniform+admission_on` each produced one paired row for
`mvbench:action_localization:0`; the baseline analyzer, two per-arm
confidence-frontier analyzers, and pooled analyzer completed. The smoke rows
contain finite candidate-letter margins (`10.0625` composed for both cheap
arms) and finite confidence-capture timings. The pooled smoke has
`schema_version=gemma_active_repair_confidence_v3`, `harmed_count=0`,
`auc_gate_passed=false`, named no-retry/retry-all baselines, and
`pooled_status.analysis_role=supportive_pooled`, so it validates
schema/logging/analyzer plumbing only; it does not test H6a/H6b.

2026-05-19 targeted H6 run result: the experiment ran on
`mvbench_motion_dev_v2` n=30 with same-run ABBA timing and same-run
`random_valid(seed=11)` admission-off baseline.

- Admission-off baseline:
  `accuracy_delta=0.000`, `choice_agreement=1.000`, `E2E=1.0056x`.
  It is output-identical to dense but not meaningfully faster.
- `random_valid(seed=11)+admission_on`:
  `accuracy_delta=-0.0667`, 95% CI `[-0.2333, +0.1000]`,
  `choice_agreement=0.667`, `E2E=1.207x`.
- `fixed_uniform+admission_on`:
  `accuracy_delta=-0.1333`, 95% CI `[-0.2667, +0.0333]`,
  `choice_agreement=0.700`, `E2E=1.187x`.
- First-token candidate-letter margin is directionally associated with harm
  but fails the preregistered confidence gate:
  random arm AUC `0.727` with lower 95% CI `0.389`, fixed arm AUC `0.771`
  with lower 95% CI `0.521`, supportive pooled AUC `0.767` with lower 95%
  CI `0.536`. All three produce `viable_threshold_count=0`.
- The common harmed core is `mvbench:moving_attribute:{1,2,5}` across both
  admission-on arms. The stronger claim "all harm is moving_attribute" is
  false: random also harms `object_interaction:2`; fixed also harms
  `moving_direction:4` and `object_interaction:5`.

Interpretation: H6 is not a win. First-token margin remains a
hypothesis-generating signal for larger N, but the current run does not justify
a live repair operator. The more actionable result is that prompt admission,
not static vision-mask scoring, is the live physical operator: it buys about
`1.19-1.21x` E2E on this slice and breaks a small, partly reproducible item
set.

2026-05-19 CPU-only H6 margin reanalysis: rerunning the confidence analyzer
on the same paired rows with `composed_first_generated_top2_margin` produces:

- `random_valid(seed=11)+admission_on`: AUC `0.758`, lower 95% CI `0.488`,
  `viable_threshold_count=0`.
- `fixed_uniform+admission_on`: AUC `0.900`, lower 95% CI `0.706`,
  `viable_threshold_count=0`.
- supportive pooled: AUC `0.831`, lower 95% CI `0.645`,
  `viable_threshold_count=0`.

Artifacts:

- `query_q1b_mvbench_random_seed11_admission_on_active_repair_confidence_vocab_margin.json`
- `query_q1b_mvbench_fixed_uniform_admission_on_active_repair_confidence_vocab_margin.json`
- `query_q1b_mvbench_admission_on_pooled_active_repair_confidence_vocab_margin.json`

Interpretation: the full-vocabulary margin claim is real, especially for the
fixed-uniform arm, but it does not rescue one-step active repair. The full
threshold sweep still has no viable point because each repaired item pays both
the cheap admission-on pass and the dense/no-admission retry. In the fixed arm,
the threshold catching all five harmed rows retries 43.3% of items and lands at
`0.786x` dense-normalized E2E, slower than dense and slower than the same-run
no-admission baseline. Therefore active repair is a diagnostic signal and a
larger-N research lead, not the next deployment mechanism.

### H7 Offline Class-Conditional Admission Simulation

The active-repair run leaves a simpler planner hypothesis: do not try to
predict harm after the cheap pass; use query/content class to decide where
prompt admission is safe. The first CPU-only simulation is intentionally
retrospective and benchmark-metadata-based.

Command:

```bash
./.venv/bin/python scripts/analyze_gemma_admission_policy_simulation.py \
  --safe-paired-items research/experiments/2026/artifacts/rlt_query_routing_active_repair_targeted/query_q1_mvbench_random_seed11_no_admission_paired.jsonl \
  --fast-paired-items research/experiments/2026/artifacts/rlt_query_routing_active_repair_targeted/query_q1b_mvbench_random_seed11_admission_on_paired.jsonl \
  --fallback-group moving_attribute \
  --policy-label moving_attribute_safe_random_admission_on \
  --output research/experiments/2026/artifacts/rlt_query_routing_active_repair_targeted/query_q1b_mvbench_random_seed11_moving_attribute_safe_policy.json
```

Result:

- Pairing audit: `dense_label_mismatch_count=0` between the no-admission safe
  rows and random admission-on fast rows.
- Policy: route `moving_attribute` to no-admission; route the other four
  buckets to `random_valid(seed=11)+admission_on`.
- Aggregate against the fixed safe/no-admission dense denominator:
  `accuracy_delta=+0.0333`, `choice_agreement=0.767`, `E2E=1.141x`, with
  `24/30` items using the fast arm and `6/30` using the safe arm.
- `moving_attribute` is recovered to `accuracy_delta=0.000`,
  `choice_agreement=1.000`; one `object_interaction` harmed row remains and
  one `object_interaction` row recovers, for net zero in that bucket.
- The same simulation against `fixed_uniform+admission_on` hard-fails by
  default because the fixed arm's dense ABBA labels drift from the baseline
  on seven items; do not use it for a primary mixed-policy estimate without a
  shared-reference rerun.

Anti-claims:

- This is not a deployed query planner. It uses MVBench bucket metadata and
  already-completed paired rows.
- This is not accuracy-clean in the strict choice-identity sense: seven
  choices still change, although the aggregate accuracy estimate improves by
  one item.
- It does show a concrete "there" worth testing: class-conditional prompt
  admission can convert the admission-on speed lever into a better
  speed/accuracy point than either always-safe no-admission (`1.005x`,
  exact agreement) or always-fast random admission (`1.207x`, `-0.0667`
  accuracy delta).

Implementation follow-up: Q1c now includes
`query_q1c_mvbench_random_seed11_moving_attribute_safe_admission`, which uses
global no-admission with prompt admission enabled for
`action_localization`, `fine_grained_action`, `moving_direction`, and
`object_interaction`, leaving `moving_attribute` on the safe arm. Q1c also
plans `query_q1c_mvbench_random_seed11_no_admission_baseline` so the verdict
compares class-conditional admission to a Q1c-local same-run no-admission
baseline instead of stale Q1 timing. Replicate on holdout or hosted-dev before
using it as more than a query-routing appendix result.

### H7b Offline Text-Only Admission Simulation

Follow-up review suggested that the bucket policy might be approximated from
question text without using MVBench metadata. A new CPU-only analyzer,
`scripts/analyze_gemma_text_routed_admission.py`, routes rows whose raw MVBench
question matches an attribute-lookup regex to the safe no-admission paired
rows and routes all other rows to the fast admission-on paired rows. It uses
the same fixed safe/no-admission dense denominator as the group-policy
simulator and hard-fails item-set, intrinsic-field, dense-label-drift,
manifest, and degenerate-routing errors by default.

Primary text policy:

```bash
./.venv/bin/python scripts/analyze_gemma_text_routed_admission.py \
  --safe-paired-items research/experiments/2026/artifacts/rlt_query_routing_active_repair_targeted/query_q1_mvbench_random_seed11_no_admission_paired.jsonl \
  --fast-paired-items research/experiments/2026/artifacts/rlt_query_routing_active_repair_targeted/query_q1b_mvbench_random_seed11_admission_on_paired.jsonl \
  --manifest research/benchmark_manifests/mvbench_motion_dev_v2.toml \
  --policy-label text_attribute_safe_random_admission_on \
  --output research/experiments/2026/artifacts/rlt_query_routing_active_repair_targeted/query_q1b_mvbench_text_keyword_safe_random_admission_policy.json
```

Result:

- Default regex:
  `\bwhat\s+(?:(?:color|shape|material)\b|is\s+the\s+(?:color|shape|material)\b)`.
- Route summary: all six `moving_attribute` rows route safe; the other 24
  rows route fast.
- Aggregate against the fixed safe/no-admission dense denominator:
  `accuracy_delta=+0.0333`, `choice_agreement=0.767`, `E2E=1.141x`.

Literal-regex variant:

- Regex `\bwhat\s+(?:color|shape|material)\s+` misses
  `mvbench:moving_attribute:4` ("What is the material..."), so it routes five
  `moving_attribute` rows safe and one fast.
- Artifact:
  `query_q1b_mvbench_text_literal_keyword_safe_random_admission_policy.json`.
- Aggregate: `accuracy_delta=+0.0333`, `choice_agreement=0.767`,
  `E2E=1.148x`.

Interpretation and anti-claims:

- This is the first deployable-looking query-routing signal in this branch:
  the route uses question text, not benchmark bucket labels or a second model
  pass.
- It is still not a paper headline at n=30. MVBench's motion templates are
  visibly lexical, so this is a candidate planner baseline and next-run
  hypothesis, not evidence of broad natural-language generalization.
- Do not cite `1.188x` for this fixed-denominator text policy. That number can
  be reproduced only by using an admission-on dense denominator or by reading a
  pooled active-repair no-retry baseline, both of which violate the denominator
  discipline adopted after the Q0b timing artifact.
- The next live validation should be a hosted-dev or holdout run that generates
  same-run no-admission and admission-on paired rows, then applies this
  text-only policy offline with the same fixed-denominator analyzer. A learned
  or conformal text router is only justified after collecting enough paired
  labels for calibration.

### H7c CPU Cost-Model and Text-Transfer Audit

Follow-up review shifted the strongest paper-facing thread away from "the
regex router is a headline" and toward a cost-model claim: prompt admission
touches the LLM prefill path, so E2E speedup should be bounded by prefill share,
vision share, decode/other share, and selection/kernel overhead. This is a
CPU-only artifact audit, not a new MLX run.

Implementation updates:

- `scripts/analyze_gemma_admission_policy_simulation.py` and
  `scripts/analyze_gemma_text_routed_admission.py` now emit schema v2 with
  prefill totals, prefill speedup, prefill/E2E shares, and paired item-bootstrap
  CIs for `accuracy_delta`, E2E speedup, and prefill speedup.
- `scripts/analyze_gemma_paired_cost_model.py` summarizes any paired Gemma
  artifact as a stage-cost row: E2E, prefill, vision, other, stage shares,
  prefill-only ceiling, prefill+vision ceiling, accuracy delta, harmed count,
  and paired item-bootstrap CIs.
- `scripts/analyze_gemma_text_route_transfer.py` checks whether a preregistered
  question-text rule covers harmed rows in a single paired artifact. This is a
  transfer screen only; it does not simulate a mixed policy unless matching
  safe and fast paired rows exist.

Updated H7/H7b artifacts:

- Bucket-oracle and robust text regex both remain `1.141x` E2E,
  `Delta acc=+0.0333`, but the new bootstrap CI is wide:
  `Delta acc CI=[-0.0667,+0.1333]`, E2E CI `[1.095,1.191]`, prefill speedup
  `1.297x` with CI `[1.216,1.379]`.
- Literal regex remains `1.148x` E2E, `Delta acc=+0.0333`, with E2E CI
  `[1.098,1.201]` and prefill speedup `1.308x` with CI `[1.224,1.395]`.

Cost-model audit table (all ratio-of-sums, paired bootstrap CIs in artifacts):

| artifact | n | E2E | prefill | dense prefill share | Delta acc | harmed |
|---|---:|---:|---:|---:|---:|---:|
| MVBench dev_v2 random admission-on | 30 | `1.207x` | `1.430x` | `0.579` | `-0.0667` | 4 |
| MVBench holdout full composition | 30 | `1.779x` | `1.594x` | `0.440` | `-0.0667` | 3 |
| MVBench dev moving_attribute kr100 composition | 30 | `1.477x` | `1.392x` | `0.451` | `-0.0667` | 4 |
| MVBench holdout moving_attribute kr100 composition | 30 | `1.438x` | `1.496x` | `0.446` | `+0.0000` | 2 |
| TOMATO holdout full composition | 30 | `1.190x` | `1.232x` | `0.392` | `-0.1333` | 7 |
| VideoMME holdout full composition | 30 | `0.984x` | `1.063x` | `0.072` | `-0.1000` | 4 |

The MVBench dev_v2 random-admission row is the cleanest admission-only ceiling
check: observed E2E `1.207x` versus prefill-only ceiling `1.211x`, with
vision speedup `1.000x`. The broader cross-benchmark rows are **not** quality
wins; most are full composition rows with fidelity failures. They are useful
as timing-mechanism evidence and as a warning that E2E speed depends on which
pipeline stage a policy actually changes.

Text-rule transfer screen:

| artifact | matched rows | harmed rows | harmed recall |
|---|---:|---:|---:|
| MVBench holdout full composition | 6/30 | 3 | `0.000` |
| MVBench dev moving_attribute kr100 composition | 6/30 | 4 | `0.750` |
| MVBench holdout moving_attribute kr100 composition | 6/30 | 2 | `0.000` |
| TOMATO holdout full composition | 3/30 | 7 | `0.000` |
| VideoMME holdout full composition | 0/30 | 4 | `0.000` |

Interpretation:

- Agree with the revised peer-review framing: the text regex is a useful
  deployment knob on one MVBench dev slice, not the paper's main contribution.
  It fails to transfer as a harm detector on the available holdout/TOMATO/
  VideoMME artifacts.
- The stronger research direction is cost-accounted admission scheduling:
  measure which stage is changed, then predict E2E from the affected-stage
  share. This complements query-aware routing papers; it does not claim
  query-aware admission is novel.
- The next live experiment should be cross-benchmark admission-only, not a
  larger MVBench-only regex test: same-run dense/no-admission/admission-on rows
  on MVBench hosted-dev, TOMATO N=30, and VideoMME short N=20, with this
  cost-model auditor as the preregistered analysis.

### H7d CPU Speculative-Admission Audit

Claude proposed a new candidate mechanism after the H7c audit: run the
admission-on path until the first generated token, abort on a format signal
such as `composed_parse_failure`, then rerun the no-admission LM prefill while
reusing encoder features. This is a plausible physical-operator policy, but it
must be treated as an offline simulation until the live cache path exists.

Implementation updates:

- `scripts/analyze_gemma_speculative_admission.py` simulates the policy from
  paired safe/no-admission and fast/admission-on rows. It reports both
  `with_vision_cache` and `without_vision_cache` cost assumptions. Aborted rows
  pay according to when the signal is observable: first-token signals
  (`non_letter`, first-token margin) pay fast vision plus fast admission
  prefill before rollback; final-output parse failure pays the full fast row
  before rollback. Rollback then pays the safe no-admission prefill and
  decode/parse tail, plus safe vision only in the no-cache assumption. This
  avoids the earlier double-pass active-repair accounting bug and the
  parse-failure-as-first-token oracle-cost bug.
- `scripts/analyze_gemma_abort_signal_transfer.py` audits whether an intrinsic
  abort signal covers harmed rows in a single paired artifact. This is only a
  transfer screen; it does not simulate a safe fallback.
- `scripts/fit_gemma_cost_model.py` fits observed E2E speedup against
  prefill-only and prefill+vision ceilings across the existing cost-model
  artifacts.

Speculative-admission simulation on H7 active-repair rows:

| fast arm / abort rule | cache E2E | no-cache E2E | Delta acc | abort rate | harmed recall |
|---|---:|---:|---:|---:|---:|
| random_seed11 / parse_failure | `1.139x` | `1.125x` | `-0.0333` | `0.033` | `0.25` |
| random_seed11 / non_letter | `0.900x` | `0.794x` | `+0.0000` | `0.467` | `0.75` |
| random_seed11 / parse_failure_or_margin_lt_0.5 | `0.936x` | `0.841x` | `-0.0667` | `0.367` | `0.50` |
| fixed_uniform / parse_failure | `1.026x` | `0.983x` | `-0.0667` exploratory | `0.133` | `0.50` |
| fixed_uniform / non_letter | `0.903x` | `0.804x` | `-0.0333` exploratory | `0.433` | `0.833` |
| fixed_uniform / parse_failure_or_margin_lt_0.5 | `0.896x` | `0.805x` | `-0.0333` exploratory | `0.400` | `0.833` |

The fixed-uniform rows use the random no-admission artifact as the safe arm and
were run with `--allow-dense-label-drift`; their pairing audit reports seven
dense-label mismatches. Treat fixed-arm Delta acc as exploratory only. The
random arm has a stable dense reference and is the primary accuracy readout.

Interpretation: parse-failure gating is cheaper than double-pass active
repair, but it is not yet the "1.20x near-lossless" result. On the random arm
it improves accuracy loss from `-0.0667` to `-0.0333`, but catches only one of
four harmed rows. The fixed arm is useful for signal/timing texture but not for
a clean accuracy claim because its dense reference drifts relative to the safe
arm. Non-letter and margin gates catch more harmed rows, but their abort rates
are high enough to erase E2E speedup.

Parse-failure transfer screen:

| artifact | signal rate | harmed rows | harmed recall |
|---|---:|---:|---:|
| MVBench holdout full composition | `0.033` | 3 | `0.000` |
| MVBench dev moving_attribute kr100 composition | `0.067` | 4 | `0.250` |
| MVBench holdout moving_attribute kr100 composition | `0.033` | 2 | `0.000` |
| TOMATO holdout full composition | `0.000` | 7 | `0.000` |
| VideoMME holdout full composition | `0.033` | 4 | `0.000` |

This falsifies the strongest version of the parse-failure story on existing
artifacts. Parse failure is a low-cost guardrail for visible format collapse,
not a robust harm detector. A live speculative-admission implementation is
still worth a small smoke only if the goal is systems validation of the
vision-cache rollback path, not because the existing data predicts a clean
quality/speed win.

Cost-model fit:

- Across six existing cost-model artifacts, prefill-only ceiling has
  `R^2=0.489` against observed E2E and mean absolute relative error `0.188`.
- Prefill+vision ceiling has `R^2=0.971` and mean absolute relative error
  `0.033`.

Interpretation: the timing story is stronger when it is stated as a stage-cost
model, not as "admission alone explains everything." Admission-only MVBench
dev is essentially at its prefill-only ceiling. Full-composition rows require
charging both the prefill and vision stages; otherwise the model underpredicts
MVBench composition speedups and overstates what admission-only scheduling can
deliver.

Revised next-experiment gate:

- Do **not** launch a full speculative-admission validation as the next
  headline experiment. The parse-failure signal does not transfer on existing
  artifacts.
- If implemented, run only an `N_ITEMS=1` or similarly bounded MLX smoke first
  to verify that encoder features can actually be reused across admission-on
  and no-admission prefill without changing outputs or corrupting timing.
- The next substantive live run remains cross-benchmark, same-run,
  admission-only cost accounting: MVBench hosted-dev, TOMATO N=30, and
  VideoMME short N=20. Speculative admission can be added as a secondary row
  only after the cache-reuse smoke passes.

### H8 Multi-Shot Consistency Gate, Timing Check Only

Multi-shot consistency is a plausible future variant: run two cheap admission
passes with different random masks, accept if they agree, and retry dense if
they disagree. The literature gap is attractive, but the first-order timing
model is unfavorable under full E2E accounting:

```text
two cheap passes at 1.45x each cost about 2 / 1.45 = 1.38 dense units
before any fallback retry.
```

Therefore H7 is **not** ready for implementation as a VLM experiment. Before
any code branch, it needs either (a) measured work reuse that makes the second
cheap pass much cheaper than the first, or (b) a different design where the
second pass is a nearly-free verifier rather than another full VLM call.

Preregistered gate before implementation:

- Accept for implementation only if a CPU/timing model or measured n=1 smoke
  shows expected E2E speedup `>1.0` after charging both cheap passes and the
  predicted dense fallback rate.
- Falsify as an E2E speedup path if the second cheap pass is another full
  Gemma call with no reusable vision/prefill work.

### Not Yet Implemented

- QuoTA/QTSplus-style scalar query allocation.
- VideoRouter-style coverage-versus-detail policy.
- Live one-step active repair / confidence-gated rerun.
- Holdout or hosted-dev validation of the live
  `moving_attribute`-safe class-conditional admission cell.
- Model-facing codec-grid pruning or sidecar-backed C-VISION.
- Multi-shot consistency as an efficiency gate; current status is timing-model
  only, not experiment-ready.

Those require new preregistered branches after Q1c and hosted-dev evidence.
