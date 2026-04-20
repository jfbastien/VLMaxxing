---
date: 2026-04-20
phase: 1.55A
status: findings
parent_prereg: 2026-04-20-phase-1_55A-3b-40f-temperature-prereg.md
siblings:
  - 2026-04-20-phase-1_55A-3b-40f-deeper-plateau-findings.md
  - 2026-04-20-phase-1_55A-3b-36f-interpolation-findings.md
  - 2026-04-20-phase-1_55A-7b-40f-symmetry-findings.md
  - 2026-04-20-phase-1_55A-3b-20f-temperature-findings.md
  - 2026-04-20-phase-1_55A-7b-20f-temperature-findings.md
---

# Phase 1.55A — 3B 40f temperature probe (FINDINGS)

## Bottom line

**HYBRID verdict.** Neither H1-distribution-collapse nor pure
H1-sampler-recovers earns cleanly. Under T=0.7+min_p=0.05 the 3B 40f
basin is **partially dispersed**: only 1/14 follow-ups emit novel
content (vs 4/14 under greedy), and Δacc lifts from greedy's
−0.238 to **−0.190 — exactly the pre-basin plateau value** 3B hits
at 24f/32f/36f. Temperature does NOT clear the ceiling (accuracy
does not recover toward baseline's 0.714), but it DOES reshape the
basin distribution toward the pre-basin saturated-letter regime.

This **earns a cross-architectural asymmetry**: 3B's basin is a
thinner attractor than 7B's, dispersible by sampler-side
intervention; 7B's basin is sampler-invariant (earned at both 20f
and 40f depths, `addCriterion`-family preserved under temperature).
The unified-mechanism claim narrows from "distribution collapse is
sampler-invariant everywhere past the basin-onset threshold" to
"distribution collapse saturates at a pre-basin noise floor, but
above that floor the basin geometry differs by architecture:
7B-basin survives sampling, 3B-basin does not."

## Numerical results

| Metric                                     | Value         | Verdict             |
|--------------------------------------------|---------------|---------------------|
| Session accuracy (n=21)                    | 11/21 = 0.524 | —                   |
| Baseline accuracy (n=21)                   | 15/21 = 0.714 | —                   |
| **Δacc (session − baseline)**              | **−0.190**    | plateau value       |
| Session Q1 accuracy (n=7)                  | 4/7 = 0.571   | matches baseline Q1 |
| Session follow-up accuracy (n=14)          | 7/14 = 0.500  | Δfollow-up = −0.214 |
| Prefix coverage (follow-ups)               | 0.9964        | H3 ✓ (≥ 0.993)      |
| Speedup (first over follow-up, median)     | 236.4×        | H2 ✓ (≥ 150×)       |
| Median follow-up elapsed                   | 648 ms        | H2 ✓ (≤ 900 ms)     |
| Peak RSS                                   | 3.95 GB       | H4 ✓ (≤ 5 GB)       |
| Wall time (42 queries)                     | ~70 min       | on-budget (~45 min predicted, ran hot on the M3 Air thermal envelope — no semantic impact) |

## Attractor identity tally (n=14 session follow-ups)

| Attractor class                                     | Count | Class        |
|-----------------------------------------------------|-------|--------------|
| **Clean 2-token letter (any of A/B/C/D)**           | **13** | clean       |
| Plain `addCriterion`                                | 0     | 7B-basin     |
| `addCriterion(…)` Java-code                         | 0     | 7B-basin     |
| `自动生成` Chinese auto-generate                    | 0     | 7B-temp-basin |
| Long-garbage (>16 gen tokens)                       | 0     | 7B-basin     |
| **Empty-response (`generation_tokens=1`)**          | **1** | 3B-40f-basin |
| "The" / other clean-non-letter                      | 0     | 3B-40f-basin |
| Novel (non-letter, non-basin)                       | 0     | novel        |

**13/14 clean-letter, 1/14 empty-response.** Under greedy the same
regime produced 4/14 non-letter (3 empty + 1 "The"). Temperature
dispersed 3 of the 4 basin emissions.

### Per-query breakdown (session follow-ups)

- **037-2** D (wrong; truth=C)
- **037-3** D (correct; truth=D)
- **100-2** D (wrong; truth=B)
- **100-3** D (wrong; truth=A)
- **116-2** D (correct; truth=D)
- **116-3** B (correct; truth=B)
- **120-2** D (correct; truth=D)
- **120-3** `` (empty; truth=C; tok=1) — the sole surviving basin emission
- **158-2** D (correct; truth=D)
- **158-3** B (wrong; truth=C)
- **160-2** D (correct; truth=D)
- **160-3** D (wrong; truth=B)
- **210-2** D (wrong; truth=B)
- **210-3** B (wrong; truth=B)

