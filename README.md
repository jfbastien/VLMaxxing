# codec-through

Research repo for codec-conditioned acceleration of video vision-language models.

This repo starts from a local whitepaper, imported ChatGPT seed artifacts, and an audited predecessor repo. None of those are treated as final truth. The job here is to turn promising ideas into a reproducible research program with explicit experiment contracts, honest measurement, and preserved negative results.

## Current Status

- `whitepaper.pdf` and `whitepaper.md` are checked in.
- Imported ChatGPT material lives under `seed/chatgpt/`.
- Selected reference material from the original `codec-through-sam` repo lives under `seed/original_repo/`.
- Clean rewritten utilities for frame probing, block classification, and strict answer parsing live under `src/codec_through/`.
- The current research plan, experiment ledger, and paper framing live in `PLAN.md`, `research/`, and `paper/`.

## Research Principles

- hypothesis first
- separate semantic validation from real sparse execution
- change one variable at a time
- measure both quality and systems impact
- keep failed experiments and weakened hypotheses

## Quick Start

```bash
uv sync --group dev
uv run ruff check .
uv run ruff format --check .
uv run mypy src tests
uv run pytest
```

If you want the imported reference and seed stacks available too:

```bash
uv sync --group dev --group seed --group research
```

If you want the local MLX/MLX-VLM stack available too:

```bash
uv sync --group dev --group research --group vlm
```

## Where To Read First

- [AGENTS.md](AGENTS.md): canonical coding-agent guidance
- [PLAN.md](PLAN.md): current research plan and phase order
- [docs/README.md](docs/README.md): where durable knowledge belongs
- [research/README.md](research/README.md): experiment-note and decision-log workflow
- [paper/framing.md](paper/framing.md): current paper story, anti-claims, and future horizons
- [docs/original-repo-audit.md](docs/original-repo-audit.md): what the original repo actually proved
- [docs/external-feedback-validation.md](docs/external-feedback-validation.md): validated takeaways from Claude and ChatGPT reviews
- [docs/methodology/performance.md](docs/methodology/performance.md): measurement contract
- [docs/local-setup.md](docs/local-setup.md): repo-centric setup and model guidance

## Repository Layout

```text
.
├── AGENTS.md
├── CLAUDE.md
├── .github/workflows/ci.yml
├── PLAN.md
├── README.md
├── docs/
│   ├── README.md
│   ├── external-feedback-validation.md
│   ├── knowledge-base-notes.md
│   ├── literature-map.md
│   ├── local-setup.md
│   ├── methodology/
│   │   ├── performance.md
│   │   └── timing-harness.md
│   └── original-repo-audit.md
├── paper/
│   └── framing.md
├── research/
│   ├── README.md
│   ├── decision-log.md
│   └── experiments/
│       └── 2026/
│           └── 2026-04-13-phase-0_5-feasibility.md
├── seed/
│   ├── chatgpt/
│   └── original_repo/
├── src/
│   └── codec_through/
└── tests/
```

## What This Repo Is For

The near-term job is to answer a narrow set of questions with good evidence:

1. How much temporal reuse is actually safe for video VLMs?
2. How much of the remaining waste is in decode, the vision encoder, attention, and prefill?
3. Which cheap routing signals are genuinely useful: pixel diff, frame metadata, motion vectors, Q-table flatness, or something else?
4. Which content classes break the idea first: egomotion, OCR, color-sensitive tasks, small objects, or screen content?

## Seed Material

The material under `seed/` is preserved because it is useful source material.

It is intentionally not the repo's source of truth.

The source of truth is:

- measured local results
- checked-in clean code
- verified primary references
- explicit notes about uncertainty and failed ideas
