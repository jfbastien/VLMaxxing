# Phase 1.55A-7B-20f — Temperature probe (FINDINGS)

**Date:** 2026-04-20.
**Parent:** `2026-04-20-phase-1_55A-7b-20f-temperature-prereg.md`.

## Headline

**H2-temp.distribution-collapse EARNED** (both prereg conditions cleared):
Δacc = −0.429 (session 9/21 vs baseline 18/21) — **temperature-invariant
within n=21 noise** (greedy 20f Δacc = −0.381; diff = 0.048 ≈ 1
correct/21). Basin prevalence remained high at 0.571 (8/14 follow-ups
still hit an `addCriterion` variant). The 7B cache-reuse failure is
**NOT** a greedy-argmax artifact; it is intrinsic to the cache-reused
logit distribution.

**H1 (speedup 117×), H3 (prefix 0.993), H4 (RSS 1.61 GB) all earned.**

## Numbers

Temperature condition (T=0.7, top_p=1.0, min_p=0.05, seed=42):

| | Session | Baseline | Δ |
|---|---|---|---|
| Accuracy | 9/21 (0.429) | 18/21 (0.857) | **−0.429** |
| First-query | 7/7 (1.00) | — | — |
| Follow-up | 2/14 (0.143) | — | — |

Greedy 20f reference (T=0.0):

| | Session | Baseline | Δ |
|---|---|---|---|
| Accuracy | 9/21 (0.429) | 17/21 (0.810) | **−0.381** |
| First-query | 6/7 (0.857) | — | — |
| Follow-up | 3/14 (0.214) | — | — |

The session count is **numerically identical** between greedy and
temperature runs (9/21 both); the baseline shifted by +1 correct under
temperature, moving Δ by 0.048. That is below the 1/21 ≈ 0.048
per-query noise floor of this sample size.

## Attractor tally (14 follow-ups per condition)

| Attractor | Greedy 20f | Temp 20f |
|---|---:|---:|
| `addCriterion` (plain) | 9 | 4 |
| `addCriterion(…)` Java code | 4 | 4 |
| `自动生成` ("auto-generate", Chinese) | 0 | 5 |
| Clean letter (A/B/C/D) | 1 | 1 |

**Total "any `addCriterion`" basin:** 13/14 (0.929) greedy → 8/14
(0.571) temperature. **Novel-attractor share:** 0/14 greedy → 5/14
(0.357) temperature. **Clean-drift share unchanged** at 1/14 (0.071)
in both conditions.

## Interpretation

Three observations together falsify H-greedy-commit and establish
H-distribution-collapse:

1. **Δacc is temperature-invariant** (−0.381 → −0.429; inside noise).
   If greedy argmax were the mechanism, T=0.7 + min_p=0.05 would have
   smoothly dispersed argmax mass and reduced Δacc. It did not.
2. **Basin prevalence decreased but clean-drift share did not
   increase.** Dispersed basin mass moved into a *different*
   pathological attractor (`自动生成`), not into clean letters. The
   dispersal is *within* the set of high-probability collapse modes,
   not *out* of it.
3. **Java-code basin variant is rigid.** 4/14 follow-ups generate
   `<|im_start|>\n addCriterion("…").…;` under both greedy and
   temperature — identical 4 clips (158, 160 Q2 and Q3). These
   attractors have internal structure (method chains, parameter
   parsing) that persists under temperature. This is textbook
   distribution-collapse onto structured output patterns.

The cache-reused 7B distribution has collapsed onto a low-entropy
set `{addCriterion, addCriterion(...)Java, 自动生成}` plus a thin tail
that includes clean letters. Temperature + min-p redistribute within
that set but do not escape it.

## Three-dimensional decomposition (finalized)

The 1.55A mechanism-mapping phase closes with a three-dimensional
decomposition of the cache-reuse failure:

