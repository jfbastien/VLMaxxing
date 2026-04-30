# Phase 1.63I — Qwen 16f keep-rate bracket findings

## Preregistered question

After the Qwen 16f keep-rate sweep found a fidelity-safe but low-gain point at
\(kr=0.85\), is there a nearby keep rate that preserves fidelity while clearing
the sparse-vision reduction gate?

## Protocol

- Model/runtime: Qwen2.5-VL-7B-Instruct-4bit on the local MLX stack.
- Corpus: 16-frame VideoMME sparse-vision bracket.
- Arms: fine keep-rate bracket around the 0.75--0.85 region.

## Result

No bracketed point earned a full promotion.

- \(kr=0.78\): higher gain, but fidelity still fails.
- \(kr=0.80\) and \(kr=0.82\): accuracy delta improves to -0.0167 with
  85% choice agreement, but format gate fails.
- \(kr=0.85\) from the earlier sweep remains the format-clean low-gain
  boundary: fidelity/format/ceiling-safe, but only 13.6% vision-time reduction
  and 1.032x end-to-end speedup.

## Interpretation

Qwen does have a measurable configuration envelope, but the current bracket did
not turn it into a strong sparse-execution headline. The result supports the
paper's architecture-conditional framing: Gemma supplies the clean timed-skip
cell, while Qwen shows the fidelity/gain tradeoff.

## Artifacts

- `research/experiments/2026/artifacts/phase1_63I_16f_kr_fine_bracket/fine_bracket_summary.json`
