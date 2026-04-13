# Paper Framing

This file tracks the paper story, contribution boundary, and anti-claims.

It is not the place for raw experimental detail.

## Current Narrow Claim

Training-free temporal feature reuse appears much more semantically safe than
many video-VLM pipelines assume.

That is the claim the imported evidence supports today.

## Current Anti-Claims

We are not yet claiming:

- real sparse execution wins from the current Track A path
- state-of-the-art benchmark accuracy
- end-to-end gains from stacked compression arithmetic
- robotics inner-loop safety or real-time guarantees
- AI-native codecs as a near-term deliverable

## Why This Project Matters

The systems-engineering thesis is straightforward:

- modern codecs already expose cheap signals about novelty, motion, and reference structure
- current VLM pipelines often ignore those signals and pay dense compute anyway
- part of the opportunity is not inventing new model internals first, but recovering cross-layer wins that existing systems left on the table

Another framing that may survive into the paper:

- classical codecs are hand-designed predictive programs shaped by hardware constraints and perceptual objectives
- machine-consumption pipelines may want to reuse some of those ideas, but not inherit the human-vision objective blindly

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

- changed-query attention
- compute-denial or novelty-amplification robustness evaluation
- multi-reference and IMU-assisted stabilization
- machine-oriented codec sidecars
- sensor-fusion timelines or world-state codecs
- AI-native codecs and hardware co-design

## Writing Discipline

- every paper claim should link back to local evidence or a primary source
- future-work sections should say why a direction follows from observed evidence, not just why it sounds interesting
- negative results belong in the paper story when they narrow the design space in a useful way
