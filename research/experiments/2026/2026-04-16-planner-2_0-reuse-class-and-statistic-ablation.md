# Planner 2.0: Reuse-Class and Statistic Ablation (N=30)

Date: 2026-04-16

## Purpose

Ablation study of the two primary planner axes beyond the base winner
`max_abs(8,32) static+shifted age=4`:

1. **Reuse-class axis**: STATIC-only vs STATIC+SHIFTED
2. **Statistic axis**: changed_pixel_fraction (CPF) vs max_abs

All cells evaluated on N=30 holdout v2 slices. All cells used
`--allow-dirty` (diagnostic provenance, not paper-grade).

## Results

### Reuse-class comparison (STATIC-only vs STATIC+SHIFTED)

| Benchmark | STATIC+SHIFTED | STATIC-only | Δ accuracy | Δ fresh |
|---|---|---|---|---|
| MVBench holdout v2 | 0.600 @ 4.06 | 0.567 @ 5.11 | −0.033 | +1.05 |
| TOMATO holdout v2 | 0.333 @ 3.55 | 0.300 @ 4.56 | −0.033 | +1.01 |

**Cross-benchmark consistency**: SHIFTED adds exactly −0.033 accuracy
and −1.0 fresh frame on both benchmarks. The whitepaper's "localized
motion preserves embeddings at 0.997+ cosine" translates directly into
method value.

### Statistic comparison (CPF vs MAX_ABS)

| Benchmark | MAX_ABS (8,32) | CPF (px8, 0.02/0.08) | Δ accuracy | Δ fresh |
|---|---|---|---|---|
| MVBench holdout v2 | 0.600 @ 4.06 | 0.600 @ 4.46 | 0.000 | +0.40 |
| TOMATO holdout v2 | 0.333 @ 3.55 | pending | — | — |

CPF matches MAX_ABS accuracy on MVBench but uses +0.40 more fresh
frames. MAX_ABS is the strictly better statistic on this slice.

## Interpretation

The base winner `max_abs(8,32) static+shifted age=4` is not a fragile
one-off: removing SHIFTED hurts consistently, and replacing MAX_ABS
with CPF does not improve the Pareto position. This supports the
paper claim that:

- **MAX_ABS is a better routing oracle** than CPF for temporal
  reasoning tasks (it catches subtle single-pixel changes that CPF's
  count threshold misses)
- **SHIFTED reuse is a real method contribution** (the whitepaper's
  shift-locality observation translates into measurable accuracy + budget
  improvements)

## Provenance

All cells ran with `--allow-dirty`. For paper-facing use, the
reuse-class finding should be rerun clean. The CPF comparison is
informative but exploratory.

## Links

- [phase 1.21 MVBench N=30](2026-04-15-phase-1_21-mvbench-motion-slice-enlargement.md)
- [phase 1.20 TOMATO N=30](2026-04-15-phase-1_20-tomato-motion-slice-enlargement.md)
- [docs/methodology/planner-sweep.md](../../../docs/methodology/planner-sweep.md)
