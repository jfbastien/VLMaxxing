# Codec-Through Codebase Review and Revised Science Plan

## 1. Executive summary

This repository is much more mature than the whitepaper alone suggests. It is not just a single caching hack. It contains:

- a working **benchmark path** for temporal embedding reuse on Qwen2.5-VL-7B via MLX
- a **mechanism path** for PyTorch/MPS experiments on Qwen2.5-VL-3B
- a substantial **codec-native exploration branch** for motion vectors, residuals, frame headers, H.264 spatial signals, and bit-allocation proxies
- a partially implemented **spatial cascade** branch for JPEG/Q-table-guided token reduction
- a **wall-clock timing harness** that appears to have been designed carefully but not yet completed in the experimental narrative
- a large **research knowledge layer** from agent missions with many negative results already explored and synthesized

The codebase strongly reinforces the main scientific claim:

> Video VLMs tolerate much more temporal embedding reuse than expected.

But it also makes the next step much clearer:

> The next frontier is not proving that reuse is semantically safe. The next frontier is moving the reuse boundary deeper into the runtime so that it saves real encoder and attention compute.

## 2. What the codebase actually does

### 2.1 Core benchmark path

The most important benchmark file is `experiments/run_tomato_mlx.py`.

What it does:
- extracts `n` frames from a video with ffmpeg
- encodes all video frames through the vision tower once
- splits vision features frame-by-frame using `grid_thw`
- builds a cached version where frame 0 is fresh and later frames reuse cached token embeddings for blocks classified as STATIC or SHIFTED
- passes the modified image features into `mlx-vlm` using `cached_image_features`
- compares baseline answer vs cached answer on TOMATO and MVBench

What this means scientifically:
- this path is a **strong semantic validation** of embedding reuse
- it is **not yet the final systems implementation** of sparse execution, because the fresh features are still computed for every frame before mixing

So the current benchmark code proves:
- the model output is robust to token reuse

It does **not yet fully prove**:
- how much wall-clock speedup a production sparse encoder implementation will achieve

That distinction is critical and should stay explicit in the paper and in all future work.

### 2.2 Mechanism experiments

The PyTorch/MPS branch includes files like:
- `exp_phase1d_e2e_cache.py`
- `exp_phase1e_static_identity.py`
- `exp_phase2_shifted_warp.py`
- `exp_phase2b_position_separability.py`
- `exp_mv_embedding_relocation.py`
- `exp_mv_reloc_e2e.py`

These are the “science microscope” experiments. They test:
- exact determinism of the ViT output
- how local changes spread through attention
- whether shifted content preserves embeddings
- whether position is too deeply baked into the embedding to permit relocation/warping
- whether output substitution affects LLM answers

This branch is where most of the real conceptual learning happened.

### 2.3 Codec-native branch

The repository also contains a serious codec-native exploration:
- `codec_pipeline.py`
- `exp_a2_mv_extraction.py`
- `exp_codec_native_classify.py`
- `exp_per_block_mv_lookup.py`
- `exp_h264_spatial_signals.py`
- `exp_h264_deep_signals.py`
- `exp_bit_allocation.py`
- `exp_bit_allocation_deep.py`

This branch asks a different question:

> If the codec already knows what changed, can the VLM use codec signals instead of or before pixel differencing?

What it found:
- motion vectors are extractable in software decode paths
- residual energy can approximate coded/non-coded novelty
- frame headers and packet sizes are useful cheap early signals
- exact per-macroblock bit counts are hard to recover without deep CABAC-level instrumentation or modified decoders
- codec-native signals are useful, but they are not automatically better than plain pixel diff for semantic-preservation experiments

### 2.4 Spatial branch

The spatial work is more advanced than it first appears:
- `qtable_prefilter.py`
- `qtable_merge_mlx.py`
- `qtable_spatial_merger.py`
- `spatial_merge.py`
- `spatial_cascade.py`
- `run_qtable_benchmark.py`
- `run_cascade_benchmark.py`

This branch is not just “Q-table curiosity.” It is a full alternative track:
- stage 1: temporal cache
- stage 2: flat-region detection / cheap merge
- stage 3: prune low-importance survivors
- stage 4: merge remaining similar tokens

The important meta-result is not that JPEG Q-tables replace attention. They do not.
The important result is that **codec-derived flatness can cheaply pre-partition the problem**, so expensive scoring needs to run on fewer tokens.

