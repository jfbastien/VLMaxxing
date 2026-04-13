# Codec-Through toy experiments
These results come from synthetic scenes built to probe design choices, not from a real VLM benchmark.
## Regime results
| regime       | method             |   static_pct |   shifted_pct |   novel_pct |   reuse_pct |   halo1_windows_pct |
|:-------------|:-------------------|-------------:|--------------:|------------:|------------:|--------------------:|
| talking_head | same_position      |        99.54 |          0    |        0.46 |       99.54 |                3.8  |
| talking_head | local_search       |        98.54 |          1.28 |        0.18 |       99.82 |                2.11 |
| parking_lot  | same_position      |        99.84 |          0    |        0.16 |       99.84 |                2.53 |
| parking_lot  | local_search       |        99.05 |          0.9  |        0.05 |       99.95 |                0.84 |
| fpv_motion   | same_position      |         9.68 |          0    |       90.32 |        9.68 |              100    |
| fpv_motion   | local_search       |         0.16 |         90.59 |        9.25 |       90.75 |               36.03 |
| fpv_motion   | global_translation |        84.17 |          0    |       15.83 |       84.17 |               41.17 |

## Robot ROI results
| setting                    |   novel_tokens_pct |   halo1_windows_pct |
|:---------------------------|-------------------:|--------------------:|
| no protected ROI           |               0.12 |                0.7  |
| protect gripper+object ROI |               6.32 |               22.38 |

## Interpretation
- Same-position differencing works extremely well when the camera is mostly fixed.
- FPV / egomotion breaks naive caching, but small-motion local search or global compensation recovers large reuse.
- Once a 1-hop halo and window grouping are added, the true recompute rate is higher than raw NOVEL token percentage.
- In robotics, protecting the gripper/object ROI raises compute noticeably but is still far cheaper than recomputing the full frame.
