# Literature Map

This file tracks the external sources that currently shape the plan.

The rule here is simple:

- use primary sources
- say what each source is actually useful for
- do not inflate a paper beyond what it directly supports

## Benchmarks

### TOMATO

Source:

- <https://arxiv.org/abs/2410.23266>

Why it matters:

- explicitly targets visual temporal reasoning
- reports 1,484 human-annotated questions across six temporal tasks
- is a better fit for this project than generic video QA agreement alone

What it does not tell us:

- whether a reuse method saves real wall-clock time

### MVBench

Source:

- <https://arxiv.org/abs/2311.17005>

Why it matters:

- broad multi-task video understanding benchmark
- good for checking whether a reuse mechanism breaks general video reasoning

What it does not tell us:

- whether failures are specifically temporal-reuse failures rather than generic model weaknesses

## Closest Efficiency Work

### CoPE-VideoLM

Source:

- <https://arxiv.org/abs/2602.13191>

Why it matters:

- directly uses codec primitives such as motion vectors and residuals
- shows that codec-native representations can reduce token usage and TTFT materially

How it differs from the whitepaper direction:

- it trains lightweight codec encoders
- it is not the same as zero-training embedding reuse

### CodecSight

Source:

- <https://arxiv.org/abs/2604.06036>

Why it matters:

- very close to the serving/systems problem we care about
- uses codec metadata to drive patch pruning before ViT encoding and selective KV refresh during prefilling
- directly supports the claim that codec metadata can be a low-cost runtime signal

Important note:

- this is the verified paper name and URL
- some seed material referred to adjacent ideas imprecisely; this file uses the verified title

## Spatial And Token Efficiency References

### ToMe

Source:

- <https://arxiv.org/abs/2210.09461>

Why it matters:

- strong spatial/token-merging prior for ViTs
- useful baseline when discussing merge-style efficiency ideas

What it does not tell us:

- whether temporal same-position reuse is safe
- whether codec-side routing helps before image tokenization

### FastV

Source:

- <https://arxiv.org/abs/2403.06764>

Why it matters:

- direct reminder that aggressive visual-token pruning claims are architecture-sensitive
- useful caution when thinking about Qwen-style hybrids with sparse or late checkpoints

### PixelPrune

Source:

- <https://arxiv.org/abs/2604.00886>

Why it matters:

- strong newer evidence that document or GUI-like imagery can be unusually redundant before dense visual encoding
- supports keeping screen-content specialization in scope

What it does not tell us:

- it is not evidence for general natural-video redundancy
- it is not evidence for codec-motion routing or temporal reuse in natural scenes

## Recent Visual-Token Pruning Competitors (2025–2026)

This section tracks the 2025-2026 visual-token-pruning papers that
set the current SOTA reference points for claim #11 (novelty-pruning
delivers end-to-end speedup on Gemma) and claim #10 (composition with
within-frame methods). These are the methods we must beat — or
explicitly bound against — to have a defensible SOTA story.

### FlashVID

Source:

- OpenReview ICLR 2026 Oral (paper ID `H6rDX4w6Al`), canonical arxiv
  listing <https://arxiv.org/abs/2602.08024>

Why it matters:

- directly comparable training-free visual-token-pruning method for
  video VLMs; reported 99.1% accuracy at 10% retention with 6.3×
  prefill speedup on reference benchmarks
- this is the closest 2026-era SOTA we must argue against on claim #11

How it differs from 1.51R:

- uses attention/diversity token selection plus tree-based spatiotemporal
  token merging inside a VLM token pipeline, not a zero-training
  pixel-novelty + anchor rule
- reports prefill and TTFT speedups rather than our strict end-to-end
  wall-clock denominator, so its 6.3× prefill figure should not be compared
  directly with our full-query E2E numbers

### FastVID

Source:

- OpenReview NeurIPS 2025 (paper ID `2xS4VtpApy`)

Why it matters:

- 98.0% accuracy at 7.1× prefill speedup on video QA benchmarks
- training-free, architecture-general token pruning for video VLMs
- second closest 2026-era SOTA point

How it differs from 1.51R:

- same caveat as FlashVID: measured in prefill speedup, not end-to-end
- does not explicitly address the arithmetic-ceiling question (how
  much of e2e is fixed cost D+V) that our task #88 analysis makes
  central

### FasterVLM

Source:

- <https://arxiv.org/abs/2412.01818>

Why it matters:

- earlier (late-2024) training-free visual-token pruning baseline
- useful floor reference; its measured speedups are lower than
  FlashVID/FastVID, which lets us stratify the competitor landscape

### EvoPrune

Source:

- <https://arxiv.org/abs/2603.03681>

Why it matters:

- 2026 evolutionary token-pruning method; provides another
  contemporary data point for the "how much can training-free
  pruning buy?" question
- differs from 1.51R by using an evolutionary search over prune
  masks instead of a single-pass novelty + anchor computation

## Compressed-Video Lineage

### CoViAR

Source:

- <https://openaccess.thecvf.com/content_cvpr_2018/html/Wu_Compressed_Video_Action_CVPR_2018_paper.html>

Why it matters:

- classic compressed-video ML baseline that works from I-frames, motion vectors,
  and residuals
- useful when explaining that codec-aware video ML is not new, but our runtime
  operating point is different

### DMC-Net

Source:

- <https://openaccess.thecvf.com/content_CVPR_2019/html/Shou_DMC-Net_Generating_Discriminative_Motion_Cues_for_Fast_Compressed_Video_Action_CVPR_2019_paper.html>

Why it matters:

- explicit reminder that raw motion vectors are useful but noisy
- helpful precedent for treating codec signals as valuable machine inputs without
  assuming they are perfect semantic saliency signals

## Model and Runtime Stack

### Qwen2.5-VL

Source:

- <https://huggingface.co/docs/transformers/en/model_doc/qwen2_5_vl>

Why it matters:

- relevant open multimodal target family
- likely the cleanest first comparison point against the seed whitepaper
- official docs expose video support and image or video feature APIs

### MLX

Source:

- <https://mlx-framework.org/>

Why it matters:

- Apple-first array and model runtime
- designed for Apple silicon and unified memory

### MLX-VLM

Source:

- <https://github.com/Blaizzy/mlx-vlm>

Why it matters:

- practical local inference stack for VLMs on Mac
- explicitly supports vision-language and omni models
- includes video support for selected models
- official README documents vision feature caching and TurboQuant KV-cache options

Important caution:

- runtime support for these knobs does not count as local proof that they are
  quality-neutral or composable in our stack

### Gemma Model Family

Source:

- <https://ai.google.dev/gemma/docs/get_started>
- <https://huggingface.co/docs/transformers/model_doc/gemma4>
- <https://huggingface.co/google/gemma-4-E4B>

Why it matters:

- official Google guidance for which Gemma variant maps to which hardware tier
- useful when choosing a laptop-appropriate baseline

Current working takeaway:

- Gemma 4 E4B is the most interesting local Gemma target for this machine class
- Gemma 4 31B is a context reference, not the day-one local model
- Gemma 4 uses a configurable visual token budget with official supported values
  `70`, `140`, `280`, `560`, and `1120`
- the repo's `Qwen -> Gemma -> Qwen-7B` model order is a local research choice,
  not an official recommendation

## Temporal Redundancy And Dynamic Compute

### Eventful Transformers

Source:

- <https://openaccess.thecvf.com/content/ICCV2023/html/Dutson_Eventful_Transformers_Leveraging_Temporal_Redundancy_in_Vision_Transformers_ICCV_2023_paper.html>

Why it matters:

- closest non-codec temporal-redundancy reference for reprocessing only changed
  tokens across time
- especially relevant if Track B becomes changed-window execution and later
  changed-query attention

### FitPrune

Source:

- <https://arxiv.org/abs/2409.10197>

Why it matters:

- training-free visual-token pruning reference for MLLMs
- useful adjacent comparison when discussing efficiency work that avoids
  retraining

What it does not tell us:

- it is not codec-specific
- it is not itself a temporal-reuse result

## Codec and Tooling References

### FFmpeg `export_mvs`

Sources:

- `export_mvs` / `AV_FRAME_DATA_MOTION_VECTORS` side data:
  <https://ffmpeg.org/ffmpeg-codecs.html>
- `codecview` visualization of exported motion vectors:
  <https://ffmpeg.org/ffmpeg-filters.html>

Why it matters:

- confirms that motion vectors can be exported as frame side data for codecs that support it

### FFmpeg `codecview`

Source:

- <https://ffmpeg.org/ffmpeg-filters.html>

Why it matters:

- useful for visual inspection and debugging of motion-vector extraction

## Test Media And Dataset Provenance

### Xiph Test Media

Source:

- <https://media.xiph.org/>
- <https://media.xiph.org/video/derf/>

Why it matters:

- practical stable source for small local bring-up clips
- useful for low-motion and moderate-motion proxy content without relying on transient video-hosting platforms

### UVG Dataset

Source:

- <https://researchportal.tuni.fi/fi/publications/uvg-dataset-50120fps-4k-sequences-for-video-codec-analysis-and-de>

Why it matters:

- strong later-stage source for reproducible 4K codec experiments
- useful when the project graduates from tiny bring-up clips to higher-resolution systems work

### EPIC-KITCHENS

Source:

- <https://epic-kitchens.github.io/2022.html>

Why it matters:

- explicit egocentric dataset option for later mobile or FPV-style evaluation
- non-commercial license means it should be kept separate from the initial lightweight public corpus

## Machine-Oriented Media Standards

### MPEG VCM

Source:

- <https://www.mpeg.org/standards/MPEG-AI/2/>

Why it matters:

- official sign that machine-oriented video coding is a real standards direction
- supports the long-term sidecar or machine-first framing without implying that our repo already implements it

### MPEG FCM

Source:

- <https://www.mpeg.org/standards/MPEG-AI/4/>

Why it matters:

- feature compression is directly relevant if later work moves from pixels to intermediate representations

### JPEG AI

Source:

- <https://jpeg.org/jpegai/>

Why it matters:

- useful reference for machine-aware image compression and text/graphics handling
- supports the screen-content and machine-consumption discussion

## Screen-Content And Codec Design Hints

### AV1 Tooling Overview

Source:

- <https://aomedia.org/docs/aomenc-command-line-parameters-draft.pdf>

Why it matters:

- documents screen-content and global-motion tools such as `intrabc`
- useful when framing why natural video and screen video should not share one policy blindly

## What We Still Need To Add

- one or two robotics references that are directly about caching or reuse rather than generic VLA efficiency
- one or two audio references if we decide to expand beyond video
