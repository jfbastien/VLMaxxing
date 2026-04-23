---
phase: 1.30-rootcause
date: 2026-04-23
parent: research/experiments/2026/2026-04-23-phase-1_30-sam-streaming-findings.md
prior:
  - research/experiments/2026/2026-04-21-phase-1_30-sam-streaming-reproduction-prereg.md
  - research/experiments/2026/2026-04-23-phase-1_30-sam-streaming-findings.md
  - research/experiments/2026/2026-04-23-phase-1_51V-qwen-cross-arch-findings.md
  - research/experiments/2026/2026-04-19-phase-1_55A-persistent-kv-findings.md
status: preregistered 2026-04-23. Two-phase plan (Phase A short scout, Phase B Q0 parity; Phase C full confirmation conditional) to factorize the 1.30 negative result into V-only, K-only, and interaction components.
tracking: autonomous AFK session 2026-04-22/23 — codex round-28 review
---

# 1.30 root-cause decomposition — prereg

## Why this prereg exists

The 2026-04-23 1.30 findings established a **real negative** on Qwen
2.5-VL-7B-Instruct-4bit at VideoMME 8f: 3.326× speedup PASS, but
Δacc = −0.193 FALSIFIES the preregistered ±0.05 accuracy clause of
H_sam_e2e. The paper-promotion rule for deployment-grade C-VISION
composition does not trigger.

A negative result without a root cause is not a paper claim — it is
open noise. Codex round-28 observed that the current findings note
attributes most of the loss to follow-up KV-cross-contamination, but
the paired data show:

- Q0 (first query) already drops 0.596 → 0.491 (Δ = −0.105)
- Q1/Q2 (follow-ups) drop 0.544 → 0.307 (Δ = −0.237)

The Q0 drop alone violates the ±0.05 budget. The story cannot be
"pure follow-up contamination"; there is at minimum a significant
first-query cost that KV-reuse then compounds.

This prereg factorizes the stack into its two mechanisms (kr_V=0.50
vision pruning; persistent-KV reuse) and two states per mechanism
(on/off), then runs the 2×2 matrix plus two hard-reset controls.
Six arms total. It also runs a Q0 parity check against 1.51V — the
mechanism-grade arm we know is clean — to rule out a first-query
code-path regression in 1.30.

## Hypotheses

Preregistered before the runs complete. Gates read against the short
scout artifacts (Phase A); the full confirmation (Phase C) is only
launched if Phase A is ambiguous or Phase B flags a harness bug.

**H_V (V-only loss dominates).**
`cold_pruned` accuracy on `all_queries` is more than half the size
of `streaming_pruned_off`'s loss vs `cold_dense`:
`|cold_pruned − cold_dense| ≥ 0.5 × |streaming_pruned_off − cold_dense|`.
**Interpretation if PASS:** the paper-promotion failure is primarily a
pruning cost at this operating point on Qwen 7B, not a KV-reuse cost.
Implication: C-VISION's kr_V=0.50 envelope needs revisiting on Qwen
(even though 1.51V showed a +1.044× lift at this setting, the Q0 cost
matters when the stack adds KV-reuse).

**H_K (K-only loss dominates).**
`streaming_dense_off`'s loss on `follow_ups` is more than half the size
of `streaming_pruned_off`'s loss on `follow_ups`:
`|streaming_dense_off − cold_dense|_q23 ≥ 0.5 × |streaming_pruned_off − cold_dense|_q23`.
**Interpretation if PASS:** KV-reuse drift across semantically different
follow-up queries is the main driver; pruning is a relatively clean
add-on. Implication: the right fix is a refresh policy (hard-reset or
smarter), not a pruning tweak.

**H_interaction (non-additive composition).**
The interaction term exceeds the larger of the two isolated terms:
`|combined − (V_only + K_only)| > max(|V_only|, |K_only|)`
where each delta is against `cold_dense` on `all_queries`.
**Interpretation if PASS:** the two mechanisms interact destructively —
pruned KVs reused across queries degrade worse than either alone would
predict. Implication: the paper claim becomes a **bounded anti-claim**:
"these two tricks do not compose naively on Qwen at this operating
point; deploying either alone is safe."

