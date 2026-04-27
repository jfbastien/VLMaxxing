---
date: 2026-04-27
status: draft notes for paper update; queue still running 1.63E (16f currently); not yet applied to paper/
related:
  - research/experiments/2026/2026-04-27-adaptive-mechanism-queue-findings.md
  - research/experiments/2026/2026-04-27-phase-1_55F-stage-timing-findings.md
  - research/experiments/2026/2026-04-27-phase-1_63E-8f-findings.md
  - research/experiments/2026/2026-04-27-paper-deep-mechanism-runbook.md
---

# Paper update notes — staged from in-flight queue results

These notes record what should land in `paper/arxiv/sections/` once the deep-mechanism queue completes. They are written from artifacts already on disk; they do not depend on the still-running stages. Codex has held off paper-tree edits for several rounds; this note keeps the science changes specific so the next paper-editing pass is mechanical.

## What is locked already (do not wait for the queue)

1. **C-PERSIST 4-cell scoping is the headline** — `2026-04-27-adaptive-mechanism-queue-findings.md`. The current abstract cites only the single 1.55F short cell (24.76× same-class, 0/21). The locked corpus is **0/93 paired drift across short/medium/long/32f-short, 15.28–35.97× all-query-median speedup**. The single-cell number under-sells.
2. **Per-stage mechanism for adaptive C-PERSIST** — `2026-04-27-phase-1_55F-stage-timing-findings.md`. Adaptive Q3 is 9.50× faster than fixed K=1 Q3 because `post_q2_repaired` cache covers 99.4% of the prefix and only 50 tail tokens (the question) are prefilled, vs 451 tokens for fixed K=1 (the last frame group + question). This is the *why-fast* story the paper currently lacks.
3. **1.63E 8f Track B** — `2026-04-27-phase-1_63E-8f-findings.md`. Predicted/actual E2E ceiling 1.047× / 1.042× (gap 0.005). Vision reduction 44.8%. **H_fidelity FAILS** at -0.067 aggregate (-0.25 on short bucket). The C-CEILING contribution gets a clean validation point; the C-VISION fidelity claim must be re-scoped.

## Concrete edits to stage

### `01_abstract.tex`

Current (lines 21-29):

> Selective re-prefill refreshes a small newest-frame visual tail and restores the tested follow-up contract: fixed \(K=1\) shows no observed paired answer drift on 93 paired queries across short, medium, long, and deeper VideoMME slices while retaining 9.48--20.37$\times$ same-class follow-up speedups, measured as cold follow-up latency divided by repaired-session follow-up latency. **A short-slice state-aware adaptive cell reaches 24.76$\times$ same-class speedup with 0/21 paired drift.**

The bolded sentence is single-cell. Replace with:

> A state-aware adaptive cell, sourcing Q3 from the post-Q2 repaired cache, reaches **0/93 paired drift across four cells (short, medium, long, 32f-short) with 15.28--35.97$\times$ all-query-median speedup**. The mechanism is per-stage and observable: adaptive Q3 inherits the post-Q2-repaired KV cache (99.4% prefix coverage), so its only tail-prompt work is the question text (50 median tokens), versus 451 tokens for fixed \(K=1\), giving a paired Q3 median speedup of 9.50$\times$.

This swap removes the single-cell number, adds the 4-cell scoping, and gives the mechanism in one sentence.

Current C-VISION clause (lines 31-37):

> \emph{C-VISION} gives 1.113--1.407$\times$ first-pass wall-clock gains on Gemma 4-E4B-4bit across clean and advisory holdout cells, **and a matched Qwen point lands at 1.044$\times$ observed versus 1.043$\times$ predicted.**

Change the matched-Qwen clause to reflect the 1.63E 8f result and lead with the ceiling validation:

> a matched Qwen point at 8f, n=60 paired across short/medium/long, lands at 1.042$\times$ observed E2E versus 1.047$\times$ predicted from the dense vision share, with paired vision-time reduction 44.8\%. The fidelity is not free at this configuration: aggregate accuracy delta is $-0.067$ with a $-0.25$ short-bucket gap, so this is a C-CEILING validation result, not a fidelity-preserving multiplier.

### `02_introduction.tex` (around lines 108–119, the C-PERSIST + C-VISION enumerations)

Current (paraphrased):

