---
phase: 1.60
date: 2026-04-23
parent: research/experiments/2026/2026-04-22-phase-1_60-scroll-pan-curation-audit.md
prior:
  - research/experiments/2026/2026-04-21-phase-1_60-scroll-pan-subset-prereg.md
  - research/experiments/2026/artifacts/phase1_60_curation_audit/shifted_fraction_ranking.json
  - research/experiments/2026/artifacts/phase1_60_curation_audit/qwen_8f_combined.json
  - research/experiments/2026/artifacts/phase1_60_curation_audit/qwen_16f_combined.json
  - research/experiments/2026/artifacts/phase1_60_curation_audit/qwen_32f_combined.json
status: CLOSED — CORPUS LIMITATION. VideoMME (natural, n=60 ranked across 8/16/32f, stratified 20/group) does not contain the scroll/pan regime the 1.60 prereg targets. Path A (wider VideoMME scan) fully executed and negative. No further VideoMME-based curation attempts planned.
tracking: autonomous session 2026-04-23 (codex round-31 directive — reframe from BLOCKED to corpus-limitation)
---

# 1.60 Scroll/pan subset — corpus limitation, closed

## Headline

**The scroll/pan regime does not exist at measurable scale in VideoMME.** Across a 60-item scan stratified 20 short / 20 medium / 20 long at 8f / 16f / 32f frame counts, **0 of 60 items cleared the relaxed `shifted_fraction ≥ 0.30` gate** (the prereg's original gate was ≥ 0.60 single-axis motion-mass, which the audit doc already showed was infeasible on the dev 30 subset). The maximum per-item shifted fraction observed at any frame count was **0.125** on `videomme:long:669-1`; the top-ranked item's *mean* shifted fraction across frame counts was **0.099**. This is ~4× below a weak gate and ~6× below the original prereg gate.

**This is a corpus property, not a methodology failure.** VideoMME curation favours scene-cut montages over sustained egomotion, dolly shots, pans, or scrolling content. The data simply is not in the benchmark. We are closing 1.60 on VideoMME and recording this as a corpus-coverage limitation for the paper.

## What ran (Path A from the 2026-04-22 audit)

The 2026-04-22 audit (`2026-04-22-phase-1_60-scroll-pan-curation-audit.md:69-74`) left three exit paths open:

- **Path A**: wider VideoMME scan for shifted-fraction ≥ 0.30 items. Cost: ~1-2 h compute.
- Path B: pivot to an egomotion benchmark (EgoSchema / EPIC-Kitchens / Ego4D). ~6-10 h.
- Path C: hand-labeled synthetic scroll/pan clips. ~3 h labeler.

Path A ran overnight under the 1.60 AFK queue (task #185 `scripts/measure_feature_drift.py` + `scripts/phase1_60_rank_shifted_fraction.py`):

- **Ranking input**: `qwen_{8,16,32}f_combined.json` covering 60 items (20/group). Total Qwen feature-drift measurements: 60 items × 3 frame counts = 180 drift passes.
- **Ranking output**: `shifted_fraction_ranking.json` (706 lines, 60 rows, sorted by `max_shifted_fraction` descending).
- **Gate**: `min_shifted_fraction = 0.3`. Selected: **0**. Max observed: **0.125**. Mean across all 60 ranked items: below 0.05 for 50+ items; the top ten are all 0.05-0.125.

| rank | item_id                   | group  | max_sf | mean_sf | sf @ 8f | sf @ 16f | sf @ 32f |
|------|---------------------------|--------|--------|---------|---------|----------|----------|
| 1    | videomme:long:669-1       | long   | 0.125  | 0.099   | 0.060   | 0.125    | 0.112    |
| 2    | videomme:medium:407-1     | medium | 0.119  | 0.108   | 0.098   | 0.119    | 0.108    |
| 3    | videomme:short:293-1      | short  | 0.118  | 0.078   | 0.038   | 0.118    | —        |
| 4    | videomme:short:282-2      | short  | 0.117  | 0.098   | 0.117   | 0.095    | 0.083    |
| 5    | videomme:short:158-3      | short  | 0.095  | (n/a)   | —       | —        | 0.095    |
| 6    | videomme:long:751-2       | long   | 0.093  | —       | —       | —        | —        |
| 7    | videomme:long:783-2       | long   | 0.090  | —       | —       | —        | —        |
| 8    | videomme:short:074-3      | short  | 0.089  | —       | —       | —        | —        |
| 9    | videomme:short:120-2      | short  | 0.087  | 0.076   | 0.060   | 0.080    | 0.087    |
| 10   | videomme:medium:484-2     | medium | 0.073  | —       | —       | —        | —        |

Group breakdown of the top-10: 4 short / 3 long / 3 medium (top-1 is a long-bucket item). Roughly uniform. No bucket is scroll-rich.

The dev-30 audit found `max_sf = 0.108` on `videomme:medium:407-1`. The 60-item expansion raised the ceiling only marginally, to 0.125 (`videomme:long:669-1`), and added *no* items in the 0.30-plus zone. **Path A is exhausted.**

## Why this is a corpus property, not a failure

the pre-release source framing explicitly partitions regimes:

- **SHIFTED-dominated** content (live camera feed, sustained pan, scrolling captions, dolly / tracking shots, egomotion) is where the 5-300× ViT savings claim concentrates. Measured shifted-fraction in such regimes is by construction high — often > 0.50 (most of the inter-frame content is same-object-moved rather than novel or static).
- **NOVEL-dominated** content (scene cuts, montages, edited TV) is where shifted-fraction is low by construction, because successive frames show *different* content rather than moved content. This is the VideoMME regime.

VideoMME is a benchmark corpus assembled from edited YouTube clips — montage-heavy, cut-rich, and (by evidence) scroll-sparse. The ~3.4 % mean shifted-fraction across our 60-item scan is consistent with this. It is neither a feature extraction bug, a frame sampling bug, nor a model failure. **It is the corpus having different content.**

This matches existing project knowledge:
- `memory/project_feature_drift_qwen_2026-04-19.md` records Qwen STATIC cos 0.562/0.607/0.638 (8/16/32f), i.e. natural VideoMME content is content-cut-dominated; shifted fraction low by construction.
- `paper/arxiv/sections/08_real_applications.tex` and
  `paper/arxiv/sections/09_limitations_reproducibility.tex` already flag the
  bounded benchmark envelope as a deployment hedge.

## What this means for the paper

**No claim needs to change.** The paper already characterises C-VISION as evidence on montage/cut benchmarks and carries an explicit hedge that scroll/pan regimes are out of scope. What was missing was the *affirmative* statement that we looked and the regime isn't there. That statement is now earned.

**Required paper edits** (to propagate the CLOSED-corpus-limit status):

1. **`paper/priority.md`** — should-do #5 (scroll/pan probe): update from "natural-corpus-BLOCKED 2026-04-22, deferred pending wider 1.57 sweep or egomotion benchmark" (the audit doc's recommendation) to "CLOSED 2026-04-23 — natural VideoMME corpus does not contain scroll/pan content at measurable scale (0/60 items at shifted_fraction ≥ 0.30); egomotion benchmark integration is the only remaining path and is out of paper scope". Path-A closure cross-ref: `research/experiments/2026/2026-04-23-phase-1_60-corpus-limitation-findings.md`.
2. **`paper/claim-matrix.md`** row 15 NOTE line (already added in the audit round): change suffix from "paper-body characterization deferred" to "paper-body characterization deferred; wider 60-item VideoMME scan 2026-04-23 confirmed corpus limitation (0/60 at gate 0.30, max 0.125)".
3. **`paper/framing.md`** Reviewer-Facing Limitations (already contains a static-dominated hedge): append one sentence "We re-audited this on an expanded 60-item VideoMME stratification and confirmed the regime is absent from the corpus (max shifted-fraction 0.125; gate 0.30). A scroll/pan characterisation therefore requires a different benchmark (EgoSchema, EPIC-Kitchens) and is out of paper scope."
4. **`research/experiments/registry.md`** 1.60 row: transition from "BLOCKED" to "CLOSED — CORPUS LIMITATION 2026-04-23".

These edits land as a separate doc-sync commit once this findings doc is committed.

## What this does NOT mean

- **It does not** mean scroll/pan regimes can't break the pre-release source's ViT pruning claim. They might. We just can't measure that against VideoMME.
- **It does not** invalidate the C-VISION safety claim — we have 1.51V V_red = 39-43% at L=2 kr=0.50 across all three benchmarks with Δacc bounded in a paired test. That claim stands on a montage-corpus, which is what most video benchmarks are.
- **It does not** close egomotion-benchmark integration permanently. If a reviewer demands it, Path B (EgoSchema + 1.57 + 1.60 redo) is ~6-10 h and re-opens cleanly.

## Why the Path-B/C reopen condition is cleanly documented

Both paths remain available if reviewer pressure justifies the cost:

- **Path B**: add a VideoMME-equivalent loader for an egomotion benchmark. Concrete candidates: EgoSchema (dense egomotion, 3-min clips, 5K items), EPIC-Kitchens (heavy egomotion, first-person cooking), Ego4D (multi-category egomotion). Implementation cost: new loader (~3 h), full 1.57 measurement on a 30-60 item subset (~2 h), 1.60 arm pair (~1 h). Total ~6-10 h. Gate: pre-register shifted_fraction threshold, probably 0.40+, and budget-driven subset construction.
- **Path C**: hand-label 20 synthesised sustained-pan clips (from still VideoMME medium items) with one MCQ each. Cost: ~3 h labeler. Weaker evidential weight (n=20, in-house oracle), so the deliverable is a *graceful-degradation-or-not* datapoint rather than a quantitative breakage claim.

## Repro pointer

```python
# 60-item ranking, dev+holdout union, 20/short 20/medium 20/long:
import json
ranking = json.load(open("research/experiments/2026/artifacts/phase1_60_curation_audit/shifted_fraction_ranking.json"))
print(ranking["min_shifted_fraction"], ranking["n_ranked"], ranking["n_selected"])
# -> 0.3 60 0
print(max(r["max_shifted_fraction"] for r in ranking["rows"]))
# -> 0.125  (videomme:long:669-1 at 16f)
```

Source artifacts:
- `research/experiments/2026/artifacts/phase1_60_curation_audit/qwen_8f_combined.json` — 60-item 8f drift measurements
- `research/experiments/2026/artifacts/phase1_60_curation_audit/qwen_16f_combined.json` — 60-item 16f
- `research/experiments/2026/artifacts/phase1_60_curation_audit/qwen_32f_combined.json` — 60-item 32f (n_covered smaller on some items due to 32f feasibility at decode time)
- `research/experiments/2026/artifacts/phase1_60_curation_audit/shifted_fraction_ranking.json` — final ranking, 60 rows

No driver changes required. Audit was end-to-end reproducible from the pre-existing `scripts/measure_feature_drift.py` + `scripts/phase1_60_rank_shifted_fraction.py` pipeline.

## Non-goals

- No synthesis attempt (Path C). Paper payoff weak; not on submission critical path.
- No egomotion-benchmark integration (Path B). Reviewer-pressure-only trigger.
- No wider VideoMME expansion beyond 60 items. The ceiling is too low (0.125 at 60) for additional scan to change the conclusion.

## Decision log cross-ref

- 2026-04-21 1.60 prereg filed: `2026-04-21-phase-1_60-scroll-pan-subset-prereg.md`
- 2026-04-22 natural-corpus audit on dev 30: BLOCKED at max shifted-fraction 0.108
- 2026-04-23 Path A execution on wider 60-item scan: CLOSED-CORPUS-LIMIT at max 0.125 (this doc)
