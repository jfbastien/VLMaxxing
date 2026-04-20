---
date: 2026-04-20
phase: 1.55A
status: preregistration
parent_findings:
  - 2026-04-20-phase-1_55A-3b-40f-deeper-plateau-findings.md
  - 2026-04-20-phase-1_55A-7b-40f-symmetry-findings.md
reopen_condition: (g) 3B 36f interpolation to pin onset threshold
---

# Phase 1.55A — 3B 36f basin-onset interpolation (PREREG)

## Problem statement

The 3B 40f probe (2026-04-20) earned H1-latent-basin with 4/14
novel attractors (3 empty + 1 "The"); the 3B 32f probe was clean
(14/14 letters, Δacc=−0.190 plateau-like). The basin-onset
boundary on 3B therefore lies somewhere in (32f, 40f] —
equivalently, in (~12.9k prefill tokens, ~16.1k prefill tokens].

The 7B 40f symmetry probe (2026-04-20) confirmed basin is
depth-invariant once entered (13/14 in established set at 2×
basin-onset depth). This bounds the shape of the within-basin
region but does not tell us how sharp the onset is.

**This probe samples a single interior point: 3B at 36f.**
Prefill ~14.5k tokens (midpoint between 32f and 40f).

## Competing primary hypotheses

**H1-3B-36.sharp-onset (primary):** 3B at 36f reproduces the
40f basin signature — ≥3/14 session follow-ups emit non-letter
content (empty-response OR non-addCriterion non-Chinese tokens),
Δacc worse than −0.19 (3B 32f baseline). **Earns** the
interpretation that basin-onset is sharp: transition happens
somewhere in (~12.9k, ~14.5k] tokens. Supports the "threshold"
framing of dimension 1.

**H1-3B-36.wide-transition (primary, competing):** 3B at 36f
looks like 32f — 14/14 clean 2-token letter follow-ups (0 non-
letter), Δacc ∈ [−0.25, −0.15] (plateau-like). **Earns** the
interpretation that the onset transition is wide: basin appears
only above ~14.5k tokens. Requires preregistering a 3B 48f probe
to find the closed-basin depth (if it exists at all for 3B
within hardware budget) and a 3B 42f follow-up to further narrow.

**H1-3B-36.intermediate (primary, competing):** 1–2/14 session
follow-ups emit non-letter content (ambiguous; between 32f's 0
and 40f's 4). **Earns** a continuous-transition interpretation:
basin emerges gradually over ~3k tokens. Neither sharp threshold
nor wide plateau. Requires 3B 38f interpolation to pin the
transition.

## Secondary hypotheses (unchanged structure from 40f run)

**H2-3B-36 (speedup):** Speedup ≥ 170× (monotonic interpolation
from 3B 32f=213× and 3B 40f=191×; may be non-monotonic like
7B 18f was). Follow-up median ≤ 1000 ms.

**H3-3B-36 (prefix coverage):** ≥ 0.993.

**H4-3B-36 (RSS):** Peak RSS ≤ 5 GB.

## Parameters

- **Model:** Qwen 2.5-VL-3B-Instruct-4bit
  (`~/models/Qwen2.5-VL-3B-Instruct-4bit`).
- **Frame count:** 36.
- **Clips:** 7 short-bucket VideoMME clips (037, 100, 116, 120,
  158, 160, 210) × 3 Qs = 21 queries.
- **Decoding:** greedy (T=0.0), max_tokens=64.
- **Driver:** `scripts/run_kv_cache_session.py` (unchanged,
  defaults to 7B — override `--model-path`).
- **Output dir:**
  `research/experiments/2026/artifacts/phase1_55A_3b_36f_interpolation/`.

## Attractor identity tally (to populate post-run)

| Attractor class                                | Count |
|------------------------------------------------|-------|
| Clean 2-token letter (any)                     | TBD   |
| Plain `addCriterion` (short)                   | TBD   |
| `addCriterion(…)` Java-code method-chain       | TBD   |
| `自动生成` Chinese auto-generate               | TBD   |
| Long-garbage repetition (> 16 gen tokens)      | TBD   |
| Empty-response (`generation_tokens=1`)          | TBD   |
| "The" / other clean-non-letter                 | TBD   |

## Runtime estimate

3B 32f wall: ~30 min (n=42). 3B 40f wall: ~40 min. 36f
interpolation: **~35 min.** (baseline is wall-dominated by
first-query prefill which scales near-linearly with frame count).

## Falsification decision tree

- **H1-sharp earns:** basin-onset is a threshold at ~13–14.5k
  tokens; claim #14 dimension-2 framing is clean. No further
  interpolation needed for this draft. Task #141 closes.
- **H1-wide earns:** basin-onset requires more than 14.5k
  tokens on 3B. Preregister 3B 38f (~1 turn) to narrow. Keep
  task open.
- **H1-intermediate earns:** continuous transition; preregister
  3B 38f and possibly 3B 34f for full gradient. Update Claim
  #14 dimension-2 phrasing from "threshold onset" to "gradient
  onset".

## What this probe does NOT test

- 3B 40f temperature probe (separate reopen condition h).
- 7B 48f / 64f deeper-closed-basin probe.
- 4-bit quantization-level interaction (1.58 deferred).

## Artifact paths

- Findings (post-run): `...-3b-36f-interpolation-findings.md`.
- Session/baseline JSONL + summary.json in output dir above.
- Run log: `run.log` in output dir.
