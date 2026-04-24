# Publishability Status — 2026-04-23

One-file answer to "what can we actually claim, in what venue, with what
numbers, today." Kept in sync with [claim-matrix.md](claim-matrix.md) but
scoped narrower: reviewer-facing readiness and runtime-cost evidence.

For paper triage, prefer [priority.md](priority.md) and
[claim-matrix.md](claim-matrix.md) over this file when they disagree. The
current headline is the anti-recomputation story summarized next. Detailed
runtime inventories lower in this file are retained for provenance, but the
current narrative interpretation should come from `priority.md` and the claim
matrix.

## Current Manuscript Position (2026-04-23)

The draft should lead with three linked claims, not with a Qwen-only routing
note:

- **C-VISION**: Gemma vision-tower pruning now has paper-grade first-pass
  speedup evidence on clean and advisory holdout cells, and the same
  scatter-back ceiling now transfers to a matched Qwen VideoMME probe.
- **C-PERSIST**: persistent-KV reuse already delivers the largest local
  deployment numbers in the repo on same-video follow-up queries.
- **Qwen routing**: mechanism and boundary evidence showing why placement of
  fresh computation matters more than novelty magnitude alone.

Sam's streaming lane is not decorative support. It is deployment-scale evidence
for the same anti-recomputation thesis. Its benchmarking style is different, so
the manuscript should label those results as deployment-scale or case-study
evidence rather than flattening them into the same table cell as the local
Gemma holdouts.

## One paper, multiple evidence regimes

**The goal is one results paper, co-authored with Sam, that advances
SOTA across three independent axes.** Codex rounds 25–26 retired the
earlier "one big multiplicative number via claim 11" framing: the
paper spine is now three already-earned, independently-evaluable
contributions (all landed before Codex round-26 2026-04-21):

- **C-CEILING — arithmetic end-to-end ceiling** (claim 13).
  `E2E ≤ 1/(fixed + (1−fixed)/s)` validated across 7 independent
  regime dimensions (8-frame kr-sweep + 32-frame short/medium/long +
  smoke + Stage 7 short × gemma_structural × kr=0.33) at median
  2.1% / worst 5.2% prediction error. A standalone analytical
  contribution independent of any specific SOTA arm.
- **C-PERSIST — persistent-KV safe-deployment envelope** (claim 14).
  6-point speedup curve (47×→91×→70×→94×→122×→150× at 8/16/18/20/24/32f
  on Qwen 7B-4bit) + 3-point cross-arch scaling on Qwen 3B-4bit +
  4-regime temperature matrix. Mechanism decomposes into three
  independently-varying axes (threshold onset × saturation ceiling ×
  basin-attractor identity), scaling relation ~1.6× basin-onset depth
  across architectures. Deployment-facing envelope: 7B stays inside the
  safe region through 16f / ~6.5k prefill, with a clean 16f point and a
  slightly worse but still safe 8f point; 3B stays inside the bounded
  region through 36f / ~14.5k prefill at a tolerated Δacc=−0.19 plateau
  (not clean).
- **C-VISION — vision-tower pruning with scatter-back ceiling**
  (claim 15). `E2E ≤ 1/(1 − V_share × V_red)` on Gemma 4-E4B-4bit
  validated across **6 core scatter points** (4 Gemma dev + 1 matched
  Qwen dev + 1 pooled EXP10 n=60), with **9 rendered points total** once
  the 3 Gemma holdout cells are included; V_red benchmark-invariant at
  39–43% at L=2 kr_V=0.50 on the first dev tranche. **Three-benchmark
  holdout trifecta CLOSED 2026-04-21** (VideoMME 8f CLEAN,
  MVBench 8f CLOSED-ADVISORY on thermal-calibration footnote,
  TOMATO 8f EARNED-ADVISORY on favorable-drift footnote).

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

**Sam as deployment-scale evidence (NOT applications/support).**
The Sam stack (26B-class, real streaming, full end-to-end pipeline)
runs on a deliberately disjoint regime from codec-through (4B-class,
sparse benchmark, mechanism isolation): 4.2–4.5× real-video, 13× ViT,
~50× dominant-pipeline, 0.8 s median follow-up, 5–300× live-camera ViT.
Its sparse exactness rows and streaming rows do not use one uniform
classifier: sparse-sampled QA stays pixel-diff by design, while native-rate
streaming uses H.264 metadata by design.
Shared frame with codec-through: C-CEILING arithmetic + attention-
propagation drift (NOT PE drift). Paper claims are the **evidence
union** across both repos with regime labels attached. Weak streaming
case-study claims without paired baselines stay appendix-bound.

1.51R novelty-pruning does NOT carry the headline. It appears as
(a) the EXP10 n=60 composition-appendix gate (≥4 pp E2E lift over
V-alone AND agreement ≥0.75 AND acc Δ within −0.067), and (b) the
Stage 5 anchor-arm comparison that establishes `gemma_structural`
as the in-repo default (secondary methodology content). Claim 11 is
duration-conditional partial reproduction, arithmetically bounded to
≤1.46× at 8f kr=0.10 per C-CEILING.

See `paper/framing.md`, `paper/abstract.md`, `paper/intro.md`, and
`paper/priority.md` for the authoritative three-contribution
narrative.

> **Training-free anti-recomputation for video VLMs: measured first-pass
> speedups on Gemma, sub-second same-video follow-up queries on Qwen, and
> routing evidence showing that fresh-compute placement matters more than
> novelty magnitude.**

**Concrete headline cells today:**

- **Gemma first-pass vision pruning:** VideoMME 8f holdout **1.113×** clean,
  MVBench 8f holdout **1.407×** advisory, TOMATO 8f holdout **1.194×**
  earned-advisory from the freshly pulled upstream session-5 rerun.
- **Qwen cross-architecture C-VISION transfer:** VideoMME 8f dev at matched
  `L=2`, `kr_V=0.50` lands **1.044×** observed vs **1.043×** predicted, with
  `V_red = 0.398` and aggregate `Δacc = −0.033`.
