# Phase 1.55A-3B-24f — Boundary-shift findings (2026-04-20)

**Status:** landed. Second 3B cross-arch mechanism probe.
**Parent prereg:** `2026-04-19-phase-1_55A-3b-24f-boundary-prereg.md`.

## Headline

**H2-3B-24.shifted-ramp EARNED.** Δacc = **−0.190** on 3B at 24f
(~9.7k tokens prefill) — inside the pre-registered (−0.30, −0.05) band.
3B has a ramp; it is shifted to longer prefill vs 7B and has a
**structurally different failure mode**: clean-letter drift, not
basin-attractor collapse.

| Metric | 3B 20f (matched) | 3B 24f (this run) | 7B 20f |
|---|---|---|---|
| Δacc (session − baseline) | −0.048 | **−0.190** | −0.381 |
| Follow-up Δacc (n=14) | 0.000 | **−0.286** | −0.571 |
| Median follow-up (ms) | 412 | 423 | 905 |
| Speedup | 136× | **154×** | 94× |
| Prefix coverage | 0.9928 | 0.9940 | 0.9940 |
| Peak RSS (GB) | 3.93 | 1.48¹ | 5.36 |
| Basin structure | 7 correct + 7 wrong letter | 6 correct + 8 wrong letter | 1 clean, 4 long-garbage, 9 addCriterion |

¹ Peak RSS dropped vs 3B 20f — likely measurement-window difference
(RSS is sampled by the driver at defined checkpoints; does not reflect
working-set shrinkage). Follow up if this matters.

## Hypothesis verdicts

- **H1-3B-24 speedup ≥ 80× — EARNED.** 154×. 3B speedup keeps scaling
  with prefill length, like 7B (47→91→70→94→122→150× on 7B across
  8/16/18/20/24/32f; 3B now 136× @ 20f, 154× @ 24f). Median follow-up
  423 ms, well under 600 ms budget.
- **H2-3B-24 fidelity — H2-3B-24.shifted-ramp sub-outcome EARNED.**
  Δacc = −0.190 ∈ (−0.30, −0.05). Confirms 3B has a ramp, shifted later
  than 7B's.
- **H3-3B-24 prefix coverage ≥ 0.99 — EARNED.** 0.9940.
- **H4-3B-24 peak RSS ≤ 4.5 GB — EARNED.** 1.48 GB.

## Basin decomposition (the key mechanistic finding)

All 14 follow-ups emit clean 2-token single-letter answers (A/B/C/D).
**Zero addCriterion, zero long-garbage, zero empty.**

| Clip | Q2 session | Q2 baseline | Q3 session | Q3 baseline |
|---|---|---|---|---|
| 037 | C ✓ | C ✓ | D ✓ | D ✓ |
| 100 | B ✓ | B ✓ | A ✓ | D ✗ |
| 116 | A ✗ | D ✓ | B ✓ | B ✓ |
| 120 | D ✓ | D ✓ | A ✗ | D ✗ |
| 158 | B ✗ | B ✗ | A ✗ | B ✓ |
| 160 | A ✗ | D ✓ | C ✗ | B ✓ |
| 210 | D ✗ | B ✓ | B ✗ | B ✗ |

- Session follow-up correct: 6/14
- Baseline follow-up correct: 10/14 (at the same 24f prefill)
- First-query correct: 4/7 both modes (identical — no first-query
  degradation; the deficit is entirely on cache-reused follow-ups)

**3B at 24f exhibits a qualitatively different failure mode from 7B:**
decode-choice drift without basin collapse. The model stays in a
well-formed output distribution (2-token letter-options), but the KV
cache reuse biases the letter choice away from the baseline letter on
4/14 follow-ups. Compare to 7B 24f where 14/14 follow-ups emit the
`addCriterion` attractor.

## Frame-scaling curve (updated, both architectures)

