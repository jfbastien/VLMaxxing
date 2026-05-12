# OV-6 Qwen Random Multi-Seed Audit

Gate: All tested random seeds must be >= magnitude_norm by point estimate.
Falsification: Any seed where magnitude_norm exceeds random by at least 3 items.

Magnitude baseline: 24/57 = 0.421

| random arm | accuracy | Wilson 95% CI | fixes | breaks | McNemar p |
| --- | ---: | --- | ---: | ---: | ---: |
| uniform_random_seed1 | 31/57 = 0.544 | [0.416, 0.666] | 10 | 3 | 0.0923 |
| uniform_random_seed100 | 29/57 = 0.509 | [0.383, 0.634] | 9 | 4 | 0.2668 |
| uniform_random_seed42 | 28/57 = 0.491 | [0.366, 0.617] | 8 | 4 | 0.3877 |
| uniform_random_seed7 | 29/57 = 0.509 | [0.383, 0.634] | 8 | 3 | 0.2266 |

Point-estimate gate: 4/4 seeds random >= magnitude_norm.
Falsifying seeds: []
