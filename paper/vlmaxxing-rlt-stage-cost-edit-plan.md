# VLMaxxing + RLT Stage-Cost Paper Edit Plan

Status: ready for manuscript editing
Created: 2026-05-25
Scope: paper integration plan only; no new experimental claims are introduced here.

## Decision

Move to paper editing for the VLMaxxing + RLT update. Do not keep expanding the
local M3 query-routing thread before editing.

The edit should make the paper feel as if the RLT and stage-cost experiments
were part of the original design, not a late add-on. The central paper move is:

> Token count does not predict wall-clock speedup. Stage share does. RLT is
> useful when it cheaply shortens a stage that owns runtime; paired answer
> checks decide whether that speed is usable.

This is not a query-aware-routing paper. Query-aware routing, active repair, and
text-rule routing should be treated as boundary evidence and future-work seeds.
The reproducible paper value is stage-cost accounting plus RLT as a cheap
C-VISION scorer and composition primitive.

## Evidence Basis

Use only the current artifact-backed evidence:

- `paper/framing.md`
- `paper/claim-matrix.md`
- `paper/publishability-status.md`
- `research/experiments/2026/2026-05-14-vlmaxxing-rlt-closeout-prereg.md`
- `research/experiments/2026/2026-05-20-vlmaxxing-rlt-cost-accounting-closeout.md`
- `research/experiments/2026/artifacts/rlt_m3_cost_accounting_followup/cost_model_fit_n19.json`
- `research/experiments/2026/artifacts/rlt_followup_queue/`
- `research/experiments/registry.md`

The raw chat/review discussions are not source material for the paper. They are
useful only as prompts to verify claims against the files above.

#### Exact artifact paths and key paths (verified 2026-05-25)

Every headline number below was read directly from the committed artifacts.
Generators and table authors must read these exact paths/keys, not rounded
values transcribed from prose. All paths are under
`research/experiments/2026/artifacts/`.

Stage-cost model (evidence-plumbing slice, Result 1):

- `rlt_m3_cost_accounting_followup/cost_model_fit_n19.json`
  - `n_artifacts` = 19
  - `models.observed_e2e_vs_prefill_plus_vision_ceiling.r2` = 0.9709678 (prose `~= 0.971`)
  - `error_summaries.prefill_plus_vision_ceiling.mean_abs_relative_error` = 0.017225 (1.72% MARE)
  - `error_summaries.prefill_plus_vision_ceiling.max_abs_relative_error` = 0.078469 (7.85% max rel)
  - Do NOT use `models.observed_e2e_vs_prefill_plus_vision_ceiling.max_abs_error` = 0.0963; that is absolute speedup-space error, not relative.
  - The six selected rows live under the top-level `rows` list keyed by `label`; all six labels confirmed present.

RLT-as-C-VISION scorer rows (Result 2 / Table 2), keep-rate 0.5, n=30 each:

- `rlt_followup_queue/cvision_rlt_videomme_analysis.json`,
  `cvision_rlt_tomato_analysis.json`, `cvision_rlt_mvbench_analysis.json`
  - E2E speedup: `all.actual_e2e_speedup_dense_over_sparse`
    = 1.0581 / 1.3153 / 1.4018 (VideoMME / TOMATO / MVBench)
  - CI: `all.actual_e2e_speedup_dense_over_sparse_ci95`
  - Delta accuracy: `all.accuracy_delta_sparse_minus_dense` = +0.0333 / -0.0333 / +0.0333
    (all three CIs in `..._ci95` cross zero)
  - RLT scorer cost: `all.mean_sparse_scorer_total_ms` = 19.18 / 20.83 / 36.32 ms/item
- Expensive comparator (max-min diversity scorer):
  `cvision_maxmin_videomme_analysis.json`, `cvision_maxmin_tomato_analysis.json`,
  `cvision_maxmin_mvbench_analysis.json`
  - `all.mean_sparse_scorer_total_ms` = 2334.06 / 2379.89 / 2942.94 ms/item
  - Derived RLT cost advantage: 122x / 114x / 81x cheaper.
- Cheap-scorer honesty check (do not omit): the `magnitude` scorer
  (`cvision_magnitude_videomme_analysis.json`) reports
  `all.mean_sparse_scorer_total_ms` = 0.0 (precomputed, not charged in the loop),
  and `magnitude_valid` reports ~1100 ms. RLT is therefore NOT the cheapest
  scorer; it is ~80-120x cheaper than the expensive learned-diversity scorer.
  Claim only that; do not claim RLT is universally cheapest.

Composition frontier (Result 3 / Table 3), pooled dev+holdout n=60:

- Aggressive (direct): `rlt_followup_queue/full_composition_rlt_combined_{videomme,tomato,mvbench}_analysis.json`
  - E2E: `summary.e2e_speedup_dense_over_composed` = 1.0289 / 1.2329 / 1.8419
  - Delta accuracy: `summary.accuracy_delta_composed_minus_dense` = -0.0667 / -0.0667 / -0.1167
  - CI: `summary.accuracy_delta_ci95`; MVBench CI [-0.2167, -0.0167] EXCLUDES 0
  - `summary.pass_fidelity` = false / false / false. All aggressive rows
    must be shown as fidelity-gate failures, not only MVBench.
  - `summary.pass_bucket_quality_and_e2e` = false / false / false, with
    bucket failures: VideoMME `long`, `medium`; TOMATO `direction`,
    `rotation`; MVBench `action_localization`, `moving_attribute`,
    `object_interaction`.
- Rescue: `rlt_followup_queue/full_composition_rlt_rescue_combined_{videomme,tomato,mvbench}_analysis.json`
  - E2E: `summary.e2e_speedup_dense_over_composed` = 1.0784 / 1.2374 / 1.4328
  - Delta accuracy: `summary.accuracy_delta_composed_minus_dense` = -0.0500 / -0.0833 / -0.0500
  - CI: `summary.accuracy_delta_ci95`; all three CROSS 0
  - `summary.pass_fidelity` = true / false / true. TOMATO rescue is NOT a
    fidelity-passing row despite its CI crossing 0; it has
    `summary.pass_bucket_quality_and_e2e=false` with bucket failures
    `direction` and `rotation`.
  - `summary.pass_bucket_quality_and_e2e` = false / false / false, with
    bucket failures: VideoMME `long`, `medium`; TOMATO `direction`,
    `rotation`; MVBench `action_localization`, `moving_attribute`.

Denominator-collision warning: the pooled-n=60 composition rows above are a
DIFFERENT experiment from the `m3_*_compose` rows in `cost_model_fit_n19.json`
(n=20-30, same-run M3 cost-accounting). They will disagree in sign for TOMATO:
`m3_tomato_compose` shows Δacc = +0.067 (small-sample, choice-churn caveat),
while pooled `full_composition_rlt_rescue_combined_tomato` shows Δacc = -0.083.
Both are correct for their own slice. The manuscript must never place these two
TOMATO composition numbers in the same table or paragraph without naming the
distinct slice and n; otherwise a reviewer sees a contradiction. Prefer the
pooled n=60 rows for the composition-frontier table and the M3 rows only for
the stage-cost-model fit table. The cost-accounting generator must hard-fail if
the `m3_tomato_compose` selected row's `source_paths` list does not exactly
match the expected M3 cost-accounting artifact path in the source-path map
below, because that is the guard against silently pulling the pooled
sign-disagreeing TOMATO row into the M3 table.
If both Table 1 and Table 3 appear in the same results section, add explicit
cross-section disambiguation prose: Table 1 uses same-run M3 cost-accounting
cells (`m3_tomato_compose`, n=30, timing/boundary evidence), while Table 3 uses
pooled dev+holdout composition-frontier cells (n=60, rescue TOMATO remains a
fidelity-gate failure). The table captions must carry those slice labels; do
not rely on the surrounding paragraph alone.

