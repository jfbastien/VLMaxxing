---
date: 2026-04-29
status: design doc; local scripts implemented for A1/A2/A4/A5/A6/A7
authors: Claude (lead), Codex (reviewer), JF (PI)
related:
  - research/experiments/2026/2026-04-29-paper-update-notes-v2.md
  - research/experiments/2026/2026-04-29-phase-1_63H-16f-kr-sweep-findings.md
  - research/experiments/2026/2026-04-27-phase-1_30AG-kcache-distance-prereg.md
---

# Phase 2 — Experiment Design (post-deep-mechanism)

This document is the agreed-on next-experiment slate after the deep-mechanism queue and 1.63H 16f kr-sweep landed. It incorporates Codex's read of the queue ("the science is materially stronger but two overclaims to avoid: Gemma 8f misses the ceiling gate, all Gemma cells have parse failures in both arms, and Qwen 16f kr=0.85 is fidelity-safe but only 13.6% vision reduction") and adds my own analysis from sub-agent investigations.

2026-04-29 Codex implementation update: A1/A2/A4/A5/A6/A7 now have run-capable scripts, and Sam's scale-out track has a strict JSON schema plus handoff doc. A6 is explicitly a **stateless same-video repeated-query horizon** to preserve continuity with the existing local C-PERSIST protocol; it is not a true conversational-history benchmark. A2 reports both label-free and explanatory-oracle variants so answer-aware features cannot be mistaken for deployable runtime guard evidence.

The design splits into two tracks:
- **Track A — Local (M3 Air, 16 GB unified, mlx 4-bit)**: configuration-envelope tightening, predictor enrichment, many-turn drift, low-FPS baseline, K-cache distance.
- **Track B — Sam (M5 MBP, 128 GB unified, 26B runtime)**: cross-protocol scale-out evidence; C-PERSIST/C-VISION/C-CEILING at scale; streaming baselines.

Total scope is the *complete* set of experiments needed to close the paper to reviewer-defense quality; we will execute a prioritized subset based on time budget.

## Executive summary

| ID | Phase | Track | Hours | Status | Tightens |
|---|---|---|---|---|---|
| A1 | Gemma format diagnostic | local | 0.5 | scripted, analysis-only | Gemma headline framing |
| A2 | 1.65v2 richer predictor | local | 0.5 | scripted, analysis-only on existing data | C-PERSIST limitations / future-work |
| A3 | 1.62D low-FPS dense | local | 3.5 | preregistered, script ready | "why not just 4f dense?" attack |
| A4 | 1.63I Qwen 16f kr fine-bracket | local | 9 | scripted | Qwen Track B real gate-pass |
| A5 | 1.30AG K-cache distance probe | local | 2 | scripted; needs smoke review | 1.30 boundary causal mechanism |
| A6 | 1.55L Many-turn C-PERSIST drift | local | 8 | scripted; stateless-query horizon | "two follow-ups" reviewer attack — biggest |
| A7 | 1.55K-extended seeds | local | 7.5 | scripted after seed plumbing | sampler-seed robustness |
| **Track A total** | | | **~28h** | (compute) + ~5h impl |  |
| B0 | 26B cache-correctness smoke | Sam | 1.5 | blocked on Sam | gating gate for C1 |
| B1 | 26B C-PERSIST replication | Sam | 8 | conditional on B0 | C-PERSIST scale-out |
| B2 | 26B many-turn streaming horizon | Sam | 10 | conditional on B0 | streaming first-class |
| B3 | Matched streaming baselines | Sam | 8 | conditional on B0 | C-STREAM real comparator |
| B4 | 26B sparse-ViT / C-CEILING | Sam | 8 | conditional on runtime support | C-CEILING at scale |
| B5 | 1,937 re-export | Sam | 1.5 | doc + tooling | reproducibility |
| **Track B total** | | | **~37h** |  |  |

Local execution order (A1 → A2 → A3 → A4 → A5 → A6 → A7) is what I recommend; if Sam can run in parallel, B0 should land before any of B1–B4 because cache-correctness is gating.

