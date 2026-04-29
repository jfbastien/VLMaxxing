# 2026-04-29 Scale-Out Artifact Handoff

Status: preregistered handoff plan; no scale-out results imported here yet.

## Goal

Promote external 26B streaming work from "partner evidence" to first-class
same-graph evidence by requiring the same paired-artifact structure used in
this repo: item ids, raw outputs, parse failures, paired correctness/choice
diffs, timing, memory, and confidence intervals.

## Hardware / Runtime

- Machine: M5-class MacBook Pro with 128 GB unified memory.
- Primary model: the exact 26B Gemma/Qwen-family model used in prior
  scale-out work. Run from `codec-through`; if prior external prototype code
  is used as reference or called by a wrapper, record the reference commit and
  runtime provenance in the findings note.
- Record full model id, model hash, quantization, runtime commit,
  `codec-through` commit, and Metal/macOS versions.
- Do not inherit this repo's 12 GB MLX memory cap. That cap is a local M3
  mitigation for a Metal panic and would invalidate the scale-out run.

Rows should validate against
`research/schemas/scaleout_artifact_v1.schema.json`.

## Acceptance Contract

Scale-out results become same-graph evidence only if the raw row JSONL validates
against `research/schemas/scaleout_artifact_v1.schema.json` and the
phase-specific gates below. The schema is intentionally provenance-heavy:
stage timings, prompt/input/frame hashes, parse failures by arm, cache
topology, runtime metadata, command line, and memory definition are required on
every paired row.

Use `scripts/validate_scaleout_artifact.py` before importing artifacts into
this repo. The validator enforces the base schema and the B0b/B3/B5 gates that
are easy to overclaim by prose.

## B0b — Expanded Cache-Correctness Gate

Hypothesis: the 26B runtime's prompt-cache semantics match the local paired
protocol closely enough to support C-PERSIST replication.

Protocol:
- Minimum: 7 videos x 3 questions = 21 cross-turn rows.
- Also export the matching 21 within-turn cache-equivalence replay rows; the
  repaired runtime must prove the within-turn path did not regress.
- Deterministic decoding.
- Arm labels: `baseline_arm=cold_dense`, `arm=within_turn_cache_replay`, and
  `arm=cross_turn_warm`.
- Require identical prompt text and frame selection between paired arms.
- Require raw prompt, raw response, frame ids/hashes, prompt hashes,
  input-id hashes, cache-topology metadata, prefix-hit metadata, and per-arm
  stage timings on every row.
- Export one JSONL row per paired query.

Gate:
- 0 parse failures.
- 0 choice diffs, 0 correctness diffs, and 0 raw-text diffs across all paired
  rows.
- Identical prompt hashes, input-id hashes, and frame hashes between paired
  arms.
- Prefix-hit and prefix-coverage metadata are non-null and positive on
  follow-up rows.

Interpretation:
- Pass gates B1/B2. Fail means the scale-out runtime needs cache debugging before
  cross-turn C-PERSIST numbers can be used as first-class evidence.

Validation command:

```bash
python scripts/validate_scaleout_artifact.py \
  --jsonl scaleout_b0b_cache_correctness.jsonl \
  --phase B0b \
  --min-rows 42 \
  --require-zero-choice-diffs \
  --require-zero-correctness-diffs \
  --require-zero-text-diffs \
  --require-zero-parse-failures \
  --require-matching-input-hash \
  --require-matching-prompt-hash \
  --require-matching-frame-hashes \
  --require-positive-prefix-on-followups \
  --require-b0b-protocol \
  --summary-output scaleout_b0b_cache_correctness_summary.json
```

Expected runtime: 10-30 minutes.

## B1 — 26B C-PERSIST Replication

Hypothesis: adaptive/fixed C-PERSIST is not a Qwen-7B/MLX-local artifact; the
same answer-stability envelope appears at 26B scale.

Prerequisite: B0b passes. If B0b fails, B1 is blocked.

