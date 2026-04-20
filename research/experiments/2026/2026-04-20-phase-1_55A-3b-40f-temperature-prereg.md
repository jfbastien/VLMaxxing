---
date: 2026-04-20
phase: 1.55A
status: preregistration
parent_findings:
  - 2026-04-20-phase-1_55A-3b-40f-deeper-plateau-findings.md
  - 2026-04-20-phase-1_55A-7b-40f-symmetry-findings.md
  - 2026-04-20-phase-1_55A-3b-36f-interpolation-findings.md
  - 2026-04-20-phase-1_55A-7b-20f-temperature-findings.md
  - 2026-04-20-phase-1_55A-3b-20f-temperature-findings.md
reopen_condition: (h) 3B 40f temperature probe to extend sampler-invariance claim to the 3B basin regime
---

# Phase 1.55A — 3B 40f temperature probe (PREREG)

## Problem statement

Sampler-invariance under temperature+min-p has been earned at
three regimes:
- **7B pre-basin (20f):** H2-temp.distribution-collapse EARNED
  (Δacc temperature-invariant, basin mass redistributed to novel
  `自动生成` Chinese attractor, no clean-decoding recovery).
- **7B basin (20f):** [same as pre-basin since 20f is 7B's
  basin-entry regime; no separate probe needed]
- **3B pre-basin (20f):** H2-3B-temp.null-robust EARNED (Δacc
  stays inside envelope; 14/14 clean-letter follow-ups under
  temperature; zero pathological-attractor emergence).

The open regime is **3B basin (40f, ~16.1k prefill)**. The 3B
basin at 40f shows 4/14 non-letter follow-ups under greedy
(3 empty-response + 1 "The") with Δacc = −0.238. Under
temperature+min-p, does this basin:

a. **Stay closed** (sampler-invariant basin, mirror of 7B basin
   behavior at 20f): Δacc within ±0.05 of greedy 3B 40f Δacc;
   comparable non-letter count (3–5/14) possibly with different
   identity. Earns: the basin is a distribution-level property
   at BOTH architectures, not a greedy-argmax artifact.

b. **Open to clean-letter under sampling** (sampler-recovers
   3B basin; asymmetric to 7B): Δacc within ±0.05 of baseline
   3B 40f (−0.095 or better); 12/14+ clean-letter follow-ups.
   Earns: 3B's basin is a thinner attractor than 7B's and can
   be escaped by sampler-side intervention.

c. **Degrade further** (temperature makes it worse): Δacc worse
   than −0.30 OR novel-attractor count ≥8/14. Earns: sampler
   interacts pathologically with 3B basin geometry; rules out
   distribution-collapse being the unified mechanism.

## Competing primary hypotheses

**H1-3B-40-temp.distribution-collapse (primary):** Δacc ∈
[−0.29, −0.19] (inside 1/21 envelope of greedy 3B 40f Δacc =
−0.238) AND ≥3/14 session follow-ups emit non-letter content.
**Earns** the cross-architectural distribution-collapse
interpretation: basin is sampler-invariant at BOTH 7B and 3B
once basin-onset depth is crossed.

**H1-3B-40-temp.sampler-recovers (primary, competing):** Δacc
∈ [−0.15, +0.05] (close to baseline) AND ≥12/14 clean-letter
follow-ups. **Earns** a novel asymmetry: 3B's basin is
escapable via sampling but 7B's is not. Would require rewriting
the "upstream intervention required" claim to be architecture-
conditional.

**H1-3B-40-temp.degenerate (primary, competing):** Δacc worse
than −0.30 OR novel-attractor count ≥8/14. **Earns** the
interpretation that temperature interacts pathologically with
the 3B basin, falsifying the unified mechanism hypothesis.

## Secondary hypotheses

**H2-3B-40-temp (speedup):** Speedup ≥ 150× (some degradation
vs greedy 3B 40f's 191× expected due to min_p filter overhead).
Follow-up median ≤ 900 ms.

**H3-3B-40-temp (prefix coverage):** ≥ 0.993.

**H4-3B-40-temp (RSS):** Peak RSS ≤ 5 GB.

## Parameters

- **Model:** Qwen 2.5-VL-3B-Instruct-4bit.
- **Frame count:** 40.
- **Clips:** 7 short-bucket VideoMME clips (037, 100, 116, 120,
  158, 160, 210) × 3 Qs = 21 queries.
- **Decoding:** T=0.7, top_p=1.0, min_p=0.05, seed=42 (same as
  prior 7B/20f and 3B/20f temperature probes).
- **Driver:** `scripts/run_kv_cache_session.py` (unchanged).
- **Output dir:**
  `research/experiments/2026/artifacts/phase1_55A_3b_40f_temperature/`.

## Attractor identity tally (to populate post-run)

| Attractor class                                      | Count |
|------------------------------------------------------|-------|
| Clean 2-token letter (any of A/B/C/D)                | TBD   |
| Empty-response (`generation_tokens=1`)                | TBD   |
| "The" / other clean-non-letter                       | TBD   |
| `addCriterion` family                                | TBD   |
| `自动生成` Chinese auto-generate                     | TBD   |
| Novel (non-letter, non-known-basin)                  | TBD   |

## Runtime estimate

3B 40f greedy wall: ~40 min. Temperature adds ~2-5% from min_p
filter. **~45 min.**

## Falsification decision tree

- **H1-distribution-collapse earns:** Cross-architectural
  distribution-collapse unified. Paper's "upstream intervention
  required" claim stays architecture-independent. Task #141b
  closes.
- **H1-sampler-recovers earns:** 3B basin is thinner than 7B.
  Paper's intervention claim becomes architecture-conditional.
  Preregister a 3B 48f temperature probe to test if deeper
  basin remains escapable.
- **H1-degenerate earns:** Unified mechanism falsified at the
  sampler level. Paper reverts to architecture-specific basin
  descriptions. Major rewrite of Claim #14's sampler-invariance
  subclaim.

## Related to 1/21 noise-floor signature

Both the 7B/20f and 3B/20f probes shifted Δacc by exactly 1/21
(one query) from greedy to temperature, in the same direction
(greedy → temperature slightly worse). This is the conversation-
memory noise floor. **Predicted null value for 3B 40f temperature
Δacc: −0.238 − 1/21 = −0.286.** If observed Δacc ∈ [−0.33, −0.24]
the 1/21 signature is symmetric across ALL regimes; if outside,
the basin regime breaks the pattern.

## What this probe does NOT test

- 3B 48f deeper-basin probe (preregister later if H1-sampler-
  recovers earns).
- 7B 48f deeper-basin probe (not in queue for this draft).
- Selective re-prefill (blocked on 1.55D infra).

## Artifact paths

- Findings (post-run): `...-3b-40f-temperature-findings.md`.
- Session/baseline JSONL + summary.json in output dir above.
- Run log: `run.log` in output dir.
