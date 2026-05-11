# OV-3 Full Analysis: Final Track A Readout And Next Gates

Date: 2026-05-10
Hardware: M3 16GB MacBook Air, MLX unified GPU
Scope: Qwen2.5-VL-7B-4bit, VideoMME short, Track A semantic substitution.

## Final Result

The OV-3 result is a bounded positive Track A signal. It is not yet a systems
speedup.

At 8 frames on 57 VideoMME-short items, all four codec score sources beat pixel
`max_abs` and dense by point estimate at matched active-refresh budget:

| source | dense | pixel | codec | codec - pixel | codec->dense | codec->pixel | McNemar fixes/breaks |
|---|---:|---:|---:|---:|---:|---:|---:|
| novel_coded | 0.667 | 0.649 | 0.702 | +0.053 | 55/57 | 54/57 | 3 / 0 |
| motion | 0.667 | 0.649 | 0.684 | +0.035 | 54/57 | 55/57 | 2 / 0 |
| residual | 0.667 | 0.649 | 0.684 | +0.035 | 56/57 | 55/57 | 2 / 0 |
| fused | 0.667 | 0.649 | 0.684 | +0.035 | 54/57 | 55/57 | 2 / 0 |

None of the per-source McNemar tests is significant: novel_coded p=0.25, the other
sources p=0.50. The correct statistical interpretation is "consistent positive
direction across sources, underpowered per-cell tests", not "codec significantly
beats pixel."

## What Changed From The Interim N=20 Readout

The N=20 result overcalled two things.

First, "simple codec sources preserve dense on 20/20" was true on that slice but did
not remain exact at N=57. Final codec->dense agreement is still high, 54/57 to 56/57,
but no source is perfect.

Second, "fused fails" was too strong. The N=20 manifest did not contain the later N=57
fused-rescue rows, so fused-equals-pixel at N=20 was a manifest-coverage artifact. It
still does not beat the simpler codec sources, and the frame=16 collapse is a separate
operating-point boundary affecting every codec source.

## Boundary Conditions

Frame budget matters. At frame_count=16 on the N=20 manifest, every codec source
matches the pixel answer set exactly: codec=0.750, pixel=0.750, dense=0.700,
codec->pixel=20/20, codec->dense=19/20. The frame=8 advantage over pixel is not a
general frame-budget claim.

Dense is not a perfectly stable reference on this hardware. Across two driver-session
overlaps, dense flipped 1/20 answers while pixel and codec had 0/20 flips in the same
overlaps. This is a caveat on dense-agreement metrics, not a broad determinism theorem.

PyAV metadata extraction is expensive in the current harness: median about
19.4 seconds/item and p95 about 28.1 seconds/item in the N=57 statistical audit. A
decoder-integrated implementation may make this cheap, but our current repo-local
implementation does a separate extraction pass.

## Paper Interpretation

The strongest honest paper contribution from OV-3 is:

- OneVision-Encoder is the trained codec-aligned encoder counterpart.
- VLMaxxing can use codec metadata as a frozen-runtime refresh oracle in Track A.
- The local evidence reopens continuous H.264 spatial scoring as a bounded hypothesis:
  VideoMME short, Qwen2.5-VL-7B-4bit, 8 frames, matched-budget semantic substitution.
- The result is diagnostic until Track B shows real skipped work.

Do not use "WOW" language around speed yet. The industry-relevant claim becomes real
only if OV-6 shows measured vision-stage or end-to-end savings at fidelity-clean
codec pruning.

## Recommended Next Experiments

### 1. OV-6 Track B Codec Sparse Vision

Hypothesis: the best simple OV-3 codec source can drive real Qwen sparse vision at
8 frames with less fidelity loss than current magnitude_norm / uniform_random baselines.

Implementation requirements:

- Add a `codec_grid` score path to `src/codec_through/qwen_pruned_vision_tower.py`.
- Build pure helpers that map per-frame codec grids into Qwen merged groups, then into
  post-window group order.
- Reject shape mismatches, NaN/inf scores, negative scores, and frame-count mismatch.
- Add runner provenance fields for score source, fusion mode, projection version, and
  metadata extraction cost.
- Add CPU tests for synthetic grid alignment, frame-0/anchor policy, and setup-inclusive
  accounting.

Expected cost: 200-350 LoC if done cleanly, plus 1-2h GPU for an M3 8f smoke. Use M5
only after the M3 smoke proves codec-grid alignment and lands a fidelity-clean cell.

### 2. OV-8 C-PERSIST Composition

Run only after OV-6 produces dense-vs-codec timing rows. The first pass should be
artifact-level accounting:

`session_time(Q) = measured_sparse_first_query + (Q - 1) * measured_C-PERSIST_followup`

Do not multiply speedup ratios across denominators.

### 3. TOMATO Motion Replication

Hypothesis: if codec scores are genuinely useful saliency proxies, motion-heavy TOMATO
items should preserve or strengthen the codec-over-pixel direction. If TOMATO reverses,
the claim stays VideoMME-short-specific.

### 4. Threshold Sensitivity

Hypothesis: the N=57 signal may depend on share-matched calibration. Sweep static/fresh
budget and absolute-score thresholds at frame_count=8 before adding any tuned policy.

### 5. Dense Determinism Multi-Seed

Hypothesis: dense instability is small but nonzero on this local MLX stack. A rerun of
the N=57 driver would tighten the flip-rate interval and help decide whether
codec->dense should remain a primary metric or be demoted behind ground-truth direct
accuracy.

## M5 Update

The M5 should not rerun the whole exploratory tree first. It should execute only after
the M3 8-frame smoke validates codec-grid ordering and produces a fidelity-clean cell:

1. Broaden Qwen Track B at 8f on M5 only after M3 smoke gates.
2. Run 16f Track B only if 8f remains fidelity-clean with measured timing gain.
3. Run 32f Track B only if 16f remains fidelity-clean and memory headroom is acceptable.
4. Run Gemma only after Qwen has a clean cell worth cross-family confirmation.
5. Use spare M5 time for TOMATO motion replication or multi-seed dense characterization
   if Track B is blocked.

## Query-Aware / RLT Boundary

Do not implement query-aware routing on this branch. The useful cross-pollination is
conceptual: codec score planes may become physical evidence operators in a later
query-aware/RLT planner. That needs a separate design/dev/holdout split and should not
reuse OV-3 inspected items for rule design.