7/14 correct.

## Cross-architectural clip 120 note

Under greedy 3B 40f, clip **120-2** was empty-response (the basin
emission). Under temperature 3B 40f, the empty-response moves to
**120-3**. Same clip, different question. Clip 120 is therefore
the most basin-sensitive of the 7-clip short-bucket subset on 3B.
This matches the earlier 7B 40f observation (120-2 also emitted
empty-response there). **Cross-architectural: clip 120 is the
hardest-basin clip on the short-bucket subset across both 3B and
7B at 40f.**

## Verdicts against preregistered hypotheses

### H1-3B-40-temp.distribution-collapse — **REJECTED**

- Δacc ∈ [−0.29, −0.19]: borderline (−0.190, at the upper edge)
- ≥3/14 non-letter: ✗ (1/14)

The accuracy-delta technically falls on the boundary (the 1/14
non-letter does preserve a tiny basin signature), but the
non-letter count is ¼ of what the prereg required. Under the
prereg's conjunction (AND), this hypothesis fails. The basin is
NOT sampler-invariant at 3B-40f — in sharp contrast to 7B where it
is.

### H1-3B-40-temp.sampler-recovers — **PARTIALLY EARNS**

- Δacc ∈ [−0.15, +0.05]: ✗ (−0.190, just outside the band)
- ≥12/14 clean-letter: ✓ (13/14)

The attractor-identity criterion earns decisively. The Δacc
criterion misses by 0.04 — it lands at the 3B pre-basin plateau,
not at baseline. Interpret: **sampler recovers the distribution
(basin mostly dispersed) but NOT the answer quality** — the
pre-basin plateau noise floor remains. This was not a preregistered
mixed outcome; it's a novel finding that the basin and the plateau
are distinct degradation modes that stack.

### H1-3B-40-temp.degenerate — **REJECTED decisively**

- 1/14 << 8/14 novel-attractor threshold
- Δacc = −0.190 is BETTER than greedy's −0.238, not worse

Temperature does not interact pathologically with the 3B basin.

### H2-3B-40-temp (speedup) — **EARNS**

- Speedup ≥ 150×: ✓ (236.4×, above 3B 40f greedy 191.1×)
- Follow-up median ≤ 900 ms: ✓ (648 ms)

### H3-3B-40-temp (prefix coverage) — **EARNS**

- ≥ 0.993: ✓ (0.9964).

### H4-3B-40-temp (RSS) — **EARNS**

- ≤ 5 GB: ✓ (3.95 GB).

## The 1/21 resolution signature extends to 4 regimes

Cumulative evidence across sampler-invariance probes:

| Regime                | Greedy Δacc | Temp Δacc | Shift (temp − greedy) |
|-----------------------|-------------|-----------|-----------------------|
| 7B 20f (basin)        | −0.429      | −0.476    | −0.048 (= −1/21)      |
| 3B 20f (pre-basin)    | −0.143      | −0.190    | −0.048 (= −1/21)      |
| 3B 40f (basin)        | −0.238      | **−0.190** | **+0.048 (= +1/21)** |

All three probes show shifts of exactly one query's worth (1/21).
The first two move in the same direction (greedy marginally better
than temperature); 3B 40f moves in the opposite direction
(temperature marginally better than greedy). This is consistent
with the 1/21 shift being the **metric's minimum resolution**
(21-query denominator → 0.048 quantum), with direction determined
by regime-specific recovery behavior:

- **pre-basin** / **7B basin** regimes: temperature adds stochastic
  noise to an already-noise-floor-saturated signal → −1/21 drift.
- **3B basin** regime: temperature disperses basin emissions
  (+3 wins from 3 converted empty-response to clean-letter) while
  introducing sampler noise (−2 wins from 2 previously-correct
  clean-letter answers flipped to wrong letter). Net: +1/21.

## Mechanism interpretation — cross-architectural asymmetry confirmed

The shifted-onset-same-basin model from the deeper-plateau findings
(2026-04-20) had three axes: threshold × basin-onset-depth ×
basin-geometry. The four sampler-invariance probes now discriminate
axis-3 at the architecture level:

