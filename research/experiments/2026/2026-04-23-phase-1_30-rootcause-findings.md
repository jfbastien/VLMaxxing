---
phase: 1.30-rootcause
date: 2026-04-23
parent:
  - research/experiments/2026/2026-04-23-phase-1_30-rootcause-prereg.md
  - research/experiments/2026/2026-04-23-phase-1_30-sam-streaming-findings.md
artifacts:
  - research/experiments/2026/artifacts/phase1_30_rootcause_short_codex_20260423/
status: CLOSED-SCOUT. Phase A and Phase B completed. Phase C is not triggered because Phase A is unambiguous: H_V PASS, H_K FAIL, H_interaction FAIL, H_reset PASS, H_path PASS.
tracking: codex takeover 2026-04-23 after interrupted Claude Phase A run
---

# Phase 1.30 root-cause findings

## Question

The paired Sam-style 1.30 run reproduced large amortized speedup on Qwen
2.5-VL-7B-4bit VideoMME 8f, but failed the preregistered accuracy budget:

- paired cold vs streaming, dev+holdout union: 3.326x speedup PASS
- accuracy: cold 0.561 / streaming 0.368, delta = -0.193, FAIL versus
  the +/-0.05 budget

This decomposition asks why. The preregistered hypotheses split the loss into:

- V-only: vision-tower pruning at L=2, kr_V=0.50
- K-only: persistent-KV reuse across follow-up questions
- V+K interaction: the combined path is worse than additive
- hard-reset recovery: resetting the cache removes the K-only loss
- H_path: 1.30's Q0 pruned path matches the validated 1.51V pruned path

## Execution

The first Phase A attempt was interrupted with partial artifacts. It is preserved
outside the active artifact namespace at:

- `/tmp/claude/phase1_30_rootcause_short_interrupted_20260423_1813`

The completed rerun used a fresh output directory:

- `research/experiments/2026/artifacts/phase1_30_rootcause_short_codex_20260423/`

All six Phase A arms completed with 30 rows each:

- `cold_dense`
- `cold_pruned`
- `streaming_dense_off`
- `streaming_pruned_off`
- `streaming_dense_reset`
- `streaming_pruned_reset`

Phase B then ran the matched 1.51V Q0 parity check on the same ten Q0 items.
An extra dense Q0 path diagnostic was run after Phase B to verify the dense
1.30 and dense 1.51V paths also agree.

Two analysis/tooling fixes landed during this run:

- `scripts/analyze_phase1_30_rootcause.py` now sorts paired bootstrap keys so
  repeated analyzer runs emit identical confidence intervals.
- `scripts/phase1_30_rootcause_q0_compare.py` now normalizes 1.30 letter
  choices and 1.51V zero-based choice indices before computing H_path.

The runner itself hit a macOS Bash 3 portability bug after all six arms wrote
summaries (`${MODE^^}` uppercase expansion). The data are complete; the runner
completion sentinel has been fixed.

## Phase A result

Raw summaries:

| arm | all | q0 | q23 | wall_s | parse | degen |
|---|---:|---:|---:|---:|---:|---:|
| cold_dense | 0.733 | 0.900 | 0.650 | 1288.9 | 0 | 0 |
| cold_pruned | 0.400 | 0.500 | 0.350 | 1203.1 | 0 | 0 |
| streaming_dense_off | 0.667 | 0.900 | 0.550 | 408.1 | 0 | 0 |
| streaming_pruned_off | 0.300 | 0.500 | 0.200 | 409.6 | 1 | 1 |
| streaming_dense_reset | 0.733 | 0.900 | 0.650 | 1522.0 | 0 | 0 |
| streaming_pruned_reset | 0.400 | 0.500 | 0.350 | 1046.8 | 0 | 0 |

Accuracy deltas versus `cold_dense`:

| arm | all delta | q0 delta | q23 delta |
|---|---:|---:|---:|
| cold_pruned | -0.333 | -0.400 | -0.300 |
| streaming_dense_off | -0.067 | +0.000 | -0.100 |
| streaming_pruned_off | -0.433 | -0.400 | -0.450 |
| streaming_dense_reset | +0.000 | +0.000 | +0.000 |
| streaming_pruned_reset | -0.333 | -0.400 | -0.300 |

Paired bootstrap CIs are in
`research/experiments/2026/artifacts/phase1_30_rootcause_short_codex_20260423/analysis.txt`.

## Gate adjudication

**H_V: PASS.** V-only dominates the combined loss.

- V-only all-query loss: abs(-0.333)
- 0.5 x combined all-query loss: 0.217
- Gate: abs(V) >= 0.5 x abs(combined)

**H_K: FAIL.** K-only follow-up loss is smaller than the preregistered
dominance threshold.

