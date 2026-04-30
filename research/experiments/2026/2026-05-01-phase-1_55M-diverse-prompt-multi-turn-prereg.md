---
date: 2026-05-01
phase: 1.55M (diverse-prompt multi-turn C-PERSIST stress)
status: PREREG. Requires either a small A6-driver patch (per-turn prompt-prefix templating) OR a curated natural-dialogue corpus.
related:
  - 2026-04-29-phase-2-experiment-design.md
  - 2026-04-30-phase-1_55L-many-turn-cpersist-findings.md (A6, the repeated-question baseline)
  - 2026-05-01-paper-defensibility-experiment-plan.md (Item 3 in the experiment plan)
---

# Phase 1.55M — diverse-prompt multi-turn C-PERSIST stress (PREREG)

## Context and motivation

A6 (Phase 1.55L, commit `b06a345`) cycles 3 unique questions per video for 50 turns. The prereg outcome was clean: zero observed paired drift on `adaptive_post_q2` and `refresh10` at horizon=50. The codex round-36 critique (echoed by the editor) is that the schedule is "repeated-question/stateless" — the same three prompt strings rotate every 3 turns. A reviewer can fairly ask: does cache reuse hold when each turn's prompt is *different text*?

This prereg is the next-cleanest defensibility step short of a true natural-dialogue benchmark. It tests "does C-PERSIST hold when the prompt text varies turn-by-turn while the visual prefix stays constant?"

## What this is and is not

This is **not** a natural-dialogue benchmark. There is no curated multi-turn dialogue dataset attached, and follow-up turns do not actually depend on prior turn answers. The schedule is a templated extension of A6 that varies the prompt prefix per turn while keeping the underlying question pool the same.

It **is** a step beyond A6's "repeated question" framing in three respects:
- Each turn's prompt token sequence is unique (prefix varies even when the question repeats).
- The cache reuse mechanism must handle a non-trivial prompt-text delta between turns, not just a fixed re-issue.
- The fidelity gate is the same as A6 (3% paired drift, 0 pathological), so a clean pass extends C-PERSIST coverage at no claim inflation.

The only legitimate way to claim "natural dialogue" remains a curated multi-turn corpus where turn k+1 references turn k's content. That is **out of scope** for this prereg and gated on user-supplied or model-curated dialogues. See "Path C" below.

## Hypothesis

`H1`: Adaptive post-Q2 reuse and scheduled refresh-10 produce zero observed paired choice or correctness drift at horizon=20 on the same 7-clip × 21-row VideoMME tranche A6 used, with per-turn prompt prefixes drawn from a fixed 5-template pool. Falsification = paired drift exceeds the 3% gate at any horizon ≤ 20.

`H2`: Fixed K=1 produces strictly more paired drift in 1.55M than in A6 because each turn's prompt-text re-prefill exposes a larger cache delta. Falsification = fixed K=1 1.55M drift ≤ A6 drift.

## Method

### Driver patch

Extend `scripts/run_phase1_55L_many_turn_cpersist.py` with a new flag `--prompt-prefix-templates "<comma-separated list>"`. Default is the empty string (current A6 behavior preserved). When non-empty, on turn k the question text becomes `templates[k % len(templates)] + " " + original_question`.

Default 5-template pool (synthetic, content-agnostic, not actually referencing prior answers):

```
"Following up on that, "
"Building on what we just discussed, "
"Now changing topic, "
"Looking at the same scene, "
"One more about this clip, "
```

These are intentionally short and content-independent so the experiment isolates "varying prompt text per turn" from "actual content-conditional dialogue." A second future variant could test content-conditional prefixes ("You said X — what about Y?") but that requires reading the prior turn's output, which is an additional code surgery.

### Cell

- Model: Qwen 2.5-VL-7B-Instruct-4bit (MLX), 20 frames, max-tokens 32, greedy.
- Corpus: same 7-clip VideoMME short tranche as A6 (`videomme_dev_v1.toml`, 7 video IDs).
- Horizon: 20 turns per session (matches A6's mid horizon).
- Policies: `fixed_k1`, `adaptive_post_q2`, `refresh10`.
- Total paired rows per policy: 7 × 21 × (20/3) ≈ 980 if we keep A6's source_q_index cycle, OR 7 × 20 = 140 if we reset to fresh question-per-turn. Use the A6 cycle for consistency.

### Gates

Per cell (policy × horizon):
- `pass_three_percent_drift` — paired choice diffs / n_followup ≤ 0.03 AND paired correctness diffs / n_followup ≤ 0.03 (same as A6).
- `pass_zero_pathological` — pathological format hits == 0 (same as A6).
- `pass_baseline_quality` — cold-baseline accuracy ≥ 14/21 per cell (same as A6's gate definition).

Headline pass = all 3 policies × horizon=20 pass all three gates.

### Wall clock estimate

~3-4 h on M3 16 GB. A6's full horizon=50 × 3 policies took 6.79 h; horizon=20 with the same 3 policies should be ~2.7 h. Add ~1 h overhead for the larger prompt token count from the prefixes (~15-30 extra tokens per question). Net: budget 4 h.

## Pitfalls + mitigations

- *Prefix-induced drift conflated with cache instability.* If 1.55M shows more drift than A6, that could mean (a) C-PERSIST is fragile to prompt variation, or (b) the longer prefixed prompts have higher intrinsic answer variance even at cold baseline. Run the cold baseline arm with the same prefixed prompts so this is paired-controlled; report Δacc at the SAME prefix per turn.
- *Pathological-format hit rate increase.* The synthetic prefixes might confuse the model into emitting longer / different-formatted answers. The gate `pass_zero_pathological` will catch this. If hit rate >0, document and re-run with a smaller prefix pool.
- *Memory.* Same as A6 (~10 GB peak RSS). Should fit.
- *Cache trim correctness.* Qwen 2.5-VL is full-attention only, so the upstream mlx-vlm SWA-trim bug does not apply here. The runtime correctness-control guard is not needed.

## Decision-required path before launch

This prereg requires ONE of:

(a) **Implement the `--prompt-prefix-templates` flag** in `scripts/run_phase1_55L_many_turn_cpersist.py` (estimated ~30-60 lines). User OK to land that surgery. Then run with sandbox off (~4 h). This is the **default path**.

(b) **Use a curated natural-dialogue corpus.** User supplies a 7-clip × 20-turn dialogue pack where turn k+1 actually references turn k's content. Then run with the existing driver but the dialogue replaces the cycled question bank. This is the **stronger path** if the corpus exists.

(c) **Skip 1.55M and accept that A6 is the C-PERSIST horizon evidence in the paper, with the explicit caveat that natural-dialogue stability is future work.** This is the **defer path**.

The author/editor recommends (a) as the right balance of effort vs paper defensibility. The user's prior "Yeah do item 2 and 3" message authorizes (a) once the driver patch lands; this prereg is the gate for that patch.

## Cross-references

- A6 driver: `scripts/run_phase1_55L_many_turn_cpersist.py`.
- A6 findings: `research/experiments/2026/2026-04-30-phase-1_55L-many-turn-cpersist-findings.md`.
- Editor feedback memo §(1) (paper-prose correction on "expected late leakage"): `research/experiments/2026/2026-05-01-paper-editor-feedback.md`.
- Plan: `research/experiments/2026/2026-05-01-paper-defensibility-experiment-plan.md` Item 3.

## Status

PREREG only. The driver patch is queued but not landed in this session because A5 closure + Item 2 launch already saturated the autonomous-safe scope. The next session should land the patch and launch the experiment with sandbox off.
