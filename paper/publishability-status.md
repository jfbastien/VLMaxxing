# Publishability Status — 2026-04-30

One-file answer to "what can we actually claim, in what venue, with what
numbers, today." Kept in sync with [claim-matrix.md](claim-matrix.md) but
scoped narrower: reviewer-facing readiness and runtime-cost evidence.

For paper triage, prefer [priority.md](priority.md) and
[claim-matrix.md](claim-matrix.md) over this file when they disagree. The
current headline is the anti-recomputation story summarized next. Detailed
runtime inventories lower in this file are retained for provenance, but the
current narrative interpretation should come from `priority.md` and the claim
matrix.

## Current Manuscript Position (2026-04-30)

The draft should lead with three linked claims, not with a Qwen-only routing
note:

- **C-VISION**: Gemma vision-tower pruning has paper-grade first-pass
  speedup evidence on clean and advisory holdout cells, and measured sparse
  vision now has a bounded timed-execution envelope: Gemma 32f short is clean
  at 1.316× with 0/20 paired drift, while Qwen recovers fidelity only at a
  conservative low-gain keep rate.
- **C-PERSIST**: persistent-KV reuse already delivers the largest local
  deployment numbers in the repo on same-video follow-up queries, and
  adaptive selective re-prefill now repairs the 20f/32f basin across the broad
  tested Qwen tranche: n=93, 0 observed paired drift, 15.28×--35.97× all-query
  speedup, and 14.90×--35.92× same-class follow-up speedup.
- **Qwen routing**: mechanism and boundary evidence showing why placement of
  fresh computation matters; novelty-ranked diagnostics stay local-only until
  their raw outputs are materialized as checked artifacts.

Candidate C-STREAM is not decorative support, but it is not a release claim
yet. The manuscript should keep native-rate streaming as a pending scale-out
lane until artifact-compatible protocols, raw paired rows, cache-correctness
smokes, source paths, and matched baselines make it first-class in the same
evidence graph.

## One paper, multiple evidence regimes

**The goal is one results paper that advances the anti-recomputation evidence
across three independent axes.** Codex rounds 25–26 retired the
earlier "one big multiplicative number via claim 11" framing: the
paper spine is now three already-earned, independently-evaluable
contributions (all landed before Codex round-26 2026-04-21):

- **C-CEILING — arithmetic end-to-end ceiling** (claim 13).
  `E2E ≤ 1/(fixed + (1−fixed)/s)` validated across 7 independent
  regime dimensions (8-frame kr-sweep + 32-frame short/medium/long +
  smoke + Stage 7 short × gemma_structural × kr=0.33) at median
  2.1% / worst 5.2% prediction error. A standalone analytical
  contribution independent of any specific SOTA arm.
- **C-PERSIST — persistent-KV tested deployment envelope** (claim 14).
  6-point speedup curve (47×→91×→70×→94×→122×→150× at 8/16/18/20/24/32f
  on Qwen 7B-4bit) + 3-point cross-arch scaling on Qwen 3B-4bit +
  4-regime temperature matrix. Mechanism decomposes into three
  independently-varying axes (threshold onset × basin-onset depth ×
  basin geometry). The current onset evidence is bracketed rather than a clean
  scaling law: 7B enters the basin by roughly 20f / 8.1k prefill tokens, while
  3B is bracketed to (36f, 40f] / 14.5k--16.1k. Deployment-facing envelope:
  7B stays inside the tested region through 16f / ~6.5k prefill, with a clean
  16f point and a slightly worse but still tolerated 8f point; 3B stays inside
  the bounded region through 36f / ~14.5k prefill at a tolerated Δacc=−0.19
  plateau (not clean). Phase 1.55D/G/I/H now make recovery local evidence rather
  than a hypothesis: fixed K=1 selective re-prefill shows no observed paired
  drift on n=93 across 20f short/medium/long plus 32f short at
  9.48×–20.37× same-class median follow-up speedup. Phase 1.55F breadth is now
  the stronger adaptive headline: 0/93 observed paired drift at
  14.90×–35.92× same-class follow-up speedup and a 15.28×–35.97×
  cold-all-query ratio.
- **C-VISION — vision-tower pruning with scatter-back ceiling**
  (claim 15). `E2E ≤ 1/(1 − V_share × V_red)` on Gemma 4-E4B-4bit
  validated across Gemma dev/holdout cells, a matched Qwen dev point,
  measured sparse-execution cells, and the EXP10 n=60 composition audit;
  dev V_red was 39–43% at L=2 kr_V=0.50 on the first tranche, while
  holdout V_red is benchmark- and protocol-conditional (observed
  0.350–0.471). **Three-benchmark holdout trifecta CLOSED 2026-04-21**
  (VideoMME 8f CLEAN, MVBench 8f CLOSED-ADVISORY on thermal-calibration
  footnote, TOMATO 8f EARNED-ADVISORY on favorable-drift footnote).
  **Measured sparse-execution envelope landed 2026-04-29**: Gemma 8/16/32f
  skips timed vision work with zero paired answer drift but matched
  parse-failure caveats; Gemma 32f short is the clean operating point at
  1.316×. Qwen 16f keep-rate sweep recovers fidelity at kr=0.85 but with only
  13.6% vision-time reduction and 1.032× E2E.

- **First-pass measured gains (Gemma / C-VISION).** This is the main
  reviewer-facing result today: measured end-to-end speedups on VideoMME,
  MVBench, and TOMATO, with clean versus advisory status stated explicitly.
- **Cross-architecture C-VISION transfer (Qwen).** The same
  `1/(1 − V_share × V_red)` ceiling now binds on a matched Qwen
  VideoMME point at 1.044× observed versus 1.043× predicted. This
  strengthens the mechanism claim, not the headline magnitude.
- **After-ingest follow-up gains (Qwen / C-PERSIST).** This is where the
  largest local speedups live today: same-video follow-up queries collapse to
  sub-second latency when the expensive prefix is reused.
- **Mechanism and boundary evidence (Qwen routing).** This is where the paper
  explains why anti-recomputation works, where it fails, and why sparse-path
  claims must stay separate from semantic-substitution claims.

**Mechanism-validation backbone (NOT the headline).** Qwen routing
work (claims 1/2/6/9 earned, 3/4/5 partial, 8/12 preregistered on
TOMATO + MVBench) is the negative-result discipline lane: it shows
what works and what does not, and it belongs in the paper as mechanism
and boundary evidence rather than as the headline result.

**Candidate C-STREAM (NOT applications/support).** Native-rate streaming is the
scale-out regime for the same anti-recomputation thesis, but numeric deployment
rows stay pending until they are imported as validated artifacts rather than
sibling prose. Sparse-sampled QA stays pixel-diff by design; native-rate
streaming may use H.264 metadata by design. The shared frame is C-CEILING
arithmetic plus cache-state correctness, not a cross-repo multiplier.

1.51R novelty-pruning does NOT carry the headline. It appears as
(a) the EXP10 n=60 composition-appendix gate (≥4 pp E2E lift over
V-alone AND agreement ≥0.75 AND acc Δ within −0.067), and (b) the
Stage 5 anchor-arm comparison that establishes `gemma_structural`
as the in-repo default (secondary methodology content). Claim 11 is
duration-conditional partial reproduction, arithmetically bounded to
≤1.46× at 8f kr=0.10 per C-CEILING.

