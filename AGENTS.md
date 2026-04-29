# Agent Guidance

This file is the canonical coding-agent guide for this repo.

If another tool or agent-specific file exists, it should point here instead of
duplicating instructions.

## Read Order

Read these before changing anything substantial:

1. [README.md](README.md)
2. [PLAN.md](PLAN.md)
3. [docs/README.md](docs/README.md)
4. [docs/claim-register.md](docs/claim-register.md)
5. [docs/reproduction-status.md](docs/reproduction-status.md)
6. [paper/README.md](paper/README.md)
7. [paper/claim-matrix.md](paper/claim-matrix.md)
8. [paper/publishability-status.md](paper/publishability-status.md)
9. [research/README.md](research/README.md)
10. [research/experiments/registry.md](research/experiments/registry.md)

Use that order for repo-wide orientation.

Within `docs/`, use [docs/README.md](docs/README.md) as the scoped router for
the docs subtree only.

## Task Routing

Do not read the whole repo by default. Pull only the context needed for the
current task.

- For experiment design and evaluation rules:
  [docs/methodology/performance.md](docs/methodology/performance.md) and
  [docs/methodology/preprocessing.md](docs/methodology/preprocessing.md) and
  [docs/methodology/timing-harness.md](docs/methodology/timing-harness.md)
- For current claim status, reopen conditions, and killed ideas:
  [research/decision-log.md](research/decision-log.md)
- For the canonical pre-release source targets and known internal
  inconsistencies:
  [docs/claim-register.md](docs/claim-register.md)
- For exact source-reproduction status and what is still imported-only:
  [docs/reproduction-status.md](docs/reproduction-status.md)
- For active roadmap and phase order:
  [PLAN.md](PLAN.md)
- For corpus and local asset policy:
  [docs/clip-policy.md](docs/clip-policy.md),
  [docs/local-setup.md](docs/local-setup.md), and
  [data/corpus/manifest.toml](data/corpus/manifest.toml)
- For data acquisition or local synthetic generation:
  [scripts/fetch_corpus.py](scripts/fetch_corpus.py) and
  [scripts/generate_synthetic_corpus.py](scripts/generate_synthetic_corpus.py)
- For versioned prompts and answer keys:
  [research/prompt_bank](research/prompt_bank/)
- For paper positioning, submission triage, and manuscript mechanics:
  [paper/AGENTS.md](paper/AGENTS.md),
  [paper/priority.md](paper/priority.md),
  [paper/claim-matrix.md](paper/claim-matrix.md),
  [paper/publishability-status.md](paper/publishability-status.md),
  [paper/framing.md](paper/framing.md), and
  [paper/arxiv/README.md](paper/arxiv/README.md)

## Current Research Position

Validated enough to guide work:

- training-free temporal feature reuse is worth studying
- same-position reuse is the default baseline
- pixel diff is the current semantic-validation baseline
- bounded measured sparse-vision execution now exists, but broad sparse-backend
  coverage and sparse LM prefill remain open systems work
- imported target claims are tracked in the claim register; raw historical
  source imports are intentionally absent from the release tree because git
  history preserves them

Deprioritized until new evidence appears:

- embedding relocation as the main temporal path
- DCT-bypass as an early systems win
- continuous H.264 spatial scoring as a saliency oracle

Still hypotheses:

- changed-window sparse execution
- stabilization plus same-position reuse for egomotion
- changed-query attention after sparse execution is working
- screen-content specialization
- machine-oriented sidecars and AI-native codecs

## Working Rules

- Label every important claim as `reproduced here`, `imported result`, or `hypothesis`.
- Keep Track A and Track B separate.
  - Track A: semantic substitution and answer stability.
  - Track B: real work skipped in decode, vision, attention, or prefill.
- Hard-fail on mismatched shapes, silent truncation, or ambiguous parsing unless the repo explicitly wants softer behavior.
- Use primary sources for literature or standards claims.
- Do not let historical imports become the source of truth by repetition.

## Knowledge Maintenance

The repo should accumulate evidence, not drift.

After every decision-worthy experiment:

1. Add or update a dated note under `research/experiments/<year>/`.
2. Put the preregistration at the top of that note before the run.
3. Append execution, result, interpretation, and links after the run.
4. Update [research/decision-log.md](research/decision-log.md) if the result adopts, weakens, kills, or revives an idea.
5. Update [paper/framing.md](paper/framing.md) if the contribution boundary, anti-claims, or future-work story changed.

Durable homes:

- `PLAN.md`: active roadmap and phase order
- `docs/`: stable methodology, provenance, literature, and setup guidance
- `research/`: experiment notes and decision ledger
- `paper/`: manuscript source, claim framing, and paper-story notes

## Model And Runtime Notes

- First local target: Qwen2.5-VL-3B on MLX-VLM.
- Second local model: Gemma 4 E4B as the early cross-family check.
- Third-pass confirmation: Qwen2.5-VL-7B on smaller slices.
- Interpret cross-family results per family. Do not collapse Qwen and Gemma into one acceptance metric.
- Never assume a `28 px` token block. Derive geometry from model config.

## Review Standard

Before presenting work as complete:

- run the relevant checks
- say what was verified
- say what remains imported or uncertain
- record any weakened hypotheses, not just wins
