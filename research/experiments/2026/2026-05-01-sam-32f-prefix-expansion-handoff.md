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

Two commands. First wrapper runs the M5-5b prefix-snapshot mechanism, validates
the artifact, and runs preflight. Second wrapper stages the two generated
artifacts, prompts for confirmation, then commits and pushes to the handoff
branch. New filenames preserve the existing 9-row artifact.

```bash
# 1. Run the experiment (writes *_32f_n21.jsonl + summary, validates, runs preflight)
HF_TOKEN=... bash scripts/run_sam_m5_5b_32f_expansion.sh

# 2. Submit results (creates branch, stages exact files, prompts y/N, commits, pushes)
bash scripts/submit_sam_m5_5b_32f_expansion.sh
```

`HF_TOKEN` is the same gated `google/gemma-4-26B-A4B-it` weights used in the
prior 9-row M5-5b run; no new model. The check is unconditional even if the
snapshot is already cached locally. Pass `--yes` to the submit script to skip
the confirmation prompt. The branch name defaults to
`sam/scaleout-m5-32f-expansion-20260501`; override via `SAM_M5_5B_BRANCH=...`.

If you prefer to do the git ceremony manually after step 1, the equivalent flow
is `git switch -c <branch>; git add <jsonl> <summary>; git commit -m '...';
git push -u origin HEAD`.

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
