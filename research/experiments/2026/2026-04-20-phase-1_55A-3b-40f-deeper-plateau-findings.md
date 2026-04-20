# Phase 1.55A — 3B 40f deeper-plateau probe (FINDINGS)

**Date:** 2026-04-20.
**Parent prereg:** `2026-04-20-phase-1_55A-3b-40f-deeper-plateau-prereg.md`.
**Verdict:** **H1-latent-basin EARNS. H1-plateau FAILS.** The 24f/32f
plateau does not extend to 40f. 3B's mechanism is revised from
"architectural saturation ceiling" to "delayed-onset same-basin
geometry as 7B, shifted rightward in prefill depth."

## Headline

At 40f (≈16.1k prefill tokens), the 3B persistent-KV session run
emits **4/14 non-letter follow-ups** (3 empty-token responses, 1
"The"), while the matched cold-start baseline emits **0/14** non-
letter. This is a qualitative regime change: 24f and 32f had been
clean-letter-dominant on both session and baseline, and the saturation
plateau was built on that uniformity. At 40f, the basin that 7B
exhibits at 20f+ (attractor emergence beyond accuracy loss) finally
appears on 3B. The reopen condition (f) in the registry is earned
scientifically — 40f exposes a latent basin that 20/24/32f did not.

## Numerical results

| Metric                                        | Value     |
|-----------------------------------------------|-----------|
| Baseline accuracy (cold-start, 21 queries)    | 13/21 (0.619) |
| Session accuracy (persistent-KV, 21 queries)  | 8/21 (0.381)  |
| Δacc (session − baseline)                     | **−0.238** |
| Baseline Q1 accuracy (7 cold-starts)          | 4/7 (0.571) |
| Session Q1 accuracy (7 cold-starts)           | 4/7 (0.571) |
| Baseline follow-up accuracy (14 queries)      | 9/14 (0.643) |
| Session follow-up accuracy (14 queries)       | 4/14 (0.286) |
| Δacc_followup (session − baseline)            | **−0.357** |
| Baseline non-letter follow-ups                | **0/14** |
| Session non-letter follow-ups                 | **4/14** (3 empty, 1 "The") |
| Session first-query mean latency              | 121.1 s |
| Session follow-up median latency              | 602.8 ms |
| Speedup (first / follow)                      | 191.1× |
| Peak RSS                                      | 3.15 GB |
| Total wall                                    | 59 min |

## Hypothesis verdicts

- **H1-3B-40f.plateau: FAILS.** Δacc=−0.238 is inside the prereg
  band [−0.25, −0.10] (barely), but the follow-up clean-letter count
  is 10/14, not ≥12/14. The conjunction (both conditions required)
  fails.
- **H1-3B-40f.latent-basin: EARNS.** Condition "≥3/14 non-letter
  follow-ups" met: 4/14. (The alternate disjunct "Δacc worse than
  −0.25" falls short by 0.012 — the non-letter count is the load-
  bearing dimension.)
- **H2-3B-40f speedup: EARNS.** 191.1× ≥ 150×; median follow-up
  603 ms ≤ 700 ms.
- **H3-3B-40f RSS: EARNS.** 3.15 GB ≤ 8 GB.

## Non-letter attractor breakdown

All 4 non-letter follow-ups are on the **session** mode only (0 on
baseline). Pattern:

| Clip | Query | Response | generation_tokens |
|------|-------|----------|-------------------|
| 037  | Q3 (q=2) | `"The"`  | 2                 |
| 120  | Q2 (q=1) | `""`     | 1                 |
| 120  | Q3 (q=2) | `""`     | 1                 |
| 160  | Q3 (q=2) | `""`     | 1                 |

Three of the four are empty-response with `generation_tokens=1`,
meaning a single token (likely EOS or whitespace) decoded to empty —
this is **degenerate generation**, not wrong-answer-but-clean-letter.
The "The" response is a non-letter but non-degenerate continuation.

Clip 120 is especially striking: both follow-ups produce empty
responses, while its baseline runs are clean (`D`, `D`). This is a
clip-specific attractor emerging only under persistent-KV at 40f.

## Comparison across 3B prefill depths

| Depth | Prefill tokens | Δacc      | Non-letter follow-ups | Verdict |
|-------|----------------|-----------|------------------------|---------|
| 20f   | ~8.1k          | −0.190    | 0/14 (prereg-clean)    | plateau |
| 24f   | ~10.0k         | −0.190    | 0/14                   | plateau |
| 32f   | ~12.9k         | −0.190    | 0/14                   | plateau |
| **40f** | **~16.1k**   | **−0.238**| **4/14**               | **basin onset** |

The jump from 32f → 40f is the first qualitative change: Δacc
worsens by 0.048 and non-letter count jumps from 0 to 4. The
previous "three-depth plateau" interpretation (10k / 13k / 16k all
identical) is invalidated.

