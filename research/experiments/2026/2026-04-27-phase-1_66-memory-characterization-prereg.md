---
date: 2026-04-27
phase: 1.66
status: preregistered; analysis-only
---

# Phase 1.66 — Memory Characterization (PREREG)

## Question

What is the measured local memory envelope for the paper's C-VISION,
C-PERSIST, and Track B operating points on the 16 GB unified-memory laptop?

Several recent experiments passed their scientific fidelity/speed gates while
exceeding earlier strict RSS prereg gates. This phase turns those observations
into an explicit memory table rather than leaving them as surprising footnotes.

## Protocol

- No MLX generation.
- Read landed artifact summaries and JSONL rows from the 1.30, 1.55, and 1.63
  lanes.
- For every file with memory information, compute `peak_observed_gb` as the
  largest available signal among:
  - `peak_rss_gb`
  - `final_rss_mb / 1024`
  - max or mean row-level `peak_memory_gb`
- Emit:
  - `memory_characterization_summary.json`
  - `memory_cells.csv`

## Gates

- H1-report: at least 8 memory-bearing cells are discovered.
- H2-high-watermark: report the top 10 peak-memory cells.
- H3-budget-flags: report counts above 9 GB and 10 GB.
- H4-lane-coverage: memory-bearing cells include all three intended families:
  C-VISION/1.30, C-PERSIST/1.55, and Track-B/1.63.

## Interpretation

This phase is reviewer defense, not a new model-quality result. If high-water
cells exceed earlier strict RSS gates but remain inside the operator's actual
successful runtime envelope, the paper should present a measured memory envelope
and avoid implying those scientific passes were hidden failures.

If Track B or adaptive cells exceed the 10 GB operator policy, the paper should
state the local-memory boundary explicitly and keep large-memory controls (for
example 1.58 bf16) off-laptop.
