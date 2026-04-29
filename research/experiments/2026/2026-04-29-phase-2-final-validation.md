---
date: 2026-04-29
status: phase-2 chain validated and ready to launch after second-round Codex hardening (commit 83a6fb6)
related:
  - research/experiments/2026/2026-04-29-phase-2-launch-ready.md
  - research/experiments/2026/2026-04-29-phase-2-codex-review.md
---

# Phase 2 — final validation before launch

After the second-round Codex review flagged six issues (executable bit, RSS guard default, A6 turn-zero dilution, A5 capture floor, A6/A7 missing completeness gates, A7 stale-file glob), Codex landed fix 83a6fb6. Three sub-agent audits plus direct inspection verify every fix.

## Verified fixes

| Issue | Fix | Verified by |
|---|---|---|
| 1.62D shell exec bit | all 7 wrappers chmod 755 | `ls -la scripts/run_phase1_*.sh` |
| RSS_GUARD_MB default | A3/A4/A6/A7 default 12000 (env override works) | `grep RSS_GUARD_MB scripts/run_phase1_*.sh` |
| A6 turn-zero dilution | `followup_rows` excludes `turn_index > 0`; `post_repair_rows` filters on `cache_source == "post_previous_repaired"` | sub-agent A6-followup audit |
| A5 capture floor | `capture_row_floor = 20` + `n_unique_followup_rows ≥ 20` | direct inspection 1.30AG.py:593-598 |
| A6/A7 chain gates | A6: 5 pass_complete_* (rows, cells, chains, turns, grid); A7: 2 (grid, row_counts) | dry-run output |
| A7 stale-file pollution | summarizer uses explicit seeds/temps list, records `unexpected_seed_summaries_ignored` | sub-agent A7-grid audit |

## Verified extras (Codex did more than asked)

- **Chain reorder**: A1, A2, A3, A4, A6, A7, A5 (A5 last). Verified by `--dry-run` step name order.
- **1.30AG try/finally**: `_full_prompt_cache(pruned)` wrapped; restores `keep_rate=1.0` on any exception. Earlier audit's only remaining P1 is now closed.
- **OSError handling**: chain runner catches OSError (FileNotFoundError, PermissionError, NotADirectoryError) on subprocess launch; ordered after CalledProcessError to avoid shadowing.
- **1.55L summary-only validator** at `scripts/validate_phase1_55l_summary.py` imports only argparse/json/pathlib — no MLX, no Metal sandbox crash risk.

## Design philosophy I endorse

The chain runner's `required_gates` for A6 are 5 *structural* completeness gates (row counts, cells, chain counts, turn coverage, policy×horizon grid), not drift gates. This is intentional: the chain should fail-close on bad infrastructure (script crashed, cells missing) but not on bad-but-valid science (high drift is itself a publishable finding). Drift outcomes go in the summary's `pass_three_percent_drift_*` keys for paper interpretation, but they don't gate the chain.

The same philosophy applies to A4: `complete = all(pass_complete_pairing && pass_format)` not `all_gates_pass`. A confirmed low-gain envelope is a valid landing.

## One scoping deviation worth noting

A7 uses 3 seeds × 3 temps (42, 99, 2026) × (0.5, 1.0, 1.5) = 9 cells, vs my Phase 2 design proposal of 3 × 5 temps. Tighter than I proposed but defensible: covers the temperatures where the original 1.55K showed any non-zero drift (T=0.0 was perfectly stable; T=0.7 was already tested with the same drift signature as T=1.0). The user should know it's 9 cells × ~50 min ≈ 7.5h, not the original 5h estimate I made. Acceptable.

## Worktree status

- Branch: `main`, ahead of origin by 1 commit (this peer-review work since the last Codex commit).
- `git status`: clean.
- Disk: 134 GB free.

## Launch command

```bash
nohup ./.venv/bin/python scripts/run_phase2_local_chain.py \
  --auto-commit --continue-on-failure \
  > /tmp/claude/phase2_local_chain.log 2>&1 &
```

with `dangerouslyDisableSandbox: true` for Metal access (CVE-2026-28834 mitigation in 12 GB MLX cap; same precedent as the deep-mechanism queue).

## ETA (with the new chain order)

| Step | Hours | Notes |
|---|---|---|
| A1 1.63G format diagnostic | <1 min | already landed; rerun is cheap |
| A2 1.65v2 richer predictor | <1 min | already landed; rerun is cheap |
| A3 1.62D low-FPS dense | ~3.5 | new |
| A4 1.63I Qwen kr fine-bracket | ~9 | new |
| A6 1.55L many-turn | ~8 | new |
| A7 1.55K-extended seeds | ~7.5 | new |
| A5 1.30AG cache-distance | ~2 | new (last; reordered to not block A6/A7) |
| **Total** | **~30** |  |

## What I'm watching

1. A6 50-turn cell timing — cache state at turn 50 unverified.
2. A4 kr-sweep cells 0.78–0.82 should run faster than 0.50 (less aggressive prune); should fit in 9h budget.
3. A5 H1 may legitimately fail on V-prune length mismatch — that's a valid scientific outcome, not a runtime failure. With `--continue-on-failure` and A5 last, this doesn't block anything.

## I am confident this can run autonomously.

All six issues from the second-round review are fixed, all framing concerns are addressed, the chain is restructured so A5's likely partial failure doesn't kill higher-value science, and the runner has solid fail-closed semantics.

Launching now.