Protocol:
- Use the same 7 short clips as local 1.55F where possible.
- Arms: cold dense baseline, fixed K=1, adaptive post-Q2 repaired cache.
- Deterministic decoding first; optional T=0.7 after deterministic pass.
- Export raw paired JSONL plus summary with Wilson or bootstrap CIs.

Primary metrics:
- Paired choice/correctness diffs.
- Parse failures.
- Follow-up speedup vs cold dense.
- Peak memory/RSS equivalent.

Gate:
- Deterministic: <=1/21 correctness diffs and <=2/21 choice diffs.
- Parse failures <=1/21.
- Follow-up speedup reported, not gated.
- Findings summary must report correctness diffs, choice diffs, parse
  failures, same-class follow-up speedup, all-query speedup, and row count.

Expected runtime: 1-3 hours depending on 26B decode speed.

## B2 — 26B Many-Turn Streaming Horizon

Hypothesis: the practical value of C-PERSIST at 26B is a measured horizon, not
only a two-follow-up result.

Prerequisite: B0b passes. If B0b fails, B2 is blocked.

Protocol:
- Same stateless repeated-query design as local 1.55L unless the scale-out runtime
  already has a true conversational-history harness.
- Horizons: 10, 20, 50 turns.
- Policies: fixed K=1, adaptive post-Q2/post-previous repaired cache,
  scheduled refresh every 10 turns.
- Dense control must be turn-matched with the exact same prompt sequence.

Gate:
- Report longest horizon with <=3% paired choice and correctness drift.
- Flag a cliff if any 10-turn bucket exceeds 10% drift.
- Findings summary must report drift by horizon and by 10-turn bucket, plus
  the longest horizon satisfying the <=3% criterion.

Expected runtime: 4-12 hours.

## B3 — Matched Streaming Baselines

Hypothesis: C-PERSIST is not only beating an overprovisioned dense baseline; it
also beats simpler streaming policies under matched evidence budgets.

Baselines:
- Screenshot polling / fixed-cadence dense.
- Low-FPS dense.
- Recency / last-K frames.
- scale-out policy.

Protocol:
- Use the same recordings, event ids/timestamps, observation windows,
  questions, answer keys, scoring, and artifact schema across all arms.
- Record the evidence budget on every row: cadence, FPS, last-K, selected frame
  indices, selected frame ids/hashes, and observation window.
- Evidence-budget metadata must be present on every row, but it is
  policy-specific and is not required to be identical across arms.
- Use the same videos/questions as B1/B2 where possible, but B3 may run even
  if B0b blocks cross-turn PromptCacheState, as long as the compared policy
  does not depend on the broken cache path.
- Export the same paired JSONL schema.
- Include at least one stale-cache failure case where recency/polling and
  C-PERSIST disagree; raw outputs are required.

Interpretation:
- If low-FPS dense is competitive, add low-FPS + C-PERSIST/adaptive as a
  follow-up before claiming dominance.
- If recency wins on specific items, use them as limitations/failure cases.

Validation command:

```bash
python scripts/validate_scaleout_artifact.py \
  --jsonl scaleout_b3_streaming_baselines.jsonl \
  --phase B3 \
  --min-rows 80 \
  --min-pair-keys 20 \
  --min-videos 2 \
  --require-arms screenshot_polling,low_fps_dense,recency_last_k,scaleout_policy \
  --require-zero-parse-failures \
  --require-b3-matched-events \
  --summary-output scaleout_b3_streaming_baselines_summary.json
```

Expected runtime: 4-8 hours for a minimal bundle.

## B4 — 26B Sparse-ViT / C-CEILING Validation

Hypothesis: the arithmetic ceiling that predicts local sparse-ViT wall-clock
also predicts scale-out behavior when the scale-out runtime actually skips ViT work.

Only run if the scale-out runtime has a real compact/sparse vision path. Do not count
dense-with-zeros as Track B.

