# Application Taxonomy for Temporal Feature Reuse

Date: 2026-04-17
Parent: [paper/framing.md](../paper/framing.md)

This document enumerates the application classes where training-free
temporal feature reuse has different expected behavior, so the paper
can scope its contribution honestly rather than claim a universal
result.

The taxonomy is an application-side companion to the
content-conditional statistic finding (phase 1.36 oracle: Pearson r
0.23 TOMATO vs 0.50 MVBench on the best pixel statistic; Planner 2.0
MAX_ABS wins routing cross-benchmark but is the worst point
predictor on both). Different content classes concentrate the
pixel→feature signal differently, and the paper's claim scope
should match.

## Axis 1: Camera motion

| Class | Expected reuse behavior | Example |
|---|---|---|
| **Static camera** | HIGH reuse. Background blocks are near-identical across frames; novelty concentrates on moving subjects. Pixel-diff is a strong proxy. | Surveillance, talking head, lab bench, monitor capture |
| **Forward-driving** | MEDIUM reuse. Radial optical flow means every block changes, but change is structured (expansion from focus-of-expansion). Pixel-diff sees uniform change and under-uses available redundancy. A motion-compensated proxy (phase 1.29 MV-only) would likely recover more signal here. | Dashcam, autonomous driving, FPV drone in transit |
| **Egocentric / head-mounted** | LOW reuse. Camera motion is jerky, parallax-heavy, and unpredictable. Novelty is dominated by camera motion, not scene events. Pixel-diff is a weak proxy; feature-space metrics help but are not cheap. | Ego4D, smart glasses, sports camera |
| **Handheld / consumer** | VARIABLE. Mix of static and motion depending on user intent; framing hesitations create short bursts of reuse opportunity. | Social video, home recording |

## Axis 2: Content density

| Class | Expected reuse behavior |
|---|---|
| **Talking head / lecture** | HIGH reuse except around mouth and hand regions; spatial pruning (Gemma-style) is additive. |
| **Surveillance** | HIGH reuse except around entry/exit events; placement-over-time is critical (phase 1.26 sticky-dynamic motivation). |
| **Screen capture / UI** | HIGH reuse except around UI changes and scroll events; has near-binary change character. Strong candidate for a specialization line. |
| **Cooking / how-to** | MEDIUM reuse. Objects appear/disappear; hand occlusion creates localized change. |
| **Sports / action** | LOW reuse. Decisive-event frames are short and content is globally novel during motion. TOMATO-style constrained motion is the hardest case. |

## Axis 3: Task type

| Class | Expected mechanism sensitivity |
|---|---|
| **Temporal-reasoning QA** (TOMATO, TempCompass, MVBench motion) | Placement-over-time is critical; novelty magnitude is NOT a substitute (phase 1.34 TOMATO novelty-ranked under-performs uniform by 0.100 at N=6 and N=8). |
| **Long-video summarization / retrieval** (VideoMME long, EgoSchema) | Token reuse across a long horizon matters more than event localization; bounded staleness is the load-bearing mechanism. |
| **Video captioning** (pre-temporal-reasoning paradigm) | May be robust to aggressive reuse; less informative for our thesis. |
| **Robotics / control** | Real-time constraints dominate; approximate-computing contract is hard-checkable. Not in our current evaluation scope. |

## How this structures the paper

The paper's headline claim applies to **temporal-reasoning QA on
static-to-medium-motion content**. The evaluated benchmarks
(MVBench motion, TOMATO motion, future VideoMME + TempCompass)
largely sit in that box. We explicitly do NOT claim:

- that the method transfers to egocentric content (different
  novelty structure)
- that the method beats dense on high-motion sports content (low
  reuse available)
- that the method is appropriate for real-time robotics
  perception (answer-stability metric ≠ latency-bounded correctness)

When Gemma-novelty-pruning (Axis 2 spatial) composes with our
temporal reuse (Axis 1), the application classes that benefit most
are those where BOTH axes have headroom — static-camera talking
head is the cleanest example; forward-driving is intermediate;
egocentric is the hardest.

## Content-class labeling for future evaluation

When a future phase adds a benchmark, label the content along
these three axes in the phase note. That way cross-benchmark
generalization claims can be checked against the axis coverage,
not just against benchmark names.

## Links

- [paper/framing.md](../paper/framing.md) — paper scope
- [docs/benchmark-taxonomy.md](benchmark-taxonomy.md) — benchmark-
  level content labels (may need update)
- [research/experiments/2026/2026-04-17-phase-1_34-novelty-ranked-dense.md](../research/experiments/2026/2026-04-17-phase-1_34-novelty-ranked-dense.md)
  — first empirical evidence that content class flips the
  novelty-ranking sign (TOMATO hurt, MVBench N=4 help)
