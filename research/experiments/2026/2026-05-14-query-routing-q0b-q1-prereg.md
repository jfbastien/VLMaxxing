# 2026-05-14 query-routing Q0b/Q1 implementation prereg

Status: **Q0b/Q1/Q1b measured; Q1c admission-scheduler follow-up implemented,
not yet measured; hosted-dev breadth sweep, codec-motion scan, and
active-repair confidence-probe scaffolding implemented, not yet measured**.

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

- Margin field: `composed_first_generated_candidate_top2_margin` by default.
  Full-vocabulary top-2 margin is logged as a secondary diagnostic, but it can
  be dominated by formatting/punctuation tokens and is not the default gate.
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

### H7 Multi-Shot Consistency Gate, Timing Check Only

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
- Model-facing codec-grid pruning or sidecar-backed C-VISION.
- Multi-shot consistency as an efficiency gate; current status is timing-model
  only, not experiment-ready.

Those require new preregistered branches after Q1c and hosted-dev evidence.
