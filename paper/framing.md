# Paper Framing

This file tracks the paper story, contribution boundary, and anti-claims.

It is not the place for raw experimental detail.

## Current Narrow Claim

Training-free temporal feature reuse appears much more semantically safe than
many video-VLM pipelines assume.

That is the claim the imported evidence supports today.

The current local evidence now adds two useful controls:

- dense baselines and dense-through-cache identity are locally reproduced on the Apple-Silicon MLX-VLM path
- an initial `12`-item synthetic Qwen pilot yielded dense-versus-cached agreement
  of `1.0` under default same-position reuse, while the dense baseline itself
  still missed two event-centric prompts
- that pilot is still substrate evidence rather than a whitepaper-quality
  reproduction because it does not yet include divergence-capable items or
  scored natural video
- a repaired synthetic v2 suite now includes a controlled failure: default
  same-position reuse misses one middle-dependent OCR flash that dense answers
  correctly

## Current Anti-Claims

We are not yet claiming:

- real sparse execution wins from the current Track A path
- state-of-the-art benchmark accuracy
- end-to-end gains from stacked compression arithmetic
- robotics inner-loop safety or real-time guarantees
- AI-native codecs as a near-term deliverable

## Why This Project Matters

Candidate line worth keeping:

> The codec already knows what changed. Stop re-encoding what didn't.

The systems-engineering thesis is straightforward:

- modern codecs already expose cheap signals about novelty, motion, and reference structure
- current VLM pipelines often ignore those signals and pay dense compute anyway
- part of the opportunity is not inventing new model internals first, but recovering cross-layer wins that existing systems left on the table

Another framing that may survive into the paper:

- classical codecs are hand-designed predictive programs shaped by hardware constraints and perceptual objectives
- machine-consumption pipelines may want to reuse some of those ideas, but not inherit the human-vision objective blindly

## Comparison Boundary

What adjacent work already shows:

- CoPE-VideoLM shows that trained codec-native representations can materially reduce tokens and TTFT
- CodecSight shows that codec metadata can drive pre-ViT pruning and selective KV refresh in a serving-oriented pipeline

What this repo is trying to show:

- how far a training-free reuse path can go before architecture changes
- how to separate answer-stability evidence from true skipped compute
- which cheap routing signals are useful before we pay for deeper model changes

## Likely Contribution Stack

Near-term paper:

- honest separation of semantic substitution from sparse execution
- local reproduction of answer-stability claims on Apple Silicon
- careful measurement of where latency actually goes
- decoder-side routing and scheduling baselines

Follow-on systems paper if evidence lands:

- changed-window sparse execution
- task-aware media policies
- screen-content specialization

## Future Horizons To Track Carefully

These are worth discussing, but should stay clearly labeled as future work until
local evidence exists:

Closest to current evidence:

- compute-denial or novelty-amplification robustness evaluation
- multi-reference and IMU-assisted stabilization
- changed-query attention after changed-window execution

Medium-distance:

- machine-oriented codec sidecars
- screen-content specialization as a major branch

Far-distance:

- sensor-fusion timelines or world-state codecs
- AI-native codecs and hardware co-design

## Proxy Chain To State Explicitly

The current training-free planner is a proxy chain:

- pixel-space RGB differencing is standing in for decoded-frame change
- current `STATIC / SHIFTED / NOVEL` planner labels are therefore proxy labels
  under RGB differencing, not literal codec-motion truth
- decoded-frame change is standing in for codec-side motion and residual semantics
- codec-side motion and residual semantics are standing in for latent-feature reuse decisions

That chain is useful, but reviewers should not mistake it for direct compressed-domain execution.

## Writing Discipline

- every paper claim should link back to local evidence or a primary source
- future-work sections should say why a direction follows from observed evidence, not just why it sounds interesting
- negative results belong in the paper story when they narrow the design space in a useful way
