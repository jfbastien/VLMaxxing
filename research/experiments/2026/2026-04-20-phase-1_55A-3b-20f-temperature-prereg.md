# Phase 1.55A-3B-20f — Temperature probe (PREREG)

**Date:** 2026-04-20. **Status:** preregistration.
**Parent phase:** 1.55A (reopened briefly per reopen-condition on
failure-geometry dimension — cross-arch mirror of 7B/20f temperature
probe).

## Why reopen 1.55A

Phase 1.55A was declared closed 2026-04-20 after the 7B/20f
temperature probe earned H-distribution-collapse. The closure note
explicitly deprioritized a 3B temperature mirror because "3B's ceiling
is shallow (Δacc ≈ −0.19) and the mechanism-mapping budget has been
spent."

**Reopen justification:** the 3B failure geometry (clean 2-token
letter drift across A/B/C/D) looks structurally like greedy-argmax
committing on a softly-perturbed distribution rather than
distribution-level collapse. The 7B temperature probe resolved that
question ONLY for 7B. The 3D decomposition's third dimension (failure
geometry) is architecture-specific, but whether it is
**sampler-specific on 3B** is unanswered. A single ~30-min probe
closes the last open mechanistic question about the 3B ceiling.

If H-3B-distribution-collapse earns, both architectures' failure
geometries are distribution-level (the mechanism is symmetric across
ceilings). If H-3B-greedy-commit earns, the two architectures differ
in a fourth orthogonal dimension (sampler sensitivity), which is
paper-relevant.

## Setup

- **Model:** `Qwen/Qwen2.5-VL-3B-Instruct-4bit` (4-bit MLX weights).
- **Frame count:** 20 frames/clip (matches 3B 20f baseline +
  3B 20f cross-arch + 7B 20f temperature — cleanest apples-to-apples
  comparison across all three runs).
- **Driver:** `scripts/run_kv_cache_session.py` (unchanged since the
  temperature-flag landing; already supports 3B via `--model`).
- **Clips:** same 7 VideoMME dev clips as 3B 20f baseline, 3 queries
  per clip → 21 total queries × 2 modes (session + baseline) = 42
  generations.
- **Sampling (temperature condition):** `--temperature 0.7 --top-p
  1.0 --min-p 0.05 --seed 42` — matches 7B temperature probe exactly.
  Sampling params written to summary.json under `"sampling"` block.
- **Reference:** 3B 20f cross-arch greedy run
  (`phase1_55A_3b_20f_crossarch/summary.json`) — session 12/21,
  baseline 13/21, Δacc −0.048, 14/14 clean-letter follow-ups.

## Hypotheses

**H1-3B-temp.** Median follow-up latency ≤ 0.6 s (3B is faster than
7B; must clear the same speedup gate vs first-query ≥ 80×).
**Falsification:** median > 0.6 s OR speedup < 80×.

**H2-3B-temp (two-arm sub-outcome framework).**
The 3B cross-arch greedy run already earned H2-3B.matched
(Δacc = −0.048) — accuracy lost to cache reuse is statistically zero
on 3B at 20f prefill. The temperature probe measures whether THAT
null result is also sampler-invariant:

- **H2-3B-temp.null-robust (expected if 3B follow-ups are
  distribution-level clean):** Δacc stays within ±0.10 of the greedy
  reference (−0.048 ± 0.10). Follow-ups continue to emit 2-token
  letter answers — same distribution, same argmax, just more entropy
  in tie-breaking. Earns if **both**: (a) Δacc ∈ [−0.15, +0.05] AND
  (b) ≥12/14 follow-ups are clean 2-token letters (no basin).

- **H2-3B-temp.sampler-dispersion (weakly-plausible alternative):**
  temperature broadens 3B's decoder enough to change argmax identity
  per follow-up, producing a MORE-correct or LESS-correct session
  than greedy. Earns if Δacc drifts outside ±0.10 of greedy (either
  direction) AND follow-ups remain clean-letter.

- **H2-3B-temp.hidden-basin (least-plausible but pre-registered
  falsifier for the "3B has no basin" claim):** temperature exposes
  latent pathological attractors that greedy's argmax was masking.
  Earns if ≥ 4/14 follow-ups emit non-letter content (any
  addCriterion, long-garbage, 自动生成, empty, code). This would
  falsify the registered claim "3B's failure geometry is clean-letter
  drift" and demand a ceiling-revision.

Exactly one of the three sub-outcomes must earn; two mutually
exclusive, third strictly dominates.

**H3-3B-temp.** Prefix coverage ≥ 0.99 across follow-ups (sanity
gate — no regression in cache-reuse mechanics under temperature).
**Falsification:** < 0.99.

**H4-3B-temp.** Peak RSS ≤ 6 GB (3B 20f cross-arch already ran at
3.93 GB; temperature sampling does not change memory footprint).
**Falsification:** > 7 GB.

## Decision rules

- **H2-3B-temp.null-robust earns** → 3B ceiling is distribution-level
  with clean-letter geometry; sampler-invariant like 7B but at a
  shallower depth. 3D decomposition cleanly extends: both ceilings
  are distribution-level properties, differing only in depth and
  attractor identity. Close 1.55A for good.
- **H2-3B-temp.sampler-dispersion earns** → 3B's ceiling is at
  least partly greedy-argmax-committing; reopens mechanistic
  questioning. Counter-evidence that 7B and 3B share the same
  dimension-3 mechanism.
- **H2-3B-temp.hidden-basin earns** → falsifies the paper-grade
  claim "3B failure geometry is clean-letter drift"; requires
  findings retraction on 3B cross-arch cluster. Highest-impact
  outcome; lowest prior probability.

## Pre-registered analyses

1. Tabulate attractor distribution across the 14 follow-ups under
   temperature; compare against the 3-row (20f/24f/32f) greedy
   reference. Same columns: clean-correct / clean-wrong-letter /
   long-garbage / empty / addCriterion. Any non-letter count ≥ 4
   triggers H2-3B-temp.hidden-basin.
2. Compute Δacc = session_accuracy − baseline_accuracy. Compare
   absolute difference against greedy reference (−0.048).
3. Inspect first-query accuracy separately (cold path) — should
   remain ~baseline (temperature affects cold first-query too, but
   small n=7 means noise dominates).
4. Record exact gen strings for any non-clean-letter follow-up.

## Non-goals

- No 3B/24f or 3B/32f temperature probes (confirmatory of 20f
  result if H2-3B-temp.null-robust earns; requested only if
  H2-3B-temp.sampler-dispersion earns).
- No extreme-sampler conditions (T=1.5, top_k=1, min_p=0.2) — out
  of the paper's practical-sampler envelope.
- No seed variation (single seed=42 matches 7B temperature probe;
  tie-breaking is low-variance on clean-letter follow-ups).

## Artifact paths (expected)

- `research/experiments/2026/artifacts/phase1_55A_3b_20f_temperature/summary.json`
- `research/experiments/2026/artifacts/phase1_55A_3b_20f_temperature/session_qwen7b_n7.jsonl`
- `research/experiments/2026/artifacts/phase1_55A_3b_20f_temperature/baseline_qwen7b_n7.jsonl`
- `research/experiments/2026/artifacts/phase1_55A_3b_20f_temperature/run.log`

## Runtime budget

~30 min (3B 20f cross-arch ran in 29 min; sampling cost is
negligible).