## Validated Editorial Claims

| Claim | Verdict | Evidence class | Manuscript action |
| --- | --- | --- | --- |
| Stage-cost accounting is the strongest RLT/VLMaxxing narrative spine. | Valid. | Reproduced here. The n=19 prefill+vision model reports `R^2 = 0.97097`, 1.72% mean absolute relative error, and 7.85% max absolute relative error across observed E2E speedups from about 0.98x to 1.78x. | Put the predicted-vs-observed speedup result early and make it the main explanatory figure. |
| RLT-as-C-VISION is the cleanest direct RLT result. | Valid, bounded. | Reproduced here. RLT reaches the speed class of expensive scorers while costing tens of ms/item rather than seconds/item. | Add an RLT scorer table. Say "same speed class at far lower scorer cost", not "RLT dominates". |
| Full RLT composition is a frontier, not a clean universal win. | Valid. | Reproduced here. Aggressive MVBench composition reaches the high-speed frontier but has statistically decisive quality cost; rescue composition is safer but still bucket-caveated. | Add a small frontier table that separates aggressive speed frontier from rescue operating point. |
| The H3B prompt-admission regression is a useful negative result. | Valid. | Reproduced here / systems diagnostic. The result shows token reduction can regress wall-clock when the runtime changes kernel path. | Keep as a compact systems lesson: token reduction is not speed unless the substrate makes the shortened stage faster. |
| Query-aware routing is solved. | Reject. | Boundary evidence. Static typed routing and active repair did not clear gates; text routing is post-hoc and does not transfer. | Compress routing into a boundary/future-work subsection or appendix. |
| "Random vision pruning is exact-output equivalent" as a broad claim. | Weaken. | Narrow reproduced-here evidence only. It applies to specific random-valid/no-admission controls and must name whether identity is raw text or parsed choice. | Use narrow wording: "On the audited Gemma controls, random vision masking changed little or nothing while buying little E2E speed." Do not generalize to all models/workloads. |
| VideoMME-short admission rows are clean fidelity wins. | Valid only as parsed-choice fidelity. | Reproduced here. Parsed choices are 20/20 identical for selected keep-rate rows; raw text identity is not established for all rows. | State "parsed-choice identical", not "byte-identical" or "lossless". |
| MVBench hosted and TOMATO admission/composition rows are clean quality wins. | Weaken. | MVBench hosted admission is timing-only evidence; TOMATO composition is timing/boundary evidence. Aggregate accuracy may pass, but choice churn and bucket caveats remain. | Use them for cost-model validation and boundary evidence, not as headline fidelity rows. |
| M5 should be broad discovery. | Reject. | Hypothesis / future confirmation. Current scoped wrapper is for scale confirmation. | Keep M5 as optional scale confirmation: n=1 smoke, VideoMME n=30 RLT C-VISION, optional scorer tier. |

Precision rule: use `R^2 = 0.97097` in source/provenance tables and `R^2 ~= 0.971`
in prose captions. Do not mix additional rounded variants.

## Reader-Facing Thesis

The manuscript should explain the work in simple stage language before using
project terms:

- The video model first computes visual features.
- The language model then reads visual placeholders plus the question.
- The language model then writes the answer.
- A pruning method only speeds up the stages it actually shortens.
- RLT is useful because it is a cheap way to select or admit visual evidence.
- The speed is only publishable when paired answer checks show the model still
  answers the same task.

The short abstract-level phrasing should be:

> We turn VLM pruning from a token-count claim into a stage-accounting problem:
> which stage got shorter, how much of the request did that stage own, and did
> the answer stay acceptable?

Avoid the jargon stack "stage-cost C-VISION admission primitive" in first-use
prose. Introduce the plain operation first, then name it.

## Manuscript Restructure

### Editorial staging: plumbing first, manuscript integration second

This plan is staged only to keep reviews tractable. The evidence-plumbing slice
below is NOT the finished paper edit. It is acceptable as a preparatory commit
only if the next manuscript slice immediately rewrites the abstract,
introduction, method framing, setup labels, and first results ordering around
stage accounting. Stopping after the generated table would fail the user's
"as if run from the start" requirement.

Acceptance criteria for the actual manuscript integration:

1. The abstract opens on the runtime-bill problem and the n=19 stage-cost
   result, not on experiment history or C-PERSIST alone.
2. The introduction asks "which stage got shorter?" before introducing project
   names.
3. The method defines the runtime stages and cost equation before RLT,
   admission, composition, or C-PERSIST.
4. The first results figure/table is predicted-vs-observed E2E speedup or its
   compact table form.
5. Query-aware routing appears only as boundary/future-work evidence, not as a
   third main regime.
6. The edit is length-neutral or shorter under the size-control gate below.

If a future editor wants a single larger commit instead of staged commits, merge
the evidence-plumbing slice and the manuscript-integration slice. Do not merge
only the plumbing slice and call the paper updated.

### Evidence-plumbing slice: integrate without growing the paper

The first edit should be a narrow, source-backed manuscript pass rather than a
large rewrite. The minimum strong integration is:

1. Add a generated snapshot:
   - `paper/arxiv/generated/data/rlt_cost_accounting_snapshot.json`
   - Source from `research/experiments/2026/artifacts/rlt_m3_cost_accounting_followup/cost_model_fit_n19.json`
     plus the May 20 closeout note.
   - Keep it separate from `measured_sparse_execution_snapshot.json`; this is
     prefill+vision admission accounting, not pure sparse vision execution.
   - Update `paper/arxiv/scripts/sync_sources.py` in the same manuscript edit so
     this snapshot and its table are regenerated by the normal paper pipeline.
   - Read row-level artifact data from the top-level `rows` key in
     `cost_model_fit_n19.json`; there is no `cells` key.
2. Add one compact generated table:
   - `paper/arxiv/generated/tables/rlt_cost_accounting.tex`
   - Caption carries the summary: prefill+vision model fit over 19 cells,
     selected rows shown in the table body, `R^2 ~= 0.971`, 1.72% MARE, 7.85%
     max error. The 7.85% max-error number is for the full 19-cell fit, not the
     maximum over the six displayed rows.
   - Select exactly these row labels from the artifact:
     `m3_videomme_no_adm`, `m3_videomme_kr07`, `m3_videomme_kr03`,
     `m3_videomme_compose`, `m3_mvbench_kr07`, and `m3_tomato_compose`.
   - Fidelity labels do not come from `fidelity_verdict` in the artifact
     because that field is absent for these rows. The generator must attach a
     small curated evidence-class mapping sourced from the May 20 closeout:
     `m3_videomme_no_adm` = `denominator control`; `m3_videomme_kr07` and
     `m3_videomme_kr03` = `parsed-choice clean`; `m3_videomme_compose` =
     `timing/boundary`; `m3_mvbench_kr07` = `timing only`;
     `m3_tomato_compose` = `timing/boundary`.
     Any "composition choice churn" or "aggregate positive" phrasing belongs in
     a table note derived from artifact fields, not in the source-backed
     `evidence_status` label.
   - Because `m3_tomato_compose` is one of the selected rows, the table must
     include a note showing the observed positive aggregate accuracy delta with
     a choice-churn caveat. Source the note to
     `accuracy_delta_composed_minus_dense` from the top-level row and
     `summary.choice_agreement` from the artifact named by that row's input `source_path`. Do not
     put this note in `evidence_status`, and do not imply composition always
     improves quality.