**H_reset (hard-reset recovers K-only loss).**
Hard-reset recovers ≥ 50% of the `streaming_dense_off` follow-up loss:
`(streaming_dense_reset_q23 − streaming_dense_off_q23) ≥ 0.5 × (cold_dense_q23 − streaming_dense_off_q23)`.
**Interpretation if PASS:** cumulative reuse drift is the K-only
mechanism; a smarter refresh policy (adjacent-cos threshold, sliding
window, etc.) is worth implementing.
**Interpretation if FAIL:** the K-only cost is not just cumulative drift
(e.g., it's a single-query KV-contamination even from Q0→Q1); adjacent-cos
or any time-thresholded refresh won't help.

**H_path (1.30 Q0 matches 1.51V Q0 under matched pruning).**
On the same Q0 item set, the **chosen option index** agrees between
`cold_pruned` (1.30) and the 1.51V pruned run at ≥ 0.90 rate
(primary criterion). Correctness-flag agreement is reported as a
secondary diagnostic only.
**Rationale for choice over correctness:** two harnesses that both
answer wrong with *different* wrong options would score 100% on
correctness-agreement but reveal that the model is taking different
logit paths through the two drivers — which is exactly the kind of
harness divergence this gate exists to catch. Choice agreement
directly tests path parity; correctness agreement can hide it.
**Interpretation if PASS:** the Q0 degradation in 1.30 is a real
mechanism cost at kr_V=0.50 on Qwen, not a harness regression.
**Interpretation if FAIL:** 1.30 has a first-query code-path regression
(possibly in its session harness or refresh gating) that must be fixed
before any mechanism conclusion can be drawn. The compare script at
`scripts/phase1_30_rootcause_q0_compare.py` already prints both
statistics; the gate reads the choice-agreement row.

## Arms (Phase A short scout)

All 6 arms run against `research/benchmark_manifests/videomme_dev_v1_short_only.toml`
at Qwen 2.5-VL-7B-Instruct-4bit, 8 frames, max_tokens=32, rss_guard=10GB.
Allow-dirty flag threaded per 1.51V/1.30 wrapper pattern (multi-arm runs
tolerate dirty tree between arms so instrumentation edits don't abort
mid-matrix).

| # | Arm                       | stack     | kr_V | refresh    | role                                   |
|---|---------------------------|-----------|------|------------|----------------------------------------|
| 1 | `cold_dense`              | cold      | 1.00 | off        | baseline                               |
| 2 | `cold_pruned`             | cold      | 0.50 | off        | V-only cost                            |
| 3 | `streaming_dense_off`     | streaming | 1.00 | off        | K-only cost (cumulative reuse)         |
| 4 | `streaming_pruned_off`    | streaming | 0.50 | off        | combined = current 1.30                |
| 5 | `streaming_dense_reset`   | streaming | 1.00 | hard-reset | K-only upper-bound recovery            |
| 6 | `streaming_pruned_reset`  | streaming | 0.50 | hard-reset | combined upper-bound recovery          |

The `hard-reset` policy clears the session KV cache before every
follow-up query; it is the strongest refresh we have already implemented
(no adjacent-cos; that policy is not yet in the driver, flagged FAIL
in the existing `--drift-refresh-policy threshold` CLI branch).

Runner: `scripts/run_phase1_30_rootcause_decompose.sh` (MODE=short).
Analyzer: `scripts/analyze_phase1_30_rootcause.py`.

## Phase B: Q0 parity check (blocking on Phase A arm #2)

After `cold_pruned.jsonl` lands, build a Q0-only manifest and run 1.51V
against the same Q0 items at matched kr_V=0.50 / L=2:

```bash
./.venv/bin/python scripts/phase1_30_rootcause_q0_manifest.py \
  research/experiments/2026/artifacts/phase1_30_rootcause_short/cold_pruned.jsonl \
  /tmp/phase1_30_q0_manifest.toml

./.venv/bin/python scripts/run_phase1_51V.py \
  --manifest /tmp/phase1_30_q0_manifest.toml \
  --frame-count 8 --max-tokens 32 \
  --model-path "$HOME/models/Qwen2.5-VL-7B-Instruct-4bit" \
  --vision-tower-layer 2 --vision-tower-keep-rate 0.50 \
  --allow-dirty --rss-guard-mb 10000 \
  --output research/experiments/2026/artifacts/phase1_30_rootcause_short/q0_151V_pruned.jsonl \
  --summary research/experiments/2026/artifacts/phase1_30_rootcause_short/q0_151V_pruned_summary.json

./.venv/bin/python scripts/phase1_30_rootcause_q0_compare.py \
  research/experiments/2026/artifacts/phase1_30_rootcause_short/cold_pruned.jsonl \
  research/experiments/2026/artifacts/phase1_30_rootcause_short/q0_151V_pruned.jsonl
```

Gate: **choice agreement ≥ 0.90** (the `choice agreement` line the
compare script prints). Correct-flag agreement is printed as a
diagnostic only, since two drivers can match on correctness while
routing logits through different paths to different wrong answers.

## Phase C: full 57-seed confirmation (conditional)

Triggered only if Phase A yields one of:
- H_interaction **PASS** (the 57-seed run confirms the anti-claim at
  tighter CI; the short-scout n is too small to rule out noise).
- Phase A ambiguous (closest gate margin is < 0.05).

Full run: same decomposition script, `MODE=full`, against
`videomme_dev_v1.toml ∪ videomme_holdout_v1.toml`. Runtime estimate
~6-10× the short scout (≈6h) since the full union is ~5× the seeds and
the streaming arms amortize less with more unique queries.

## Non-goals

- **No adjacent-cos implementation.** The `--drift-refresh-policy threshold`
  CLI path hard-fails in `scripts/run_phase1_30_sam_streaming.py:286-290`.
  Implementing adjacent-cos refresh is a separate follow-up that only
  makes sense if H_reset **PASSES** in Phase A.
- **No Gemma replication.** The 1.30 driver hard-fails on
  `model_type != qwen2_5_vl` (`scripts/run_phase1_30_sam_streaming.py:303-308`).
  Porting 1.30 to Gemma is a separate phase whose value depends on what
  Phase A says about Qwen. If the failure is V-only-dominated on Qwen
  at kr_V=0.50, Gemma at the same kr_V may or may not reproduce — that's
  an interesting but second-order question.
- **No paper-claim update yet.** C-VISION remains mechanism-grade,
  1.30 remains "protocol reproduces speedup not fidelity on Qwen at these
  tolerances." The findings doc is updated when this prereg's gates
  adjudicate.

## Runtime estimates (M3 16GB, Qwen 4-bit)

- Phase A — 6 arms × ~10 seeds × 8 frames each:
  - cold_dense ~15 min
  - cold_pruned ~12 min
  - streaming_dense_off ~10 min
  - streaming_pruned_off ~8 min
  - streaming_dense_reset ~15 min
  - streaming_pruned_reset ~12 min
  - **Phase A total ≈ 75 min**
- Phase B — 1.51V over ~10 Q0 items: **≈ 10 min**
- Phase C (conditional, only if triggered) — dev+holdout union:
  **≈ 5–7 h**

If Phase A is unambiguous (typical case), root-cause lands in ~1.5h total
against current 1.30 ambiguity.

## Reproduction

```bash
# Phase A (short scout)
bash scripts/run_phase1_30_rootcause_decompose.sh
./.venv/bin/python scripts/analyze_phase1_30_rootcause.py \
  research/experiments/2026/artifacts/phase1_30_rootcause_short

# Phase B (Q0 parity)
# see commands in §"Phase B" above

# Phase C (full, only if Phase A ambiguous or H_interaction PASS)
MODE=full bash scripts/run_phase1_30_rootcause_decompose.sh
./.venv/bin/python scripts/analyze_phase1_30_rootcause.py \
  research/experiments/2026/artifacts/phase1_30_rootcause_full
```

## Acknowledgements

This decomposition plan closely follows the Codex round-28 review. The
factorization structure (V-only × K-only × interaction × hard-reset
upper-bound × 1.51V Q0 parity) is Codex's. The concrete scripts have
been landed in-repo rather than in `/tmp` so future readers can reproduce.
