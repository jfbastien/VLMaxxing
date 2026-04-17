# Phase 1.42 — Gemma 4 architecture-topology lane (second-architecture reuse fidelity)

Date: 2026-04-17
Parent: `paper/claim-matrix.md` claim #7 (architecture-conditioned
reuse fidelity is a spectrum)
Sibling: `research/experiments/2026/2026-04-17-phase-1_51-novelty-pruning-gemma-prereg.md`
(same model, orthogonal pruning axis)

## Motivation

Claim #7 in the paper matrix asserts that reuse fidelity is a
spectrum that depends on vision-encoder attention topology. The
evidence so far is entirely on **Qwen 2.5-VL** (windowed global
attention with full-global layers at layers {1, 9, 17, 25}). Sam's
whitepaper §2.7/§2.9 notes that all-global architectures (e.g.
InternVL3) still exhibit 95 % strict agreement when reusing stale
tokens, so the claim "windowed-mostly = byte-identical, all-global
= high-fidelity approximate" was under-evidenced by the original
binary framing. A second local architecture is required.

**Why Gemma 4 and not InternVL3:** Gemma 4-E4B-IT-4bit (4 GB on
disk as MLX 4-bit) fits on the M3 Air 16 GB without activation
swapping, loads via `mlx-vlm >= 0.4.4`, and has a **different
attention topology** from Qwen:

| Axis | Qwen 2.5-VL-7B-4bit | Gemma 4-E4B-IT-4bit |
|---|---|---|
| Vision encoder | ViT w/ windowed-global (cross-layer) | ViT all-global (standard SigLIP-style) |
| Patch size | 14 × 2 merge = 28 | 16 |
| Spatial merge | `spatial_merge_size=2` | `pooling_kernel_size=3` post-encoder |
| Positional (vision) | 2D RoPE on patches | Learned 2D positional |
| Positional (LLM) | M-RoPE-V (ties token index to grid) | Standard RoPE on 1D sequence |
| Depth (vision) | 32 blocks | 16 blocks |
| Hidden (vision) | 1280 | 768 |
| Weights | ~8 GB (4-bit) | ~4 GB (4-bit) |

The Qwen/Gemma pair spans both attention-topology and positional-
embedding axes. Two architectures with four distinct properties is
a stronger test of "spectrum not binary" than one pair of nearly-
identical all-global models.

InternVL3 deferred because: (a) the local mlx-vlm fork does not
yet support it for video (only single-image), (b) InternVL3's
all-global topology is the same family as Gemma, so Gemma already
covers that axis, (c) InternVL3 would be a third-architecture
nice-to-have but not paper-grade-blocking.

## Hypothesis

H1 (fidelity): Gemma 4 under Planner 2.0 base (MAX_ABS static+
shifted age=4) exhibits ≥ 85 % strict cached-vs-dense agreement on
TOMATO motion holdout N=30. If Qwen hits ≥ 95 % agreement at this
configuration (phase 1.26.B shows 0.93-0.95 on MVBench, 0.82-0.87
on TOMATO), Gemma agreement MAY be lower (all-global topology
propagates stale token errors more broadly through self-attention),
but not catastrophically so.

H2 (accuracy): Gemma 4 cached accuracy is within 0.10 absolute of
dense-8 Gemma accuracy on both TOMATO and MVBench motion N=30. A
larger gap would indicate that all-global reuse on a smaller model
(4 B params vs 7 B) is quality-limiting.

H3 (Pareto): Planner 2.0 on Gemma achieves a Pareto win against
matched-budget dense on at least one benchmark (equal-or-better
accuracy at lower effective_fresh_frames). If it does not, the
"architecture-conditioned" story is asymmetric: the Qwen win may
depend on Qwen's windowed topology creating bounded information
flow.

## Method

**Phase A — model integration** (infrastructure, not yet written):

1. Extend `scripts/run_benchmark_track_a.py` to accept
   `--model-path` pointing at Gemma 4; the script currently
   hard-codes Qwen-specific vision-merger reshape code in
   `_mix_qwen_features`. A `_mix_gemma_features` parallel path is
   needed that respects Gemma's `pooling_kernel_size=3` and
   `patch_size=16`.
2. Update `src/codec_through/track_a.py::active_region_block_mask`
   to handle Gemma's 14×14 merged-token grid (at 224×224 images
   with 16-px patches and pool=3, the grid is `224/16/3 = 4.67`
   which does NOT divide evenly; the active-region mask must
   account for non-integer pooling or the image size must be
   chosen to divide cleanly — likely 336×336 → `336/16/3 = 7.0` or
   384×384 → `384/16/3 = 8.0`).
3. Verify `mx.get_peak_memory()` stays under 13 GB for a single
   Gemma-4-E4B forward at 8 frames × 336×336 (the leftover 3 GB
   headroom preserves ability to run Track B dense baseline
   alongside).

**Phase B — fidelity run** (paper-grade, N=30 holdout):

