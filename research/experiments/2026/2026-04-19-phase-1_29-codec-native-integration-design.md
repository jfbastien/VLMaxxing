# Phase 1.29 — Codec-native BlockStatistic integration (design note)

**Status:** design note 2026-04-19. **Not an experiment prereg** —
scoping the code change needed before a codec-native planner run can
be preregistered. Ports the newly-landed `h264_metadata.py`
extractor (`src/codec_through/codec/`) into the Track A planner path
at `src/codec_through/temporal.py` + `scripts/run_benchmark_track_a.py`.

## Problem

`BlockStatistic` in `src/codec_through/temporal.py:29-36` is a
**pixel-domain** registry. Every entry consumes decoded frame pairs:

```
block_statistic_values(frame_a, frame_b, block_size, config)
    -> ndarray[block_rows, block_cols]  # float32 scalars per block
```

The codec-native path has a different input signature. It needs the
**encoded .mp4/.mkv bitstream path**, runs PyAV once with
`AV_CODEC_FLAG2_EXPORT_MVS`, and emits per-macroblock motion vectors
+ residual-CBF labels. The shape is `(H/16, W/16)` for H.264 (hard
16×16 MB geometry), not the tunable `block_size` used by the
pixel-domain planner.

Adding `BlockStatistic.CODEC_NATIVE` as a 5th enum value is
**insufficient** because:

1. `block_statistic_values(frame_a, frame_b, ...)` never sees the
   video path.
2. H.264 MBs are fixed 16×16; the pixel-domain config passes
   arbitrary `block_size`.
3. Codec metadata is a *whole-video* precompute, not a per-pair
   recomputation — redoing it per frame-pair would 2×-8× video
   decode cost and defeat the point of the signal.

## Design (3 incremental stages)

### Stage A — data path

Add a `PerFramePairMetadata` optional cache on the benchmark sample:

```python
# src/codec_through/sample.py (or wherever BenchmarkSample lives)
@dataclass(frozen=True)
class CodecMetadataCache:
    # One entry per frame-pair: (block_rows, block_cols) label array
    # with BlockClass (STATIC/SHIFTED/NOVEL) values.
    per_pair_labels: tuple[np.ndarray, ...]
    mb_rows: int
    mb_cols: int
```

During `_prepare_sample` in `scripts/run_benchmark_track_a.py:1097`,
call the codec extractor once per video, compute the F-1 pair
classification labels via `classify_blocks_h264`, and attach the
cache to the sample. Pixel-domain frames are still decoded
separately (they feed the vision tower); the codec cache is
additive.

### Stage B — planner dispatch

Extend `block_statistic_values()` at `temporal.py:171` with a
short-circuit branch:

```python
if config.statistic is BlockStatistic.CODEC_NATIVE:
    # Caller must have attached codec_cache via kwargs or config.
    return codec_cache.per_pair_labels[frame_pair_index]
```

Note this short-circuit returns **BlockClass integer labels**
directly, not a scalar that gets thresholded. That means
`classify_blocks_with_planner` (`temporal.py:202`) needs a
corresponding branch: when values are already class labels
(`dtype == int` and statistic is `CODEC_NATIVE`), skip the
`static_threshold`/`shifted_threshold` step entirely.

Alternative (cleaner): emit a continuous codec-score in Stage B
(e.g., `residual_energy + motion_magnitude`) and let existing
threshold machinery classify it. Trade-off: loses the explicit
STATIC/SHIFTED/NOVEL tri-state that h264_metadata already computes
and forces arbitrary threshold choice.

**Recommended:** take the short-circuit path. Codec metadata is the
authoritative label; round-tripping it through a continuous scalar +
threshold is a regression.

### Stage C — CLI + prereg

Add `codec_native` to the `--statistic` choice list at
`scripts/run_benchmark_track_a.py:1544-1548`. The enum addition is
the one-line code change; the plumbing lives in Stages A+B.

Write a prereg for the first codec-native run:
- **H1**: codec_native on Qwen 8f VideoMME matches `MEAN` within
  ±3pp aggregate accuracy (bit-faithfulness-ish check that the
  STATIC/SHIFTED/NOVEL semantics are comparable to the pixel-diff
  proxy at the current operating point).
- **H2**: codec_native is faster per-item than pixel-diff MEAN on
  the long bucket (single decode vs. two-pass pixel extract +
  frame_a/frame_b difference).
- **H3**: dense-vs-cached agreement = 1.000 under identity cache
  (bit-faithfulness of the new planner path, same invariant we
  check for every other statistic).

## Estimated effort

- Stage A (sample-side cache plumbing): ~3h, touches 2-3 files,
  no model changes.
- Stage B (planner dispatch short-circuit): ~1h, tightly scoped to
  temporal.py.
- Stage C (CLI + prereg): ~30 min.

All CPU-only and MLX-safe (does not perturb GPU paths).

## Tests

Regression tests for h264_metadata already exist
(`tests/codec/test_h264_metadata.py`, 6 tests, all green). For the
integration, add:

- `tests/track_a/test_codec_native_sample_prep.py`: a synthesized
  PyAV clip → BenchmarkSample with codec cache populated and
  correctly sized.
- `tests/track_a/test_codec_native_planner_dispatch.py`: verify the
  short-circuit branch returns the same labels that
  `classify_blocks_h264` produces on the synthesized clip.

No MLX/CUDA required for either test; both work on GitHub Actions
CPU runners.

## What this earns if landed

- Claim #5 Track B gets a **non-pixel-diff signal column** — the
  paper's "real sparse execution" narrative becomes multi-signal
  instead of pixel-diff-only.
- Codec-native path unblocks 1.54's "most aggressive" decode-
  avoidance option (line 74-77 of 1.54 prereg).
- Orthogonal to 1.51V (vision-tower pruning) and 1.51R (novelty
  pruning) — can A/B against both without conflict.

## What this does NOT earn / limitations

- Signal quality on non-H.264 videos is out of scope (VideoMME,
  MVBench, TOMATO are H.264; good enough for paper claims).
- Per-frame *quality* (not just speed) improvement is not
  guaranteed — H1 is deliberately a parity-band test.
- Fixed 16×16 MB geometry: cannot compete in any experiment that
  sweeps `block_size`.

## Deferred until

User gives green light to implement. The design is recorded so
execution is ~5h of mechanical work when un-deferred.

## Cross-references

- `src/codec_through/codec/h264_metadata.py` (the port)
- `tests/codec/test_h264_metadata.py` (regression tests, green)
- `src/codec_through/temporal.py:29-36` (BlockStatistic registry)
- `scripts/run_benchmark_track_a.py:1544-1548` (CLI `--statistic`)
- Phase 1.54 prereg (uses codec-native as decode replacement)
