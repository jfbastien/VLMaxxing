---
date: 2026-05-01
phase: 1.55M (diverse-prompt multi-turn C-PERSIST stress)
status: READY TO LAUNCH for dense-anchored controlled stress. True natural dialogue still requires a curated corpus.
related:
  - 2026-04-29-phase-2-experiment-design.md
  - 2026-04-30-phase-1_55L-many-turn-cpersist-findings.md (A6, the repeated-question baseline)
  - 2026-05-01-paper-defensibility-experiment-plan.md (Item 3 in the experiment plan)
---

# Phase 1.55M — dense-anchored multi-turn C-PERSIST stress

## Context and motivation

A6 (Phase 1.55L, commit `b06a345`) cycles 3 unique questions per video for 50 turns. The prereg outcome was clean: zero observed paired drift on `adaptive_post_q2` and `refresh10` at horizon=50. The codex round-36 critique (echoed by the editor) is that the schedule is "repeated-question/stateless" — the same three prompt strings rotate every 3 turns. A reviewer can fairly ask: does cache reuse hold when each turn's prompt is *different text*?

This prereg is the next-cleanest defensibility step short of a true natural-dialogue benchmark. It tests "does C-PERSIST hold when each turn's prompt text is different and includes the prior canonical dense answer while the visual prefix stays constant?"

## What this is and is not

This is **not** a human natural-dialogue benchmark. There is no curated multi-turn dialogue dataset attached. It is a controlled dense-anchored stress: turn `k+1` injects the canonical dense answer from turn `k`, and both dense and cached arms receive the exact same rendered prompt for each paired turn.

It **is** a step beyond A6's "repeated question" framing in three respects:
- Each turn's prompt token sequence is unique after the first turn.
- Prompt variation is anchored on the prior canonical dense answer, not just a fixed prefix.
- The driver records prompt hashes and hard-fails if the dense and cached arms see different prompt text.
- The fidelity gate is the same as A6 (3% paired drift, 0 pathological), so a clean pass extends C-PERSIST coverage at no claim inflation.

The only legitimate way to claim "natural dialogue" remains a curated multi-turn corpus where turn k+1 references turn k's content. That is **out of scope** for this prereg and gated on user-supplied or model-curated dialogues. See "Path C" below.

## Hypothesis

`H1`: Adaptive post-Q2 reuse and scheduled refresh-10 produce zero observed paired choice or correctness drift at horizon=20 on the same 7-clip VideoMME tranche A6 used, with each follow-up prompt anchored on the prior canonical dense answer. Falsification = paired drift exceeds the 3% gate at any horizon ≤ 20.

`H2`: Fixed K=1 produces at least as much paired drift in 1.55M as in A6 because each turn's prompt-text re-prefill exposes a larger non-image suffix delta. Falsification = fixed K=1 stays indistinguishable from adaptive/refresh10.

## Method

### Driver support

`scripts/run_phase1_55L_many_turn_cpersist.py` now supports:

- `--prompt-variant-mode stateless_question_cycle` — A6 default, unchanged.
- `--prompt-variant-mode templated_prefix` — synthetic fixed template variation.
- `--prompt-variant-mode dense_anchored` — the 1.55M launch mode.

In dense-anchored mode the driver precomputes the canonical dense sequence per
video up to the maximum requested horizon. For turn `k>0`, the rendered question
is:

```text
Previous dense answer: {previous_answer}
Using the same video, answer this follow-up question:
{question}
```

The cached policy arms reuse those same precomputed turn prompts. The driver
records `prompt_hash` / `baseline_prompt_hash` and raises before writing a
paired row if they differ. Baselines are therefore keyed by exact turn prompt,
not by `(video_id, source_q_index)`.

### Cell

- Model: Qwen 2.5-VL-7B-Instruct-4bit (MLX), 20 frames, max-tokens 32, greedy.
- Corpus: same 7-clip VideoMME short tranche as A6 (`videomme_dev_v1.toml`, 7 video IDs).
- Horizon: 20 turns per session (matches A6's mid horizon).
- Policies: `fixed_k1`, `adaptive_post_q2`, `refresh10`.
- Total paired rows per policy: 7 × 20 = 140.

### Gates

Per cell (policy × horizon):
- `pass_three_percent_drift` — paired choice diffs / n_followup ≤ 0.03 AND paired correctness diffs / n_followup ≤ 0.03 (same as A6).
- `pass_zero_pathological` — pathological format hits == 0 (same as A6).
- `pass_prompt_hash_pairing` — every paired dense/cached row has identical prompt hashes.

Headline pass = all 3 policies × horizon=20 pass the drift and prompt-hash gates.

### Wall clock estimate

~4 h on M3 16 GB. A6's full horizon=50 × 3 policies took 6.79 h; horizon=20 with the same 3 policies should be ~2.7 h. Dense-anchored prompts are longer, so budget 4 h.

## Pitfalls + mitigations

- *Self-conditioning divergence.* Avoided by using canonical dense answers for prompt construction in both arms. Cached-arm output never feeds the next prompt.
- *Prompt mismatch.* The driver hard-fails on prompt-hash mismatch before emitting a paired row.
- *Pathological-format hit rate increase.* The anchor prefix might confuse the model into emitting longer / different-formatted answers. The pathological gate will catch this.
- *Memory.* Same as A6 (~10 GB peak RSS). Should fit.
- *Cache trim correctness.* Qwen 2.5-VL is full-attention only, so the upstream mlx-vlm SWA-trim bug does not apply here. The runtime correctness-control guard is not needed.

## Launch

Ready command:

```bash
bash scripts/run_phase1_55M_dense_anchored_cpersist.sh
```

This reuses existing complete artifacts if `summary.json` validates for the
requested video IDs, turn counts, and policies. Otherwise it overwrites the
JSONL outputs in `phase1_55M_dense_anchored_cpersist/`.

## Remaining stronger path

A curated natural-dialogue corpus would still be stronger. If supplied, it
should use the same prompt-hash pairing and dense-anchor invariants. Do not
call this 1.55M result "natural dialogue" in the paper; call it controlled
dense-answer-anchored prompt variation.

## Cross-references

- A6 driver: `scripts/run_phase1_55L_many_turn_cpersist.py`.
- A6 findings: `research/experiments/2026/2026-04-30-phase-1_55L-many-turn-cpersist-findings.md`.
- Editor feedback memo §(1) (paper-prose correction on "expected late leakage"): `research/experiments/2026/2026-05-01-paper-editor-feedback.md`.
- Plan: `research/experiments/2026/2026-05-01-paper-defensibility-experiment-plan.md` Item 3.

## Status

READY TO LAUNCH for the controlled dense-anchored stress. Not launched in this
commit.