### 2.5 Timing and systems branch

`exp_wall_clock_speedup.py` is a strong sign that the codebase already understood the main remaining gap.

It tries to separately time:
- ViT encode
- token classification
- LLM prefill
- generation

This is exactly the right measurement decomposition.

But the codebase still needs one more level of systems work:
- truly sparse vision execution
- changed-token-focused attention
- decode-side fast paths without temp-file-heavy frame extraction

## 3. What the codebase learned

## 3.1 Strong conclusions

### A. Temporal reuse is real and robust

This is the strongest result in the whole repo.

The whitepaper result is not a fluke. The code shows a coherent chain:
- identical pixels produce identical vision outputs
- small localized motion keeps embeddings extremely similar
- LLM outputs are largely insensitive to these small hidden-state perturbations
- benchmark answers remain unchanged under aggressive reuse

### B. Same-position caching is much stronger than expected

A major surprise is how often same-position reuse already works, even when “true motion” exists.
That means the model is more tolerant of positional mismatch than we might expect from raw embedding cosine alone.

### C. Relocation/warping is much weaker than expected

The repository explored motion-vector relocation carefully and mostly killed it.
Why?
- many motions stay inside the same pooled token anyway
- once motion crosses boundaries, position information contaminates the embedding
- cross-boundary relocation gives little or no end-to-end improvement

This is one of the most valuable negative results.

### D. Pixel diff beats codec-native classification for the current paper

This is extremely important.

The codebase did *not* just assume codec-native is better.
It found that for the present benchmark objective, pixel diff is often the best practical proxy because it measures the final decoded image the model actually sees.

That means the correct framing is:
- pixel diff is the best current semantic validation tool
- codec metadata is the best next production/systems tool

### E. Spatial codec signals are useful as pre-filters, not semantic oracles

The spatial branch found that codec-derived signals like Q-table flatness, MB type, coefficient counts, QP, etc. do not replace final model saliency.
But they can help cheaply identify:
- obvious flatness
- obvious complexity
- regions where more expensive scoring should be focused

This is a very strong systems insight.

## 3.2 Negative results that matter

The repo already killed several tempting but weak directions:

- DCT bypass as a multiplicative compression layer
- DCT-initialized rotation for KV quantization
- provenance-aware KV bit allocation as a major additional win after temporal filtering
- naive output-embedding relocation
- simple translational global compensation for FPV motion
- many H.264 spatial signals as standalone saliency predictors

This is excellent science. Keep these negative results visible.

## 4. Code review findings

## 4.1 Scientific strengths

The codebase is much better than a throwaway prototype because it has:
- direct mechanism experiments
- benchmark validation
- alternative pipelines that were actually tried
- explicit negative-result tracking
- a clear split between semantic validation and future production design

## 4.2 Engineering issues to fix immediately

### 1. Remove and rotate the Hugging Face token

`experiments/run_gemma4_validation.py` contains a hardcoded HF token.
That should be treated as compromised and rotated immediately.
Do not keep secrets in-source.

### 2. Unify duplicated core utilities

Many files duplicate:
- ffmpeg frame extraction
- `classify_blocks`
- temp file handling
- hook registration patterns

This increases drift and hides bugs.

Refactor into a small reusable library, e.g.:
- `codec_through/io.py`
- `codec_through/classify.py`
- `codec_through/hooks.py`
- `codec_through/bench.py`

### 3. Fix known hook/resource bugs before more benchmarking

The reviewer artifacts already found several meaningful issues:
- forward hook leaks on exception paths
- stale state bug in `SpatialCascade`
- temp file leaks
- missing subprocess error checks

These should be fixed before running new ablations, otherwise you risk measuring a broken pipeline.

### 4. Remove local absolute paths

Several H.264/deep-signal scripts still contain local machine paths and local decoder paths.
That makes reproduction hard.

### 5. Reduce file-I/O-heavy frame pipelines

The repo writes many frames to `/tmp/*.png` or `/tmp/*.jpg`, then re-reads them.
This is acceptable for small experiments, but it will badly distort timing on a 16GB M3 Air and can dominate short-video runtime.

Move toward:
- in-memory frame arrays
- batched decode
- persistent reusable frame cache
- avoiding per-frame temp-file creation during benchmark loops

## 4.3 Scientific caveat in the current benchmark implementation

The current `run_tomato_mlx.py` path mixes cached features **after** a fresh multi-frame vision pass.
That is the right way to validate output stability.
It is not the right way to claim end-to-end speedup.