3. Add the generated RLT cost-accounting table near the current C-CEILING
   residual table with one short paragraph.
4. Preserve the existing C-CEILING numeric residual evidence. Do not remove the
   in-body manual `tab:vshare-ceiling-residuals` table in the first slice unless
   its row-level content is first copied into a machine-readable generated
   source, an appendix table, or an explicit source-traceability table. The n=19
   RLT table extends C-CEILING; it does not replace the prior Qwen/Gemma
   C-CEILING rows by itself.
   Second-pass retirement path for this paper update: keep the manual table
   permanently unless a later dedicated refactor extracts the old residual rows
   into a generated `c_ceiling_residuals` source/table. No commit should delete
   it without that replacement home.
5. Do not add a new intro regime row, a new experimental lane, or a headline
   table row in the first pass. This evidence strengthens C-CEILING; it is not a
   fourth regime.
6. Add source traceability for the new generated table in
   `paper/arxiv/sections/appendix_a_source_traceability.tex`.
7. Re-check `paper/AGENTS.md`, `paper/README.md`, `paper/framing.md`, and
   `paper/narrative-rules.md` after the manuscript slice lands so the paper
   routers still point at the stage-cost/RLT spine.

This slice gives the paper the new science while keeping length controlled: add
the generated RLT cost-accounting table beside the existing C-CEILING evidence,
then remove or move lower-value prose only after the old residual rows have a
safe generated or appendix home.

### Abstract: rewrite around the runtime bill

Current issue: the abstract centers the earlier C-PERSIST and cross-architecture
story before the RLT/stage-accounting result is visible.

Edit:

1. Open with the denominator problem: pruning papers often report token
   reductions or local stage wins, while users pay end-to-end runtime.
2. State the stage-cost result: across 19 Gemma cells, the prefill+vision model
   predicts E2E speedups with `R^2 ~= 0.971` and 1.72% mean absolute relative
   error.
3. State the RLT result: RLT is a cheap C-VISION scorer that reaches the speed
   class of expensive diversity scoring at roughly two orders of magnitude lower
   scorer cost.
4. Keep C-PERSIST, but give it one sentence as a separate regime: large
   follow-up gains exist when the same video is already ingested; first-pass
   gains obey the stage-cost bill.
5. Name the caveat in the abstract-level evidence class: composition is a
   speed/quality frontier, not a universal lossless win.

Remove or shorten:

- Any abstract wording that implies token count itself is the explanatory
  variable.
- Any "lossless" wording unless the row is raw-output audited; otherwise use
  "parsed-choice identical" or "aggregate accuracy preserved".

Justification: the abstract should give the reader the money shot and the
denominator in the same breath.

### Introduction: make stage accounting the question the reader holds

Current issue: the introduction leads with stable-video reuse, then introduces
several regimes. The RLT result would read like a patch if simply appended.

Edit:

1. Replace the opening problem with:
   - "Pruning fewer tokens is not the same as speeding up a VLM."
   - "The relevant question is which runtime stage the method shortens."
2. Introduce the two physical regimes plus boundary diagnostics as a table, not
   a long taxonomy:
   - First-pass vision/prefill pruning.
   - Same-video follow-up reuse.
   - Boundary diagnostics and future forks, including query-aware routing.
3. Move the largest C-PERSIST number out of the opening hook and into the
   regime table or results preview. It remains important, but it is not the
   first-pass RLT story.
4. Add a compact "what we found" paragraph:
   - RLT cheaply scores visual redundancy.
   - Aggressive composition creates a speed/quality frontier.
   - A stage-cost model predicts when either matters.
5. Add anti-claims near the contribution list:
   - Not SOTA accuracy.
   - Not broad sparse-backend coverage.
   - Not query-aware routing solved.
   - Not "full composition is lossless".

Remove or shorten:

- Repeated explanations of C-terms before the reader sees why they matter.
- Any historical sequencing that implies the paper followed the same order as
  the experiments.

Justification: the reader should understand the scientific question before
meeting internal method names.

### Method: define physical operators by the stage they shorten

Current issue: the method has pieces of C-CEILING and C-VISION accounting, but
the new RLT/admission evidence needs one coherent cost model.

Edit:

1. Add a "Runtime bill" subsection before the specific mechanisms:
   - video decode / input handling,
   - vision encoding,
   - LM prefill / prompt reading,
   - answer generation.
2. Add the prefill+vision E2E prediction:

   ```text
   predicted_speedup =
     1 / ((1 - P_share - V_share) + P_share / P_speedup + V_share / V_speedup)
   ```

   Define every term in plain language. State that the equation is a ceiling
   model for touched stages, not a quality guarantee.
3. Introduce operators by physical effect:
   - RLT-as-C-VISION: uses run-length-like raw-frame redundancy to choose visual
     evidence cheaply.
   - Placeholder/prefill admission: feeds the LM fewer visual placeholders, so
     prompt reading is shorter.
   - Composition: applies both levers and must be measured, not inferred by
     multiplying component speedups.
   - C-PERSIST: reuses same-video state for follow-up questions, a different
     denominator.
4. Move query-routing implementation details out of the main method unless they
   are needed to explain a negative-control result.
5. Add one sentence explaining scorer cost accounting: a scorer that takes
   seconds can erase the runtime it saves, so scorer time is charged.

Remove or shorten:

- Duplicate C-CEILING derivations that only cover vision share after the broader
  stage model is introduced.
- Internal naming before plain operation.

Justification: this makes the paper's math explain both wins and failures, and
it prevents token-count overclaims.

### Experimental Setup: make evidence classes auditable

Current issue: some rows are clean fidelity evidence; others are timing or
boundary evidence. The manuscript needs this distinction before readers see the
tables.

Edit:

1. Add a short "evidence labels" paragraph:
   - clean fidelity row,
   - timing/model-fit row,
   - speed frontier with quality cost,
   - boundary/diagnostic row,
   - imported result.
2. State that all headline speedups use paired timing where possible and charge
   scorer cost.
3. State that "answer-identical" means parsed-choice identity unless raw text
   identity is explicitly named.
4. Add a small note on same-run vs pooled dev/holdout rows so speedup tables do
   not mix denominators silently.
5. Update the existing "First-pass pruning" lane to mention admission and
   cost-accounting controls; do not add a new lane for RLT/admission controls.
6. In the metrics paragraph, state that admission rows report
   observed-vs-predicted E2E and paired parsed-choice agreement.

Remove or shorten:

- Repeated caveats in each result paragraph once the evidence-label system is
  established.

Justification: reviewers will trust stronger claims if weaker rows are labeled
before they are useful.

### Results: reorder around the cost model

Current issue: the current cross-architecture results section predates the RLT
closeout and does not foreground the n=19 model.

Edit to this order:

1. **Result 1: End-to-end speed follows stage share, not token count.**
   - Put the n=19 predicted-vs-observed figure first.
   - State `R^2 ~= 0.971`, 1.72% mean absolute relative error, 7.85% max error.
   - Explain one positive and one negative example:
     - MVBench/TOMATO rows move when vision/prefill owns enough runtime.
     - VideoMME-long does not move because the shortened stages do not own
       enough runtime.
2. **Result 2: RLT is a cheap C-VISION scorer.**
   - Add table with VideoMME, TOMATO, MVBench RLT rows.
   - Include E2E speedup, delta accuracy, vision reduction, scorer cost, and
     a comparator cost column for max-min.
   - State "same speed class as expensive diversity scoring" only where the
     evidence supports it.
