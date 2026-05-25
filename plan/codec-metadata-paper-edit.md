# Integrate codec metadata results into the paper

## Goal

Revise the manuscript so the OneVision-inspired H.264 metadata work reads like
part of the original VLMaxxing argument, not a late appendix. The paper should
present compressed-video metadata as:

1. a calibration-robust refresh signal for cached visual evidence,
2. a bounded sparse-token ranking prior at specific operating points, and
3. a systems interface that becomes practical when codec evidence is sidecarized.

It should not claim broad end-to-end VLM speedups, statistical superiority of
codec pruning, TOMATO motion gains, or clean session-reuse composition.

Preferred integration: fold the work into the existing codec/pruning narrative
instead of adding a standalone "OneVision experiment" section. Use a short
reader-facing bridge to OneVision-Encoder in related work, then integrate the
method and evidence into the existing first-query and temporal-reuse sections.
This makes the paper stronger without making it feel like a patch note.

## Peer-review findings (added 2026-05-25)

A peer-review pass verified every number in this plan against the source
JSON and surfaced four science-altering corrections that the plan must
enforce. They are folded into the checklist items below; this block records
the reasoning so it is not lost.

1. **The pooled refresh result does not beat the trivial pixel baseline.**
   The same probe that produced the codec rows also recorded a pixel-domain
   baseline. On the N=57 VideoMME-short Qwen 8f slice, pooled thresholds give
   codec accuracy 0.684 (39/57) and codec-to-dense agreement 0.982 (56/57),
   versus pixel accuracy 0.649 (37/57) and pixel-to-dense agreement 0.947
   (54/57). Codec beats pixel by +2 items out of 57 (`codec_minus_pixel_accuracy`
   = 0.0351), which is not significant at N=57. Any refresh table or claim that
   omits the pixel baseline is selective reporting and will read as
   cherry-picking. The honest contribution is not "codec beats alternatives";
   it is "codec is an answer-preserving refresh trigger at this low-reuse
   operating point, matches a trivial pixel proxy, works without per-item
   calibration, and becomes operationally cheap only when sidecarized."

2. **The refresh result is not "the strongest/cleanest" result; it is a
   modest, high-precision/low-recall efficiency point.** `codec_reuse_ratio_mean_active`
   = 0.106 means the planner skips refresh on only ~10.6% of active
   frame pairs (and pixel skips ~10.8% — slightly more). Via the project's own
   `effective_fresh_frames ~= 1 + (N-1)(1 - reuse)` accounting, that is roughly
   a 10% vision-recompute saving at N=8, not a headline speedup. The 0.982
   agreement is *coupled* to the low reuse: if you only skip 10% of refreshes,
   the answers necessarily barely move. Agreement must never be presented as a
   standalone strength without the reuse budget and the pixel baseline beside
   it. The genuine "wow" results are the sidecar systems win and the
   calibration-free thresholding property, not the refresh agreement number.

3. **OneVision-style fusion does not transfer; report the `fused` source.** The
   pooled dir contains a fourth source, `fused` (motion+residual), which the
   plan currently drops. It underperforms: `fused` codec accuracy 0.667 (=
   dense, below the 0.684 single sources) and agreement 0.965. Reporting only
   the three best-looking sources while silently dropping the worse fused source
   is selective. Either report `fused` or justify its exclusion in the snapshot
   and a footnote. Its underperformance is positive evidence for the plan's
   existing "fusion is not privileged" claim and against naive OneVision-style
   fusion transferring to frozen inference.

4. **The refresh efficiency frontier is uncharacterized.** There is no N=57
   pooled threshold sweep, only a single operating point. A single low-reuse
   point cannot establish a useful agreement-vs-reuse frontier. Limitations must
   say so; do not imply a curve.

Provenance facts confirmed in this pass: all pooled summaries carry
`environment.git_dirty: true`; the OneVision-Encoder citation is real
(arXiv 2602.08683, EvolvingLMMs-Lab; 3.1--25% signal-rich regions, shared 3D
RoPE, cluster-discrimination objective over 1M+ concepts, +4.1% avg over
Qwen3-ViT all verified against the source). The "128 A800 GPUs" and "13B/4B
sample stages" figures from the upstream chat review are NOT on the source and
must not be cited unless found in the paper body. The dense-baseline mismatch
(0.667 vs 0.684) is a run/provenance mismatch: the refresh probe
(`run_phase1_29_planner_accuracy_probe.py`) records a dense path with 38/57,
while the `run_phase1_51V.py` pruning runner records dense 39/57. The
manuscript must name that provenance difference or use a single clean
canonical dense baseline; do not call it benign without item-level evidence.

- [ ] Run the plan gate before manuscript edits.
  - Run `ai-review team --stage plan` against this plan and fix any valid
    findings.
  - Run `git diff --check`.
  - Commit the reviewed plan before starting the manuscript implementation.
    Prerequisite paper-bundle hardening may land in the same commit only when it
    directly enforces a plan gate; the allowed prerequisite hardening here is
    the audit bundle hard-fail, `research/decision-log.md` audit inclusion, and
    manifest tests.
  - Justification: this checklist is intentionally detailed; the manuscript edit
    should start from a reviewed plan, not rediscover these paper-review
    constraints mid-edit.

- [ ] Perform a claim audit and paper-facing vocabulary cleanup.
  - Files: `paper/arxiv/sections/*.tex`, `paper/narrative-rules.md`,
    `paper/arxiv/sections/90_references.tex`.
  - Inspect `paper/framing.md`, `paper/claim-matrix.md`, `paper/priority.md`,
    and `paper/publishability-status.md` for conflicting terminology, but
    reserve claim-status edits in those files for the paper-status step below.
  - Audit `paper/terminology.md` for conflicts, but make terminology-table
    edits only in the dedicated terminology-mapping step below so the mapping is
    changed once in a controlled place.
  - Replace paper-facing uses of "oracle" for codec/pixel/refresh signals with
    "signal", "prior", "refresh signal", or "ranking prior" unless the text is
    explicitly discussing an upper bound with ground-truth access.
  - Replace "Track A", "Track B", and "OV-*" in manuscript prose with
    reader-facing terms: "refresh planning", "cached visual evidence refresh",
    "sparse vision pruning", "token ranking", and "session reuse".
  - Retain internal experiment IDs only in artifact traceability tables,
    appendix provenance, or repo-facing docs where reproducibility requires them.
  - Remove or rewrite any "WOW", "free codec", "10,000x faster VLM", "codec
    wins everywhere", or "magnitude is generally bad" phrasing.
  - Justification: the science is stronger when each denominator is explicit.
    Internal labels and hype obscure the actual contribution.