## Codex's review distilled (so we share a target)

- **Gemma Track B**: paired drift is zero across 8/16/32f, but `pass_format=False` because *both* arms inherit dense parse failures. The headline must say "matched parse failures, zero paired drift" not "clean Gemma".
- **Gemma 8f ceiling gate** misses by +0.062×. The paper should not claim ceiling-explained at 8f Gemma; it should claim it at 16f and 32f Gemma.
- **Qwen 16f kr=0.85 is fidelity-safe but low-gain**: vision_reduction 13.6% < the 25% gate. Either a kr=0.78–0.82 point passes both fidelity *and* vision-reduction, or this is a confirmed low-gain envelope.
- **1.55K is one seed × seven clips**: "robust across this practical temperature sweep" not "sampler-invariant in general."
- **1.30AF is post-hoc attribution, not causal proof.** The same equal aggregate could come from cache-distance saturation, content saturation, or a coincidental equal effect of two different mechanisms. **1.30AG** is the right causal follow-up.
- **1.65 has signal (margin gap stable 2.42 vs drift 1.12), AUC 0.71, but margin alone is insufficient**. Add features.
- **1.66 wording**: 12 GB MLX cap kept us out of kernel-panic territory; observed peak was 13.6 GB; do not conflate the two.
- The biggest remaining reviewer attack on C-PERSIST is "only two follow-ups." **Many-turn** is the priority defense.

## Track A — Local (M3 Air 16 GB)

### A1. Gemma format diagnostic + paper-text reframe

**Question.** Are Gemma Track B parse failures parser-strictness, prompt-template, or model-capacity?

**Hypothesis.** Model capacity. Sub-agent inspection shows: 100% overlap of failing items between dense and sparse arms (8f: 11/11, 16f: 3/3, 32f: 4/4); failure texts are apologies ("I am sorry, I cannot…"), prose answers ("The score is 3-1"), and thinking-tag leaks (`<|channel|>thought`); none contain A/B/C/D anywhere.

**Protocol.** Analysis-only. No new MLX runs. Read the existing `paired_items_<N>f.jsonl`, count parse failures by item, dump failure texts, run them through a permissive parser (`extract_choice_permissive` candidate that accepts `\bA\b`-style word-boundary letters anywhere in the response). Report: how many of the parse failures would a permissive parser recover? Predict: ≤10%, because the texts genuinely don't contain choice letters.

**Expected outcome.**
- Positive (parser recovers ≥30% of failures): we add a permissive-extraction post-processor to the Gemma analyzer and the headline becomes cleaner.
- Negative (parser recovers ≤10%): paper text becomes "matched dense-and-sparse parse failures reflect Gemma 4-E4B-4bit's instruction-following limits at these budgets, not C-VISION pruning effects; the paired drift comparison remains zero across n=60 items at 8f, 16f, and 32f."

**Time.** 30 min (no MLX). **Status.** Implementation = a small Python analysis script.

**Paper impact.** Cleans the C-VISION headline. Removes ambiguity about whether 0/60 paired drift is "real" or hides format-failure laundering.

### A2. 1.65v2 — Richer logit-margin predictor (analysis-only)

**Question.** Does combining margin with question-position, source policy, and 4-way logprob entropy push the predictor past the safe-filter precision gate?

**Hypothesis.** Yes — partial. Margin alone has AUC 0.7125 (lower CI 0.554), and the mean-margin gap stable=2.42 / drift=1.12 (2.16×) is genuine signal. Adding entropy from `candidate_logprobs` (already in scored_rows.jsonl), `q_index` (q1/q2 categorical), and `source` (1.30AC/1.30AD categorical) should lift AUC into 0.78–0.85. Whether that crosses the safe-filter precision threshold of 0.85 at 30% recall depends on the calibration of the new score; we should report what we get and let the gate verdict fall out honestly.

**Protocol.** Pure NumPy on the already-committed `scored_rows.jsonl` (n=228, 114 each from 1.30AC/AD, balanced classes). Train two logistic regressions with grouped train/test by item_id, bootstrap CIs by item, Brier + calibration bins, and train-derived safe-filter thresholds:

- `label_free`: top-second spread, 4-way entropy, q_index, source, duration, prompt tokens.
- `oracle`: label-free features plus answer-aware dense features (`dense_answer_margin`, `answer_letter_logprob`, `baseline_correct`).

The label-free variant is the only one that can support guard-like language,
but only if its features are empirically independent of the dense answer margin.
On the current 1.65 artifact, `top_second_gap` equals `dense_answer_margin`
because rows with dense-logit/discrete-choice disagreement are filtered out
upstream; treat that variant as a negative scout, not deployed-guard evidence,
unless 1.65 is rerun with `--allow-logit-choice-mismatch` or `top_second_gap`
is removed.

**Expected outcome.**
- AUC ≥ 0.80 with safe-filter precision ≥ 0.85: predictor scout becomes a useful "when reuse fails" appendix. Paper "future work" promise upgraded to "limited but functional runtime guard."
- AUC < 0.80 or safe-filter precision < 0.85: paper text stays "richer dense-side features bring measurable signal but remain below the safe-runtime-guard threshold; the deployment-ready predictor is still future work."

**Time.** 30 min (no MLX). **Status.** Pure analysis on existing data.

**Paper impact.** Converts 1.65 from blunt negative to graduated negative-with-signal. Reviewer-defense for "you must have measured this."

### A3. 1.62D — Low-FPS dense baseline

**Question.** Is dense Qwen 4f or 2f competitive with the dense 8f reference on the same VideoMME combined manifest?

**Hypothesis.** Mostly no. The expected ordering is: 8f (0.617 measured) > 4f > 2f, with 4f probably 5–10 percentage points below 8f and 2f another 5–10 below that. If 4f is within 5pp of 8f, the "why not just fewer frames?" reviewer attack has weight; otherwise, low-FPS dense is rejected as a replacement.

**Protocol.** Already preregistered in the reviewer-defense queue. Run `bash scripts/run_phase1_62D_lowfps_dense_videomme.sh`. Two cells: dense Qwen 4f and dense Qwen 2f on the same 57-session / 171-query 1.30W union used by the preregistered 8f reference. This is not the 1.63E n=60 Track-B manifest; if we need a separate n=60 C-VISION comparator, register that separately.

**Expected outcome.**
- 4f Δacc ≥ -0.05: low-FPS dense is a serious comparable; paper needs explicit caveat about why we choose 8f as the reference.
- 4f Δacc ≤ -0.10: low-FPS dense is rejected as a replacement; paper can defend the 8f / 16f tested envelope as not being arbitrarily large.
- 2f result for completeness; predicted to be uniformly worse.

**Time.** ~1.5h (4f arm) + ~45min (2f arm) + analysis = ~3.5h.

**Status.** Script exists at `scripts/run_phase1_62D_lowfps_dense_videomme.sh`. **Verify** the manifest path matches the dense_8f reference before running.

**Paper impact.** Closes the explicitly-listed gap on line 123–124 of `08_real_applications.tex`.

### A4. 1.63I — Qwen 16f kr fine-bracket

**Question.** Is there a kr in (0.75, 0.85) that satisfies *both* the fidelity gate (Δacc ≥ -0.05) and the sparse-vision gate (vision_reduction ≥ 25%)?

**Hypothesis.** Probably yes, around kr=0.78–0.80. The 1.63H sweep showed Δacc -0.10 at kr=0.75 and -0.05 at kr=0.85 with 27% and 13.6% vision reduction respectively. Linearly interpolating, kr=0.78 should give Δacc ≈ -0.07 with vision_reduction ≈ 22%, and kr=0.80 should give Δacc ≈ -0.06 with vision_reduction ≈ 21%. Neither obviously crosses both thresholds, but the actual measurement is the point. If a real kr in [0.78, 0.82] passes both, Qwen Track B becomes a "real" C-VISION gate-pass at 16f. If not, the low-gain envelope is confirmed and the paper writes the result honestly.