So there should be two explicitly named paths in the codebase:

- **semantic substitution path**: proves answer stability
- **sparse execution path**: proves actual speedup

Right now the repo has the first and design scaffolding for the second.

## 5. What else we should do that was not emphasized enough before

These are the main new directions that became clearer after reviewing the codebase.

## 5.1 Changed-token-focused attention

This is now the most important missing experiment.

The repository validated that codec and pixel signals are good at identifying novelty, but weak at identifying semantic importance globally.
That suggests a new architecture rule:

- use codec/pixel signals to decide **who is dynamic**
- use model attention to decide **what matters among the dynamic subset**

In other words:
- static tokens become memory
- changed tokens become active queries
- only changed queries get broad attention
- static queries either skip compute, use local attention, or attend only to a compact summary bank

This is the cleanest way to combine the repo’s temporal results with the spatial negative results.

## 5.2 Canonical-coordinate caching via frame stabilization

The repo killed naive embedding relocation, which is correct.
But there is a different path that was not pushed hard enough:

**stabilize the frame first, then reuse same-position tokens in stabilized coordinates.**

Instead of moving embeddings around in token space, estimate global camera motion in image space:
- affine / homography / ECC / feature-based stabilization
- warp the frame toward a canonical background coordinate system
- then apply same-position caching

This avoids the “embedding already contains position” problem by moving the pixels instead of moving the embeddings.

This is especially promising for:
- FPV/drone
- dashcam
- egocentric video
- mobile robotics

## 5.3 Codec-conditioned frame scheduling

The codebase focuses on token reuse within chosen frames.
Another powerful lever is to change **which frames are chosen at all**.

Use codec/header signals to schedule frames before vision encoding:
- always keep I-frames
- keep P/B frames with large packet size or high residual rate
- aggressively drop tiny skip-heavy B-frames
- increase sampling density near novelty bursts and scene transitions

This is especially attractive on an M3 Air because it reduces decode, encode, and LLM prefill together.

## 5.4 Multi-reference caching and B-frame-aware reuse

The codebase is still mostly single-hop: compare frame `t` to `t-1`.

But the codec itself is not single-hop.
A better system should maintain multiple references:
- previous reference frame
- previous I/P frame
- optionally future reference when offline processing is allowed
- a static background memory

Then a block can choose the best source:
- same-position from current reference
- same-position from older reference
- stabilized background reference
- fresh encode

This is probably better than embedding relocation and aligns more naturally with codec semantics.

## 5.5 Treat codec signals as uncertainty, not saliency

This is one of the most important conceptual updates.

The spatial-signal branch showed that codec signals are poor replacements for final attention.
That does **not** make them weak.
It means their right role is different.

Use codec signals to answer:
- how risky is it to cache this region?
- how much detail might be missing here?
- where should the model spend more compute?

Examples:
- high residual energy → unsafe to reuse
- flat region with low residual → safe to compress
- high QP / strong distortion region → refresh or route to higher-quality crop
- strong chroma difference with low luma difference → refresh only if color-critical

This is the right way to use codec metadata.

## 5.6 Task-aware luma/chroma/resolution policies

The original codebase is largely RGB-uniform.
But codec theory says not all bits are equally valuable.

Next experiments should split decisions by task class:
- motion / counting / scene gist → luma-first, maybe low chroma resolution
- OCR / UI / charts → preserve edges and local detail, maybe screen-content path
- color questions → chroma refresh required
- localization / small objects → higher resolution or ROI refinement

This will likely matter more than trying to squeeze more signal from generic H.264 metadata.

## 5.7 Screen-content path

The repo explored JPEG/Q-table flatness, but it did not yet fully fork a separate screen-content strategy.
That is a missed opportunity.

For screen video or slides:
- repeated glyphs
- large flat backgrounds
- low color cardinality
- exact copies of icons and UI tiles

That suggests:
- exact-copy token dedup
- palette/cardinality-aware tokenization
- higher weight on sharp edges and text boxes
- possible glyph dictionary reuse

This could outperform generic natural-image heuristics by a lot.

## 5.8 Layer-segmented caching for Qwen2.5-VL’s attention pattern

The codebase already measured Qwen’s sawtooth pattern of local and full-attention layers.
That opens a new, fairly specific experiment:

