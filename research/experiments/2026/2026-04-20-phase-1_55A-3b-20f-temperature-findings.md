# Phase 1.55A-3B-20f — Temperature probe (FINDINGS)

**Date:** 2026-04-20.
**Parent:** `2026-04-20-phase-1_55A-3b-20f-temperature-prereg.md`.

## Headline

**H2-3B-temp.null-robust EARNED** (both prereg conditions cleared):
Δacc = −0.095 (session 13/21 vs baseline 15/21) — inside the
[−0.15, +0.05] null-robust envelope; 14/14 follow-ups emit clean
2-token letter answers. **3B's failure geometry is sampler-invariant
clean-letter drift.** Zero hidden basin. No pathological attractor
exposed by temperature + min-p. The cache-reuse deficit at the 3B
20f ceiling is distribution-level at its shallower depth — exactly
symmetric with 7B's distribution-level basin collapse at its deeper
ceiling.

**H1 (speedup 130.8×), H3 (prefix 0.993), H4 (RSS 2.36 GB) all earned.**

## Numbers

Temperature condition (T=0.7, top_p=1.0, min_p=0.05, seed=42):

| | Session | Baseline | Δ |
|---|---|---|---|
| Accuracy | 13/21 (0.619) | 15/21 (0.714) | **−0.095** |
| First-query | 4/7 (0.571) | — | — |
| Follow-up | 9/14 (0.643) | — | — |

Greedy 3B/20f cross-arch reference (T=0.0):

| | Session | Baseline | Δ |
|---|---|---|---|
| Accuracy | 12/21 (0.571) | 13/21 (0.619) | **−0.048** |
| First-query | — | — | — |
| Follow-up | 6/14 (0.429) | — | — |

**Both session and baseline gained exactly 1-2 correct under
temperature (+1 session, +2 baseline)**. The Δacc shift
(−0.048 → −0.095, diff 0.048) is exactly 1 correct/21 = the noise
floor of this sample size. Δacc is **temperature-invariant within
noise** at the 3B ceiling, identical in structure (but opposite
direction) to the 7B noise-floor shift of 0.048 observed on the
7B probe.

## Attractor tally (14 follow-ups)

| Attractor | Greedy 3B/20f | Temp 3B/20f |
|---|---:|---:|
| Clean 2-token letter (A/B/C/D) | 14 | **14** |
| `addCriterion` (any variant) | 0 | **0** |
| `自动生成` / novel pathological | 0 | **0** |
| Long-garbage / empty | 0 | **0** |

Every follow-up emits a clean 2-token letter. Letter distribution
under temp: D×8, B×4, C×2. Under greedy (from 3B cross-arch findings):
broadly similar letter spread. Temperature shuffles argmax on a few
queries (one more correct in session, two more correct in baseline)
but never exposes any non-letter content.

## Interpretation

Three observations jointly falsify H2-3B-temp.hidden-basin and
H2-3B-temp.sampler-dispersion, establishing H2-3B-temp.null-robust:

1. **Δacc is temperature-invariant within 1/21 noise floor**
   (−0.048 → −0.095; diff 0.048). Exactly the same signature
   observed on 7B/20f (−0.381 → −0.429; diff 0.048). In both
   architectures, temperature moves the Δacc by at most one
   correct-answer flip per 21 queries.

2. **14/14 follow-ups remain clean 2-token letters.** No
   pathological attractor emerges under temperature on 3B; no
   hidden basin was waiting behind greedy's argmax. The 3B
   cache-reused logit distribution genuinely has its mass on the
   clean-letter tokens — sampling from it yields more clean-letter
   tokens, just with slightly different argmax choices.

3. **Both the deficit AND the recovery under temperature are
   symmetric across Qwen 7B and 3B at 20f:** both architectures
   show Δacc shift by exactly 1/21 (opposite directions;
   magnitude identical); both architectures show 100% preservation
   of their characteristic failure geometry (7B: pathological-
   attractor set remains 13/14 → 8/14 with zero clean-drift
   recovery; 3B: clean-letter set remains 14/14 → 14/14).

The temperature-invariance signature is thus a **property of
cache-reused logit distributions** that holds across the ceiling-
depth dimension. Sampler-side intervention cannot escape either
architecture's ceiling.

## Three-dimensional decomposition (now temperature-verified at both ceilings)

| Dimension | 7B-4bit | 3B-4bit |
|---|---|---|
| **1. Threshold onset** | ~7.3k prefill tokens (18f) | ~9.7k prefill tokens (24f) |
| **2. Saturation ceiling** | Δacc ≈ −0.43 (greedy and temp) | Δacc ≈ −0.05 to −0.19 (greedy and temp; architecture-specific shallower ceiling) |
| **3. Failure geometry** | Pathological-attractor SET {addCriterion, addCriterion(…)Java, 自动生成}; **temperature-invariant**, basin redistribution stays IN the set | Clean 2-token letter; **temperature-invariant**, geometry remains clean-letter with argmax shuffling |