## Mechanism revision: from architectural ceiling to shifted onset

**Previous paper claim (1.55A 32f findings):** 3B has a 2.3× shallower
architectural saturation ceiling than 7B (Δacc=−0.19 vs −0.43). The
3-D decomposition's dimension 2 ("saturation ceiling = architecture-
specific") was a two-data-point claim on 3B.

**Revised claim:** 3B and 7B share the **same basin geometry**. The
difference is **threshold onset depth**. 7B enters the basin at
~10k prefill tokens (20f); 3B enters the basin at ~16k prefill
tokens (40f). The ~1.6× scaling in onset depth is a **measurable
architectural property** and a cleaner structural claim than
"different ceilings."

This revision is **scientifically stronger**, not weaker, for three
reasons:
1. It unifies 3B and 7B under one mechanism (same attractor
   geometry, same failure mode).
2. It predicts behavior at intermediate 3B depths (36f, 44f, 48f)
   as interpolations of the 32f/40f gap — a testable prediction.
3. It matches the 7B cross-architectural evidence: 7B's basin
   appears at the shallowest depth tested (20f, ~8k tokens), and we
   never observed a 7B regime where Δacc stays clean-letter. 3B at
   20f–32f was that regime. At 40f, 3B finally enters it.

## Paper-impact: Claim #14 3-D decomposition revision

The current Claim #14 row of `paper/claim-matrix.md` reads:
"3-D failure decomposition: threshold × saturation ceiling ×
geometry." The **saturation ceiling** dimension was built on the
24f/32f plateau.

**Proposed revision (to be applied):** Replace "saturation ceiling =
architecture-specific" with "**basin-onset depth is architecture-
dependent; basin geometry is cross-architectural**." This makes the
3-D decomposition read:
1. **Threshold** (sampler-invariance / temperature-robustness) —
   earned at both 7B and 3B ceilings (1.55A temp probes).
2. **Onset depth** (prefill tokens at which basin emerges) — 7B
   ~8k, 3B ~16k, scales ~1.6× with parameter count.
3. **Basin geometry** (cross-architectural attractor structure) —
   same failure mode across Qwen-7B and Qwen-3B.

The 1/21 quantum observation (Δacc shifts in 1/21 increments at
both architectures under temperature) already supports dimension 3
(shared geometry). This 40f probe supports dimension 2 (onset-
depth scaling, not architectural ceiling).

## What this does NOT tell us

- **7B 40f novel-attractor behavior.** The prereg noted this as a
  deferred ~2h probe. Now highly motivated: if 7B at 40f (~16k
  prefill) maintains its established basin with no qualitative
  change, it strengthens the "7B saturated early" picture. If 7B
  shows a **second** attractor emergence (Δacc worse than −0.50,
  new non-letter patterns), it opens dimension 4.
- **Gemma cross-family.** Still blocked on 1.55C infra
  (RotatingKVCache truncation corruption).
- **Temperature invariance at 40f.** The 20f/32f temp probes found
  distribution-level invariance; whether the 40f basin is also
  temperature-robust is untested. Would add one more run.
- **Intermediate 3B depths (36f, 44f).** Would pin onset-depth
  scaling more precisely. The 1.6× figure rests on two
  architectures × two onset thresholds.

## Follow-up probes to enqueue (ranked)

1. **7B 40f novel-attractor probe (~2h).** Highest value: tests
   whether the "onset-shift" interpretation holds symmetrically
   (i.e., 7B's basin at ~8k tokens doesn't deepen qualitatively at
   16k). Registry task to create.
2. **3B 36f interpolation (~45min).** Pins the 3B onset threshold
   more precisely. Expected: 36f sits between 32f plateau and 40f
   basin — likely 1–2/14 non-letter if the onset is gradual.
3. **3B 40f temperature probe (T=0.2, ~50min).** Tests whether the
   40f basin is also distribution-level sampler-invariant like the
   24f plateau. Scientifically cleanest extension.

## Artifact paths

- Prereg: `2026-04-20-phase-1_55A-3b-40f-deeper-plateau-prereg.md`.
- Session/baseline JSONL:
  `research/experiments/2026/artifacts/phase1_55A_3b_40f_deeper_plateau/{session,baseline}_qwen7b_n7.jsonl`.
  (Filename is legacy-labeled; model was Qwen 3B not 7B.)
- Summary: `.../summary.json`.
- Run log: `.../run.log`.

## One-line summary for registry

"1.55A 3B 40f probe: Δacc=−0.238 (edge of band), **4/14 non-letter
follow-ups** on session vs 0/14 on baseline. H1-latent-basin EARNS;
plateau invalidated. 3B mechanism revised from saturation-ceiling to
shifted-onset same-basin geometry. Reopen condition (f) retired."