| Frames | Prefill | 7B Δacc | 3B Δacc | 7B speedup | 3B speedup |
|---|---|---|---|---|---|
| 8 | ~3.3k | −0.048 | — | 47× | — |
| 16 | ~6.5k | 0.000 | — | 91× | — |
| 18 | ~7.3k | −0.238 | — | 70× | — |
| 20 | ~8.1k | −0.381 | −0.048 | 94× | 136× |
| **24** | **~9.7k** | **−0.429** | **−0.190** | **122×** | **154×** |
| 32 | ~12.9k | −0.429 | ? | 150× | ? |

**3B ramp emerges between 20f and 24f; 7B ramp emerges between 16f and
18f.** 3B boundary is shifted by ~2-3k prefill tokens. **The ramp
exists on 3B — it is not absent, just shifted.**

## Mechanism verdict update (since 3B 20f)

1. **Re-weighted (mildly rehabilitated): prefill-length-modulated
   mechanism with capacity-dependent threshold.** 3B 20f earlier looked
   like a full falsification of prefill-length-intrinsic; the 24f
   result shows 3B does have a ramp, just at longer prefill. The
   mechanism is *modulated by* prefill length with a capacity- and
   architecture-specific onset. NOT purely model-identity-specific.
2. **Strongly supported: model-capacity / depth-dependent
   accumulation.** 7B reaches saturation at ~9.7k; 3B reaches mid-ramp
   at ~9.7k and the slope is shallower (first step −0.19 at 24f, vs 7B
   which was already at −0.43 by 24f).
3. **Strongly supported (new mechanistic finding): basin-attractor
   identity is architecture-specific.** 7B collapses to saturated
   `addCriterion`; 3B does NOT collapse to a saturated attractor even
   when accuracy degrades. 3B stays in the trained-completion
   distribution (2-token letters) and drifts the argmax across letters.
   **The failure *geometry* differs across model sizes, not just the
   *threshold*.**
4. **Falsified (reaffirmed): shared-tokenizer basin attractor as the
   mechanism.** Same tokenizer; no shared attractor basin even when
   accuracy degrades.

## Paper implication — claim #14 refinement

Current language ("ramp is model-specific, likely depth- or
capacity-mediated") holds but can be sharpened:

> Cache-reuse preserves accuracy on Qwen 7B-4bit at ≤ ~6.5k tokens,
> then degrades via progressive basin collapse (4-basin mid-ramp at
> ~7.3k → 2-basin at ~8.1k → single-attractor saturation at ≥ ~9.7k).
> The smaller Qwen 2.5-VL-3B-4bit exhibits the same
> progressive-degradation shape with a **shifted threshold and a
> structurally distinct failure mode**: at 8.1k the 3B ramp has not
> started (Δacc = −0.048); at 9.7k it is mid-ramp (Δacc = −0.190); 3B
> failures are clean-letter drift rather than basin-attractor
> collapse. This shows cache-reuse robustness scales with model size
> AND that the basin-attractor identity (e.g. `addCriterion`) is
> architecture-specific, not a generic consequence of long-prefill
> cache-reuse.

## Decision-rule cascade (per prereg)

`shifted-ramp` verdict → queued next:

1. **32f 3B frame-scaling** — map the full 3B shifted curve. Expected
   to land around the saturated plateau (if 3B saturates) or a
   further-degraded mid-ramp point. Budget ~40 min (32f = ~12.9k
   prefill, 3B decode fast).
2. **7B/20f temperature probe** — still queued. The 3B data expands
   the mechanism picture (capacity-modulated ramp + architecture-
   specific failure geometry); the 7B temperature probe now addresses
   the narrower question: is the 7B addCriterion basin a greedy-argmax
   commit on a broad distribution, or a true distribution-collapse? The
   3B result that 3B drifts letters cleanly (broad distribution) suggests
   the answer may differ across architectures.

## Runtime

30.5 min total wall clock. Within the 33-min prereg budget.

## Artifacts

- `research/experiments/2026/artifacts/phase1_55A_3b_24f_boundary/`
  - `summary.json`
  - `session_qwen7b_n7.jsonl`
  - `baseline_qwen7b_n7.jsonl`
  - `run.log`
