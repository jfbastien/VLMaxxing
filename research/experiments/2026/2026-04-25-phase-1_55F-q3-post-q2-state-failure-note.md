---
phase: 1.55F
date: 2026-04-25
parent: research/experiments/2026/2026-04-25-phase-1_55F-q3-post-q2-state-prereg.md
status: runner failed 2026-04-25; code path fixed in 1b7c05a; rerun pending.
---

# Phase 1.55F — Q3 from repaired post-Q2 state (RUNNER FAILURE NOTE)

**Verdict:** **Not a science failure; a runner-code failure that is now fixed
and smoke-validated.** The prereg's hypothesis is still untested. The specific
MLX path `generate_qwen_tail_with_explicit_positions` used to crash when a
`K=0` re-prefill slice contained zero new image tokens, causing
`mx.concatenate` on an empty list inside `qwen2_5_vl/vision.py:rot_pos_emb`.
Commit `1b7c05a` fixed that text-only-tail path by bypassing the vision tower
when the slice contains no image rows; a one-clip Q3 smoke run now completes
successfully on the repaired branch, so the full experiment is ready to rerun.

## What was supposed to happen

`1.55E` showed that Q3 collapses when a K=0 fallback reuses the original
Q1 full-cache path. `1.55F` was the controlled alternative: Q3 with K=0
but cache source set to `post_q2_repaired`, testing whether Q3 is safe if
it reuses the repaired Q2 visual state instead of reverting to Q1.

## What actually happened

On the first clip (`videomme:short:037`):

- session Q1: completed (cold, K=0). 86.6 s, prefix 0%, correct=True.
- session Q2: completed (K=1, post-Q1 cache rewind + tail re-prefill).
  9.4 s, prefix 94.3%, correct=True.
- session Q3: **crashed**. Configured K=0 with `q3_cache_source=post_q2_repaired`.

Stack trace:

```
ValueError: [concatenate] No arrays provided for concatenation
File ".../qwen_selective_reprefill.py:310, in generate_qwen_tail_with_explicit_positions
File ".../mlx_vlm/models/qwen2_5_vl/qwen2_5_vl.py:49, in get_input_embeddings
File ".../mlx_vlm/models/qwen2_5_vl/vision.py:334, in __call__
File ".../mlx_vlm/models/qwen2_5_vl/vision.py:254, in rot_pos_emb
    pos_ids = mx.concatenate(pos_ids, axis=0)
```

## Root cause

`generate_qwen_tail_with_explicit_positions` calls
`model.get_input_embeddings(input_ids=..., pixel_values=tail_pixels, ...)`
on the K=0 tail slice. With K=0 and `q3_cache_source=post_q2_repaired`,
the tail slice contains **only text tokens** (the new question + assistant
header). `tail_pixels` is empty, `grid_thw` has shape `[0, 3]`, and the
upstream `vision_tower.rot_pos_emb` builds `pos_ids` as an empty list
because there are no batch entries to iterate over. `mx.concatenate([], axis=0)`
hard-errors instead of returning a degenerate empty tensor.

This is a path that did not exist before `1.55E` introduced
`q3_cache_source` last week. Fixed-K runs (1.55D) never hit it because they
always have ≥1 frame's worth of new image tokens in the tail.

## Applied fix

`src/codec_through/qwen_selective_reprefill.py:generate_qwen_tail_with_explicit_positions`
now short-circuits the vision-tower call when there are no new image tokens
to embed and routes the text-only tail through Qwen's text embedding path:

```python
# Pseudocode at line ~305
if tail_image_token_count == 0:
    # text-only tail, skip the vision tower entirely
    embeddings = model.language_model.embed_tokens(tail_input_ids)
else:
    embeddings = model.get_input_embeddings(
        input_ids=tail_input_ids,
        pixel_values=tail_pixels,
        ...,
    )
```

The exact embedding entry point on Qwen2.5-VL is
`model.language_model.embed_tokens(...)`; it is what `get_input_embeddings`
falls back to when `pixel_values` is `None`. The repo-local helper also
hard-fails if an ostensibly text-only slice still carries image/video marker
tokens or mismatched `pixel_values` / `grid_thw` rows.

## Recovery plan

1. Fix landed in `1b7c05a`.
2. Smoke test: completed on clip `037` with `--reprefill-k-q3 0
   --q3-cache-source post_q2_repaired`; Q3 now runs to completion instead of
   crashing.
3. Rerun 1.55F's wrapper (`scripts/run_phase1_55F_q3_post_q2_state.sh`)
   end-to-end. Estimated runtime ≈ 60-75 min (unchanged).
4. Auto-commit findings.

## What this does NOT mean

- The Q3 collapse-vs-recovery question is still open, not answered. The
  paper cannot yet say "Q3 catastrophe was caused by cache-source choice"
  because no data was produced.
- `1.55D` and `1.55G` both ran cleanly with `K=1` (always ≥1 frame in the
  tail), so this bug does not contaminate any landed result.

## Pending follow-ups

- After the landed fix: rerun 1.55F (~60-75 min).
- After 1.55F lands: if it passes H1+H2+H3 cleanly, write findings doc and
  consider promoting "C-PERSIST adaptive recovery via post-Q2 state" as
  the strongest mechanism story in the paper.
