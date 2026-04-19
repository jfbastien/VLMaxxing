# Phase 1.57 — Feature-drift mechanism study (PREREG)

**Status:** preregistration, 2026-04-19. Promoted from planning
pointer in `2026-04-19-codex-round-21-sam-imports.md` to real
prereg following external review (2026-04-19 Codex round-22).

## What changed in scope

Earlier drafts framed 1.57 as "attention-entropy logging." External
review flagged that this is the wrong proxy.

Sam's current research queue (`~/s/codec-through-sam/research_queue.md`
lines 14-29) documents that the dominant cache-miss phenomenon on
Gemma 4 is **attention-propagation drift in STATIC tokens**,
observed directly in per-class feature-space cosine between cache-
substituted and fresh-encoded frames:

- NOVEL tokens: cos = 1.000 (trivially — we replaced them fresh)
- **STATIC tokens: cos = 0.67–0.80** ← the actual drift lives here
- SHIFTED tokens: cos = 0.58–0.95 (small sample, high variance)

The tokens classified "unchanged" have outputs that drift
~20–30% in cosine from fresh because ViT global self-attention
mixes in NOVEL neighbors' changed content. This is architectural.
The paper's 90% byte-identity on Gemma 4 survives not because the
cache is accurate but because the LLM is robust to feature drift.

Attention-entropy is a second-order proxy (if drift makes attention
diffuse, entropy rises). Feature-space cosine is the **direct**
measurement of the same phenomenon. 1.57 therefore re-scopes to
feature-drift-first, with attention-entropy as a supplementary lens
only if the cosine story is ambiguous.

## Motivation (why this is load-bearing)

