# Paper Claim Matrix

Last updated: 2026-05-03

This is the single-file answer to "what must be true before we can
make each claim in the paper?" Per codex 2026-04-16 review: keep
the repo aligned to a ship-worthy thesis instead of an endless good
research program.

## Paper thesis

> Training-free anti-recomputation can improve video-VLM efficiency in
> three distinct regimes: first-pass visual processing, after-ingest
> follow-up queries on the same video, and benchmarked routing under a
> frozen dense backend. The paper's job is to keep those regimes
> separate, quantify them honestly, and explain where fresh visual evidence
> must be placed over time to stay on the relevant quality-compute frontier.

The paper may discuss VLM-native media, machine-oriented sidecars, sensor-
fusion world-state codecs, and hardware-aware active tiles only as future
requirements suggested by the measurements. They are not promoted claims in
this matrix until local evidence lands.

Phase 1.29 now lands as a local codec-native planner-substitution bridge, not a
systems-speed bridge. Paper wording should therefore stay protocol-qualified:
sparse-QA routing remains pixel-diff proxy, while the narrow local 1.29 row can
be called codec-guided in the semantic-planner sense.

## Claim matrix

| # | Paper claim | Required evidence | Current status | Blocker | Promotion rule |
|---|---|---|---|---|---|
| 1 | Pixel-diff proxy has measurable (not perfect) point-predictor fidelity for ViT feature change | Phase 1.36 oracle reports per-block Pearson r by benchmark; pixel→feature correlation is non-trivial | **LOCAL DIAGNOSTIC COMPLETE, NOT RELEASE CLAIM-BEARING YET.** Phase 1.36 records best pixel-stat Pearson r=0.233 (TOMATO MEAN) to r=0.504 (MVBench CPF) on a 45/60-item cache-hit subset. Weak-to-moderate, content-dependent. The raw outputs were under ignored `results/feature_change_oracle/`, so this remains mechanism context until materialized as checked artifacts. | Regenerate or materialize the phase 1.36 raw outputs before using exact oracle numbers as paper-body evidence. | Local diagnostic until artifact-backed |
| 2 | Naive mean-diff is too blunt on temporally concentrated evidence | Phase 1.36 oracle + Planner 2.0 ablation show that the best routing statistic is NOT the best point predictor; falsified-hypotheses ledger entry for mean-diff default | **LOCAL DIAGNOSTIC COMPLETE, NOT RELEASE CLAIM-BEARING YET.** The phase 1.36 note records MAX_ABS as 2nd-to-last as a point predictor on both benchmarks while winning in Planner 2.0 routing, which supports the mechanism story. Raw oracle outputs were ignored local files, so this can guide prose but should not be promoted as an exact paper-body table until checked in. | Regenerate or materialize the phase 1.36 raw outputs before using exact oracle numbers as paper-body evidence. | Local diagnostic until artifact-backed |
| 3 | Concentration-aware routing (within-block child-veto, neighbor-halo veto, sticky-dynamic, age-bounded) repairs hard temporal failures | Phase 1.37 within-block child-veto OR phase 1.37B neighbor-halo veto + phase 1.26 sticky + age-bounded all evaluated on dev/holdout | Sticky4 passes MVBench holdout (1.26.B) but remains supplementary until rerun clean. Phase 1.37B **neighbor-halo veto RETIRED 2026-04-17 as preregistered null** — code landed (commits 2ebf90d, db10e12, 0ea69fe, 46b5d05, 2947198; `NeighborHaloVetoConfig` + `apply_neighbor_halo_veto` + 10 unit tests; Track A `--halo-veto-percentile` / `--halo-veto-neighborhood` CLI flags) and the full 9/9 cells × 2 benchmarks dev sweep landed. **TOMATO NO-LIFT**: control cached_accuracy=0.233 is rank-1 and within MRU 1/30=0.034 of every cell (halo moves only agreement 0.833→0.867–0.933 at the cost of fresh-frame budget 3.77→4.20–6.58). **MVBench NO-LIFT-NEGATIVE**: halo hurts — control is sole rank-1 at 0.800, 7/8 halo cells lose 0.067–0.100. No holdout run per the frozen promotion rule (no cell clears the 1/30 MRU bar). Phase 1.37 within-block child-veto remains preregistered but NOT YET IMPLEMENTED (distinct mechanism, lives in `_mix_qwen_features`); it is now the only remaining path toward claim 3 evidence. See registry row 1.37B and `research/experiments/2026/2026-04-17-phase-1_37B-neighbor-halo-veto-prereg.md` for full provenance. | Phase 1.37 within-block child-veto implementation + dev + holdout, plus a clean rerun for sticky4 if the refinement is used beyond supplementary discussion. Halo variant is off the table per frozen rule. | Claim on clean N=30 sticky4 or another surviving concentration-aware refinement plus at least one veto variant result; halo variant is unavailable, child-veto remains the only candidate. |
| 4 | Saved budget placement matters more than quantity | Phase 1.38 temporal placement ablations show middle-event items; phase 1.28 shows 16-frame saturation | Partially supported (1.26 asymmetry, 1.28 saturation) | Phase 1.38 run | Claim when ablations + oracle + N=30 all converge |
| 5 | Real sparse execution converts proxy gain into measured speedup | Measured sparse-execution harness: wall-clock decode/preprocess/vision/prefill/generation + peak memory + FLOPs | **LANDED AS A BOUNDED ENVELOPE, NOT A BROAD SPARSE BACKEND.** Phase 1.63G gives Gemma measured sparse vision over 8f/16f/32f with zero paired accuracy delta and 100% choice agreement at each frame count; the cleanest operating point is 32f short at 1.316× first-query E2E, 0/20 paired drift, dense/sparse parse failures 0/0, and -0.012× ceiling gap. Caveat: the full Gemma sweep has matched dense/sparse parse failures and 8f misses the ceiling tolerance (+0.062×). Qwen 1.63E/H/J supplies the boundary: 8f `kr_V∈{0.25,0.50,0.75}` tightly validates timing but all cells fail fidelity; 16f `kr_V=0.85` recovers to within aggregate-accuracy/format/ceiling gates but gives only 1.032× E2E and 13.6% vision-time reduction. | Broader sparse-backend curve, competitor comparison, and conservative operating-point search remain open. | Sparse execution is no longer prospective: real skipped vision work exists, with one clean Gemma cell and a Qwen configuration boundary. Do not promote it as a universal fidelity-preserving backend. |
| 6 | Method survives on temporal-reasoning benchmarks at N=30 | Phase 1.21 MVBench N=30 + phase 1.20 TOMATO N=30 | **BOTH HALVES PAPER-GRADE (clean trees).** MVBench: base 0.600@4.06 (Pareto win vs dense-6). TOMATO: base 0.333@3.55 (Pareto tie vs dense-8 at 44% budget). | Done | Full claim satisfied with clean provenance |
| 7 | Architecture-conditioned reuse fidelity is a spectrum (not binary: windowed-mostly = byte-identical; all-global = high-fidelity approximate but can still be lossless depending on pretraining) | Phase 1.42 attention-topology (Qwen windowed vs Gemma global + optional InternVL3 all-global) | **PARTIAL, now benchmarked on a second local architecture (2026-04-24).** Qwen remains the exact/high-stability reference family. Gemma 1.57 already strengthened the mechanism story on VideoMME long dev n=10 with corrected pooled cached-feature geometry (`133` cached tokens/frame): STATIC adjacent-frame cosine is **0.769 / 0.794 / 0.807** at 8f / 16f / 32f, materially above Qwen long-bucket values at matched frame counts. The new Gemma 1.42 holdouts convert that into answer-level evidence: **TOMATO motion N=30 passes** the preregistered fidelity gate (`agreement=0.933`, `dense_acc=cached_acc=0.267`), while **MVBench motion N=30 fails the strict-agreement gate** (`agreement=0.733`, `dense_acc=cached_acc=0.200`). So the local evidence now supports a stronger but narrower claim: reuse fidelity is architecture-conditioned **and benchmark-conditioned**. Gemma can preserve aggregate accuracy exactly while answer identity drifts more than on Qwen. | Third-architecture or tighter Gemma follow-up only if it materially changes the benchmark-conditional spectrum story | Claim on ≥ 2 local architectures with different attention topologies; universal "all-global = high-fidelity approximate" wording no longer defensible |
| 8 | Validated on VideoMME (de facto benchmark standard) | Phase 1.41 VideoMME lane on Qwen 7B | **EARNED 2026-04-18 (8f); strengthened 2026-04-19 (16f, 32f); holdout 16f EARNED 2026-04-21; 1.57 holdout geometry re-check landed 2026-04-23.** Qwen 2.5-VL-7B-Instruct-4bit (MLX) on `videomme_dev_v1.toml` n=30 AND `videomme_holdout_v1.toml` n=30. **8f dev**: `dense_acc=0.533`, bucket short 0.800 → medium 0.500 → long 0.300. **16f dev**: `dense_acc=0.567`, short 0.800 → medium 0.700 → long 0.100. **32f dev (2026-04-19)**: `dense_acc=0.533` (n=30), short 0.800 → medium 0.700 → long 0.100 — **zero flips vs 16f per-bucket; long bucket plateau confirmed as third data point**. **16f holdout (2026-04-21, task #160)**: `dense_acc=0.700` (21/30), short 0.600 → medium 0.600 → **long 0.900**. The 16f long-bucket regression observed on dev (8f 0.300 → 16f 0.100) **did NOT replicate on holdout** (holdout 16f long 0.900); non-monotone long-bucket shape is item-draw-dependent. All four frame counts × splits: `parse_failures=0`, `agreement=1.000` (identity cache bit-faithful), peak RSS 7.23 GB. **Phase 1.57 mechanism ablation landed 2026-04-19 on same manifest** — adjudicates the 16f→32f hypotheses: per-bucket drift (adjacent-frame ViT cos, STATIC class — **lower-bound proxy** on cache-substitute error via adjacent fresh-vs-fresh cosine, NOT a direct cache-substitute measurement; the 1.45/1.46 identity controls are the direct path) shows 8f→32f rise 0.567→0.676 (short, accelerating), 0.575→0.639 (medium, sub-linear), 0.545→0.592 (long, saturated at 16f). **H-drift-compounds REJECTED** (direction is rise, not decline); **H-saturation SUPPORTED** on dev (long-bucket drift AND accuracy both plateau at 16f co-saturation); H-stride-window neutral; H-4bit-quant (1.58) deferred. **Phase 1.57 holdout re-check (2026-04-23)** upgrades the drift story: per-class geometry transfers to holdout at 8f and 16f with max \(|\Delta| \le 5\)pp across class × statistic pairs, so the dev-only part is the downstream long-bucket accuracy shape, not the drift signal itself. Prereg: `2026-04-19-phase-1_41-qwen-videomme-16f-prereg.md`, `2026-04-19-phase-1_41-qwen-videomme-32f-long-prereg.md`, `2026-04-19-phase-1_57-feature-drift-mechanism-prereg.md`, `2026-04-21-phase-1_41-qwen-videomme-16f-holdout-prereg.md`. Findings: `2026-04-19-phase-1_41-qwen-videomme-16f-findings.md`, `2026-04-19-phase-1_41-qwen-videomme-32f-long-findings.md`, `2026-04-19-phase-1_57-feature-drift-findings.md`, `2026-04-21-phase-1_41-qwen-videomme-16f-holdout-findings.md`, `2026-04-23-phase-1_57-holdout-recheck-findings.md`. | **32f NOT Pareto-efficient on this model/benchmark** — 2× prompt tokens, 2× latency, zero aggregate acc lift over 16f. Long-bucket plateau on dev confirmed at 16f onward; bucket-dependent attention-mixing ceiling means per-bucket drift caveats must accompany per-bucket acc in paper. Drift is a *co-indicator* of capacity plateau, not the binding constraint — short-bucket acc is flat from 16f despite drift still rising at 32f. **16f holdout (2026-04-21) shows the long-bucket plateau does NOT replicate cross-split**: holdout 16f long 0.900 vs dev 16f long 0.100. **1.57 is therefore split-portable as a drift-geometry result, not as a long-bucket accuracy law.** Phase 1.58 (bf16 quantization ablation) remains the open mechanism question. | Claim on local VideoMME evaluation earned at 8f, 16f, and 32f dev + 16f holdout; per-bucket scaling surface fully mapped with drift-geometry evidence on dev + holdout and a cross-split long-bucket non-replication caveat on the accuracy shape. |
| 9 | Beats novelty-ranked dense at matched budget | Phase 1.34 novelty-ranked dense baseline | **DIAGNOSTIC COMPLETE, NOT RELEASE CLAIM-BEARING YET.** The phase note records a full 2×3 grid N=30: TOMATO novelty N=4 ties uniform (0.133), N=6 and N=8 hurt by 0.100; MVBench novelty N=4 beats uniform by +0.067, N=6 ties, and N=8 loses by 0.067. Cached base on each benchmark (0.333@3.55 TOMATO, 0.600@4.06 MVBench) dominates every recorded novelty-ranked cell at equal-or-lower fresh-frame budget. The raw outputs were under ignored `results/`; keep this as local diagnostic support until the raw rows are regenerated or materialized as checked artifacts. | Regenerate or materialize the phase 1.34 raw outputs as checked artifacts before using as paper-body evidence. | Local diagnostic only until artifact-backed |
| 10 | Composition with within-frame methods (FastV/FlashVID) is an open measured question, not an assumed multiplier | Phase 1.32 FastV pilot or FlashVID comparison OR **phase 1.52R temporal+spatial on Gemma** | NOT STARTED; two paths now queued (original: mlx-vlm fork; new: phase 1.52R on Gemma). The manuscript now treats composition as ceiling-bounded until a direct stacked run earns more. | Phase 1.52R depends on 1.42+1.51R | Deferred; claim only after measured |
| 11 | Novelty-pruning visual tokens before LLM prefill delivers end-to-end speedup on Gemma 4 | Phase 1.51R novelty-pruning on Gemma (5 anchor arms × 5 keep rates dev tranche, single-shot holdout) | **DURATION-CONDITIONAL PARTIAL REPRODUCTION (2026-04-18).** Stage 1 n=30 at kr=0.5: e2e=1.00×, gen=1.01× — **pre-registered NULL at the pre-release reference kr**. Stage 2b n=30 at kr=0.10: e2e=1.12× aggregate, gen=2.62×, **Δacc=-0.10 (NOT accuracy-preserving aggregate)** with bucket asymmetry (medium Δacc=0 at 2.71× gen; short -10pp; long -20pp). Stage 5 (kr=0.50 n=30 × 3 anchors): **gemma_structural = paper default** (Δacc=-0.033, mask cost 2ms, +0.10 long-bucket lift); nuwa_pillar REJECTED. Stage 6 gemma_structural kr sweep (n=30 each): **8f Pareto knee = kr=0.33 short-bucket (Δacc=0 at e2e=1.090× per_tok=7.904×)**, does NOT extend to kr=0.25. Stage 6 32-frame regime match (n=10 per bucket, kr=0.10, anchor=none): H1 long FALSIFIED (1.234× below [1.5, 2.0]); H1' short favorable falsification (1.663× above [1.40, 1.55]); H1'' medium strict-inside-band EARNED (1.565×). **Δacc bucket-invariant at -0.100 across all three 32f buckets at kr=0.10**. Cross-bucket 32f aggregate (n=30 dev): **e2e = 1.389× time-weighted at Δacc=-0.100 — DEV-ONLY, NOT a paper headline** (holdout not run; per-bucket are the primary reportable results). *Methodology note (Codex round-21, 2026-04-19):* the earlier 1.487× figure was a mean-of-bucket-ratios; correct aggregate is `sum(dense_e2e)/sum(pruned_e2e) = 2458.03s/1769.88s = 1.389×`. Stage 7 (32f short × kr=0.33 × gemma_structural n=10): 8f recipe does NOT generalize — Δacc=-0.100 at 1.558×; kr=0.10 anchor=none strictly dominates in 32f short. **Ceiling implication:** long-32 ceiling@∞ = 1.312× (decode-bounded at 56.9% of e2e) — the pre-release 1.8× long is arithmetically unreachable without Phase 1.54 decode acceleration. Short/medium levers belong to Phase 1.51V. **Full stage history:** `research/experiments/2026/2026-04-19-claim-11-reproduction-log.md` (Stages 1/2b/3/5/6/7 with per-bucket numbers, ceiling decompositions, and confound checks). See row 13 (C-CEILING) for the analytical contribution graduating from this work. | Claim earned on ≥ 1.8× end-to-end speedup (not generate-only) with accuracy within 0.10 of Gemma-dense-8 on one benchmark. **Stage 2b n=30 kr=0.10 e2e=1.12× aggregate, -10pp accuracy — partial reproduction, not a full paper result at the pre-release bar.** The medium-bucket slice (Δacc=0 at 2.71× gen) and the 8f kr=0.33 gemma_structural short-bucket (Δacc=0 at 1.090×) anchor the paper if Stage 5 anchors don't close the aggregate gap. Paper fallback: "duration-conditional partial reproduction + pre-registered null at the pre-release kr" with the duration × kr grid as the headline figure. |
| 12 | Method generalizes to long-form egocentric video (EgoSchema) | Phase 1.43 EgoSchema lane on Qwen 2.5-VL | NOT STARTED; preregistered | EgoSchema loader + manifest | Claim earned on N=30 holdout with agreement ≥ 0.80 and Pareto tie-or-win vs matched dense |
| 13 | **C-CEILING:** Token-pruning wall-clock speedup is predicted within ≤5.2% by an arithmetic-ceiling model `e2e ≤ 1/(fixed_frac + (1-fixed_frac)/s)` where fixed_frac = (D+P+V)/e2e and s = per-token generate speedup. Standalone analytical claim, independent of any specific SOTA arm. | Seven independent LLM-side/token-pruning regime dimensions cross-validate the original model at ≤5.2% error on Gemma 4-E4B-4bit: 8-frame LLM-side keep-rate sweep (`kr_R=0.10/0.25/0.33` n=30 each), 32-frame smoke (n=1), 32-frame long (n=10), 32-frame short (n=10), 32-frame medium (n=10), 32-frame short × gemma_structural × `kr_R=0.33` (n=10 — second anchor arm). Median error 2.1%, worst 5.2%. The manuscript's C-VISION scatter-back figure is a separate 17-regime rendered view that includes advisory/boundary cells; do not summarize those 17 points as all within 5.2%. | **EARNED (2026-04-18).** Seven-regime LLM-side cross-validation done. All predictions were pre-registered BEFORE observation in individual phase prereg docs; all fall within stated bands. Decode cliff between medium and long buckets (seek-dominated) is a testable corollary quantifying where Phase 1.54 pays off. The later Qwen 8f keep-rate sweep validates the timing axis on a second architecture even when fidelity fails. | None for the standalone claim. To strengthen further: validate on another Qwen benchmark or a server-class timing setup. | Claim earned: ≥ 5 independent LLM-side regimes validated, each with pre-registered predictions, all within ±10% of observed. **Already satisfied.** |
| 14 | **Persistent-KV follow-up latency.** After-ingest same-video follow-up reuse delivers the largest local speedups, but only inside a tested/tolerated envelope and with paired-drift accounting. 7B is clean at 16f / ~6.5k prefill tokens and the 8f point remains within the preregistered criterion despite Δacc=-0.048; 3B is bounded/tolerated through 36f / ~14.5k with Δacc=-0.19, not clean. Selective re-prefill is now broad local recovery evidence: fixed K=1 has no observed paired drift on n=93 across 20f short/medium/long plus 32f short at 9.48x-20.37x same-class speedup, and adaptive repaired-cache inheritance has no observed paired drift on the same n=93 breadth at 14.90x-35.92x same-class speedup and a 15.28x-35.97x cold-all-query ratio. The operating envelope is now bounded by dense-answer-anchored prompt variation: fixed K=1 has 0/133 observed follow-up drift, while adaptive repair and refresh-10 each show 6/133 paired drift at roughly 0.7 s follow-up latency. | Phase 1.55A speedup/basin curve plus phase 1.55D/E/F/G/H/I/K/L/M and adaptive-mechanism selective-reprefill artifacts; paired session-vs-cold queries, drift audits, pathological-output counts, same-class/all-query follow-up latency denominators, stage-timing attribution, sampler-temperature/seed sweep, setup-inclusive economics, 50-turn repeated-question stress, and dense-answer-anchored prompt-variation stress. | **EARNED for after-ingest follow-up regime; BOUNDED for deployment envelope.** Speedup mechanism earned on the 6-point curve; fixed K=1 repair broadened to n=93 and survives 1.55M; adaptive breadth is the primary repaired follow-up headline under stationary same-video sessions; 1.55K shows the short-cell adaptive mechanism is not greedy-only across temperatures/seeds; 1.55L shows adaptive and scheduled refresh remain drift-free through a 50-turn repeated-question stress; 1.55M shows aggressive policies have real 4.51% drift under dense-answer-anchored prompt variation. | Natural-dialogue many-turn stability, cross-architecture C-PERSIST once Gemma cache semantics are safe, causal/independent guard features beyond the landed KV-cache distance probe, and clean submission artifact bundle. | Claim only as same-video follow-up latency, never first-query latency; report paired drift and denominator with every speedup. |

| 15 | **C-VISION:** Vision-tower pruning at mid-layer `L=2` with keep-ratio `kr_V=0.50` is a benchmark- and frame-count-aware reduction mechanism whose end-to-end effect is governed by the scatter-back ceiling `E2E ≤ 1/(1 − V_share × V_red)`. Mechanism generalizes across VideoMME, MVBench, and TOMATO, but headline magnitude is regime-conditional on `V_share` and on the paired-fidelity status of each holdout cell. | Phase 1.51V expansion 12/12 dev cells (VideoMME 8f/16f, MVBench 8f, TOMATO 8f; `kr_V ∈ {0.25, 0.50, 0.75}`; thermally paired n=30 each), 32f probe (EXP13/14), holdout session 2 for V+novelty stack replication, and holdout sessions 3–5 for the V-only unpatched-vs-patched pairs. | **EARNED 2026-04-21 as the headline first-pass claim.** Dev n=30 headlines: VideoMME 1.08× (8f) / 1.12× (16f), MVBench **1.21×**, TOMATO **1.24×**. The original six core scatter points track within 2.7pp; the expanded 17-regime view includes an advisory MVBench holdout residual of 13.6pp, so the old shorthand “V_red ≈ 40% benchmark-invariant” needs softer wording. MVBench’s aggregate loss localizes to three object-binding flips rather than broad degradation. | **V-only UNPATCHED-vs-PATCHED holdout status (three benchmarks):** VideoMME 8f **CLOSED clean** 2026-04-21 session 3 EXP17/18 (E2E 1.113×, V_red 0.413, decode Δ 1.53%, acc Δ 0.000; holdout V_share 15.45%). MVBench 8f **CLOSED advisory** 2026-04-21 session 4 EXP19/20 (E2E **1.407×**, V_red **0.471**, acc Δ −0.033; thermal gate formally fails, but the 50 ms absolute decode delta sits at OS-jitter scale on a 432 ms decode window). TOMATO 8f **EARNED-ADVISORY** 2026-04-21 from checked-in session-5 artifacts (EXP23/24: E2E **1.194×**, V_red **0.350**, acc Δ −0.067; revised thermal gate misses by 19 ms in the favorable direction). The three-benchmark first-pass story is effectively closed, but MVBench and TOMATO keep their advisory footnotes. **Composition appendix — EXP10 n=60 CLOSED-NULL 2026-04-21 (session autonomous, task #152):** V-only reference E2E 1.0159×, V+novelty E2E 1.0420× on VideoMME dev+holdout n=60; lift 2.6pp FAILS ≥4pp gate; agreement 0.65 FAILS ≥0.75; acc Δ −0.017 PASSES. Prereg primary 1.10× gate FAILS (observed below 1.08× partial-confirm line by 3.8pp). Thermal gate FAILS (decode Δ 3.07% rel, direction adverse, thermal-correction does not cross 1.08×). Ceiling model reproduces observation to within 0.2pp: fixed_frac = 0.875 (decode-dominated pool, V_share = 6.26% vs dev 15.2%), so arithmetic ceiling at observed per-token generate speedup 1.446× is 1.041× — the regime is compute-bounded on decode. Composition is **ceiling-bounded, not unbounded**. Findings: `research/experiments/2026/2026-04-21-phase-1_51V-exp10-n60-findings.md`. | Claim earned as paper-grade first-pass evidence, with benchmark-specific clean versus advisory status made explicit in the manuscript and provenance. Composition-appendix claim does NOT land; paper reports composition as regime-conditional with the ceiling model as the explanation. |

**2026-04-29 measured sparse-execution update for Claims 5/15:** The paper can
now say real timed vision work was skipped in local runs. Keep it separate from
the older semantic first-pass holdouts: Gemma 32f short is the current clean
operating point, the broader Gemma sweep has matched parse-failure caveats, and
Qwen exposes a keep-rate/fidelity boundary rather than a broad success. The
new Qwen 8f keep-rate sweep is timing-validation evidence, not a Qwen fidelity
win.

## Tested Deployment Envelope (claim 14, practitioner summary)

Rendered as `paper/figures/c_persist_safe_budget.png` (data JSON
companion `..._data.json`). Cross-architectural tested/tolerated prefill
envelope from Phase 1.55A four-regime probe (Qwen 2.5-VL, n=21 per cell):

| Model               | Tested/tolerated prefill tokens  | Tested/tolerated frame count (VideoMME short prompts) | Observed speedup | Accuracy floor at tested edge |
|---------------------|----------------------|--------------------------------------------|-------------------|-------------------------------|
| Qwen 2.5-VL-7B-4bit | ≤ ~6,500             | ≤ 16f                                      | 47×–91×           | Δacc = 0.000 at 16f (clean)   |
| Qwen 2.5-VL-3B-4bit | ≤ ~14,500            | ≤ 36f                                      | 91×–215×          | tolerated Δacc = −0.19 pre-basin plateau (three-point 24f/32f/36f) |

**Crossing the tested threshold triggers a bracketed basin onset:**

- **7B basin onset at ~8,000 prefill tokens (20f)**; saturated single-token `addCriterion` attractor by 24f. Tested temperature changes do not recover clean letters.
- **3B basin onset bracketed to (36f, 40f] ≈ (14,500, 16,100] prefill tokens** — ~11% depth window, SHARP. Sampler-dispersible at 40f, but only to the pre-basin plateau noise floor (Δacc=−0.19), NOT to baseline.
- **Failure geometry is cross-architectural:** non-letter attractor emergence on both models once basin is entered (7B `addCriterion`; 3B empty/"The").

**Deployment-envelope recommendation:** treat 7B persistent-KV reuse as tested
through ≤16f / ≤6.5k prefill, with clean fidelity at the 16f point and the 8f
point within the preregistered criterion despite Δacc=−0.048. Treat 3B as a
bounded/tolerated regime through ≤36f / ≤14.5k prefill with Δacc=−0.19, not as
clean fidelity. Fidelity recovery inside the 7B basin now has local evidence:
fixed `K=1` selective re-prefill shows **no observed paired drift on the landed
n=93 short/medium/long + 32f-short tranche** (`Δacc = 0.0`, paired diffs
`0/93`, `0/62` pathological follow-up attractors; one-sided rule-of-three upper
bound ≈3.2% on an unseen paired-diff rate). The canonical fixed-K same-class
speed range is `9.48×–20.37×`. The adaptive repaired-cache policy is now the
strongest broad repair lane (`0/93` paired diffs, `15.28×–35.97×` all-query
speedup, `14.90×–35.92×` same-class speedup). The many-turn stress now extends
the cache-horizon evidence: adaptive repaired-cache inheritance and scheduled refresh are
drift-free through a 50-turn repeated-question cycle on seven 20f short videos,
while fixed `K=1` stays below the 3% drift gate but shows nonzero repeated-question drift.
The dense-answer-anchored stress now defines the aggressive-policy boundary:
fixed `K=1` has 0/133 observed follow-up drift, while adaptive and refresh-10
show `6/133` paired drift at roughly 0.7 s median follow-up latency.
The remaining scope gaps are natural-dialogue many-turn stability,
cross-architecture C-PERSIST once Gemma cache semantics are safe, and
cache-state causal instrumentation, not basic runnability.

**2026-04-30 scale-out bundle update:** candidate C-STREAM now has a checked
mixed bundle on an M5 Max MacBook Pro with 128 GB unified memory, but it
remains a bounded evidence lane rather than a fourth headline. The checked
26B-class scale-out bundle shows default mixed-topology cross-turn cache reuse
is unsafe; a topology-aware prefix snapshot gives positive small-N follow-up
rows; fixed-evidence screen/UI baselines favor low-FPS dense over the tested
event-window proxy; and exactness claims must separate zero correctness delta
on 1,937 logged rows from byte-identical raw-paired text on 513 rows.
The derived perception-fps view is after-warm only: 27.02 fps median at 8f
(8/21 rows >=30 fps) and 54.68 fps median at 32f (19/21 rows >=30 fps), traced
to the May 2 findings note and the checked Sam prefix-snapshot JSONL rows.

## V_share Governs 1.51V Gains (claim 15, ceiling validation)

Rendered as `paper/arxiv/generated/figures/v_share_v_red_ceiling.png`
(data JSON companion
`paper/arxiv/generated/data/v_share_v_red_ceiling_data.json`). Scatter-back
ceiling `E2E ≤ 1/(1 − share × reduction)` now has **17 plotted regimes**:
4 Gemma C-VISION dev cells, 3 Gemma holdout cells, 1 matched Qwen
cross-architecture cell, 1 n=60 composition-audit cell, and 8 measured sparse
vision cells including the Qwen 8f keep-rate timing-only sweep, the Qwen 16f
aggregate/format boundary, and Gemma sparse-vision cells. The table below is
the original n=30/core explanation set; the paper figure is the expanded
accounting view:

| Regime                        | V_share (dense) | V_red observed | Predicted E2E | Observed E2E | Δ (obs − pred) |
|-------------------------------|-----------------|-----------------|----------------|---------------|-----------------|
| VideoMME 8f dev               | 15.2%           | 39.0%           | 1.062×         | 1.08×         | +1.8pp          |
| VideoMME 16f dev              | 24.3%           | 39.0%           | 1.105×         | 1.12×         | +1.5pp          |
| MVBench 8f dev                | 47.8%           | 40.0%           | 1.237×         | **1.21×**     | −2.7pp          |
| TOMATO 8f dev                 | 40.7%           | 42.7%           | 1.214×         | **1.24×**     | +2.6pp          |
| Qwen VideoMME 8f dev          | 10.3%           | 39.8%           | 1.043×         | 1.044×        | +0.1pp          |
| VideoMME holdout 8f (V+novelty, LLM-side) | 18.0% (G_share) | 33.4% (G_red) | 1.064×    | 1.064×        | +0.0pp          |

**Formula predicts within 2.7pp across the 6 original core scatter points**
(max |Δ| 2.7pp on MVBench 8f dev; Qwen cross-arch point lands at +0.1pp).
Mechanism generalizes across the vision axis on **two architectures**
(Gemma and Qwen) AND across the LLM-decode axis (holdout composition audit).
The expanded 17-regime figure also uses the Qwen 8f keep-rate sweep as
timing-axis validation under failed fidelity; the worst residual remains the
MVBench 8f holdout advisory row at 13.6pp. Headline magnitude is
regime-conditional on share-term:
vision-dominated benchmarks (TOMATO, MVBench) deliver >1.20× E2E; Qwen at
VideoMME 8f sits near 1.04× because the vision tower owns only ~10% of
wall-clock there; and at 32f the ceiling arithmetic says 1.14× is the
max even with thermal-perfect pairing.

**Architectural implication:** to break through the 1.20× barrier on VideoMME, the path is (a) move to vision-dominated benchmarks (TOMATO, MVBench — done, 1.21–1.24×), (b) raise V_share via longer frames (limited by decode thermals on M3), or (c) earn a direct stacked run. The current composition audit is ceiling-bound boundary evidence, not a headline multiplier.

## One paper, multiple evidence regimes (round-17 reframe, updated)

**The target is ONE paper that advances
anti-recomputation evidence across distinct reuse regimes.** Method work
serves that science goal and is welcome in an appendix; it is not a separate
methods paper. Both lanes must contribute evidence.

**Qwen routing regime (TOMATO + MVBench).**
- Claims 1, 2, 3, 4, 5, 6, 8, 9, 12 primarily exercise Qwen 2.5-VL.
- Role in the paper: validates the routing / bounded-staleness mechanism and the "pixel-diff proxy" story. Natural home for the method appendix.
- Currently earned for the manuscript surface: 6 and 8. Local diagnostics complete but not
  manuscript claim evidence until raw outputs are checked in: 1, 2, 9. Partial: 3
  (sticky4 only — supplementary rerun-required; halo-veto retired 2026-04-17 as
  preregistered null on TOMATO + MVBench dev, child-veto 1.37 remaining path), 4
  (asymmetry only; placement ablations pending), 5 (bounded measured
  sparse-execution envelope, not a broad sparse backend).

**Measured anti-recomputation gains (Gemma + Qwen follow-up).**
- Claims 14 and 15 now provide the strongest paper-facing numbers.
- Role in the paper: the main results section, not an appendix or future-work placeholder.
- Currently earned: local C-VISION first-pass gains and Qwen C-PERSIST
  follow-up-query gains. 26B default cache reuse is blocked by cache semantics,
  while the checked prefix-snapshot rows are positive small-N scale-out evidence.
  What remains open is broader composition, broad sparse-backend coverage, and
  native C-STREAM quality/baseline closure, not whether the paper has a
  headline result.

Prose must never conflate routing-backed evidence with scale-out-prospective evidence. When a claim sits in both lanes (e.g., claim 5 sparse-execution delta measured on either Qwen or Gemma), name the architecture explicitly.

## What must land before a paper submission (one-paper gate)

**Source-of-truth note (codex round-26 2026-04-21):** the authoritative
venue-readiness / submission-gate doc is `paper/priority.md`. This
section conforms to it. The round-17 "claim 11 must be earned as the
big-number gate" framing has been **retired** — the paper spine is now
the three first-class contributions (claims 13, 14, 15), with claim 11
providing composition-appendix evidence conditional on EXP10 n=60.

**Required for the current anti-recomputation paper to make sense at all:**

- **Claim 13 earned (C-CEILING).** Already satisfied: 7 independent
  LLM-side/token-pruning regime dimensions cross-validate the arithmetic
  ceiling at median 2.1% / worst 5.2% error. Standalone analytical
  contribution independent of any specific SOTA arm. Do not conflate this
  historical validation set with the manuscript's expanded 17-regime
  C-VISION scatter-back figure, which includes advisory and boundary cells.
- **Claim 14 earned (C-PERSIST).** Already satisfied: 6-point speedup
  curve (47×→150×) + 4-regime temperature matrix + bracketed cross-arch
  basin-onset relation. The deployment-facing tested envelope is
  reviewer-ready: 7B is clean at 16f / ~6.5k prefill and 8f remains within the
  preregistered criterion; 3B is bounded/tolerated through 36f / ~14.5k
  prefill on a Δacc=−0.19 plateau, not clean.
- **Claim 15 earned (C-VISION).** Already satisfied on dev n=30 across
  three benchmarks, with the **holdout trifecta closed 2026-04-21**
  and differentiated advisory strength: VideoMME 8f CLEAN (EXP17/18
  session 3), MVBench 8f CLOSED-ADVISORY on thermal-calibration
  footnote (EXP19/20 session 4), TOMATO 8f EARNED-ADVISORY on
  favorable-drift footnote (EXP23/24 session 5). Scatter-back ceiling
  `E2E ≤ 1/(1 − V_share × V_red)` is predictive across dev and holdout
  cells.
- **Claim 8 earned (VideoMME lane).** Dev at 8f / 16f / 32f on Qwen
  7B-4bit with per-bucket scaling surface mapped, mechanism
  co-saturation evidence (phase 1.57), **plus holdout 16f** (agg
  0.700, 21/30; 2026-04-21). The 16f long-bucket regression observed
  on dev did NOT replicate on holdout (dev 16f long 0.100 vs holdout
  16f long 0.900); non-monotone shape is item-draw-dependent, 1.57
  co-saturation framing stays local to dev.
- **Claim 6 earned (method on ≥ 2 temporal benchmarks).** Already done
  (TOMATO + MVBench paper-grade N=30).
- **Claim 5 remains explicitly separate.** Measured sparse-path
  wall-clock has landed as a bounded local vision-tower envelope and must
  still not be implied by the routing lane. Treat it as real skipped vision
  work with architecture/configuration caveats, not as a broad sparse backend.

**Strongly recommended to strengthen the paper** (`priority.md`
should-do tier):

- ~~EXP10 n=60 composition-audit gate.~~ **CLOSED-NULL 2026-04-21.**
  n=60 landed E2E 1.042× / lift 2.6pp / agreement 0.65 / acc Δ −0.017;
  2/3 promotion thresholds FAIL, ceiling-arithmetic explanation lands
  (fixed_frac = 0.875 caps any LLM-side gain at ~1.04×).
  Composition is ceiling-bounded, not multiplicative; no paper-level
  appendix claim earned. See `claim-matrix.md` row 15 sub-row and
  `research/experiments/2026/2026-04-21-phase-1_51V-exp10-n60-findings.md`.
- ~~**Claim 5 measured sparse-execution delta** on at least one path.~~
  **CLOSED as a bounded envelope 2026-04-29.** Gemma gives the clean
  operating point at 32f short; Qwen supplies the configuration boundary.
  Broader sparse-backend coverage and matched competitor comparisons remain
  strengthening work.
- **Cross-arch C-VISION probe on Qwen.** **CLOSED 2026-04-23.**
  C-VISION is now two-architecture mechanism evidence at matched
  \(L=2\), \(kr_V=0.50\); broader benchmark coverage on the second
  architecture remains optional strengthening, not a missing gate.
- **1.29 local codec-native benchmark slice.** **LANDED as planner-substitution
  evidence, not latency evidence.** Continuous H.264-derived codec scores with
  dense choices on VideoMME dev all-duration n=30 (codec-dense agreement 1.000,
  codec accuracy = dense accuracy = 0.533, parse failures 0) and short
  dev+holdout n=20 passes on the -5pp boundary. Subsequent calibration-mode and
  calibration-source ablations are answer-level identical on the local slices
  we ran, so the remaining blocker is systems-side rather than semantic-side:
  offline extraction totals 7290s, and any speed claim still requires
  streaming decoder integration.
- **1.51V scroll/pan regime-boundary probe (phase 1.60).**
  CLOSED 2026-04-23 as a natural-VideoMME corpus limitation: wider
  60-item scan found 0/60 items above `shifted_fraction >= 0.30`
  (max 0.125), so scroll/pan characterization requires a different
  egomotion/scroll corpus or labeled synthetic set.
- **Claim 10 (phase 1.52 combined temporal+spatial on Gemma).**
  Measures composition rather than projecting it.
- **Claim 3 routing-mechanism evidence** (within-block child-veto or
  halo-veto replacement path).
- **Claim 9 novelty-ranked-dense disqualifier.**
  Diagnostic complete; manuscript claim requires regenerated or materialized raw
  outputs.

**Claim 11 (Gemma novelty-pruning ≥ 1.8× own-axis e2e) — RETIRED as
a headline gate.** Status: duration-conditional partial reproduction
with preregistered null at the pre-release kr; 32f cross-bucket dev aggregate
1.389× (not 1.8×); the 4B-class / 8-frame regime is arithmetically
bounded to ≤1.46× at kr=0.10 (C-CEILING). Stage 5 anchor comparison
lands `gemma_structural` as a paper-default (secondary methodology
content). The scientifically honest framing is "Gemma 4B / 8f
constitutes a preregistered duration-conditional partial reproduction
of the pre-release 26B / 32f novelty-pruning result; the arithmetic-ceiling
model quantifies why the absolute multiplier differs across
regimes". 1.51V's `E2E ≤ 1/(1 − V_share × V_red)` is the local
big-number mechanism (now claim 15).

**Can defer to paper discussion / future work / appendix**:
- Claim 12 (EgoSchema long-form)
- TempCompass as third benchmark
- Claim 4 (placement ablation) — strengthens, not required
- Broader sparse-backend coverage beyond the bounded measured sparse-vision
  envelope — described as future work with the ceiling upper bound already
  analytically characterized (claim 13 C-CEILING). Keep as strengthening work,
  not as a blocker for the three-contribution submission.

## Language rules

Per ChatGPT 2026-04-16 review:

- DO NOT say "confidence-conditioned" until answer-margin analyses
  land. SAY: "staleness × temporal-evidence concentration."
- DO NOT say "content-conditioned" (too broad). SAY: "temporally
  concentrated, fine-grained evidence dependence."
- DO NOT say "SOTA claim reopened." SAY: "paper slot reopened" or
  "SOTA-direction signal."
- DO NOT present measured sparse execution as a broad sparse backend. SAY:
  "bounded measured sparse-vision envelope" or "real skipped vision work with
  architecture/configuration caveats."
