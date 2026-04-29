# 2026-04-29 Sam Scale-Out Operator Prompt

Use this as the short instruction for Sam's coding agent on the M5 128 GB
machine. `codec-through` is the canonical execution, artifact, validation, and
commit repo for this bundle. `codec-through-sam` may be used only as reference
or prototype code if needed.

## Bootstrap

From Sam's machine:

```bash
git clone git@github.com:jfbastien/codec-through.git
cd codec-through
git checkout <branch-or-commit-containing-this-handoff>
claude
```

Then give Claude the one-shot request below. If `codec-through` is already
cloned, update that clone instead of creating a second one. Run from the
`codec-through` repo root.

## One-Shot Request

Please run the Sam scale-out bundle described in:

`research/experiments/2026/2026-04-29-sam-scaleout-handoff.md`

Use `codec-through` as the artifact repo. If code from `codec-through-sam` is
needed, port or call it from this repo and record that provenance in the
findings note; do not make `codec-through-sam` the returned artifact home.

Return one committed artifact bundle that validates with:

```bash
python scripts/validate_sam_scaleout_bundle.py \
  --bundle-dir research/experiments/2026/artifacts/<sam-scaleout-run-id> \
  --summary-output research/experiments/2026/artifacts/<sam-scaleout-run-id>/sam_scaleout_bundle_validation.json
```

Commit the raw JSONLs, summaries, validation output, command logs, and a short
findings note in `codec-through`. Send back the `codec-through` commit SHA,
artifact directory path, and the bundle validation summary.

## Required File Names

Put these files in one artifact directory:

`research/experiments/2026/artifacts/<sam-scaleout-run-id>/`

- `sam_b0b_cache_correctness.jsonl`
- `sam_b3_streaming_baselines.jsonl`
- `sam_b5_s4_accuracy_1937.jsonl`
- `sam_b5_s4_raw_paired_513.jsonl`

If B0b passes, also run and include:

- `sam_b1_cpersist_replication.jsonl`
- `sam_b2_many_turn_horizon.jsonl`

If the runtime has real compact/sparse ViT execution, also run and include:

- `sam_b4_sparse_vit_ceiling.jsonl`

Dense-with-zeroed-tokens is not Track B and must not be exported as B4.

## Execution Order

1. Run B0b first. Stop B1/B2 if B0b fails.
2. Run B3 matched streaming baselines early; it can run even if B0b blocks
   cross-turn cache reuse as long as the compared policies do not rely on the
   broken cache path.
3. Run B5 S4 re-export/accounting cleanup before importing any S4 breakdowns.
4. Run B1/B2 only after B0b passes.
5. Run B4 only if real sparse/compact ViT execution exists.

## Non-Negotiable Artifact Rules

- Validate every row against
  `research/schemas/sam_scaleout_artifact_v1.schema.json`.
- Do not port the local 12 GB MLX memory cap to the 128 GB M5 machine.
- Record exact model id, model hash, quantization, runtime commit, macOS,
  Metal, MLX/runtime version, `codec-through` `commit_sha`, command line, and memory
  definition.
- Include raw paired prompts/responses, parse failures split by arm, prompt
  hashes, input-id hashes, frame ids/hashes, cache topology, prefix coverage,
  stage timings, and peak memory.
- B3 must use the same recordings, events/timestamps, observation windows,
  questions, answer keys, scoring, and schema across screenshot polling,
  low-FPS dense, recency/last-K, and Sam policy.
- B3 must include at least 20 matched event/question pair keys across at least
  2 recordings/scenes. With the four required arms, this is at least 80 rows.
- B5 must keep the claim bounded unless raw paired responses exist: 1,937
  zero-accuracy-delta rows and 513 byte-identical raw-paired rows are separate
  artifacts.

## What We Need Back

- The `codec-through` commit SHA.
- The artifact directory path under `research/experiments/2026/artifacts/`.
- `sam_scaleout_bundle_validation.json`.
- One short note with: which phases ran, which gates passed/failed, any parse
  failures, and any runtime/cache implementation deviations from the handoff.
