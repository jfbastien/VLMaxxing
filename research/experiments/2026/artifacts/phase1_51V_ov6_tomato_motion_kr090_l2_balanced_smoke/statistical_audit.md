# OV-6 Qwen TOMATO Motion Statistical Audit

Gate: codec_novel_coded >= magnitude_norm by point estimate, with Wilson intervals and paired tests reported.
Falsification: magnitude_norm exceeds codec_novel_coded by at least 3 items.

| arm | accuracy | Wilson 95% CI | vision_ms | e2e_ms | e2e+codec_ms |
| --- | ---: | --- | ---: | ---: | ---: |
| dense | 3/9 = 0.333 | [0.121, 0.646] | 11652 | 46374 | 46374 |
| magnitude_norm | 3/9 = 0.333 | [0.121, 0.646] | 11427 | 47730 | 47730 |
| uniform_random | 2/9 = 0.222 | [0.063, 0.547] | 11131 | 47736 | 47736 |
| codec_novel_coded | 3/9 = 0.333 | [0.121, 0.646] | 9670 | 40152 | 50702 |
| codec_motion | 2/9 = 0.222 | [0.063, 0.547] | 8653 | 35641 | 43975 |
| codec_residual | 1/9 = 0.111 | [0.020, 0.435] | 8535 | 34978 | 42997 |

| comparison | fixes | breaks | McNemar p | choice agreement |
| --- | ---: | ---: | ---: | --- |
| magnitude_norm_vs_dense | 2 | 2 | 1.0000 | 4/9 = 0.444 |
| uniform_random_vs_magnitude_norm | 0 | 1 | 1.0000 | 7/9 = 0.778 |
| uniform_random_vs_dense | 1 | 2 | 1.0000 | 5/9 = 0.556 |
| codec_novel_coded_vs_magnitude_norm | 0 | 0 | 1.0000 | 8/9 = 0.889 |
| codec_novel_coded_vs_dense | 2 | 2 | 1.0000 | 4/9 = 0.444 |
| codec_motion_vs_magnitude_norm | 0 | 1 | 1.0000 | 6/9 = 0.667 |
| codec_motion_vs_dense | 1 | 2 | 1.0000 | 4/9 = 0.444 |
| codec_residual_vs_magnitude_norm | 0 | 2 | 0.5000 | 5/9 = 0.556 |
| codec_residual_vs_dense | 0 | 2 | 0.5000 | 7/9 = 0.778 |

Point-estimate gate: codec_novel_coded 3 correct vs magnitude_norm 3 correct.
Falsified: False
Interpretation: boundary: all sparse arms remain near the chance floor.