- [ ] Verify codec-result provenance before promoting any table cell.
  - Files/artifacts:
    `research/experiments/2026/artifacts/phase1_29_onevision_n57_pooled_calibration/*/summary.json`,
    downstream generated paper snapshots, and the final manuscript text.
  - The current pooled-calibration summaries record
    `environment.git_dirty: true`; the paper edit must either use a clean rerun
    with `git_dirty: false` or explicitly label the pooled-threshold result as
    dirty-tree/advisory/pending-clean-rerun everywhere it appears.
  - Trace every reported reuse value to `codec_reuse_ratio_mean_active`. This
    metric is active-region reuse, i.e. the fraction whose refresh is skipped,
    not the active refreshed fraction. If the paper needs active refreshed
    fraction, derive and label `1 - codec_reuse_ratio_mean_active` explicitly.
    At this operating point reuse is ~0.106, so the planner skips refresh on
    only ~10% of active frame pairs; never phrase this as "uses only 10% of
    evidence".
  - Mandatory pixel baseline: every refresh summary also carries
    `pixel_accuracy`, `pixel_dense_agreement`, and `pixel_reuse_ratio_mean_active`,
    plus `codec_minus_pixel_accuracy` and `codec_pixel_agreement`. Pull these
    into the snapshot and show pixel beside codec in any refresh table. On the
    N=57 slice the simple single-source codec rows beat pixel by +2/57
    (0.684 vs 0.649) at essentially equal reuse (0.106 vs 0.108), while `fused`
    is +1/57; neither gap is significant. A refresh table without the pixel row
    is selective reporting.
  - Mandatory `fused` source: the pooled dir has four sources
    (`novel_coded`, `motion`, `residual`, `fused`), not three. `fused`
    underperforms (accuracy 0.667, agreement 0.965). Report it or justify its
    exclusion in the snapshot and a footnote; do not silently drop the worst
    source.
  - Justification: denominator and provenance errors are fatal for this paper.
    The result can be important only if the reader can tell exactly what was
    measured and from what repository state, and only if the trivial baseline that
    the same artifact already measured is shown next to it.

- [ ] Audit dense-baseline consistency across codec result families.
  - Source artifacts:
    pooled-refresh summaries under
    `research/experiments/2026/artifacts/phase1_29_onevision_n57_pooled_calibration/`
    and sparse-pruning summaries under
    `research/experiments/2026/artifacts/phase1_51V_ov6_n57*/`.
  - The pooled-refresh table implies dense accuracy 38/57 = 0.667, while the
    sparse-pruning dense arm reports 39/57 = 0.684 on the N=57 VideoMME-short
    Qwen 8f slice. The provenance difference is identified: the two figures
    come from different scripts (`run_phase1_29_planner_accuracy_probe.py`
    dense path = 38/57 versus the `run_phase1_51V.py` pruning runner dense =
    39/57), a one-item difference. Footnote both run-specific dense baselines
    with their script/run IDs, or rerun/derive a single canonical dense baseline
    for both tables. Do not silently harmonize by hand or call the mismatch
    benign without item-level evidence.
  - The generated snapshots must carry run IDs, manifest IDs, dense-answer
    hashes if available, and the source artifact path for each dense baseline.
  - Justification: adjacent tables with different dense baselines will look
    like an arithmetic error unless the provenance is explicit.

- [ ] Update repo paper-status docs before final manuscript edits.
  - Files: `paper/framing.md`, `paper/claim-matrix.md`,
    `paper/priority.md`, `paper/publishability-status.md`.
  - Apply the same paper-facing vocabulary cleanup in these status docs while
    changing claim state: no "oracle" for codec/pixel priors, no Track A/B
    prose except as artifact aliases, and no "WOW/free codec" phrasing.
  - Mark pooled H.264 refresh as reproduced-here only after a clean rerun, or
    mark it as dirty-tree/advisory with N, model, frame count,
    active-reuse ratio, Wilson interval, hardware, git SHA, and the required
    clean-rerun condition.
  - Mark codec sparse pruning as reproduced-here but statistically bounded:
    favorable point estimate, paired p-value inconclusive.
  - Mark sidecar equivalence as reproduced-here systems evidence with zero
    drift and extraction-path speedup only at n=3 per-source smoke scope.
  - Mark TOMATO and session composition as boundary results.
  - Justification: the durable claim register must match the manuscript before
    paper tables or abstract claims move.

- [ ] Update the canonical decision ledger for codec metadata outcomes.
  - File: `research/decision-log.md`.
  - Record sidecar equivalence as adopted systems evidence with the three
    sidecar artifact paths, n=3 per-source smoke scope, zero
    choice/correctness/kept-count drift, and the extraction-path timing
    denominator.
  - Record pooled H.264 refresh as advisory until clean rerun if the dirty-tree
    summaries remain the source, or as clean reproduced evidence if a clean
    rerun replaces them.
  - Keep machine-oriented sidecars as future/deployment work only where the
    claim exceeds the current smoke-slice equivalence gates.
  - Justification: `research/decision-log.md` is the canonical ledger for
    adopted, weakened, killed, and revived ideas; the paper should not promote
    sidecars while the ledger still treats them only as a hypothesis.

- [ ] Update the experiment registry for sidecar and codec-metadata outcomes.
  - File: `research/experiments/registry.md`.
  - Update or split the relevant sidecar-bearing row so it no longer remains
    preregistered-only after the paper promotes sidecar equivalence. Include
    status, prereg outcome, current best policy, exact sidecar artifact paths,
    n=3 per-source scope, zero-drift fields, and extraction-path timing
    denominator.
  - Keep pooled H.264 refresh, sparse-pruning, TOMATO, and session-composition
    status aligned with the decision log and paper claim docs.
  - Justification: registry, decision log, paper claim docs, and manuscript
    must agree on what is completed evidence versus advisory or pending.