**Protocol.** Three sparse cells at L=2, kr ∈ {0.78, 0.80, 0.82} on `videomme_combined_v1_n60.toml`, paired against the committed `phase1_63E_track_b_frame_scaling/dense_16f.jsonl`. Same script structure as 1.63H, with a keep-rate-specific summarizer so the aggregate JSON does not mislabel keep-rate cells as frame counts.

**Expected outcome.**
- Some kr passes both gates: Qwen Track B becomes a paper-grade gate-pass; the paper can lead with "Qwen 16f Track B is fidelity-safe at kr=0.X with X% vision reduction and X.XX× E2E."
- No kr passes both: confirm low-gain envelope; paper text stays "the safe Qwen 16f operating point trades vision-reduction for fidelity; the configuration envelope is real."

**Time.** 3 cells × ~3h each = ~9h. **Status.** Scripted at `scripts/run_phase1_63I_16f_kr_fine_bracket.sh`.

**Paper impact.** Either upgrades or empirically locks the Qwen 16f Track B configuration envelope.

### A5. 1.30AG — K/V-cache distance probe (causal mechanism for 1.30 boundary)

**Question.** Do 1.30AC (cache-invalidated, V-pruned) and 1.30AD (cache-reuse) reach the same aggregate accuracy because both move the follow-up cache state a comparable distance from the dense reference?

**Hypothesis.** Saturation. Different perturbations, similar distance from dense, same aggregate landing point. The 1.30AF attribution showed concentration on different slices (top reuse: short/q2 with drift 0.526; top invalidated: short/q1 with drift 0.579) — these are concentrated on different slices but with similar magnitude, which is exactly the pattern 1.30AG is designed to test causally.

**Protocol.** Per the existing prereg `2026-04-27-phase-1_30AG-kcache-distance-prereg.md`. Select a deterministic 20-follow-up subset stratified by drift class (shared, reuse-only, invalidated-only, stable). For each: capture the current follow-up prompt cache for dense reference, Q0-cache-reuse plus current text-tail prefill, and cache-invalidated current-query prefill with follow-up vision pruning. Compute layer-wise cosine distance to dense reference, K and V separately. Join distance summaries to row-level drift outcomes.

**Expected outcome.** Per prereg's H4: if both policies' aggregate distances within 10% AND their row drift sets non-identical → saturation supported, paper can claim cache-state distance threshold mechanism. If not → empirical boundary, no stronger mechanism claim. Either is publishable; the saturation result would be much stronger.

**Time.** ~2h estimated. **Status.** Scripted at `scripts/run_phase1_30AG_kcache_distance_probe.py`; needs smoke review because it directly introspects MLX prompt-cache objects.

**Paper impact.** Either gives the 1.30 boundary a causal mechanism (huge), or honestly closes it as empirical (acceptable).

**Risk.** I have not verified that the 1.30 runner exposes a cache-tensor capture hook. If it doesn't, 1.30AG needs a runtime-hook implementation that is bigger than the current 2h estimate. Need to check.

### A6. 1.55L — Many-turn C-PERSIST drift (10/20/50 turns)

**Question.** Does paired drift accumulate across turns, and does periodic refresh prevent that accumulation?

**Hypothesis.** Without refresh, drift accumulates linearly or super-linearly with turns; with periodic post-Q2-style refresh every 5–7 turns, drift is bounded. The current paper claim is explicitly "two follow-ups, many-turn is stress test for future work" (line 195–196 section 07). This is the single biggest claim-tightening experiment in the entire slate.

**Protocol.** `scripts/run_phase1_55L_many_turn_cpersist.py` cycles the 3 VideoMME questions per video into a 10/20/50-turn sequence: `[Q1, Q2, Q3, Q1, Q2, Q3, …]`. It applies three policies: fixed K=1, adaptive post-Q2/post-previous repaired cache, and scheduled refresh every 10 turns. The dense control uses the same stateless question cycle. This keeps the experiment inside the existing local C-PERSIST protocol and avoids a new chat-history prompt distribution.

Cells: `{10t, 20t, 50t} × {fixed_k1, adaptive_post_q2, refresh10}` plus turn-matched dense controls.