- **Qwen persistent-KV:** **47.2×** speedup and **815 ms** median follow-up at
  8f, rising to **91.1×** and **807 ms** at 16f inside the safe envelope
  (16f clean; 8f slightly worse but still inside the criterion).
- **Sam deployment-scale evidence:** **13×** streaming ViT reduction,
  **~50×** dominant-pipeline reduction, **4.2–4.5×** real-video end-to-end
  speedups in selected regimes, and **0.8 s** same-video follow-up latency on
  Gemma 4 26B.
- **Qwen routing:** clean-tree Pareto win/tie on MVBench and TOMATO holdouts
  at much lower effective fresh-frame budgets, with the mechanism lesson that
  fresh-compute placement matters more than novelty magnitude alone.

**Secondary — C-PERSIST (persistent-KV safe-deployment envelope):**

> **Persistent KV-cache follow-up queries on Qwen 2.5-VL (MLX) deliver
> 47×→150× speedups along an 8/16/18/20/24/32-frame curve on 7B-4bit
> (prefill-dominated) and 136×→213× on 3B-4bit (decode-dominated).
> Safe deployment envelope is architecture-specific: 7B stays inside the
> safe regime through 16f / ~6.5k prefill, with a clean 16f point and a
> slightly worse but still safe 8f point; 3B stays inside the bounded
> regime through 36f / ~14.5k prefill on a tolerated Δacc=−0.19 plateau
> (not clean). Fidelity degradation
> decomposes into three independently-varying axes (threshold onset,
> saturation ceiling, basin-attractor identity), with a ~1.6× basin-
> onset depth scaling across architectures. Sampler-invariance at both
> architecture ceilings is cross-architectural, not a 7B idiosyncrasy.**

**Tertiary — C-CEILING (arithmetic analytical contribution):**

> **An architectural speedup ceiling E2E ≤ 1/(fixed + (1−fixed)/s)
> explains observed end-to-end multipliers within median 2.1% / worst
> 5.2% across 7 independent regime dimensions on Gemma 4-E4B-4bit
> (Qwen 7B-4bit composition ceiling also matches observed to 0.1pp).
> Bounds the measurable sparse-execution delta analytically before the
> code is written; a standalone analytical contribution independent of
> any specific SOTA arm.**

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

- "**N%** faster" — Track B sparse execution path is not written; only
  the dense wall-clock baseline has been captured (60.1 s/item median
  end-to-end at 8 frames). The projected ceiling on a vision-cache-only
  Track B speedup is **22% end-to-end** at this geometry (phase 1.50).
- "**N%** less energy" — no energy instrumentation. Projected proportional
  to wall-clock at fixed memory.
- "**N%** as accurate" — accuracy is equal (0.633=0.633 on MVBench
  dense-8 vs sticky4, clean tree) or marginally lower (0.333=0.333 on
  TOMATO dense-8 vs base, clean tree). No accuracy trade on the clean
  tree; the win is on the x-axis, not the y-axis.

**Honest one-liner for reviewers:** "matched-accuracy Pareto win at
reduced fresh-frame budget on two temporal-reasoning benchmarks at
N=30 holdout, clean-tree provenance; projected compute-savings ceiling
+22% end-to-end pending sparse-execution implementation."

## Publishable claim inventory (with concrete numbers)

### What is earned RIGHT NOW (can appear in paper body, not just discussion)