- [ ] Update the abstract without adding a new contribution paragraph.
  - File: `paper/arxiv/sections/01_abstract.tex`.
  - Replace the current fresh-video pruning sentence with a two-clause sentence
    that includes both existing measured sparse-vision pruning and the new
    codec-metadata result. Phrase the refresh clause as: pooled
    (calibration-free) H.264 thresholds preserve dense answers on 56/57
    VideoMME-short items for the simple single-source rows while skipping
    refresh on only ~10--11% of active frame pairs. Do NOT write "reusing
    10--11% of visual evidence" (a reader will misread it as using only 10%).
    Do not state bare "56/57" as an all-codec result: the `fused` row is 55/57
    and must be visible in the table/footnote. Label the pooled-threshold number
    advisory until a clean rerun lands.
  - Do not imply codec beats the trivial baseline in the abstract: a pixel proxy
    matches it within 2 items. If abstract space is tight, the strongest
    honest codec mention is the sidecar systems result plus the
    calibration-free property, not the refresh agreement number. Prefer leading
    the codec mention with sidecars.
  - Replace or compress the final VLM-native media paragraph so it mentions
    codec sidecars as the concrete bridge: H.264 evidence is expensive through a
    separate PyAV pass but millisecond-scale when precomputed as sidecars.
  - Keep C-PERSIST and C-CEILING as the abstract's main spine; do not add a
    fourth headline contribution.
  - Justification: the abstract should reflect the new strongest evidence but
    stay size-neutral and avoid implying broad end-to-end speedup.

- [ ] Rewrite the introduction's codec motivation as a planned design question.
  - File: `paper/arxiv/sections/02_introduction.tex`.
  - Near the opening codec/motion paragraph, add one compact sentence: recent
    codec-aligned encoders show that compressed-video structure can be model
    native; VLMaxxing asks which parts transfer to frozen inference without
    retraining.
  - In the regime map, keep the three existing regimes but add codec metadata
    under the first-query row as "refresh planning and sparse-token ranking",
    not as a separate regime.
  - Modify the contribution bullets so codec metadata supports the existing
    first-query and VLM-native-media claims rather than becoming a new bullet.
  - Cut redundant explanatory text about codecs as future speculation if the
    same point is now carried by the concrete H.264/sidecar result.
  - Justification: OneVision should motivate the question, while VLMaxxing's
    contribution remains frozen-backend anti-recomputation.

- [ ] Add OneVision-Encoder to related work as a contrast, not a reproduction.
  - Files: `paper/arxiv/sections/03_related_work.tex`,
    `paper/arxiv/sections/90_references.tex`.
  - Add a short paragraph after the trained codec-native approaches paragraph
    (it slots next to CoPE-VideoLM / CoViAR / Deja Vu):
    OneVision-Encoder trains a codec-aligned encoder that focuses on the
    signal-rich 3.1--25% of regions, uses a shared 3D RoPE for irregular
    spatial/temporal layouts, and trains a cluster-discrimination objective over
    1M+ semantic concepts; VLMaxxing instead uses H.264 metadata as an external
    routing signal for frozen VLM inference without retraining.
  - Citation is verified real: arXiv 2602.08683, EvolvingLMMs-Lab,
    "OneVision-Encoder: Codec-Aligned Sparsity as a Foundational Principle for
    Multimodal Intelligence" (code: github.com/EvolvingLMMs-Lab/OneVision-Encoder).
    Add a new `\bibitem{onevision}` in `90_references.tex` with the real authors
    and arXiv id. Only the source-confirmed specifics above (3.1--25% regions,
    3D RoPE, cluster discrimination over 1M+ concepts, +4.1% avg over Qwen3-ViT,
    fewer visual tokens) may be stated. Do NOT cite "128 A800 GPUs" or "13B/4B
    sample stages" from the upstream chat review; those are not in the source.
    If any GPU/sample-count figure is wanted, confirm it in the paper body
    first.
  - Preserve the distinction from CodecSight, CoPE-VideoLM, and CoViAR:
    those motivate codec-aware representations; our paper measures which
    codec signals are useful without retraining or decoder integration.
  - Justification: reviewers will compare this branch to OneVision. The paper
    should answer that comparison directly and early.

- [ ] Refactor the method's signal description around H.264 evidence.
  - File: `paper/arxiv/sections/04_method.tex`.
  - Rename or revise the current "Temporal Planner" language to cover temporal
    and codec evidence signals.
  - Define the three H.264 score sources used in the experiments:
    `novel_coded` (intra/cbf-style changed macroblock evidence), `motion`, and
    `residual`. Mention fused motion+residual as tested but not privileged by
    the evidence.
  - Define pooled thresholding for refresh planning: no per-item threshold
    fitting; thresholds are chosen from the corpus-level score distribution and
    then applied item by item.
  - Define sidecars as an ingest-time or research-loop artifact that binds item
    IDs, source video hashes, score source, projection version, geometry, score
    config, git provenance, and score-array hashes. Make live PyAV extraction
    and sidecar loading separate timing denominators.
  - Keep the warning that codec/pixel signals are physical change priors, not
    semantic labels.
  - Justification: the method should make the later result tables legible and
    prevent "free codec" or "semantic saliency" misreadings.