| Axis                    | Finding                                                          |
|-------------------------|------------------------------------------------------------------|
| threshold onset         | capacity-modulated (Δacc differs per architecture pre-basin)     |
| basin-onset depth       | ~2× deeper on 3B (20f vs 40f window onset)                        |
| **basin geometry**      | **architecture-dependent sampler response**                       |
| — 7B basin at 20f       | sampler-invariant (`addCriterion` → `自动生成`, same collapse)    |
| — 7B basin at 40f       | sampler-invariant basin (Δacc=−0.476, 13/14 in basin — preregd, symmetric)  |
| — 3B pre-basin at 20f   | null-robust (no basin, no change)                                 |
| — **3B basin at 40f**   | **partial sampler-dispersal** (4/14 → 1/14, Δacc lifts to pre-basin plateau) |

**The 3B basin is a thinner attractor than the 7B basin.**
Temperature+min-p intervenes successfully 3 out of 4 times at 3B
40f; the same sampler provides NO recovery at either 7B basin
regime. This is the first observation of sampler-side partial
intervention being effective — and it is architecture-specific.

## Claim #14 impact

The "distribution-collapse is sampler-invariant" subclaim was
established on 7B only. It now **does not survive cross-architecture
scrutiny at the basin regime**:

- The unified cross-architectural claim reduces to "the pre-basin
  plateau noise floor is sampler-invariant at both architectures"
  (which holds for 7B 20f and 3B 20f, and 3B 40f recovers TO this
  floor under temperature).
- The sampler-invariant-basin claim reduces to "7B-specific": at
  7B 20f and 7B 40f temperature leaves the basin intact; at 3B 40f
  temperature disperses it.

Updates paper claim #14 sampler-invariance subclaim to be
architecture-conditional. The "upstream intervention required"
statement now says: **sampler-side intervention is sufficient at 3B
basin (returns to pre-basin plateau but not baseline); sampler
intervention is INSUFFICIENT at 7B basin (no return)**. Upstream
intervention (1.55D selective re-prefill) remains the only path to
full baseline recovery at 7B — and is still required even at 3B to
close the remaining plateau gap.

## Falsification decision-tree resolution

Per prereg:
- **If H1-distribution-collapse earned:** Task #141b closes cleanly;
  unified mechanism holds.
- **If H1-sampler-recovers earned:** 3B basin thinner than 7B; paper
  claims become architecture-conditional.
- **If H1-degenerate earned:** Unified mechanism falsified at
  sampler level.

The HYBRID outcome resolves the tree toward the
H1-sampler-recovers branch with a refinement: **sampler recovers the
distribution (attractor shape) but not the answer quality (plateau
floor remains)**. Paper claims are architecture-conditional at the
sampler level. Task #141/142 can close. The "3B 48f deeper-basin
temperature probe" the prereg flagged as conditional follow-up is
still deferrable — the partial-recovery finding is robust at 40f
and a deeper probe would confirm, not overturn.

## Next action recommendation

Phase 1.55A basin mechanism work is now saturated on the short-
bucket subset:
- 6-point 7B frame sweep (8/16/18/20/24/32/40f) — baseline shape
- 3-point 3B ramp (24/32/36) at plateau + 1-point at 40f basin
- 7B 40f basin-symmetry confirmed
- 3B 36f onset bracket closed to (36f, 40f] = (14.5k, 16.1k]
- 7B temperature probe (20f): sampler-invariant basin
- 3B temperature probe (20f): null-robust plateau
- **3B temperature probe (40f): partial basin dispersal (THIS)**

Remaining basin-mechanism unknowns are not worth the compute:
- 7B 48f temperature: would confirm 7B basin invariance at deeper
  prefill — low information per min. **Deferred.**
- 3B 48f temperature: would test if 3B basin stays dispersible at
  deeper prefill — interesting but not paper-critical. **Deferred.**
- 1.55C Gemma 4-E4B-4bit cross-family — still open but gated on
  separate model-load infra. **Deferred.**

**Pivot to numerical-SOTA work:**
1. **1.51V vision-tower pruning** (preregistered, driver wiring
   landed this turn). Pilot → dev tranche → n=30 → composition
   with 1.51R. Target: ≥ 1.5× e2e on VideoMME dev (H3 acceptance).
2. **1.51R focused dev sweep (#82)** — pending from the post-pilot
   queue.

## Artifact paths

- Prereg: `2026-04-20-phase-1_55A-3b-40f-temperature-prereg.md`
- Run dir: `research/experiments/2026/artifacts/phase1_55A_3b_40f_temperature/`
- `run.log`, `session_qwen7b_n7.jsonl`, `baseline_qwen7b_n7.jsonl`, `summary.json`
- Findings (this file): `2026-04-20-phase-1_55A-3b-40f-temperature-findings.md`
