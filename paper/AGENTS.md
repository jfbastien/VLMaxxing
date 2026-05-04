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

Authority is split by question:

- submission gates and priority: [priority.md](priority.md)
- paper-facing claim status and exact numbers: [claim-matrix.md](claim-matrix.md)
- reviewer-facing inventory and runtime-cost summary:
  [publishability-status.md](publishability-status.md)
- accepted wording and contribution boundary: [framing.md](framing.md)
- manuscript text: [`arxiv/sections/`](arxiv/sections/)

If files disagree inside one of those scopes, prefer the scoped authority above
and update the stale file in the same change.

## Current Paper Position

As of 2026-04-22, the manuscript should be centered on a single
anti-recomputation story with three first-class contributions plus one
mechanism-validation backbone:

1. **C-CEILING** is the arithmetic frame:
   component wins survive to end-to-end wall-clock only in proportion to the
   dense share they actually own.
2. **C-PERSIST** is the big-number after-ingest regime:
   same-video follow-up queries can collapse to sub-second latency with large,
   architecture-specific speedups.
3. **C-VISION** is the first-pass headline:
   training-free mid-layer vision-tower pruning on Gemma produces measured
   end-to-end speedups on fresh videos, again bounded by share × reduction.
4. **Qwen routing** is mechanism and boundary evidence, not the headline:
   it explains where temporal reuse preserves answers, why placement of fresh
   computation matters, how local novelty-ranked diagnostics should be treated
   until raw artifacts are checked in, and which intuitive fixes do not survive
   matched conditions.

The streaming lane remains important, but it is not just decoration. Use it for:

- bounded deployment-scale evidence from checked validated bundles, with
  positive, negative, and baseline-pressure rows kept visibly separate
- streaming / deployment motivation
- bounded case studies when the evidence is qualitative or lacks a matched
  wall-clock baseline

Do not let the paper drift back to a Qwen-only routing note, and do not let it
flatten streaming work into generic demo material.

## Evidence Hygiene

- `paper/arxiv/sections/*.tex` are draft prose, not the source of truth.
- Every paper-facing number must trace to a dated note plus checked-in
  artifacts, or be explicitly labeled as pending artifact harmonization.
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
