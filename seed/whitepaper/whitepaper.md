---
title: "Codec-Through: Training-Free Temporal Compression for Video VLMs via Embedding Caching"
subtitle: "Research Whitepaper — April 2026"
---

# Codec-Through: Training-Free Temporal Compression for Video VLMs via Embedding Caching

**Research Whitepaper — April 2026**

Converted from the local PDF on 2026-04-13 with `mutool`, then lightly cleaned for readability. This markdown copy also carries local errata fixes where the repo audit found reference or arithmetic issues. The original PDF has been removed from this repo in favor of the corrected markdown import.

## Abstract

Current video VLMs re-encode every frame from scratch through the vision encoder, even when 80% to 99% of visual content is unchanged between frames. We show that simply caching and reusing ViT output embeddings for unchanged tokens, classified by pixel differencing as a proxy for codec metadata, achieves 29× temporal compression on conferencing video with zero quality loss on temporal reasoning benchmarks.

We validate on two standard benchmarks: TOMATO (90 temporal reasoning questions across 6 splits, Δ = -1.1%) and an MVBench sample (160 questions drawn from a 20-task benchmark, covering 18 task types in the saved local run). The approach is training-free, requires no new parameters, adds about 1.6 MB cache per frame for Qwen2.5-VL-3B at `560×560` input, and can in principle eliminate most redundant vision-side recomputation.

Composed compression arithmetic remains illustrative rather than locally measured. For example, TurboQuant reports quality-neutral KV quantization at 3.5 bits per channel, about 4.6× versus fp16, and any temporal × KV stackup should be treated as a hypothesis until measured on the same stack.

## 1. The Core Observation

Video codecs already classify every region of every frame as unchanged, moved, or new. In H.264, a P-frame macroblock with `MV=0` and `CBF=0` is a pixel-perfect copy from the previous frame. One with `MV!=0` and `CBF=0` is identical content at a different position. Only blocks with `CBF>0` contain genuinely new visual information.

We measured this on real video:

| Content | STATIC (identical) | SHIFTED (moved) | NOVEL (changed) | Source |
| --- | ---: | ---: | ---: | --- |
| Talking head (Lex Fridman) | 98.2% | 1.4% | 0.3% | Pixel-level 16×16 MB classification |
| Surveillance (parking lot) | 80.7% | 9.3% | 10.0% | 1280×720 H.264, 150 frames |
| FPV drone (mountain run) | 40.2% | 29.2% | 30.6% | Extreme motion worst case |

If a ViT output embedding is determined by the input pixels, and the input pixels have not changed, then the embedding should not change either. We tested this hypothesis directly.

## 2. Empirical Validation

### 2.1 ViT Embedding Identity

Test: Encode the same image twice through Qwen2.5-VL-3B's vision encoder. Compare output embeddings.

Result: cosine similarity = `1.000000`. Max absolute difference = `0`. The ViT is perfectly deterministic. Any deviation from `1.0` in subsequent comparisons is real signal, not numerical noise.

### 2.2 Attention Locality Under Partial Change

Test: Change 1 of 400 tokens (0.25% of image) and re-encode. Measure how much unchanged tokens' embeddings shift.

| Region | Cosine sim to original |
| --- | ---: |
| Changed token | 0.905 |
| 8 neighbor tokens | 0.968 |
| 4 corner tokens (far away) | 0.99999 |

With 5% of tokens changed (realistic P-frame), unchanged tokens retain `0.990` cosine similarity. Global self-attention spreads changes, but the effect drops off sharply with distance.

### 2.3 Localized Motion Preserves Embeddings

Test: Shift content within a single 28×28 block by `N` pixels, simulating real video motion, keep the rest of the image identical, and measure the shifted token's embedding similarity.

| Pixel shift | Cosine similarity |
| --- | ---: |
| 0 px | 1.00000 |
| 1 px | 0.99875 |
| 4 px | 0.99705 |
| 8 px | 0.99664 |
| 14 px (half a token) | 0.99618 |