- [ ] Plan generated tables and figures so the paper gets stronger, not longer.
  - Default main-text layout: use the per-section tables specified below for
    refresh planning, sparse pruning, and sidecar extraction. If those tables
    can be combined without dropping required baselines, provenance, or
    denominators, a compact "Codec metadata results" table with three blocks is
    acceptable. The per-section result specs take precedence over forcing one
    combined table.
  - Generated tables and figures must be produced through
    `paper/arxiv/scripts/sync_sources.py` or another checked-in generator, not
    hand-edited generated `.tex`.
  - Track source snapshots under `paper/arxiv/generated/data/*.json` with
    source artifact paths, git provenance, table cell inputs, and any
    dirty-tree/advisory flags.
  - Conceptual architecture diagrams may be hand-authored as committed TikZ,
    SVG, or PDF figure sources under the paper tree. The generator/snapshot
    requirement applies to data-driven panels and all generated tables.
    Hand-authored figures referenced by the manuscript must still be registered
    in `build.py` `ARXIV_FIGURE_FILES` or otherwise covered by the arXiv upload
    bundle allowlist. Prefer placing committed hand-authored figure outputs
    under `paper/arxiv/generated/figures/`; if a referenced hand-authored figure
    lives elsewhere, extend `tests/test_arxiv_bundle_manifest.py` so its
    registration is checked instead of relying on manual review.
  - Generated table files to add or update via the generator:
    `paper/arxiv/generated/tables/codec_refresh_signal.tex`,
    `paper/arxiv/generated/tables/codec_sparse_pruning.tex`,
    `paper/arxiv/generated/tables/codec_sidecar_equivalence.tex`, or a single
    combined `codec_metadata_summary.tex` if space is tight.
  - Main figure candidate: a three-panel figure:
    A. H.264 bitstream to score sidecar to two consumers: refresh planning and
       sparse pruning.
    B. Agreement at the pooled threshold versus active reuse ratio, one point
       per score source AND the pixel baseline point. Do not imply a
       threshold-sweep curve: this is a single operating point per source, so
       plot discrete points and annotate that the agreement-vs-reuse frontier is
       uncharacterized. The pixel point sitting next to the codec points is the
       honest visual: codec and pixel land in nearly the same place.
    C. Log-scale codec-evidence extraction time: live PyAV seconds versus
       sidecar milliseconds, with the n=3 pilot scale and denominator note.
  - Appendix figure candidate: real-video contact sheet / score overlay /
    selected tiles from the existing OneVision-VLMaxxing visual artifacts.
  - Remove or compress any older figure/table that repeats weaker codec-native
    per-item-calibration evidence.
  - Justification: the visuals should teach denominator discipline and the
    concrete systems path, not just decorate the new result.

- [ ] Extend the paper generator after locking the table/figure design above.
  - Files: `paper/arxiv/scripts/sync_sources.py`, or a new checked-in generator
    called from `paper-sync`, plus `paper/arxiv/scripts/build.py`.
  - Completed prerequisite before manuscript editing: audit-bundle hard-fail,
    `research/decision-log.md` audit inclusion, and bundle-manifest tests. The
    codec snapshot builders, table emitters, and manuscript edits remain
    pending.
  - The generator should encode the table/figure design above; it should not
    invent table scope, figure panels, or bundle membership while being written.
  - Add codec-metadata snapshot builders that read the source artifacts named
    in this plan and write tracked `paper/arxiv/generated/data/*.json`
    snapshots with source paths, git provenance, artifact dirtiness, table cell
    inputs, confidence intervals, paired-test inputs, and sample sizes.
  - For the refresh snapshot, the cell inputs must include all four codec
    sources (`novel_coded`, `motion`, `residual`, `fused`) and the pixel
    baseline fields (`pixel_accuracy`, `pixel_dense_agreement`,
    `pixel_reuse_ratio_mean_active`, `codec_minus_pixel_accuracy`,
    `codec_pixel_agreement`). Do not let the generator silently select only the
    favorable sources.
  - For refresh paired codec-vs-pixel correctness, read
    `summary_json["items"][]` from each source summary. Each row must contain
    `item_id`, `codec_correct`, and `pixel_correct`; compute fixes as rows where
    `codec_correct is true and pixel_correct is false`, and breaks as rows where
    `codec_correct is false and pixel_correct is true`. If an `items` array or
    any required key is absent, the generator must hard-fail for manuscript
    table generation rather than fabricating paired statistics from aggregate
    rates.
  - For sparse-pruning snapshots, read
    `research/experiments/2026/artifacts/onevision_vlmaxxing_plan/ov6_track_b_statistical_audit.json`
    plus `research/experiments/2026/artifacts/phase1_51V_ov6_n57/dense/summary.json`,
    `research/experiments/2026/artifacts/phase1_51V_ov6_n57_kr070_l2/magnitude_norm/summary.json`,
    `research/experiments/2026/artifacts/phase1_51V_ov6_n57_kr070_l2/codec_novel_coded/summary.json`,
    `research/experiments/2026/artifacts/phase1_51V_ov6_n57_kr070_l2/codec_motion/summary.json`,
    and
    `research/experiments/2026/artifacts/phase1_51V_ov6_n57_kr070_l2/codec_residual/summary.json`;
    do not recompute paired fixes/breaks from mismatched manifests.
  - For sidecar snapshots, read the three sidecar-equivalence JSON artifacts
    `research/experiments/2026/artifacts/phase1_51V_ov6_sidecar_equivalence/sidecar_equivalence.json`,
    `research/experiments/2026/artifacts/phase1_51V_ov6_sidecar_equivalence_f16/sidecar_equivalence.json`,
    and
    `research/experiments/2026/artifacts/phase1_63G_ov6_gemma_sidecar_equivalence/sidecar_equivalence.json`,
    plus these paired live/sidecar summaries:
    `research/experiments/2026/artifacts/phase1_51V_ov6_sidecar_equivalence/{live,sidecar}_{novel_coded,motion,residual}/summary.json`,
    `research/experiments/2026/artifacts/phase1_51V_ov6_sidecar_equivalence_f16/{live,sidecar}_{novel_coded,motion,residual}/summary.json`,
    and
    `research/experiments/2026/artifacts/phase1_63G_ov6_gemma_sidecar_equivalence/{live,sidecar}_{novel_coded,motion,residual}/summary.json`.
    Preserve the n=3 per-source scope and extraction-path denominator.
  - Add table/figure emitters that consume those snapshots and write the
    generated `.tex`/figure files. Do not hand-edit generated tables.
  - Register every new generated table in `build.py` `ARXIV_TABLE_FILES` and
    every new generated figure in `build.py` `ARXIV_FIGURE_FILES`, or document
    explicitly why a generated artifact is audit-only and excluded from the
    upload bundle. Add `research/decision-log.md` to `AUDIT_EXTRA_FILES`
    because the manuscript will rely on that ledger for codec-metadata claim
    state.
  - Change `build.py` audit-bundle behavior to hard-fail if any
    `AUDIT_EXTRA_FILES` entry is missing. Keep the explicit post-build audit
    that confirms `repo/research/decision-log.md` is present as a second check,
    not as a substitute for the hard fail.
    Evidence: the prerequisite bundle hardening is intentionally allowed before
    manuscript editing so the later manuscript edit can rely on the
    audit-bundle gate.
    Decision: bundle hardening and manifest tests may be completed before the
    manuscript generator work; codec snapshot builders, table emitters, and
    manuscript edits remain pending implementation work.
  - Update or add tests for the build-bundle contract, preferably in
    `tests/test_arxiv_bundle_manifest.py`: missing `AUDIT_EXTRA_FILES` entries
    must fail, `research/decision-log.md` must be included in
    `AUDIT_EXTRA_FILES`, and manuscript-referenced codec tables/figures must be
    represented in the arXiv upload allowlists. If hand-authored figures are
    referenced outside `generated/figures/`, extend the existing figure
    discovery regex/test coverage before accepting that layout.
  - Validate by running `make paper-sync` and confirming the generated files
    reproduce from a clean checkout without manual edits.
  - Justification: the paper workspace treats generated JSON snapshots as the
    audit surface; the codec tables need to obey the same rule.