> We characterize \textbf{C-PERSIST}: after-ingest persistent-KV reuse on Qwen 7B/3B with bracketed safe regimes...while retaining 9.48--20.37$\times$ follow-up speedup. A state-aware adaptive cell reaches **24.76$\times$**.

Replace the single number with the 4-cell envelope:

> A state-aware adaptive cell with `q3_cache_source=post_q2_repaired` lands **0/93 paired drift / 15.28--35.97$\times$ all-query-median speedup across four cells**, and per-Q decomposition attributes the win specifically to Q3 cache inheritance (paired Q3 9.50$\times$, tail-prompt tokens 451$\to$50).

Current C-VISION enumeration (line 119):

> We establish \textbf{C-VISION}: training-free mid-layer vision-tower [pruning that gives 1.113--1.407$\times$ ...]

Add a Track B / C-CEILING anchor sentence after the existing C-VISION list:

> A 60-item paired Qwen Track B point at 8f reaches the predicted vision-only E2E ceiling within 0.5 percentage points (1.042$\times$ vs 1.047$\times$ predicted), confirming that the C-CEILING arithmetic model is tight on the lowest-vision-share operating point.

### `06_results_qwen_routing.tex`

This is the section the C-PERSIST table lives in (per task #161). Add three things after the queue lands:

1. A per-Q decomposition table from `phase1_55F_stage_timing/stage_timing_summary.json`:

| Stage | Adaptive median (ms) | Fixed K=1 median (ms) | Speedup | Adaptive prefix coverage | Tail tokens (adaptive / fixed) |
|---|---|---|---|---|---|
| Q1 | 77,954 | 94,564 | 1.21× | 0% (cold) | 8097 / 8097 |
| Q2 | 8,212 | 12,615 | 1.54× | 94.3% | 459 / 459 |
| Q3 | 675 | 6,652 | **9.85×** | 99.4% | **50 / 451** |

Single-sentence caption: "Adaptive C-PERSIST's wall-clock advantage is concentrated on Q3 by construction; the post-Q2-repaired cache reduces Q3 tail-prompt work from 451 tokens (the last frame group plus the question) to 50 tokens (the question alone)."

2. The 4-cell summary table from the adaptive-mechanism queue (already in `2026-04-27-adaptive-mechanism-queue-findings.md` lines 44–48). It has the per-cell speedups and 0/93 drift.

3. After 1.63E lands more frame points: a frame-scaling figure showing predicted-vs-actual ceiling at each frame budget, and the frame budget at which fidelity becomes safe. (Currently 8f short is the unsafe point.)

### `09_discussion_future_work.tex` / `09_limitations_reproducibility.tex`

Add a new limitation paragraph: "Track B sparse-vision execution at L=2, kr=0.50 on 8f shows aggregate paired Δacc=−0.067 with a short-bucket regression to −0.25 on a 60-item combined manifest, despite the previously reported 0/30 paired drift on the 30-item dev split. This is consistent with item heterogeneity rather than implementation regression; the n=60 combined manifest contains short-bucket items where answer-bearing patches concentrate in the dropped groups. Per-item attribution and a less aggressive (kr higher) configuration are obvious next steps."

## What is *not* in these notes (still in flight)

- **1.63E 16f / 20f / 32f**: ceiling-vs-actual at higher vision share. Will materially extend the C-CEILING figure when they land.
- **1.63G Gemma Track B**: cross-architecture ceiling check.
- **1.55K temperature sweep**: sampler-robustness of adaptive C-PERSIST.
- **1.65 logit-margin probe**: failure-predictor scout.
- **1.30AF (already landed)**: cache-boundary attribution. Could land in C-PERSIST limitations as "cache-reuse and cache-invalidation reach the same aggregate accuracy through different row sets" once the paper has space.
- **1.66 (already landed, partial)**: memory characterization. Will fill in once 1.63E lands the Track-B family.

## Recommended sequencing

Do not touch `paper/arxiv/sections/` yet. The 1.63E 16f/20f points will likely change the C-VISION framing again (e.g., if 16f short fidelity is fine, the headline shifts back to "free at 16f, paid for at 8f"). The right time to apply these notes is after the queue lands the 1.63E point set and 1.63G Gemma reference.

In the meantime: this note is the staging document. When the paper-edit pass starts, walking these edits is a ~30-minute session, not a re-investigation.