1.57 is what distinguishes our 1.51R result ("Gemma kr=0.10
preserves accuracy within -10pp confidence") from the mechanism
claim "caching works because cache features match fresh features."
If STATIC-token cosine is 0.67-0.80 on Gemma but 0.95+ on Qwen,
that fully explains:

- why Qwen is bit-faithful under identity cache (cos ≈ 1.0 →
  LLM sees the same features) — already observed across 8f/16f/32f
- why Gemma is approximate under identity cache — the LLM sees
  drifted features but is robust enough to produce accurate answers
- why our novelty-pruning is a different lever than Sam's —
  pruning STATIC tokens is safe *because* they are already drifted
  and contribute less useful information than a cache-substitute
  framing suggests

This mechanism explanation is exactly what a main-submission
paper needs to convert "partial reproduction" into a coherent
scientific story.

## Hypotheses

### H1 (drift-by-class stratification on Gemma)

Per-token cosine between cache-substituted features and fresh
ViT encode, stratified by STATIC / SHIFTED / NOVEL class:

- STATIC mean cos ∈ [0.60, 0.85] on VideoMME dev n=10 long-bucket
  items (reproducing Sam's finding in our env).
- NOVEL mean cos = 1.000 ± 0.001 (trivially — we re-encoded them
  fresh; anything else is a bug).
- SHIFTED mean cos ∈ [0.50, 0.99] (wide band; Sam reports high
  variance).

**Falsification:** STATIC cos > 0.90 or < 0.50 → our
instrumentation disagrees with Sam's direction; investigate
bit-level config before treating the number as meaningful.

### H2 (drift-by-class stratification on Qwen)

Same measurement on Qwen 2.5-VL-7B-Instruct-4bit:

- STATIC mean cos ∈ [0.95, 1.000] — consistent with identity-
  cache being bit-faithful on Qwen across all prior frame-count
  runs.

**Falsification:** STATIC cos < 0.90 → identity-cache bit-
faithfulness result is mysterious; we haven't measured what we
thought we measured.

### H3 (drift compounds with frame count)

On Gemma, STATIC mean cos **decreases monotonically** as frame
count increases 8f → 16f → 32f. If each additional frame adds
~0.01 attention-drift per Sam's framing, we expect STATIC cos to
drop roughly linearly.

**Falsification:** flat or non-monotonic → drift hypothesis is
wrong and a different mechanism explains the 16f non-monotonic
bucket scaling on Qwen (which, under Sam's drift framing, would
not have occurred on Qwen at all since Qwen STATIC cos is ≈ 1).

### H4 (attention-entropy is a WEAKER proxy than cosine)

Mean attention-entropy over visual tokens, computed at the same
classification granularity, **correlates weaker** with ground-
truth accuracy than STATIC-token mean cosine does. Correlation is
measured over 20 (bucket, frame_count) cells we already have
baselines for.

**Falsification:** entropy correlation > cosine correlation →
entropy is the better proxy after all; re-scope 1.57 to
entropy-first in the followup.

## Implementation sketch

Not an experiment runtime estimate — just scope for planning.

1. Reuse existing dense runs' feature-cache artifacts. Each cached
   feature tensor can be compared to a fresh-encode pass on the
   same frame.
2. Add a `scripts/measure_feature_drift.py` that:
   - loads a pre-computed classification (STATIC/SHIFTED/NOVEL)
     for a short video
   - runs two ViT passes: (a) cache-substitute for STATIC+SHIFTED,
     (b) fresh ViT encode of all tokens
   - emits per-token cosine + per-class mean + entropy statistics
3. Runs on M3 Air are 1-video at a time; bounded RSS.

## Runtime estimate (benchmark-only)

- Per video: ~60-90 s (2 ViT passes per frame × 10 frames ≈ 90 s).
- Cell count: 3 classes × 2 models × 3 frame counts × 5 videos
  = 90 measurements, batchable to ~30 × 90 s = 45 min wall-clock.
- Total: **~45-60 min**, light compute. Works on CPU too if MPS
  availability is a problem.

## Decision rules

- H1 + H2 both earn → mechanism claim lands. This is a paper
  section: "Why identity-cache is bit-faithful on Qwen but only
  -10pp on Gemma: STATIC-token attention-propagation drift, 0.95+
  on Qwen but 0.67–0.80 on Gemma."
- H1 earns + H2 rejects → even Qwen has STATIC drift; our
  identity-cache agreement result needs re-interpretation.
- H3 earns → drift-compounds framing explains why frame scaling
  has different shapes per model; becomes a claim #8/#11 thread.
- H4 falsified → re-scope to entropy; rerun experiment.

## Scope — what 1.57 does NOT answer

- Which levers *fix* drift (RoPE correction, periodic refresh,
  mixed-resolution sampling) — deferred; this is the measurement
  phase, not the intervention phase.
- Whether drift is causally load-bearing for accuracy — 1.57
  shows the correlation. Causal claim requires an intervention
  study (e.g., artificial drift injection).
- Whether Sam's specific numbers reproduce on our stack — we
  use Sam's framing but measure on our regime (Qwen 7B 4-bit,
  Gemma 4-E4B 4-bit, 8-32 frames).

## Cross-references

- `~/s/codec-through-sam/research_queue.md` lines 14-29
  (authoritative drift-by-class finding).
- `2026-04-19-codex-round-21-sam-imports.md` (now superseded for
  1.57; that file was a planning note).
- Claim #11 (streaming reproduction — mechanism strengthener).
- Claim #8 (VideoMME frame scaling — non-monotonic buckets).
- Phase 1.51R (novelty-pruning on Gemma — this mechanism
  explains why pruning STATIC is safe).

## Status

- [ ] `measure_feature_drift.py` scaffold landed
- [ ] Gemma 4-E4B-4bit drift-by-class on VideoMME n=10
- [ ] Qwen 2.5-VL-7B-4bit drift-by-class on VideoMME n=10
- [ ] Frame-count sweep (8f, 16f, 32f) on each model, one bucket
- [ ] Attention-entropy comparison pass
- [ ] Findings doc with H1-H4 verdicts
- [ ] Claim matrix update (#11 mechanism strengthener)