- [ ] Preserve result-section reader flow before inserting codec tables.
  - `paper/arxiv/main.tex` currently includes
    `sections/07_results_cross_architecture.tex` before
    `sections/06_results_qwen_routing.tex`.
  - Keep that order unless there is a separate manuscript-structure decision.
    Put the compact reader-facing codec metadata summary in Section 7, where
    readers first encounter measured frontiers, and use Section 6 for the
    Qwen routing/mechanism detail.
  - Justification: the strongest codec result should not first appear after the
    sparse-pruning discussion without warning. Section 7 carries the systems
    order; Section 6 can then explain the routing mechanism.

- [ ] Integrate the pooled H.264 refresh result into Qwen results as a
      calibration-free, sidecarizable refresh signal (NOT as the strongest
      headline win).
  - Files: compact summary in
    `paper/arxiv/sections/07_results_cross_architecture.tex`, mechanism detail
    in `paper/arxiv/sections/06_results_qwen_routing.tex`.
  - Source artifacts:
    `research/experiments/2026/artifacts/phase1_29_onevision_n57_pooled_calibration/novel_coded/summary.json`,
    `research/experiments/2026/artifacts/phase1_29_onevision_n57_pooled_calibration/motion/summary.json`,
    and
    `research/experiments/2026/artifacts/phase1_29_onevision_n57_pooled_calibration/residual/summary.json`,
    plus the mandatory fused comparison source
    `research/experiments/2026/artifacts/phase1_29_onevision_n57_pooled_calibration/fused/summary.json`.
  - Add a compact Section 7 table block before the sparse-pruning table so the
    reader sees the refresh result before the bounded sparse-ranking result.
  - Add or update a Section 6 subsection after the routing frontier setup and
    before broad mechanism interpretation: "Compressed-video metadata as a
    refresh signal".
  - Include a small table with rows for `novel_coded`, `motion`, `residual`,
    and `fused`, plus a `pixel` baseline row: codec accuracy 0.684 (0.667 for
    fused, coincidentally equal to the dense 38/57 run-specific baseline), dense
    accuracy 0.667, pixel accuracy 0.649, codec-to-dense agreement
    0.982 (0.965 fused), pixel-to-dense agreement 0.947, active reuse roughly
    10.6--10.9% from `codec_reuse_ratio_mean_active` (pixel 10.8%), and
    per-row Wilson intervals for agreement (single-source lower bound around
    0.91; fused lower bound is lower). The table must let the reader see that
    codec, pixel, and dense accuracies are all within ~2 items of each other.
  - Add a table note that the `fused` codec accuracy equals the refresh-probe
    dense baseline numerically (38/57 = 0.667) but is a separate sparse/refresh
    policy row, not a second dense measurement.
  - Compute codec-vs-pixel paired correctness from the `items` arrays in each
    refresh summary. For the current single-source rows this is 2 codec fixes
    and 0 pixel fixes; report it as finite paired evidence, not as a
    significance claim. If the generator reports a McNemar p-value, it must
    compute the value from item rows rather than hard-coding it.
  - State the key claim precisely: with pooled (calibration-free) thresholds,
    codec metadata is an answer-preserving refresh trigger at this tested
    low-reuse point: the simple single-source codec rows preserve dense answers
    on 56/57 items while skipping refresh on only ~10--11% of active frame pairs
    (the `fused` row is 55/57 and must remain visible).
    Explicitly add that a trivial pixel-difference proxy does nearly as well
    (54/57, +2 items behind codec, not significant) at the same reuse, so the
    codec-specific accuracy advantage is bounded; the durable value is that the
    signal is calibration-free and sidecarizable. It is refresh
    planning, not sparse execution or session reuse.
  - Do not call this the strongest or cleanest result. The agreement number is
    coupled to the small reuse budget (skipping ~10% of refreshes necessarily
    preserves almost all answers), so it cannot carry a standalone efficiency
    claim. Report agreement, reuse budget, and pixel baseline together or not
    at all.
  - If a clean rerun is not available when the manuscript edit lands, put the
    dirty-tree caveat in the table note and status docs instead of presenting
    the pooled result as final paper-grade evidence.
  - Remove stale or weaker codec-planner phrasing that only reports older
    per-item calibration or n=10/n=20 results if it no longer earns space.
  - Justification: this is a legitimate calibration-free, sidecarizable refresh
    result that belongs in the main results, but framed as an observed
    answer-preserving, sidecarizable signal rather than a headline win.
    Overstating it (omitting the pixel
    baseline, dropping fused, or quoting agreement without the reuse budget)
    would invite the exact denominator critique this plan exists to prevent.