3. **Result 3: Composition gives a speed/quality frontier.**
   - Small table: aggressive composition vs rescue composition for VideoMME,
     TOMATO, MVBench.
   - Put MVBench 1.84x in the frontier row with decisive quality cost.
   - Put MVBench 1.43x rescue as the safer paper operating point with bucket
     caveats.
4. **Result 4: Large same-video gains are a different regime.**
   - Keep C-PERSIST as the large follow-up result, but frame it as "when the
     video has already been paid for".
   - Do not let C-PERSIST obscure the first-pass stage-cost story.
5. **Result 5 / Appendix boundary: smarter routing was not enough.**
   - Static typed routing failed against fixed/random controls.
   - Active repair had directional margin signal but no viable threshold after
     retry cost.
   - Text routing is post-hoc and template-leaky.
   - This subsection must not appear in the contribution list or operator
     table; it is a boundary that protects the main claim.

Remove or move:

- Move the current Qwen-routing-heavy section to a shorter boundary section or
  appendix unless it directly supports a main claim.
- Move excessive per-bucket detail into generated tables or appendix.

Justification: the strongest result should teach the reader how to read every
other result.

### Related Work: position by accounting, not by novelty adjectives

Current issue: related work risks becoming a long list. The paper needs to
separate "what token selection method" from "what runtime stage did it shorten".

Edit:

1. Add a paragraph on token-pruning evaluation discipline:
   - random/fixed baselines matter,
   - actual latency matters,
   - token count and FLOPs are insufficient.
2. Add RLT original work as the source of the run-length-tokenization idea, then
   state our different use: a cheap scorer/admission prior inside a frozen VLM
   runtime.
3. Group FastV, SparseVLM, QuoTA, QTSplus, Q-Frame, Static or Dynamic,
   VideoRouter, CodecSight, and CoPE-VideoLM by the stage or evidence operator
   they touch.
4. Add one database analogy paragraph only if it earns space:
   - System R-style cost accounting is the analogy for choosing operators under
     a runtime bill.
   - Do not turn this paper into a query-planning survey.

Remove or shorten:

- Repetitive "our work differs because..." sentences for each related method.
- Any related-work paragraph that cannot be tied to the stage accounting claim
  or a required baseline.

Justification: reviewers should see that the field is crowded, and that this
paper's contribution is the accounting denominator plus measured controls.

#### Reference accuracy and bibliography gate (verified 2026-05-25)

All cited works below are real (none hallucinated), but local bibliography
coverage is incomplete. Before any related-work rewrite ships, add the missing
`\bibitem` entries or remove the corresponding prose cite. This is a hard gate:
an accurate plan with missing references still produces an unreviewable
manuscript.

Required bibliography status:

| Work | Primary source | `90_references.tex` status | Manuscript rule |
| --- | --- | --- | --- |
| RLT | `2411.05222`, NeurIPS 2024 Spotlight | Present as `\bibitem{rlt}` after this plan hardening. | Required. This is the source of the run-length idea. |
| QuoTA | `2503.08689`, AAAI 2026 | Missing. | Add only if cited; do not use the unverified 50%->1.08x ratio without a source table. |
| QTSplus | `2511.11910` | Missing. | Add if citing the 89% compression / 28% latency result. |
| Q-Frame | `2506.22139`, ICCV 2025 | Missing. | Add if the query-aware boundary paragraph cites it. |
| Static or Dynamic | `2504.21403`, EMNLP 2025 main | Missing. | Use this exact name; add if cited. |
| VideoRouter | `2605.05848` | Missing. | Add if cited as trained query-adaptive routing prior. |
| Token-pruning critique | `2502.11501`, Findings ACL 2025 | Missing. | Add if using the random/fixed-baseline discipline claim. |
| System R | Selinger et al., SIGMOD 1979 | Missing. | Add only if the database analogy earns space. |
| Eddies | Avnur and Hellerstein, SIGMOD 2000 | Missing. | Add only if adaptive query-routing analogy earns space. |
| PARQO | `2406.01526`, VLDB 2024 | Missing. | Add only if robust-plan analogy earns space. |
| CodecSight | `2604.06036` | Present. | Scope as streaming inference. |
| CoPE-VideoLM | `2602.13191` | Present. | Scope as codec primitives, not positional encoding. |

The following corrections MUST be applied before any related-work prose ships,
because the current characterizations contain errors a reviewer will catch:

- RLT (`2411.05222`, NeurIPS 2024 Spotlight): full title is "Don't Look Twice:
  Faster Video Transformers with Run-Length Tokenization". `\bibitem{rlt}` is
  now present in `90_references.tex` (verified 2026-05-25). Since RLT is the
  source of the run-length idea this paper builds on, keep the citation in any
  RLT-related prose. It operates training-free OR with fine-tuning; do not call
  it simply "training-free".
- CoPE-VideoLM (`2602.13191`): do not confuse this paper with unrelated
  positional-encoding CoPE work. This paper uses video codec primitives,
  specifically motion vectors and residuals, and aligns codec-derived tokens to
  image-encoder embeddings. Any "position-encoding" phrasing is FALSE and must
  be removed.
- CodecSight (`2604.06036`): it is a streaming-VLM inference system using codec
  metadata for patch pruning and selective KV-cache refresh, not a general
  "video understanding" system. Frame it as streaming-inference-efficiency.
- QuoTA (`2503.08689`, AAAI 2026): query-oriented token assignment via CoT query
  decomposition. The QuoTA paper's own headline is "+3.2% average across six
  benchmarks at identical token budget" (matches `docs/related-work-table.md`),
  NOT a compression/latency ratio. The "50%->1.08x" external-validation pairing
  that circulated in review discussion does NOT currently appear in any
  `sections/*.tex` (verified 2026-05-25). Forward guard: if a future external-
  validation paragraph reproduces QuoTA in the cost-model section, the specific
  speedup ratio must be sourced from the QuoTA paper before it ships; do not
  transcribe it from discussion. The QTSplus "89%->28%" pairing (`2511.11910`)
  is confirmed against the source and is safe to cite.
- PARQO (`2406.01526`, VLDB 2024): full name "Penalty-Aware Robust Plan
  Selection in Query Optimization"; uncertain selectivity is the setting, while
  user-definable penalty metrics and sensitivity-aware robust plan selection are
  the distinctive mechanism. Only cite if the database analogy earns its single
  paragraph.
- Confirmed accurate as characterized: FastV (`2403.06764`, ECCV 2024),
  SparseVLM (`2410.04417`, ICLR 2025), Q-Frame (`2506.22139`, ICCV 2025),
  Static or Dynamic (`2504.21403`, EMNLP 2025 main), VideoRouter (`2605.05848`),
  the token-pruning critique "Are We Solving the Right Problem?"
  (`2502.11501`, Findings of ACL 2025), System R (Selinger et al., SIGMOD 1979),
  Eddies (Avnur & Hellerstein, SIGMOD 2000).
- The token-pruning critique's strongest verified claim is that many pruning
  methods underperform random selection; cite it specifically for the
  random/fixed-baseline discipline, which directly supports our negative-control
  framing. Note the repo's `docs/related-work-table.md` already tracks TWO
  distinct random-baseline papers: the ACL Findings 2025 critique "Are We Solving
  the Right Problem?" (`2502.11501` / `2025.findings-acl.802`) and the separate
  preprint "All You Need Are Random Visual Tokens?" (`2512.07580`, DivPrune+random
  keeps 96.9% of Qwen2.5-VL-7B at 50% pruning). Both are legitimate; the
  negative-control paragraph may cite either or both, but must attribute the
  specific numeric claim to the correct paper. The bibliography-status table
  above tracks `90_references.tex` bibitem presence, not planning-doc coverage:
  these critiques are already in `related-work-table.md` but still need a
  `\bibitem` before the manuscript can `\cite` them.

