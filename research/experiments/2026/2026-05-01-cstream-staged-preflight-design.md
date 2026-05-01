---
date: 2026-05-01
phase: cstream-staged-preflight
status: cheap Stage 0 candidate preflight ready; native Stage 0 validator ready; native runner still blocked
related:
  - 2026-04-29-phase-B3-sam-streaming-baselines-findings.md
  - 2026-05-01-paper-defensibility-experiment-plan.md
---

# C-STREAM staged preflight design

## Current status

C-STREAM should stay candidate evidence unless a native throughput-axis run
passes. The existing B3 runner is a matched-baseline proxy, not native
C-STREAM: its `sam_policy` arm uses representative-frame selection, and B3
already showed the cheap negative signal (`low_fps_dense` 17/22 vs proxy 13/22).

A one-hour run can still be useful as a stop/go preflight for the current Qwen
session-streaming candidate. It cannot promote C-STREAM by itself.

## Stage 0A — one-hour candidate preflight

Ready command:

```bash
bash scripts/run_cstream_stage0_preflight.sh
```

This uses `scripts/run_phase1_30_scaleout_streaming.py` on a tiny VideoMME dev
slice (`CSTREAM_STAGE0_N_SEEDS=2`, 8 frames by default), compares cold dense
against the current Qwen session-streaming candidate, and writes
`research/experiments/2026/artifacts/cstream_stage0_preflight/stage0_summary.json`.

The validator is `scripts/validate_cstream_stage0_preflight.py`. It reports
`go_to_stage1=true` only if all gates pass.

This is intentionally a cheap candidate preflight. Passing it says "do not
kill C-STREAM yet." It does not prove the event-window native mechanism.

Scope:

- 2 VideoMME session seeds by default.
- 6 matched question rows by default.
- 8 frames only.
- Arms: cold dense vs current Qwen session-streaming candidate.
- Emit raw cold/streaming JSONL, paired queries, pair summary, and stage summary.
- Record decode / processor / query / end-to-end timings, prefix coverage, image
  token reuse, parse failures, and degeneracy.

Hard stop if any condition is true:

- Wall time exceeds 60 minutes.
- Fewer than 6 paired rows.
- Any cold or streaming parse failure.
- Any degenerate streaming response.
- Streaming accuracy drops by more than 10 percentage points vs cold dense.
- Amortized speedup is below 1.0x.
- Follow-up image-token reuse is not fully instrumented.
- Follow-up image-token reuse fraction is below 0.90.

Continue only if `stage0_summary.json` has `go_to_stage1=true`.

## Stage 0B — native event-window artifact gate

The native runner is not implemented yet, but its artifact gate is ready. A
future native event-window runner must emit schema-valid
`sam_scaleout_artifact_v1` rows and pass:

```bash
python3 scripts/validate_sam_scaleout_artifact.py \
  --jsonl <native-stage0.jsonl> \
  --phase C-STREAM \
  --min-rows 30 \
  --require-cstream-stage0 \
  --summary-output <native-stage0-summary.json>
```

The gate requires five arms per event (`fresh_oracle_dense`,
`low_fps_dense`, `screenshot_polling`, `recency_last_k`,
`c_stream_native`), 6–8 pair keys, at least 2 videos, source media hashes,
event/window metadata, a stale-cache case, native update/rebuild/skip counts,
and at least 2x fewer ViT calls for `c_stream_native` than `low_fps_dense`.

## Stage 1 — small signal pilot

Scope:

- At least 20 matched events across at least 2 videos.
- 8 frames only.
- Same five arms.
- Prefer scored multiple-choice rows. Keep LLM-judge rows separate.

Hard stop:

- `c_stream_native` accuracy vs `fresh_oracle_dense` worse than -0.10.
- More than 1 paired choice/correctness diff on scored rows.
- `low_fps_dense` beats native by more than 2/20 events.
- ViT-fire reduction remains below 2x.
- Any missing evidence-budget or stale-cache metadata.

## Stage 2 — full closure

Only run if Stage 0 and Stage 1 pass.

- 60 events × 3 video families.
- 8f / 16f / 32f, sequential.
- Continue from 8f to 16f only if 8f passes.
- Continue to 32f only if 16f passes and RSS/thermal are safe.
- Final gates: Δacc within ±0.05 vs fresh oracle on at least 40 scored rows,
  zero paired choice/correctness diffs on those rows, at least one stale-cache
  failure case, and at least 2x ViT-fire reduction vs low-FPS dense at matched
  accuracy.

## Implementation blocker after Stage 0

Stage 0A and the Stage 0B validator are ready. Do not claim either promotes
C-STREAM. To run Stage 1 / Stage 2 as paper-grade C-STREAM, the repo still
needs:

- a real `c_stream_native` arm,
- a stage controller that gates continuation,
- a small event corpus with scored rows and stale-cache cases.

Until those exist, rerunning B3 or a one-hour proxy would only duplicate the
known negative result and should not be used as paper evidence.
