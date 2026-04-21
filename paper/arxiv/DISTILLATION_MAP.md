# Distillation Map

This file answers: "Which existing repo documents can be imported into the
paper, and which need serious rewriting?"

Short answer: almost everything in this repo is **source material**, not
drop-in manuscript prose.

## Section Mapping

| Manuscript section | Best current source material | Distillation level | Notes |
| --- | --- | --- | --- |
| Abstract | `paper/framing.md`, `paper/publishability-status.md`, `paper/claim-matrix.md` | High | Current docs are ops- and claim-gate-heavy. Convert into 4-6 crisp sentences. |
| Introduction | `paper/framing.md`, `docs/literature-map-2026-04-16.md`, `docs/related-work-table.md` | High | Replace repo-internal language like "lane A" and "claim 15" with normal paper framing. |
| Related work | `docs/related-work-table.md`, `docs/literature-map-2026-04-16.md` | Medium | Good source inventory, but every final claim still needs a primary-paper check before citation. |
| Method | `src/codec_through/temporal.py`, `src/codec_through/novelty_pruning.py`, `src/codec_through/pruned_vision_tower.py`, `docs/methodology/*.md` | High | Current material is implementation- and methodology-first; rewrite around reader comprehension. |
| Experimental setup | `docs/benchmark-taxonomy.md`, `docs/benchmark-setup.md`, `research/benchmark_manifests/`, `scripts/run_track_b.py` | Medium | Good evidence sources, but needs concise benchmark/hardware/protocol tables. |
| Qwen routing results | Canonical summary JSONs under `research/experiments/2026/artifacts/`, plus `paper/claim-matrix.md` | Low to Medium | The numbers are manuscript-ready; the prose is not. |
| Cross-architecture / Gemma / persistent KV | `paper/publishability-status.md`, `paper/claim-matrix.md`, relevant experiment notes | High | There is good evidence, but it is embedded in repo-control language and needs normal-paper restructuring. |
| Real applications / streaming case studies | `../codec-through-sam/paper/publishability-status.md`, `../codec-through-sam/research/decision-log.md`, `../codec-through-sam/live_demo_v2_writeup.md`, `../codec-through-sam/diagrams/live_demo_v2/` | High | Use Sam's repo for controlled case-study evidence and imagery, not as the paper's narrative source-of-truth. |
| Limitations / reproducibility | `paper/framing.md`, `docs/reproduction-status.md`, `docs/methodology/performance.md`, `docs/methodology/preprocessing.md` | Medium | Good source material already exists; distill into reviewer-facing prose. |
| Appendix traceability | `paper/claim-matrix.md`, `docs/reproduction-status.md`, generated provenance | Low | Can stay more explicit and source-traceable than the main text. |

## What `codec-through-sam` Has That `codec-through-2` Still Needs

- Streaming/UI case-study figures and recordings
- Piecewise cache-shift and real-application qualitative examples
- Post-fix live-demo writeups and decision-log context for supplementary
  streaming evidence

## What `codec-through-2` Has That Should Be The Paper Backbone

- Better claim discipline
- Better provenance and methodology
- Canonical, machine-readable summary JSONs
- Cleaner separation between reproduced result, imported result, and hypothesis

## Practical Rule

Use `codec-through-2` as the **paper spine** and `codec-through-sam` as a
**source repo for specific figures, case studies, and supplementary evidence**.
Do not treat `codec-through-sam/whitepaper.md` as the paper's main
source-of-truth.