Protocol:
- 8f and 32f first.
- Keep rate 0.50 or the closest architecture-safe point.
- Report dense vision share, observed vision reduction, predicted E2E speedup,
  observed E2E speedup, and residual.

Gate:
- Complete pairing and clean parsing.
- Delta accuracy >= -0.05.
- Positive E2E speedup.
- Actual-vs-predicted residual within +/-0.05x.

Expected runtime: 3-8 hours depending on 26B vision cost.

## B5 — S4 Exactness Re-Export / Accounting Cleanup

Hypothesis: the original S4 evidence can be re-exported with enough per-row
provenance to support the bounded paper claim without importing inconsistent
accounting.

Current admissible bound:
- Supported: 0 accuracy delta on 1,937 sparse-sampled items.
- Supported: byte-identical raw-paired verification on 513 rows.
- Not supported until re-exported with raw paired rows: byte-identical
  exactness over all 1,937 rows or any finer breakdowns from inconsistent S4
  accounting.

Protocol:
- Export `scaleout_b5_s4_accuracy_1937.jsonl` with 1,937 paired rows, item ids,
  parse failures split by arm, raw paired responses, correctness fields, CIs,
  model/runtime/hardware metadata, commit, command line, prompt hash, frame
  ids/hashes, frame count, policy, source artifact path/hash, and provenance
  note.
- Export `scaleout_b5_s4_raw_paired_513.jsonl` with the 513 raw-paired rows used
  for byte-identical verification.
- If the scale-out bundle can re-export all 1,937 rows with raw paired
  responses, treat that as a new stronger artifact and validate it explicitly;
  do not infer it from the older accounting.
- If the 1,937-row source cannot provide raw paired responses, it cannot pass
  this schema as same-graph evidence; keep the paper claim bounded to imported
  zero-accuracy-delta support plus the 513 raw-paired exactness audit.

Validation commands:

```bash
python scripts/validate_scaleout_artifact.py \
  --jsonl scaleout_b5_s4_accuracy_1937.jsonl \
  --phase B5 \
  --expected-row-count 1937 \
  --require-zero-correctness-diffs \
  --require-zero-parse-failures \
  --require-b5-provenance \
  --summary-output scaleout_b5_s4_accuracy_1937_summary.json

python scripts/validate_scaleout_artifact.py \
  --jsonl scaleout_b5_s4_raw_paired_513.jsonl \
  --phase B5 \
  --expected-row-count 513 \
  --require-zero-choice-diffs \
  --require-zero-correctness-diffs \
  --require-zero-text-diffs \
  --require-zero-parse-failures \
  --require-b5-provenance \
  --summary-output scaleout_b5_s4_raw_paired_513_summary.json
```

Expected runtime: 1-2 hours if the source artifacts already exist.

## Run Order

1. Run B0b first. Stop B1/B2 if it fails.
2. Run B3 matched streaming baselines early; they are useful even if B0b blocks
   cross-turn C-PERSIST, provided the compared policies do not use the broken
   cache path.
3. Run B5 re-export/accounting cleanup before importing any S4 breakdowns.
4. Run B1 and B2 only after B0b passes.
5. Run B4 only if the 26B runtime has real sparse/compact ViT execution.

## Deliverables

For each run, provide:
- `*.jsonl` raw paired rows conforming to the schema.
- `summary.json` with gate fields, CIs, model/runtime/hardware metadata.
- The exact clean pre-run `codec-through` code commit used for the run in every
  row as `commit_sha`, plus the exact command line.
- A short note describing any parse failures and at least one representative
  raw response for each failure class.
- A bundle-level validation summary produced by:

```bash
python scripts/validate_scaleout_bundle.py \
  --bundle-dir research/experiments/2026/artifacts/scaleout_m5_20260429 \
  --summary-output research/experiments/2026/artifacts/scaleout_m5_20260429/scaleout_bundle_validation.json
```

This bundle is sufficient for this repo to import scale-out evidence as same-graph
scale-out data rather than as un-audited companion evidence.