- [ ] Replace the stale Qwen random-keep sanity paragraph with the new
      sparse-pruning evidence.
  - File: `paper/arxiv/sections/07_results_cross_architecture.tex`.
  - Source artifacts for the keep-rate 0.7 table:
    `research/experiments/2026/artifacts/phase1_51V_ov6_n57/dense/summary.json`,
    `research/experiments/2026/artifacts/phase1_51V_ov6_n57_kr070_l2/magnitude_norm/summary.json`,
    `research/experiments/2026/artifacts/phase1_51V_ov6_n57_kr070_l2/codec_novel_coded/summary.json`,
    `research/experiments/2026/artifacts/phase1_51V_ov6_n57_kr070_l2/codec_motion/summary.json`,
    and
    `research/experiments/2026/artifacts/phase1_51V_ov6_n57_kr070_l2/codec_residual/summary.json`.
  - Source artifact for paired fixes/breaks and McNemar p-values:
    `research/experiments/2026/artifacts/onevision_vlmaxxing_plan/ov6_track_b_statistical_audit.json`.
    The generated snapshot must store the paired inputs, fixes, breaks, and
    p-value instead of hard-coding p=0.2188 in TeX.
  - Source artifacts for the keep-rate 0.5 random-seed caution:
    `research/experiments/2026/artifacts/phase1_51V_ov6_random_multiseed/magnitude_norm/summary.json`
    plus the aggregate
    `research/experiments/2026/artifacts/phase1_51V_ov6_random_multiseed/random_multiseed_summary.json`
    and the four explicit seed paths:
    `research/experiments/2026/artifacts/phase1_51V_ov6_random_multiseed/uniform_random_seed1/summary.json`,
    `research/experiments/2026/artifacts/phase1_51V_ov6_random_multiseed/uniform_random_seed7/summary.json`,
    `research/experiments/2026/artifacts/phase1_51V_ov6_random_multiseed/uniform_random_seed42/summary.json`,
    and
    `research/experiments/2026/artifacts/phase1_51V_ov6_random_multiseed/uniform_random_seed100/summary.json`.
  - Remove the paragraph claiming the Qwen structured magnitude scorer reaches
    0.500 versus random mean 0.358 at matched keep-rate; that is no longer the
    right paper-facing evidence.
  - Add a compact table for Qwen VideoMME-short N=57, 8 frames,
    configured keep-rate 0.7, actual mean effective keep-rate 0.6875,
    layer 2:
    dense 39/57 = 0.684, magnitude_norm 31/57 = 0.544,
    codec_novel_coded 35/57 = 0.614, codec_motion 32/57 = 0.561,
    codec_residual 33/57 = 0.579, and McNemar p=0.2188 for the
    codec_novel_coded versus magnitude_norm paired comparison.
  - Add one sentence that the point estimate is favorable but statistically
    bounded: five paired fixes and one break are not enough for a standard
    significance claim.
  - Preserve both configured target keep-rate (`vision_tower_keep_rate`) and
    actual mean effective keep-rate (`mean_effective_keep_rate`) in the
    generated snapshot. Apply the same target-versus-effective audit to the
    keep-rate 0.5 random-seed caution.
  - Add a short caution paragraph for Qwen keep-rate 0.5, layer 2: four
    uniform-random seeds beat magnitude_norm, so hidden-state magnitude is a
    poor default at that operating point, not a generally reliable video-token
    importance signal.
  - Keep Gemma N=10 as an implementation smoke result unless M5 N=57 lands
    before the paper edit is finalized.
  - Justification: this replaces a stale positive baseline story with the real
    current result: codec ranking is promising but underpowered, and magnitude
    needs operating-point scrutiny.

- [ ] Add a sidecar systems result without inflating the model-speed claim.
  - Candidate location: end of `paper/arxiv/sections/07_results_cross_architecture.tex`
    or a short paragraph in `paper/arxiv/sections/05_experimental_setup.tex`
    plus a result table in Section 7.
  - Source artifacts:
    `research/experiments/2026/artifacts/phase1_51V_ov6_sidecar_equivalence/sidecar_equivalence.json`,
    `research/experiments/2026/artifacts/phase1_51V_ov6_sidecar_equivalence_f16/sidecar_equivalence.json`,
    and
    `research/experiments/2026/artifacts/phase1_63G_ov6_gemma_sidecar_equivalence/sidecar_equivalence.json`,
    plus their paired live/sidecar `summary.json` files.
  - Include a small table with Qwen 8f, Qwen 16f, and Gemma 8f sidecar
    equivalence gates: `n_items` per source (currently n=3 smoke gates), live
    PyAV extraction seconds per item, sidecar load milliseconds per item, and
    choice/correctness/kept-count drift all zero.
  - For extraction-path timing, do not hard-code any previously discussed
    live-versus-sidecar constants. Generate per-source live extraction means,
    sidecar load means, and ratios from
    `sidecar_equivalence.json["pairs"][source]["live_extract_mean_s_per_item"]`
    and
    `sidecar_equivalence.json["pairs"][source]["sidecar_load_mean_s_per_item"]`.
    If the paper reports an aggregate extraction-path ratio, declare the formula
    and store every input path/value in the generated snapshot.
  - If the paper also reports setup-inclusive timing, keep it in a separate row
    or note using `mean_end_to_end_including_codec_score_runtime_ms` from the
    paired live/sidecar summaries. That field includes VLM inference time and
    supports only the modest setup-inclusive ratio, not the 3,800--17,900x
    extraction-path claim.
  - Put the 3,800--17,900x number only on the codec-evidence extraction path,
    and label it as coming from n=3 equivalence pilots rather than a large
    timing characterization.
  - Use finite-scope language: "passed zero-drift equivalence gates across Qwen
    8f, Qwen 16f, and Gemma 8f smoke slices." Do not write that the sidecar
    contract is proven for all videos or all geometries.
  - Justification: this is the practical systems win. It makes codec-aware
    repeated sweeps and deployments plausible without corrupting the
    end-to-end denominator.

