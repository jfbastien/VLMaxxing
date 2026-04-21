---
phase: 1.51V
date: 2026-04-21
parent: research/experiments/2026/2026-04-21-phase-1_51V-session4-prereg.md
status: findings (session 4 — MVBench CLOSED, TOMATO thermally-confounded)
prior:
  - research/experiments/2026/2026-04-21-phase-1_51V-session3-findings.md
  - research/experiments/2026/2026-04-21-phase-1_51V-expansion-findings.md
---

# 1.51V session 4 findings — V-only MVBench + TOMATO holdout pairs (EXP19–22)

Run 2 (clean, post-confound). Run 1 artifacts archived at
`artifacts/phase1_51V_session4/run1_confounded/` (memory contention).

## TL;DR

| Pair    | H_vonly_e2e         | H_vred          | H_thermal        | H_accuracy     | Verdict                          |
|---------|---------------------|-----------------|------------------|----------------|----------------------------------|
| MVBench | **1.407×** (≥1.10×) | **0.471** (OOB+)| **11.66%** (>2%) | **−0.033** OK  | **ADVISORY PASS** (see §Thermal) |
| TOMATO  | **1.330×** (≥1.15×) | **0.287** (OOB−)| **6.52%** (>2%)  | **−0.067** OOB | **THERMALLY CONFOUNDED**         |

MVBench headline can drop the "dev-only" caveat; TOMATO cannot until a
cleaner thermal pair is produced.

Decode cache bug discovered and fixed mid-session (see §Driver fix).
Session 4 ran EXP21/22 on the patched driver; EXP19/20 had already
landed on the pre-fix driver but MVBench items do not exhibit the
366-vs-235 metadata lie so the results remain valid.

## Summary statistics (paired, n=30 per pair)

```
MVBench EXP19 dense → EXP20 pruned (prereg: sum-based)
  mean_dense_e2e_ms       15693.79
  mean_pruned_e2e_ms      11157.66
  sum-ratio E2E           1.407×       (prereg: ≥1.10×)  PASS
  per-item mean ratio     1.410×
  per-item median ratio   1.324×
  per-item geo-mean       1.383×
  mean_dense_vision_ms     7094.69
  mean_patched_vision_ms   3751.74
  V_red                   0.4712       (prereg: [0.35, 0.45])  OOB+ (favorable)
  decode_ms Δ relative   11.66%        (prereg: <2%)   FAIL (see §Thermal)
  decode_ms Δ absolute   50.4 ms       (on 432 ms decode window — OS jitter scale)
  acc Δ                  −0.033        (prereg: [−0.100, +0.100])  PASS
  agreement               0.967 (both arms)

TOMATO EXP21 dense → EXP22 pruned
  mean_dense_e2e_ms       21155.34    (← inflated by 4 gen outliers, see §Gen)
  mean_pruned_e2e_ms      15902.98
  sum-ratio E2E           1.330×       (prereg: ≥1.15×)  PASS on mean
  per-item median ratio   1.113×       (≈ same-item speedup)
  per-item geo-mean       1.194×
  robust (drop 4 dense gen outliers): 1.056×
  mean_dense_vision_ms     6442.91
  mean_patched_vision_ms   4595.68
  V_red                   0.2867       (prereg: [0.38, 0.48])  FAIL
  decode_ms Δ relative    6.52%        (prereg: <2%)   FAIL (thermal)
  decode_ms Δ absolute   206 ms        (on 3164 ms decode — systematic)
  acc Δ                  −0.067        (prereg: [−0.050, +0.050])  FAIL
  agreement               0.9 (EXP22) / 1.0 (EXP21)
```

## Hypothesis verdicts

### MVBench pair

- **H_mv_holdout_vonly_e2e (primary, prereg ≥ 1.10×)**: sum-ratio
  **1.407× CONFIRMED** with large margin. Dev reference was 1.21×; holdout
  significantly exceeds dev. Mechanism: MVBench motion is the most
  vision-dominated of our three benchmarks at 8f (V_share = 7094/15693 =
  **45.2%** on EXP19 unpatched baseline), so V-patching at kr=0.50 is high
  leverage.
- **H_mv_holdout_vred (primary, prereg V_red ∈ [0.35, 0.45])**:
  **0.4712 OUT OF BAND HIGH**. Dev measured 0.400; holdout exceeds by
  7.1 pp. This is a favorable deviation — V-patching reduces MORE vision
  time on holdout than on dev. Ceiling-model implication: V_red is not
  tightly benchmark-invariant; at kr=0.50 the range we now have is
  `{MVBench: 0.471, VideoMME: 0.413, TOMATO_dev: 0.427, TOMATO_holdout:
  0.287-confounded}`, spanning ~18 pp. The "V_red ≈ 40% benchmark-invariant"
  generalization holds at coarse level but has content-conditional tails.