For realistic video motion (2 to 8 pixels), embedding similarity exceeds `0.997`, which is in the same rough regime often treated as acceptable for aggressive cache compression.

### 2.4 End-to-End Quality Suite

Test: Process real video frames with temporal embedding caching. For each frame, compare LLM output, fresh encode versus cached, across 5 task types of increasing difficulty.

| Task | Difficulty | Talking Head | Surveillance | FPV Drone |
| --- | --- | ---: | ---: | ---: |
| Scene description | Easy | 100% | 100% | 100% |
| Object location | Medium | 100% | 100% | 100% |
| Visual detail | Medium | 100% | 100% | 100% |
| Background detail | Hard | 100% | 100% | 100% |
| Yes/No grounding | Hard | 100% | 100% | 100% |

58/60 tests pass (97%). The 2 "failures" are false negatives. In both cases, baseline and cached outputs correctly identify "no person visible" in a surveillance scene with different phrasing.

### 2.5 TOMATO Temporal Reasoning Benchmark (7B)

Test: 90 questions from the TOMATO benchmark (ICLR 2025) across all 6 temporal reasoning splits on Qwen2.5-VL-7B via MLX. 8 frames per video. This benchmark specifically tests whether models can reason about temporal dynamics, the adversarial case for embedding caching.

| Split | Baseline | Cached | Delta |
| --- | ---: | ---: | ---: |
| Count | 20% | 20% | +0% |
| Direction | 20% | 20% | +0% |
| Rotation | 13% | 13% | +0% |
| Shape & trend | 7% | 7% | +0% |
| Velocity & frequency | 13% | 13% | +0% |
| Visual cues | 47% | 47% | +0% |
| Overall | 20.0% | 20.0% | +0.0% |

100% choice agreement on the full benchmark. The complete TOMATO evaluation, all 1,484 questions across all 6 splits, did not change a single answer. The 7B model is reported as completely indifferent to embedding caching.

Full TOMATO (1,484 questions):

| Split | N | Baseline | Cached | Delta |
| --- | ---: | ---: | ---: | ---: |
| Count | 292 | 29.8% | 29.8% | +0.00% |
| Direction | 403 | 15.6% | 15.6% | +0.00% |
| Rotation | 286 | 19.6% | 19.6% | +0.00% |
| Shape & trend | 223 | 25.1% | 25.1% | +0.00% |
| Velocity & frequency | 210 | 19.0% | 19.0% | +0.00% |
| Visual cues | 70 | 38.6% | 38.6% | +0.00% |
| Total | 1,484 | 22.2% | 22.2% | +0.00% |

1,484 out of 1,484 answers are reported as identical. Average token reuse: `83.2%`.

### 2.6 MVBench Video Understanding Benchmark (7B)

Test: 160 questions from the MVBench benchmark on Qwen2.5-VL-7B via MLX. 8 frames per video. The saved local run covers 18 task types from the full 20-task benchmark. Tasks include action recognition, object tracking, scene transitions, counterfactual reasoning, movement direction, egocentric navigation, and more.

| Metric | Value |
| --- | ---: |
| Baseline accuracy | 40.0% |
| Cached accuracy | 40.0% |
| Delta | +0.0% |
| Choice agreement | 100% |
| Avg token reuse | 74.2% |

100% choice agreement is reported across the 18 task types present in the saved run. Combined with TOMATO, this is a stability result relative to the dense baseline, not a claim of state-of-the-art absolute benchmark accuracy.

## 3. Method

### 3.1 Token Classification

For each consecutive frame pair, classify every visual token position:

- `STATIC` (`pixel diff < 3`): content identical. Cache and reuse the previous frame's ViT output embedding at this position.
- `SHIFTED` (`pixel diff 3-8`): content similar, minor motion. Cache and reuse, validated at `0.997+` cosine similarity for realistic motion magnitudes.
- `NOVEL` (`pixel diff >= 8`): content changed. Re-encode through the vision encoder.