- K-only q23 loss: abs(-0.100)
- 0.5 x combined q23 loss: 0.225
- CI crosses zero on the K-only delta

**H_interaction: FAIL.** The combined path is close to additive, not a
non-additive collapse.

- interaction point: -0.033
- paired CI includes zero
- abs(interaction) is far smaller than abs(V-only)

**H_reset: PASS.** Hard reset recovers the dense streaming follow-up loss.

- dense streaming q23 off: 0.550
- dense streaming q23 reset: 0.650
- cold dense q23: 0.650

For the pruned stream, hard reset recovers the K component and returns exactly
to the cold-pruned accuracy surface:

- streaming_pruned_reset all/q0/q23 = 0.400 / 0.500 / 0.350
- cold_pruned all/q0/q23 = 0.400 / 0.500 / 0.350

**H_path: PASS.** 1.30 cold-pruned Q0 matches the validated 1.51V pruned path
on the same ten Q0 items.

- choice agreement: 10/10 = 1.000
- correctness agreement: 10/10 = 1.000
- source: `q0_parity_compare.txt`

The extra dense-path diagnostic also passes:

- 1.30 cold_dense Q0 vs 1.51V dense Q0 choice agreement: 10/10 = 1.000
- correctness agreement: 10/10 = 1.000
- source: `q0_dense_path_compare.txt`

## Interpretation

The 1.30 Qwen 7B 8f composition failure is not primarily a K-cache failure and
not a V+K interaction collapse. On this short-scout slice, the loss is dominated
by the V-only vision-pruning arm at L=2, kr_V=0.50. Persistent-KV reuse adds a
small follow-up penalty, and hard reset removes that penalty, but neither term
explains the bulk of the negative result.

This is better science than the earlier "composition failed" statement:

- C-PERSIST remains a separate safety envelope. Dense streaming at 8f is nearly
  safe, and hard reset recovers the short-scout q23 loss.
- C-VISION remains a valid first-pass mechanism at its audited aggregate
  operating points, but this diagnostic shows a sharp item/protocol-local
  accuracy cliff when it is used as the Q0 leg of the Sam-style session bridge.
- Naive deployment composition should not use the L=2, kr_V=0.50 V path blindly
  as an admission policy. The practical fix is not "avoid C-PERSIST"; it is to
  make the V leg adaptive or more conservative before composing.

The most concrete item-level fact is Q0 sensitivity: `cold_dense` gets 9/10 Q0
items correct, while `cold_pruned` gets 5/10. Six Q0 choices differ; five of
those flips go from correct to wrong and one goes from wrong to correct. Both
the dense and pruned Q0 choices match their 1.51V counterparts exactly, so this
is not a serialization or runner-path mismatch.

## Phase C decision

Phase C is **not triggered** by the preregistered rule:

- H_interaction does not pass.
- The closest gate margin is not within 0.05.
- H_path passes after choice-normalization.

A full 57-seed Phase C would mostly confirm that the interaction is not the
dominant term. The higher-value next experiment is an adaptive V-leg follow-up:
find whether a safer Qwen C-VISION operating point (higher kr, layer change, or
admission by confidence/content class) restores the 1.30 accuracy budget while
preserving enough speedup to matter.

## Paper consequence

The paper should frame 1.30 as:

- speedup reproduced locally on Qwen 7B 8f under the Sam-style session protocol
- accuracy falsified at the preregistered budget
- root-cause localized to V-only Q0 pruning under this operating point, with a
  smaller K-only follow-up term and no evidence of non-additive V+K collapse
- deployment composition remains future work until the V leg has an admission
  policy or safer operating point

This is an anti-overclaim result, not an appendix shrug. It says exactly where
the bridge from local C-VISION/C-PERSIST to Sam-style deployment breaks.

## Reopen / next experiments

Priority follow-ups from this finding:

1. **1.30V adaptive V-leg sweep on the same short-scout Q0 set.** DONE as
   `2026-04-23-phase-1_30V-adaptive-vleg-findings.md`. Fixed-rate
   `kr_V in {0.67, 0.75}` did not recover the Q0 accuracy gate; future 1.30
   composition work should use adaptive admission/no-prune-on-risky-Q0 rather
   than another blind fixed-kr sweep.
2. **1.29 planner-accuracy n=30 short replication.** Phase A no longer blocks
   it; this remains the highest-value codec-native bridge if it replicates.
3. **Medium/long 1.29 and calibration ablation.** Run only after the n=30 short
   replication confirms that the first-point pass was not small-sample luck.
4. **Selective re-prefill / safer K policy.** Lower priority for this specific
   1.30 failure because K-only is not dominant here, but still important for
   broader C-PERSIST deployment.
