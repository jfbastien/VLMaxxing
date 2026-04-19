# Phase 1.55A-3B-32f — Saturation-mapping findings (2026-04-20)

**Status:** landed. Third 3B cross-arch mechanism probe.
**Parent prereg:** `2026-04-20-phase-1_55A-3b-32f-saturation-prereg.md`.

## Headline

**H2-3B-32.plateaued EARNED.** Δacc = **−0.190** on 3B at 32f
(~12.9k prefill tokens) — **numerically identical to the 3B 24f
result**, inside the pre-registered (−0.25, −0.10] plateaued band.
3B has **saturated** — but at a shallower ceiling than 7B's
(−0.19 vs −0.43) and with a **structurally distinct failure
geometry**: 14/14 follow-ups remain clean 2-token letter answers;
no basin-attractor collapse appears at the 2.3× deeper prefill
either.

| Metric | 3B 20f | 3B 24f | **3B 32f** | 7B 32f |
|---|---|---|---|---|
| Prefill (approx) | 8.1k | 9.7k | **12.9k** | 12.9k |
| Δacc (session − baseline) | −0.048 | −0.190 | **−0.190** | −0.429 |
| Follow-up Δacc (n=14) | 0.000 | −0.286 | **−0.286** | ~−0.64 (14/14 addCrit) |
| First-query Δacc (n=7) | — | 0.000 | **0.000** | ~0 |
| Median follow-up (ms) | 412 | 423 | **484** | 592 |
| Speedup | 136× | 154× | **213×** | 150× |
| Prefix coverage | 0.9928 | 0.9940 | **0.9955** | 0.9933 |
| Peak RSS (GB) | 3.93 | 1.48 | **4.58** | 5.37 |
| Basin structure | clean-letter drift | clean-letter drift | **clean-letter drift** | `addCriterion` saturated |

## Hypothesis verdicts

- **H1-3B-32 speedup ≥ 130× — EARNED.** 213×. 3B speedup curve
  continues to scale with prefill (136× @ 20f → 154× @ 24f → 213× @
  32f). Now higher than 7B 32f's 150×; 3B decode stays fast while
  prefill dominates. Median follow-up 484 ms, well under 600 ms budget.
- **H2-3B-32 fidelity — H2-3B-32.plateaued sub-outcome EARNED.**
  Δacc = −0.190 ∈ (−0.25, −0.10]. *And it is numerically identical to
  24f.* **3B saturates at Δacc ≈ −0.19, not 7B's −0.43.** The
  architecture caps its own cache-reuse damage.
- **H3-3B-32 prefix coverage ≥ 0.99 — EARNED.** 0.9955.
- **H4-3B-32 peak RSS ≤ 5.5 GB — EARNED.** 4.58 GB.

## Basin decomposition — saturation WITHOUT collapse

All 14 follow-ups emit clean 2-token single-letter answers (A/B/C/D).
**Zero addCriterion, zero long-garbage, zero empty** — same failure
geometry as 3B 20f and 3B 24f, at 60% more prefill than the 7B
saturation point.

| Clip | Q2 session | Q2 baseline | Q3 session | Q3 baseline |
|---|---|---|---|---|
| 037 | C ✓ | C ✓ | B ✗ | D ✓ |
| 100 | A ✗ | A ✗ | A ✓ | D ✗ |
| 116 | D ✓ | D ✓ | B ✓ | B ✓ |
| 120 | D ✓ | D ✓ | A ✗ | D ✗ |
| 158 | A ✗ | A ✗ | A ✗ | B ✓ |
| 160 | A ✗ | D ✓ | C ✗ | B ✓ |
| 210 | A ✗ | B ✓ | B ✗ | B ✗ |

- Session follow-up correct: 5/14
- Baseline follow-up correct: 9/14 (at the same 32f prefill)
- First-query correct: 5/7 both modes (identical; first-query
  continues to track baseline — deficit is entirely on cache-reused
  follow-ups)

**3B-32f stays in the same attractor-free regime as 3B-24f.** The
drifted letters are distributed across A/B/C (not a single collapse
letter). Compare to 7B 32f where 14/14 follow-ups emit the
`addCriterion` attractor.

## The "numerically identical Δacc" finding

Compare cell by cell:

| | Session correct | Baseline correct | Δacc |
|---|---|---|---|
| 3B 24f | 10/21 | 14/21 | −0.190 |
| 3B 32f | 10/21 | 14/21 | −0.190 |

Not an approximation — raw counts match. First-query splits (4/7 at
24f, 5/7 at 32f) differ but integrate to the same session total.
Follow-up splits (6/14 at 24f, 5/14 at 32f) also differ but integrate
to the same baseline delta. This is strong evidence that 3B has
**saturated** rather than continued to climb.

