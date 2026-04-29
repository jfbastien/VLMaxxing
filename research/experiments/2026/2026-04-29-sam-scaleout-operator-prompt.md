# 2026-04-29 Sam Scale-Out Operator Prompt

Use this as the short instruction for Sam's coding agent on the M5 128 GB
machine. `codec-through` is the canonical execution, artifact, validation, and
commit repo for this bundle.

## Bootstrap

From Sam's machine:

```bash
git clone git@github.com:jfbastien/codec-through.git
cd codec-through
git switch sam-scaleout-handoff-20260429
git pull --ff-only
git switch -c sam/scaleout-m5-20260429
claude
```

If `codec-through` is already cloned, use that clone instead of creating a
second one:

```bash
cd codec-through
git switch sam-scaleout-handoff-20260429
git pull --ff-only
git switch -c sam/scaleout-m5-20260429
claude
```

The base branch `sam-scaleout-handoff-20260429` must already exist on GitHub
and contain this handoff, schema, and validators. Run from the `codec-through`
repo root.

## One-Shot Request

Read `AGENTS.md`, then run the Sam scale-out bundle described in:

`research/experiments/2026/2026-04-29-sam-scaleout-handoff.md`

Use the current branch as the result branch. Implement or adapt any missing
M5/26B runners inside `codec-through`, using the handoff's schema and gates as
the acceptance contract.

Run autonomously in a loop:

- Execute phases in the gate order below.
- Monitor long-running jobs and record useful progress in logs.
- Validate each phase artifact with the row validator after it lands.
- Write a short findings note for each completed phase.
- Commit after each completed phase, including scientific failures,
  infrastructure failures, and boundary results.
- Push the result branch periodically and after the final validation.

The final bundle must validate with:

```bash
python scripts/validate_sam_scaleout_bundle.py \
  --bundle-dir research/experiments/2026/artifacts/sam_scaleout_m5_20260429 \
  --summary-output research/experiments/2026/artifacts/sam_scaleout_m5_20260429/sam_scaleout_bundle_validation.json
```

## Required File Names

Put these files in one artifact directory:

`research/experiments/2026/artifacts/sam_scaleout_m5_20260429/`

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

If B0b fails, commit the failed B0b artifacts and validation summary, mark
B1/B2 as blocked in the findings note, and continue with B3/B5 and eligible
B4. Do not silently drop failed artifacts.

## Non-Negotiable Artifact Rules

- Validate every row against
  `research/schemas/sam_scaleout_artifact_v1.schema.json`.
- Do not port the local 12 GB MLX memory cap to the 128 GB M5 machine.
- Record exact model id, model hash, quantization, runtime commit, macOS,
  Metal, MLX/runtime version, `codec-through` `commit_sha`, command line, and
  memory definition.
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

## Final Response

At the end, push the result branch and respond with:

- Pushed branch name.
- Final commit SHA.
- Compact phase table: phase, status, pass/fail gates, row counts, runtime.
- Whether `sam_scaleout_bundle_validation.json` passed.
- Any scientific blockers, infrastructure failures, or runtime deviations from
  the handoff.

Do not send raw artifacts separately; they live in the pushed branch under
`research/experiments/2026/artifacts/sam_scaleout_m5_20260429/`.
