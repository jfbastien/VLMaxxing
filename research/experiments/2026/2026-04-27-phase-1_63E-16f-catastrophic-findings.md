---
phase: 1.63E (16f point + 20f partial)
date: 2026-04-27
parent: research/experiments/2026/2026-04-27-phase-1_63E-track-b-frame-scaling-prereg.md
related:
  - research/experiments/2026/2026-04-27-phase-1_63E-8f-findings.md
status: 16f catastrophic at L=2 kr=0.50, n=60. 22 sparse parse failures, accuracy collapse to 0.217, choice agreement 36.7%, Δacc=-0.417 CI95 [-0.55, -0.28]. Partial 20f sparse (n=8) reproduces the failure pattern. Run terminated by an unrelated kernel panic before 32f could start.
---

# Phase 1.63E 16f — Track B Qwen frame scaling, **catastrophic boundary** (FINDINGS)

**Verdict.** At 16 frames, the same vision-tower-sparse configuration that produced a clean (if fidelity-bounded) result at 8f — Qwen2.5-VL-7B-Instruct-4bit, L=2, kr=0.50 — collapses instruction-following. 22 of 60 sparse outputs fail to parse a multiple-choice letter; among those that parse, accuracy is 0.217 vs dense 0.633. The C-CEILING arithmetic model also breaks at this point: actual E2E speedup 1.132× exceeds the predicted 1.074× ceiling because junk-output generation is faster than aligned generation. Partial 20f sparse data (n=8) shows the same pattern.

**This is a boundary result, not a bug.** It is the right outcome for a paper that claims sparse vision execution has frame-budget limits; it is the wrong outcome to keep selling Track B as a free fidelity-preserving win.

## Headline numbers, 16f n=60

| Metric | Dense | Sparse | Δ / ratio |
|---|---|---|---|
| Accuracy | 0.633 | **0.217** | **−0.417** (CI95 [−0.55, −0.28]) |
| Parse failures | 0 | **22** | format gate FAILS |
| Choice agreement | — | — | 36.7% |
| Mean vision (ms) | 21,268 | ~11,400 | −46.4% |
| Mean E2E (ms) | 142,766 | ~126,165 | 1.132× speedup |
| Vision share dense | 14.9% | — | — |
| Predicted E2E ceiling | — | — | 1.074× |
| Actual − predicted | — | — | **+0.058** (gate FAILS, > +0.05 tolerance) |

By bucket: short Δ=−0.50 (CI [−0.70, −0.30]), medium Δ=−0.40 (CI [−0.65, −0.15]), long Δ=−0.35 (CI [−0.55, −0.15]). All buckets fail.

Gates against prereg:

- H_pairing PASS (60 paired items).
- H_format **FAIL** (22 sparse parse failures).
- H_fidelity **FAIL** (−0.417 ≪ −0.05).
- H_sparse_vision PASS (46.4% vision reduction).
- H_e2e_positive PASS (1.132×).
- H_ceiling_explained **FAIL** (gap +0.058 > +0.05).

Three of six gates fail; only the mechanical "did we skip vision work and is end-to-end faster?" gates still pass.

## Failure mode is instruction-following collapse, not random-noise

Sample sparse outputs at 16f:

- `"With one letter only."` (parse failure — looks like the model partially echoed an instruction prefix)
- `"The right hand."` (descriptive answer instead of a letter)
- `""` (empty)
- `"The video features Salah's goal in the 11th minute of the match."` (full prose answer to a multiple-choice question)
- `"The man named Tony is a professional photographer."` (similar)

This signature matches the 1.55E Q3 catastrophe (`addCriterion`-style attractor outputs under unrepaired cache reuse): the LM has been pushed off its prompt-format manifold and is producing text that looks like a generic VLM caption, not a multiple-choice answer.

That gives the C-CEILING violation a concrete mechanism: when the sparse arm produces shorter, less constrained outputs, generate_ms drops below what dense produces, so E2E speedup over-shoots the vision-only ceiling.

## 20f partial (n=8 of 60, sparse arm only) reproduces the pattern

The kernel panic terminated 1.63E during the 20f sparse arm at row 8/60. The 8 rows we have:

- 3/8 parse failures (37.5%)
- 0/8 correct
- Output text patterns identical to 16f (prose, descriptive, off-format)

n=8 is too small for a paper claim, but it is enough to *confirm* that the 16f catastrophe is not a one-off and is consistent with what would happen at 20f at this configuration.

## Why 8f did not break

At 8f, kr=0.50 drops 1,600 merged-token groups (half of 3,200). At 16f, it drops 3,200 of 6,400. The total dropped-token magnitude is 2× larger at 16f, and apparently crosses the threshold beyond which the LM cannot recover the multiple-choice format from the surviving prompt. The 8f data showed pass_format=True (0 parse failures) and produced a usable arithmetic-ceiling validation point; the 16f data shows the boundary.

This is consistent with how the 1.51V landed cells were collected: most prior 1.51V results were on 8f or n=30 dev manifests, where this break was not surfaced.

## What the paper should say

This 16f result is **valuable evidence**, not a setback. The paper should:

1. **Lead C-VISION with frame-budget conditioning, not a generic claim.** "C-VISION at L=2 kr=0.50 is a clean wall-clock-arithmetic-validation point at 8f (1.042× observed vs 1.047× predicted, V_red 44.8%) and falls off a fidelity cliff at 16f (Δacc −0.417, 22/60 parse failures, choice agreement 36.7%)."
2. **Cite the failure mode by name.** Instruction-following collapse — same signature as the 1.55E Q3 catastrophe. The model produces prose VLM-caption text instead of A/B/C/D. This is concrete, falsifiable, and explains the apparent C-CEILING-violating super-prediction at 16f (junk is faster than answers).
3. **Define the safe-operating envelope as a research artifact, not a guarantee.** kr=0.50 at L=2 has a 16-frame ceiling on this Qwen 4-bit configuration on this manifest. A kr-sweep at 16f (kr=0.65, 0.75) is the obvious next experiment to find where fidelity returns.

The current C-VISION paragraph should NOT advertise "free speedup at any frame budget." It should advertise "we measure where Track B is safe and where it is not, and the ceiling model holds when fidelity holds."

## Recommended follow-ups

1. **16f kr-sweep at L=2** at higher keep-rate values (kr=0.65, 0.75; possibly 0.85) to bracket the safe operating point at 16f. ~6 h on M3 16 GB.
2. **20f re-run** is *not recommended* at kr=0.50 — predicted-broken from this data. If we do 20f, do it after the 16f kr-sweep tells us the safe kr.
3. **32f at kr=0.50 should be skipped entirely** — predicted-much-worse-than-16f. Replace with 32f at the kr that 16f tells us is safe.
4. **1.63G Gemma cross-arch Track B** is still the right run — but watch for the same pattern at 16f kr=0.50 on Gemma. If it breaks the same way, the boundary is architecture-general; if it does not, the boundary is Qwen-specific and that is itself a publishable contrast.

## Limits

- All 60 items used Qwen2.5-VL-7B-Instruct-4bit on `videomme_combined_v1_n60.toml`. Different manifests / quant / model size may have different boundaries.
- The kernel panic that ended the run was unrelated to the experiment per current evidence (Apple IOKit GPU driver bug; investigation under way). The data on disk for 8f and 16f is complete and trustworthy; 20f is partial and should not be used to claim a 20f result.