- [ ] Update the discussion to connect OneVision, VLMaxxing, and future media.
  - File: `paper/arxiv/sections/09_discussion_future_work.tex`.
  - Rewrite "Codec Signals Are Requirements Probes" so it says:
    OneVision-Encoder validates codec structure as a trainable representation
    prior; our frozen-backend results show what transfers without retraining:
    codec metadata is a calibration-free, sidecarizable refresh trigger that is
    answer-preserving at the tested low-reuse operating point
    (but not measurably better than a pixel proxy at our operating point and not
    via OneVision-style fusion, which underperformed), sparse ranking transfers
    only at bounded operating points, and session composition remains blocked by
    first-query drift. The transfer is "codec metadata as a sidecarizable physical-change
    signal," not "OneVision's fusion recipe."
  - Replace "oracle" language with "signals" or "priors".
  - Add one systems sentence: sidecars are not the final decoder-integrated
    interface, but they passed zero-drift smoke gates across three
    model/frame configurations spanning two vision geometries: Qwen ViT
    merged-group geometry at 8 and 16 frames, and Gemma SigLIP pre-pool patch
    geometry at 8 frames.
  - Justification: this turns mixed results into the actual contribution:
    mapping where codec structure helps frozen VLM inference.

- [ ] Tighten limitations and anti-claims.
  - File: `paper/arxiv/sections/09_limitations_reproducibility.tex`.
  - Replace the older codec-native bridge paragraph with current boundaries:
    the Qwen refresh result is Qwen-only and, at its single operating point,
    codec gives only a +2/57 (non-significant) edge over a pixel-difference
    proxy at ~10% reuse (and fused is only +1/57), so it is a bounded,
    sidecarizable refresh trigger rather than a demonstrated codec-over-pixel win;
    the refresh agreement-vs-reuse frontier
    is uncharacterized (no N=57 pooled threshold sweep), so no efficiency-frontier
    claim is made; OneVision-style fused motion+residual scoring did not help
    (fused underperformed single sources); sparse ranking has favorable point
    estimates but inconclusive paired tests; Gemma accuracy evidence is
    smoke-level until M5; TOMATO dense baseline is too weak to promote; live
    PyAV extraction is not a deployable per-query path; session reuse
    composition is blocked by 12/57 first-query drift.
  - Explicitly say not to multiply refresh percentage, sparse keep-rate, and
    session reuse speedup.
  - Justification: strong limits make the codec result credible and prevent
    review damage from denominator confusion.

- [ ] Add M5 confirmation insert points without blocking paper editing.
  - Files: same manuscript and status docs as above.
  - Prepare wording so M5 can update the paper with one paragraph/table-row
    change:
    Qwen parity confirms or weakens hardware stability;
    Gemma N=57 confirms, bounds, or contradicts cross-family sparse ranking;
    Gemma random-vs-magnitude confirms or bounds the magnitude-pruner critique;
    Qwen 16f confirms or bounds frame-budget transfer.
  - If M5 Gemma N=57 confirms the N=10 smoke, upgrade the Gemma rows and expand
    the cross-family claim scope. If it weakens or contradicts the N=10 smoke,
    report that contradiction explicitly and reduce the Gemma statement to
    mechanical cross-family wiring plus a negative/boundary accuracy result.
  - Do not wait for M5 to begin paper editing. Treat M5 as confirmation, not
    discovery, unless it overturns the current claim.
  - Justification: paper editing can proceed now, and the planned insert points
    avoid a rewrite when M5 results arrive.

- [ ] Preserve an internal-to-paper terminology mapping.
  - Primary location: `paper/terminology.md`. Cross-link from
    `paper/framing.md` or `paper/claim-matrix.md` only when the claim status
    needs it.
  - Update `paper/narrative-rules.md` if the claim order or denominator wording
    changes.
  - Record that internal experiment terms such as "Track A", "Track B", and
    "OV-*" remain valid in scripts, artifact names, and reproducibility notes,
    while manuscript prose maps them to reader-facing terms such as refresh
    planning, sparse vision pruning, and session reuse.
  - Supersede the existing `paper/terminology.md` avoid-table guidance:
    map Track A to "refresh planning" or "cached visual evidence refresh" in
    reader prose, with "dense-backend semantic-substitution routing" retained
    only as an internal/provenance alias; map Track B to "sparse vision
    pruning" or "measured sparse execution" depending on whether the sentence
    discusses the mechanism or timed skipped work.
  - Do not churn script names or artifact directories merely to match prose.
  - Justification: the paper should avoid internal jargon, but contributors
    still need a clear bridge from artifact names to manuscript claims.

- [ ] Run manuscript implementation verification before committing manuscript
      edits.
  - For the eventual manuscript-edit implementation, run the paper workflow:
    `make paper-doctor`, `make paper-sync`, and `make paper-build`, or record
    an explicit blocker if local TeX tooling is unavailable.
  - Exercise the arXiv upload path after registering codec tables/figures in
    `paper/arxiv/scripts/build.py`: during an uncommitted edit, run
    `make paper-arxiv-check-dirty` as a path check; do not treat that dirty
    bundle as releasable. Before submission or merge of the manuscript edit, run
    `make paper-arxiv-check` from a clean tree. That target builds the minimal
    upload tarball, extracts it, and compiles `main.tex` from the extracted
    upload bundle; it must pass before packaging is called verified. If local
    TeX tooling is unavailable, record that blocker explicitly, do not call
    packaging fully verified, and at least list the tarball contents to verify
    every codec table and figure named in the manuscript is present.
  - Run `make paper-audit-bundle` from a clean tree after adding
    `research/decision-log.md` to `AUDIT_EXTRA_FILES`.
  - Inspect the arXiv tarball contents and confirm every codec table/figure
    named in the manuscript and every codec generated asset registered in
    `ARXIV_TABLE_FILES` / `ARXIV_FIGURE_FILES` is present in the upload bundle.
    Also confirm `repo/research/decision-log.md` appears in the audit bundle
    after adding `research/decision-log.md` to `AUDIT_EXTRA_FILES`.
  - Confirm generated-table diffs are reproducible from the tracked JSON
    snapshots and canonical artifacts.
  - Run a vocabulary audit over `paper/arxiv/sections/*.tex` and paper-facing
    docs for `oracle`, `Track A`, `Track B`, `OV-`, `WOW`, `safe`, `free codec`,
    `10,000x`, and `codec wins`; any remaining hits must be in traceability,
    explicit upper-bound language, or repo-facing terminology notes.
    `safe` has a narrow carve-out for established non-codec terms that already
    describe a concrete invariant (for example topology-safe cache reuse,
    deadline-safe perception, denominator-safe paired rows, unsafe default cache
    paths, "safe to say" status headings, `c_persist_safe_budget` filenames, and
    the `paper-sync` "safe first step" setup wording). It also has a narrow
    carve-out for already-scoped cache-system phrases such as
    correctness-safe fallback, safe path, or statements that a specific
    `PromptCacheState` wrapper is safe only under tested conditions, and
    data-ingestion phrases such as iterating to the only safe frame count. It
    must not be used to summarize codec refresh, sparse ranking, sidecar timing,
    or experiment fidelity.
  - Confirm every manuscript cell or table note that draws from a dirty-tree
    artifact carries the advisory/pending-clean-rerun label.
  - Confirm the refresh table includes the pixel baseline row and the `fused`
    source (or a footnoted justification for excluding fused), and that no
    manuscript sentence calls the refresh result the "strongest"/"cleanest"
    result or quotes its agreement without the reuse budget and pixel baseline.
  - Confirm the refresh/pruning dense-baseline mismatch is either resolved by a
    single canonical rerun or explicitly footnoted with both source artifact
    paths and run-specific dense values (38/57 versus 39/57).
  - Confirm the OneVision bibitem cites only source-confirmed specifics (no
    "128 A800", no "13B/4B samples" unless verified in the paper body).
  - Justification: the user asked for a manuscript edit that can survive
    in-depth paper review and arXiv packaging, not just a local PDF build.

