# Agent Guidance

This file is the canonical coding-agent guide for this repo.

If another tool or agent-specific file exists, it should point here instead of
duplicating instructions.

## Read Order

Read these before changing anything substantial:

1. [README.md](README.md)
2. [PLAN.md](PLAN.md)
3. [docs/README.md](docs/README.md)
4. [docs/methodology/performance.md](docs/methodology/performance.md)
5. [research/README.md](research/README.md)
6. [research/decision-log.md](research/decision-log.md)
7. [paper/framing.md](paper/framing.md)

## Current Research Position

Validated enough to guide work:

- training-free temporal feature reuse is worth studying
- same-position reuse is the default baseline
- pixel diff is the current semantic-validation baseline
- sparse execution is not yet proven and must be measured separately

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
- Do not let seed material become the source of truth by repetition.

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
- `docs/`: stable methodology, provenance, literature, external-review validation
- `research/`: experiment notes and decision ledger
- `paper/`: claim framing and paper-story notes
- `seed/`: imported provenance only

## Model And Runtime Notes

- First local target: Qwen2.5-VL-3B on MLX-VLM.
- Second-pass confirmation: Qwen2.5-VL-7B on smaller slices.
- Gemma checks are useful, but only after geometry-sensitive helpers use model config rather than Qwen-specific constants.
- Never assume a `28 px` token block. Derive geometry from model config.

## Review Standard

Before presenting work as complete:

- run the relevant checks
- say what was verified
- say what remains imported or uncertain
- record any weakened hypotheses, not just wins
