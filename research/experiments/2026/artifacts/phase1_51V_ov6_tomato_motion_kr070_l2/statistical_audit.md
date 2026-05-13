# OV-6 Qwen TOMATO Motion Statistical Audit

Gate: codec_novel_coded >= magnitude_norm by point estimate, with Wilson intervals and paired tests reported.
Falsification: magnitude_norm exceeds codec_novel_coded by at least 3 items.

| arm | accuracy | Wilson 95% CI | vision_ms | e2e_ms | e2e+codec_ms |
| --- | ---: | --- | ---: | ---: | ---: |
| dense | 8/30 = 0.267 | [0.142, 0.445] | 12093 | 46000 | 46000 |
| magnitude_norm | 4/30 = 0.133 | [0.053, 0.297] | 7218 | 34676 | 34676 |
| uniform_random | 4/30 = 0.133 | [0.053, 0.297] | 8321 | 39991 | 39991 |
| codec_novel_coded | 5/30 = 0.167 | [0.073, 0.336] | 9760 | 45877 | 56178 |
| codec_motion | 5/30 = 0.167 | [0.073, 0.336] | 8539 | 40095 | 49216 |
| codec_residual | 4/30 = 0.133 | [0.053, 0.297] | 8402 | 39590 | 48713 |

| comparison | fixes | breaks | McNemar p | choice agreement |
| --- | ---: | ---: | ---: | --- |
| magnitude_norm_vs_dense | 1 | 5 | 0.2188 | 14/30 = 0.467 |
| uniform_random_vs_magnitude_norm | 0 | 0 | 1.0000 | 22/30 = 0.733 |
| uniform_random_vs_dense | 1 | 5 | 0.2188 | 15/30 = 0.500 |
| codec_novel_coded_vs_magnitude_norm | 2 | 1 | 1.0000 | 21/30 = 0.700 |
| codec_novel_coded_vs_dense | 1 | 4 | 0.3750 | 18/30 = 0.600 |
| codec_motion_vs_magnitude_norm | 2 | 1 | 1.0000 | 19/30 = 0.633 |
| codec_motion_vs_dense | 2 | 5 | 0.4531 | 14/30 = 0.467 |
| codec_residual_vs_magnitude_norm | 0 | 0 | 1.0000 | 21/30 = 0.700 |
| codec_residual_vs_dense | 1 | 5 | 0.2188 | 13/30 = 0.433 |

Point-estimate gate: codec_novel_coded 5 correct vs magnitude_norm 4 correct.
Falsified: False
Interpretation: boundary: all sparse arms remain near the chance floor.
