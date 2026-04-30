# Phase 1.62D — low-FPS dense baseline findings

## Preregistered question

Is a simple lower-frame dense baseline enough to explain the session/composition
benefits, or does it lose too much quality?

## Protocol

- Model/runtime: Qwen2.5-VL-7B-Instruct-4bit on the local MLX stack.
- Corpus: VideoMME composition corpus, 57 sessions / 171 queries.
- Comparison: dense 4-frame baseline versus dense 8-frame baseline.

## Result

- Overall accuracy: 4f = 0.5088, 8f = 0.5614, delta = -0.0526 with 95% CI
  [-0.1228, 0.0175].
- Choice agreement: 0.7251.
- Median speedup: 1.2116x.
- Parse failures: 0 in both arms.
- Short bucket: delta = -0.1930 with 95% CI [-0.3158, -0.0702].

## Interpretation

The low-FPS dense baseline is not a strawman. It is ambiguous overall and
clearly damaging on the short bucket. The paper should use it as baseline
pressure, not as a fully defeated alternative.

## Artifacts

- `research/experiments/2026/artifacts/phase1_62D_lowfps_dense_videomme/lowfps_4f_vs_8f_summary.json`
- `research/experiments/2026/artifacts/phase1_62D_lowfps_dense_videomme/cold_dense_4f_summary.json`
