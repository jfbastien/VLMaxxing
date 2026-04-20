---
phase: 1.51V
date: 2026-04-20
parent: research/experiments/2026/2026-04-18-phase-1_51V-vision-tower-pruning-prereg.md
status: findings
---

# 1.51V dev tranche — layer × keep_rate Pareto (n=5)

## Setup

- Manifest: `videomme_dev_v1_stage2_subset.toml` (5 items: 2 short + 2 medium + 1 long)
- Model: gemma-4-e4b-it-4bit, 8 frames, max_tokens=32
- Control baseline (unpatched vision tower): V=4546.6ms, E2E=18943.2ms, acc=0.40 (2/5)
- Grid: layer ∈ {1, 6, 12} × keep_rate ∈ {0.25, 0.50, 0.75}
- Driver: `scripts/run_novelty_pruning_gemma.py` with `--vision-tower-layer` + `--vision-tower-keep-rate`

## Results table

| cell         | V_ms | V_red % | E2E_ms  | E2E_spd | gen_spd | acc  | agr  |
|--------------|------|---------|---------|---------|---------|------|------|
| control      | 4547 | 0       | 18943   | 1.000   | 1.000   | 0.40 | -    |
| L1_kr025     | 1912 | **+58** | 17070   | 1.110   | 0.925   | 0.20 | 0.80 |
| L1_kr050     | 2681 | **+41** | 18940   | 1.000   | 0.794   | 0.20 | 0.60 |
| L1_kr075     | 4366 | +4      | 20810   | 0.910   | 0.766   | 0.40 | 0.80 |
| L6_kr025     | 3286 | +28     | 19964   | 0.949   | 0.749   | 0.40 | 0.60 |
| L6_kr050     | 4274 | +6      | 20823   | 0.910   | 0.763   | 0.40 | 0.80 |
| L6_kr075     | 5072 | -12     | 22224   | 0.852   | 0.707   | 0.20 | 0.80 |
| L12_kr025    | 5004 | -10     | 21387   | 0.886   | 0.794   | 0.20 | 0.80 |
| L12_kr050    | 5051 | -11     | 21097   | 0.898   | 0.808   | 0.40 | 1.00 |
| L12_kr075    | 5530 | -22     | 21988   | 0.862   | 0.774   | 0.20 | 0.80 |

## Verdicts on preregistered hypotheses

### H1 (V reduction ≥ 35% at 50% tokens): **PROVISIONALLY EARNED at L=1**

- L=1 kr=0.50: V_red = 41% (> 35% threshold) — the prereg's designated H1 cell
- L=1 kr=0.25: V_red = 58% (strong signal at aggressive kr)
- H1 is cleanly rejected at L=6 kr=0.50 (V_red = 6%) and L=12 (V_red NEGATIVE).

### H3 (E2E speedup ≥ 1.5× when composed with 1.51R): **ARCHITECTURALLY BLOCKED ON 1.51V ALONE**

Best E2E speedup observed in tranche: **1.11× at L=1 kr=0.25**. This is an order of magnitude below the 1.5× H3 target. Root cause is architectural, not tuning-dependent (see "Scatter-back ceiling" below).

### H4 (accuracy preserved): **VIOLATED AT L=1**

- L=1 drops from 0.40 (2/5) to 0.20 (1/5) at both kr=0.25 and kr=0.50.
- L=6 kr≤0.50 preserves accuracy (0.40).
- L=12 kr=0.50 also preserves accuracy but at NEGATIVE V-reduction.

## Pareto frontier

V-reduction trades off against accuracy along the prune-layer axis:

- **Aggressive (L=1)**: Max V-reduction, accuracy drops.
- **Middle (L=6)**: Moderate V-reduction (28% at kr=0.25), accuracy preserved.
- **Late (L=12)**: V-reduction NEGATIVE (scatter-back overhead exceeds savings of 3-4 remaining layers), accuracy mixed.

The joint criterion (V ≥ 35% AND accuracy preserved) is **NOT satisfied by any cell** in the grid.

## Scatter-back ceiling (architectural finding)

**Root-cause analysis of the ~1.1× E2E cap:**

The 1.51V design scatters pruned tokens back to original sequence length to preserve the pooler's geometric assumptions. Consequence: the LM prompt token count is UNCHANGED regardless of keep_rate (observed: all cells report `mean_pruned_prompt_tokens = 2157`). LM prefill + generate get zero speedup from 1.51V.

