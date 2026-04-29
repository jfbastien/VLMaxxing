# Methodology: Machine-readable Experiment Integrity

Date: 2026-04-17
Parent: [pareto-reporting.md](pareto-reporting.md)

Per ChatGPT 2026-04-17 review: as the paper approaches submission,
we need the experiment artifacts to be machine-checkable, not just
human-readable. This document specifies the two conventions that
make per-claim reproduction auditable without running the full
pipeline.

## 1. Frontmatter state field on every phase note

Every file under `research/experiments/2026/*.md` MUST carry an
explicit `state` field near the top (in the existing header block).
Valid values:

| state | meaning |
|---|---|
| `in-flight` | GPU / CPU work is running right now. Results partial. |
| `complete` | All cells landed; claim decision recorded. |
| `blocked` | Prereg written; pre-req not satisfied. Includes blocker. |
| `superseded` | Earlier phase outcome replaced by a later phase; link to successor. |
| `retired` | Hypothesis falsified or scope no longer applicable; link to `research/falsified-hypotheses.md` if applicable. |

Example header (new phase):

```markdown
# Phase 1.37 — Planner 2.1 prereg

Date: 2026-04-17
State: blocked (pre-req: child-veto code landed in planner)
Parent: `paper/claim-matrix.md` claim #3
```

Example header (in-flight):

```markdown
# Phase 1.34 — Novelty-ranked dense baseline

Date: 2026-04-17
State: in-flight (TOMATO complete; MVBench N=6 running)
Parent: `paper/claim-matrix.md` claim #9
```

Retrofitting: existing notes have de-facto state embedded in the
"Status" section at the bottom; a retrofit pass can add the
frontmatter without losing information. The frontmatter is the
machine-readable surface; the Status section remains the
human-readable narrative.

## 2. Artifact integrity pointers

Every phase note that cites a quantitative result MUST include, in
a dedicated "Artifacts" section near the bottom:

- The path (relative to repo root) of every JSON summary cited.
- The git commit of the commit that introduced each summary (short
  form OK).
- The N (items) used for each summary, not just "our run."

Example:

```markdown
## Artifacts

- `research/experiments/2026/artifacts/phase1_20_tomato_motion_holdout_v2_dense/frame_6_summary.json` (N=30, commit short-SHA)
- `research/experiments/2026/artifacts/phase1_20_tomato_motion_holdout_v2_dense/frame_8_summary.json` (N=30, commit short-SHA)
- `research/experiments/2026/artifacts/phase1_21_mvbench_motion_holdout_v2_dense/frame_8_summary.json` (N=30, commit short-SHA)
```

This makes "did this number come from the commit I think it did?"
mechanically checkable, and it makes ambiguous claim-to-artifact
mappings visible during review.

Artifact files themselves (the JSONs) do NOT need extra integrity
metadata; their commit provenance comes from git.

## 3. Paper-facing numbers trace to frontmatter + artifact

Rule for `paper/claim-matrix.md` and `paper/framing.md`:

> Every quantitative claim ("0.333 @ 3.55 fresh frames") traces
> through `(phase-id, result-name)` into exactly one phase note;
> that phase note's "Artifacts" section lists the file + commit.

The claim-matrix row's "Current status" field should link to the
phase note, and the phase note's frontmatter `state` says whether
the number is frozen (complete) or still moving (in-flight).

## Status

Rule is live as of 2026-04-17. Phase notes authored from this date
forward MUST use the frontmatter `state` field and the Artifacts
section. Retrofitting older notes is a separate cleanup task;
priority is paper-critical claims (#1, #3, #4, #6, #9) first.