### Discussion and Future Work: cut broad ambition, keep decision rules

Current issue: the discussion can drift into VLM-native media and query-planning
future work. That weakens the paper by making it sound less finished.

Edit:

1. Lead with practitioner decision rules:
   - measure the runtime bill,
   - prune the stage that owns the bill,
   - charge the scorer,
   - verify paired answers,
   - do not multiply component speedups without measuring composition.
2. Keep M5 as optional scale confirmation:
   - n=1 smoke,
   - VideoMME n=30 RLT C-VISION,
   - optional scorer tier.
   - No M5 query routing, active repair, or broad composition by default.
3. Mention query-aware routing as a future fork:
   - promising frame,
   - current evidence is diagnostic/boundary,
   - future work must beat fixed/random, no-admission controls, RLT-only, and
     same-run stage accounting.
4. Compress the speculative-admission/conformal ideas to a short future-work
   paragraph if they remain.

Remove or shorten:

- Long roadmap material not needed to defend the current paper.
- Any phrase implying the query-aware branch is already a second paper.

Justification: the discussion should help a practitioner decide what to run,
and help a reviewer see the paper's boundaries.

### Limitations and Reproducibility: name the narrow identities

Current issue: several attractive shorthand phrases can become false if they
lose the fidelity denominator.

Edit:

1. Add a short limitation that VideoMME-short admission rows are parsed-choice
   clean, not raw-output identical unless raw text was explicitly audited.
2. State that MVBench hosted admission rows are timing-only cost-model evidence
   and TOMATO composition rows are timing/boundary evidence with choice-churn or
   bucket caveats, not clean quality-frontier rows.
3. State that random-valid no-admission rows are denominator controls, not a
   broad claim that random pruning is always behaviorally identical.

Justification: this lets the main results stay punchy without hiding fidelity
boundaries.

### Conclusion: one sentence the reader remembers

Rewrite the conclusion around:

> Token reduction is not an efficiency result until it shortens an expensive
> runtime stage and preserves the paired answer.

Then summarize:

- RLT is a cheap way to target visual redundancy.
- Composition exposes a speed/quality frontier.
- Stage-cost accounting predicts which workloads benefit.
- Same-video follow-up reuse remains a separate high-gain regime.

## Figure And Table Plan

### Figure 1: Predicted vs observed E2E speedup

Job: show in five seconds that the cost model explains the speedups.

Data:

- n=19 Gemma cells from `cost_model_fit_n19.json`.
- x-axis: predicted E2E speedup from prefill+vision model.
- y-axis: observed E2E speedup.
- Diagonal y=x reference line.
- Color: physical operator class (`C-VISION/RLT`, `admission/prefill`,
  `composition`, `control`).
- Shape or outline: evidence class (`clean`, `timing`, `frontier`, `boundary`).
- Direct labels for outliers by exact row label plus human-readable display:
  `m3_tomato_compose` (`TOMATO composition, same-run M3`),
  `videomme_holdout_long` (`VideoMME-long composition`), and
  `mvbench_holdout` (`MVBench holdout composition`). Do not label a point
  only as "MVBench composition"; that phrase collides with multiple artifacts.

Caption must include:

- `R^2 ~= 0.971`,
- 1.72% mean absolute relative error,
- 7.85% max absolute relative error,
- "prediction uses stage shares and stage speedups; it is not a quality model."

Replace or demote:

- The older vision-share-only ceiling figure should become a subpanel, appendix
  figure, or historical stepping stone. It is too narrow to be the main result
  now.

Implementation note:

- If the first manuscript pass needs to stay minimally invasive, add the compact
  generated table first and leave `v_share_v_red_ceiling.*` unchanged. The
  predicted-vs-observed figure should replace the older vision-share-only figure
  in the second pass, or be added only if a lower-value figure/table is removed.
  Do not add it as extra furniture.

### Table 1: Operators, stages, and evidence status

Job: prevent jargon confusion.

Columns:

- Operation in plain English.
- Project name (`C-VISION`, `admission`, `composition`, `C-PERSIST`).
- Stage shortened.
- Best reproduced-here evidence.
- Fidelity status.
- Not claimed.

This table should appear near the method or at the start of results.

### Table 2: RLT as cheap C-VISION scorer

Job: show the practical RLT win.

Data source (verified): `rlt_followup_queue/cvision_rlt_{videomme,tomato,mvbench}_analysis.json`
for RLT rows and `cvision_maxmin_{...}_analysis.json` for the comparator, using
the exact keys listed in the Evidence Basis section. All rows are kr=0.5, n=30.

Rows:

- VideoMME RLT C-VISION (1.058x, Δacc +0.033, scorer 19.2 ms).
- TOMATO RLT C-VISION (1.315x, Δacc -0.033, scorer 20.8 ms).
- MVBench RLT C-VISION (1.402x, Δacc +0.033, scorer 36.3 ms).
- A required scorer-cost comparator column for max-min (2334 / 2380 / 2943 ms).

Columns:

- Benchmark.
- E2E speedup with CI (`all.actual_e2e_speedup_dense_over_sparse[_ci95]`).
- Delta accuracy with CI (`all.accuracy_delta_sparse_minus_dense[_ci95]`); note
  all three Δacc CIs cross zero, so state "no decisive accuracy change at n=30".
- Vision reduction from `all.vision_reduction`; do not substitute
  `all.vision_reduction_excluding_scorer` unless the caption explicitly says
  scorer overhead is excluded. The key choice must be deliberate even when the
  fields are numerically close.
- RLT scorer time (`all.mean_sparse_scorer_total_ms`).
- Max-min E2E speedup and delta accuracy from the same `all.*` keys.
- Expensive scorer time (max-min `all.mean_sparse_scorer_total_ms`).
- Interpretation.

Caption wording:

> RLT reaches the speed class of expensive learned-diversity scoring (max-min)
> while moving scorer cost from seconds to tens of milliseconds (~80-120x
> cheaper across the three benchmarks).

Do not say RLT dominates every scorer, and do not imply RLT is the cheapest
possible scorer: the magnitude scorer is effectively free (precomputed). The
honest claim is that RLT matches the expensive learned scorer's speed class at a
fraction of its cost, which is the comparator that actually competes on quality.
If the table omits max-min E2E and delta accuracy, weaken the caption to a pure
scorer-cost comparison and remove "speed class" from the table-level claim.

### Table 3: Composition frontier

Job: make the speed/quality tradeoff honest.

Data source (verified): `rlt_followup_queue/full_composition_rlt_combined_*`
(aggressive) and `full_composition_rlt_rescue_combined_*` (rescue), pooled
dev+holdout n=60, using `summary.*` keys from the Evidence Basis section. Use
these pooled n=60 rows, NOT the M3 `*_compose` rows from the cost-model fit
(see the denominator-collision warning).

Rows:

- Aggressive VideoMME (1.029x, -0.067), TOMATO (1.233x, -0.067),
  MVBench (1.842x, -0.117, CI excludes 0).
- Rescue VideoMME (1.078x, -0.050), TOMATO (1.237x, -0.083),
  MVBench (1.433x, -0.050, CI crosses 0).

Columns:

- E2E speedup (`summary.e2e_speedup_dense_over_composed`).
- Delta accuracy with CI (`summary.accuracy_delta_composed_minus_dense[_ci95]`).
- Fidelity verdict (`summary.pass_fidelity`) for every row. The table generator
  must display or snapshot-check the actual artifact verdicts: aggressive
  VideoMME/TOMATO/MVBench are all false; rescue VideoMME/MVBench are true;
  rescue TOMATO is false.
