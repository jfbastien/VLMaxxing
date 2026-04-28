# 2026-04-29 Sam Scale-Out Handoff

Status: preregistered handoff plan; no Sam-side results imported here yet.

## Goal

Promote Sam's 26B streaming work from "partner evidence" to first-class
same-graph evidence by requiring the same paired-artifact structure used in
this repo: item ids, raw outputs, parse failures, paired correctness/choice
diffs, timing, memory, and confidence intervals.

## Hardware / Runtime

- Machine: Sam's M5 MacBook Pro with 128 GB unified memory.
- Primary model: the exact 26B Gemma/Qwen-family model used in
  `~/s/codec-through-sam`; record full model id, quantization, runtime commit,
  and Metal/macOS versions.
- Do not inherit this repo's 12 GB MLX memory cap. That cap is a local M3
  mitigation for a Metal panic and would invalidate the scale-out run.

Rows should validate against
`research/schemas/sam_scaleout_artifact_v1.schema.json`.

## B0 — Cache-Correctness Smoke

Hypothesis: the 26B runtime's prompt-cache semantics match the local paired
protocol closely enough to support C-PERSIST replication.

Protocol:
- 3 videos, 3 questions each, deterministic decoding.
- Arms: cold dense baseline and persistent-cache session.
- Require identical prompt text and frame selection between arms.
- Export one JSONL row per paired query.

Gate:
- 0 parse failures.
- 0 choice diffs across the 9 paired queries.
- Prefix-hit metadata is non-null and positive on follow-ups.

Interpretation:
- Pass gates B1/B2. Fail means Sam's runtime needs cache debugging before its
  numbers can be used as first-class evidence.

Expected runtime: 10-30 minutes.

## B1 — 26B C-PERSIST Replication

Hypothesis: adaptive/fixed C-PERSIST is not a Qwen-7B/MLX-local artifact; the
same answer-stability envelope appears at 26B scale.

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

Expected runtime: 1-3 hours depending on 26B decode speed.

## B2 — 26B Many-Turn Streaming Horizon

Hypothesis: the practical value of C-PERSIST at 26B is a measured horizon, not
only a two-follow-up result.

Protocol:
- Same stateless repeated-query design as local 1.55L unless Sam's runtime
  already has a true conversational-history harness.
- Horizons: 10, 20, 50 turns.
- Policies: fixed K=1, adaptive post-Q2/post-previous repaired cache,
  scheduled refresh every 10 turns.
- Dense control must be turn-matched with the exact same prompt sequence.

Gate:
- Report longest horizon with <=3% paired choice and correctness drift.
- Flag a cliff if any 10-turn bucket exceeds 10% drift.

Expected runtime: 4-12 hours.

## B3 — Matched Streaming Baselines

Hypothesis: C-PERSIST is not only beating an overprovisioned dense baseline; it
also beats simpler streaming policies under matched evidence budgets.

Baselines:
- Screenshot polling / fixed-cadence dense.
- Low-FPS dense.
- Recency / last-K frames.

Protocol:
- Use the same videos/questions as B1/B2 where possible.
- Export the same paired JSONL schema.
- Include at least one stale-cache failure case where recency/polling and
  C-PERSIST disagree; raw outputs are required.

Interpretation:
- If low-FPS dense is competitive, add low-FPS + C-PERSIST/adaptive as a
  follow-up before claiming dominance.
- If recency wins on specific items, use them as limitations/failure cases.

Expected runtime: 4-8 hours for a minimal bundle.

## B4 — 26B Sparse-ViT / C-CEILING Validation

Hypothesis: the arithmetic ceiling that predicts local sparse-ViT wall-clock
also predicts scale-out behavior when Sam's runtime actually skips ViT work.

Only run if `codec-through-sam` has a real compact/sparse vision path. Do not
count dense-with-zeros as Track B.

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

## Deliverables

For each run, provide:
- `*.jsonl` raw paired rows conforming to the schema.
- `summary.json` with gate fields, CIs, model/runtime/hardware metadata.
- The exact repo commit and command line.
- A short note describing any parse failures and at least one representative
  raw response for each failure class.

This bundle is sufficient for this repo to import Sam evidence as same-graph
scale-out data rather than as un-audited companion evidence.
