# Phase 1.55D (v1 driver) — Selective re-prefill (FINDINGS)

**Date:** 2026-04-20.
**Parent:** `2026-04-20-phase-1_55D-selective-reprefill-prereg.md`.
**Verdict:** **INFRASTRUCTURE-FALSIFIED (not scientifically falsified).**
The prereg is not actionable with the current mlx-vlm driver. The
scientific hypotheses H1/H2/H3/H4 remain preregistered and untested.
This is a **parallel finding to 1.55C**: both run into distinct but
related limitations of mlx-vlm's multimodal prefix-cache reuse path.

## Headline

The v1 driver (`scripts/run_kv_selective_reprefill.py`) lands cleanly
and runs Q1 of each clip correctly. It fails on Q2 with a shape-
broadcast crash inside mlx-vlm's Qwen 2.5-VL `get_rope_index`, because
mlx-vlm's `PromptCacheState`-based prefix trimming is a single-tensor
operation: when `find_prefix_length` trims `input_ids` to only the
new-tokens tail, it does **not** correspondingly trim
`attention_mask`, `pixel_values`, or `image_grid_thw`. The prefix-
reuse contract in mlx-vlm currently assumes one of two clean regimes:

1. **Full image-block reuse** (1.55A): the shared prefix contains the
   entire image block. mlx-vlm's `generate` sets `pixel_values = None`
   (generate.py:684) and feeds only post-image new text tokens — no
   image processing, no broadcast. This works.
2. **No reuse** (cold start): full prompt with full auxiliary tensors;
   image block freshly processed. This works.

**The "partial image-block reuse" regime that selective re-prefill
requires is not supported.** In this regime, the shared prefix covers
the first N−K frames but stops inside the image block; the trimmed
tail still contains `(K frames + question)` image tokens. mlx-vlm
keeps the full 20-frame `pixel_values` and full-length
`attention_mask` — then `get_rope_index` asserts their length against
the trimmed `input_ids` and crashes.

## Concrete crash (clip 037, K=4)

```
[1.55D] clip 037 duration=short
   trunc_idx=6447 (input_len=8094; reprefill tail = last 4 frames + question)
   session Q1: 68505 ms prefix=0/8094 (0.00%) correct=True resp='D'
ValueError: [broadcast_shapes] Shapes (8119) and (1672) cannot be broadcast.
 at mlx_vlm/models/qwen2_5_vl/language.py:296
   input_ids = mx.where(attention_mask[i] == 1, input_ids, mx.zeros_like(input_ids))
```

- Q1 cold-start succeeded: 68.5s prefill on 8094 tokens, correct="D".
- On Q2: `PromptCacheState.find_prefix_length` computed a 6447-token
  shared prefix (after my `_truncate_state_for_reprefill(state,
  trunc_idx=6447)` rewound the cache before Q2). mlx-vlm then trimmed
  `input_ids` from 8119 → 1672 new tokens. The retained
  `attention_mask` (length 8119) and `pixel_values` (20 frames, full)
  were not co-trimmed. `get_rope_index` broadcast failure ensued.

## Why 1.55A works but 1.55D does not

1.55A's follow-up Q2/Q3 share the ENTIRE image block with Q1 (same
frames, same question template scaffold). The prefix-length match
runs past the last image token into the prior answer or into the
question-text region. mlx-vlm's `generate.py:683-687` detects this
and sets `pixel_values = None` for the continuation. No shape
broadcast involving image auxiliaries is performed.

1.55D by design cuts the prefix at `trunc_idx = (N−K) × tokens_per_
frame + system-prompt`, which lands **inside** the image block.
`generate.py:683-687`'s `pixel_values = None` shortcut doesn't
trigger. mlx-vlm attempts full auxiliary processing with mismatched
shapes.

## Why this was not caught pre-run

The prereg's "driver prerequisite" noted that `PromptCacheState`
truncation support was needed but assumed cache-level truncation was
sufficient. Cache-level truncation IS sufficient for the KV math;
what's missing is that mlx-vlm's `generate` entrypoint also needs to
co-slice `pixel_values`, `image_grid_thw`, and `attention_mask` when
the shared prefix lands inside an image block. This is an
architectural constraint of the multimodal prefix-reuse contract, not
a drop-in-trimming bug.

## What IS and IS NOT falsified

**FALSIFIED:** The prereg's implicit assumption that mlx-vlm's current
`PromptCacheState` + `find_prefix_length` contract supports partial
image-block reuse (shared-prefix-ends-inside-image-block).

**NOT FALSIFIED (still scientifically open):**
- H1-1.55D (fidelity recovery at K=4 Δacc ≤ −0.15): untested.
- H2-1.55D (speedup floor ≥ 10× at K=4): untested.
- H3-1.55D (basin dispersal ≤ 4/14 on attractor set): untested.
- H4-1.55D (RSS ≤ 6 GB): untested.

All H1–H4 remain preregistered for re-run once a correctness-
preserving driver path is available.

## Path to actionability

Three options, ranked by effort and faithfulness to the prereg:

### Option A: Fork mlx-vlm's generate path to co-slice auxiliaries (~3-5 h)

Modify `mlx_vlm/generate.py` around lines 680-710 to, when prefix
trimming lands inside an image block, slice `pixel_values` and
`image_grid_thw` to the last K frames and slice `attention_mask` to
match the trimmed `input_ids` length. Requires:

