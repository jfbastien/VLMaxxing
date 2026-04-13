# Knowledge Base Notes

Scope:

- reviewed `~/s/codec-through-sam/fleet-kb/`
- treated it as prioritization input, not authoritative evidence

## Trust Model

What the KB is good for:

- surfacing repeated negative results
- showing where the earlier project spent time already
- highlighting sequencing constraints that are easy to miss from the scripts alone

What the KB is not good for:

- replacing raw result artifacts
- serving as a citation graph
- justifying exact numeric claims on its own

Highest-value entries are the ones that point back to concrete imported artifacts or primary papers.

## Useful Takeaways To Carry Forward

### 1. Preserve the relocation kill signal

Useful KB direction:

- relocation is not where the next gain is

Why it survives audit:

- it matches imported relocation result artifacts

Planning effect:

- keep same-position reuse as the temporal baseline
- move egomotion work toward stabilization and multi-reference caches instead

### 2. Treat Q-table as pre-filter only

Useful KB direction:

- Q-table flatness is useful as a binary pre-filter
- it should not be promoted to a general-purpose spatial importance ranker

Why it survives audit:

- it matches imported Q-table and attention references

Planning effect:

- keep Q-table work in task-aware spatial-policy phases
- do not let it become the main spatial-scoring story

### 3. Kill continuous H.264 spatial scoring early

Useful KB direction:

- direct H.264 spatial gradients are weak as a main saliency path

Why it survives audit:

- it is directionally consistent with imported attention and H.264 signal results

Planning effect:

- do not spend early milestones on exact per-MB bit counting or fine-grained bitrate saliency maps

### 4. Use cheap temporal metadata first

Useful KB direction:

- simple metadata paths often dominate more elaborate coefficient parsing

Why it matters:

- it aligns with the original repo's packet-size and frame-header routing ideas

Planning effect:

- prioritize frame type, keyframe position, packet size, and skip-like routing early

### 5. Respect architecture-specific merge points

Useful KB direction:

- Qwen-like models need direct checkpoint validation
- early pruning assumptions do not automatically transfer

Why it survives audit:

- it matches imported attention results and the sawtooth full-attention pattern

Planning effect:

- sparse visual execution work must be model-specific
- late checkpoints matter more than generic early-prune folklore

### 6. Keep stackup claims conservative

Useful KB direction:

- multiplicative compression narratives become misleading quickly

Why it matters:

- the seed material contains tempting arithmetic that is not yet measured end-to-end

Planning effect:

- report component-wise evidence first
- compose wins only after each component is independently measured

### 7. Deprioritize DCT-bypass and alignment-heavy shortcuts

Useful KB direction:

- DCT-domain shortcut ideas look much weaker once patch alignment, actual FLOPs, and model-specific tokenization are checked

Planning effect:

- keep DCT-bypass out of the early milestone list
- verify patch and merge geometry directly from model configs before making any alignment-dependent claim

## What We Intentionally Did Not Promote

- DCT-bypass numeric claims as settled fact
- provenance-aware KV allocation as a core milestone
- exact patch-alignment claims for Gemma-like paths without direct config checks
- mission-file proposals that lack raw artifacts

## Consequences For Review

When other agents review this repo, ask them specifically:

- are we still giving too much weight to synthesized KB conclusions?
- are any "killed" claims actually only "weakened"?
- are we enforcing model-specific sparse-execution validation strongly enough?
