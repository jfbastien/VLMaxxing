# arXiv Manuscript Scaffold

This subtree is the actual manuscript workspace.

## Layout

- `main.tex`: manuscript entrypoint
- `appendix.tex`: appendix entrypoint
- `sections/`: one file per paper section
- `generated/`: automated tables, figures, and provenance snippets
- `scripts/`: manuscript sync/build/doctor tooling
- `references.bib`: bibliography placeholder

## Build Flow

1. `make paper-doctor`
2. `make paper-sync`
3. `make paper-build`
4. `make paper-bundle`

`paper-sync` regenerates:

- the Lane A Pareto figure and table from canonical
  `research/experiments/2026/artifacts/...` summaries
- a headline anti-recomputation figure and table covering:
  - first-pass Gemma vision-pruning holdout cells from canonical artifacts
  - the local Qwen persistent-KV scaling curve from canonical artifacts
  - an optional TOMATO session-5 advisory upgrade from `../codec-through`
    when that sibling repo is available locally
- repo provenance tables
- a contact-sheet placeholder or imported streaming/UI snapshots from
  `../codec-through-sam` when available

## Local Tooling

Current local requirements:

- Python via `uv`
- `matplotlib` and `Pillow` through the existing `seed` dependency group
- One TeX engine:
  - preferred lightweight local path: `tectonic`
  - acceptable fuller path: `latexmk` + `pdflatex`

Current verified local path:

- `tectonic` builds the draft PDF successfully on this machine
- the paper bundle can be generated locally with `make paper-bundle`
- CI can still use a fuller TeX Live action independently of the local setup

Current caveat:

- `make paper-build` is still flaky with the Homebrew `tectonic` binary on this
  machine because the binary sometimes panics inside its Rust
  `reqwest/system-configuration` path when launched through `make`/shell.
  The direct script path is reliable:

```bash
./.venv/bin/python paper/arxiv/scripts/build.py
```

## Style Choice

This scaffold intentionally uses a minimal local LaTeX draft setup instead of a
conference `.sty` file, because no official NeurIPS/CVPR/ICML style bundle is
checked into the repo yet. Once the target venue is fixed, swap the
`\documentclass`/style layer without changing the section split or automation.

## Source Of Truth

For manuscript work, use [`../AGENTS.md`](../AGENTS.md) and
[`../priority.md`](../priority.md) before editing prose. The LaTeX files are a
distilled view of the science, not the claim authority.
