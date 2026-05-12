# OV-8 Artifact-Level Session Accounting

This is accounting-only, not a live combined runtime claim.

First-query sparse-vs-dense pairing: choice_drift=12/57; correctness_drift=12/57.

## fixed_k1 — excluded_model_side

first_query_ms=33253; followup_median_ms=7362; followup_drift=2/343

| Q | dense cold-every-query ms | combined ms | speedup |
| ---: | ---: | ---: | ---: |
| 1 | 38711 | 33253 | 1.16x |
| 2 | 77422 | 40615 | 1.91x |
| 5 | 193554 | 62700 | 3.09x |
| 10 | 387109 | 99510 | 3.89x |
| 50 | 1935543 | 393989 | 4.91x |

## fixed_k1 — included_current_pyav

first_query_ms=52078; followup_median_ms=7362; followup_drift=2/343

| Q | dense cold-every-query ms | combined ms | speedup |
| ---: | ---: | ---: | ---: |
| 1 | 38711 | 52078 | 0.74x |
| 2 | 77422 | 59440 | 1.30x |
| 5 | 193554 | 81526 | 2.37x |
| 10 | 387109 | 118336 | 3.27x |
| 50 | 1935543 | 412815 | 4.69x |

## adaptive_post_q2 — excluded_model_side

first_query_ms=33253; followup_median_ms=771; followup_drift=0/343

| Q | dense cold-every-query ms | combined ms | speedup |
| ---: | ---: | ---: | ---: |
| 1 | 38711 | 33253 | 1.16x |
| 2 | 77422 | 34023 | 2.28x |
| 5 | 193554 | 36335 | 5.33x |
| 10 | 387109 | 40188 | 9.63x |
| 50 | 1935543 | 71015 | 27.26x |

## adaptive_post_q2 — included_current_pyav

first_query_ms=52078; followup_median_ms=771; followup_drift=0/343

| Q | dense cold-every-query ms | combined ms | speedup |
| ---: | ---: | ---: | ---: |
| 1 | 38711 | 52078 | 0.74x |
| 2 | 77422 | 52849 | 1.46x |
| 5 | 193554 | 55161 | 3.51x |
| 10 | 387109 | 59014 | 6.56x |
| 50 | 1935543 | 89840 | 21.54x |

## refresh10 — excluded_model_side

first_query_ms=33253; followup_median_ms=706; followup_drift=0/343

| Q | dense cold-every-query ms | combined ms | speedup |
| ---: | ---: | ---: | ---: |
| 1 | 38711 | 33253 | 1.16x |
| 2 | 77422 | 33959 | 2.28x |
| 5 | 193554 | 36076 | 5.37x |
| 10 | 387109 | 39606 | 9.77x |
| 50 | 1935543 | 67845 | 28.53x |

## refresh10 — included_current_pyav

first_query_ms=52078; followup_median_ms=706; followup_drift=0/343

| Q | dense cold-every-query ms | combined ms | speedup |
| ---: | ---: | ---: | ---: |
| 1 | 38711 | 52078 | 0.74x |
| 2 | 77422 | 52784 | 1.47x |
| 5 | 193554 | 54902 | 3.53x |
| 10 | 387109 | 58432 | 6.62x |
| 50 | 1935543 | 86670 | 22.33x |