**Expected outcome.**
- Off-refresh drift ≤ 0.05/21 paired diffs at 10t, 20t, 50t: the C-PERSIST repeated-prefill mechanism is robust over 50 turns. Paper goes from "two follow-ups" to "tested through 50 turns".
- Off-refresh drift accelerates with turns; periodic-5 keeps drift ≤ 0.05/21: refresh is needed; paper makes a stronger conditional claim.
- Drift accumulates even with refresh10: a tighter refresh interval is needed; paper reports the boundary of repair.

**Time.** 10t × 7 clips ≈ 1.5h, 20t × 7 ≈ 3h, 50t × 7 ≈ 7h. With adaptive + dense control + 2 refresh policies that's `12 cells × {1.5h, 3h, 7h scaled by horizon}` ≈ ~12h sequential, ~8h with reuse of the cold dense baseline across cells.

**Status.** Scripted. It is a stateless repeated-query horizon; a true conversational-history benchmark remains a separate Sam-scale/deployment experiment.

**Findings-doc requirement.** When 1.55L lands, describe it as a **stateless
same-video cache-horizon stress test**, not a many-turn conversation. The prompt
text is reset to the current question each turn; only the cache state is carried
forward.

**Paper impact.** Single biggest tightening: converts "many-turn is future work" to "tested through 50 turns with measured refresh interval".

### A7. 1.55K-extended — Multi-seed sampler robustness

**Question.** Is the 1.55K sampler-stable result robust across seeds (not just one) on the original short tranche?

**Hypothesis.** The aggregate Δacc 0/0/-0.048/-0.048/0 across T={0,0.5,0.7,1.0,1.5} should be reproducible across 3 different sampling seeds with overlap. This does not broaden the clip set; it specifically tests whether the existing short-tranche sampler result was seed-fragile.

**Protocol.** `run_kv_selective_reprefill_v2.py` and `run_kv_cache_session.py` now accept `--seed` and pass it into both standard and explicit-tail generation paths. Run 3 seeds × 3 temperatures (`0.5, 1.0, 1.5`) on the short tranche. Aggregate-level analysis: do the cross-seed CIs include zero? Per-seed Δacc dispersion.

**Expected outcome.**
- Cross-seed Δacc ranges all within ±0.05: paper claim upgrades from "robust across this temperature sweep" to "stochastic-stable across seeds and temperatures."
- Cross-seed dispersion > 0.10: the single-seed result was lucky; paper text becomes "robust median across temperatures and seeds, with X% per-cell variance."

**Time.** 3 seeds × the 1.55K runtime (~5h) = ~15h, but we can prune: just T=0.0, 0.5, 1.0 across 3 seeds × short tranche = 9 cells × ~50 min each = ~7.5h. Pick this tighter scope.

**Status.** Seed plumbing and extended sweep script implemented; run a 1-clip smoke before the full sweep if launch time allows.

**Paper impact.** Lifts 1.55K from "single-seed T-sweep" to "short-tranche stochastic-stable" claim. It does not answer cross-bucket sampler robustness.

## Track B — Sam (M5 MBP, 128 GB, 26B runtime)

These are best-effort spec sheets for Sam; we won't run them locally. Codex's bundle (C0–C5) is the canonical list; I'm refining the schema and prerequisites.

### B0. 26B cache-correctness smoke

**Question.** Does Sam's 26B runtime preserve answer identity across cross-turn warm follow-ups?

**Why.** Sam's last cache-correctness smoke failed on 3/5 cross-turn follow-up items (per paper line 72–74). Until this passes, *no* C-PERSIST claim from 26B is admissible.

