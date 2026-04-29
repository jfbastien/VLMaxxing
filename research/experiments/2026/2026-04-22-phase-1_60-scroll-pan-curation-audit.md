---
phase: 1.60
date: 2026-04-22
parent: research/experiments/2026/2026-04-21-phase-1_60-scroll-pan-subset-prereg.md
prior:
  - research/experiments/2026/artifacts/phase1_57/qwen_8f_dev30.json
  - research/experiments/2026/artifacts/phase1_57/qwen_16f_dev30.json
  - research/experiments/2026/artifacts/phase1_57/qwen_32f_dev30.json
status: BLOCKED — natural VideoMME dev items cap at shifted_fraction = 0.108 (well below prereg's >60% single-axis motion threshold); synthesis fallback requires MCQ-question generation (not in repo). Deferred pending either (a) a larger VideoMME sweep that turns up scroll-dominated clips, (b) a different benchmark with egomotion content, or (c) a teacher-VLM MCQ generator.
tracking: autonomous session 2026-04-21/22 dynamic-loop
---

# 1.60 Scroll/Pan subset — curation audit (BLOCKED)

## Headline

The prereg called for 20 items stratified 7 light / 7 medium / 6 heavy by scroll intensity, where "heavy" means > 60 % of inter-frame motion concentrated in a single spatial axis (vertical scroll or horizontal pan). After scanning Phase 1.57's STATIC/SHIFTED/NOVEL decomposition across the full VideoMME dev 30-item subset at three frame counts (8f, 16f, 32f), **zero items qualify as heavy scroll** and **no items qualify as medium scroll either**: the maximum per-item shifted fraction observed across any frame count is **0.108** on `videomme:medium:407-1`, an order of magnitude below the 0.60 gate.

The synthesis fallback (prereg §"Subset construction" step 2) calls for augmenting 10 natural items with 10 synthetic sustained-pan clips derived from still VideoMME medium items — but this requires producing VideoMME-format multi-choice QA pairs (question + 4 options + correct answer) for each synthetic clip, which the existing `scripts/generate_synthetic_corpus.py` does not do (it generates 320×240 pan clips for feature-drift calibration, not benchmark items with ground-truth answers).

**Decision:** mark 1.60 BLOCKED on curation. Paper narrative for C-VISION deployment envelope will continue to carry the operating-point caveat without the scroll/pan breakage number; the prereg's three alternative exit branches (CLEAN FAILURE CLAIM / BROKEN DEPLOYMENT CLAIM / SHIFTED-DOES-NOT-BREAK) remain open.

## Shifted-fraction distribution across VideoMME dev 30

Per-item `shifted / (novel + shifted + static)` ratio from Phase 1.57 artifacts (same 30-item subset across frame counts):

| rank | item_id                   | group  | mean_sf | sf @ 8f | sf @ 16f | sf @ 32f |
|------|---------------------------|--------|---------|---------|----------|----------|
| 1    | videomme:medium:407-1     | medium | 0.108   | 0.098   | 0.118    | 0.108    |
| 2    | videomme:long:669-1       | long   | 0.099   | 0.060   | 0.125    | 0.112    |
| 3    | videomme:short:282-2      | short  | 0.098   | 0.117   | 0.095    | 0.083    |
| 4    | videomme:short:120-2      | short  | 0.076   | 0.060   | 0.080    | 0.087    |
| 5    | videomme:medium:484-2     | medium | 0.070   | 0.066   | 0.072    | 0.073    |
| 6    | videomme:medium:486-2     | medium | 0.057   | 0.049   | 0.051    | 0.071    |
| 7    | videomme:short:158-3      | short  | 0.053   | 0.019   | 0.046    | 0.095    |
| 8    | videomme:medium:380-3     | medium | 0.048   | 0.046   | 0.043    | 0.055    |
| 9    | videomme:short:160-1      | short  | 0.041   | 0.030   | 0.035    | 0.058    |
| 10   | videomme:short:100-2      | short  | 0.027   | 0.047   | 0.015    | 0.020    |
| 11-30| (remaining 20 items)      | mixed  | < 0.026 | —       | —        | —        |

- Prereg gate: ≥ 0.60 single-axis motion-mass — **none of 30 qualifies**
- Even relaxing to total shifted-fraction ≥ 0.20 (broader "camera-moving-somehow" proxy) yields **0 items**
- The most scroll-biased item (medium:407-1 at 0.108) has shifted roughly 1 in 10 tokens of its `n_pairs = 7` inter-frame pairs — a far cry from "scroll dominates".

Group distribution among the top 10 shifted-fraction items: 4 short, 5 medium, 1 long. No systematic bucket concentration.

## Why natural VideoMME lacks scroll/pan

VideoMME's corpus curation favours **scene-composition variety**: most clips are montages of static shots with cuts (giving high `novel` and `static` fractions, low `shifted`). Genuine sustained camera motion — TV pans, scrolling captions, dolly shots, egomotion — is rare in the 900-video corpus and vanishingly rare in our 57-video dev subset.

This is also consistent with the pre-release source §SHIFTED framing: SHIFTED content dominates **live-camera** regimes (the 5-300× ViT savings end of that report) and is structurally narrow on benchmark corpora. VideoMME is a benchmark corpus; the absence of scroll-heavy items is a feature of the corpus, not a methodology bug.

## Synthesis fallback — why it is not trivial

The prereg §"Subset construction" step 2 proposes:

> if (1) does not yield ≥ 20 items, synthesize by applying a constant-velocity crop over 5 still VideoMME medium-bucket items (2-second sustained pan) for 10 synthetic items, and combine with 10 natural items.

Three gaps:

1. **MCQ authoring.** Each benchmark item carries a question and 4 answer options. A 2-second sustained pan across a still image does not carry a ground-truth answer; we cannot compare "answer correct" without fabricating one. A teacher VLM (e.g. Qwen 2.5-VL 72B or GPT-4V-class) could be prompted to generate a Q and A, but we do not have one in the local stack and downloading is out of scope.
2. **Loader integration.** Our VideoMME loader resolves `videomme:<bucket>:<id>-<option>` from a manifest with a fixed Parquet schema; synthetic items would require a parallel "manifest ↔ file" shim or a new synthetic-items loader.
3. **Ground-truth calibration.** Even if we synthesize Q/A pairs, we have no second independent oracle; degradation Δacc would be measured against our own teacher — circular.

Fixing any of these is a 4-8 h engineering effort with uncertain paper payoff (the result would be an adverse or graceful-degradation datapoint on a synthetic corpus, carrying weaker evidential weight than a natural-corpus result).

## Recommendation

Mark 1.60 **deferred, not abandoned**. Three clean unblock paths exist:

- **Path A**: scan a larger VideoMME slice (beyond the 57-video dev subset, or using the full 900-video corpus) and look for clips with shifted-fraction > 0.30. If ≥ 20 qualifying items exist, restart 1.60 against them. Cost: 1.57 measurement run over a wider subset (~1-2 h compute; no code).
- **Path B**: use a different benchmark with known egomotion content (EgoSchema, EPIC-Kitchens, Ego4D). Requires new loader + 1.57 measurement + full 1.60 arm pair. ~6-10 h.
- **Path C**: downstream the MCQ-authoring problem by hand-labeling 20 synthesized clips with one question each. ~3 h labeler work, no code. Result carries weaker statistical weight (n = 20 hand-labels vs thousands of benchmark items) but unblocks the paper row.

None of the three is on the critical path for paper submission. The C-VISION claim already has deployment-envelope hedging ("three benchmark corpora, mostly static content, scroll/pan regime characterization is future work"). A reviewer demanding an empirical scroll/pan number is reasonable but not fatal; the defer is principled.

## Claim-matrix / priority edits required

- `paper/priority.md` **should-do #5 (scroll/pan probe)**: update from "prereg'd, queued after EXP10" to "prereg'd, natural-corpus-BLOCKED 2026-04-22, deferred pending wider 1.57 sweep or egomotion benchmark".
- `paper/claim-matrix.md` row 15 NOTE line: append "scroll/pan boundary: natural VideoMME dev-30 does not contain scroll-dominated clips (max shifted_fraction = 0.108; prereg gate ≥ 0.60). Paper-body characterization deferred".
- `paper/framing.md` Reviewer-Facing Limitations: add one sentence "the three benchmark corpora we test (VideoMME, MVBench, TOMATO) are structurally static-dominated; scroll/pan / egomotion regimes are deferred to future work pending a corpus with sustained camera motion".

## Reproduction

The shifted-fraction ranking used by this audit:

```python
import json

items_by_id = {}
for fc in [8, 16, 32]:
    p = f'research/experiments/2026/artifacts/phase1_57/qwen_{fc}f_dev30.json'
    d = json.load(open(p))
    for item in d['per_item']:
        iid = item['item_id']
        cc = item['class_counts']
        total = cc['novel'] + cc['shifted'] + cc['static']
        sf = cc['shifted'] / total if total > 0 else 0.0
        items_by_id.setdefault(iid, {'group': item['group'], 'shifted': {}})
        items_by_id[iid]['shifted'][fc] = sf

rows = []
for iid, rec in items_by_id.items():
    sf_mean = sum(rec['shifted'].values()) / len(rec['shifted'])
    rows.append((iid, rec['group'], sf_mean))
rows.sort(key=lambda r: -r[2])
for r in rows:
    print(r)
```

Max shifted_fraction across all 30 items × 3 frame counts: **0.125** (videomme:long:669-1 at 16f).
Mean shifted_fraction across dev: **0.034** (roughly 3.4% of inter-frame pairs are same-content-moved).

## Non-goals

- **No synthesis attempt.** The MCQ gap alone justifies deferral.
- **No larger VideoMME sweep.** The 57-video dev subset is what we have; expanding needs a new fetch + 1.57 re-run.
- **No synthesis pipeline coding.** 4-8 h with weak paper payoff on current priorities.

## What unblocks this

Any one of:

1. Phase 1.57 run over a wider VideoMME slice (≥ 200 items) that surfaces ≥ 20 items with `shifted_fraction ≥ 0.30`.
2. An EgoSchema / EPIC-Kitchens benchmark integration.
3. A hand-labeled 20-item synthetic scroll-pan corpus with one MCQ per clip.