- Bucket verdict fields when present in the artifact:
  `summary.pass_bucket_quality_and_e2e` and `summary.bucket_failures`.
  All six composition rows have `pass_bucket_quality_and_e2e=false`; the
  manuscript table or caption must name the failing buckets instead of
  implying that aggregate fidelity passing is the full verdict.
- Caveat.

Required wording:

- "Speed frontier" for aggressive MVBench 1.84x.
- "Paper-safer operating point" for rescue MVBench 1.43x.
- Explicit bucket caveats for rescue. Do not describe any rescue row as
  globally fidelity-passing; VideoMME and MVBench pass the aggregate fidelity
  gate but still fail bucket gates. TOMATO rescue is stricter still: it is a
  speed-positive boundary row with both aggregate fidelity failure and
  direction/rotation bucket failures.
- If the M3 TOMATO composition row is included in this or the cost-accounting
  table, describe its positive aggregate delta as small-sample aggregate
  positive with choice-churn caveat, not as proof that composition improves
  quality.

### Box or small figure: H3B substrate cliff

Job: make the negative result memorable without bloating results.

Message:

> Token reduction can make wall-clock slower if it pushes the runtime onto a
> worse kernel/chunk path.

Use as a short mechanism box unless the figure budget allows a small timing
curve.

## Size-Control Plan

The edit should be same length or shorter. Target net change: -5% to 0% words.

This is a gate, not a preference. Before editing manuscript sections, record a
baseline word count for `paper/arxiv/sections/*.tex` (excluding generated
tables, bibliography, and build metadata). After the manuscript-integration
slice, rerun the same count. The slice fails review if the total increases
unless the commit message explicitly identifies the removed figure/table budget
that lands in the following commit. Evidence-plumbing commits may add generated
files, but they must not be described as the finished manuscript edit.

Cut budget to take before or with additions:

1. Compress Qwen/query-routing result prose into one boundary subsection before
   adding the RLT scorer and composition prose.
2. Move repeated roadmap/future-work bullets out of the discussion before
   adding M5/query-aware future-work language.
3. Replace repeated C-term explanatory paragraphs with the operator/stage table
   before adding new operator prose.
4. Collapse related-work one-method-per-paragraph novelty claims into grouped
   accounting paragraphs before adding the new RLT/query-adaptive citations.

Additions:

- Cost model figure and paragraph: +350 to +500 words.
- RLT scorer result: +300 to +450 words.
- Composition frontier table and paragraph: +250 to +350 words.
- Evidence-label paragraph: +100 to +150 words.

Cuts:

- Compress Qwen/query-routing results into boundary section/appendix: -600 to
  -900 words.
- Compress discussion roadmap and VLM-native media future work: -500 to -800
  words.
- Replace repeated C-term prose with operator table: -300 to -500 words.
- Remove duplicate caveats after evidence labels are introduced: -200 to -400
  words.
- Collapse related-work laundry list into grouped accounting paragraphs: -300 to
  -500 words.

Net effect: stronger paper, similar or shorter manuscript.

## Exact File-Level Plan

### `paper/AGENTS.md`

Modify:

- Keep the 2026-05-25 paper-position block aligned with this plan.
- Ensure the read order points manuscript editors at this plan for the
  VLMaxxing + RLT update.
- Keep query-aware routing described as boundary/future-work evidence.

Justification: this is the paper-local router. If it drifts, future agents will
edit from the old after-ingest-first spine.

### `paper/framing.md`

Modify:

- Promote "stage-cost accounting + RLT-as-cheap-C-VISION" to the active paper
  spine.
- Update the "Three Major Contributions" section heading and contribution names
  so the manuscript order is C-CEILING / stage-cost accounting, C-VISION /
  RLT-as-cheap-C-VISION, then C-PERSIST. If the local claim-ID list keeps
  C-PERSIST before C-VISION for historical continuity, it must explicitly say
  that list order is not the manuscript contribution order. Do not add
  composition as a fourth contribution.
- Keep C-PERSIST as a separate high-gain regime.
- Add anti-claims:
  - RLT does not dominate every scorer.
  - Aggressive composition is not fidelity-clean.
  - Query routing is not solved.
  - Parsed-choice identity is not raw-output identity.

Justification: this file is the source of truth for paper narrative boundaries.

### `paper/claim-matrix.md`

Modify:

- Add or update rows for:
  - n=19 prefill+vision stage-cost model,
  - RLT-as-C-VISION scorer-cost result,
  - aggressive vs rescue composition as boundary/frontier evidence,
  - H3B substrate cliff,
  - query-routing boundary result.
- Label each as reproduced here, diagnostic, advisory, or hypothesis.

Justification: every abstract/result claim needs provenance and evidence class.

### `paper/publishability-status.md`

Modify:

- Update the paper-ready claim list to include stage-cost accounting and RLT
  scorer cost.
- Add a reviewer-risk section for:
  - parsed-choice vs raw-output identity,
  - aggregate accuracy vs choice churn,
  - same-run vs pooled rows,
  - M5 still future confirmation.

Justification: prevents the manuscript from outgrowing what the evidence
supports.

### `paper/priority.md`

Modify:

- Make the next editorial milestone "RLT/stage-cost manuscript integration".
- Move query-aware routing to future fork.
- Keep M5 scoped as scale confirmation, not a blocker for paper editing.

Justification: aligns project execution with the new paper plan.

### `paper/arxiv/sections/01_abstract.tex`

Modify:

- Rewrite to lead with stage-accounted wall-clock prediction.
- Include n=19 cost-model result.
- Include RLT scorer-cost result.
- Include C-PERSIST as a separate same-video regime.
- Use conservative wording for composition.

Cut:

- Any unsupported "lossless" or broad exact-output language.

### `paper/arxiv/sections/02_introduction.tex`

Modify:

- Open with token count vs runtime bill.
- Add a compact operator/regime table or prose equivalent.
- Update contributions to exactly these three paper claims:
  1. stage-cost accounting,
  2. RLT cheap C-VISION,
  3. same-video C-PERSIST regime.
- Add composition frontier as a supporting result under the stage-cost/RLT
  claim, not as a fourth contribution. The aggressive and rescue rows teach
  the speed/quality frontier and denominator discipline; they do not overturn
  the source-of-truth contribution count.
- Add a separate boundary paragraph after the contribution list for
  query-aware/routing failures. Do not count it as a contribution.
- Replace the current C-CEILING contribution sentence with one that includes
  both the earlier Qwen composition audit and the n=19 Gemma/RLT prefill+vision
  audit.
- Do not add a new intro regime row for RLT/admission controls.

Cut:

- Historical experiment sequencing.
- Repeated C-term explanations.

### `paper/arxiv/sections/03_related_work.tex`

Modify:

- Add RLT original positioning.
- Tighten FastV/SparseVLM/token-pruning critique positioning.
- Group query-adaptive methods by evidence allocation stage.
- Add a short cost-based systems analogy only if it stays under one paragraph.

Cut:

- One-by-one novelty claims that do not affect the reader's interpretation.

### `paper/arxiv/sections/04_method.tex`

Modify:

- Add runtime-bill decomposition and prefill+vision formula.
- Define RLT, admission, composition, and C-PERSIST by physical stage.
- State scorer cost is charged.

Cut:

- Narrow vision-only ceiling derivation if duplicated by the broader model.

### `paper/arxiv/sections/05_experimental_setup.tex`

Modify:

- Add evidence labels and answer-identity definitions.
- Explain paired timing, scorer charging, and same-run/pooled distinctions.
- Update the existing first-pass pruning lane for admission/cost-accounting
  controls instead of adding a new lane.

