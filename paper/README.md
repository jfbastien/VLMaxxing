# Paper Workspace

This directory now has two distinct roles:

- Manuscript source and build tooling live under [`paper/arxiv/`](arxiv/).
- Research-facing paper planning and claim-boundary docs stay at the top level:
  - [`paper/AGENTS.md`](AGENTS.md)
  - [`paper/priority.md`](priority.md)
  - [`paper/framing.md`](framing.md)
  - [`paper/claim-matrix.md`](claim-matrix.md)
  - [`paper/publishability-status.md`](publishability-status.md)
  - [`paper/terminology.md`](terminology.md)
  - [`paper/narrative-rules.md`](narrative-rules.md)

The manuscript is **not** meant to directly copy those markdown files into a
paper. They are source material for humans and agents. The LaTeX source should
distill them into reader-facing prose for AI/VLM researchers.

For paper work, use [`paper/AGENTS.md`](AGENTS.md) as the paper-local router.
Its source-of-truth order is stricter than the repo root because the manuscript
has already outgrown the older single-note framing.

Use `terminology.md` and `narrative-rules.md` when editing prose. They capture
the current wording contract: front-load the exciting after-ingest numbers, keep
denominators visible, distinguish local mechanism evidence from the scale-out
streaming lane, and avoid turning internal agent labels into paper jargon.

Use these commands from the repo root:

```bash
make paper-doctor
make paper-sync
make paper-build
make paper-bundle
```

`paper-sync` is the safe first step. It regenerates automated manuscript inputs
without needing a TeX installation.
