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

## Model and Runtime Stack

### Qwen2.5-VL

Source:

- <https://huggingface.co/docs/transformers/en/model_doc/qwen2_5_vl>

Why it matters:

- relevant open multimodal target family
- likely the cleanest first comparison point against the seed whitepaper

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
- already exposes vision feature caching and TurboQuant KV settings

### Gemma Model Family

Source:

- <https://ai.google.dev/gemma/docs/get_started>

Why it matters:

- official Google guidance for which Gemma variant maps to which hardware tier
- useful when choosing a laptop-appropriate baseline

Current working takeaway:

- Gemma 4 E4B is the most interesting local Gemma target for this machine class
- Gemma 4 31B is a context reference, not the day-one local model

## Codec and Tooling References

### FFmpeg `export_mvs`

Source:

- <https://www.ffmpeg.org/ffmpeg-codecs.html>

Why it matters:

- confirms that motion vectors can be exported as frame side data for codecs that support it

### FFmpeg `codecview`

Source:

- <https://ffmpeg.org/ffmpeg-filters.html>

Why it matters:

- useful for visual inspection and debugging of motion-vector extraction

## What We Still Need To Add

- stronger coverage of screen-content-specific video coding ideas
- stronger coverage of adaptive partitioning and transform-domain ideas
- one or two robotics references that are directly about caching or reuse rather than generic VLA efficiency
- one or two audio references if we decide to expand beyond video
