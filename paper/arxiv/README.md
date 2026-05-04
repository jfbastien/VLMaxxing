# arXiv Manuscript Workspace

This subtree is the actual manuscript workspace.

## Layout

- `main.tex`: manuscript entrypoint
- `appendix.tex`: appendix entrypoint
- `sections/`: one file per paper section
- `generated/`: automated tables, figures, and provenance snippets
- `scripts/`: manuscript sync/build/doctor tooling
- `sections/90_references.tex`: manual `thebibliography` used by the
  current lightweight build

Generated JSON snapshots under `generated/data/` are intentionally tracked
because they are the audit surface for plotted and tabulated cells. Generated
figures/tables are reproducible from those snapshots plus the canonical
artifacts named inside them; checkout-specific provenance snippets remain
untracked until the final clean-tag freeze.

## Build Flow

1. `make paper-doctor`
2. `make paper-sync`
3. `make paper-build`
4. `make paper-bundle`

`paper-sync` regenerates:

- the routing Pareto figure and table from canonical
  `research/experiments/2026/artifacts/...` summaries
- a headline anti-recomputation figure and table covering:
  - first-pass Gemma vision-pruning holdout cells from canonical artifacts
  - the local Qwen persistent-KV scaling curve from canonical artifacts
- the local TOMATO session-5 advisory rerun from checked-in artifacts
- repo provenance tables, generated at build/freeze time

## Local Tooling

Current local requirements:

- Python via `uv`
- `matplotlib` and plotting dependencies through the `paper` dependency group
- One TeX engine:
  - preferred lightweight local path: `tectonic`
  - acceptable fuller path: `latexmk` + `xelatex`

Current verified local path:

- `tectonic` builds the manuscript PDF successfully on this machine.
- `latexmk -xelatex main.tex` is the intended explicit TeX Live build path.
- The minimal arXiv upload bundle can be generated locally with
  `make paper-arxiv-upload` or the compatibility alias `make paper-bundle`.
- The richer audit/reproducibility bundle can be generated with
  `make paper-audit-bundle`.
- CI builds the extracted arXiv upload tarball under a pinned TeX Live 2025
  container independently of the local setup.

Install commands on macOS:

- preferred lightweight path:

```bash
brew install tectonic
```

- fuller TeX Live path:

```bash
brew install --cask mactex-no-gui
eval "$(/usr/libexec/path_helper)"
```

Direct script paths:

```bash
./.venv/bin/python paper/arxiv/scripts/build.py
./.venv/bin/python paper/arxiv/scripts/build.py --skip-pdf --arxiv-upload
./.venv/bin/python paper/arxiv/scripts/build.py --skip-pdf --audit-bundle
```

The arXiv upload bundle contains only the TeX sources, generated table `.tex`
files, generated build metadata, and figure PDFs needed for arXiv to compile
the paper. It also contains a short submission-facing `README.md` and a
`00README` file that declares TeX Live 2025, `main.tex` as the top-level source,
and `xelatex` as the intended compiler. The audit bundle is the place for
scripts, generated JSON snapshots, duplicate figure formats, and traceability
materials that are useful for reviewers but unnecessary for arXiv processing.

## Style Choice

This workspace intentionally uses a minimal local LaTeX setup instead of a
conference `.sty` file, because no official NeurIPS/CVPR/ICML style bundle is
checked into the repo yet. Once the target venue is fixed, swap the
`\documentclass`/style layer without changing the section split or automation.

## Source Of Truth

For manuscript work, use [`../AGENTS.md`](../AGENTS.md) and
[`../priority.md`](../priority.md) before editing prose. The LaTeX files are a
distilled view of the science, not the claim authority.

The current manuscript intentionally uses the manual bibliography in
`sections/90_references.tex`. Do not add a parallel `.bib` file unless the build
workflow is also converted to BibTeX/Biber.

## Provenance

`generated/tex/build_meta.tex` and `generated/tables/repo_provenance.tex`
encode the current checkout SHA, so they are generated locally and not tracked.
Regenerate them from a clean release tag before treating a PDF as frozen.
