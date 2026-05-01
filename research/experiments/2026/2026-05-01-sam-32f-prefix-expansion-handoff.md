---
date: 2026-05-01
phase: sam-32f-prefix-expansion
status: handoff ready; Sam-side M5 run only
related:
  - 2026-04-29-phase-M5-comp-sam-prefix-snapshot-32f-composition-findings.md
  - 2026-04-29-phase-M5-5b-sam-prefix-snapshot-fix-findings.md
---

# Sam handoff — expand 32f prefix-snapshot from 9 rows to 21 rows

## Why

The current Gemma 26B-A4B 32f prefix-snapshot result is strong but small:
`sam_m5_5b_swa_prefix_snapshot_32f_summary.json` has 9 rows. The 8f M5-5b
reference has 21 rows. This run expands the 32f cell to the same 7-video ×
3-question shape so the paper can cite the 32f speedup without a small-N caveat
as the first thing reviewers notice.

## What to run

Use the wrapper. It runs the existing M5-5b prefix-snapshot mechanism, validates
the artifact, and runs preflight. It writes to new filenames so the existing
9-row artifact stays preserved.

```bash
git fetch origin
git switch main
git pull --ff-only origin main
git switch -c sam/scaleout-m5-32f-expansion-20260501

HF_TOKEN=... bash scripts/run_sam_m5_5b_32f_expansion.sh
git add \
  research/experiments/2026/artifacts/sam_scaleout_m5_20260429/sam_m5_5b_swa_prefix_snapshot_32f_n21.jsonl \
  research/experiments/2026/artifacts/sam_scaleout_m5_20260429/sam_m5_5b_swa_prefix_snapshot_32f_n21_summary.json
git commit -m "research(sam): expand 32f prefix snapshot evidence" \
  -m "Run the existing M5-5b SWA-aware prefix-snapshot protocol at 32 frames on the full 7-video x 3-question set. This preserves the prior 9-row artifact and adds a 21-row validation target for the Gemma 26B-A4B 32f result."
git push -u origin sam/scaleout-m5-32f-expansion-20260501
```

## Gates

- Expected rows: 21.
- Required: 0 choice diffs, 0 correctness diffs, 0 parse failures.
- Required: matching prompt hashes and frame hashes.
- Required: positive prefix metadata on follow-up rows.
- Not required: byte-identical text. M5-5b permits paraphrase-level text drift
  as long as choice/correctness stay matched.

## How to report it

Report exactly these fields:

- `n_rows`
- `choice_diffs`
- `correctness_diffs`
- `parse_failures`
- `text_diffs` / byte-identical count
- median per-follow-up speedup
- range of per-follow-up speedups
- peak memory

Do not compare the 32f speedup to the Qwen 7B 47×–150× band. This is a
different architecture and cache mechanism.
