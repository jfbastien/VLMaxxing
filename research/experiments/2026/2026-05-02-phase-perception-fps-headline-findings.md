---
date: 2026-05-02
phase: post-r2 reframe - perception-fps headline
status: closed-earned (computed from existing M5-5b artifacts; no new runs)
related:
  - 2026-04-29-phase-M5-5b-sam-prefix-snapshot-fix-findings.md
  - 2026-04-30-phase-upstream-mlx-vlm-swa-aware-trim-findings.md
  - sam/scaleout-m5-32f-expansion-20260501 (07f3b4a -- 32f n=21 expansion)
---

# 2026-05-02 Perception-fps headline - Gemma 4 26B-A4B prefix-snapshot

- **Status:** **closed-earned as a derived view (write-up only).** No new
  runs. Recomputes
  existing M5-5b prefix-snapshot rows as `frames-per-turn / wall-clock-
  per-turn`, the metric directly comparable to native-rate streaming
  observation budgets (e.g. 30fps continuous video computer-use agents).
- **Verdict:** at 32 frames/turn the snapshot path **ingests at a
  median 54.68 fps of perception per follow-up turn** on Gemma 4
  26B-A4B / mlx-vlm 0.4.4 / M5 Max, with worst-case 23.85 fps and
  best-case 134.43 fps across 21 paired rows. At 8 frames/turn the
  median is 27.02 fps. The 32f expanded cell clears the 30fps
  observation threshold at the median and in 19/21 rows; the 8f cell
  does not clear the threshold at the median and only 8/21 rows exceed
  30fps. The older 32f n=9 slice clears 30fps in every paired row, but
  the expanded n=21 slice does not.
- **Why this matters for the paper:** the paper currently quotes
  speedup-multipliers (9.11x at 8f, 26.59x at 32f from n=9). Multipliers
  are the correct quality-vs-cost report for after-ingest C-PERSIST;
  perception-fps is a complementary throughput denominator for readers
  thinking about native-rate visual observation. They are the same
  rows; the recomputed view does not add a new correctness gate.

## Definition

For each paired row in an M5-5b artifact:

```
fps_of_perception = prompt_frame_count / (end_to_end_ms / 1000.0)
```

`end_to_end_ms` is the same wall-clock the existing speedup tables use.
`prompt_frame_count` is the per-row frame budget (8 or 32 in the
M5-5b cells). The metric is per-turn, not per-session: the first
query still pays full cold-dense freight; the gain only appears on
follow-up turns once the prefix snapshot is warm.

## Numbers

| Source artifact | n | frames/turn | cold-dense fps (median) | prefix-snapshot fps (median) | snapshot fps min-max |
|---|---:|---:|---:|---:|---|
| `sam_m5_5b_swa_prefix_snapshot.jsonl` | 21 | 8 | 2.97 | **27.02** | 10.02 - 35.88 |
| `sam_m5_5b_swa_prefix_snapshot_32f.jsonl` (n=9, paper-cited predecessor) | 9 | 32 | 2.18 | **51.87** | 32.57 - 136.73 |
| **`sam_m5_5b_swa_prefix_snapshot_32f_n21.jsonl` (7 videos x 3 questions)** | **21** | **32** | **3.17** | **54.68** | **23.85 - 134.43** |

Speedup-multiplier view (same rows, same wall-clocks, just a different
denominator) for cross-reference with the existing paper text:

| Source artifact | n | frames | median paired speedup | min-max speedup |
|---|---:|---:|---:|---|
| 8f n=21 | 21 | 8 | 9.11x | 3.59x - 12.83x |
| 32f n=9 | 9 | 32 | 26.59x | 13.62x - 83.49x |
| **32f n=21** | **21** | **32** | **18.71x** | **7.34x - 44.17x** |

The 32f n=21 expansion brings the median *down* from 26.59x to 18.71x
because it adds four more videos beyond the favorable n=9 sample. The
**perception-fps median is essentially flat (51.87 -> 54.68)** because
the median session wall-clock drifted very little (617 ms -> 585 ms);
what shrunk was the cold-dense baseline (14.7 s -> 10.1 s) since the
new videos are easier-to-prefill than the n=9 sample. The fps view is
therefore more stable across the n=9 -> n=21 expansion than the
multiplier view, but it is a complementary throughput denominator, not
a replacement for setup-inclusive or paired-speedup accounting.