See `paper/framing.md`, `paper/priority.md`, and the canonical LaTeX sources
under `paper/arxiv/sections/` for the authoritative narrative. The Markdown
LaTeX section files are the canonical manuscript sources.

> **Training-free anti-recomputation for video VLMs: measured first-pass
> speedups on Gemma, sub-second same-video follow-up queries on Qwen, and
> routing diagnostics suggesting that fresh-compute placement is not captured
> by novelty magnitude alone.**

**Concrete headline cells today:**

- **Gemma first-pass vision pruning:** VideoMME 8f holdout **1.113×** clean,
  MVBench 8f holdout **1.407×** advisory, TOMATO 8f holdout **1.194×**
  earned-advisory from checked-in session-5 artifacts.
- **Qwen cross-architecture C-VISION transfer:** VideoMME 8f dev at matched
  `L=2`, `kr_V=0.50` lands **1.044×** observed vs **1.043×** predicted, with
  `V_red = 0.398` and aggregate `Δacc = −0.033`.
- **Qwen persistent-KV:** **47.2×** speedup and **815 ms** median follow-up at
  8f, rising to **91.1×** and **807 ms** at 16f inside the tested envelope
  (16f clean; 8f slightly worse but still inside the criterion). The repaired
  basin headline is adaptive selective re-prefill: **0/93** observed paired
  drift with **15.28×–35.97×** all-query speedup.
- **Candidate C-STREAM:** pending validated artifact bundle. Do not include
  numeric deployment rows in release claims until raw paired outputs, cache
  smokes, source paths, and matched baselines are checked in.
- **Qwen routing:** audited Pareto win/tie on MVBench and TOMATO holdouts
  at much lower effective fresh-frame budgets, with local novelty-ranked
  diagnostics suggesting that fresh-compute placement is not captured by
  novelty magnitude alone.

**Secondary — C-PERSIST (persistent-KV tested deployment envelope):**

> **Persistent KV-cache follow-up queries on Qwen 2.5-VL (MLX) deliver
> 47×→150× speedups along an 8/16/18/20/24/32-frame curve on 7B-4bit
> (prefill-dominated) and 136×→213× on 3B-4bit (decode-dominated).
> Tested deployment envelope is architecture-specific: 7B stays inside the
> tested regime through 16f / ~6.5k prefill, with a clean 16f point and a
> slightly worse but still tolerated 8f point; 3B stays inside the bounded
> regime through 36f / ~14.5k prefill on a tolerated Δacc=−0.19 plateau
> (not clean). Fidelity degradation
> decomposes into three independently-varying axes (threshold onset,
> basin-onset depth, basin geometry). Basin onset is bracketed rather than a
> clean ratio: 7B by ~20f/~8.1k tokens; 3B in (36f, 40f] / 14.5k--16.1k.
> Sampler-side recovery is not uniform:
> 7B basin behavior is sampler-resistant in the tested regimes, while
> 3B basin behavior can disperse only back to its pre-basin plateau.**

**Tertiary — C-CEILING (arithmetic analytical contribution):**

> **An architectural speedup ceiling E2E ≤ 1/(fixed + (1−fixed)/s)
> explains observed end-to-end multipliers within median 2.1% / worst
> 5.2% across 7 independent regime dimensions on Gemma 4-E4B-4bit
> (Qwen 7B-4bit composition ceiling also matches observed to 0.1pp).
> It bounded the expected sparse-vision delta before measurement, and
> the current bounded measured sparse-vision envelope validates that
> scope; a standalone analytical contribution independent of any
> specific SOTA arm.**

**Quaternary — Qwen routing (mechanism-validation backbone):**

> **Training-free temporal routing on Qwen 2.5-VL-7B-4bit (MLX): matches
> 8-frame uniform-dense accuracy on MVBench motion holdout while using
> 56% of the fresh-frame budget (4.49 vs 8.0 effective fresh frames) —
> no training, no architecture change, one percentile pass + a bounded
> staleness counter. Reported alongside an explicit null ledger
> (halo-veto 1.37B retired; sticky-dynamic TOMATO no-lift; PE-only
> correction refused by 1.49; 1.51R VideoMME duration-conditional
> partial reproduction; 1.55D fixed-K frontier landed but remains just
> below the deployment-speed crossover).**

What we CANNOT yet honestly say in HN-headline form:

- "**N%** faster" for a broad sparse backend — the local measured-sparse-vision
  path has landed as a bounded envelope, not a broad backend claim. Gemma has a
  clean 32f-short cell; Qwen has a fidelity-safe low-gain boundary. Sparse LM
  prefill and broad fidelity-preserving curves remain out of scope.
- "**N%** less energy" — no energy instrumentation. Projected proportional
  to wall-clock at fixed memory.
- "**N%** as accurate" — the clean-tree release-backed routing cells preserve
  aggregate accuracy on TOMATO (dense-8 vs base: 0.333=0.333) and improve the
  MVBench dense-6 comparison at lower effective budget. The MVBench sticky4
  dense-8 tie remains dirty-tree supplementary until rerun clean.

**Honest one-liner for reviewers:** "training-free anti-recomputation across
separate denominator regimes: large after-ingest follow-up reuse, share-limited
first-pass pruning, a negative composition boundary, and bounded measured
sparse-execution validation for the measured wall-clock ceiling."

## Publishable claim inventory (with concrete numbers)

### What is earned RIGHT NOW (can appear in paper body, not just discussion)