1. Single-shot: Planner 2.0 base (MAX_ABS, static+shifted, age=4,
   no halo-veto) vs dense-8 on TOMATO motion holdout N=30 and
   MVBench motion holdout N=30. No dev tranche (we are NOT re-
   selecting the winner on Gemma — we are transferring the Qwen-
   selected policy as-is and measuring drift).
2. Metrics: cached_accuracy, dense_accuracy, strict agreement,
   effective_fresh_frames, per-pair reuse class histogram,
   per-pair longest-stale-run.

**Phase C — Track B on Gemma** (if Phase B passes):

1. Same harness as `scripts/run_track_b.py` but with Gemma
   model-path. Measure dense wall-clock baseline at 8 frames.
   Record prefill / vision / decode split. Compare to Qwen
   baseline (TOMATO 61.1 s, MVBench 56.5 s at 8-frame 560×560).
   Prediction: Gemma is 2-3 × faster per item because half the
   weights, no windowed-attention overhead, and smaller vision
   hidden size. If confirmed, the "BIG NUMBERS" story opens.

## Accept / reject gates (preregistered)

- **TOMATO holdout Gemma 4, accept fidelity:** strict agreement
  ≥ 0.85 AND cached_accuracy within 0.10 of dense-8 Gemma. This
  lets us say "reuse fidelity is a spectrum, and the all-global
  Gemma sits at 85-95 % agreement, not catastrophically below
  windowed-global Qwen's 93-95 %."
- **TOMATO holdout Gemma 4, reject fidelity:** strict agreement
  < 0.70 OR cached_accuracy > 0.15 below dense-8 Gemma. This
  would falsify the "high-fidelity approximate" half of claim #7
  and force us to rewrite the claim as genuinely binary.
- **MVBench holdout Gemma 4, accept fidelity:** strict agreement
  ≥ 0.85 AND cached_accuracy within 0.10 of dense-8 Gemma. Same
  threshold as TOMATO.
- **Pareto win, accept claim #7 architecture transfer:** Planner
  2.0 on Gemma is at least tied on one benchmark and strictly
  wins on the other at matched effective_fresh_frames.
- **Track B speed prediction, accept:** Gemma median end-to-end
  is ≤ 30 s/item at TOMATO 8-frame mc_scoring (half Qwen's
  61 s). Falsification = Gemma runs as slow as Qwen despite half
  the weights, which would indicate the mlx-vlm Gemma path has
  implementation overhead we can't attribute to model size alone.

## Why this phase is architecturally important

Before phase 1.42, claim #7 rests on one model. The paper cannot
responsibly claim "architecture-conditioned reuse" with N=1.
Adding Gemma takes N to 2 and lets us measure the *difference*
rather than just state the claim. If the difference is small
(Gemma and Qwen agreement within 5 points), the paper's claim
shrinks to "reuse works across two different VLM topologies";
that's a smaller claim but defensible. If the difference is large
(Gemma < 70 % agreement), we have a more interesting story: the
paper explains WHEN reuse fails, not just THAT it can work.

## Runtime estimate

Wall-clock only (infrastructure impl time excluded, per user
instruction):

| Stage | Duration estimate |
|---|---|
| Phase A integration smoke run (single-item Gemma fwd, verify feature extraction) | 5 min |
| Phase B TOMATO N=30 single-shot (8 frames, 4-bit, expected 30 s/item) | 15 min cached + 15 min dense = 30 min |
| Phase B MVBench N=30 single-shot (8 frames, 4-bit) | 15 min cached + 15 min dense = 30 min |
| Phase C Track B dense baseline TOMATO N=30 | 15 min |
| Phase C Track B dense baseline MVBench N=30 | 15 min |
| **Total** | **~95 min of GPU time** |

## Paper-grade artifacts (expected)

- `research/experiments/2026/artifacts/phase1_42_gemma_tomato_motion_holdout_v2_cached/*.json`
- `research/experiments/2026/artifacts/phase1_42_gemma_mvbench_motion_holdout_v2_cached/*.json`
- `results/track_b/gemma_tomato_mc_n30.json`
- `results/track_b/gemma_mvbench_mc_n30.json`

## Status

- 2026-04-17: Gemma 4-E4B-IT-4bit verified to load under
  `mlx-vlm==0.4.4` on M3 Air 16 GB (patch_size=16,
  pooling_kernel_size=3, 16 vision layers, hidden=768). Registry
  entry follows.
- Phase A integration: NOT STARTED. Blocked on
  `_mix_gemma_features` implementation in the Track A harness.
- Phase B single-shot: NOT STARTED. Blocked on Phase A.
- Phase C Track B: NOT STARTED. Blocked on Phase B pass gate.

## Why Gemma and not InternVL3 — a methodological note

Sam's whitepaper uses InternVL3 as the all-global reference.
Running the same reference on M3 Air is desirable for direct
comparison. However, InternVL3 MLX support is weaker than Gemma's
(single-image only in the current mlx-vlm fork), and the
architectural axis Gemma covers (all-global + learned 2D
positional + standard RoPE on LLM) is already distinct enough
from Qwen to settle the binary/spectrum question. InternVL3
remains a future-work architecture but is not blocking.
