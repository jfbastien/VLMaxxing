# Paper Narrative Rules

This file captures editorial rules learned during the manuscript/review loop.
It exists so future paper edits do not re-litigate the same framing choices.

## The Spine

The paper is about **training-free anti-recomputation for video VLMs**.

The central variable is not "how many frames can we drop?" It is:

> Where must the runtime buy fresh visual evidence over time, and where is
> cached state enough for the relevant quality--compute frontier?

Everything should hang off that.

## Claim Order

Order the story by reader impact, while keeping denominators visible:

1. **C-PERSIST / after-ingest follow-up reuse** is the big-number regime.
   Lead with it when the goal is attention, but say "after-ingest" and
   "same-video follow-up" near every large multiplier.
2. **C-CEILING / stage-share accounting** is the guardrail that keeps the
   paper serious. It explains why first-pass speedups are smaller and why
   composition does not multiply.
3. **C-VISION / first-pass vision pruning** is the fresh-video speedup claim.
   It is real, measured, and share-limited.
4. **Qwen routing** explains temporal placement and failure boundaries. It is
   mechanism evidence under a dense backend until measured sparse execution
   lands.
5. **Scale-out streaming** should become a first-class lane only when matched
   artifacts and baselines exist. Until then, frame it as scale-out
   operational evidence pending artifact harmonization, not as "other" work.

## Do Not Multiply The Headlines

Never imply that 91x follow-up reuse, first-pass pruning, and streaming
counters multiply into one end-to-end speedup. The paper's credibility comes
from refusing that story.

Correct sentence shape:

> These are separate regimes with separate denominators.

Wrong sentence shape:

> Combining these techniques yields X times total speedup.

## How To Talk About Sam's 26B Lane

Do not make Sam's work sound like an anecdote. It is the **scale-out streaming
lane**.

Current wording:

- "scale-out operational evidence"
- "pending artifact harmonization"
- "different model, machine, runtime, and streaming protocol"

Promotion requirements:

- cache-correctness smoke test
- exact model/runtime/hardware provenance
- raw paired outputs with item IDs
- C-PERSIST same-video follow-up replication
- measured sparse-ViT / C-CEILING validation
- screenshot-polling, low-FPS dense, and recency baselines
- stale-cache failure case
- re-export of large exactness artifacts with parse failures and confidence
  intervals

## Paired Drift

The paper's paired-drift discipline is a contribution. Aggregate accuracy is
not enough.

Use:

- paired choice drift
- paired correctness drift
- parse failures
- degenerate/pathological outputs
- finite-sample confidence bounds

Avoid:

- "safe" unless the finite criterion is named
- "exact" unless it is byte/logit/row identity
- "sampler-invariant" for one warmer-sampler point

Open experiment: run a many-turn follow-up horizon sweep. Current C-PERSIST
sessions contain two follow-ups. We do not know whether 10, 20, or 50
follow-ups gradually accumulate drift, or which repair schedule prevents it.

## Results That Need Mechanistic Explanations

Do not leave readers with "huh, why?"

- Adaptive beats fixed \(K=1\) because Q3 inherits the post-Q2 repaired
  cache and re-prefills mostly question text, while fixed \(K=1\) pays the
  newest-frame tail again. Existing stage timing shows paired median Q3
  fixed/adaptive speedup 9.50x and 88.9% tail-token reduction.
- 1.30AC and 1.30AD reach the same aggregate loss through different row sets.
  Current evidence supports an aggregate boundary, not identical failures.
  If feature concentration is not enough, run the K-cache distance probe.
- Track B, when it lands, should be framed as ceiling-model validation for
  measured ViT-only skipped work, not as a huge end-to-end speedup.

## Training Claim Boundary

The current paper is inference-only and training-free.

Permitted training implication:

> The traces show where frozen models already tolerate reuse and can supervise
> learned refresh gates, delta encoders, codec-conditioned tokens, or
> cache-state-aware attention.

Not permitted yet:

> This method directly reduces VLM training compute.

Reason: cached post-ViT features do not preserve the gradient path when the
vision encoder is trainable. A training-speedup claim needs a model-native
delta/sidecar training experiment.

## Voice

The title and opening can be playful. The evidence accounting must be severe.

The desired reader reaction is:

> This is fun, but the science is stricter than most serious papers.

Humor is allowed when it clarifies the model or creates momentum. Cut any joke
that makes a denominator, evidence class, or failure boundary less clear.
