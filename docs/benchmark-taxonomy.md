# Benchmark Taxonomy for Video-VLM Efficiency Research

Date: 2026-04-16
Parent: [literature-map-2026-04-16.md](literature-map-2026-04-16.md)

This taxonomy states why each benchmark is used or deferred, what it
controls for, and where our current slices stand. A benchmark's
presence here does not imply a local result.

## Axes we care about

| Axis | Question |
|---|---|
| **temporal-bias controls** | does the benchmark suppress single-frame / few-frame shortcuts? |
| **task format** | multiple choice / open-ended VQA / long-form answer |
| **scorer** | exact-match / strict parser / judge-model / metric-based |
| **frame structure** | short clip / medium / long / streaming |
| **current local slice** | what have we frozen and where? |
| **status** | active / deferred with reason |

## The four benchmarks in scope

### TOMATO (arXiv 2410.23266) — primary temporal stress benchmark

- **Temporal-bias controls**: explicitly designed to force multi-frame
  gain, order sensitivity, and frame-information disparity. Items
  are constructed so naive single-frame or out-of-order answers fail.
- **Task format**: multiple choice (letters A-F).
- **Scorer**: strict-choice parser on the local runner (exact letter
  match on the first recognized choice-letter in the generation,
  with the loose fallback parser kept as a documented backup).
- **Frame structure**: short clips (~8 uniform frames on our stack).
- **Current local slices**:
  - `tomato_motion_dev_v1.toml` (15 items, groups: direction,
    rotation, shape_trend) — used for planner search
  - `tomato_motion_holdout_v1.toml` (15 disjoint items, same groups)
    — phase 1.12 holdout
- **Why we use it**: our current strongest motion-reasoning test,
  and the benchmark the source whitepaper claims near-perfect
  agreement on.
- **Status**: **active**, primary temporal-reasoning benchmark.
- **Open**: Phase 1.20 N=30 enlargement required for cross-paper
  comparability.

### MVBench (arXiv 2311.17005) — broader video-reasoning benchmark

- **Temporal-bias controls**: the benchmark paper claims no task
  should be solvable with a single frame. In practice, our chosen
  motion-heavy subset retains partial first-frame solvability on
  some items (noted in phase 1.47 ablation). Treat as broader
  video-reasoning, not pure temporal stress.
- **Task format**: multiple choice.
- **Scorer**: exact-letter match.
- **Frame structure**: short clips (hosted predecessor-style
  selection, 8 uniform frames on our stack).
- **Current local slices**:
  - `mvbench_motion_dev_v1.toml` (15 items, groups:
    action_localization, fine_grained_action, object_interaction,
    moving_direction, moving_attribute) — phase 1.11 planner grid
  - `mvbench_motion_holdout_v1.toml` (15 disjoint items, same
    groups) — phase 1.12 holdout
- **Why we use it**: validates cross-benchmark generalization and
  gives us a different content mix than TOMATO.
- **Status**: **active** but narrower than the paper's scope. Do
  not claim our MVBench slice is representative of "MVBench" as a
  whole.
- **Open**: Phase 1.21 N=30 enlargement required after phase 1.12.B
  surfaced a holdout survivor.

### TempCompass (arXiv 2403.00476) — temporal-aspect-isolation benchmark

- **Temporal-bias controls**: explicitly uses "conflicting videos
  with the same static content but different temporal aspects" to
  suppress single-frame bias. Aspects directly isolated: speed,
  direction, event order, attribute change.
- **Task format**: mix of multiple choice and open-ended VQA.
- **Scorer**: task-specific (judge model for open-ended).
- **Frame structure**: short clips.
- **Why we want it**: TempCompass's weak categories (direction,
  speed, order, attribute change) are exactly the ones showing
  failure patterns on our current MVBench + TOMATO work. It is a
  better next diagnosis benchmark than a broader one.
- **Status**: **preregistered as phase 1.25**; not yet ingested.
  Corpus + parser work needed.
- **Priority**: should move up in the queue per the 2026-04-16
  audit; defer to after the sticky-dynamic + projector-group +
  N=30 work only because those are in-flight.

### Video-MME (arXiv 2405.21075) — long-horizon general-video benchmark

- **Temporal-bias controls**: general video QA; not specifically a
  temporal-stress benchmark. Multi-modal (includes audio / long
  clips / multiple camera angles).
- **Task format**: multiple choice.
- **Scorer**: exact-match.
- **Frame structure**: short / medium / long / very long.
- **Why we might use it**: once a stable Track A positive survives
  both TOMATO N=30 and MVBench N=30 holdout, Video-MME is the
  broader external-validity check.
- **Status**: **deferred** pending Track A + Track B both landing.
  Do not use as a diagnosis benchmark; the task heterogeneity
  dilutes failure-mode signal.

## Not in scope (but occasionally referenced)

- **UCF-Crime streaming anomaly**: what CodecSight evaluates.
  Different task format (video-level F1), different failure mode.
  Only referenced for Track B streaming-window harness comparison
  (phase 1.30), not for Track A quality claims.
- **PerceptionTest, NextQA, ActivityNet-QA, CVRR-ES, etc.**: used by
  CoPE-VideoLM as their benchmark suite. Not aligned to our
  temporal-reasoning focus; not planned.
- **VideoMME**: occasionally cited as the CoPE / FastVID reference;
  treat as external validity not diagnosis.

## What this taxonomy means for paper framing

1. Our Track A story must survive on TOMATO (primary) and MVBench
   (secondary) with N=30. TempCompass becomes the third benchmark
   when budget permits, and its per-aspect breakdown is the most
   useful mechanistic evidence for "where budget placement matters."
2. Do not generalize our MVBench motion slice to "MVBench" — be
   explicit about the motion-heavy group subset.
3. If / when Video-MME is evaluated, it's a breadth check, not a
   method-comparison arena.
