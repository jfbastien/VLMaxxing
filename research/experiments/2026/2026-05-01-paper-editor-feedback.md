---
date: 2026-05-01
phase: paper-editor-feedback (cumulative recommendations from 2026-04-30 chain results + codex review + sub-agent audits)
status: research-side feedback only; the manuscript edits live in paper/arxiv/sections/ and are owned by the paper editor
---

# Paper editor feedback — 2026-05-01

This file is a structured, cite-able set of recommendations for the paper editor. The research thread does not edit the manuscript directly; everything below is delta-style, with quoted current text where applicable, suggested replacement text, and the artifact / commit that backs the suggestion.

## P0 — wording corrections that should land before the next external review

### (1) A6 many-turn C-PERSIST: drop "expected late leakage"

**Current text** (`paper/arxiv/sections/07_results_cross_architecture.tex` ~line 257-258 in the post-481e863 version, line numbers may have drifted):

> "Fixed K=1 remains below the 3% drift gate but shows the expected late leakage: 3/343 choice diffs and 2/343 correctness diffs."

**Why this is misleading.** The horizon=50 follow-up bucket data (in `research/experiments/2026/artifacts/phase1_55L_many_turn_cpersist/summary.json`, `cells[].followup_turn_buckets` for `policy=fixed_k1, horizon=50`) shows the 5 drift events are spread, not late-concentrated:

| turn bucket | n | choice diffs | correctness diffs |
|---|---|---|---|
| 0–10 | 63 | 1 | 1 |
| 10–20 | 70 | 1 | 1 |
| 20–30 | 70 | 0 | 0 |
| 30–40 | 70 | 1 | 0 |
| 40–50 | 70 | 0 | 0 |

The latest two buckets (30–40, 40–50) carry less drift than the first two. "Late" suggests a temporal monotonic increase the data does not show.

**Suggested replacement** (one-line edit):

> "Fixed K=1 stays below the 3% drift gate at the 50-turn horizon but accumulates 3/343 choice diffs and 2/343 correctness diffs spread across the schedule (0–10, 10–20, 30–40 buckets), not concentrated at the latest turns."

Alternative if the editor prefers a shorter rewrite that keeps the "long-horizon" framing:

> "Fixed K=1 stays below the 3% drift gate but shows the expected long-horizon leakage: 3/343 choice diffs and 2/343 correctness diffs accumulate across the 50-turn run."

### (2) Upstream mlx-vlm SWA-trim status — already corrected

The fa1708c cherry-pick (commit `254b281`) updated `research/experiments/2026/2026-04-30-phase-upstream-mlx-vlm-swa-aware-trim-findings.md` to "full-regression verified". No further paper edit needed unless the editor wants to surface this in section 9 (limitations / reproducibility); a sentence like "the upstream mlx-vlm topology-aware trim patch is now full-regression verified against B0b 42/42 paired rows" would close the residual `§9` reproducibility note.

### (3) B4 row in `scaleout_bundle_status.tex` — needs a context note

**Current generated text** (`paper/arxiv/generated/tables/scaleout_bundle_status.tex`):

> B4 row: "choice/correct 0/10 ... pass=true"

**Why this misleads readers.** B4 (sam_track_b_hard_prune) is a descriptive / post-ViT hard-prune diagnostic. It does not have ground-truth multiple-choice rows in the same sense that B0b does. A reader scanning the bundle table will read "0/10" as "this row is paper-grade correctness evidence" when it is not.

**Suggested fix** — add a `\caption{}` footnote in the generator (`paper/arxiv/scripts/sync_sources.py`) and the inline table comment:

> "B4 is descriptive (post-ViT hard-prune ablation), not ground-truth correctness evidence; the 0/10 figure is a diagnostic-arm count, not a paired-drift count comparable to B0b."

The text-side edit is one paragraph in `paper/arxiv/sections/08_real_applications.tex` clarifying which scale-out bundle rows are paper-body claim-bearing (B0b is, B4 is not).

### (4) C-STREAM remains a candidate, not a 4th headline (conditional path noted below)

**Current state** of `paper/framing.md`, `paper/publishability-status.md`, `paper/arxiv/sections/08_real_applications.tex`: C-STREAM is described as "candidate / mixed bundle, not pending and not a fourth headline." That framing is correct on the current evidence and should stay.

**Why current evidence is not enough**, with citations:
- Phase 1.30 family (Qwen session/streaming) is a falsified accuracy gate (Δacc=−0.193 vs ±0.05 budget); 1.30W repair Δacc=−0.0585 at 2.79× still misses the 3.0× floor.
- Sam Phase B3 (`research/experiments/2026/2026-04-29-phase-B3-sam-streaming-baselines-findings.md`) shows `low_fps_dense` 17/22 (77.3%) vs `sam_policy` 13/22 (59.1%) — i.e. the trivial baseline currently beats the streaming arm at matched evidence.
- 1.60 scroll/pan closed null on VideoMME for lack of regime coverage.
- M5-5b/M5-comp prefix-snapshot speedups (9.11×/26.59×) are per-follow-up after the cache is warm, not setup-inclusive session speedups, and only 5/21 rows are ground-truth multiple-choice.