- cache outputs of lower local-attention segments for static windows
- recompute only dynamic windows through later full-attention blocks
- or let static windows skip query formation in full-attention layers and use summary memory instead

This is more realistic than full token relocation and better aligned with the model’s actual internals.

## 6. Revised workplan for an M3 MacBook Air (16GB)

## Phase 0 — hygiene and reproducibility

Objective: make the repo safe and runnable on the laptop.

Tasks:
1. Rotate/remove hardcoded HF token.
2. Fix hook cleanup with `try/finally`.
3. Fix `SpatialCascade` stale state bug.
4. Centralize frame extraction and classification utilities.
5. Replace absolute local paths with config/env-based paths.
6. Add a tiny regression test suite for:
   - token-grid shape alignment
   - cache substitution
   - hook cleanup
   - Q-table classification
   - MV extraction availability

Deliverable:
- stable research branch that can be repeatedly benchmarked without hidden corruption

## Phase 1 — reproduce the semantic result cheaply on the Mac

Objective: confirm the “LLM doesn’t care” result on hardware you actually have.

Recommended setup:
- MLX-VLM
- Qwen2.5-VL 3B or 7B 4-bit if memory allows comfortably
- 20-50 TOMATO questions first, then scale

Experiments:
1. Re-run the cached-vs-baseline semantic substitution on a small TOMATO subset.
2. Re-run with 8 frames and 4 frames.
3. Add failure logging with saved frame grids and token masks.
4. Run the Pareto refresh sweep.

Success criteria:
- near-perfect answer agreement
- similar reuse rates to prior runs

## Phase 2 — run the missing systems measurements

Objective: quantify where time is actually going.

Tasks:
1. Run `exp_wall_clock_speedup.py` after cleanup.
2. Add a second timing mode that excludes temp-file extraction overhead.
3. Separate timing into:
   - decode
   - preprocess
   - vision encode
   - classification
   - feature mixing
   - prefill
   - generation
4. Report both:
   - semantic substitution timing
   - realistic projected sparse execution timing

Success criteria:
- a trustworthy speed breakdown on the M3 Air
- an honest estimate of which component dominates at 4, 8, 16, 32 frames

## Phase 3 — decoder-side fast path experiments

Objective: reduce work before the model even sees frames.

Experiments:
1. Packet-size early exit:
   - implement `ALL_STATIC`, `SPARSE_DYNAMIC`, `FULL_DYNAMIC` frame routing based on frame type + pkt_size ratio
2. Gray-only decode baseline:
   - decode luma only and run selected tasks to see where quality breaks
3. Low-res baseline:
   - full video at 280px / 336px / 448px equivalent
4. Mixed-res baseline:
   - low-res full frame + high-res changed ROI crops
5. Dynamic frame scheduler:
   - keep I-frames + novelty peaks, drop trivial B/P frames

Success criteria:
- measurable TTFT reduction with minimal semantic change

## Phase 4 — changed-token-focused attention

Objective: turn dynamic masks into actual compute savings.

Experiments:
1. Simulated changed-query attention:
   - static tokens frozen, changed tokens attend globally
   - static tokens attend only locally or to summary tokens
2. Summary-bank attention:
   - static regions pooled into a small bank
   - dynamic tokens attend bank + local neighborhood
3. Layer-segmented Qwen experiment:
   - cache outputs before a full-attention layer
   - recompute only dynamic windows plus halo through later layers

Success criteria:
- large reduction in attention interactions
- minimal answer drift
- clearer path to a true runtime implementation

## Phase 5 — motion and stabilization for egomotion video

Objective: recover reuse on FPV/drone/mobile video without bad embedding relocation.

Experiments:
1. Global stabilization before tokenization:
   - ECC, ORB homography, or affine fit
2. Multi-reference cache:
   - compare same-position reuse from last frame vs stabilized reference vs previous I/P frame
3. Residual-gated reuse:
   - if stabilization error is low, reuse; otherwise refresh

Success criteria:
- FPV reuse improves materially beyond naive same-position caching
- answer stability stays high

## Phase 6 — task-aware color and screen-content policies

Objective: exploit codec/color structure where it actually matters.

Experiments:
1. Luma-only vs RGB vs chroma-refresh on color tasks
2. Screen-content dataset slice:
   - slides, code editors, UIs, dashboards
3. Palette/cardinality heuristic:
   - identify screen-like regions cheaply
4. OCR-aware ROI refinement