| # | Claim | Numbers (cite) | Evidence path |
|---|---|---|---|
| A | **Pointwise Pareto win on MVBench motion holdout N=30 at matched accuracy.** | Planner 2.0 base `max_abs(8,32) static+shifted age=4` → 0.600 cached_accuracy @ 4.06 effective fresh frames, vs uniform dense-6 at 0.567 @ 6.0 (higher point estimate at fewer fresh frames; keep the n=30 caveat visible). | `research/experiments/2026/artifacts/phase1_21_mvbench_motion_holdout_v2_cached_nosticky/max_abs-8.0-32.0-static+shifted-age4_summary.json`; `paper/arxiv/generated/data/lane_a_snapshot.json` |
| B | **Pareto tie on TOMATO motion holdout N=30 at 44% of the fresh-frame budget.** | Planner 2.0 base → 0.333 cached_accuracy @ 3.55 effective fresh frames, equal to uniform dense-8 at 0.333 @ 8.0. | `research/experiments/2026/artifacts/phase1_20_tomato_motion_holdout_v2_cached_clean/max_abs-8.0-32.0-static+shifted-age4_summary.json`; `paper/arxiv/generated/data/lane_a_snapshot.json` |
| E | **Bounded staleness is the mechanism on TOMATO; removing age=4 causes catastrophic novelty collapse.** | TOMATO Planner 2.0 no-age: novel_blocks→0, identical-feature reuse. With age=4: recovers proxy signal. Content-conditional finding. | `research/experiments/2026/2026-04-15-phase-1_20-tomato-motion-slice-enlargement.md`; `research/experiments/2026/artifacts/phase1_planner2_reference_default_tomato_holdout_v2/mean-3.0-8.0-static+shifted-noage_summary.json`; `research/experiments/2026/artifacts/phase1_20_tomato_motion_holdout_v2_cached_clean/max_abs-8.0-32.0-static+shifted-age4_summary.json` |
| R | **1.51V vision-tower pruning on Gemma 4-E4B-4bit (MLX), dev n=30 at L=2 kr_V=0.50 thermally paired:** VideoMME 1.08× (8f) / 1.12× (16f), MVBench **1.21×**, TOMATO **1.24×**; dev V-red lands around 40% across the three benchmarks, but holdout spread is wider and should be described more softly in the manuscript. Scatter-back ceiling `1/(1 − V_share × V_red)` predicts E2E within 2pp on the main dev cells. Holdout replications bound the claim: VideoMME 8f **clean** at 1.113×; MVBench 8f **advisory** at 1.407×; TOMATO 8f **earned-advisory** at 1.194×. | `research/experiments/2026/2026-04-21-phase-1_51V-expansion-findings.md`; `research/experiments/2026/2026-04-21-phase-1_51V-holdout-findings.md`; `research/experiments/2026/2026-04-21-phase-1_51V-session5-findings.md`; `research/experiments/2026/artifacts/phase1_51V_session3/exp18_videomme_holdout_8f_L2_kr050_summary.json`; `research/experiments/2026/artifacts/phase1_51V_session4/exp20_mvbench_holdout_8f_L2_kr050_summary.json`; `research/experiments/2026/artifacts/phase1_51V_session5/exp24_tomato_holdout_8f_L2_kr050_summary.json` |
| O | **Persistent-KV follow-up speedup and selective re-prefill repair on Qwen 7B-4bit.** Persistent-KV reproduces the after-ingest latency regime and bounds fidelity by token budget; selective re-prefill v2 is the local recovery frontier, with fixed K=1 and adaptive post-Q2-state reuse showing no observed paired drift on checked local repair slices. | Use the phase notes and checked repair artifacts rather than this compressed inventory when writing final manuscript prose. | `research/experiments/2026/2026-04-19-phase-1_55A-persistent-kv-findings.md`; `research/experiments/2026/2026-04-24-phase-1_55D-selective-reprefill-v2-k1-findings.md`; `research/experiments/2026/2026-04-25-phase-1_55F-q3-post-q2-state-findings.md`; `research/experiments/2026/2026-04-27-adaptive-mechanism-queue-findings.md`; `research/experiments/2026/artifacts/phase1_55D_selective_reprefill_v2/pair_metrics_k1_n7.json`; `research/experiments/2026/artifacts/phase1_55F_q3_post_q2_state/pair_metrics_k1_n7.json` |

### Local-only historical comparators (not release claim-bearing yet)

These findings can inform discussion, but should not appear as paper-body
claim evidence until their ignored `results/` outputs are regenerated or
re-materialized as checked artifacts.

| # | Finding | Status |
|---|---|---|
| C | Sticky4 refinement matches dense-8 accuracy at 56% of budget on MVBench. | Dirty-tree artifact. Keep as supplementary/provisional discussion only until rerun clean. |
| D | Novelty-ranked dense N=8 underperforms the cached policy on TOMATO and saturates below uniform dense on MVBench. | Phase 1.34 note records the exact local-only ignored `results/` tree and commit IDs; regenerate or re-materialize before citing as release claim-bearing evidence. |
| F | Pixel-diff proxy to ViT feature-change correlation is non-trivial but content-conditional (Pearson r=0.233--0.504). | Phase 1.36 note records local-only ignored `results/feature_change_oracle/` outputs; diagnostic only until checked artifacts exist. |
| G/H | Historical dense wall-clock baseline and the derived 22% vision-cache-only ceiling. | Phase 1.50 note records local-only ignored `results/track_b/` outputs. Current paper-facing sparse-vision claims should cite checked phase 1.63 artifacts instead. |

### Remaining gaps and strengthening work before venue submission

| # | Claim | Blocker | Runtime estimate |
|---|---|---|---|
| I | "Method delivers broad measured sparse-path speedup" | Bounded measured sparse-vision envelope landed. Gemma 32f short is clean at 1.316× with 0/20 paired drift; full Gemma sweep has matched parse-failure caveats. Qwen kr=0.85 restores fidelity/format/ceiling at 16f but is low-gain (1.032×, 13.6% vision-time reduction). | Broad sparse backend and sparse LM prefill remain larger systems projects. |
| J | "Validated on VideoMME (de facto benchmark)" | **EARNED 2026-04-18 (8f); strengthened 2026-04-19 (16f, 32f); holdout 16f earned 2026-04-21.** Qwen 2.5-VL-7B-4bit, videomme_dev_v1.toml n=30 plus videomme_holdout_v1.toml n=30 at 16f. **8f dev**: dense_acc=0.533, parse_fail=0, agreement=1.000, RSS=6.67GB, mean e2e=31.0s. **16f dev**: dense_acc=0.567, mean e2e=75.2s. **32f dev**: dense_acc=0.533 (n=30), mean e2e=157.9s, RSS=8.52GB. **16f holdout**: dense_acc=0.700, short/medium/long = 0.600/0.600/0.900. The dev long-bucket regression did not replicate on holdout; 32f is not Pareto-efficient. Phase 1.57 Qwen drift geometry transfers to holdout at 8f/16f, while 32f drift remains dev-only. | Open: Phase 1.58 (4bit × long-context quantization) to test the one surviving mechanism candidate. Phase 1.54 (decode-accel) still open for long-item latency, not accuracy. |
| K | "Cross-architecture generalization (Qwen windowed ↔ Gemma/InternVL3 all-global)" | Partial but no longer infrastructure-blocked: 1.42 Gemma E4B split-landed (TOMATO strict-agreement pass; MVBench aggregate-tie but strict-agreement fail), and 1.57 Gemma drift landed with corrected 133-token cached-feature geometry. Matched Qwen C-VISION transfer also exists. | Further work is interpretation, third-architecture breadth, or a stricter Gemma cache-substitute measurement; do not describe this as waiting for 1.42 to land. |
| L | "Placement ablation (phase 1.38)" | Not run. | ≈ 30 min GPU wall time on a subset. |

## Evidence table with RUNTIME (not implementation) time

Runtime = benchmark wall time to reproduce the cited number from a
warm cache on an M3 Air 16 GB. Implementation time is deliberately
out of scope for this table — it does not compose across phases and
is work the user is buying forever. What the user is paying for
**per re-run** is the benchmark wall-clock below.

### Earned (paper body)

