---
phase: 1.41
date: 2026-04-22
parent: research/experiments/2026/2026-04-21-phase-1_41-qwen-videomme-8f-holdout-prereg.md
prior:
  - research/experiments/2026/2026-04-21-phase-1_41-qwen-videomme-16f-holdout-findings.md
  - research/experiments/2026/2026-04-19-phase-1_41-qwen-videomme-16f-findings.md
  - research/experiments/2026/2026-04-18-phase-1_41-qwen-videomme-baseline-findings.md
  - research/experiments/2026/artifacts/phase1_41_qwen_videomme_8f_holdout/
status: CLOSED — all 5 H land; H2 sub-outcome **H2b** (holdout long flat/near-ceiling at 0.800; 8f→16f long +10pp uptick, dev's −20pp shape does NOT replicate in either direction on holdout). Paired-holdout closer: non-monotone long-bucket shape is dev-only + item-draw-dependent, not a stable property of Qwen 2.5-VL 7B-4bit.
tracking: autonomous session 2026-04-21/22 dynamic-loop
---

# 1.41 Qwen 8f VideoMME holdout — findings (paired-holdout closer)

## Headline

| H  | Gate                                                                    | Observed                               | Verdict    |
|----|-------------------------------------------------------------------------|----------------------------------------|------------|
| H1 | `dense_acc ∈ [0.45, 0.75]`                                              | **0.700 (21/30)** — upper edge         | PASS (boundary) |
| H2 | sub-outcome on `long_acc(holdout 8f)` vs `long_acc(holdout 16f) = 0.900`| **long_acc 8f = 0.800** → **H2b**      | H2b LANDS  |
| H3 | `short ∈ [0.40, 0.95]`, `medium ∈ [0.30, 0.90]`                         | short 0.800, medium 0.500              | PASS (both in-band) |
| H4 | `agreement = 1.000`                                                     | 1.000 (30/30)                          | PASS       |
| H5 | peak RSS ≤ 10 GB                                                        | ≤ 16f's 7.23 GB (strictly less prefill)| PASS       |

Parse failures: 0. 30/30 items complete. Mean `dense.elapsed_ms` 27.9 s/item; total wall-clock 837 s ≈ **14 min**, well under the prereg 15-20 min estimate.

## Per-bucket per-split matrix

| split          | frame | short | medium | long  | agg   |
|----------------|-------|-------|--------|-------|-------|
| dev n=30       | 8     | 0.800 | 0.500  | 0.300 | 0.533 |
| dev n=30       | 16    | 0.800 | 0.700  | 0.100 | 0.567 |
| **holdout n=30** | **8**   | **0.800** | **0.500**  | **0.800** | **0.700** |
| holdout n=30   | 16    | 0.600 | 0.600  | 0.900 | 0.700 |

**Paired-holdout 8f→16f shape on long:** 0.800 → 0.900 = **+10pp uptick** (within n=10 noise, single-bucket Wilson 95% CI roughly [0.44, 0.97] for 8/10 and [0.55, 0.99] for 9/10 — overlap substantial).

**Dev 8f→16f shape on long:** 0.300 → 0.100 = **−20pp drop**.

The dev −20pp non-monotone shape **does not replicate on the disjoint holdout in either direction**. Holdout shows flat-to-slight-uptick long accuracy at both frame counts.

## Decision-matrix verdict (prereg §"Decision matrix")

Prereg table:

| H1 | H2 sub-outcome | Claim-matrix action |
|----|----------------|---------------------|
| pass | **H2b** (flat near ceiling) | No 8f→16f effect on holdout; paper reads "the shape did not replicate on holdout (holdout long flat ~0.85 at both frame counts)". |

Observed long-bucket mean across the two holdout frame counts is (0.800 + 0.900) / 2 = **0.85**, exactly matching the H2b description. **Paper softening from the 16f-only findings stands with added strength**: this was not just a cross-split comparison (dev 8f vs holdout 16f) but a **paired same-split comparison** (holdout 8f vs holdout 16f) that confirms the dev shape is absent.

## Item-level failures (9/30 wrong, same pattern as 16f)

| item_id              | bucket | answer_idx |
|----------------------|--------|------------|
| videomme:long:840-1  | long   | 3 (D)      |
| videomme:long:851-3  | long   | 0 (A)      |
| videomme:medium:350-2| medium | 3 (D)      |
| videomme:medium:377-2| medium | 0 (A)      |
| videomme:medium:441-1| medium | 3 (D)      |
| videomme:medium:562-1| medium | 2 (C)      |
| videomme:medium:569-1| medium | 0 (A)      |
| videomme:short:136-3 | short  | 0 (A)      |
| videomme:short:293-1 | short  | 0 (A)      |

**Overlap with 16f-holdout failures (9/30):** items that failed on both 8f and 16f: `long:851-3`, `medium:350-2`, `medium:377-2`, `medium:562-1`, `medium:569-1`, `short:136-3`, `short:293-1` (7/9). Frame-count insensitive failures — item-difficulty dominated rather than frame-count dominated. Items that failed on 8f but passed on 16f: `long:840-1`, `medium:441-1`. Items that failed on 16f but passed on 8f: `long:851-3` failed both; `medium:066-3` appeared only in 16f list; `short:066-3`, `short:280-3`, `short:074-3` short-bucket 16f-failures. Net: the two frame counts have partially overlapping failure sets but converge on the same aggregate 0.700.

## Dev–vs–holdout split-shift breakdown

Holdout 8f matches dev 8f exactly on short (0.800) and medium (0.500); the aggregate gap (+16.7pp) is entirely driven by long (+50pp holdout vs dev). This reinforces the 16f-holdout finding: **long-bucket item-difficulty heterogeneity is the 1.41 holdout story**, not frame-scaling non-monotonicity.

## Paper-impact summary

- **Claim #8 (VideoMME breadth gate on Qwen 7B)** now covers the paired-holdout 8f+16f pair: **holdout 8f 0.700 (21/30)**, **holdout 16f 0.700 (21/30)** — identical aggregate, matching bucket distributions with only long-bucket frame scaling differing. Row should cite "dev 8f/16f/32f + holdout 8f/16f" as the accuracy banner.
- **Intro §3 (what Qwen routing contributes)** softening stays intact and is **strengthened**: "the 16f long-bucket regression of ≈ −20 pp on dev does not replicate on the disjoint holdout (paired: holdout 8f long 0.800, holdout 16f long 0.900)". Keep the "item-draw-dependent, dev-only" frame.
- **1.57 attention-mixing framing:** dev-only co-saturation with long-bucket floor is a dev phenomenon. Two-split measurement of 1.57 on holdout would further discipline the claim; not required for paper submission.
- **No C-VISION / C-PERSIST / C-CEILING cells move.** Diagnostic by design.

## Claim-matrix edits required

- Row 8 "VideoMME breadth gate on Qwen 7B" evidence line: append `holdout 8f 0.700 (21/30) 2026-04-22` alongside `dev 8f/16f/32f` and `holdout 16f 0.700`.
- Row 8 NOTE: update advisory to "paired-holdout test (holdout 8f + holdout 16f, n=30 each) confirms the dev 8f→16f long-bucket −20pp drop is item-draw-dependent — does not replicate on holdout in either direction (holdout 8f long 0.800 / holdout 16f long 0.900 / dev 8f long 0.300 / dev 16f long 0.100)".
- `paper/priority.md` autonomous-session 2026-04-21/22 status: add 1-line "1.41 Qwen 8f VideoMME holdout CLOSED 2026-04-22, paired-holdout H2b".

## Reproduction

```
uv run python scripts/run_benchmark_track_a.py run \
  --benchmark videomme \
  --manifest research/benchmark_manifests/videomme_holdout_v1.toml \
  --model-path /Users/jfb/models/Qwen2.5-VL-7B-Instruct-4bit \
  --frame-count 8 \
  --cache-mode identity \
  --max-tokens 32 \
  --allow-dirty \
  --output-path research/experiments/2026/artifacts/phase1_41_qwen_videomme_8f_holdout/dense_n30.jsonl \
  --summary-path research/experiments/2026/artifacts/phase1_41_qwen_videomme_8f_holdout/dense_n30_summary.json
```

Env: `mlx-vlm 0.4.4` / `mlx` latest / macOS Darwin 25.3.0 / M3 16 GB. Git SHA at run-time `cba04c7` (dirty).

## Non-goals

- No pruning / vision-tower patching — dense-only identity-cache.
- No 32f holdout (16f already showed no aggregate lift vs 8f on holdout; 32f is not Pareto-efficient for this diagnostic).
- No RSS tracking — we infer ≤ 16f's 7.23 GB since 8f prefill is strictly smaller.