### `paper/arxiv/sections/06_results_qwen_routing.tex`

Modify:

- Compress to boundary/diagnostic result.
- Preserve the negative science:
  - fixed/random controls matter,
  - typed routing did not win,
  - active repair did not survive cost gates.

Cut:

- Any prose implying this is a solved query-planning mechanism.

### `paper/arxiv/sections/07_results_cross_architecture.tex`

Modify:

- Add the n=19 cost-model figure and text as the first result in this section,
  or split into a new `07_results_stage_cost.tex`.
- Add RLT scorer-cost result.
- Add composition frontier result as supporting/boundary evidence under the
  stage-cost/RLT claim, not as a new contribution.
- Keep architecture-specific limits visible.
- First-pass implementation: add
  `\input{generated/tables/rlt_cost_accounting.tex}` near the current manual
  `tab:vshare-ceiling-residuals` and one short paragraph explaining that the
  May 20 Gemma/RLT audit extends C-CEILING from vision-only share accounting to
  prefill+vision stage accounting. Keep the manual residual table unless its
  rows are first given a generated or appendix home.

Cut:

- Older C-VISION text that repeats what the RLT/stage-cost table now explains.

### `paper/arxiv/sections/09_discussion_future_work.tex`

Modify:

- Turn discussion into practitioner decision rules.
- Add query-aware routing as future fork, not current paper claim.
- Add M5 scale confirmation as optional validation.

Cut:

- Broad future-work material not needed for the current paper.

### `paper/arxiv/sections/09_limitations_reproducibility.tex`

Modify:

- Add the parsed-choice/raw-output limitation for VideoMME-short.
- Add the timing-only limitation for MVBench hosted admission rows and the
  timing/boundary limitation for TOMATO composition rows.
- Add the denominator-control limitation for random-valid no-admission rows.

### `paper/arxiv/sections/10_conclusion.tex`

Modify:

- Close on "token reduction is not speed; stage-shortening plus fidelity checks
  is speed."
- Keep the conclusion short.
- Replace any generic "fresh-video pruning is smaller" sentence with the sharper
  point: fresh-video pruning and the Gemma/RLT admission audit are diagnostic
  because gains obey measured stage shares, not dropped-token counts.

### `paper/arxiv/sections/appendix_a_source_traceability.tex`

Modify:

- Add one source-traceability row for the Gemma/RLT cost-accounting table,
  pointing to the May 20 closeout note and `cost_model_fit_n19.json`.

### Generated assets

Add or update through the paper generation pipeline, not hand-edited generated
outputs when avoidable:

- `paper/arxiv/scripts/sync_sources.py`
- `paper/arxiv/scripts/build.py`, specifically `ARXIV_TABLE_FILES`, for any
  generated tables that must be included in paper bundles. Add
  `generated/tables/rlt_cost_accounting.tex` when that table is wired into the
  manuscript.
- `paper/arxiv/generated/data/rlt_cost_accounting_snapshot.json`
- `paper/arxiv/generated/tables/rlt_cost_accounting.tex`

Second-pass assets, not required for the first manuscript integration slice:

- `paper/arxiv/generated/figures/stage_cost_predicted_vs_observed.*`
- `paper/arxiv/generated/tables/rlt_cvision_scorer_cost.tex`
- `paper/arxiv/generated/tables/rlt_composition_frontier.tex`
- `paper/arxiv/generated/tables/operator_stage_status.tex`

The first manuscript pass must add the generator before adding manuscript
`\input{}` calls for new generated tables. Do not create checked-in generated
data/table files without the generator and bundle manifest updates that keep
them reproducible.

Generator details:

- Pull `R^2` from
  `models.observed_e2e_vs_prefill_plus_vision_ceiling.r2`.
- Pull MARE and max relative error from
  `error_summaries.prefill_plus_vision_ceiling.mean_abs_relative_error` and
  `error_summaries.prefill_plus_vision_ceiling.max_abs_relative_error`.
- Do not confuse those relative-error fields with
  `models.observed_e2e_vs_prefill_plus_vision_ceiling.max_abs_error`, which is
  an absolute speedup-space error.
- Add generator assertions for the expected source paths and values:
  `n_artifacts == 19`, rounded `R^2 == 0.971`, rounded MARE `== 1.72%`, and
  rounded max relative error `== 7.85%`.
- Assert exact row-selection completeness: the selected-label set must equal
  the six labels listed below. Hard-fail on any missing or extra selected label.
- Select rows by exact membership in `rows[*].label` using:
  `m3_videomme_no_adm`, `m3_videomme_kr07`, `m3_videomme_kr03`,
  `m3_videomme_compose`, `m3_mvbench_kr07`, and `m3_tomato_compose`.
- Read each selected artifact row's `source_path`, assert it matches the exact
  map below, and emit it in the generated snapshot as a single-item
  `source_paths` list so the existing validators see it:
  - `m3_videomme_no_adm`:
    `research/experiments/2026/artifacts/rlt_m3_cost_accounting_followup/videomme_short/videomme_short_random_cvision_no_admission_cost_model.json`
  - `m3_videomme_kr07`:
    `research/experiments/2026/artifacts/rlt_m3_cost_accounting_followup/videomme_short/videomme_short_random_cvision_admission_kr070_cost_model.json`
  - `m3_videomme_kr03`:
    `research/experiments/2026/artifacts/rlt_m3_cost_accounting_followup/videomme_short/videomme_short_random_cvision_admission_kr030_cost_model.json`
  - `m3_videomme_compose`:
    `research/experiments/2026/artifacts/rlt_m3_cost_accounting_followup/videomme_short/videomme_short_rlt_composition_kr050_cost_model.json`
  - `m3_mvbench_kr07`:
    `research/experiments/2026/artifacts/rlt_m3_cost_accounting_followup/mvbench_hosted/mvbench_hosted_random_cvision_admission_kr070_cost_model.json`
  - `m3_tomato_compose`:
    `research/experiments/2026/artifacts/rlt_m3_cost_accounting_followup/tomato_motion_dev/tomato_motion_dev_rlt_composition_kr050_cost_model.json`
- Snapshot schema:
  - `source_paths`: list containing `cost_model_fit_n19.json`, the May 20
    closeout note path, and every selected row source artifact. Use this
    validated key instead of inventing `source_artifact`, `source_notes`, or
    row-level `source_path` fields.
  - `summary_source`: string naming the May 20 closeout note as the source for
    curated fidelity/evidence labels. `summary_source` is part of the existing
    source-key validator vocabulary.
  - `summary`: object with `n_artifacts`, `r2`, `mean_abs_relative_error`,
    and `max_abs_relative_error`.
  - `rows`: list of selected row objects after applying the exact-label filter.
    Each selected row should include `label`, `display_name`, `n`,
    `source_paths`, `observed_e2e_speedup`,
    `prefill_plus_vision_ceiling_speedup`,
    `prefill_plus_vision_relative_error`,
    `accuracy_delta_composed_minus_dense`, `prefill_share`, `vision_share`,
    `prefill_speedup`, `vision_speedup`, `choice_agreement`, and
    `evidence_status`.
    For composition rows, `choice_agreement` must be read from
    `summary.choice_agreement` in the artifact named by the row's input `source_path`, not
    from the top-level `cost_model_fit_n19.json` row where that field may be
    null.
    `display_name` and `evidence_status` are derived from the curated mappings
    in this plan; they are not read from the artifact.
  - Hard-fail if any selected row is missing `source_paths`, stage-share inputs,
    stage-speedup inputs, observed speedup, predicted speedup, relative error,
    or accuracy delta. Hard-fail if either selected composition row
    (`m3_videomme_compose`, `m3_tomato_compose`) is missing `choice_agreement`
    from `summary.choice_agreement` in the artifact named by its input
    `source_path`. Verified `choice_agreement` values are `0.750` for
    `m3_videomme_compose` and `0.533` for `m3_tomato_compose`. Do not silently
    fill `None`.
  - Hard-fail if a selected row's `source_paths` value is not a single-item
    list matching the exact source-path map above.
  - Assert `fidelity_verdict` is absent from the selected cost-model rows so the
    generator cannot accidentally treat curated evidence labels as artifact
    fields.