In production, pixel differencing would be replaced with codec metadata:

- `MV=0 -> STATIC`
- `MV!=0 and CBF=0 -> SHIFTED`
- `CBF>0 -> NOVEL`

That would eliminate the need for full frame decode during classification.

### 3.2 Embedding Cache

A 2D tensor of shape `(merged_h × merged_w × embed_dim)` per reference frame. For Qwen2.5-VL, this is model- and resolution-dependent.

Examples:

- Qwen2.5-VL-3B at `560×560`: `400` merged tokens × `2048` fp16 dims = about `1.6 MB`
- Qwen2.5-VL-3B at `280×280`: `100` merged tokens × `2048` fp16 dims = about `0.4 MB`
- Qwen2.5-VL-7B at `560×560`: `400` merged tokens × `3584` fp16 dims = about `2.8 MB`

The overhead is still modest, but it should be reported with the actual model and input resolution.

### 3.3 I-Frame Refresh

To guard against possible global-attention context drift, the method periodically re-encodes all tokens at I-frame boundaries. With a typical H.264 GOP of 1 I-frame per 30 frames at 30 fps:

| Content | NOVEL % per P-frame | I-frame overhead (1/30) | Effective compression |
| --- | ---: | ---: | ---: |
| Talking head | 0.1% | 3.3% | 29× |
| Surveillance | 10% | 3.3% | 7.7× |
| FPV drone | 30.6% | 3.3% | 3.0× |

### 3.4 Integration

The mechanism is implemented as a forward hook on the vision encoder. No model modifications, no retraining, and no new parameters. The paper claims it works with any VLM that has a separable vision encoder, including Qwen2.5-VL, LLaVA, and Gemma 4.

## 4. What We Killed

Honest accounting of ideas that did not survive experimental validation:

| Idea | Status | Why |
| --- | --- | --- |
| DCT bypass as compression layer | Killed | DCT is a basis change, not size reduction. Patch embedding is 0.7% of ViT FLOPs. |
| DCT-initialized rotation for KV cache | Killed | TurboQuant's random rotation at 3-bit is within 2.7× of the Shannon bound. Less than 0.1 perplexity room for improvement. |
| Provenance-aware KV bit allocation | Killed | Diminishing returns. After temporal elimination removes `STATIC` tokens, surviving tokens are disproportionately `NOVEL` with similar importance. |
| Whole-image shift methodology | Killed | Gave misleadingly bad results (`0.72` cosine). Real video has localized shifts with stable context (`0.997+`). Methodology correction was critical. |
| Global MV compensation for FPV drone | Killed | Translational RANSAC only gave `+0.6%`. Camera rotation needs affine estimation. |
| Output-embedding warping without correction | Killed | ViT bakes position deeply into embeddings. Cross-boundary embedding swap gives `0.72` cosine. The paper claims the LLM is robust to it anyway. |

## 5. Composition with KV Cache Compression

Temporal token elimination, fewer entries, composes with KV entry compression, fewer bits per entry. The arithmetic below is illustrative only, not a measured end-to-end system result.

| Layer | Mechanism | Compression | Training required |
| --- | --- | ---: | --- |
| Temporal caching | Cache `STATIC + SHIFTED` embeddings | 3-29× | None |
| TurboQuant | 3.5-bit KV quantization, quality-neutral | about 4.6× | None |
| STATIC KV dedup | PagedAttention CoW | 1.3-1.7× | None |
| Composed | Combined effect | illustrative only | None |

Any composed total should be measured on the same stack before it is treated as a real systems claim.

### Illustrative Impact Only

The original whitepaper included stacked scenario arithmetic for large-server and edge deployments. In this repo, those scenarios are treated as thought experiments only until the component gains are measured on the same stack.

