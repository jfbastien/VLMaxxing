# OV-6 Track B Statistical Audit

## kr0.5_layer2_n57

| arm | acc | Wilson 95% CI | vision_ms | e2e_ms | e2e+codec_ms | codec_extract_s |
| --- | ---: | --- | ---: | ---: | ---: | ---: |
| dense | 39/57 = 0.684 | [0.555, 0.790] | 9669 | 38711 | 38711 | - |
| magnitude_norm | 24/57 = 0.421 | [0.302, 0.550] | 5415 | 33838 | 33838 | - |
| uniform_random | 28/57 = 0.491 | [0.366, 0.617] | 5226 | 33261 | 33261 | - |
| codec_novel_coded | 25/57 = 0.439 | [0.318, 0.567] | 4900 | 31146 | 48772 | 17.63 |
| codec_motion | 26/57 = 0.456 | [0.334, 0.584] | 4893 | 31092 | 48965 | 17.87 |
| codec_residual | 22/57 = 0.386 | [0.271, 0.516] | 5298 | 33729 | 53027 | 19.30 |

| comparison | fixed | broken | McNemar p | choice agreement |
| --- | ---: | ---: | ---: | --- |
| uniform_random_vs_magnitude_norm | 8 | 4 | 0.3877 | 41/57 = 0.719 |
| codec_novel_coded_vs_magnitude_norm | 8 | 7 | 1.0000 | 39/57 = 0.684 |
| codec_motion_vs_magnitude_norm | 7 | 5 | 0.7744 | 41/57 = 0.719 |
| codec_residual_vs_magnitude_norm | 7 | 9 | 0.8036 | 38/57 = 0.667 |
| magnitude_norm_vs_uniform_random | 4 | 8 | 0.3877 | 41/57 = 0.719 |
| codec_novel_coded_vs_uniform_random | 6 | 9 | 0.6072 | 38/57 = 0.667 |
| codec_motion_vs_uniform_random | 4 | 6 | 0.7539 | 44/57 = 0.772 |
| codec_residual_vs_uniform_random | 3 | 9 | 0.1460 | 43/57 = 0.754 |
| magnitude_norm_vs_dense | 4 | 19 | 0.0026 | 34/57 = 0.596 |
| uniform_random_vs_dense | 4 | 15 | 0.0192 | 37/57 = 0.649 |
| codec_novel_coded_vs_dense | 5 | 19 | 0.0066 | 31/57 = 0.544 |
| codec_motion_vs_dense | 4 | 17 | 0.0072 | 34/57 = 0.596 |
| codec_residual_vs_dense | 3 | 20 | 0.0005 | 33/57 = 0.579 |

## kr0.7_layer2_n57

| arm | acc | Wilson 95% CI | vision_ms | e2e_ms | e2e+codec_ms | codec_extract_s |
| --- | ---: | --- | ---: | ---: | ---: | ---: |
| magnitude_norm | 31/57 = 0.544 | [0.416, 0.666] | 6592 | 34442 | 34442 | - |
| codec_novel_coded | 35/57 = 0.614 | [0.484, 0.729] | 6490 | 33253 | 52078 | 18.83 |
| codec_motion | 32/57 = 0.561 | [0.433, 0.682] | 6533 | 33403 | 52416 | 19.01 |
| codec_residual | 33/57 = 0.579 | [0.450, 0.698] | 7354 | 37557 | 58065 | 20.51 |

| comparison | fixed | broken | McNemar p | choice agreement |
| --- | ---: | ---: | ---: | --- |
| codec_novel_coded_vs_magnitude_norm | 5 | 1 | 0.2188 | 51/57 = 0.895 |
| codec_motion_vs_magnitude_norm | 3 | 2 | 1.0000 | 52/57 = 0.912 |
| codec_residual_vs_magnitude_norm | 5 | 3 | 0.7266 | 49/57 = 0.860 |
| magnitude_norm_vs_dense | 3 | 11 | 0.0574 | 43/57 = 0.754 |
| codec_novel_coded_vs_dense | 4 | 8 | 0.3877 | 45/57 = 0.789 |
| codec_motion_vs_dense | 3 | 10 | 0.0923 | 44/57 = 0.772 |
| codec_residual_vs_dense | 3 | 9 | 0.1460 | 45/57 = 0.789 |

## kr0.5_layer8_n57

| arm | acc | Wilson 95% CI | vision_ms | e2e_ms | e2e+codec_ms | codec_extract_s |
| --- | ---: | --- | ---: | ---: | ---: | ---: |
| magnitude_norm | 31/57 = 0.544 | [0.416, 0.666] | 6639 | 37245 | 37245 | - |
| codec_novel_coded | 23/57 = 0.404 | [0.286, 0.533] | 6404 | 36048 | 56082 | 20.03 |
| codec_motion | 24/57 = 0.421 | [0.302, 0.550] | 7280 | 41095 | 63978 | 22.88 |
| codec_residual | 31/57 = 0.544 | [0.416, 0.666] | 6389 | 35635 | 55546 | 19.91 |

| comparison | fixed | broken | McNemar p | choice agreement |
| --- | ---: | ---: | ---: | --- |
| codec_novel_coded_vs_magnitude_norm | 5 | 13 | 0.0963 | 35/57 = 0.614 |
| codec_motion_vs_magnitude_norm | 5 | 12 | 0.1435 | 37/57 = 0.649 |
| codec_residual_vs_magnitude_norm | 6 | 6 | 1.0000 | 42/57 = 0.737 |
| magnitude_norm_vs_dense | 3 | 11 | 0.0574 | 42/57 = 0.737 |
| codec_novel_coded_vs_dense | 3 | 19 | 0.0009 | 31/57 = 0.544 |
| codec_motion_vs_dense | 3 | 18 | 0.0015 | 34/57 = 0.596 |
| codec_residual_vs_dense | 5 | 13 | 0.0963 | 38/57 = 0.667 |

## Interpretation Guardrails

- N=57 Track B cells are reproduced here, but codec-over-magnitude superiority is point-estimate evidence unless a paired test gates.
- `mean_e2e_ms` excludes separate PyAV codec extraction; `e2e+codec_ms` includes the repo-local extraction overhead.
- C-PERSIST composition must use setup-inclusive accounting and must not multiply first-query sparse-vision ratios by follow-up ratios.