## Constraints

- Do not implement query-aware or RLT work in this branch. Mention synergy only
  as future work when it helps frame sidecars.
- Do not use "Track A" or "Track B" in paper-facing prose.
- Do not call codec, pixel, or magnitude scores "oracles" unless the text is
  explicitly about a ground-truth upper bound.
- Do not claim statistically significant codec sparse-pruning superiority.
- Do not claim broad end-to-end VLM speedup from sidecars.
- Do not promote TOMATO motion gains from the current smoke.
- Do not present the pooled refresh result as a codec-over-pixel accuracy win;
  simple single-source codec rows beat the pixel proxy by only +2/57
  (non-significant) at equal reuse, and the fused row is only +1/57.
- Do not call the pooled refresh trigger "safe" in paper-facing prose; say
  "answer-preserving at the tested low-reuse operating point" or an equivalent
  finite-scope phrase.
- Do not show a refresh table or figure without the pixel baseline, and do not
  silently drop the `fused` source.
- Do not call the refresh result the "strongest"/"cleanest" result, and do not
  quote its 0.982 agreement without the ~10% reuse budget beside it.
- Do not cite OneVision specifics absent from the source ("128 A800 GPUs",
  "13B/4B sample stages").
- Do not promote dirty-tree pooled-calibration artifacts as clean paper-grade
  evidence. Rerun clean or label them advisory.
- Do not treat n=3 sidecar equivalence gates as broad timing
  characterization. They validate drift-free equivalence on smoke slices and
  provide pilot extraction-path timings.
- Keep the paper size neutral or smaller where possible by replacing stale
  paragraphs and tables rather than appending a new long section.

## Implementation Notes

- Decision: integrate codec metadata across related work, method, results, and
  limits. A standalone section would make the work read like a late add-on and
  would duplicate existing first-query pruning material.
- Evidence: OneVision-Encoder's arXiv abstract frames codec-aligned sparsity as
  a trained encoder principle using sparse codec patchification and irregular
  layouts; VLMaxxing's arXiv abstract frames this paper as training-free
  anti-recomputation with separate first-query, follow-up, and ceiling
  denominators. The manuscript edit should preserve that distinction.
- Evidence: current branch artifacts support three paper-useful claims:
  pooled H.264 single-source refresh preserves dense answers 56/57 while
  skipping refresh on only ~10--11% of active frame pairs (codec accuracy 0.684
  vs pixel proxy 0.649, a non-significant +2/57 edge at equal reuse for the
  simple single-source rows; fused source underperforms at 0.667, 55/57
  agreement, and +1/57 over pixel), with a dirty-tree caveat
  until rerun clean; Qwen sparse-pruning
  favorable point estimate 35/57 versus 31/57 but McNemar p=0.2188; sidecar
  extraction equivalence with zero drift and seconds-to-milliseconds
  extraction-path speedup (n=3 per-source smoke gates, ~3,800--17,900x on the
  extraction path only). The sidecar systems result and the calibration-free
  thresholding property are the durable "wow"; the refresh agreement number is
  not, because it is coupled to the small reuse budget and matched by a trivial
  pixel baseline.
- Open: M5 confirmations should update the table cells and scope language when
  they land, but they are not prerequisites for starting the edit.

## Verification

- `ai-review team --stage plan` passes or all valid findings are addressed.
- `git diff --check` passes.
- Future manuscript implementation includes `make paper-doctor`,
  `make paper-sync`, and `make paper-build`, or a recorded local-tooling
  blocker.
- Future manuscript implementation verifies codec generated assets in both
  `build.py` bundle lists and an extracted arXiv upload tarball compile, or
  records an explicit TeX/tooling blocker plus tarball-content audit.
- Future manuscript implementation runs `make paper-audit-bundle` from a clean
  tree and verifies `repo/research/decision-log.md` is present in the audit
  tarball after hard-failing missing `AUDIT_EXTRA_FILES` entries.
- Future manuscript implementation verifies refresh paired stats from
  `summary_json["items"][]` rows, not aggregate rates, and hard-fails if item
  rows or required keys are missing.
- Future manuscript implementation verifies the paper-science gates from this
  plan: dirty-tree pooled-refresh artifacts are either rerun clean or labeled
  advisory; the refresh table contains the pixel baseline and `fused` source;
  no refresh claim quotes agreement without reuse and the pixel baseline; the
  38/57 versus 39/57 dense-baseline mismatch is resolved or footnoted with
  source paths; and the OneVision citation uses only source-confirmed facts.
- Future manuscript implementation completes the vocabulary audit with the
  explicit `safe` carve-outs above and leaves no codec-summary use of "safe" in
  paper-facing prose.
- Final response names the committed plan and the review status.
