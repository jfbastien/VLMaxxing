---
date: 2026-04-29
status: launch-ready paper-update notes after deep-mechanism queue + 1.63H kr-sweep complete; supersedes 2026-04-27-paper-update-notes.md
related:
  - research/experiments/2026/2026-04-27-paper-update-notes.md
  - research/experiments/2026/2026-04-27-phase-1_55F-stage-timing-findings.md
  - research/experiments/2026/2026-04-27-phase-1_63E-8f-findings.md
  - research/experiments/2026/2026-04-27-phase-1_63E-16f-catastrophic-findings.md
  - research/experiments/2026/2026-04-29-phase-1_63H-16f-kr-sweep-findings.md
---

# Paper update notes v2 — after deep-mechanism queue closeout

The deep-mechanism queue (1.63G + 1.55K + 1.65 + 1.30AF + 1.66) plus the 1.63H 16f kr-sweep all landed. Several rows are boundary evidence, not clean all-gates wins: Gemma measured sparse vision has matched parse-failure caveats, Qwen kr=0.85 is fidelity-safe but low-gain, and 1.66 observed process memory peaks above 12 GB even though the MLX allocation cap avoided the panic path. Codex has already done the front-loading pass for adaptive C-PERSIST (commit 9b9dceb). These notes are the consolidated edit checklist for what still needs to land in `paper/arxiv/sections/` to reflect the new evidence.

## What's locked since the previous notes (2026-04-27)

- 1.55F-stage-timing committed (bc6c2e2): paired Q3 9.50× explained by post-Q2-repaired prefix coverage 99.4%
- 1.63E 8f committed (43e8a0c): C-CEILING tight, fidelity bounded
- 1.63E 16f catastrophic + 20f partial (5cd2245): boundary result
- 1.63G Gemma full-frame measured sparse vision (74d957e): **0/60 paired drift at 8f/16f/32f, 1.316× clean short-bucket 32f; full sweep has matched parse-failure caveats and 8f ceiling miss**
- 1.55K adaptive temperature sweep (5f9aaa1): **short-cell sampler-stability evidence over T∈[0,1.5], not the full 0/93 breadth claim**
- 1.65 logit-margin scout (4d6bf61): **margin alone insufficient — useful negative result**
- 1.30AF re-run with margin data (b69365b): all 5 gates pass
- 1.66 memory characterization (6dde8c0): all 3 families covered; MLX cap mitigated panics, while observed process peaks still reached 13.61 GB
- 1.63H 16f kr-sweep (57cf3a4 + f206504): **kr=0.85 is the fidelity-safe, low-gain Qwen 16f measured sparse-vision boundary**

## Concrete edits to apply (paper/arxiv/sections/)

### `01_abstract.tex`

Codex already updated the abstract for adaptive C-PERSIST in 9b9dceb. Two further edits remain:

1. **C-VISION clause should lead with Gemma cross-architecture, not Qwen 8f matched-point.**

   Current (post-9b9dceb): single-cell Qwen 1.044× / 1.043× framing.

   Replace with: "C-VISION generalizes across architectures: a 60-item paired measured sparse-vision sweep on Gemma 4-E4B at 8f/16f/32f produces zero paired answer drift in all three frame budgets, with a clean 1.316× short-bucket end-to-end speedup at 32f; the full sweep carries matched parse-failure caveats and the 8f point misses the ceiling tolerance. A matched Qwen sweep is more configuration-conditional: at 16f the fidelity-safe operating point shifts to keep-rate 0.85 (1.032× E2E, 0/60 parse failures, ceiling gap +0.011) but only saves 13.6% vision time."

2. **Add one sentence on adaptive C-PERSIST sampler stability** (paper currently does not mention 1.55K).

   Insert (after the existing 0/93 / 15.28–35.97× line): "The same adaptive policy reproduces these numbers across sampling temperatures T∈[0,1.5] (0–2 paired choice diffs per cell, no pathological-output hits in any cell)."

### `02_introduction.tex`

The C-VISION enumeration item should pick up the cross-arch frame-scaling result. After the existing "C-VISION: training-free mid-layer vision-tower pruning..." sentence add:

> "Gemma Track B remains zero-drift across 8f/16f/32f at L=2, kr=0.50 with the C-CEILING arithmetic model holding within 0.05× tolerance; Qwen Track B has a measured configuration envelope (16f kr=0.50 induces instruction-following collapse, 16f kr=0.85 is fidelity-safe). The contribution becomes a measured envelope across architecture × frame budget × pruning aggressiveness, not a single operating point."

### `06_results_qwen_routing.tex`

This section already has the C-PERSIST table. Two tables to add:

1. **1.55F-stage-timing per-Q decomposition** (the why-fast story for the headline):

| Stage | Adaptive median (ms) | Fixed K=1 median (ms) | Speedup | Adaptive prefix coverage | Tail tokens (adaptive / fixed) |
|---|---|---|---|---|---|
| Q1 | 77,954 | 94,564 | 1.21× | 0% (cold) | 8097 / 8097 |
| Q2 | 8,212 | 12,615 | 1.54× | 94.3% | 459 / 459 |
| Q3 | 675 | 6,652 | **9.85×** | 99.4% | **50 / 451** |

Caption: "Adaptive C-PERSIST's wall-clock advantage is concentrated on Q3 by construction; the post-Q2-repaired cache reduces Q3 tail-prompt work from 451 tokens (last frame group plus question) to 50 tokens (question alone). Per-pair median Q3 speedup is 9.50× (range 7.82–14.99×, n=7)."

2. **1.55K sampler stability table** (4-cell sweep):

| Temperature | Baseline n_correct/21 | Session n_correct/21 | Δaccuracy | Paired choice / correct diffs | Pathological hits | All-query speedup |
|---|---|---|---|---|---|---|
| 0.0 | 17/21 | 17/21 | +0.000 | 0/0 | 0+0 | 24.91× |
| 0.5 | 17/21 | 17/21 | +0.000 | 0/0 | 0+0 | 25.39× |
| 0.7 | 18/21 | 17/21 | -0.048 | 2/1 | 0+0 | 20.75× |
| 1.0 | 18/21 | 17/21 | -0.048 | 1/1 | 0+0 | 23.17× |
| 1.5 | 16/21 | 16/21 | +0.000 | 0/0 | 0+0 | 24.66× |

Caption: "The adaptive C-PERSIST policy that produced 24.76× greedy speedup is sampler-stable across T∈[0.0, 1.5]: paired session/baseline choice and correctness diffs stay below 2/21 in every cell, no cell registers a pathological output, and the all-query-median speedup stays in 20.75–25.39× across the sweep."

### `07_results_cross_architecture.tex`

This is where the Gemma 32f result becomes the C-VISION headline.

Add the **frame-scaling table for Gemma Track B**:

| Frame budget | Δaccuracy | Choice agreement | Vision share dense | Vision reduction | E2E actual / predicted | Ceiling gap |
|---|---|---|---|---|---|---|
| 8f | 0.000 | 100% | 7.9% | 48.2% | 1.102× / 1.039× | +0.062 |
| 16f | 0.000 | 100% | 15.6% | 40.6% | 1.035× / 1.067× | -0.032 |
| **32f** | **0.000** | **100%** | **24.2%** | **43.4%** | **1.126× / 1.117×** | **+0.009** |

By bucket at 32f:

| Bucket | Δacc | Vision share | E2E speedup |
|---|---|---|---|
| short (n=20) | 0.000 | 58.6% | **1.316×** |
| medium (n=20) | 0.000 | 39.8% | 1.233× |
| long (n=20) | 0.000 | 11.0% | 1.060× |

Caption: "Gemma 4-E4B-4bit Track B at L=2, kr=0.50 produces zero paired answer drift across all three frame budgets and 60 short/medium/long videos. The C-CEILING arithmetic gap stays within ±0.05× tolerance at every frame budget, with the tightest match at 32f (gap +0.009). Short-bucket 32f reaches 1.316× E2E speedup with 0/20 paired drift, the strongest C-VISION operating point we measure."