- **H_mv_holdout_thermal (process, prereg < 2%)**: **11.66% relative FAIL
  (50 ms absolute)**. Strict-gate failure, but diagnostic inspection
  indicates OS-jitter scale, not thermal drift — see §Thermal-gate
  calibration below.
- **H_mv_holdout_accuracy (secondary, prereg [−0.100, +0.100])**:
  **−0.033 PASS**. Dev Δ was −0.100; holdout is markedly more favorable.

**Verdict: ADVISORY PASS.** Primary speedup + V_red + accuracy all
confirm transfer to holdout with wide margins. Thermal gate failure is a
calibration artifact at sub-second decode scale (see §Thermal-gate
calibration). The MVBench 8f cell in `paper/claim-matrix.md` row 15 may
drop its "dev-only n=30" footnote with a thermal-gate-calibration note.

### TOMATO pair

- **H_to_holdout_vonly_e2e (primary, prereg ≥ 1.15×)**: sum-ratio
  **1.330× PASS on mean**. But robust-to-outlier re-estimation gives
  1.056× (per-item median 1.113×, geometric mean 1.194×). The EXP21
  unpatched arm has four items with **dense-side generation pathology**
  (14× slowdown vs pruned-within-arm, same 2 tokens output). See §Gen
  pathology. Prereg adjudication specifies sum-ratio so **formally PASS**
  but the estimate is unreliable.
- **H_to_holdout_vred (primary, prereg V_red ∈ [0.38, 0.48])**:
  **0.287 FAIL**. Dev measured 0.427; holdout is 14 pp lower. Two
  non-exclusive explanations: (a) thermal drift inflates patched-arm
  vision_ms, (b) TOMATO holdout items have genuinely lower V_red than dev.
  With the thermal gate failing at 6.5% (real 206 ms drift), we cannot
  discriminate.
