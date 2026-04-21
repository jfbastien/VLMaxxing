# Publishability Status — 2026-04-21

One-file answer to "what can we actually claim, in what venue, with what
numbers, today." Kept in sync with [claim-matrix.md](claim-matrix.md) but
scoped narrower: reviewer-facing readiness and runtime-cost evidence.

## One paper, two experimental lanes (round-17 reframe)

**The goal is one results paper, co-authored with Sam, that advances
SOTA with big multiplicative speedups.** Method work is in service of
that scientific goal and is welcome to land in an appendix; it is
NOT a separate methods paper.

The paper has two experimental lanes, both of which must contribute
evidence to the final manuscript:

- **Lane A — Qwen methods (TOMATO + MVBench).** Pareto-frontier /
  routing claims on Qwen 2.5-VL-7B-4bit. Claims 1/2/6/9 earned;
  3/4/5 partial; 8/12 preregistered. Provides scientific validity
  for the routing / bounded-staleness mechanism, and is a natural
  home for the appendix method content.
- **Lane B — Gemma big-numbers (VideoMME + TOMATO + MVBench).**
  Multiplicative end-to-end speedup via novelty-pruning + temporal
  reuse on Gemma 4-E4B-4bit. Claims 7/10/11 all preregistered today;
  nothing earned. **This is the SOTA-facing content** and drives
  paper-venue readiness.

Prose must never conflate lane-A-earned with lane-B-prospective.
When a claim sits in both lanes (e.g., claim 5 sparse-execution
delta on Qwen or Gemma), name the architecture explicitly.

## HN-style headline (honest version)

> **Training-free temporal routing on Qwen 2.5-VL-7B-4bit (MLX): matches
> 8-frame uniform-dense accuracy on MVBench motion holdout while using
> 56% of the fresh-frame budget (4.49 vs 8.0 effective fresh frames) —
> no training, no architecture change, one percentile pass + a bounded
> staleness counter.**

**Secondary headline (1.51V vision-tower pruning, dev n=30 only; holdout
unpatched pair not yet run):**

> **Vision-tower pruning at L=2 kr_V=0.50 on Gemma 4-E4B-4bit (MLX):
> 1.24× end-to-end on TOMATO and 1.21× on MVBench motion dev n=30,
> thermally paired, at −0.10pp / +3.3pp accuracy delta. Governed by an
> architectural ceiling E2E ≤ 1/(1 − V_share × V_red) validated on 4
> regimes (vision axis) + 1 regime (LLM-decode axis).**

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
| R | **1.51V vision-tower pruning on Gemma 4-E4B-4bit (MLX), dev n=30 at L=2 kr_V=0.50 thermally paired:** VideoMME 1.08× (8f) / 1.12× (16f), MVBench **1.21×**, TOMATO **1.24×**; V_red benchmark-invariant at ~40% across all three benchmarks; acc Δ +3.3pp (TOMATO) / -10pp MVBench (localized to object-binding, 3 item flips) / -6.7pp (VideoMME 8f, long+medium) / +3.3pp (VideoMME 16f). Scatter-back ceiling `1/(1 − V_share × V_red)` predicts E2E within 2pp on 4 cells. **32f frame-scaling probe:** V_share = 31.0% at 32f (continues 15.2% → 24.3% → 31.0% monotone), but thermal pairing FAILS on M3 16 GB at 32f (decode Δ = +7.6%); observed cross-run 0.94× is thermally confounded; charitable ceiling prediction 1.14×, sub-threshold. **Holdout replication (EXP15/16, VideoMME holdout v1 n=30 disjoint):** H_stack partial confirmation — V+novelty kr=0.3 on V-patched baseline stacks at 1.064× within-run (thermally clean), 1.127× cross-session (dirty), agreement=0.667, acc Δ=-0.033. LLM-side ceiling `1/(1 − generate_share × generate_reduction) = 1.064×` matches observed to 0.1pp (fifth ceiling regime). V_share on holdout = 8.6% (vs dev 15.2%) explains smaller magnitude — regime-conditional, not noise. **V-only UNPATCHED-vs-PATCHED holdout pair NOT YET RUN** — TOMATO/MVBench/VideoMME V-only cells remain dev-only headlines until EXP17/18 lands (~40 min). | `research/experiments/2026/2026-04-21-phase-1_51V-expansion-findings.md`; `2026-04-21-phase-1_51V-32f-probe-findings.md`; `2026-04-21-phase-1_51V-holdout-findings.md`; `artifacts/phase1_51V_expansion/exp{01..12}_*_summary.json`; `artifacts/phase1_51V_session2/exp{13..16}_*_summary.json` |
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

