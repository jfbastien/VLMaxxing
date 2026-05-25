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

- [ ] Perform a claim audit and paper-facing vocabulary cleanup.
  - Files: `paper/arxiv/sections/*.tex`, `paper/framing.md`,
    `paper/claim-matrix.md`, `paper/priority.md`,
    `paper/publishability-status.md`, `paper/terminology.md`,
    `paper/narrative-rules.md`, `paper/arxiv/sections/90_references.tex`.
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
  - Justification: denominator and provenance errors are fatal for this paper.
    The result can be important only if the reader can tell exactly what was
    measured and from what repository state.

- [ ] Audit dense-baseline consistency across codec result families.
  - Source artifacts:
    pooled-refresh summaries under
    `research/experiments/2026/artifacts/phase1_29_onevision_n57_pooled_calibration/`
    and sparse-pruning summaries under
    `research/experiments/2026/artifacts/phase1_51V_ov6_n57*/`.
  - The pooled-refresh table currently implies dense accuracy 38/57 = 0.667,
    while the sparse-pruning dense arm reports 39/57 = 0.684 on the N=57
    VideoMME-short Qwen 8f slice. Before manuscript promotion, either identify
    the protocol/provenance difference and footnote the two run-specific dense
    baselines, or rerun/derive a single canonical dense baseline for both
    tables. Do not silently harmonize by hand.
  - The generated snapshots must carry run IDs, manifest IDs, dense-answer
    hashes if available, and the source artifact path for each dense baseline.
  - Justification: adjacent tables with different dense baselines will look
    like an arithmetic error unless the provenance is explicit.

- [ ] Update repo paper-status docs before final manuscript edits.
  - Files: `paper/framing.md`, `paper/claim-matrix.md`,
    `paper/priority.md`, `paper/publishability-status.md`.
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
    codec-metadata result: pooled H.264 refresh preserves dense answers on
    56/57 VideoMME-short items while reusing roughly 10--11% of active visual
    evidence, or else label the number advisory until a clean rerun lands.
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
  - Add a short paragraph after the trained codec-native approaches paragraph:
    OneVision-Encoder trains a codec-aligned encoder with sparse codec
    patchification, irregular layouts, 3D RoPE, and large-scale objectives;
    VLMaxxing instead uses H.264 metadata as an external routing signal for
    frozen VLM inference.
  - Cite the arXiv primary source for OneVision-Encoder.
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

- [ ] Extend the paper generator before adding generated tables or figures.
  - File: `paper/arxiv/scripts/sync_sources.py`, or a new checked-in generator
    called from `paper-sync`.
  - Add codec-metadata snapshot builders that read the source artifacts named
    in this plan and write tracked `paper/arxiv/generated/data/*.json`
    snapshots with source paths, git provenance, artifact dirtiness, table cell
    inputs, confidence intervals, paired-test inputs, and sample sizes.
  - Add table/figure emitters that consume those snapshots and write the
    generated `.tex`/figure files. Do not hand-edit generated tables.
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

- [ ] Integrate the pooled H.264 refresh result into Qwen results as the
      strongest codec evidence.
  - Files: compact summary in
    `paper/arxiv/sections/07_results_cross_architecture.tex`, mechanism detail
    in `paper/arxiv/sections/06_results_qwen_routing.tex`.
  - Source artifacts:
    `research/experiments/2026/artifacts/phase1_29_onevision_n57_pooled_calibration/novel_coded/summary.json`,
    `research/experiments/2026/artifacts/phase1_29_onevision_n57_pooled_calibration/motion/summary.json`,
    and
    `research/experiments/2026/artifacts/phase1_29_onevision_n57_pooled_calibration/residual/summary.json`.
  - Add a compact Section 7 table block before the sparse-pruning table so the
    reader sees the refresh result before the bounded sparse-ranking result.
  - Add or update a Section 6 subsection after the routing frontier setup and
    before broad mechanism interpretation: "Compressed-video metadata as a
    refresh signal".
  - Include a small table with rows for `novel_coded`, `motion`, and
    `residual`: codec accuracy 0.684, dense accuracy 0.667, codec-to-dense
    agreement 0.982, active reuse roughly 10.6--10.8% from
    `codec_reuse_ratio_mean_active`, and Wilson lower bound 0.91 for agreement.
  - State the key claim as "56/57 dense-answer agreement with pooled thresholds"
    and explicitly say this skips refresh for about 10--11% of active regions;
    it is refresh planning, not sparse execution or session reuse.
  - If a clean rerun is not available when the manuscript edit lands, put the
    dirty-tree caveat in the table note and status docs instead of presenting
    the pooled result as final paper-grade evidence.
  - Remove stale or weaker codec-planner phrasing that only reports older
    per-item calibration or n=10/n=20 results if it no longer earns space.
  - Justification: this is the cleanest scientific result and should be in the
    main results, not hidden in an editor packet.

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
  - For setup-inclusive timing, do not hard-code any previously discussed
    live-versus-sidecar constants. Generate per-source live-versus-sidecar
    means and ratios from
    `mean_end_to_end_including_codec_score_runtime_ms` in the paired live and
    sidecar summaries. If the paper reports an aggregate ratio, declare the
    formula and store every input path/value in the generated snapshot.
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
    refresh planning transfers cleanly, sparse ranking transfers only at
    bounded operating points, and session composition remains blocked by
    first-query drift.
  - Replace "oracle" language with "signals" or "priors".
  - Add one systems sentence: sidecars are not the final decoder-integrated
    interface, but they passed zero-drift smoke gates across two vision
    geometries.
  - Justification: this turns mixed results into the actual contribution:
    mapping where codec structure helps frozen VLM inference.

