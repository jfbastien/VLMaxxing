# codec-through

Research repo for codec-conditioned acceleration of video vision-language models.

This repo starts from an imported whitepaper, imported ChatGPT seed artifacts, and an audited predecessor repo. None of those are treated as final truth. The job here is to turn promising ideas into a reproducible research program with explicit experiment contracts, honest measurement, and preserved negative results.

## Current Status

- the imported whitepaper and its correction notes live under `seed/whitepaper/`.
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

If you want the local primary and synthetic evaluation clips:

```bash
uv run python scripts/fetch_corpus.py --tier primary --encode
uv run python scripts/generate_synthetic_corpus.py
```

## Where To Read First

- [AGENTS.md](AGENTS.md): canonical coding-agent guidance
- [PLAN.md](PLAN.md): current research plan and phase order
- [docs/claim-register.md](docs/claim-register.md): frozen imported whitepaper targets and inconsistencies
- [docs/reproduction-status.md](docs/reproduction-status.md): what is and is not reproduced locally from the imported whitepaper
- [docs/README.md](docs/README.md): where durable knowledge belongs
- [docs/clip-policy.md](docs/clip-policy.md): local-only clip and corpus policy
- [docs/benchmark-setup.md](docs/benchmark-setup.md): benchmark-native TOMATO and MVBench asset setup
- [research/README.md](research/README.md): experiment-note and decision-log workflow
- [paper/framing.md](paper/framing.md): current paper story, anti-claims, and future horizons
- [docs/chatgpt-review-packet.md](docs/chatgpt-review-packet.md): focused next-pass external review questions
- [docs/original-repo-audit.md](docs/original-repo-audit.md): what the original repo actually proved
- [docs/external-feedback-validation.md](docs/external-feedback-validation.md): validated takeaways from Claude and ChatGPT reviews
- [docs/methodology/performance.md](docs/methodology/performance.md): measurement contract
- [docs/methodology/preprocessing.md](docs/methodology/preprocessing.md): decode, resize, padding, and sampling contract
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
│   ├── clip-policy.md
│   ├── external-feedback-validation.md
│   ├── knowledge-base-notes.md
│   ├── literature-map.md
│   ├── local-setup.md
│   ├── methodology/
│   │   ├── performance.md
│   │   ├── preprocessing.md
│   │   └── timing-harness.md
│   └── original-repo-audit.md
├── data/
│   └── corpus/
│       └── manifest.toml
├── paper/
│   └── framing.md
├── research/
│   ├── README.md
│   ├── decision-log.md
│   ├── prompt_bank/
│   └── experiments/
│       └── 2026/
│           ├── 2026-04-13-phase-0_5-feasibility.md
│           └── 2026-04-13-phase-0_75-cache-identity.md
├── seed/
│   ├── chatgpt/
│   ├── original_repo/
│   └── whitepaper/
├── scripts/
│   ├── check_model_configs.py
│   ├── fetch_corpus.py
│   └── generate_synthetic_corpus.py
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

## License

- code: [MIT](LICENSE)
- docs, research notes, and paper-draft materials: [CC BY 4.0](LICENSE-docs)