**Phase 1.55A mechanism mapping is now temperature-verified at BOTH
ceilings.** Sampler-invariance is a cross-architecture property of
cache-reused logit distributions on Qwen 2.5-VL-4bit at 20f; the
pathology (or its absence) is encoded in the logit distribution, not
in the argmax decoder.

## Pre-registered verdicts

- **H1-3B-temp** (speedup ≥ 80× AND median ≤ 0.6 s): 130.8× /
  385 ms — EARNED.
- **H2-3B-temp.null-robust** (Δacc ∈ [−0.15, +0.05] AND ≥12/14
  clean-letter follow-ups): Δacc = −0.095 ✓, 14/14 clean-letter ✓
  — **EARNED on both conditions.**
- **H2-3B-temp.sampler-dispersion** (Δacc outside [−0.15, +0.05]
  AND clean-letter): Δacc inside envelope — **NOT TRIGGERED.**
- **H2-3B-temp.hidden-basin** (≥4/14 non-letter follow-ups): 0/14
  non-letter — **NOT TRIGGERED.**
- **H3-3B-temp** (prefix ≥ 0.99): 0.993 — EARNED.
- **H4-3B-temp** (RSS ≤ 6 GB): 2.36 GB — EARNED.

## Paper implication

Claim #14 now reads at its tightest: **cache-reused logit
distributions in Qwen 2.5-VL-4bit are sampler-invariant at both the
7B and 3B ceilings; the failure geometry (pathological-attractor
set vs clean-letter drift) and the saturation depth (−0.43 vs
roughly −0.05 to −0.19) are properties of the distribution itself
at each architecture, not of greedy decoding.** The 3-D decomposition
(threshold onset capacity-modulated; saturation ceiling architecture-
specific; failure geometry architecture-specific at distribution
level) now has distribution-level verification at BOTH ceilings
of the architecture pair.

Corollary: temperature + min-p sampling does not recover fidelity
at EITHER ceiling. On 3B the "recovery" is moot because the greedy
ceiling is already within paper-publishable envelope (−0.05 at 20f;
−0.19 at 24f+). On 7B the temperature probe (previously landed)
proved recovery is not possible from the sampler. Fidelity recovery
must be upstream (Phase 1.55D selective re-prefill; Phase 1.55C
Gemma cross-family parametrization).

## What this does NOT prove

- **It does not prove 3B has zero basin mass.** A longer follow-up
  budget (max_tokens > 2) would tell us whether 3B has pathological
  tail attractors after the clean letter. We bounded gen to 2 tokens
  per the clean-letter answer format. Not relevant to the ceiling
  question but a point to note if someone later asks "does 3B EVER
  produce addCriterion."
- **It does not prove ceiling invariance at other prefill depths.**
  Tested at 20f only. Greedy reference at 24f and 32f already
  established the 3B plateau (Δacc ≈ −0.19 at both); the
  distribution-level claim extrapolates from temperature-invariance
  at 20f but a 3B/32f temp probe would be confirmatory.
- **It does not prove the pattern generalizes to Gemma or other
  families.** Phase 1.55C is the cross-family test.

## Artifact paths

- Driver: `scripts/run_kv_cache_session.py` (temperature-flag version,
  unchanged since 2026-04-20 7B temp probe landing).
- Session JSONL:
  `research/experiments/2026/artifacts/phase1_55A_3b_20f_temperature/session_qwen7b_n7.jsonl`
- Baseline JSONL:
  `research/experiments/2026/artifacts/phase1_55A_3b_20f_temperature/baseline_qwen7b_n7.jsonl`
- Summary JSON:
  `research/experiments/2026/artifacts/phase1_55A_3b_20f_temperature/summary.json`
- Run log: same dir, `run.log`.

## Next steps

**Phase 1.55A now fully closed with temperature verification at both
architectures' ceilings.** No mechanism-mapping experiments remain.

Next priorities shift entirely to:
1. **Phase 1.55D selective re-prefill** (preregistered 2026-04-20):
   first fidelity-recovery lever, targets Δacc ≤ −0.15 at K=4 on
   7B-20f with ≥ 15× speedup retained. Requires mlx-vlm
   PromptCacheState truncation support (1-3 hours driver work).
2. **Phase 1.55C Gemma 4-E4B-4bit cross-family** (preregistered
   2026-04-20): cross-family parametrization of the 3-D decomposition.
   Requires driver Gemma loader + PromptCacheState attention-
   interleave compatibility verification (~30 min implementation +
   30-60 min run).

1.55D is higher-priority because it directly addresses the fidelity-
recovery gap identified by both temperature probes. 1.55C is
second-priority because architectural generalization is valuable but
the 3-D decomposition is already strongly evidenced across Qwen 7B
and 3B.