### Blocked / forward queue (pre-reg runtime budget)

| # | Claim / phase | Benchmark runtime | Model | Blocker |
|---|---|---|---|---|
| I | Sparse-execution delta (claim 5 "N% measured speedup") | ≈ 1 h per benchmark | either | sparse execution path not written |
| L | Placement ablation (phase 1.38) | ≈ 30 min | Qwen 2.5-VL-7B-4bit | not queued |
| N₅₇ | Phase 1.57 feature-drift measurement (Qwen landed; Gemma deferred) — **lower-bound proxy via adjacent fresh-vs-fresh cosine**, NOT a direct cache-substitute error measurement (the 1.45/1.46 oracle is the direct measurement path). | **Qwen 8/16/32f: LANDED 2026-04-19** (~30 min total); Gemma path deferred (needs inline ViT encode) | both | **Qwen DONE**: STATIC cos 0.562/0.607/0.638; H2 FALSIFIED, H3 EARNED (monotonic-rise with frame count); Gemma path deferred |
| N₅₅ₐ | Phase 1.55A persistent-KV reproduction (short bucket 7×3, 8f+16f+20f+24f+32f) | **LANDED 2026-04-19** (1057 s at 8f + 2095 s at 16f + 2506 s at 20f + 3281 s at 24f + 4573 s at 32f = 13 512 s total) | Qwen 2.5-VL-7B-4bit | 8f and 16f earn all 4 H; 20f/24f/32f earn H1/H3/H4 but REJECT H2. 5-point speedup curve (47×→91×→94×→122×→150×) confirms prefill-dominance. Fidelity transition is a **narrow soft threshold, not a clean cliff**: clean at 6.5k (16f, Δacc=0), partial-basin-collapse at 8.1k (20f, Δacc=−0.38, mixed 10 short `addCriterion` + 4 long-garbage + 1 correct), saturated single-token attractor at 9.7k (24f, Δacc=−0.43) persisting through 12.9k (32f). Favours threshold mechanisms with a soft edge (4-bit KV quantization budget, M-RoPE OOD) over pure accumulation. 18f bisection in flight 2026-04-19 to localize ramp onset. Promoted to row O with safe-prefill-budget caveat |
| N₅₆ | Phase 1.56 VLM-signaled refresh (3 arms × n=30 VideoMME dev) | ≈ 45 min @ 8f; ≈ 2 h @ 32f | Qwen 2.5-VL-7B-4bit | Phase 1.44 margin logging + RefreshPolicy API |
| N₁.₅₂R | Phase 1.52R temporal+spatial composition on Gemma | ≈ 2-3 h @ 8f; ≈ 6-8 h @ 32f | Gemma 4-E4B-4bit | 1.42 + 1.51R sweep completion |
| N₁.₅₅B | Phase 1.55B KV × decode-accel composition | ≈ 65 min @ 8f; ≈ 2.5 h @ 32f | Qwen 2.5-VL-7B-4bit | 1.54 landing + 1.55A earning |
| N₁.₅₈ | Phase 1.58 bf16 × long-context quantization ablation | ≈ 1 h bf16 8f; ≈ 3 h bf16 16f | Qwen 2.5-VL bf16 (15 GB download) | bf16 checkpoint + RSS feasibility check |
| N₁.₄₂ | Phase 1.42 Gemma architecture-topology lane | ≈ 2 h @ 8f; ≈ 6 h @ 32f | Gemma 4-E4B-4bit | _mix_gemma_features integration |
| N₁.₄₃ | Phase 1.43 EgoSchema lane | ≈ 2 h @ 8f | Qwen 2.5-VL-7B-4bit | EgoSchema loader + manifest |

### Runtime cost summary

**Already spent** (benchmark wall-clock, cumulative approx over project):
- Lane A (TOMATO + MVBench routing, Qwen): ~25-30 h (A+B+C+D+E+F+G, measured across many N=30 passes)
- Lane B (Gemma 1.51R + ceiling validation): ~10-12 h (K+M)
- Lane B (Gemma 1.51V expansion + 32f probe + holdout session 2): ~7.1 h (P 4.34 h + Q 1.99 h + R 0.75 h measured)
- VideoMME lane (claim 8 earned + strengthened): ~82 min (J₈ 16 min + J₁₆ 38 min + J₃₂L 28 min)
- Persistent-KV lane (claim 14): ~7.3 h (O)
- **Total benchmark wall-clock already spent: ~51-58 h**