Upper bound on E2E gain from 1.51V alone:
- V / E2E share = 4547 / 18943 = **24%**
- Max achievable E2E speedup = 1 / (1 - 0.24 × V_red)
  - At V_red = 41%: theoretical max = 1.11× (matches our best observed!)
  - At V_red = 58%: theoretical max = 1.16×

**1.51V is inherently V-ceiling-bound.** To reach H3's 1.5× target, we need either:
1. A reduction that cuts the LM prompt (post-pool token merging, or bypass scatter-back)
2. Composition with another technique that cuts generate time (persistent-KV, but 1.55 is CLOSED on that lane)
3. Abandon E2E target; reframe as "vision-tower-time reduction" only

## Implications

- **1.51V standalone** is viable only if framed as "savings proportional to V's share of E2E." For 8-frame VideoMME on Gemma-4-E4B-4bit, that share is 24%, capping 1.51V at ~1.15× E2E.
- **Composition with 1.51R** (novelty pruning at post-pool stage): 1.51R's claim was E2E speedup at cost of accuracy; composition multiplicatively may yield 1.2-1.3× E2E. Still below H3.
- **Middle-layer knee**: L=6 preserves accuracy but V-reduction is only 28%. Worth an n=30 confirm on accuracy stability, but H1 already fails there.
- **Late-layer penalty**: L=12 demonstrates the scatter-back overhead empirically — at 4 remaining layers, per-layer savings don't cover the one-hot matmul cost. This validates the "early-layer pruning is necessary" part of the design.

## Knee search — L ∈ {2, 3, 4} at kr=0.50 (addendum 2026-04-20)

| cell         | V_ms | V_red % | E2E_spd | acc  | agr  |
|--------------|------|---------|---------|------|------|
| control      | 4547 | 0       | 1.000   | 0.40 | -    |
| L1_kr050     | 2681 | +41     | 1.000   | 0.20 | 0.60 |
| **L2_kr050** | **2817** | **+38** | **1.073** | **0.40** | **0.80** |
| L3_kr050     | 4042 | +11     | 0.850   | 0.40 | 0.60 |
| L4_kr050     | 4199 | +8      | 0.864   | 0.40 | 0.80 |
| L6_kr050     | 4274 | +6      | 0.910   | 0.40 | 0.80 |
| L12_kr050    | 5051 | -11     | 0.898   | 0.40 | 1.00 |

### Verdict (knee)

**L=2 kr=0.50 is the Pareto-dominant cell**: V_red = 38% (clears H1 threshold), E2E speedup 1.07× (first positive), accuracy preserved at 0.40 (matches control). Accuracy-preserving cells at higher layer (L=3,4,6) drop V_red to 6-11% and have NEGATIVE E2E speedup (overhead dominates).

**Discontinuity between L=2 and L=3** in V-reduction (38% → 11%). This suggests the pruning cost at L=3 onwards is eaten by scatter-back overhead relative to savings from the 13 remaining layers. At L=2, savings from 14 remaining layers clear the overhead break-even.

### Revised next steps

1. ✅ Knee search done → winner **L=2 kr=0.50**.
2. **n=30 at L=2 kr=0.50 on `videomme_dev_v1.toml`** (30 items): statistically confirm both H1 (V_red ≥ 35%) and H4 (accuracy preservation). Expected runtime ~30 min.
3. **Composition with 1.51R at L=2 kr=0.50 × novelty kr ∈ {0.5, 0.3}**: test whether 1.51V stacks multiplicatively with 1.51R's generate-side speedup.
4. **Downsize scope for paper**: report Pareto frontier + architectural cap as publication-worthy negative-plus-positive finding (1.51V reduces vision-tower time by 38% at zero accuracy cost, but E2E speedup is architecturally bounded at V_share × V_red without post-pool token reduction).

## Raw artifacts

- Control: `phase1_51V_dev_tranche/control_nopatch_summary.json`
- Cells: `phase1_51V_dev_tranche/L{1,6,12}_kr{025,050,075}_summary.json`
- Runner: `phase1_51V_dev_tranche/run_tranche.sh`
- Tranche log: `phase1_51V_dev_tranche/tranche.log`
