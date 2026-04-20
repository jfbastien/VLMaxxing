---
phase: 1.51R
date: 2026-04-21
parent: research/experiments/2026/2026-04-17-phase-1_51-novelty-pruning-gemma-prereg.md
prior:
  - research/experiments/2026/2026-04-18-phase-1_51R-stage5-cross-arm-synthesis.md
  - research/experiments/2026/2026-04-20-phase-1_51V-expansion-prereg.md
  - research/experiments/2026/2026-04-21-phase-1_51V-expansion-findings.md
status: closed (with one targeted follow-up flagged)
closes_task: 82
---

# Phase 1.51R — closure verdict post-1.51V expansion

## Headline

**1.51R is NULL on its own axis** (Stage 5 closure, 2026-04-18, holds): no anchor arm at kr=0.50 on raw-feature VideoMME n=30 clears the 1.10× E2E ceiling OR earns accuracy beyond noise.

**1.51R has one open composition signal under 1.51V**: EXP10 (V-patched at L=2 kr_V=0.50 stacked with novelty at anchor=none, kr_novelty=0.3) shows a **+4.7pp own-pair E2E lift over V-alone** (1.057× vs 1.010×, same thermal session) with **aggregate accuracy preserved** (-0.000 / +0.000 both 0.333) but **agreement dropping to 0.63** — the pruned path is answering ~11/30 items differently than the V-alone pruned path would, and aggregate accuracy is preserved by compensating right/wrong flips, not by concordance.

This is not a clean win. It is a real but noisy signal that warrants n=60 confirmation before being promoted to a composition-stack claim.

## Evidence

### Own-axis null (Stage 5 2026-04-18, unchanged)

| Arm | kr | E2E | acc Δ | agree | Verdict |
|-----|----|----:|------:|------:|---------|
| nuwa_pillar (5a)       | 0.50 | 0.987× | -0.167 | 0.43 | fail acc bar |
| max_min_diversity (5b) | 0.50 | 0.963× | -0.033 | 0.47 | within acc bar, below E2E bar |
| gemma_structural (5c)  | 0.50 | 0.992× | -0.033 | 0.53 | within acc bar, below E2E bar |

Arithmetic ceiling binds anchor-invariantly (task #88 prediction): `(D+V+G)/(D+V+G/s)` ≤ 1.10× even at s=∞ on 8-frame VideoMME. No anchor arm beats that ceiling.

### Composition on V-patched features (EXP09/EXP10 from 1.51V expansion, 2026-04-21)

Both runs: VideoMME dev v1 n=30, 8f, L=2 kr_V=0.50 (1.51V patched), plus novelty pruning. Own-pair same-session thermal pairing (decode_ms within-run identical by construction).

| Exp | anchor | kr_novelty | dense_acc | pruned_acc | agree | own-pair E2E |
|-----|--------|-----------:|----------:|-----------:|------:|-------------:|
| EXP02 (V-alone control) | —       | —    | 0.333 | 0.333 | 0.90 | 1.010× |
| EXP09 composition      | gemma_structural | 0.50 | 0.333 | **0.267** | 0.50 | **0.990×** |
| EXP10 composition      | none             | 0.30 | 0.333 | 0.333 | **0.63** | **1.057×** |

**Interpretation of EXP10**:
- ΔE2E vs V-alone = +4.7pp (1.057× / 1.010× = 1.047). Real same-session lift.
- Agreement 0.63 vs V-alone 0.90 (-0.27 concordance). The composition path disagrees with V-alone on ~8-11/30 items.
- Aggregate accuracy preserved (both 0.333) because right/wrong flips compensate. This is the "noisy preserve" signature: unreliable item-level behavior masked by aggregate pass-through.

**Interpretation of EXP09**:
- ΔE2E vs V-alone = -2.0pp (0.990× / 1.010× = 0.980). Real same-session slowdown.
- Agreement 0.50 even worse. Accuracy drops -6.7pp.
- This replicates the Stage 5 own-axis null pattern — adding novelty on top of V-patched features does not help at kr_novelty=0.50 under gemma_structural.

## Decision

**1.51R formally CLOSED as null on own axis** (Stage 5 verdict holds; no new same-axis evidence contradicts).

**1.51R composition-with-1.51V flagged as an OPEN n=60 lane**: specifically, the (anchor=none, kr_novelty=0.30) cell under 1.51V at L=2 kr_V=0.50 on VideoMME 8f. Decision rule for promotion:

- Run n=60 at the EXP10 configuration, thermally paired with an n=60 V-alone (EXP02 replication).
- Promote to "composition stack" if: own-pair E2E lift ≥ 4pp over V-alone *and* agreement ≥ 0.75 *and* aggregate accuracy within -0.067 of V-alone.
- Reject as "aggregate-preserve noise" if: agreement < 0.70 even when aggregate accuracy passes.

The agreement bar is the critical one. A speedup with low agreement does not help the paper — it erodes trust in the stacked pipeline's per-item behavior.

## What this leaves for the paper

- **1.51R does not advance the SOTA number**. Null on own axis at Gemma-4-E4B/VideoMME. Keep the methodology contribution (five literature-grounded anchors evaluated; all bounded by arithmetic ceiling).
- **1.51V × 1.51R composition (EXP10 cell) is ambiguous**, not clean. Paper-table framing should not yet claim a stacked win — await n=60 follow-on.
- **Stage 5 cross-arm synthesis remains the canonical 1.51R finding**: anchor choice drives a 13.4pp accuracy swing, but no anchor clears the arithmetic ceiling. Publishable as methodology.

## Artifacts

- Own-axis null: `research/experiments/2026/2026-04-18-phase-1_51R-stage5-cross-arm-synthesis.md`
- Composition evidence: `research/experiments/2026/artifacts/phase1_51V_expansion/exp02_*_summary.json`, `exp09_*_summary.json`, `exp10_*_summary.json`
- Follow-up lane (n=60 EXP10 replication): not run in this batch; requires fresh sandbox approval.

## Registry and task ledger

- Task #82 (P1: 1.51R focused dev sweep post-pilot): **completed with null verdict + one flagged follow-up**.
- Registry 1.51R entry should reflect: "CLOSED null on own axis 2026-04-18; composition re-check lane n=60 open pending sandbox approval 2026-04-21."