- [ ] Tighten limitations and anti-claims.
  - File: `paper/arxiv/sections/09_limitations_reproducibility.tex`.
  - Replace the older codec-native bridge paragraph with current boundaries:
    Qwen refresh result is strong but Qwen-only; sparse ranking has favorable
    point estimates but inconclusive paired tests; Gemma accuracy evidence is
    smoke-level until M5; TOMATO dense baseline is too weak to promote; live
    PyAV extraction is not a deployable per-query path; session reuse
    composition is blocked by 12/57 first-query drift.
  - Explicitly say not to multiply refresh percentage, sparse keep-rate, and
    session reuse speedup.
  - Justification: strong limits make the codec result credible and prevent
    review damage from denominator confusion.

- [ ] Plan generated tables and figures so the paper gets stronger, not longer.
  - Main-text table candidate: one compact "Codec metadata results" table with
    three blocks: refresh planning, sparse pruning, sidecar extraction. If it
    becomes too dense, split sidecar extraction into a small systems table and
    move detailed per-source values to the appendix.
  - Generated tables and figures must be produced through
    `paper/arxiv/scripts/sync_sources.py` or another checked-in generator, not
    hand-edited generated `.tex`.
  - Track source snapshots under `paper/arxiv/generated/data/*.json` with
    source artifact paths, git provenance, table cell inputs, and any
    dirty-tree/advisory flags.
  - Conceptual architecture diagrams may be hand-authored as committed TikZ,
    SVG, or PDF figure sources under the paper tree. The generator/snapshot
    requirement applies to data-driven panels and all generated tables.
  - Generated table files to add or update via the generator:
    `paper/arxiv/generated/tables/codec_refresh_signal.tex`,
    `paper/arxiv/generated/tables/codec_sparse_pruning.tex`,
    `paper/arxiv/generated/tables/codec_sidecar_equivalence.tex`, or a single
    combined `codec_metadata_summary.tex` if space is tight.
  - Main figure candidate: a three-panel figure:
    A. H.264 bitstream to score sidecar to two consumers: refresh planning and
       sparse pruning.
    B. Agreement at the pooled threshold versus active reuse ratio, one point
       per score source. Do not imply a threshold-sweep curve unless a
       threshold-sweep artifact is added.
    C. Log-scale codec-evidence extraction time: live PyAV seconds versus
       sidecar milliseconds, with the n=3 pilot scale and denominator note.
  - Appendix figure candidate: real-video contact sheet / score overlay /
    selected tiles from the existing OneVision-VLMaxxing visual artifacts.
  - Remove or compress any older figure/table that repeats weaker codec-native
    per-item-calibration evidence.
  - Justification: the visuals should teach denominator discipline and the
    concrete systems path, not just decorate the new result.

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

- [ ] Run review and verification on the plan before manuscript edits.
  - Run `ai-review team --stage plan` against this plan and fix any valid
    findings.
  - Run `git diff --check`.
  - For the eventual manuscript-edit implementation, run the paper workflow:
    `make paper-doctor`, `make paper-sync`, and `make paper-build`, or record
    an explicit blocker if local TeX tooling is unavailable.
  - Confirm generated-table diffs are reproducible from the tracked JSON
    snapshots and canonical artifacts.
  - Run a vocabulary audit over `paper/arxiv/sections/*.tex` and paper-facing
    docs for `oracle`, `Track A`, `Track B`, `OV-`, `WOW`, `free codec`,
    `10,000x`, and `codec wins`; any remaining hits must be in traceability,
    explicit upper-bound language, or repo-facing terminology notes.
  - Confirm every manuscript cell or table note that draws from a dirty-tree
    artifact carries the advisory/pending-clean-rerun label.
  - Commit only the reviewed plan in this round.
  - Justification: the user asked for a full plan that Claude can review before
    we edit the manuscript.

## Constraints

- Do not implement query-aware or RLT work in this branch. Mention synergy only
  as future work when it helps frame sidecars.
- Do not use "Track A" or "Track B" in paper-facing prose.
- Do not call codec, pixel, or magnitude scores "oracles" unless the text is
  explicitly about a ground-truth upper bound.
- Do not claim statistically significant codec sparse-pruning superiority.
- Do not claim broad end-to-end VLM speedup from sidecars.
- Do not promote TOMATO motion gains from the current smoke.
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
  pooled H.264 refresh agreement 56/57 while reusing roughly 10--11% of active
  regions, with a dirty-tree caveat until rerun clean; Qwen sparse-pruning
  favorable point estimate 35/57 versus 31/57 but McNemar p=0.2188; sidecar
  extraction equivalence with zero drift and seconds-to-milliseconds
  extraction-path speedup.
- Open: M5 confirmations should update the table cells and scope language when
  they land, but they are not prerequisites for starting the edit.

## Verification

- `ai-review team --stage plan` passes or all valid findings are addressed.
- `git diff --check` passes.
- Future manuscript implementation includes `make paper-doctor`,
  `make paper-sync`, and `make paper-build`, or a recorded local-tooling
  blocker.
- Final response names the committed plan and the review status.