## 6. Comparison with CoPE-VideoLM

CoPE-VideoLM, February 2026, Stanford, Microsoft, ETH, is presented as the most directly comparable work.

| Topic | CoPE-VideoLM | Codec-Through |
| --- | --- | --- |
| Approach | Train delta-encoder for P-frames | Cache ViT embeddings for unchanged tokens |
| Training cost | 21,000 GPU-hours | 0 GPU-hours |
| New parameters | about 15M | 0 |
| I-frame handling | Standard RGB encode | Same plus Q-table spatial merge, future |
| P-frame handling | 8 delta-tokens per frame | Per-token: 0 for `STATIC`, cache for `SHIFTED` |
| B-frame support | No, future work | Same classification applies |
| TOMATO accuracy | 28.3, 7B model | 18.9%, 3B model, not directly comparable |
| Token reduction | 93% | 79% to 99%, content-dependent |
| Code available | No | Yes, forward hooks, about 100 lines |

The stated trade-off:

- CoPE improves temporal reasoning by training a delta encoder.
- Codec-Through preserves the baseline's temporal reasoning without training.

## 7. Additional Signal: Q-Table Spatial Merge

Beyond temporal caching, the whitepaper claims a second codec metadata signal: JPEG quantization tables as a zero-cost spatial merge pre-filter.

Finding:

- surviving DCT coefficient count correlates at `rho = 0.93`, Spearman, with pixel variance across 15 real JPEG images
- 73.2% of blocks can be classified as `FLAT` or `COMPLEX` from the Q-table alone
- learned scoring is then required on only 26.8% of tokens

This is described as signal-level validation, not end-to-end VLM benchmark validation.

## 8. Limitations and Future Work

- Validated on 3B and 7B models.
- Qwen2.5-VL-3B, PyTorch/MPS, was used for mechanism experiments.
- Qwen2.5-VL-7B, MLX, was used for benchmark evaluation.
- The larger model is reported as more robust to embedding perturbation.

Further stated limitations:

- pixel differencing is only a proxy for codec MV + CBF
- TOMATO was run fully, MVBench only partially, 160 of 4000
- single-hop caching only
- quality versus refresh interval is not yet characterized
- memory constraints limited the evaluation to 4 frames per video in some settings, even though many video benchmarks use 8 to 32 frames

## 9. Experimental Methodology

The whitepaper reports:

- mechanism experiments, Sections 2.1 to 2.4, on Apple M5 Max, 128 GB, with MPS backend and Qwen2.5-VL-3B-Instruct in float32
- benchmark evaluations, Sections 2.5 to 2.6, on Qwen2.5-VL-7B-Instruct via `mlx-vlm` on the same hardware
- about `36 tokens/sec`
- `16.6 GB` peak memory

Additional stated methodology details:

- videos sourced from YouTube
- TOMATO from the official dataset
- MVBench from Hugging Face
- `cached_image_features` on `mlx-vlm` was used for the 7B path
- PyTorch forward hooks were used for the 3B path
- about 100 lines of code
- thresholds `STATIC < 3`, `SHIFTED < 8` were set once and not tuned per benchmark

The paper also mentions a broader AI-assisted research process involving multiple fleet missions and agents before local validation.

## 10. Conclusion

The simplest version of the Codec-Through thesis is presented as working:

- cache ViT embeddings for unchanged video tokens
- re-encode only what changed
- use no training
- add no new parameters
- avoid architecture modification

The paper's closing claim is that the quality floor for temporal embedding caching is much lower than expected:

- imported, not yet locally verified in this repo: even at `0.85` embedding cosine similarity, after 14 frames without refresh, every output remained semantically correct in the reported tests
- 29× temporal compression was reported on conferencing video
- the paper reports zero delta on all 1,484 TOMATO questions and on a 160-question MVBench slice

Final line:

> The codec already knows what changed. Stop re-encoding what didn't.