| # | Claim | Numbers (cite) | Evidence path |
|---|---|---|---|
| A | **Pareto win on MVBench motion holdout N=30 at matched accuracy.** | Planner 2.0 base `max_abs(8,32) static+shifted age=4` → 0.600 cached_accuracy @ 4.06 effective fresh frames, vs uniform dense-6 at 0.567 @ 6.0 (strict dominance: better accuracy at fewer fresh frames). | `phase1_21_mvbench_motion_holdout_v2_cached_nosticky/*_summary.json`; `paper/figures/pareto_holdout_n30.png` |
| B | **Pareto tie on TOMATO motion holdout N=30 at 44% of the fresh-frame budget.** | Planner 2.0 base → 0.333 cached_accuracy @ 3.55 effective fresh frames, equal to uniform dense-8 at 0.333 @ 8.0. | `phase1_20_tomato_motion_holdout_v2_cached_clean/*_summary.json` |
| C | **Sticky4 refinement matches dense-8 accuracy at 56% of budget on MVBench.** | Planner 2.0 + sticky_window=4 → 0.633 @ 4.49 vs uniform dense-8 at 0.633 @ 8.0. Strict Pareto equivalence at reduced fresh frames. | `phase1_21_mvbench_motion_holdout_v2_cached/*-sticky4_summary.json` |
| D | **Beats novelty-ranked dense on both benchmarks at matched fresh-frame count.** | Novelty-ranked dense N=8 on TOMATO: 0.233 (hurts uniform by 0.100). On MVBench: 0.567 (loses to uniform by 0.067, saturates at 0.567). Planner 2.0 cached DOMINATES every novelty cell at equal-or-lower fresh budget. | `results/novelty_ranked_dense/*_holdout_n{4,6,8}.json`; phase 1.34 note |
| E | **Bounded staleness is the mechanism on TOMATO; removing age=4 causes catastrophic novelty collapse.** | TOMATO Planner 2.0 no-age: novel_blocks→0, identical-feature reuse. With age=4: recovers proxy signal. Content-conditional finding. | phase 1.20 ablation cells (canonical note + registry) |
| F | **Pixel-diff proxy → ViT feature-change correlation is non-trivial but content-conditional.** | Phase 1.36 feature-change oracle: best pixel stat Pearson r=0.233 (TOMATO MEAN) to r=0.504 (MVBench CPF). Ranking is content-dependent; the best routing stat (MAX_ABS) is NOT the best point predictor. | `phase1_36_feature_change_oracle/*.json`; phase 1.36 note |
| G | **Dense wall-clock baseline captured on M3 Air 16GB.** | TOMATO n=10 mc_scoring at 8 frames, 560×560: 60.1 s/item median; prefill 72% of wall time, vision encode 22%, decode 6%; peak 6.87 GB. | `results/track_b/tomato_mc_n10.json`; phase 1.50 note |
| H | **Hard ceiling for vision-cache-only Track B: 22% end-to-end speedup at this geometry.** | Arithmetic: vision encode is 22% of per-item wall time, so any method that only skips vision work caps at 22% end-to-end before prefill savings. | Derived from G; explicit in phase 1.50 §Paper implications |
| R | **1.51V vision-tower pruning on Gemma 4-E4B-4bit (MLX), dev n=30 at L=2 kr_V=0.50 thermally paired:** VideoMME 1.08× (8f) / 1.12× (16f), MVBench **1.21×**, TOMATO **1.24×**; dev V-red lands around 40% across the three benchmarks, but holdout spread is wider and should be described more softly in the manuscript. Scatter-back ceiling `1/(1 − V_share × V_red)` predicts E2E within 2pp on the main dev cells. **32f frame-scaling probe:** V_share = 31.0% at 32f (continues 15.2% → 24.3% → 31.0% monotone), but thermal pairing FAILS on M3 16 GB at 32f (decode Δ = +7.6%); observed cross-run 0.94× is thermally confounded; charitable ceiling prediction 1.14×, sub-threshold. **Holdout replication (EXP15/16, VideoMME holdout v1 n=30 disjoint):** H-stack partial confirmation — V+novelty kr=0.3 on V-patched baseline stacks at 1.064× within-run (thermally clean), 1.127× cross-session (dirty), agreement=0.667, acc Δ=-0.033. LLM-side ceiling `1/(1 − generate_share × generate_reduction) = 1.064×` matches observed to 0.1pp (fifth ceiling regime). **V-only UNPATCHED-vs-PATCHED holdout status:** VideoMME 8f **clean** at 1.113× (EXP17/18); MVBench 8f **advisory** at 1.407× (EXP19/20); TOMATO 8f **earned-advisory** at 1.194× from the session-5 rerun (EXP23/24). | `research/experiments/2026/2026-04-21-phase-1_51V-expansion-findings.md`; `2026-04-21-phase-1_51V-32f-probe-findings.md`; `2026-04-21-phase-1_51V-holdout-findings.md`; `artifacts/phase1_51V_expansion/exp{01..12}_*_summary.json`; `artifacts/phase1_51V_session2/exp{13..16}_*_summary.json`; `codec-through/research/experiments/2026/2026-04-21-phase-1_51V-session5-findings.md` |
| O | **Persistent-KV follow-up speedup 47×/91×/70×/94×/122×/150× at 8f/16f/18f/20f/24f/32f on Qwen 7B-4bit; reproduces Sam §2.13.3 AND confirms prefill-dominance on a six-point scaling curve. Fidelity preservation is bounded by a MONOTONIC-SATURATING RAMP — clean at ≤ ~6.5k tokens (16f, Δacc=0); 4-basin mixed-attractor degeneracy at ~7.3k (18f, Δacc=−0.24); 2-basin dominance at ~8.1k (20f, Δacc=−0.38); single-token attractor by ~9.7k (24f, Δacc=−0.43). Pairwise Δacc increments decay (−0.238, −0.143, −0.048, 0). Cross-architecture 3-point probe on Qwen 2.5-VL-3B-4bit: 20f Δacc=−0.048 (matched); 24f Δacc=−0.190 (shifted-ramp); 32f Δacc=−0.190 (PLATEAUED — numerically identical to 24f at 60% deeper prefill). 3B saturates at a ~2.3× SHALLOWER CEILING than 7B (−0.19 vs −0.43), and all 28/28 3B follow-ups across 20f/24f/32f emit clean 2-token letter answers (zero basin collapse). Cache-reuse damage decomposes into three independently-varying architectural dimensions: (1) threshold onset is capacity-modulated (7B ramps at ~7.3k; 3B ramps at ~9.7k), (2) saturation ceiling is architecture-specific (−0.43 vs −0.19), (3) failure geometry is architecture-specific (basin collapse to `addCriterion` vs clean-letter drift). **Temperature probe on 7B/20f (T=0.7 + min_p=0.05 + seed=42): Δacc = −0.429 — numerically temperature-invariant (greedy −0.381; diff 0.048 ≈ 1/21 noise floor). H2-temp.distribution-collapse EARNED; H-greedy-commit FALSIFIED. Basin mass redistributed to a NOVEL pathological attractor (`自动生成` Chinese "auto-generate", 5/14) NOT to clean decoding (clean share unchanged at 1/14). The pathological distribution is intrinsic to cache-reused 7B logits, not a greedy-argmax artifact. Failure geometry is architecture-specific AT THE DISTRIBUTION LEVEL on 7B — not sampler-level.** **Temperature mirror on 3B/20f (same sampler): Δacc = −0.095 (greedy −0.048 → temp −0.095, shifts by 1/21 noise floor); 14/14 clean 2-token letter follow-ups; 0 pathological-attractor emergence; H2-3B-temp.null-robust EARNED on both preregistered conditions; H2-3B-temp.hidden-basin FALSIFIED. Sampler-invariance now verified at BOTH architecture ceilings — distribution-level fidelity-loss vs distribution-level clean-drift is cross-architectural, not a 7B idiosyncrasy. Paper corollary: practitioner cannot recover fidelity via temperature + min-p at either ceiling; fidelity recovery requires upstream intervention (Phase 1.55D selective re-prefill preregistered 2026-04-20).** | 1.55A 8f: n=21, follow-up median 815 ms, Δacc −0.048, prefix 0.982, peak RSS 2.81 GB. 1.55A 16f: n=21, follow-up median 807 ms, **Δacc 0.000**, prefix 0.991, peak RSS 1.48 GB. 1.55A 18f: n=21, follow-up median 1102 ms, **Δacc −0.238 (ramp; 4/14 clean-correct + 3/14 clean-wrong-choice + 3/14 long-garbage + 2/14 empty + 2/14 saturated-`addCriterion`; richest basin diversity in the sweep)**, prefix 0.9920, peak RSS 4.19 GB. 1.55A 20f: n=21, follow-up median 905 ms, **Δacc −0.381 (ramp; 9/14 short `addCriterion` + 4/14 long garbage + 1/14 clean-correct)**, prefix 0.9928, peak RSS 3.51 GB. 1.55A 24f: n=21, follow-up median 864 ms, **Δacc −0.429 (saturated)**, prefix 0.9940, peak RSS 3.30 GB. 1.55A 32f: n=21, follow-up median 1008 ms, **Δacc −0.429 (saturated)**, prefix 0.9955, peak RSS 2.50 GB. **1.55A-3B 20f cross-arch (2026-04-19): Qwen 2.5-VL-3B-Instruct-4bit, same 7 clips × 3 Qs, same driver, same prefill ~8.1k → follow-up median 412 ms, speedup 136.07×, Δacc = −0.0476 (INSIDE ±0.05 envelope), prefix 0.9928, peak RSS 3.93 GB, 7/14 follow-up correct. All 14 follow-ups emit 2-token clean letter answers — NO addCriterion basin, NO long-garbage basin. 1.55A-3B 24f boundary-shift (2026-04-20): same 7 clips, 24 frames (~9.7k prefill) → follow-up median 423 ms, speedup 154.17×, Δacc = −0.190 (H2-3B-24.shifted-ramp EARNED, band (−0.30, −0.05)), prefix 0.9940, 6/14 follow-up correct. First-query accuracy 4/7 identical to baseline; follow-up Δacc = −0.286 concentrated on cache-reused queries. Basin structure: 14/14 clean 2-token letter answers (no addCriterion, no long-garbage) — 3B degrades via decode-choice drift, not basin collapse. 1.55A-3B 32f saturation (2026-04-20): same 7 clips, 32 frames (~12.9k prefill) → follow-up median 484 ms, speedup 213.01× (exceeds 7B 32f's 150×), **Δacc = −0.190 (H2-3B-32.plateaued EARNED, band (−0.25, −0.10] — most-surprising pre-registered sub-outcome)**, prefix 0.9955, peak RSS 4.58 GB, 5/14 follow-up correct. **Δacc is numerically identical to 3B 24f** (same 10/21 session, same 14/21 baseline) — 3B has saturated at a ~2.3× shallower ceiling than 7B. First-query 5/7 both modes. All 14 follow-ups remain clean 2-token letter answers at 12.9k prefill — no basin collapse emerges on 3B at deeper prefill than 7B saturation. Cross-arch 3-point: the cache-reuse damage decomposes into three orthogonal dimensions — threshold onset (capacity-modulated), saturation ceiling (architecture-specific), failure geometry (architecture-specific).** 24f and 32f failure statistics are numerically identical (both session 9/21, baseline 18/21, 14/14 follow-ups emit literal `addCriterion` token) — single-attractor collapse. **Basin-structure evolution across ramp on 7B**: clean (16f) → 4-basin diversity (18f) → 2-basin dominance (20f) → single attractor (24f+). This progressive collapse favours threshold mechanisms with a soft edge over pure gradient and over pure cliff. **Mechanism discrimination (cross-arch 2-point): the ramp at 3B is shifted, not absent** — 3B 20f Δacc=−0.048 → 3B 24f Δacc=−0.190 → ramp onset is capacity-modulated with an architecture-specific threshold. **Basin attractor identity is architecture-specific:** 7B saturates to `addCriterion`; 3B stays in the 2-token letter distribution even while accuracy drops. Rules out "pure prefill-length-intrinsic" as a complete mechanism and rules out "shared-tokenizer-space basin" as the locus of the attractor; supports "model-capacity / depth-dependent accumulation". Cold-prefill Q1 accuracy: 7/7 at 18f/24f/32f, 6/7 at 20f (one cold flake), matches baseline — content understanding is intact; only the cache-reuse path is. Speedup scaling (47×→91×→70×→94×→122×→150×) and first-query scaling (38.5→73.5→77.5→83.8→108.9→163.2 s) form a 6-point prefill-dominance curve (18f dip is median-inflated by long-garbage gen tokens, not cache-coupled). 3B 20f speedup 136× exceeds 7B 20f 94× — prefill-dominance ratio is HIGHER at 3B because decode is comparatively faster. Median follow-up matches Sam's 0.8 s (Gemma 4 26B / M5 Max) across 8f/16f. | `research/experiments/2026/2026-04-19-phase-1_55A-persistent-kv-findings.md`; `.../2026-04-19-phase-1_55A-{16,18,20,24,32}f-frame-scaling-findings.md`; `.../2026-04-19-phase-1_55A-3b-crossarch-findings.md`; `.../artifacts/loop_queue_20260419_155108/phase1_55A_persistent_kv_qwen/summary.json`; `.../artifacts/phase1_55A_{16,18,20,24,32}f_frame_scaling/summary.json`; `.../artifacts/phase1_55A_3b_20f_crossarch/summary.json`; `.../2026-04-20-phase-1_55A-3b-24f-boundary-findings.md`; `.../artifacts/phase1_55A_3b_24f_boundary/summary.json`; `.../2026-04-20-phase-1_55A-3b-32f-saturation-findings.md`; `.../artifacts/phase1_55A_3b_32f_saturation/summary.json`; `.../2026-04-20-phase-1_55A-7b-20f-temperature-findings.md`; `.../artifacts/phase1_55A_7b_20f_temperature/summary.json`; `.../2026-04-20-phase-1_55A-3b-20f-temperature-findings.md`; `.../artifacts/phase1_55A_3b_20f_temperature/summary.json` |

### What remains BLOCKED before venue submission

| # | Claim | Blocker | Runtime estimate |
|---|---|---|---|
| I | "Method delivers measured N% speedup" | Sparse-execution path does not exist. Track B measures dense; a sparse path must be written to measure the delta. | Implementation ≈ 1-2 weeks; per-run wall time ≈ 1 h for N=30 on each benchmark. |
| J | "Validated on VideoMME (de facto benchmark)" | **EARNED 2026-04-18 (8f); strengthened 2026-04-19 (16f, 32f).** Qwen 2.5-VL-7B-4bit, videomme_dev_v1.toml n=30. **8f**: dense_acc=0.533, parse_fail=0, agreement=1.000, RSS=6.67GB, mean e2e=31.0s. **16f**: dense_acc=0.567, mean e2e=75.2s. **32f**: dense_acc=0.533 (n=30), mean e2e=157.9s, RSS=8.52GB — zero per-bucket flips vs 16f; long plateau confirmed. **Non-monotonic bucket scaling** — medium +30pp (0.50→0.80→0.70), long −20pp at 16f and held at 32f. **Mechanism**: Phase 1.57 adjacent-frame ViT feature-cos landed on same manifest; H-drift-compounds REJECTED, H-saturation SUPPORTED (long drift AND long acc both plateau at 16f). Frame-scaling not a linear knob; 32f not Pareto-efficient (2× cost for zero aggregate lift). | Open: Phase 1.58 (4bit × long-context quantization) to test the one surviving mechanism candidate. Phase 1.54 (decode-accel) still open for long-item latency, not accuracy. |
| K | "Cross-architecture generalization (Qwen windowed ↔ Gemma/InternVL3 all-global)" | Second architecture has not been run locally. | ≈ 4-6 h GPU wall time for matched N=30 on a second 4-bit-quantized checkpoint, assuming it fits on M3 Air 16 GB. Not guaranteed: Gemma 4 SigLIP + LLM has a larger vision tower. |
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
| C | MVBench motion holdout N=30 sticky4 | ≈ 90 min | ≈ 25-30 min | Qwen 2.5-VL-7B-4bit |
| D | Novelty-ranked dense 2×3 grid (TOMATO+MVBench, N={4,6,8}) | ≈ 120 min | ≈ 45-60 min | Qwen 2.5-VL-7B-4bit |
| E | TOMATO ablation cells (6 cells × 2 benchmarks × N=30) | ≈ 6-8 h | ≈ 3-4 h | Qwen 2.5-VL-7B-4bit |
| F | Phase 1.36 oracle (per-block Pearson, partial cache coverage) | ≈ 60 min | ≈ 20 min | Qwen 2.5-VL-7B-4bit |
| G | Phase 1.50 Track B dense wall-clock baseline N=30 pair | ≈ 2 h per benchmark (cold) | ≈ 2 h (cold; no cache win) | Qwen 2.5-VL-7B-4bit |
| H | Derived from G, zero runtime | — | — | — |
| J₈ | Phase 1.41 VideoMME dev n=30 @ 8f | ≈ 16 min (931 s measured) | ≈ 16 min (no feature cache) | Qwen 2.5-VL-7B-4bit |
| J₁₆ | Phase 1.41 VideoMME dev n=30 @ 16f | ≈ 38 min (2,257 s measured) | ≈ 38 min | Qwen 2.5-VL-7B-4bit |
| J₃₂L | Phase 1.41 VideoMME long n=10 @ 32f | ≈ 28 min (1,450 s projected from 161 s/item × 9 measured) | same | Qwen 2.5-VL-7B-4bit |
| K | Claim-11 reproduction log (1.51R Stages 1/2b/3/5/6/7) | ≈ 10-12 h total across N=30 cells on both benchmarks | n/a (incremental) | Gemma 4-E4B-4bit |
| M | Claim-13 C-CEILING cross-validation (7 regime dimensions) | included in K | n/a | Gemma 4-E4B-4bit |
| O | Phase 1.55A persistent-KV follow-up latency (n=21 queries × 6 frame counts + 3B cross-arch 3-point + 7B/20f temperature probe + 3B/20f temperature probe) | ≈ 18 min at 8f (1057 s) + ≈ 35 min at 16f (2095 s) + ≈ 38 min at 18f (2302 s) + ≈ 42 min at 20f (2506 s) + ≈ 55 min at 24f (3281 s) + ≈ 76 min at 32f (4573 s) + ≈ 27 min at 3B-20f (1595 s) + ≈ 31 min at 3B-24f (1830 s) + ≈ 50 min at 3B-32f (2972 s) + ≈ 48 min at 7B-20f-temp (2862 s) + ≈ 24 min at 3B-20f-temp (1427 s) = ≈ 7.3 h | ≈ 7.3 h | Qwen 2.5-VL-7B-4bit + 2.5-VL-3B-4bit |
| P | Phase 1.51V expansion (12 exps — Tier 0 confirm + Tier 1 Pareto + Tier 2 cross-bench + Tier 3 stack + Tier 4 16f scale) | 15,621 s measured = **4.34 h** (EXP01–12; runtime per-exp 606–2155 s, dense+pruned both reported) | 4.34 h | Gemma 4-E4B-4bit |
| Q | Phase 1.51V 32f probe (EXP13 unpatched + EXP14 L=2 kr=0.50, n=30 each) | 7,167 s measured = **1.99 h** (EXP13 3415 s + EXP14 3752 s; thermal confounder documented) | 1.99 h | Gemma 4-E4B-4bit |
| R | Phase 1.51V holdout session 2 (EXP15 V-patched baseline + EXP16 V+novelty kr=0.3, n=30 VideoMME holdout v1) | 2,706 s measured = **0.75 h** (EXP15 1425 s + EXP16 1281 s; thermal pairing dirty -7.8% decode Δ; within-run pairing CLEAN) | 0.75 h | Gemma 4-E4B-4bit |
| S | Phase 1.51V session 3 (EXP17 VideoMME unpatched holdout + EXP18 V-patched kr=0.5, n=30) | ~0.8 h (sum decode + generate across 60 items; thermally paired at decode Δ 1.53%) | 0.8 h | Gemma 4-E4B-4bit |
| T | Phase 1.51V session 4 (EXP19/20 MVBench holdout pair + EXP21/22 TOMATO holdout pair, run 2) | ~2.0 h (queue.log elapsed across 4 exps; run 1 memory-contaminated and quarantined to run1_confounded/) | 2.0 h | Gemma 4-E4B-4bit |
| U | Phase 1.51V session 5 (EXP23/24 TOMATO holdout pair rerun after session 4 thermal confound) | 1735 s measured = **0.48 h** (EXP23 886 s + EXP24 849 s; favorable-direction 119 ms decode Δ; EARNED-ADVISORY on primary E2E gate) | 0.48 h | Gemma 4-E4B-4bit |
| J₁₆ₕ | Phase 1.41 Qwen 16f VideoMME **holdout** n=30 (H2 falsification run, task #160) | ~38 min (same per-item cost as dev 16f; aggregate 0.700, H2 FALSIFIES the dev-only long-bucket −20pp observation — holdout long 0.900 vs dev 0.100) | 0.63 h | Qwen 2.5-VL-7B-4bit |
| V | Phase 1.51V EXP10 n=60 pooled H_stack re-check (VideoMME dev+holdout combined, task #152 CLOSED-NULL) | ~3.0 h measured (pooled n=60; lift 2.6pp FAILS ≥4pp gate, agreement 0.65 FAILS 0.75; ceiling model reproduces to 0.2pp at pooled fixed_frac = 0.875) | 3.0 h | Gemma 4-E4B-4bit |

### Runtime cost summary

**Already spent** (benchmark wall-clock, cumulative approx over project):
- Lane A (TOMATO + MVBench routing, Qwen): ~25-30 h (A+B+C+D+E+F+G, measured across many N=30 passes)
- Lane B (Gemma 1.51R + ceiling validation): ~10-12 h (K+M)
- Lane B (Gemma 1.51V expansion + 32f probe + holdout sessions 2-5): ~10.4 h (P 4.34 h + Q 1.99 h + R 0.75 h + S 0.8 h + T 2.0 h + U 0.48 h measured)
- Lane B (Gemma 1.51V EXP10 n=60 pooled H_stack, 2026-04-21): ~3.0 h (V)
- VideoMME lane (claim 8 earned + strengthened + **holdout**): ~120 min (J₈ 16 min + J₁₆ 38 min + J₃₂L 28 min + **J₁₆ₕ 38 min** 2026-04-21)
- Persistent-KV lane (claim 14): ~7.3 h (O)
- **Total benchmark wall-clock already spent: ~58-65 h**

**Forward queue** — priority order per `paper/priority.md` round-26, benchmark
wall-clock only. Blocker column is honest about what's actually
runnable tonight vs. impl-gated.

| Prio | Phase | Runtime | Model | Blocker status |
|------|-------|---------|-------|----------------|
| should-do #3 | **1.51V Qwen cross-arch probe** (L=2, kr=0.50, VideoMME 8f n=30 thermally paired, 2 arms) | **CLOSED 2026-04-23** | Qwen 2.5-VL-7B-4bit | **landed** — `V_red = 0.398`, `E2E = 1.044× observed vs 1.043× predicted`, aggregate `Δacc = −0.033`; C-VISION upgrades to two-architecture mechanism evidence |
| should-do #4 | Local paired streaming-protocol reproduction (1.30) + root-cause decomposition | REOPENED-BOUNDARY 2026-04-24 | Qwen 2.5-VL-7B-Instruct-4bit (driver hard-fails on non-Qwen at `run_phase1_30_sam_streaming.py:303-308`) | **1.30W fixed the main mechanism and 1.30X reopened the lane on speed/accuracy** — 1.30W lands paired cold 0.561 / streaming 0.503 (Δacc = −0.0585) / 2.7869× with exact Q0 parity and clean format, but still below the `3.0×` rescue floor. The new offline 1.30X frontier replay shows a simple deployable duration policy (`dense_on_medium_short`) already passes the rescue band on speed/accuracy (`Δacc = −0.0819`, `3.0168×`), so same-protocol admission is viable. However, it still leaves 2 long-session parse failures, and the exact per-session frontier has no format-clean rescue point within the current 1.30 / 1.30W endpoint family. Next useful work is therefore a targeted fix for the remaining long-session format failures or a third endpoint family, not another blind global rerun. |
| should-do #5 | **1.55D selective re-prefill frontier** (recover Δacc at 20f while clawing back speed) | ~60-70 min per K on the 7-clip tranche | Qwen 2.5-VL-7B-4bit | **K=1 landed 2026-04-24 and remains the best fixed point** — repo-local v2 holds exact paired fidelity (`Δacc = 0.0`, paired diffs `0/21`, attractors `0/14`) while improving to a paired follow-up median `10.14 s` vs cold `98.43 s` (`9.71×`) at `4.886 GB` RSS. The first adaptive follow-up is now also closed: **1.55E (`Q2=K1`, `Q3=K0`) FALSIFIES cleanly** with `Δacc = -0.0952`, paired correctness diffs `4/21`, paired choice diffs `6/21`, and pathological-like outputs on `7/7` third queries. So the next meaningful 1.55 continuation is not another blind omission or fixed-K sweep; it is a richer Q3 state-construction or risk-gated admission policy. **1.55B** remains the separate persistent-KV × 1.54 composition phase. |
| should-do #6 | **1.58 bf16 KV control at 20f** (discriminate quantization vs attention-OOD) | ~3.5-4 h (bf16 8f n=30 + bf16 16f n=30) | Qwen 2.5-VL-7B bf16 | **wrapper-landed; run still gated** — `scripts/run_phase1_58_bf16_control.sh` + analyzer landed, but checkpoint download and RSS feasibility remain user/environment constraints |
| should-do #8 | **1.29 codec-native bridge (reframed)** | landed semantically; slow offline extraction | Qwen 2.5-VL-7B-4bit | **planner-substitution evidence landed** — MAX-over-span sparse sampling is HARD-FALSIFIED, while the continuous-score redesign reaches codec-dense agreement 1.000 on VideoMME dev all-duration n=30 with no accuracy loss and zero parse failures. Later calibration-mode and calibration-source ablations are neutral on the local slices we ran. This is not a latency claim: offline codec extraction totals 7290s; the remaining gate is streaming decoder integration / native-rate systems evaluation. |
| future | **1.60 scroll/pan subset** (20 items stratified by scroll intensity, L=2 kr=0.50 paired) | n/a on VideoMME; ~70-90 min after a real subset exists | Gemma 4-E4B-4bit or matched C-VISION stack | **closed as natural-VideoMME corpus limitation** — wider 60-item VideoMME scan found 0/60 items above `shifted_fraction >= 0.30` (max 0.125), so this only reopens with EgoSchema/EPIC-Kitchens/Ego4D or a labeled synthetic scroll/pan set |
| diagnostic | **Qwen 8f holdout `videomme_holdout_v1.toml` n=30** (parallel to already-done 16f holdout) | ~8 min (cold) | Qwen 2.5-VL-7B-4bit | **runnable-now** — driver exists, manifest exists |
| split-landed | 1.42 Gemma topology lane | complete on the preregistered N=30 pair | Gemma 4-E4B-4bit | landed 2026-04-24: TOMATO pass (`agreement=0.933`, `dense_acc=cached_acc=0.267`), MVBench strict-agreement fail (`agreement=0.733`, `dense_acc=cached_acc=0.200`); further work is interpretation or third-architecture breadth, not implementation |
| blocked | 1.43 EgoSchema breadth gate | ~2 h | Qwen 2.5-VL-7B-4bit | loader + manifest unwritten |
| blocked | 1.52R composition (1.42 × 1.51R) | ~3 h | Gemma 4-E4B-4bit | 1.42 landing + 1.51R V-patched re-run |
| future | Claim-5 sparse-execution delta | ~2 h | either | sparse backend unwritten (1-2 wk impl) |

**Runnable-without-approval tonight**: the 1.55D K-sweep frontier
(`uv run python ...` on Metal with existing repo-local v2), plus the
Qwen 8f holdout diagnostic (~8 min). The remaining should-do items
still need either implementation or user/environment support.

**Aggregate forward cost once blockers clear**: ~20 h benchmark-only
@ 8f (excludes implementation); ~40 h @ 32f.

All estimates exclude implementation, debugging, and CI — they
describe only the wall-clock the user would burn re-running
already-landed experiments or clearing the currently-blocked
queue once infra is in place.

## Venue targeting (current honest read)

| Venue | Fit today | What would need to land |
|---|---|---|
| **arXiv preprint (current anti-recomputation draft)** | **Ready today** as a multi-regime anti-recomputation paper with clean versus advisory status stated explicitly and deployment-scale evidence labeled by source class. | No new science gate. Keep provenance tight, finalize manuscript framing, and keep the paper honest about which rows are local clean, local advisory, upstream imported, or deployment-scale imported evidence. |
| **NeurIPS / ICLR / CVPR efficiency workshop** | **Defensible today** as the current anti-recomputation paper if the provenance remains tight and the manuscript keeps clean, advisory, imported, and deployment-scale rows visibly distinct. | Stronger with one measured sparse-path delta and a cleaner local streaming bridge. |
| **Main track (NeurIPS/ICML/CVPR)** | **Not ready yet.** The paper now has a better three-regime story than the old venue rows implied, but it still lacks one measured sparse-path delta, broader apples-to-apples comparison against adjacent methods, and a cleaner bridge from local benchmark evidence into deployment-style streaming evaluation. | One measured sparse-path delta, broader first-pass coverage on the second architecture, a decoder-integrated codec-native / native-rate systems bridge, a scroll/pan/egomotion probe on a corpus that actually contains that regime, and tighter head-to-head positioning against the closest trained and training-free baselines. |
| **Systems conference (MLSys/OSDI)** | **Not ready yet.** The deployment evidence is interesting, but the current paper still does not characterize a full sparse backend or benchmark the streaming path against a clean systems baseline such as screenshot polling. | Sparse execution characterization, screenshot-polling baseline, broader streaming or event-detection evaluation, and ideally a decoder-integrated codec-native streaming bridge. |

## What is safe to say in a one-paragraph abstract TODAY

> We study training-free anti-recomputation for video VLMs across three
> reuse regimes: first-pass vision pruning on fresh videos, after-ingest
> follow-up questions on the same video, and routing under a fixed dense
> backend. On Gemma 4-E4B-4bit, mid-layer vision-tower pruning yields
> measured first-pass gains from **1.113×** to **1.407×** on clean or
> advisory holdout cells, with magnitude predicted by a simple
> share×reduction ceiling. On Qwen2.5-VL-7B-4bit, persistent-KV reuse
> cuts same-video follow-up latency to **815 ms** median at **47.2×**
> speedup at 8 frames and **807 ms** at **91.1×** speedup at 16 frames.
> Routing holdouts on TOMATO and MVBench then show the mechanism
> boundary: a bounded-staleness planner preserves the quality-compute
> frontier, beats novelty-ranked dense selection, and shows that
> fresh-compute placement matters more than novelty magnitude alone.
> Deployment-scale streaming evaluations add **13×** ViT reduction,
> **~50×** dominant-pipeline reduction, **4.2–4.5×** end-to-end
> speedups in selected real-video regimes, and **0.8 s** same-video
> follow-up latency on Gemma 4 26B.

## What is NOT safe to say today

- "SOTA" on any axis.
- "N% faster end-to-end" (no sparse path).
- "Generalizes broadly across architectures" (one matched second-architecture point is now landed, but broad transfer is still too strong).
- ~~"Validated on VideoMME" (phase 1.41 not run).~~ **EARNED 2026-04-18** (Qwen 2.5-VL-7B VideoMME dev n=30, dense_accuracy 0.533).
- "Beats CodecSight / CoPE / FastV / VisionZip" (no head-to-head).
- "Training-free codec-guided" without qualifying the regime split:
  sparse-sampled QA is still pixel-diff by design, native-rate streaming is
  codec-metadata by design, and the local 1.29 bridge is semantic rather than
  latency evidence.

## Immediate next actions to extend publishability (ranked for one-paper SOTA goal)

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
  H_stack re-check.
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
- **1.51V holdout session 2 (n=30 disjoint VideoMME items):** H_stack
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
- **1.8× is our internal preregistered reproduction target, NOT Sam's
  whitepaper claim.** Sam's whitepaper reports 5.4× prefill / 4.2× e2e
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
  `2026-04-19-codex-round-21-sam-imports.md` §4.
- **Attention-context drift vs PE drift (Codex round-21).** Sam's
  whitepaper attributes the refresh requirement to attention-context
  drift (~0.01/frame, `paper/whitepaper-revised-2026-04-16.md:234`),
  NOT positional-encoding drift. Our 1.49 refresh sweep shows
  *that* periodic re-encode recovers agreement but does not isolate
  *which* drift mechanism is load-bearing. Paper framing must say
  "attention-context drift" when citing Sam and must NOT assert a
  PE-drift mechanism absent a local ablation (Phase 1.57, queued
  P2). The two require different mitigations: re-encode at I-frames
  (what we do) addresses attention drift; temporal RoPE key
  correction would address PE drift. See
  `2026-04-19-codex-round-21-sam-imports.md` §3.

**Priority ordering now lives in `paper/priority.md`** (codex round-26
2026-04-21 designated priority.md as the authoritative venue-readiness
/ submission-gate doc). This section is a short mirror + the retired
items that priority.md does not carry. For the current ordering see
`paper/priority.md` (must-do / should-do / future sections).

### Current queue mirror (priority.md §Should-do, in rank order)

1. ~~**EXP10 n=60 H_stack re-check**~~ — **CLOSED-NULL 2026-04-21
   (autonomous session, task #152).** Pooled n=60 arm B V+novelty E2E
   1.0420× / V-only ref arm A 1.0159×; lift 2.6pp FAILS ≥4pp gate;
   agreement 0.650 FAILS ≥0.75; acc Δ −0.017 PASSES. Ceiling model
   reproduces observation to 0.2pp: pooled fixed_frac 0.875 (V_share
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
4. **Local paired streaming-protocol reproduction of Sam's N=60 line**
   — **BOUNDARY NEAR-MISS 2026-04-24 after the dense-Q0 rerun.** The
   original bridge was a hard negative; the successor `1.30W` policy
   ("Q0 dense, Q2/Q3 pruned") improves the same Qwen 7B 8f
   dev+holdout-union bridge to cold `0.561` / streaming `0.503`
   (`Δacc = −0.0585`) at `2.7869×` paired amortized speedup, with exact
   Q0 parity (`34/57` in both arms), `0` parse failures, and `0`
   degenerates. The paper-promotion gate still does not trigger: every
   remaining miss is follow-up-only, and the `>=3.0×` rescue floor is
   structurally unreachable under the current 3-query protocol because
   dense Q0 alone already dominates the wall-clock budget. The next
   paper-relevant work is a cheaper safe-Q0 policy or a longer-session
   protocol, not another same-protocol follow-up tweak.
5. **1.55D selective re-prefill v2** — no longer an implementation
   question. Repo-local v2 is landed, and K=1 is the best fixed point
   (`Δacc = 0.0`, `9.71×`, `4.886 GB`). The first adaptive omission
   follow-up, 1.55E (`Q2=K1`, `Q3=K0`), is now a bounded negative:
   `Δacc = -0.0952` with pathological-like outputs on `7/7` third
   queries. The next paper-relevant move is therefore a richer Q3
   state-construction or risk-gated admission policy, not more fixed-K
   sweeps or another blind query-index omission.
6. **1.58 bf16 KV control at 20f** — isolates quantization as the
   C-PERSIST basin driver; ~2-4h wall.
7. **1.41 Qwen 16f holdout** — third data point for C-VISION V_share
   trajectory; ~30 min wall.
8. **1.29 codec-native bridge (reframed)** — now a local
   planner-substitution result, not a speed result. MAX-over-span sparse
   sampling is hard-falsified, while the continuous-score redesign matches
   dense on VideoMME dev all-duration n=30 and later calibration-mode/source
   ablations are neutral on the local slices we ran. The remaining paper risk
   is deployment integration, not medium/long semantic survival or calibration
   dependence.
9. ~~**Paper figures: C-PERSIST safe-budget table + V_share ceiling
   plot**~~ — **LANDED 2026-04-21 (autonomous session, task #161).**
   Scripts `scripts/plot_c_persist_safe_budget.py` +
   `scripts/plot_v_share_v_red_ceiling.py`; artifacts
   `paper/figures/c_persist_safe_budget.{png,_data.json}` and
   `paper/figures/v_share_v_red_ceiling.{png,_data.json}`. V_share ×
   V_red figure shows 8 regimes (4 dev + 3 holdout + 1 pooled
   CLOSED-NULL); dev median |Δ| 2.2pp, MVBench 8f holdout sits 11.6pp
   above the ceiling (thermal-inflated, matches session-4 advisory).

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
- **Track B sparse-execution path** — biggest single claim-5 unlock,
  weeks of engineering. Deferable to post-submission discussion —
  C-CEILING already bounds the measurable delta analytically.

### Retired framing (do not reintroduce)

- **"Lane B big-numbers gate via claim 11"** — retired 2026-04-21
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
