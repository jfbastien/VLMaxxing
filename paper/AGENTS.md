# Paper Workspace Guidance

This file narrows the root [AGENTS.md](../AGENTS.md) for manuscript work.

The paper now has a real drafting workspace under [`paper/arxiv/`](arxiv/).
That means manuscript edits need a tighter source-of-truth order than the rest
of the repo.

## Read Order For Paper Work

Read these before changing manuscript prose, paper positioning, or paper-facing
automation:

1. [README.md](README.md)
2. [priority.md](priority.md)
3. [claim-matrix.md](claim-matrix.md)
4. [publishability-status.md](publishability-status.md)
5. [framing.md](framing.md)
6. [arxiv/README.md](arxiv/README.md)
7. [arxiv/DISTILLATION_MAP.md](arxiv/DISTILLATION_MAP.md)

If those files disagree, prefer them in that order.

## Current Paper Position

As of 2026-04-21, the manuscript should be centered on a single
anti-recomputation story with three linked contributions:

1. **C-VISION** is the current first-pass headline:
   training-free mid-layer vision-tower pruning on Gemma produces measured
   end-to-end speedups, with magnitude governed by a `share × reduction`
   ceiling.
2. **C-PERSIST** is the current big-number deployment result:
   after-ingest follow-up queries on the same video can collapse to
   sub-second latency with large speedups.
3. **Qwen routing** is mechanism and boundary evidence:
   it explains where temporal reuse preserves answers and why placement of
   fresh computation matters more than novelty magnitude alone.

The Sam lane remains important. Use it for:

- real-application case studies
- streaming / deployment motivation
- supplementary or companion evidence

Do not let the paper drift back to a Qwen-only routing note unless the paper
docs explicitly re-promote that position.

## Evidence Hygiene

- `paper/arxiv/sections/*.tex` are draft prose, not the source of truth.
- Every paper-facing number must trace to a dated note plus checked-in
  artifacts, or be explicitly labeled as imported companion evidence.
- If a result is advisory, dev-only, dirty-tree, or imported, say so in the
  manuscript.
- Do not silently promote supplementary results into automated headline
  figures or tables.

## When Positioning Changes

Update these together:

1. [priority.md](priority.md)
2. [claim-matrix.md](claim-matrix.md)
3. [publishability-status.md](publishability-status.md)
4. [framing.md](framing.md)
5. the affected LaTeX sections under [`paper/arxiv/sections/`](arxiv/sections/)

The repo already has enough stale paper-routing text. Do not add more.