Correctness/fidelity caveat: the 8f n=21 and 32f n=21 rows both have
0 choice diffs and 0 correctness diffs. The 8f row has 6/21 text diffs
and 2/21 matched parse failures; the 32f n=21 row has 7/21 text diffs
and 0 parse failures. The fps reframe does not change those gates.

## What this changes for Section 8 of the paper

The current Section 8 reads (paraphrased):

> A topology-aware prefix snapshot is the current positive scale-out
> follow-up row: at 8f it gives a 9.11x median paired speedup with
> 0/21 paired choice or correctness diffs; at 32f it gives a 26.59x
> median paired speedup with 0/9 choice or correctness-field diffs.

Suggested addition (drop in after the existing sentence):

> Reframed as ingestion throughput: the same rows ingest a median
> 27.02 fps of perception per follow-up turn at 8 frames/turn, and
> 54.68 fps at 32 frames/turn (n=21 each, Gemma 4 26B-A4B,
> mlx-vlm 0.4.4, M5 Max). The 32f cell ranges 23.85 fps to 134.43
> fps across paired rows and clears 30fps in 19/21 rows; the 8f cell
> clears 30fps in 8/21 rows. The cold-dense baseline is 2-3 fps in
> both cells. This is the throughput axis that maps onto native-rate
> visual-stream observation, but only after the prefix is already
> warm. The first query on a fresh video still pays full cold-dense
> freight; the gain is the after-ingest regime.

This is the same C-PERSIST claim already in Section 8, restated in the
denominator that makes "30fps computer-use observation" comparisons
legible. It should not be promoted as C-STREAM closure: no continuous
capture stream, stale-cache invalidation case, or setup-inclusive
native-rate session protocol is tested here. No new experimental gates
are claimed; the 0/n choice and correctness gate is unchanged.

## What this changes for Section 9 (limitations / reproducibility)

Add to the existing paragraph on Gemma adaptive persistent-cache
reuse: the perception-fps numbers above are **conditional on the
prefix being warm and the cache topology being stable across the
turn boundary**. The library patch
(`scripts/mlx_vlm_swa_aware_trim.patch`) and the prefix-snapshot
wrapper are both required for these numbers to be safe; the default
mlx-vlm cross-turn path is unsafe on mixed SWA topologies (B0b r1),
and the patched guarded path restores correctness by refusing unsafe
reuse at roughly cold-dense wall-clock (B0b r2-followup, 0.98x of
cold). The fps story applies only to the snapshot path, not to default
cross-turn PromptCacheState reuse.

## What this does NOT cover (the next experiments)

- **Frame budgets above 32f.** The mechanism class is the same at
  64f and 128f; memory envelope is known (52 GB peak at 128f from
  S2). A 64f / 128f extension cell would test whether perception-fps
  keeps scaling with frame budget or saturates somewhere. About 1-2 hr
  per cell on M5.
- **Sustained perception over many turns.** The Qwen 7B many-turn
  cell already exists (50-turn / 343 follow-ups, no observed drift).
  An equivalent on Gemma 26B at high frame counts is what closes the
  "30fps computer-use over a full session" claim. Not run yet.
- **Real desktop captures.** All cells use VideoMME stimuli. The
  closest analogue to desktop scrolling is MV-3 (validated). A
  ground-truth replication on OSWorld-style traces is the gap that
  separates "mechanism-class match" from "tested for desktop-agent
  workloads."

## Re-derive command

```bash
cd <repo-root>
python3 - <<'PY'
import json, statistics
for path in [
    'research/experiments/2026/artifacts/sam_scaleout_m5_20260429/sam_m5_5b_swa_prefix_snapshot.jsonl',
    'research/experiments/2026/artifacts/sam_scaleout_m5_20260429/sam_m5_5b_swa_prefix_snapshot_32f.jsonl',
    'research/experiments/2026/artifacts/sam_scaleout_m5_20260429/sam_m5_5b_swa_prefix_snapshot_32f_n21.jsonl',
]:
    rows = [json.loads(l) for l in open(path)]
    fps_session = [r['prompt_frame_count'] / (r['end_to_end_ms']/1000.0) for r in rows]
    fps_cold = [r['prompt_frame_count'] / (r['baseline_end_to_end_ms']/1000.0) for r in rows]
    print(f'{path.split("/")[-1]}: median snapshot fps = {statistics.median(fps_session):.2f} '
          f'(min {min(fps_session):.2f}, max {max(fps_session):.2f}); '
          f'cold-dense fps = {statistics.median(fps_cold):.2f}')
PY
```