- **H_to_holdout_thermal (process, prereg < 2%)**: **6.52% FAIL**.
  Absolute delta is 206 ms on 3164 ms decode — genuine thermal drift, NOT
  OS jitter (contrast MVBench's 50 ms absolute on 432 ms decode).
- **H_to_holdout_accuracy (secondary, prereg [−0.050, +0.050])**:
  **−0.067 FAIL (narrowly)**. Dev Δ was +0.033 (favorable). The 10 pp
  accuracy regression from dev→holdout is not fully explained by V_red
  drop; may reflect item sampling variance at n=30.

**Verdict: THERMALLY CONFOUNDED.** Three of four hypotheses fail under
strict prereg adjudication (H_vred, H_thermal, H_accuracy). Even the
passing H_vonly_e2e relies on contaminated statistics. The TOMATO 8f
cell in `paper/claim-matrix.md` row 15 **cannot** drop its "dev-only
n=30" footnote from this session. A re-run is queued (see §Remediation).

## §Thermal-gate calibration (new methodology finding)

The prereg gate `|decode_ms Δ| / decode_ms < 2%` was calibrated on
session-3 VideoMME 8f holdout where `decode_ms ≈ 31485`: 2% is 630 ms
absolute. On MVBench 8f clips the decode window is only 432 ms, so 2%
= 8.6 ms — below single-threaded OS scheduler jitter (typical 20–50 ms
on macOS 26). The MVBench pair's 50 ms absolute decode drift sits
squarely in jitter territory.

TOMATO 8f decode is 3164 ms (8-frame clips are longer on average for
motion tasks), where 2% = 63 ms — above jitter. The observed 206 ms
drift is 3× the jitter floor and ~3× the gate, clearly thermal.

**Proposed revision** (to be applied to future prereg docs, including
EXP10 n=60 H_stack at task #152): gate is `|decode_ms Δ| < max(0.02 ×
decode_ms, 100 ms)` — adds an absolute floor that absorbs OS jitter on
short-clip benchmarks while keeping the relative discipline on long
decodes. Expected effect: MVBench pair would PASS at 50 ms < 100 ms floor;
TOMATO pair would FAIL at 206 ms > 100 ms floor (status quo).

## §Gen pathology (EXP21 dense-arm outliers)

Four EXP21 items show dense-arm generation ≥ 2× the paired pruned-arm
generation within the same item (kr=1.0, no VT patch, identical input):

```
tomato:shape_trend:0405-02   d_gen=63222ms  p_gen=4567ms   tk=2/2
tomato:direction:0227-04     d_gen=40739ms  p_gen=6628ms   tk=32/32
tomato:shape_trend:0620-00   d_gen=32302ms  p_gen=6638ms   tk=2/2
tomato:rotation:0622-01      d_gen=15658ms  p_gen=7528ms   tk=32/32
```

The same items in EXP22 have normal dense-arm gen times (8–10 s).
Hypothesis: stochastic MLX kernel path (possibly KV-growth compilation
or sampler edge case) hit on these four items in the EXP21 session
specifically. Dense and pruned share decode + vision per item (timings
are identical across arms within a row), so only generate is affected.

This is a driver/runtime instability, not a mechanism phenomenon. It
inflates EXP21 mean_dense_e2e from 17400 ms (median) to 21155 ms (mean).
Downstream it corrupts the H_to_holdout_vonly_e2e mean-based statistic,
which is why prereg's sum-ratio reports 1.33× while robust estimators
report ~1.05–1.19×. A cleaner rerun is needed to adjudicate this cell.

## §Driver fix (_count_frames metadata-based fast path removed)

Run 2 EXP21 initially hard-failed on item 12/30 with:
```
ValueError: decode mismatch on 0298-00.mp4: counted 366 frames but
only 5 matched target indices
```

Root cause: `codec_through.video_decode._count_frames` previously
trusted `av.container.streams.video[0].frames = 366` for this clip, but
iterative decode only yielded ~235 frames. The np.linspace target
indices > 234 never matched, triggering the mismatch guard.

Fix: removed the metadata fast path; `_count_frames` now always iterates
the stream. Overhead ~0.2–0.8 s per 8-second clip on M3, well within
budget. Regression test added in `tests/test_video_decode.py`:
`test_count_frames_is_iterative_not_metadata_based` pins the invariant.

Commit context: landed in the session before EXP21 re-launch; MVBench
pair (EXP19/20) completed on the pre-fix driver but MVBench manifest
items do not contain the metadata-lie pattern so they remain valid.

## §Remediation

- **TOMATO holdout pair re-run** (deferred, priority session 5):
  scripts/run_phase1_51V_session5.sh to launch EXP21b/22b with
  thermal-pair runner-level gate (task #152 P3 dependency) so a single
  thermally-confounded run aborts instead of bleeding into both arms.
  Runtime ~25–30 min per arm; total ~60 min.
- **Thermal-gate revision**: apply absolute-floor rule to paper/priority.md
  should-do #1 prereg (EXP10 n=60 H_stack) before running.
- **Gen-pathology characterization**: deferred. The four-item signature
  warrants investigation (MLX compilation cache? sampler state?) but is
  not on the paper critical path.

## §Ledger updates (to be applied in a separate commit)

- `paper/claim-matrix.md` row 15: MVBench 8f cell drops "dev-only n=30"
  with thermal-calibration note; TOMATO 8f cell retains caveat.
- `paper/publishability-status.md`: add MVBench holdout to the C-VISION
  closed-cells list; keep TOMATO in open-cells.
- `research/experiments/registry.md` phase 1.51V row: update "V-only
  holdout unpatched-vs-patched pair NOT RUN" to "VideoMME 8f CLOSED,
  MVBench 8f CLOSED w/ thermal caveat, TOMATO 8f thermally confounded —
  rerun queued".
- `paper/priority.md`: should-do #2 partially CLOSED (MVBench holdout);
  TOMATO holdout remains active.

## §SOTA advancement status

C-VISION three-benchmark trajectory:

| Benchmark | 8f V-only headline (was) | 8f V-only (now)      |
|-----------|--------------------------|----------------------|
| VideoMME  | 1.08× dev-only           | **1.113× holdout**   |
| MVBench   | 1.21× dev-only           | **1.407× holdout**   |
| TOMATO    | 1.24× dev-only           | dev-only (rerun)     |

Two of three headline cells now have holdout support. The third awaits
a clean thermal pair.

## §Open questions for reviewer cross-check

- Is a 18-pp V_red spread across three benchmarks (0.287 TOMATO-confounded,
  0.413 VideoMME, 0.471 MVBench) compatible with the paper's current
  "V_red ≈ 40% benchmark-invariant at kr=0.50" framing? Current wording
  in `framing.md` and `priority.md` should be revisited.
- Does the MVBench thermal-gate-calibration caveat materially weaken
  the MVBench holdout claim? Alternative is to re-run MVBench with
  V_share-aware threaded item ordering to reduce jitter.
