# Paper Terminology

This file is an editor-facing dictionary for the manuscript. It is not a
paper glossary unless a future venue pass decides to promote part of it.

The rule is simple: use descriptive names first, short labels second. The
title can have the fun; technical terms should help readers stay oriented.

## Core Terms

| Term | Meaning | Paper-facing guidance |
| --- | --- | --- |
| anti-recomputation | Avoiding repeated visual or prefix computation when the video state has already been encoded and can be reused under a checked fidelity contract. | Use this as the umbrella term. |
| VLM | Vision-language model: a model that consumes visual inputs and text prompts to produce text answers. | Define once in the abstract or introduction. |
| vision tower | The visual encoder inside a VLM that turns image or video frames into visual tokens before the language model consumes them. | Use freely after first definition. |
| Qwen | The Qwen2.5-VL family used for local routing and persistent-cache experiments. | First use should name the tested variant, usually `Qwen2.5-VL-7B-Instruct-4bit`. |
| Gemma | The Gemma video-VLM family used for most first-pass vision-pruning measurements and for pending scale-out discussion. | First use should name the exact model/precision when claim-bearing. |
| first-pass | The first query on a fresh video, before the visual prefix has been cached. | Prefer over "fresh-video" when talking about query protocol. |
| after-ingest | Later questions about the same video after the first query has already paid visual/prefix cost. | Use whenever reporting the large follow-up speedups. |
| persistent KV | Reusing cached key/value attention state from an already-ingested prompt/video prefix. | Pair with "after-ingest" so readers do not mistake it for first-pass speedup. |
| paired drift | Per-example disagreement between matched baseline and reuse runs. We split it into choice drift and correctness drift. | Say "no observed paired drift" rather than "safe" or "exact" unless the criterion is formalized. |
| same-class speedup | Speedup comparing the same query class, usually cold follow-up latency divided by repaired/session follow-up latency. | Define near any table that mixes all-query and follow-up denominators. |
| all-query speedup | Speedup comparing all cold queries with session execution under the artifact's convention. | Do not mix with same-class speedup without naming the denominator. |
| cache basin | A reuse-failure region where cached state drives repeated answer drift or pathological outputs instead of ordinary independent mistakes. | Evocative and useful; define before using in the abstract/results. |
| selective re-prefill | Refreshing a small newest-frame visual tail while reusing the older prompt/cache state. | The repair mechanism for C-PERSIST. |
| semantic substitution | Replacing/replaying cached visual features to test answer preservation under a dense backend. | Explicitly not a measured sparse-execution speedup. |
| measured sparse execution | A backend path that actually skips timed work in decode, vision, prefill, or generation. | Paper-facing replacement for "Track B". |
| quality--compute frontier | Tradeoff curve between answer quality and compute/latency/fresh visual budget. | Use per regime, never as a universal curve. |

## Contribution Labels

The `C-*` labels are useful handles, but they read like internal project names
unless expanded. First use should follow this pattern:

- **stage-share ceiling (C-CEILING)**: a component speedup affects
  end-to-end latency only in proportion to that component's dense wall-clock
  share.
- **persistent follow-up reuse (C-PERSIST)**: later questions about the same
  video reuse already-paid prompt/KV state and are judged by follow-up latency
  plus paired drift.
- **first-pass vision pruning (C-VISION)**: training-free pruning inside the
  VLM vision tower during the first query on a fresh video.
- **streaming state reuse (candidate C-STREAM)**: online/native-rate reuse of
  repeated visual state in a streaming or live deployment. Do not make this a
  fourth headline contribution until the scale-out lane has matched
  artifacts, cache-correctness smoke tests, and baselines.

## Terms To Avoid In Main Text

| Avoid | Use instead | Reason |
| --- | --- | --- |
| Track A | semantic-substitution routing | Internal project label. |
| Track B | measured sparse execution | Internal project label; only okay in TODOs or repo docs. |
| Lane A / Lane B | routing evidence / scale-out lane | Internal project label. |
| safe | no observed paired drift, within tested criterion, certified for this finite envelope | "Safe" implies more than the experiments prove. |
| exact | no observed paired drift, identity-preserved on these rows | "Exact" should mean byte/logit identity, not only answer identity. |
| pooled n=60 | n=60 composition audit | "Pooled" asks readers to infer what was pooled. |
| imported deployment-scale evidence | scale-out operational evidence, pending artifact harmonization | Keeps Sam's lane first-class without overclaiming. |

## Fun Budget

`FrameMogging` is safe as a title nickname for frame-level
anti-recomputation. Do not use it as a technical term in the body unless the
sentence immediately gives the sober translation.

Final Fantasy or RPG slang belongs in internal notes, talks, or secondary
channel artifacts, not as core manuscript terminology. The paper gets its
delight from the title, the wall hook, the "do not multiply the headlines"
discipline, and the scale of the follow-up numbers. The body should be strict
enough that the title reads intentional.

## Visual Vocabulary

The best overview figure should be a frame-volume diagram:

1. Frames stack along a time/depth axis.
2. Static background regions stay translucent and cached.
3. Motion/residual regions light up as fresh-evidence purchases.
4. Three horizontal rails show first-pass vision pruning, after-ingest
   follow-up reuse, and streaming state reuse.
5. A side meter shows C-CEILING: only the stage share touched by the mechanism
   can move end-to-end wall-clock.

This gives AI-curious readers the memory-palace version of the paper while
giving experts the denominator and protocol boundaries in the same visual.