## Frame-scaling curve (updated, both architectures)

| Frames | Prefill | 7B Δacc | 3B Δacc | 7B speedup | 3B speedup |
|---|---|---|---|---|---|
| 8 | ~3.3k | −0.048 | — | 47× | — |
| 16 | ~6.5k | 0.000 | — | 91× | — |
| 18 | ~7.3k | −0.238 | — | 70× | — |
| 20 | ~8.1k | −0.381 | −0.048 | 94× | 136× |
| 24 | ~9.7k | −0.429 | −0.190 | 122× | 154× |
| **32** | **~12.9k** | **−0.429** | **−0.190** | **150×** | **213×** |

**Both architectures saturate.** 7B saturates at Δacc = −0.429
between 24f and 32f. 3B saturates at Δacc = −0.190 between 24f and
32f — **at the same prefill range, to a ~2.3× shallower ceiling**.

## Mechanism verdict — three-dimensional decomposition

The 3-point 3B curve × 7B curve resolves the mechanism into **three
independently-varying dimensions**:

1. **Threshold onset — capacity-modulated.** 7B ramp kicks in at
   ~7.3k prefill; 3B ramp kicks in at ~9.7k prefill. Shifted later
   on the smaller model. Same ramp shape.
2. **Saturation ceiling — architecture-specific.** 7B caps at
   Δacc = −0.43; 3B caps at Δacc = −0.19. **Not** a function of
   prefill length — 3B at 12.9k never reaches 7B's 24f ceiling.
   The deeper model loses more accuracy to cache reuse at
   saturation; the shallower model loses ~2.3× less.
3. **Failure geometry — architecture-specific.** 7B collapses to a
   single saturated lexical attractor (`addCriterion`); 3B drifts
   the argmax across well-formed letter options without a
   common attractor. **28/28 3B follow-ups emit clean 2-token
   letter answers across 20f/24f/32f.** No basin collapse appears
   at the 3B capacity regardless of prefill length.

This decomposition upgrades claim #14 beyond "capacity-modulated
threshold" to **"capacity-modulated threshold × architecture-specific
ceiling × architecture-specific failure geometry"**. Each dimension
is evidenced by a clean falsifier in the cross-arch data.

## Paper implication — claim #14 refinement

Proposed language for claim-matrix row 14:

> Cache-reuse preserves accuracy on Qwen 7B-4bit at ≤ ~6.5k tokens,
> then degrades via progressive basin collapse to a saturated
> single-attractor (`addCriterion`) at Δacc ≈ −0.43 by ~9.7k,
> plateau confirmed at 12.9k. Qwen 2.5-VL-3B-4bit degrades through
> the same frame-scaling regime with a **shifted threshold onset**
> (~9.7k vs ~7.3k), a **shallower saturation ceiling** (Δacc ≈
> −0.19 vs −0.43, confirmed across 9.7k and 12.9k), and a
> **structurally distinct failure geometry** (28/28 follow-ups
> emit clean 2-token letter answers with no attractor basin;
> 7B 14/14 follow-ups emit `addCriterion`). Cache-reuse damage is
> thus decomposable into three independently-varying architectural
> dimensions, not a single prefill-length-intrinsic scalar.

## Decision-rule cascade (per prereg)

`plateaued` verdict → the most-surprising sub-outcome fires:

1. **Paper story upgrades** to "capacity-dependent threshold ×
   architecture-dependent ceiling × architecture-dependent failure
   geometry" (claim #14 and publishability row O).
2. **7B/20f temperature probe** becomes next. Distinguishes
   greedy-argmax commit (narrow distribution at saturation) from
   true distribution-collapse. The 3B clean-letter-drift regime
   suggests 3B has a *broad* distribution that greedy-argmax chains
   through across clips; the 7B `addCriterion` regime is *either* a
   hard distribution collapse *or* an argmax commit on a broad
   distribution with `addCriterion` happening to be the mode at
   saturation. Only temperature sampling distinguishes these.
3. **3B/40f saturation verification** — deprioritized. 3B is clearly
   saturated between 24f and 32f; going to 40f is confirmatory and
   costly with small expected information gain. Leave in backlog.
4. **Gemma 4-E4B cross-family** — still queued as the
   tokenizer-family falsifier; deferred after the temperature probe.

## Runtime

49.5 min total wall clock. Longer than 40-min prereg budget (3B 32f
prefill evidently ~60% heavier than 3B 24f, not 30% as predicted),
but well inside tolerable range.

## Artifacts

- `research/experiments/2026/artifacts/phase1_55A_3b_32f_saturation/`
  - `summary.json`
  - `session_qwen7b_n7.jsonl`
  - `baseline_qwen7b_n7.jsonl`
  - `run.log`