- Table columns:
  - Workload / setting, derived from the curated row-label mapping:
    `m3_videomme_no_adm` = `VideoMME-short control`; `m3_videomme_kr07` =
    `VideoMME-short admission kr=0.7`; `m3_videomme_kr03` =
    `VideoMME-short admission kr=0.3`; `m3_videomme_compose` =
    `VideoMME-short composition kr=0.5`; `m3_mvbench_kr07` =
    `MVBench-hosted admission kr=0.7`; `m3_tomato_compose` =
    `TOMATO composition`.
  - `Items in selected cell` from `rows[*].n`. The table caption must say the
    model fit spans 19 cells, while this column reports per-row item count.
  - Observed E2E from `rows[*].observed_e2e_speedup`.
  - Predicted E2E from `rows[*].prefill_plus_vision_ceiling_speedup`.
  - Relative error from `rows[*].prefill_plus_vision_relative_error`.
  - Delta accuracy from `rows[*].accuracy_delta_composed_minus_dense`.
  - Fidelity / evidence status from the curated evidence-class mapping above,
    not from artifact `fidelity_verdict`.
  - Source traceability: each table row must carry the selected row's
    `source_paths` into the generated snapshot, and the appendix source table
    must cite the snapshot plus `cost_model_fit_n19.json`.

Column-to-artifact-key map:

| Table column | Artifact key or curated source |
| --- | --- |
| Workload / setting | curated `display_name` mapping in this plan |
| Items in selected cell | `rows[*].n` |
| Observed E2E | `rows[*].observed_e2e_speedup` |
| Predicted E2E | `rows[*].prefill_plus_vision_ceiling_speedup` |
| Relative error | `rows[*].prefill_plus_vision_relative_error` |
| Delta accuracy | `rows[*].accuracy_delta_composed_minus_dense` |
| Fidelity / evidence status | curated mapping sourced to the May 20 closeout |
| Source paths | INPUT artifact field is singular `rows[*].source_path` (a string); the generator wraps it into the OUTPUT snapshot row's single-item `source_paths` list. Do not read `rows[*].source_paths` from `cost_model_fit_n19.json`; that plural key does not exist there. |

Required table-note map for selected caveat rows:

| Row | Required note source |
| --- | --- |
| `m3_videomme_compose` | Top-level row `accuracy_delta_composed_minus_dense` plus `summary.choice_agreement=0.750` from the artifact named by the row's input `source_path` for the composition choice-churn caveat; evidence status remains `timing/boundary`. |
| `m3_tomato_compose` | Top-level row `accuracy_delta_composed_minus_dense` plus `summary.choice_agreement` from the artifact named by the row's input `source_path` for the aggregate-positive/choice-churn caveat; evidence status remains `timing/boundary`. |
| `m3_mvbench_kr07` | Top-level row `accuracy_delta_composed_minus_dense=+0.019` may be reported only as aggregate delta next to a `timing only` evidence status; do not interpret it as a quality win because paired choice agreement is not clean. |

## M3 And M5 Experiment Policy

### M3

Do not run more broad M3 fishing before the paper edit. The local M3 evidence is
already enough for manuscript integration.

Allowed M3 work during paper editing:

- smoke tests for figure/table generation,
- artifact sanity checks,
- small reruns only if a manuscript number cannot be traced to an artifact.

### M5

M5 is scale confirmation, not discovery.

Default tier:

1. n=1 smoke to validate model path, memory, shapes, scorer timing, and pairing.
2. VideoMME n=30 RLT C-VISION to test whether RLT scorer cost and stage-cost
   prediction transfer to larger Gemma.
3. Optional scorer tier only if the paper editor needs the scale-cost story.

Do not run M5 query routing, active repair, text routing, or broad composition
by default.

## Query-Aware Fork Notes

Leave notes in the query-aware plan rather than implementing it here:

- `research/experiments/2026/artifacts/rlt_query_routing_hosted_sweep/` is
  out-of-scope scratch for this paper-editing commit. Do not stage it for the
  VLMaxxing + RLT paper update unless a later query-aware branch verifies and
  adopts the artifacts.
- Stage-cost accounting should be the required denominator for future
  query-aware operators.
- Strong baselines must include fixed/random coverage, no-admission controls,
  RLT-only, and same-run timing.
- Active repair must charge the first pass plus retry cost.
- Text routing must be preregistered and held-out before any claim.
- Query-aware methods should be framed as costed visual evidence planning, not
  as a generic "routing solved" story.

## Verification Plan For The Manuscript Edit

Before committing the actual manuscript rewrite:

1. Rebuild generated paper sources:
   - `make paper-sync` or the repo's current equivalent.
2. Build the manuscript:
   - `make paper-build`.
3. Run paper lint/doctor if available:
   - `make paper-doctor`.
4. Resolve unrelated experiment leftovers before any clean-tree bundle gate:
   - handle the untracked
     `research/experiments/2026/artifacts/rlt_query_routing_hosted_sweep/`
     scratch directory under the cleanup gate in
     `plan/rlt-vlmax-composition.md`.
5. Bundle the manuscript and validate manifest coverage:
   - `make paper-arxiv-check-dirty` before attempting any clean-tree bundle.
   - `make paper-bundle` is a post-commit clean-tree check.
   - Run `uv run pytest tests/test_arxiv_bundle_manifest.py` only after the new
     generated-table `\input{}` has been wired, so the test can actually detect
     missing `ARXIV_TABLE_FILES` coverage.
6. Check generated figure/table provenance:
   - every headline number maps to an artifact or claim-matrix row.
7. Run repo review:
   - `ai-review team --stage diff --profile thorough`.
8. Confirm the staged diff does not include unrelated experiment leftovers.

For this plan commit, verify:

1. Markdown/diff sanity:
   - `git diff --cached --check`.
2. Repo review of the staged plan:
   - `ai-review team --stage diff --profile thorough`.

## Why This Is Excellent Science

This edit makes the paper stronger because it changes the unit of explanation
from a proxy to a measured cause.

Weak version:

> We removed tokens and got some speedups.

Strong version:

> We measured which runtime stage was shortened, predicted the E2E effect from
> that stage's share of the request, charged scorer cost, and then checked
> paired answers to decide whether the speed was usable.

That is better science for four reasons:

1. It is falsifiable. The cost model predicts speedups before the final E2E row;
   misses are diagnostic rather than embarrassing.
2. It keeps denominators visible. C-PERSIST, RLT C-VISION, admission, and
   composition are not collapsed into one vague "pruning" claim.
3. It preserves negative results. H3B substrate cliffs, query-routing failures,
   active-repair cost failure, and text-rule leakage explain the boundaries.
4. It is useful to practitioners. A reader can decide whether a pruning method
   is worth implementing by measuring their runtime bill and asking which stage
   the method actually shortens.

The final manuscript should sound simple:

> Prune the stage that owns the bill. Charge the scorer. Verify the answer.

Everything else is implementation detail.