- A helper to identify which image tokens fall in the trimmed tail
  (already implemented in the v1 driver as `_compute_trunc_idx`).
- A per-frame slicing operation on `pixel_values`. Qwen 2.5-VL's
  pixel_values is flattened `(total_patches, hidden)` with
  `image_grid_thw = (n_frames, H, W)` indexing patches-per-frame as
  `(H*W)/merge_unit²` per frame. A clean slice reduces this to
  `(K * H * W / merge_unit², hidden)` and `image_grid_thw = (K, H, W)`.
- A smoke test (Q1 cold start → Q2 partial-reuse gives same logits
  as a hypothetical Q2-cold-start to within float tolerance).

This is the faithful path — it implements exactly the prereg's
selective re-prefill semantics. It also generalizes to future probes
that need partial image-block reuse (e.g., first-frame ablation on
persistent-KV sessions).

### Option B: Emit full Q2 prompt per query with manual cache injection (~1-2 h)

Bypass `PromptCacheState`'s auto-trim by constructing a custom cache
list pre-populated with the first-N−K-frames KV and passing it as
`kv_cache` rather than `prompt_cache_state`. This sidesteps
`find_prefix_length` entirely; mlx-vlm sees the cache as a pre-
initialized state and processes the full Q2 input as "continuation."
Risk: the continuation still has to re-prefill the last K frames
through the existing generate path, and it may still hit the same
broadcast mismatch if auxiliary tensors don't match the continuation
tokens. Untested.

### Option C: Swap the scientific question to "text-only selective re-prefill" (~30 min)

If the re-prefill target is shifted to the question-text tail only
(not the last-K image frames), the shared prefix ends cleanly
after the image block and Option B / existing infra works. This
tests whether re-prefilling the text question (but not the image
tail) is sufficient to escape the basin. Scientifically different
claim — weaker than the prereg's "tail-frame re-prefill" — but a
legitimate variant that can run immediately.

## Recommended disposition

1. **Do NOT re-run v1 driver.** It crashes deterministically on Q2.
2. **Keep 1.55D preregistered.** The scientific question remains the
   first fidelity-recovery lever post-temperature-probe.
3. **Defer 1.55D behind productive non-blocked experiments.** Current
   non-blocked queue: 1.51V vision-tower pruning (#108), 1.51R
   focused dev sweep (#82). Both exercise independent code paths and
   do not depend on mlx-vlm's prefix-reuse contract.
4. **1.55D can return** via either (a) Option A fork work with smoke
   test, or (b) Option C as a variant prereg on text-only selective
   re-prefill.

## Parallel with 1.55C

Both 1.55C (Gemma cross-family) and 1.55D (selective re-prefill)
have hit **distinct but related limitations of mlx-vlm's multimodal
prefix-cache reuse path**:

- **1.55C:** `PromptCacheState` truncation is semantically incorrect
  for `RotatingKVCache` once rotation has begun (Gemma sliding-window
  layers at realistic video prefills).
- **1.55D:** `PromptCacheState` truncation is not co-applied to
  auxiliary multimodal tensors (`pixel_values`, `image_grid_thw`,
  `attention_mask`) when the shared prefix lands inside an image
  block.

**Both findings are valuable for the paper.** They delineate the
*current* capability frontier of mlx-vlm's cache-reuse infrastructure
— exactly the frontier a deployment-focused paper on persistent-KV
fidelity needs to characterize. The paper should footnote both as
"infrastructure-side open questions" rather than claiming the
experiments are simply "future work."

## Implication for the paper

Claim #14 (3-D decomposition): remains Qwen-7B/3B at 20f+ greedy/
temp-invariance. The fidelity-recovery lever section (planned
addition per 1.55A findings' "Next steps") should declare selective
re-prefill as an **open infrastructure question** with the mlx-vlm
broadcast constraint documented.

## Artifact paths

- v1 driver: `scripts/run_kv_selective_reprefill.py` (597 lines).
- Crash artifact:
  `research/experiments/2026/artifacts/phase1_55D_selective_reprefill/run_k4.log`
  (Q1 correct, Q2 crash).
- Partial session JSONL (1 correct Q1 line only):
  `research/experiments/2026/artifacts/phase1_55D_selective_reprefill/session_k4_n7.jsonl`
- Source evidence:
  - `mlx_vlm/generate.py:680-710` (prefix-reuse path)
  - `mlx_vlm/models/qwen2_5_vl/language.py:296` (broadcast site)
  - `scripts/run_kv_selective_reprefill.py:208-223`
    (`_truncate_state_for_reprefill`)

## Next steps

1. **Pivot to 1.51V vision-tower pruning (#108)** as the next
   productive experiment. Independent code path; not blocked by the
   mlx-vlm prefix-reuse contract. Pre-registration from Phase 1.51V
   notes in #87.
2. **Or 1.51R focused dev sweep (#82)** continuation if 1.51V prereg
   needs more design work.
3. **1.55D deferred** pending Option A (mlx-vlm fork, correctness
   smoke test) or Option C (text-only variant prereg). Not on
   critical path; 1.55A already delivers the distribution-level
   mechanism characterization the paper needs.