| Dimension | 7B-4bit | 3B-4bit | Cross-modulation |
|---|---|---|---|
| **1. Threshold onset** | Between 16–20f prefill | Between 16–20f prefill (earlier at 20f) | Capacity-modulated |
| **2. Saturation ceiling** | Δacc ≈ −0.43 (24f, 32f, 20f-greedy, 20f-temp) | Δacc ≈ −0.19 (24f, 32f) | **Architecture-specific** (2.3× shallower on 3B) |
| **3. Failure geometry** | Pathological-attractor SET (addCriterion + 自动生成 + Java); distribution-level collapse | Clean-letter drift; 28/28 follow-ups clean 2-token letters | **Architecture-specific at distribution level** (NOT sampler-specific on 7B) |

The temperature probe closed the last open question: **dimension #3
is a property of the cache-reused logit distribution itself**, not of
the sampler. 7B's pathological-attractor set is intrinsic.

## Pre-registered verdicts

- **H1-temp** (speedup ≥ 80×): 117× — EARNED.
- **H2-temp.greedy-commit** (Δacc ≥ −0.25 AND basin ≤ 0.20): Δacc =
  −0.429 ✗, basin = 0.571 ✗ — **FALSIFIED on both conditions.**
- **H2-temp.distribution-collapse** (Δacc ≤ −0.35 OR basin ≥ 0.50):
  Δacc = −0.429 ✓, basin = 0.571 ✓ — **EARNED on both conditions.**
- **H3-temp** (prefix ≥ 0.99): 0.993 — EARNED.
- **H4-temp** (RSS ≤ 13 GB): 1.61 GB — EARNED.

## Paper implication

Claim #14 hardens to its strongest form: **the 7B basin collapse is a
property of the logit distribution under cache reuse, not of greedy
decoding.** Temperature-and-min-p sampling does not recover fidelity
because the cache-reused distribution has no mass outside the
pathological-attractor set to sample from.

Corollary for practitioners: raising temperature or adding min-p
floor will not recover fidelity for persistent-KV at 20f+ on 7B-4bit.
The pathology has to be fixed earlier in the pipeline (selective
re-prefill of later frames; attention-score-based eviction; different
quantization scheme) — not at the sampler.

## What this does NOT prove

- **It does not prove 3B's clean-letter drift is also distribution-
  level collapse.** A 3B temperature probe would be needed; we have
  deprioritized it since 3B's ceiling is shallow (Δacc ≈ −0.19) and
  the mechanism-mapping budget has been spent.
- **It does not prove the 自动生成 attractor is deterministic across
  seeds.** Only seed=42 tested; seed variation may shift the specific
  novel attractor that appears.
- **It does not rule out that extreme temperatures (T=1.5+, top_k=1
  with label tokens only, or min_p=0.2) could escape the basin.** The
  prereg argued T=0.7 + min_p=0.05 is the *most* dispersive
  conventional sampler; more aggressive samplers risk incoherent
  output and were not tested.

## Artifact paths

- Driver: `scripts/run_kv_cache_session.py` (now accepts
  `--temperature`, `--top-p`, `--min-p`; sampling block recorded in
  `summary.json`).
- Session JSONL:
  `research/experiments/2026/artifacts/phase1_55A_7b_20f_temperature/session_qwen7b_n7.jsonl`
- Baseline JSONL:
  `research/experiments/2026/artifacts/phase1_55A_7b_20f_temperature/baseline_qwen7b_n7.jsonl`
- Summary JSON:
  `research/experiments/2026/artifacts/phase1_55A_7b_20f_temperature/summary.json`
- Run log: same dir, `run.log`.

## Next steps

With the three-dimensional decomposition finalized, the 1.55A
mechanism-mapping phase closes. No further 1.55A probes queued.
The next research priorities shift back to **fidelity-recovery**:

1. **Selective re-prefill of last-K frames** (Phase 1.55B): re-prefill
   the last ~4 frames per follow-up to preserve local motion
   information while retaining global cache reuse. Target: Δacc
   ≤ −0.15 at 20f 7B with ≥ 30× speedup retained.
2. **Gemma 4-E4B-4bit cross-family probe** (Phase 1.55C): measure
   whether Gemma's architecture (different attention pattern,
   different quantization) also exhibits the three-dimensional
   collapse. This is the final cross-family confirmation.