**Conditional path to 4th headline** — see §"Optional new experiment: C-STREAM throughput-axis closure" in the research-side experiment plan (this same date). Summary: the achievable headline is *not* "we beat baselines at matched evidence accuracy" (twice falsified) but **C-STREAM = ingestion-density anti-recomputation**, where the headline number is the per-frame ViT-fire reduction at matched accuracy, not an accuracy lift. If the throughput-axis experiment (~20-32 h on M3 16 GB) lands clean against `low_fps_dense` / `screenshot_polling` / `recency_last_K` with ≥40 ground-truth MC rows and a stale-cache failure case included, the contribution can promote.

## P1 — manuscript hygiene that should land alongside paper-build

### (5) Provenance regen before any external release

The current generated provenance (`paper/arxiv/generated/data/build_meta.tex`, `paper/arxiv/generated/tables/repo_provenance.tex` — both gitignored) reflects the dirty worktree the most recent paper PDF was built from. The editor's notes already flag this. Regenerate from a clean tag before submission.

### (6) §9 reproducibility — note the seed/ archive

`docs/reproduction-status.md` carries a "Raw seed files are not kept in the release tree. Git history preserves them." line that pre-dates the `seed/` working-tree archive being explicitly gitignored. The current statement is accurate (seed/ is not in the public release surface), but a one-line clarification would help OSS readers: "The `seed/` working tree contains the predecessor pre-release source artifacts as private inspiration material; it is gitignored and intentionally excluded from the OSS release. Predecessor reproduction is therefore an import-only reference, not a runnable lane in this repo."

### (7) §8 wording on Sam scale-out 26B numbers — denominator caveat

Current text in `paper/arxiv/sections/08_real_applications.tex` cites the M5-5b 9.11× and M5-comp 26.59× numbers as cross-arch C-PERSIST evidence. The numbers are correct, but they are per-follow-up and post-warm-up. A one-line footnote or in-paragraph clarification — "per-follow-up after the prefix snapshot is warm, not setup-inclusive session speedups" — would prevent reviewers from reading them as session-level multipliers.

## P2 — research-side updates (already landed, listed for editor awareness)

These do not require paper edits but the editor should know they exist:

- **A7 sampler-robustness** integrated into §7 in commit `1dd07db` with the new generated `c_persist_sampler_seed_sweep.tex` table.
- **A6 raw artifacts + status** committed by chain runner; the existing §7 paragraph already cites them.
- **fa1708c (B0b unguarded under upstream patch)** cherry-picked in `254b281`; updates `research/experiments/2026/2026-04-30-phase-upstream-mlx-vlm-swa-aware-trim-findings.md` from "smoke-verified candidate" to "full-regression verified."
- **A5 (1.30AG cache-distance probe) diagnosis retracted** in `ef7b7da`; the previous "cache contains NaN/Inf" claim was mathematically weak. New diagnosis: "candidate pending finite audit." Finite-audit telemetry patch landed in `6cc5d32`; sandbox-off rerun in flight as of this writing. This is mechanism instrumentation, not paper claim-bearing.
- **`seed/` private archive** gitignored in `8f5aa6f`. Not paper-body content.

## What the editor should NOT do (yet)

- **Do not promote C-STREAM** to 4th headline on current evidence. Confidence per agent audit is low-to-medium; the matched-evidence regime still favors `low_fps_dense`. If the throughput-axis experiment closes cleanly with ≥40 paired MC rows, revisit.
- **Do not re-promote** Phase 1.34 / 1.36 / 1.50 from the LOCAL DIAGNOSTIC demotion. Those rows reference `results/feature_change_oracle/` and similar gitignored paths; the `seed/original_repo/results/` predecessor JSONs are *different* artifacts and do not unblock those rows. A successor audit doc + claim-matrix update would be a separate decision.
- **Do not edit `08_real_applications.tex` for B4** until the `sync_sources.py` generator is updated, otherwise the next `make paper-sync` will revert hand edits to that table.

## Cross-references

- `paper/arxiv/sections/07_results_cross_architecture.tex` (C-PERSIST + sampler robustness)
- `paper/arxiv/sections/08_real_applications.tex` (C-STREAM + Sam scale-out)
- `paper/arxiv/sections/09_limitations_reproducibility.tex` (upstream-patch + provenance notes)
- `paper/arxiv/scripts/sync_sources.py` (generator for B4 row + sampler-seed-sweep table)
- `paper/claim-matrix.md` (claim 14 C-PERSIST, 15 C-VISION, 13 C-CEILING; C-STREAM is a candidate)
- `paper/framing.md` (currently four contributions: 3 headlines + 1 candidate)
- `paper/publishability-status.md` (status snapshot; mentions C-STREAM as bundled mixed evidence)