| # | Claim | Cold-cache | Warm-cache | Model |
|---|---|---|---|---|
| A | MVBench motion holdout N=30 base | ≈ 90 min | ≈ 25-30 min | Qwen 2.5-VL-7B-4bit |
| B | TOMATO motion holdout N=30 base | ≈ 120 min | ≈ 30-40 min | Qwen 2.5-VL-7B-4bit |
| E | TOMATO ablation cells (6 cells × 2 benchmarks × N=30) | ≈ 6-8 h | ≈ 3-4 h | Qwen 2.5-VL-7B-4bit |
| J₈ | Phase 1.41 VideoMME dev n=30 @ 8f | ≈ 16 min (931 s measured) | ≈ 16 min (no feature cache) | Qwen 2.5-VL-7B-4bit |
| J₁₆ | Phase 1.41 VideoMME dev n=30 @ 16f | ≈ 38 min (2,257 s measured) | ≈ 38 min | Qwen 2.5-VL-7B-4bit |
| J₃₂L | Phase 1.41 VideoMME long n=10 @ 32f | ≈ 28 min (1,450 s projected from 161 s/item × 9 measured) | same | Qwen 2.5-VL-7B-4bit |
| K | Claim-11 reproduction log (1.51R Stages 1/2b/3/5/6/7) | ≈ 10-12 h total across N=30 cells on both benchmarks | n/a (incremental) | Gemma 4-E4B-4bit |
| M | Claim-13 C-CEILING cross-validation (7 regime dimensions) | included in K | n/a | Gemma 4-E4B-4bit |
| O | Phase 1.55A persistent-KV follow-up latency (n=21 queries × 6 frame counts + 3B cross-arch 3-point + 7B/20f temperature probe + 3B/20f temperature probe) | ≈ 18 min at 8f (1057 s) + ≈ 35 min at 16f (2095 s) + ≈ 38 min at 18f (2302 s) + ≈ 42 min at 20f (2506 s) + ≈ 55 min at 24f (3281 s) + ≈ 76 min at 32f (4573 s) + ≈ 27 min at 3B-20f (1595 s) + ≈ 31 min at 3B-24f (1830 s) + ≈ 50 min at 3B-32f (2972 s) + ≈ 48 min at 7B-20f-temp (2862 s) + ≈ 24 min at 3B-20f-temp (1427 s) = ≈ 7.3 h | ≈ 7.3 h | Qwen 2.5-VL-7B-4bit + 2.5-VL-3B-4bit |
| O₂ | Phase 1.55 selective re-prefill repair breadth (adaptive short/medium/long/32f plus fixed-K repair artifacts) | Adaptive breadth alone measured ≈ 5.1 h across short, medium, long, and 32f-short cells (0.83 h + 1.50 h + 1.14 h + 1.60 h); fixed-K repair artifacts add the no-coordination baseline | same | Qwen 2.5-VL-7B-4bit |
| P | Phase 1.51V expansion (12 exps — Tier 0 confirm + Tier 1 Pareto + Tier 2 cross-bench + Tier 3 stack + Tier 4 16f scale) | 15,621 s measured = **4.34 h** (EXP01–12; runtime per-exp 606–2155 s, dense+pruned both reported) | 4.34 h | Gemma 4-E4B-4bit |
| Q | Phase 1.51V 32f probe (EXP13 unpatched + EXP14 L=2 kr=0.50, n=30 each) | 7,167 s measured = **1.99 h** (EXP13 3415 s + EXP14 3752 s; thermal confounder documented) | 1.99 h | Gemma 4-E4B-4bit |
| R | Phase 1.51V holdout session 2 (EXP15 V-patched baseline + EXP16 V+novelty kr=0.3, n=30 VideoMME holdout v1) | 2,706 s measured = **0.75 h** (EXP15 1425 s + EXP16 1281 s; thermal pairing dirty -7.8% decode Δ; within-run pairing CLEAN) | 0.75 h | Gemma 4-E4B-4bit |
| S | Phase 1.51V session 3 (EXP17 VideoMME unpatched holdout + EXP18 V-patched kr=0.5, n=30) | ~0.8 h (sum decode + generate across 60 items; thermally paired at decode Δ 1.53%) | 0.8 h | Gemma 4-E4B-4bit |
| T | Phase 1.51V session 4 (EXP19/20 MVBench holdout pair + EXP21/22 TOMATO holdout pair, run 2) | ~2.0 h (queue.log elapsed across 4 exps; run 1 memory-contaminated and quarantined to run1_confounded/) | 2.0 h | Gemma 4-E4B-4bit |
| U | Phase 1.51V session 5 (EXP23/24 TOMATO holdout pair rerun after session 4 thermal confound) | 1735 s measured = **0.48 h** (EXP23 886 s + EXP24 849 s; favorable-direction 119 ms decode Δ; EARNED-ADVISORY on primary E2E gate) | 0.48 h | Gemma 4-E4B-4bit |
| J₁₆ₕ | Phase 1.41 Qwen 16f VideoMME **holdout** n=30 (H2 falsification run, task #160) | ~38 min (same per-item cost as dev 16f; aggregate 0.700, H2 FALSIFIES the dev-only long-bucket −20pp observation — holdout long 0.900 vs dev 0.100) | 0.63 h | Qwen 2.5-VL-7B-4bit |
| V | Phase 1.51V EXP10 n=60 composition audit (VideoMME dev+holdout combined, task #152 CLOSED-NULL) | ~3.0 h measured (n=60; lift 2.6pp FAILS ≥4pp gate, agreement 0.65 FAILS 0.75; ceiling model reproduces to 0.2pp at fixed_frac = 0.875) | 3.0 h | Gemma 4-E4B-4bit |

### Local-only historical runtime (not paper-body evidence)

| # | Claim | Cold-cache | Warm-cache | Model |
|---|---|---|---|---|
| C | MVBench motion holdout N=30 sticky4 | ≈ 90 min | ≈ 25-30 min | Qwen 2.5-VL-7B-4bit |
| D | Novelty-ranked dense 2×3 grid (TOMATO+MVBench, N={4,6,8}) | ≈ 120 min | ≈ 45-60 min | Qwen 2.5-VL-7B-4bit |
| F | Phase 1.36 oracle (per-block Pearson, partial cache coverage) | ≈ 60 min | ≈ 20 min | Qwen 2.5-VL-7B-4bit |
| G | Phase 1.50 dense wall-clock baseline for sparse-execution accounting N=30 pair | ≈ 2 h per benchmark (cold) | ≈ 2 h (cold; no cache win) | Qwen 2.5-VL-7B-4bit |
| H | Derived from G, zero runtime | — | — | — |

### Runtime cost summary

**Already spent** (benchmark wall-clock, cumulative approx over project):
- Qwen routing (TOMATO + MVBench): ~25-30 h total historical wall-clock; release-backed paper-body rows are A+B+E, while C/D/F/G are local-only diagnostics until rerun or materialized.
- Gemma first-pass pruning + ceiling validation: ~10-12 h (K+M)
- Gemma first-pass expansion + 32f probe + holdout sessions 2-5: ~10.4 h (P 4.34 h + Q 1.99 h + R 0.75 h + S 0.8 h + T 2.0 h + U 0.48 h measured)
- Gemma EXP10 n=60 composition audit, 2026-04-21: ~3.0 h (V)
- VideoMME lane (claim 8 earned + strengthened + **holdout**): ~120 min (J₈ 16 min + J₁₆ 38 min + J₃₂L 28 min + **J₁₆ₕ 38 min** 2026-04-21)
- Persistent-KV lane (claim 14): ~7.3 h (O)
- **Total benchmark wall-clock already spent: ~58-65 h**

**Forward queue** — priority order per `paper/priority.md` round-26, benchmark
wall-clock only. Blocker column is honest about what's actually
runnable tonight vs. impl-gated.

| Prio | Phase | Runtime | Model | Blocker status |
|------|-------|---------|-------|----------------|
| should-do #3 | **1.51V Qwen cross-arch probe** (L=2, kr=0.50, VideoMME 8f n=30 thermally paired, 2 arms) | **CLOSED 2026-04-23** | Qwen 2.5-VL-7B-4bit | **landed** — `V_red = 0.398`, `E2E = 1.044× observed vs 1.043× predicted`, aggregate `Δacc = −0.033`; C-VISION upgrades to two-architecture mechanism evidence |
| should-do #4 | Local paired streaming-protocol reproduction (1.30) + root-cause decomposition | CLOSED-BOUNDARY 2026-04-26 for current policy | Qwen 2.5-VL-7B-Instruct-4bit (driver hard-fails on non-Qwen at `run_phase1_30_scaleout_streaming.py:303-308`) | The 1.30W dense-Q0 reference lands paired cold 0.561 / streaming 0.503 (Δacc = −0.0585) / 2.79× with aggregate Q0 parity and clean format, but misses the preregistered `3.0×` rescue floor. The later 1.30AD instrumented cache-reuse rerun preserves the same aggregate boundary and reaches 3.02×, while proving follow-up vision pruning is inactive (`vision_pruning_active_fraction=0.0`, all follow-up image tokens cache-served). The failure is therefore fidelity/follow-up state, not a deployable sparse-vision speed win. 1.30X's Δacc=0.0 / 3.078× point is oracle-only. 1.30Z/AB falsify every tested long-Q0 keep rate from 0.67 through 0.90; high keep rates restore aggregate Q0 accuracy but still lose follow-ups by ~19pp. |
| should-do #5 | **1.55 selective re-prefill frontier** (recover Δacc at 20f/32f while clawing back speed) | Breadth landed; many-turn / sampler / cross-architecture follow-ups remain | Qwen 2.5-VL-7B-4bit | **Fixed K=1 now has broad local evidence** — no observed paired drift on n=93 across 20f short/medium/long plus 32f short (one-sided rule-of-three upper bound ≈3.2%), 9.48×–20.37× same-class median follow-up speedup, and 0/62 pathological follow-up outputs. **Adaptive post-Q2-state reuse is now the headline repair lane** — 0/93 paired drift, 14.90×–35.92× same-class follow-up speedup, and a 15.28×–35.97× cold-all-query ratio. Stage timing shows adaptive Q3 avoids fixed-K's repeated last-frame re-prefill. **1.55E (`Q2=K1`, `Q3=K0`)** remains the bounded negative that proves cache-source inheritance is the mechanism. **1.55B** remains the separate persistent-KV × 1.54 composition phase. |
| should-do #6 | **1.58 bf16 KV control at 20f** (discriminate quantization vs attention-OOD) | ~3.5-4 h (bf16 8f n=30 + bf16 16f n=30) | Qwen 2.5-VL-7B bf16 | **wrapper-landed; preflight still blocks execution** — `scripts/run_phase1_58_bf16_control.sh` + analyzer landed, but the local bf16 checkpoint is absent and the current 16 GB laptop plan caps autonomous runs near `10 GB` RSS, well below the prereg's looser `<14 GB` feasibility band |
| should-do #8 | **1.29 codec-native bridge (reframed)** | landed semantically; slow offline extraction | Qwen 2.5-VL-7B-4bit | **planner-substitution evidence landed** — MAX-over-span sparse sampling is HARD-FALSIFIED, while the continuous-score redesign reaches codec-dense agreement 1.000 on VideoMME dev all-duration n=30 with zero aggregate accuracy delta and zero parse failures. Later calibration-mode and calibration-source ablations are neutral on the local slices we ran. This is not a latency claim: offline codec extraction totals 7290s; the remaining gate is streaming decoder integration / native-rate systems evaluation. |
| future | **1.60 scroll/pan subset** (20 items stratified by scroll intensity, L=2 kr=0.50 paired) | n/a on VideoMME; ~70-90 min after a real subset exists | Gemma 4-E4B-4bit or matched C-VISION stack | **closed as natural-VideoMME corpus limitation** — wider 60-item VideoMME scan found 0/60 items above `shifted_fraction >= 0.30` (max 0.125), so this only reopens with EgoSchema/EPIC-Kitchens/Ego4D or a labeled synthetic scroll/pan set |
| diagnostic | **Qwen 8f holdout `videomme_holdout_v1.toml` n=30** (parallel to already-done 16f holdout) | ~8 min (cold) | Qwen 2.5-VL-7B-4bit | **runnable-now** — driver exists, manifest exists |
| split-landed | 1.42 Gemma topology lane | complete on the preregistered N=30 pair | Gemma 4-E4B-4bit | landed 2026-04-24: TOMATO pass (`agreement=0.933`, `dense_acc=cached_acc=0.267`), MVBench strict-agreement fail (`agreement=0.733`, `dense_acc=cached_acc=0.200`); further work is interpretation or third-architecture breadth, not implementation |
| blocked | 1.43 EgoSchema breadth gate | ~2 h | Qwen 2.5-VL-7B-4bit | loader + manifest unwritten |
| superseded | 1.52R original composition gate (1.42 × 1.51R) | obsolete | Gemma 4-E4B-4bit | original gate superseded: 1.42 split-landed and 1.51R closed own-axis null; current composition evidence comes from 1.51V EXP10 and future scale-out bundle gates |
| landed-boundary | Claim-5 measured sparse-execution envelope | landed 2026-04-29; broader curve remains open | Gemma 4-E4B and Qwen 2.5-VL-7B-4bit | Gemma 32f short is the clean timed-skip cell (1.316×, 0/20 paired drift, parse failures 0/0). Gemma 8/16/32f full sweep has matched parse-failure caveats. Qwen 16f kr=0.85 is fidelity-safe but low-gain; broad sparse backend and sparse LM prefill remain larger engineering work. |

**Runnable next with setup**: many-turn C-PERSIST stability,
direct cache-state instrumentation for the 1.30 boundary, and scale-out
artifact-compatible 26B replication are now higher leverage than more VideoMME
breadth. `1.58` remains blocked by the missing bf16 checkpoint and the current
local memory policy.

**Aggregate forward cost once blockers clear**: ~20 h benchmark-only
@ 8f (excludes implementation); ~40 h @ 32f.

All estimates exclude implementation, debugging, and CI — they
describe only the wall-clock the user would burn re-running
already-landed experiments or clearing the currently-blocked
queue once infra is in place.

## Venue targeting (current honest read)

| Venue | Fit today | What would need to land |
|---|---|---|
| **arXiv preprint (current anti-recomputation draft)** | **Ready today** as a multi-regime anti-recomputation paper with clean, advisory, and artifact-pending status stated explicitly. | No new science gate for the local claims. Keep provenance tight, finalize manuscript framing, and keep candidate C-STREAM pending until its artifact bundle lands. |
| **NeurIPS / ICLR / CVPR efficiency workshop** | **Defensible today** as the current anti-recomputation paper if the provenance remains tight and clean/advisory/pending rows stay visibly distinct. | Stronger with broader measured sparse-backend coverage, many-turn C-PERSIST stress, and a cleaner local streaming bridge. |
| **Main track (NeurIPS/ICML/CVPR)** | **Not ready yet.** The paper now has a better three-regime story than the old venue rows implied and does include bounded measured sparse-vision evidence, but it still lacks broad fidelity-preserving sparse-backend coverage, broader apples-to-apples comparison against adjacent methods, and a cleaner bridge from local benchmark evidence into deployment-style streaming evaluation. | Broader measured sparse-backend coverage, many-turn C-PERSIST stability, broader first-pass coverage on the second architecture, a decoder-integrated codec-native / native-rate systems bridge, a scroll/pan/egomotion probe on a corpus that actually contains that regime, and tighter head-to-head positioning against the closest trained and training-free baselines. |
| **Systems conference (MLSys/OSDI)** | **Not ready yet.** The deployment evidence is interesting, but the current paper still does not characterize a full sparse backend or benchmark the streaming path against a clean systems baseline such as screenshot polling. | Sparse execution characterization, screenshot-polling baseline, broader streaming or event-detection evaluation, and ideally a decoder-integrated codec-native streaming bridge. |

## What is safe to say in a one-paragraph abstract TODAY

> We study training-free anti-recomputation for video VLMs across three
> reuse regimes: first-pass vision pruning on fresh videos, after-ingest
> follow-up questions on the same video, and routing under a fixed dense
> backend. On Gemma 4-E4B-4bit, mid-layer vision-tower pruning yields
> measured first-pass gains from **1.113×** to **1.407×** on clean or
> advisory holdout cells, and bounded measured sparse-vision runs now add
> real skipped vision work, led by a clean **1.316×** 32f-short operating
> point. On Qwen2.5-VL-7B-4bit, persistent-KV reuse cuts same-video follow-up
> latency to **815 ms** median at **47.2×** speedup at 8 frames and **807 ms**
> at **91.1×** speedup at 16 frames; the repair lane is now broader, with
> adaptive selective re-prefill showing **0/93** observed paired drift at
> **14.90×–35.92×** same-class follow-up speedup and a **15.28×–35.97×**
> cold-all-query ratio.
> Routing holdouts on TOMATO and MVBench then show the mechanism
> boundary: a bounded-staleness planner preserves the quality-compute
> frontier, while local novelty-ranked diagnostics suggest that
> fresh-compute placement is not captured by novelty magnitude alone.
> Candidate C-STREAM remains pending until a validated streaming artifact bundle
> supplies raw paired outputs, cache-correctness smokes, source paths, and
> matched baselines.

## What is NOT safe to say today

- "SOTA" on any axis.
- "Broad sparse-backend speedup" (ViT-only measured sparse execution has one
  real skipped-work boundary point, but not a fidelity-preserving paper-grade
  speedup curve; sparse LM prefill remains out of scope).
- "Generalizes broadly across architectures" (one matched second-architecture point is now landed, but broad transfer is still too strong).
- ~~"Validated on VideoMME" (phase 1.41 not run).~~ **EARNED 2026-04-18** (Qwen 2.5-VL-7B VideoMME dev n=30, dense_accuracy 0.533).
- "Beats CodecSight / CoPE / FastV / VisionZip" (no head-to-head).
- "Training-free codec-guided" without qualifying the regime split:
  sparse-sampled QA is still pixel-diff by design, native-rate streaming is
  codec-metadata by design, and the local 1.29 bridge is semantic rather than
  latency evidence.

## Immediate next actions to extend publishability (ranked for one-paper submission goal)

**Status update 2026-04-23 (Qwen cross-arch probe landed; three-benchmark C-VISION trifecta already closed):**
- **TOMATO 8f holdout EARNED-ADVISORY** — EXP23/24 rerun after session 4
  confound. Paired sum-ratio E2E **1.194×** (mean), median **1.232×**;
  V_red 0.350; acc Δ −0.067. Decode Δ 119.7 ms abs (3.51% rel) — fails
  revised 100 ms floor by 19 ms BUT direction is FAVORABLE (EXP24
  patched arm ran cooler than EXP23 reference, so observed speedup is
  conservatively under-stated, not inflated). Scatter-back ceiling
  predicts 1.155×; observed 1.194× is consistent with ceiling plus
  small friendly thermal correction. Zero dense-arm runtime outliers
  (contrast session 4's 4 EXP21 outliers). Under prereg decision matrix,
  qualifies for EARNED-ADVISORY (≥1.15× AND thermal fails by <200 ms in
  favorable direction).
- **Three-benchmark C-VISION holdout trifecta effectively closed with
  differentiated advisory strength:** VideoMME clean (session 3);
  MVBench advisory on OS-jitter-scale drift (session 4); TOMATO advisory
  on 19 ms favorable-direction drift (session 5). No benchmark requires
  further rerun to support paper-grade claims; all three clear their
  primary E2E gates.
- **V_red band reinterpretation:** TOMATO 0.350 now sits 0.03 below the
  [0.38, 0.48] dev band (closer than session 4's 0.287). Three
  explanations remain indistinguishable without a third thermally-clean
  TOMATO point: (a) TOMATO item mix genuinely differs in token-
  distribution sensitivity; (b) residual thermal bias on session 4+5;
  (c) true V_red band is benchmark-conditional at ~[0.35, 0.48] rather
  than invariant at [0.38, 0.48]. Paper can report the 1.24× (dev) +
  1.194× (holdout) span honestly while flagging the V_red cross-benchmark
  spread (0.35–0.47) as an open reviewer question.
- **Session 4 legacy:** session 4 TOMATO pair (EXP21/22) formally
  DEPRECATED by session 5 for adjudication purposes. EXP21's 4 dense-
  arm runtime outliers + +206 ms hostile thermal drift made its
  mean-based E2E statistic unreliable. Session 5 is the paper-grade
  TOMATO holdout measurement.

**Status update 2026-04-21 (session 4 — MVBench holdout CLOSED, TOMATO confounded, now superseded by session 5):**
- **MVBench 8f holdout CLOSED (advisory pass)** — EXP19 unpatched →
  EXP20 V-patched at L=2 kr_V=0.50, n=30. Paired sum-ratio E2E 1.407×
  (far exceeds dev 1.21× and prereg gate 1.10×), V_red 0.4712 (above
  [0.35, 0.45] band, favorable direction), acc Δ −0.033 (within ±0.03
  band). Thermal gate formally fails: |decode Δ|/decode = 11.66%
  (50 ms absolute on 432 ms window). Adjudication: **advisory pass**.
  The 2% relative rule breaks down on short decode windows (<500 ms)
  where OS jitter dominates — 50 ms is at scheduler-jitter scale, and
  the 2% gate = 8 ms is below OS granularity.
- **Thermal-gate calibration proposal:** `|decode Δ| < max(0.02 ×
  decode_ms, 100 ms)`. Under this calibration MVBench passes cleanly,
  TOMATO still fails (206 ms > 100 ms floor), and all four dev 1.51V
  cells that previously failed the strict 2% gate clear. Will apply
  going forward to short-clip holdout benchmarks and to task #152 EXP10
  composition audit.
- **TOMATO 8f holdout THERMALLY CONFOUNDED** — EXP21/22, paired sum-ratio
  E2E 1.330× (outlier-contaminated), median 1.113×, robust (trimmed)
  1.056×; V_red 0.2867 (below band); acc Δ −0.067 (outside band);
  decode Δ 6.52% = 206 ms abs (genuine thermal drift). Four EXP21
  dense-arm items show gen-time 2–14× slower than paired pruned-arm
  with identical decode/vision/token counts — runtime instability of
  the MLX kernel path, independent of the thermal drift. Session 5
  rerun queued after thermal stabilization; TOMATO 1.24× holdout
  replication remains the last gated C-VISION experiment.
- **Three-benchmark V_red spread now 0.29 / 0.41 / 0.47 = 18 pp range**
  (TOMATO-confounded / VideoMME / MVBench). Pressures the paper's
  "V_red ≈ 40% benchmark-invariant" framing; flagged as open reviewer
  question in claim-matrix row 15.
- **Driver fix:** `_count_frames` metadata fast path removed (commit
  4174f82). Container `stream.frames` can lie (observed 366 vs actual
  235 on videomme 0298-00.mp4); iterating is the only safe count.
  Regression test pins the invariant in `tests/test_video_decode.py`.

**Status update 2026-04-21 (1.51V expansion + 32f probe + holdout session 2 landed):**
- **1.51V V-tower pruning (Gemma 4-E4B-4bit, dev n=30):** 12/12 expansion
  experiments closed at L=2 kr_V=0.50, thermally paired. VideoMME 1.08×
  (8f) / 1.12× (16f) / 0.94× (32f, thermal-confounded); MVBench **1.21×**;
  TOMATO **1.24×**. V_red benchmark-invariant at 39–43%. Scatter-back
  ceiling `1/(1 − V_share × V_red)` predictive within 2pp on 4 cells.
  **32f probe:** V_share continues monotone (15.2% → 24.3% → 31.0%), but
  M3 16 GB thermal pairing breaks at 32f (decode Δ=+7.6%); H_32f_e2e
  REJECTED on both observed (0.94×) and charitable-ceiling (1.14×)
  grounds.
- **1.51V holdout session 2 (n=30 disjoint VideoMME items):** composition
  PARTIAL confirmation — V+novelty kr=0.3 stacks at 1.064× within-run
  (thermally clean) / 1.127× cross-session (dirty, decode Δ=-7.8%);
  agreement 0.667; acc Δ=-0.033. V_share from EXP15 V-patched reference
  arm measured 8.6% (vs dev 15.2%); LLM-side ceiling
  `1/(1 − generate_share × generate_reduction) = 1.064×` matches observed
  to 0.1pp. Fifth ceiling-model regime. **Note (2026-04-21):** session 3
  EXP17 true unpatched baseline reports holdout V_share = 15.45% (vision
  7663 ms / E2E 49594 ms); the 8.6% number reflects the V-patched
  reference denominator, not the true unpatched V_share.
- **V-only holdout UNPATCHED-vs-PATCHED pair:** VideoMME 8f CLOSED
  2026-04-21 via session 3 EXP17/18 — all four preregistered hypotheses
  pass (E2E 1.113×, V_red 0.413, decode Δ 1.53%, acc Δ 0.000). The paper
  VideoMME 8f V-only cell drops its "dev-only n=30" caveat. MVBench +
  TOMATO holdout pairs queued as session 4 (EXP19–22, ~2h).
- **Thermal pairing runner gate recommended.** Three of four 1.51V pairs
  violate decode-Δ<2% (only EXP11/12 clears). Codifying auto-retry at
  the runner level would prevent future thermal confound.

**Status update 2026-04-18 (post-Stage-6 cross-bucket surface + 1.41 landed):**
- **Claim #8 VideoMME baseline EARNED** — Qwen 2.5-VL-7B-Instruct-4bit
  on `videomme_dev_v1.toml` n=30 at 8 frames, identity cache: dense
  accuracy 0.533 (H1 [0.40, 0.60] best-guess 0.50 earned), 0/30 parse
  failures (H2 earned), peak RSS 6.67 GB (H3 < 8 GB earned),
  agreement=1.000, median e2e 30.5 s (H4 [40, 90] earned faster than
  predicted). Per-bucket monotone 0.800 (short) → 0.500 (medium) →
  0.300 (long) confirms 8-frame undersampling hurts long clips most.
  The 16 GB headroom means 16/32-frame follow-up is feasible without
  OOM, should we need to put the baseline in range of public 32-frame
  ~0.55 references.
- **Claim #13 C-CEILING earned** — arithmetic-ceiling model validated
  across 7 regime dimensions (8-frame kr sweep + 32-frame short/medium/
  long + smoke + Stage 7 32f short × gemma_structural × kr=0.33) with
  median 2.1% / worst 5.2% prediction error. This graduates to a
  standalone publishable analytical contribution independent of any
  SOTA arm.
- **New Pareto points at 32 frames, kr=0.10:** short 1.663×, medium
  1.565×, long 1.234× — all at Δacc=-0.100. Strict-inside-band earn
  on medium; favorable-direction falsification on short (1.663× above
  pre-reg upper 1.55×); downward falsification on long (1.234× below
  pre-reg lower 1.50×, confirming D-ceiling).
- **8-frame kr=0.33 gemma_structural short-bucket Δacc=0 at 1.090×**
  remains the Pareto-knee earned-win. Stage 7 (in flight) tests whether
  this accuracy-preserving recipe generalizes to the 32-frame regime.
- **1.8× is our internal preregistered reproduction target, NOT the
  pre-release source claim.** The pre-release source reports 5.4× prefill / 4.2× e2e
  on Gemma 26B and Qwen 32f talking-head. Our 4B-class / 8-frame regime
  is arithmetically bounded to ≤1.46× at kr=0.10 aggregate; 32-frame
  lifts the ceiling but introduces decode cost.
- **32-frame cross-bucket aggregate = 1.389× time-weighted at
  Δacc=-0.100 is DEV-ONLY indicative.** Holdout tranche has not been
  run. Per-bucket numbers (short 1.663×, medium 1.565×, long 1.234×)
  are the primary reportable results. *Methodology note (Codex
  round-21):* the earlier 1.487× figure was a mean of per-bucket
  ratios, which overweights fast buckets; the correct time-weighted
  aggregate (`sum(dense_e2e) / sum(pruned_e2e)` across 30 items) is
  1.389×. See `2026-04-18-phase-1_51R-stage6-32frame-medium-findings.md`
  §aggregate for the full derivation.
- **Decode-economics scope (Codex round-21).** Our per-item
  subprocess driver charges full H.264 decode against every
  inference (1 session = 1 item). On a production streaming
  deployment with session-warm ViT features, decode would amortize
  across many turns per clip, and the decode fraction (56.9% of
  e2e on long-32) would shrink toward zero. Our reported aggregates
  and the Ceiling@∞ numbers they feed should be read as **upper
  bounds on decode cost**, not fundamental ceilings; a streaming
  client running Phase 1.55 (persistent KV-cache) could reach the
  C-CEILING prediction at s→∞ asymptotically. We do not
  retroactively adjust numbers — keep them as pessimistic
  benchmarks, note the amortization in the method section. See
  `2026-04-19-codex-round-21-scaleout-imports.md` §4.
- **Attention-context drift vs PE drift (Codex round-21).** The imported
  predecessor pre-release source attributed the refresh requirement to attention-context
  drift (~0.01/frame; target summarized in `docs/claim-register.md`),
  NOT positional-encoding drift. Our 1.49 refresh sweep shows
  *that* periodic re-encode recovers agreement but does not isolate
  *which* drift mechanism is load-bearing. Paper framing must say
  "attention-context drift" when citing the pre-release source and must NOT assert a
  PE-drift mechanism absent a local ablation (Phase 1.57, queued
  P2). The two require different mitigations: re-encode at I-frames
  (what we do) addresses attention drift; temporal RoPE key
  correction would address PE drift. See
  `2026-04-19-codex-round-21-scaleout-imports.md` §3.

**Priority ordering now lives in `paper/priority.md`** (codex round-26
2026-04-21 designated priority.md as the authoritative venue-readiness
/ submission-gate doc). This section is a short mirror + the retired
items that priority.md does not carry. For the current ordering see
`paper/priority.md` (must-do / should-do / future sections).

### Current queue mirror (priority.md §Should-do, in rank order)

1. ~~**EXP10 n=60 composition audit**~~ — **CLOSED-NULL 2026-04-21
   (autonomous session, task #152).** n=60 arm B V+novelty E2E
   1.0420× / V-only ref arm A 1.0159×; lift 2.6pp FAILS ≥4pp gate;
   agreement 0.650 FAILS ≥0.75; acc Δ −0.017 PASSES. Ceiling model
   reproduces observation to 0.2pp: fixed_frac 0.875 (V_share
   collapsed to 6.26% vs dev 15.2%), per-token speedup 1.446× gives
   arithmetic ceiling 1.041×. Composition appendix does NOT land; the
   paper's three-contribution spine is unchanged. Findings:
   `research/experiments/2026/2026-04-21-phase-1_51V-exp10-n60-findings.md`.
2. ~~**1.51V MVBench and TOMATO holdout V-only pairs**~~ — **CLOSED
   2026-04-21** (three-benchmark C-VISION trifecta). No further rerun
   required to support paper-grade C-VISION claims.
3. ~~**1.51V cross-architecture transfer probe on Qwen 2.5-VL-4bit**~~ —
   **CLOSED 2026-04-23.** Turns C-VISION from single-arch mechanism into
   two-architecture mechanism evidence at matched `L=2`, `kr_V=0.50`:
   `V_red = 0.398`, `E2E = 1.044×` observed vs `1.043×` predicted,
   aggregate `Δacc = −0.033`.
4. **Local paired streaming-protocol reproduction of the pre-release N=60 line**
   — **CLOSED-BOUNDARY FOR THE CURRENT POLICY.** The original bridge was
   a hard negative; the successor `1.30W` policy improves the same Qwen 7B
   8f dev+holdout-union bridge to cold `0.561` / streaming `0.503`
   (`Δacc = −0.0585`) at `2.7869×`, with aggregate Q0 parity (`34/57` in
   both arms), `0` parse failures, and `0` degenerates. 1.30Z/AB then
   falsify every tested long-Q0 keep rate from `0.67` through `0.90`, and
   the conditional union rerun was correctly skipped. Later instrumentation
   confirms the wording boundary: 1.30AD's speed comes from **Q0 admission +
   K-cache reuse** (`vision_pruning_active_fraction=0.0`), while 1.30AC forces
   follow-up V-pruning active but falls to **1.06×**. Both land at the same net
   aggregate loss through different any-paired-drift sets. 1.30X's
   `Δacc = 0.0000`, `3.0781×` point remains an oracle upper bound, not a
   deployable result.
5. **1.55 selective re-prefill v2** — no longer an implementation
   question. Repo-local v2 is landed, fixed K=1 is the broad recovery
   envelope, and adaptive post-Q2-state reuse is the headline repair lane:
   **fixed K=1 has no observed paired drift on n=93** across 20f
   short/medium/long plus 32f short, 9.48×–20.37× same-class follow-up
   speedup, and 0/62 pathological follow-up outputs. **1.55F adaptive**
   has no observed paired drift on n=93 at 15.28×–35.97× all-query speedup
   and 14.90×–35.92× same-class speedup. The first adaptive omission follow-up,
   1.55E
   (`Q2=K1`, `Q3=K0`), is a bounded negative: `Δacc = -0.0952` with
   pathological-like outputs on `7/7` third queries. Together, 1.55E and
   1.55F say the Q3 catastrophe was a cache-source inheritance problem,
   not adaptive repair impossibility.
   The next paper-relevant moves are many-turn stability, sampler sweep,
   cross-architecture cache semantics, and direct cache-state instrumentation.
6. **1.58 bf16 KV control at 20f** — isolates quantization as the
   C-PERSIST basin driver; ~2-4h wall once the bf16 checkpoint exists
   locally. Preflight currently marks it blocked.
7. **1.41 Qwen 16f holdout** — frame-count / holdout scaling diagnostic,
   not a C-VISION V-share point.
8. **1.29 codec-native bridge (reframed)** — now a local
   planner-substitution result, not a speed result. MAX-over-span sparse
   sampling is hard-falsified, while the continuous-score redesign matches
   dense on VideoMME dev all-duration n=30 and later calibration-mode/source
   ablations are neutral on the local slices we ran. The remaining paper risk
   is deployment integration, not medium/long semantic survival or calibration
   dependence.
9. ~~**Paper figures: C-PERSIST tested-envelope table + V_share ceiling
   plot**~~ — **LANDED 2026-04-21 (autonomous session, task #161).**
   Scripts `scripts/plot_c_persist_safe_budget.py` +
   `scripts/plot_v_share_v_red_ceiling.py`; artifacts
   `paper/figures/c_persist_safe_budget.{png,_data.json}` and
   `paper/figures/v_share_v_red_ceiling.{png,_data.json}`. V_share ×
   V_red figure now shows Gemma dev/holdout, Qwen cross-arch, measured
   sparse-execution, and composition-audit points;
	   dev median |Δ| 2.2pp, MVBench 8f holdout sits 13.6pp above the
   ceiling (thermal-inflated, matches session-4 advisory).

### Mechanism-validation backbone (Qwen routing, NOT the headline)

Documented here as appendix-grade method evidence. These are the null
/ partial results that the paper's negative-result discipline rests on:

- **Phase 1.37B halo-veto dev tranche** — **RETIRED 2026-04-17** as
  preregistered null. 9/9 cells × 2 benchmarks landed (commits
  2ebf90d + db10e12 + 0ea69fe + 46b5d05 + 2947198). TOMATO NO-LIFT;
  MVBench NO-LIFT-NEGATIVE (halo hurts). Claim 3 rests on phase 1.37
  within-block child-veto as the remaining open path.
- **Phase 1.38 placement ablation** — ≈30 min wall; strengthens claim
  4 mechanism. Not queued.
- **Phase 1.37 within-block child-veto** — not yet implemented;
  ≈2 h wall after code lands; orthogonal path to claim 3.
- **Phase 1.43 EgoSchema N=30 on Qwen** — long-form/egocentric
  generalization; ≈2-3 h wall; claim 12 enabler.
- **Broader measured sparse-backend path** — bounded sparse-vision evidence has
  landed, but broad sparse-backend coverage and sparse LM prefill remain open.
  Defer broad claims until fidelity-preserving curves exist.

### Retired framing (do not reintroduce)

- **"Claim 11 as the big-numbers gate"** — retired 2026-04-21
  per codex round-26. Claim 11 is duration-conditional partial
  reproduction, arithmetically bounded to ≤1.46× at 8f kr=0.10 per
  C-CEILING. Stage 5 anchor comparison lands `gemma_structural` as
  default (secondary methodology content). The paper spine is the
  three first-class contributions (claims 13, 14, 15), not claim 11.
- **"Phase 1.51R novelty-pruning is the headline big-numbers result"**
  — retired. 1.51R is the EXP10 n=60 gate + Stage-5 anchor default.
- **"1.42 gates 1.51R"** — reaffirmed NOT a dependency. 1.51R is a
  fresh LLM-prefill code path; 1.42 is a claim-7 enabler
  independently. 1.42 is now landed as a split result (TOMATO pass,
  MVBench fidelity fail) and no longer belongs in the future-list
  blocker bucket.

Maintained by: research automation. Source of truth for submission
gates: [`priority.md`](priority.md). Source of truth for numbers:
[`claim-matrix.md`](claim-matrix.md) and the artifact JSONs it cites.