Success criteria:
- cheap paths for non-color tasks
- specialized path that does not destroy text/UI performance

## Phase 7 — optional lightweight model changes

Objective: get the next gain without losing the elegant training-free baseline.

Possible changes:
1. Tiny recache gate trained on hidden-state drift / disagreement labels
2. Codec-conditioned token-type embeddings
3. Dynamic/static token split module
4. Small policy head predicting refresh risk

Rule:
- train the *policy*, not the whole VLM, unless a later paper targets a fully learned delta encoder

## 7. Concrete experiment ranking

| Rank | Experiment | Why now | Expected payoff | Risk |
|---|---|---:|---:|---:|
| 1 | Wall-clock measurement on cleaned repo | Missing proof point | Very high | Low |
| 2 | Packet-size/frame-scheduler fast path | Cheap on M3 | High | Low |
| 3 | Changed-query attention simulation | Biggest conceptual next step | Very high | Medium |
| 4 | Global stabilization + same-position cache | Best FPV recovery path | High | Medium |
| 5 | Low-res + ROI refinement | Practical and easy | High | Low |
| 6 | Luma/chroma task-aware policy | New and likely useful | Medium-high | Low |
| 7 | Multi-reference/B-frame cache | Strong codec alignment | Medium-high | Medium |
| 8 | Screen-content specialization | Likely wins on UI/video | Medium-high | Medium |
| 9 | Layer-segmented caching inside Qwen | Most exciting model-aware path | Very high | High |
| 10 | Tiny learned recache gate | Good if heuristics plateau | Medium | Medium |

## 8. Questions we want the next round to answer

### Semantic questions
- When does cached output first diverge semantically, not just numerically?
- Are failure cases mostly color, OCR, small objects, or fast egomotion?
- Is answer agreement hiding calibrated uncertainty drift?

### Systems questions
- What fraction of total latency is still vision encode on 16GB Apple Silicon?
- How much of the real win comes from frame scheduling vs token reuse vs sparse attention?
- Is decode or temp-file I/O dominating any measured results?

### Modeling questions
- Can dynamic tokens attend broadly while static tokens remain memory without answer loss?
- Can Qwen’s window/full-attention structure be exploited explicitly?
- Does a tiny learned gate outperform fixed thresholds enough to justify the complexity?

### Codec questions
- Which codec/header signals best predict safe reuse rather than “importance”?
- Are B-frame and multi-reference semantics worth the added engineering?
- Does luma-first processing give a practical cheap path for non-color tasks?

## 9. Suggested implementation order for Codex / Claude

1. **Clean the repo first**
   - remove secret
   - fix hooks
   - fix stale state
   - unify utilities

2. **Create two explicit APIs**
   - `semantic_substitution_runner`
   - `sparse_execution_runner`

3. **Run three baseline experiments on the M3 Air**
   - TOMATO subset semantic agreement
   - wall-clock breakdown
   - packet-size early exit

4. **Add one new science branch at a time**
   - changed-query attention simulation
   - stabilization + multi-reference cache
   - luma/chroma task-aware policy

5. **Do not spend time on these until later**
   - embedding relocation
   - DCT-as-compression multiplier
   - continuous bit-allocation scoring
   - generic codec saliency replacement for final attention

## 10. My updated scientific position

After reading the actual repository, my view is stronger and more specific:

- the core temporal result is real
- the codebase already did unusually good negative-result science
- the next best idea is **not** richer codec saliency scoring
- the next best idea is **dynamic working-set inference**:
  - static tokens become memory
  - changed tokens get compute
  - frame scheduling removes trivial frames
  - stabilization recovers reuse under camera motion
  - color/resolution are made task-aware

In one sentence:

> The right follow-up is to turn Codec-Through from “output feature reuse” into a full **codec-conditioned dynamic compute policy** for video VLMs.

## 11. Further work beyond video

### Robotics
The best transfer is probably mobile or manipulator VLA with protected ROIs:
- always refresh gripper / contact / target object / goal receptacle
- stabilize background or use egomotion
- cache the rest aggressively

### Audio
The analogous direction is not “low energy = safe reuse.”
It is:
- onset/boundary/prosody-aware reuse
- static acoustic background memory
- dynamic speech/event working set

### Video generation / world models
The analogous form is:
- cache latent hidden states for low-change regions across denoising or autoregressive steps
- refresh only high-uncertainty or high-motion regions
- use delta tokens instead of dense full-frame latent updates