**Protocol.** 5 short videos × 3 questions each. Three arms per video:
1. Dense deterministic replay (Q1, Q2, Q3 from cold cache)
2. Within-turn cache replay (Q1 → cache → Q1' produces same output)
3. Cross-turn warm follow-up (Q1 → cache → Q2 produces same output as cold-Q2-on-same-cache-state)

Schema per row: `item_id, q_index, arm, model_id="26B", runtime_commit, frame_count, choice, correct, raw_output, parse_failure, elapsed_ms`.

**Gate.** All 15 cross-turn warm rows must match cold rows. Anything less = 26B C-PERSIST remains blocked.

**Time.** ~1.5h. **Status.** Sam-only, blocking gate.

### B1. 26B C-PERSIST replication (conditional on B0 PASS)

**Question.** Do 26B cache reuse and adaptive repair reproduce the 7B result envelope (15.28–35.97× speedup, 0/93 paired drift)?

**Protocol.** Match local protocol. Cold dense baseline + fixed K=1 reprefill (or nearest 26B equivalent) + adaptive post_q2 if supported. Same VideoMME short/medium/long manifest, paired against the local 1.55F-tranche videos when possible. Report: paired choice/correctness diffs, parse failures, pathological hits, stage timings, peak memory, cache prefix coverage.

**Schema per row** (mirror local JSONL): `item_id, q_index, arm, model_id, runtime_commit, hardware, frame_count, policy, prompt_hash, choice, correct, raw_output, parse_failure, pathological, elapsed_ms, decode_ms, vision_ms, generate_ms, end_to_end_ms, peak_memory_gb, cache_hit, prefix_coverage, prompt_tokens, generation_tokens`.

**Time.** ~8h.

### B2. 26B many-turn streaming horizon (the headline scale-out)

**Question.** Does same-video cache reuse stay stable through 10/20/50 turns at 26B?

**Protocol.** Same as A6, but at 26B and ideally with Sam's actual streaming protocol (continuous turn history rather than synthesized cycle). Three horizons: 10, 20, 50 turns, with two refresh policies.

**Time.** ~10h. **This is the headline experiment.**

### B3. Matched streaming baselines (C-STREAM bundle)

**Question.** What does same-video reuse measure against compared to: screenshot polling, low-FPS dense, recency/last-K, and Sam's adaptive repair?

**Protocol.** Same videos, events, and questions across all four protocols. Include one stale-cache failure case (a question whose answer changed between turns 1 and 5).

**Time.** ~8h. **Promotes C-STREAM from "partner evidence" to "same-graph science"** per Codex.

### B4. 26B sparse-ViT / C-CEILING

**Question.** Does sparse vision-tower execution skip real wall-clock work at 26B, and does the C-CEILING arithmetic predict it?

**Protocol.** If 26B runtime supports a real sparse-ViT path (gather/scatter compact execution), run dense vs sparse paired at 8/16/32f or nearest native. Report: paired choice, parse failures, dense vs sparse vision_ms, predicted ceiling, actual speedup, ceiling gap.

**Risk.** Conditional on whether the 26B runtime exposes the sparse path. If it doesn't, this experiment is blocked.

**Time.** ~8h.

### B5. 1,937 re-export with full schema

**Question.** Is the 1,937 exactness claim from the original Sam protocol still reproducible with full per-row provenance?

**Protocol.** Re-export the data Sam used for the 1,937 number with: item IDs, raw paired outputs, parse_failure, CIs, model/runtime/hardware metadata, exact commit, prompt_hash, frame_count, policy. This is a documentation+tooling task, not a new experiment.

**Time.** ~1.5h.

## Things I'm unsure about / need extra scrutiny

1. **A5 (1.30AG) cache-tensor capture hook.** Implemented through direct `make_prompt_cache` objects and K/V tensor introspection, not through the 1.30 runner. It still needs a one-row MLX smoke because cache-entry internals are runtime-object dependent.
2. **A6 (1.55L) controls.** The implemented local control is the same stateless question cycle in both arms, not true conversational text history. This is scientifically valid as a C-PERSIST protocol horizon, but the paper must not call it a conversational-history result.
3. **A6 (1.55L) refresh-policy interpretation.** The first implemented policy is `refresh10`. Adaptive refresh ("refresh when drift detected") would be more interesting but requires online drift detection that we have not built; keep it future work.
4. **A7 (1.55K-extended) seed plumbing.** Seed arguments are now threaded through the standard and explicit-tail paths. A 1-clip T=1.0 smoke should still verify that different seeds produce different stochastic outputs before the full sweep.
5. **A4 (1.63I) negative-result framing.** If no kr in [0.78, 0.82] passes both gates, the paper conclusion is "low-gain envelope confirmed." That's a fine outcome but worth pre-committing to before running, so we don't post-hoc rationalize a near-miss.
6. **B-track schema mirror.** Implemented at `research/schemas/sam_scaleout_artifact_v1.schema.json`, with protocol details in `2026-04-29-sam-scaleout-handoff.md`.
7. **Memory cap on Sam.** The 12 GB MLX cap was a workaround for the 16 GB unified-memory laptop's GPU race. On Sam's 128 GB box this is irrelevant; do *not* port the cap into B-track scripts.

## Recommended execution order

**Phase 2a (this session, ~5h compute):**
1. **A1 Gemma format diagnostic** (30 min) → paper text correction
2. **A2 1.65v2 richer predictor** (30 min) → predictor scout upgrade
3. **A3 1.62D low-FPS dense** (3.5h) → fills a specifically-listed paper gap

**Phase 2b (overnight, ~14h compute):**
4. **A6 1.55L many-turn drift** (3h impl + 8h run = 11h) → biggest reviewer defense
5. **A5 1.30AG K-cache distance** (30min spike + 2h run = 2.5h, conditional) → causal mechanism

**Phase 2c (subsequent session, ~17h compute):**
6. **A4 1.63I Qwen kr fine-bracket** (9h) → Qwen Track B gate-pass attempt
7. **A7 1.55K-extended seeds** (1h impl + 7.5h run = 8.5h) → universal sampler

**Sam track (in parallel):**
- **B0 cache-correctness smoke** as soon as Sam can — gating gate
- **B1, B2, B3, B4, B5** in any order after B0 passes, prioritized by Codex's review (B2 is the headline)

## Each experiment will get a wrapper script

Following the established pattern (`scripts/run_paper_deep_mechanism_restart.sh`, `scripts/run_phase1_63H_16f_kr_sweep.sh`), every experiment in this slate gets:
1. A standalone bash script under `scripts/run_phase<ID>_*.sh` that is idempotent and resume-safe.
2. A Python analyzer that consumes its JSONLs and writes a `<phase>_summary.json` with `pass_*` gate keys.
3. A findings markdown doc once the cell lands.

The wrapper script `scripts/run_phase2_local_chain.py` chains A1–A7 in order, with `--start-at <phase>` resume support and auto-commit of artifact directories. Same pattern as the deep-mechanism queue.

## Open questions for the user

1. Run all of Track A in one chain, or want me to gate at A3 / A6 boundaries for human review?
2. Should A6 (many-turn) include a "no refresh + dense control" 50-turn cell, or skip the unsafe scenario?
3. A7 (1.55K-extended) is optional for arXiv v1 — keep it in scope, or save for v2?
4. For B-track: do you want me to draft the Sam handoff document (schema + protocol + acceptance criteria) now, or wait until A-track completes?

## What this slate does NOT include

- New benchmarks / new manifests beyond what already exists (`videomme_combined_v1_n60`, short tranche)
- Cross-arch C-VISION on benchmarks other than VideoMME (TOMATO/MVBench imports stay deferred)
- A 1.62D 1f or 0.5f cell (the prereg covers 4f and 2f only; below 2f is a separate decision)
- Gemma kr-sweep at 16f (Gemma is robust at kr=0.50 across all frame budgets; kr-sweep is informative but not paper-defining)
- 1.55B v2 selective re-prefill on the broader benchmarks (still pending, not part of this slate)

## Bottom line for the editor

If we land A1–A6 and Sam lands B0–B2, the paper has all five contributions (C-PERSIST, C-CEILING, C-VISION, C-STREAM, plus 1.30 attribution) backed by gate-grade evidence at the configuration boundaries. If A4 finds a real Qwen kr gate-pass, we can lead C-VISION with two architectures showing zero-drift sparse vision execution. If A6 stays drift-bounded through 50 turns, the C-PERSIST headline goes from "two follow-ups" to "tested at scale". Both are paper-defining.
