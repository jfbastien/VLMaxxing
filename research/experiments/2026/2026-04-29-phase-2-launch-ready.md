---
date: 2026-04-29
status: phase-2 chain verified launch-ready after Codex fix at 7c8d002
related:
  - research/experiments/2026/2026-04-29-phase-2-codex-review.md
  - research/experiments/2026/2026-04-29-phase-2-experiment-design.md
---

# Phase 2 — launch verification (post-fix)

After my peer review (3df0bfb) flagged P0 issues in A5 (1.30AG) and a P1 leakage caveat in A2 (1.65v2), Codex landed fix commit 7c8d002 addressing every concern. A focused sub-agent re-audit verifies all three P0 fixes are correct and the prereg is aligned with the code.

## P0 verification — 1.30AG cache-distance probe

| Issue | Audit fix | Verification |
|---|---|---|
| P0-1 zero-padded buffer | use `entry.offset` valid window | `_cache_window` slices `keys[..., :offset, :]`; `_distance_for_windows` operates on sliced tensors. |
| P0-2 length mismatch crash | non-fatal, record mismatch | `same_valid_token_length` recorded per layer; `pass_H1_capture` ANDs `same_valid_lengths`; H4 short-circuits if H1 fails. |
| P0-3 H4 metric mismatch | use `1 - cosine` not `mean_abs` | `keys_cosine_distance_gap` / `values_cosine_distance_gap` drive `pass_H4_saturation_test`; `mean_abs` retained as diagnostic only. |

Prereg lines 50-56, 62-63, 68-71 now explicitly require valid-offset windows, token-length parity, and `1 - cosine` distance — matches the code.

## P1 framing verifications

- **1.65v2** artifact emits `top_second_gap_vs_dense_answer_margin` metadata with `exact_match_fraction=1.0, max_abs_difference=0.0, n=228` — empirical evidence that on this artifact `top_second_gap == dense_answer_margin`. The label-free vs oracle distinction is now machine-readable.
- **1.55L** design doc adds explicit "Findings-doc requirement" block: 1.55L must be reported as a **stateless same-video cache-horizon stress test**, not a many-turn conversation.
- **paper-update-notes-v2** adopts boundary-evidence framing: "matched parse-failure caveats" for Gemma, "fidelity-safe but low-gain" for Qwen kr=0.85, "MLX cap mitigated panics; observed peaks reached 13.61 GB" for memory.

## Remaining P1 (acceptable, not blocking)

- 1.30AG `_full_prompt_cache(pruned)` not wrapped in try/finally; if it raises, model is left in `keep_rate=0.50`. Audit notes the next iteration's `_full_prompt_cache(dense)` resets `keep_rate=1.0`, so the bug only manifests if exception escapes the outer loop. Don't block; flag for a follow-up fix if 1.30AG runs cleanly.

## Launch plan

- **Codex's recommendation** (post-fix): run the chain normally fail-closed; use `--continue-on-failure` only if I want A6/A7 to proceed even when A5 reveals non-comparable cache lengths.
- **My recommendation**: launch with `--auto-commit --continue-on-failure`. Reasons: A5 may legitimately report `pass_H1_capture=False` due to V-pruning length mismatch (a valid scientific outcome), and we shouldn't block A6/A7 on that. The fail-closed default would treat it as failure-to-run.

## Launch command

```bash
nohup ./.venv/bin/python scripts/run_phase2_local_chain.py \
  --auto-commit --continue-on-failure \
  > /tmp/claude/phase2_local_chain.log 2>&1 &
```

with `dangerouslyDisableSandbox: true` per the deep-mechanism queue precedent (CVE-2026-28834-class GPU race; Metal init blocked by sandbox).

## ETA

| Step | Hours |
|---|---|
| A1 (already landed) | <1 min |
| A2 (already landed) | <1 min |
| A3 1.62D low-FPS | ~3.5h |
| A4 1.63I Qwen kr fine-bracket | ~9h |
| A5 1.30AG cache-distance | ~2h |
| A6 1.55L many-turn | ~8h |
| A7 1.55K extended seeds | ~7.5h |
| **Total local chain** | **~30h** |

## Post-chain manual steps

1. Manually commit findings docs that land outside `step.artifact_paths` (chain runner doesn't auto-commit those).
2. Update 1.55L findings doc to use "stateless cache-horizon" framing (Codex's design doc requires this).
3. Update 1.65v2 doc if needed (already updated by Codex).
4. Optionally write a chain-completion summary doc.

## Why I'm confident I can run autonomously

1. The chain runner has fail-closed default with explicit `--continue-on-failure` opt-in. Status records persist to `phase2_local_chain_status.json` after every step.
2. Per-step timeouts prevent runaway processes.
3. Auto-commit is per-step; no failed step pollutes the artifact tree (unless `--commit-failed-artifacts` is set, which I'm not using).
4. CVE-2026-28834 mitigation is in place (12 GB MLX cap on every MLX-using script).
5. The failure modes I've already handled in production (kernel panic mid-queue, MLX init in sandbox, restart from `--start-at`) are all covered.

## Things I'm watching

1. **A5 may take longer than 2h** if the deterministic 20-row subset has many length-mismatch rows that require scientific interpretation but pass H1 (impossible per the new gate logic — H1 fails on any mismatch, H4 short-circuits, chain continues with `--continue-on-failure`).
2. **A6 50-turn cell** has unknown timing properties — cache state at turn 50 may behave differently than at turn 3. The wrapper has a 14h timeout; if it hits, partial data still lands.
3. **A4 9h estimate** assumes kr-sweep cells run at the same rate as 1.63H. The kr=0.78–0.82 cells should be faster than kr=0.50 (less aggressive pruning means closer to dense, but also less compute saving).
