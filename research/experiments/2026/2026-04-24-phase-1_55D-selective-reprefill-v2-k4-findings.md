# Phase 1.55D v2 — Selective re-prefill K=4 (FINDINGS)

**Date:** 2026-04-24.
**Parent:** `2026-04-20-phase-1_55D-selective-reprefill-prereg.md`.
**Verdict:** **fidelity-recovery earns; deployment-speed gate fails.**

## What changed from v1

The earlier v1 driver was infrastructure-falsified because it relied on
mlx-vlm's `PromptCacheState.find_prefix_length` to trim inside the image
block, and the stock multimodal path did not co-slice
`pixel_values` / `image_grid_thw` / `attention_mask`.

The v2 path is different and repo-local:

- it computes the truncation boundary explicitly,
- slices the Qwen image/text tail explicitly,
- builds the reusable prefix KV cache explicitly,
- continues the tail with explicit position IDs,
- rewinds the prefix cache between follow-up queries.

One additional repo-local bug surfaced during the first v2 smoke:
`model.language_model(...)` returns `LanguageModelOutput`, not a raw
tensor. Commit `d6f9354` fixed that adapter and added a unit test. After
that fix, the one-clip smoke and the full K=4 tranche both completed on
the intended multimodal partial-prefix regime.

## K=4 pilot setup

- Model: `Qwen2.5-VL-7B-Instruct-4bit`
- Regime: 20-frame persistent-KV short-bucket VideoMME session
- Clips: `037,100,116,120,158,160,210`
- Queries: 3 per clip, session path vs matched cold baseline
- Output dir:
  `research/experiments/2026/artifacts/phase1_55D_selective_reprefill_v2/`

## Headline results

From `summary_k4_n7.json`:

- `session_accuracy = 17/21 = 0.8095`
- `baseline_accuracy = 17/21 = 0.8095`
- `accuracy_delta_session_minus_baseline = 0.0`
- `session_follow_up_accuracy = 11/14 = 0.7857`
- `session_follow_up_median = 28.976 s`
- `baseline_median = 105.933 s`
- median speedup vs cold baseline `= 3.66×`
- mean follow-up prefix coverage `= 0.7947`
- `peak_rss_gb = 5.040`

Most importantly:

- **per-item correctness diffs = 0/21**
- **pathological attractor count on follow-ups = 0/14**

So K=4 does not merely improve the basin; it removes the observed
`addCriterion` / `自动生成` collapse entirely on this tranche.

## Preregistered verdicts

### H1-1.55D.K=4 (fidelity recovery)

**EARNED.**

The preregistered target was `Δacc <= -0.15` relative to cold baseline.
Observed `Δacc = 0.0`.

This is stronger than the prereg target: selective re-prefill K=4
recovers the entire 7-clip short-bucket tranche to baseline accuracy.

### H2-1.55D (speedup floor)

**FALSIFIED.**

The preregistered target was follow-up median `<= 15 s` and speedup
`>= 10×`.

Observed:

- follow-up median `= 28.976 s`
- speedup `= 3.66×`

So K=4 is a fidelity-recovery lever, but not yet a deployment-grade
speedup lever on this local Qwen 7B regime.

### H3-1.55D (basin dispersal)

**EARNED strongly.**

The preregistered target was reducing pathological-attractor prevalence
from `13/14` to `<= 4/14`.

Observed pathological-attractor prevalence on session follow-ups:

- `0/14`

This is the cleanest scientific result in the run. The v2 path does not
merely "soften" the basin; it eliminates it on the pilot tranche.

### H4-1.55D (peak RSS)

**NARROW FAIL.**

The preregistered target was `<= 5 GB`.

Observed:

- `peak_rss_gb = 5.040`

That is only ~40 MB above the gate, but by the preregistered rule it is
still a fail.

## Interpretation

K=4 establishes that the 20f Qwen 7B basin is recoverable by an
**upstream visual-prefix intervention**. That directly supports the
causal story from phase 1.55A:

- the failure is not sampler-only,
- the failure is not irrecoverable once the long-tail cache is altered,
- re-prefilling the last four frames is enough to restore the answer
  distribution to the cold-start manifold on this tranche.

What K=4 does **not** establish is a strong systems win. The follow-up
latency remains in the tens of seconds, not the sub-15-second regime
needed for the preregistered deployment lever.

So the honest conclusion is:

> Selective re-prefill works as a fidelity-recovery mechanism, but K=4
> pays too much latency to be the final deployment recipe on local Qwen
> 7B.

## Consequence for the next run

The next frontier point should be **K=2**, not K=8.

Reason:

- K=4 already earns H1 exactly, so a larger `K` is unlikely to change
  the scientific story on fidelity.
- H2 fails badly at K=4, so the next informative question is whether a
  smaller tail can preserve most of the recovery while materially
  improving speed.

If K=2 keeps `Δacc` within the preregistered partial-recovery band while
lifting the speedup substantially above `3.66×`, then 1.55D becomes a
genuine recovery-speed frontier instead of a single-point rescue.
