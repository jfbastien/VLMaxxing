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
- a follow-up temporal-necessity ablation shows that some other apparent v2
  passes are contaminated by prompt structure or endpoint solvability, so the
  current local synthetic result should be read through the smaller
  discrimination-safe subset
- direct repeated-image feature identity is reproduced locally, but the stronger
  locality and shift-strength claims are still only partial on the current
  controlled probes
- benchmark-native local evidence now splits:
  - TOMATO `30`-item subset: dense `0.300`, cached `0.233`, agreement `0.833`
  - MVBench hosted `54`-item subset: dense `0.630`, cached `0.648`, agreement
    `0.870`
- first-frame ablations sharpen that split:
  - TOMATO falls to `0.067` on frame `0` alone
  - MVBench only falls to `0.519` on frame `0` alone
  - the current contrast therefore looks content-conditioned before it looks
    parser-conditioned
- targeted TOMATO `direction` refresh sweeps now show a concrete repair path:
  - no refresh gives cached `0.2` and agreement `0.6`
  - refresh every `4` frames recovers exact dense agreement on the same
    five-item subset while keeping active reuse at `0.732`
- local strict and loose parser rescoring are identical on those saved slices
  because parse failures stayed at `0`, so the current local disagreement is
  not a local parser artifact
- imported `100%` benchmark agreement is therefore not the right paper-facing
  baseline by itself:
  this repo should compare against both the imported whitepaper and the
  broader efficiency literature, then explain where the current method is still
  weaker

## Current Anti-Claims

We are not yet claiming:

- real sparse execution wins from the current Track A path
- state-of-the-art benchmark accuracy or efficiency
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
- FastV and ToMe show that competitive efficiency papers need both meaningful
  compute reduction and small quality loss, not just a semantic proxy result

What this repo is trying to show:

- how far a training-free reuse path can go before architecture changes
- how to separate answer-stability evidence from true skipped compute
- which cheap routing signals are useful before we pay for deeper model changes

What the current evidence says about competitiveness:

- the project now has a credible reproduction substrate and benchmark-native
  Track A evidence
- it does not yet have a competitive method-paper position against the current
  efficiency literature because Track B evidence is still missing and the
  current agreement range (`0.833` to `0.870`) is weaker than the small-drop
  quality narratives reported by stronger systems and token-pruning papers
- the way toward a stronger paper is therefore:
  - finish the whitepaper reproduction controls honestly
  - diagnose the TOMATO and MVBench gap causally
  - use that diagnosis to design a better training-free planner before claiming
    SOTA relevance

## Likely Contribution Stack

Near-term strong paper path:

- honest reproduction of the whitepaper controls and benchmark lane on Apple
  Silicon
- benchmark-native diagnosis of where same-position reuse fails and why
- a stronger training-free planner that materially improves the current TOMATO
  and MVBench range
- careful Track B timing only after sparse execution exists

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