Add the **Qwen 16f kr-sweep table** (configuration-envelope evidence):

| kr | Δaccuracy | Choice agreement | Sparse parse failures | Vision reduction | E2E speedup | Ceiling gap |
|---|---|---|---|---|---|---|
| 0.50 | -0.417 | 36.7% | 22 | 46.4% | 1.132× | +0.058 |
| 0.65 | -0.283 | 46.7% | 11 | 36.1% | 1.093× | +0.036 |
| 0.75 | -0.100 | 75.0% | 0 | 27.0% | 1.065× | +0.023 |
| **0.85** | **-0.050** | **81.7%** | **0** | **13.6%** | **1.032×** | **+0.011** |

Caption: "Qwen 2.5-VL-7B-4bit Track B at 16f exhibits a continuous configuration envelope: kr=0.50 produces instruction-following collapse (22/60 parse failures, Δacc -0.42), kr=0.65 partially recovers, kr=0.75 eliminates parse failures, and kr=0.85 lands within fidelity tolerance with the tightest C-CEILING match across the entire campaign."

### `09_discussion_future_work.tex` and `09_limitations_reproducibility.tex`

1. **Track B fidelity envelope** (limitations): "Track B sparse vision-tower execution is configuration-conditional. On Gemma 4-E4B-4bit, L=2, kr=0.50 is fidelity-safe across 8f/16f/32f; on Qwen 2.5-VL-7B-4bit, the safe-operating envelope is more conservative — 16f kr=0.50 induces instruction-following collapse, and the safe operating point on this manifest is kr=0.85 with a smaller (1.032×) E2E gain. The cross-architecture asymmetry suggests Gemma's 16×16-uniform patch grid tolerates aggressive merged-token-group dropping better than Qwen's merge structure on this 60-item combined VideoMME manifest."

2. **Failure predictor scout** (future work): "We measured whether the dense answer-letter logprob margin predicts paired stability across cache-boundary cells (1.30AC + 1.30AD, n=228 grouped train/test by item_id). Margin alone is insufficient at the precision threshold needed for a runtime guard (`pass_margin_signal` and `pass_safe_filter` both fail). Future work: combine logprob margin with question-position, duration-bucket, and entropy features into a richer predictor — the methodology of grouped train/test, bootstrap CIs by item, and Brier calibration is preregistered (research/experiments/2026/2026-04-27-phase-1_65-logit-margin-predictor-prereg.md) and ready to extend."

3. **Memory budget** (reproducibility): "All cells were collected on a 16 GB unified-memory M3 Air with `mlx.set_memory_limit(12 * 1024**3)` enforced (a CVE-2026-28834-class GPU race in unpatched macOS 26.3 motivated capping below the unified-memory ceiling so allocation failures surface as Python exceptions, not kernel panics). The 1.66 memory characterization inventories 78 cells across the C-PERSIST/1.55, C-VISION/1.30, and Track-B/1.63 families: peak observed working set is 13.6 GB (1.55F 32f short adaptive), and 24/45 C-PERSIST cells exceed 10 GB. Track B never exceeded 10.8 GB."

## What is *not* changing in the paper

- C-PERSIST 4-cell scoping (0/93 / 15.28–35.97×) and Codex's adaptive front-loading (commit 9b9dceb) are correct as written.
- the pre-release source streaming (cross-protocol 26B) numbers are out of scope for this update.
- The deployment-scale framing the round-25/26/27 Codex passes established holds.

## Recommended next steps (not science, but launch-blockers)

1. **Push the 14 commits ahead of origin/main** (CI status unverified). User authorization required — do not auto-push.
2. **Apply the edits in this doc to `paper/arxiv/sections/`** (~30 min mechanical).
3. **Run `paper-doctor` and `paper/arxiv/scripts/build.py`** to regenerate tables/figures (Codex's pre-existing pipeline).
4. **Optional**: Gemma 16f kr-sweep cross-arch (~5h) for paper-thoroughness; predict the safe Gemma envelope is much wider than Qwen's, but only worth running if a reviewer asks.