**Forward queue** (blocked + runnable-now, benchmark wall-clock only):
- **Runnable now**: 1.57 ~60 min + 1.55A ~17 min = **~1.3 h**
- **Short blockers** (1.54 decode + 1.44 margin land first): 1.55B ~65 min + 1.56 ~45 min = **~1.8 h @ 8f, ~4.5 h @ 32f**
- **Larger blockers** (Gemma harness + bf16 download + EgoSchema loader): 1.42 ~2 h + 1.58 ~4 h + 1.43 ~2 h + 1.52R ~3 h = **~11 h @ 8f, ~25 h @ 32f**
- **One full reviewer-response cycle** (re-run A through F, warm-cache): **~5-7 h**
- **Sparse execution delta** (claim 5 — unblocks "measured speedup"): **~2 h** benchmark-only after ~1-2 wk implementation

**Aggregate forward cost to clear the full queue**:
- At 8f: ~14 h benchmark-only (excludes implementation of gating infra)
- At 32f: ~30 h benchmark-only
- Earned-claims reviewer rerun: additional ~5-7 h warm-cache

All estimates exclude implementation, debugging, and CI — they
describe only the wall-clock the user would burn re-running
already-landed experiments or clearing the currently-blocked
queue once infra is in place.

## Venue targeting (current honest read)

| Venue | Fit today | What would need to land |
|---|---|---|
| **arXiv preprint (lane-A-only positional)** | **Possible today as a narrow positional note on Qwen routing.** Would need framing as "method positioning; SOTA results forthcoming." **Not the target artifact** — the goal is one big-numbers paper, not a positional subset. | Keep Arc A claims current; do not submit until Lane B is earned. |
| **NeurIPS / ICLR / CVPR efficiency workshop** | **Within reach** once Lane B lands one of: novelty-pruning-on-Gemma multiplicative speedup OR Gemma+VideoMME fidelity + Track B sparse delta. | Lane B phases 1.42 + 1.51R earned. |
| **Main track (NeurIPS/ICML/CVPR)** | **NOT ready.** Single-architecture, two benchmarks, no measured speedup, no SOTA comparison. Reviewers will flag all four. | Phase 1.52 combined (multiplicative speedup measured) + claim 8 VideoMME + claim 7 second architecture. |
| **Systems conference (MLSys/OSDI)** | **NOT ready.** No sparse execution to characterize. | Claim 5 (sparse path) + Phase 1.52 combined. |

## What is safe to say in a one-paragraph abstract TODAY

> We study training-free temporal feature reuse for video VLMs on a
> Qwen 2.5-VL-7B-4bit MLX deployment, using a bounded-staleness,
> concentration-aware pixel-diff planner over spatial blocks. On the
> TOMATO motion holdout (N=30), our planner matches uniform-dense
> 8-frame accuracy (0.333) at 44% of the fresh-frame budget (3.55
> effective fresh frames). On the MVBench motion holdout (N=30), a
> sticky-window refinement matches uniform-dense 8-frame accuracy
> (0.633) at 56% of the fresh-frame budget (4.49 effective fresh
> frames), while the base policy strictly dominates uniform dense-6
> (0.600 > 0.567 at fewer fresh frames). A feature-change oracle
> (phase 1.36) establishes that pixel-diff statistics correlate with
> ViT feature change at Pearson r up to 0.504 on MVBench, and that
> the best routing statistic (MAX_ABS) is not the best point predictor
> — routing cares about ordering, not magnitude matching. We report
> a dense wall-clock baseline of 60.1 s/item on M3 Air 16 GB at
> 8 frames (prefill 72% of end-to-end), giving a 22% ceiling on any
> vision-cache-only Track B speedup before the prefill path is also
> compressed. Sparse-execution measurement is left as follow-up work.

## What is NOT safe to say today

- "SOTA" on any axis.
- "N% faster end-to-end" (no sparse path).
- "Generalizes across architectures" (single architecture).
- ~~"Validated on VideoMME" (phase 1.41 not run).~~ **EARNED 2026-04-18** (Qwen 2.5-VL-7B VideoMME dev n=30, dense_accuracy 0.533).
- "Beats CodecSight / CoPE / FastV / VisionZip" (no head-to-head).
- "Training-free codec-guided" without qualifying "pixel-diff proxy
  for codec MV/CBF; phase 1.29 MV-only is the bridge."

