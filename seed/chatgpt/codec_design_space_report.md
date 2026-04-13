# Expanded codec design-space toy experiments
These experiments probe design ideas suggested by codec theory and the whitepaper, but they are synthetic and do **not** replace end-to-end VLM benchmarking.

## 1) Color-aware planning
This experiment creates a square whose **luma stays constant while chroma changes**. It tests a key failure mode of luma-only screening: non-color tasks may safely reuse such regions, while color-sensitive tasks should refresh them.

| method                             |   novel_pct | notes                                                                    |
|:-----------------------------------|------------:|:-------------------------------------------------------------------------|
| RGB diff baseline                  |        3.52 | Detects pure chroma change because RGB values moved.                     |
| Color-aware planner / GENERAL task |        0    | Treats chroma-only differences as reusable for non-color tasks.          |
| Color-aware planner / COLOR task   |        3.52 | Promotes chroma-only differences to NOVEL for color-sensitive questions. |

Interpretation:
- A generic planner can safely ignore some chroma-only changes for many tasks.
- A color-sensitive policy should explicitly promote chroma-only changes to refreshes.
- This is a concrete reason to make compression **task-aware**, not just frame-aware.

## 2) Attention focused on changed blocks
We estimate attention interaction counts for a 400-token frame under several sparse attention schedules.

Best strategy by dynamic ratio:

|   dynamic_ratio | strategy                     |   reduction_x |
|----------------:|:-----------------------------|--------------:|
|            0.01 | dynamic_only_global          |         33.33 |
|            0.02 | dynamic_only_global          |         25    |
|            0.05 | changed_queries_plus_summary |         21.74 |
|            0.1  | changed_queries_plus_summary |         18.35 |
|            0.2  | changed_queries_plus_summary |         11.56 |
|            0.4  | changed_queries_plus_summary |          4.75 |
|            0.6  | changed_queries_plus_summary |          2.41 |

Interpretation:
- When only 1%-10% of tokens are dynamic, changed-block-focused attention can reduce attention work by roughly an order of magnitude in this toy model.
- Savings shrink as the dynamic fraction rises, which is why FPV/egomotion content needs better motion compensation and/or multi-reference caches.
- This estimate only covers attention interactions; real speedups depend on implementation details, memory traffic, and how much of the encoder can skip recomputation.

## 3) Adaptive codec-style partitioning
This experiment uses a quadtree over luma variance to imitate variable block sizes such as codec CTUs / recursive partitions. The minimum block size is 16×16, matching the fixed-token baseline; the gain comes only from keeping flat regions coarse.

| scene        |   baseline_16x16_tokens |   adaptive_leaves |   compression_vs_fixed |
|:-------------|------------------------:|------------------:|-----------------------:|
| flat         |                     256 |                16 |                  16    |
| mixed_detail |                     256 |               154 |                   1.66 |

Interpretation:
- Large flat regions deserve coarse tokens or large skipped blocks.
- Dense or text-like regions deserve finer partitions.
- A variable-resolution visual frontend could therefore behave more like a modern codec: spend detail budget where entropy is concentrated.

## Takeaways
1. **Model changes are worth it.** The zero-change path is excellent for validation, but bigger gains appear when the encoder/attention schedule becomes change-aware.
2. **Color should be conditional.** Luma-first screening is attractive, but color questions, screen content, and UI text need a more conservative policy.
3. **Codec partition logic is underused.** Recursive variable block sizes look promising for VLM tokenization, especially on content with large flat regions and small dense details.
4. **Attention can be guided by change maps.** Even a crude changed-query schedule offers strong theoretical savings when the dynamic token fraction is low.

## Generated artifacts
- Attention savings plot: `codec_attention_savings.png`
- Color-aware masks: `codec_color_change_masks.png`
- Flat-scene quadtree: `codec_quadtree_flat.png`
- Mixed-detail quadtree: `codec_quadtree_mixed_detail.png`