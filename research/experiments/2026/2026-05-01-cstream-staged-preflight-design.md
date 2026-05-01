---
date: 2026-05-01
phase: cstream-staged-preflight
status: design ready; implementation blocked on native c_stream arm
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

A one-hour run can still be useful, but only as a native-harness preflight. It
cannot promote C-STREAM by itself.

## Stage 0 — one-hour native-harness preflight

Implement this only after a real `c_stream_native` arm exists.

Scope:

- 2 recordings.
- 6–8 matched events.
- 8 frames only.
- Arms: `fresh_oracle_dense`, `low_fps_dense`, `screenshot_polling`,
  `recency_last_K`, `c_stream_native`.
- Include at least one stale-cache case by construction.
- Emit raw paired JSONL plus cache-correctness sidecar.
- Record per-frame update/rebuild stats, `vit_calls`, decode / routing /
  vision / prefill / generation timings, and source media paths.

Hard stop if any condition is true:

- Wall time exceeds 60 minutes.
- Any schema error, parse failure, missing raw response, missing source media
  path, or missing event/window metadata.
- `c_stream_native` is still representative-frame selection rather than a real
  per-frame cache update/rebuild mechanism.
- No stale-cache case appears.
- `c_stream_native` loses to both `screenshot_polling` and `recency_last_K`.
- `c_stream_native` loses to `low_fps_dense` by more than 1 event on the tiny
  sample.
- ViT-fire reduction is less than 2x vs `low_fps_dense`.
- Cache-correctness sidecar shows any deterministic choice/correctness drift.

Continue only if mechanics pass and native looks plausibly competitive:
complete schema, no parse failures, at least 2x ViT-fire reduction, no obvious
quality cliff.

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

## Implementation blocker

Do not launch Stage 0 yet. The repo still needs:

- a real `c_stream_native` arm,
- a stage controller that gates continuation,
- validator/table updates for throughput-axis metrics,
- a small event corpus with scored rows and stale-cache cases.

Until those exist, rerunning B3 or a one-hour proxy would only duplicate the
known negative result and should not be used as paper evidence.