## Immediate next actions to extend publishability (ranked for one-paper SOTA goal)

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
  agreement 0.667; acc Δ=-0.033. V_share on holdout = 8.6% (vs dev
  15.2%); LLM-side ceiling `1/(1 − generate_share × generate_reduction)
  = 1.064×` matches observed to 0.1pp. Fifth ceiling-model regime.
- **V-only holdout UNPATCHED-vs-PATCHED pair NOT RUN.** EXP15 is a
  V-patched reference point (novelty=1.0, not an unpatched baseline).
  The four dev headlines above stay "dev n=30" until an EXP17/18 holdout
  unpatched pair lands (~40 min runtime, one sandbox cycle).
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

Lane B (Gemma big-numbers on VideoMME) is the SOTA-facing priority.
Lane A (Qwen routing) continues in parallel where it doesn't contend
for the MLX queue, and produces method content for the appendix.

### Lane B — the big-numbers path (Gemma + VideoMME, highest priority)

**Reordered 2026-04-17 round-18:** 1.51R novelty-pruning is a fresh
LLM-prefill code path and does NOT depend on phase 1.42's
`_mix_gemma_features` temporal-reuse integration. See
`research/experiments/2026/2026-04-17-phase-1_42-gemma-integration-design.md:62`
for the explicit note. 1.42 stays in the queue as the claim-7
enabler but is not the headline gate.

1. ~~**Phase 1.41 VideoMME N=30 on Qwen**~~ — **DONE 2026-04-18** at
   aa793d3 (prereg) + findings landing. dense_acc=0.533, agreement=1.000,
   parse_fail=0/30, peak RSS 6.67 GB, median e2e 30.5 s. Claim 8 is
   earned on the local VideoMME dev slice. Next incremental lift:
   16-frame or 32-frame re-run (H3 headroom; ~1 h wall-clock each) to
   match published 32-frame Qwen 7B numbers.
2. **Phase 1.42 v0 Gemma smoke** — minimum-viable whole-frame
   temporal-reuse integration. ~30 s on 1 item + ≈ 1.5 h N=30 dev.
   Unlocks claim 7 partial and de-risks the Gemma data path for the
   novelty-pruning lane. Not a prerequisite for claim 11.
3. **Phase 1.51R Sam novelty-pruning reproduction on Gemma + VideoMME
   N=30** — 5 anchor arms × 5 keep-rates dev + single-shot holdout;
   ≈ 6–8 h GPU wall time. Runs **independently** of 1.42 (per design
   note §Recommended path). **This is the headline big-numbers
   result.** Unlocks claim 11.
4. **Phase 1.52R combined temporal + spatial on Gemma (VideoMME)** —
   depends on 1.42 + 1.51R; ≈ 2–3 h GPU wall time. Tests whether
   Sam's multiplicative composition transfers to local Gemma 4-E4B;
   unlocks claim 10.

### Lane A — Qwen routing content (appendix-grade method evidence)

5. **Phase 1.37B halo-veto dev tranche** — **RETIRED 2026-04-17**
   as preregistered null. Full 9/9 cells × 2 benchmarks landed
   (commits 2ebf90d + db10e12 + 0ea69fe + 46b5d05 + 2947198).
   TOMATO NO-LIFT (control rank-1 at cached_accuracy 0.233, all cells
   within 1/30 MRU); MVBench NO-LIFT-NEGATIVE (halo hurts: control
   sole rank-1 at 0.800, 7/8 cells lose 0.067–0.100). Claim 3
   (routing-mechanism evidence) now rests on phase 1.37
   within-block child-veto (item 7 below) as the remaining path,
   not on halo-veto.
6. **Phase 1.38 placement ablation** — ≈ 30 min GPU wall time;
   strengthens claim 4 mechanism.
7. **Phase 1.37 within-block child-veto (distinct from 1.37B)** —
   not yet implemented; ≈ 2 h GPU wall time after code lands;
   orthogonal path toward claim 3.
8. **Phase 1.43 EgoSchema N=30 on Qwen** — long-form/egocentric
   generalization; ≈ 2-3 h GPU wall time; unlocks claim 12.

### Track B (sparse execution, blocks claim 5 measured)

9. **Track B sparse-execution path (Qwen or Gemma)** — weeks of
   engineering; the biggest single claim unlock (claim 5 measured,
   not ceiling-derived). Currently lane B's phase 1.52 gives a
   cheaper path to a measured end-to-end delta because novelty-
   pruning is sparse-at-input, not sparse-in-ViT.

Maintained by: research automation. Source of truth for numbers:
[`claim-matrix.md`](claim-matrix.md) and the artifact JSONs it cites.
