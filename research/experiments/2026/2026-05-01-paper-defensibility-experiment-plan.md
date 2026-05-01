---
date: 2026-05-01
phase: paper-defensibility-plan (codex round-36 + editor 2026-04-30 feedback)
status: design only; each item has hypothesis / expected outcome / pitfalls / ETA / paper-outcome and is gated on user OK before launch
related:
  - 2026-05-01-paper-editor-feedback.md
  - 2026-04-29-phase-2-experiment-design.md
---

# Paper-defensibility experiment plan — 2026-05-01

This file consolidates the remaining experiments that codex and the paper editor flagged as worth running before external review. Each is preregistered to the bar of the existing prereg files: hypothesis, gate definitions, baselines, pitfalls, ETA, paper outcome. Nothing here launches without user approval. The setup-inclusive economics analysis (item 1) is the only one that has already executed because it is pure analysis with no GPU compute.

## Item 1 — Setup-inclusive C-PERSIST economics ✅ landed

**Status:** committed in `82b1ad8` (setup-inclusive economics generator + paper table).

**What it does.** Reads existing `phase1_55A_*/summary.json` artifacts and emits, for each of (Qwen 7B 16f, 18f, 20f, 24f, 32f; Qwen 3B 20f), the session-level speedup as a function of follow-ups-per-session N: `naive_total / persist_total = N·baseline / (first + (N-1)·follow)`.

**Numbers landed (see `paper/arxiv/generated/tables/c_persist_setup_inclusive.tex`):**

| Cell | Δacc | Warm (per-follow-up) | N=1 | N=2 | N=10 | N=50 |
|---|---|---|---|---|---|---|
| 7B / 16f | 0.00 | 91.06× | 1.04 | 2.05 | 9.33 | 32.17 |
| 7B / 24f | -0.43 | 121.58× | 1.08 | 2.14 | 10.01 | 37.85 |
| 3B / 20f | -0.05 | 136.07× | 1.05 | 2.08 | 9.79 | 37.78 |

**Paper outcome.** Honestly defends C-PERSIST against the "but the 91× hides the warm-up cost" reviewer criticism. The N=10 column is plausibly the most relevant single number for serving (a chat session of 10 follow-ups on the same video) and shows ~9–10×, well clear of trivial-baseline territory.

**No further compute.** Recommendation to paper editor in `2026-05-01-paper-editor-feedback.md`.

## Item 2 — Competitor positioning table + one matched local baseline

**Hypothesis.** Even without re-running peer methods (FastV, FasterVLM, SparseVILA, HERMES) on identical hardware, a disciplined comparison table that quotes their reported numbers under the C-CEILING constraint (component speedup × stage share = e2e bound) is enough to position our results. Adding ONE additional local visual-token-pruning baseline that we run ourselves under matched conditions removes the "no head-to-head" objection.

**Falsification of the hypothesis** = at the closest matched cell (model class × frame count × benchmark), our reported e2e Δacc/speedup envelope does not improve on or differ from the chosen baseline.

**Local baseline candidate.** FasterVLM's training-free token reduction at the same vision-tower cut layer (L=2) used by phase 1.51V. Reuses the existing `codec_through.qwen_pruned_vision_tower` infrastructure. Matched against a single Qwen 7B 16f cell on VideoMME holdout (n=30) for a single keep-rate choice.

**Gates.**

- Paired Δacc within ±0.05 vs uniform-dense reference.
- Per-paired choice/correctness diffs ≤ 1/30 absolute (loose, since this is positioning evidence, not headline).
- Wall-clock prefill + e2e logged per row.
- Comparison table cites measured `e2e_speedup_actual` / `e2e_speedup_predicted` against the existing C-CEILING model so reviewers see we apply the same arithmetic to the competitor.

**Pitfalls + mitigations.**

- *Different selection metric* — FasterVLM uses CLS-attention to rank tokens; our 1.51V uses gemma_structural / nuwa anchors. Run the FasterVLM scoring at the same cut layer rather than the original CLS-head layer to keep apples-to-apples on the prefill point. State the difference in the table caption.
- *Ranking equivalence* — at fixed keep-rate, with identical kept count, the only axis we control is *which tokens* survive. Ensure the FasterVLM scorer is implemented as a drop-in selection function passed into `qwen_pruned_vision_tower` so the surrounding code is identical.
- *Single cell can be cherry-picked* — choose the cell from the existing 1.51V results that already has clean dense-vs-pruned baseline (Qwen 7B 16f VideoMME holdout). State the cell choice up front.

**Wall clock estimate.** ~1.5 h for the FasterVLM cell on M3 16 GB (n=30 holdout, 16f Qwen 7B). Comparison-table generator: 30 min wall.

**Paper outcome.** A new `paper/arxiv/generated/tables/competitor_positioning.tex` that puts our headline cells next to FasterVLM (run locally), FastV (cited reported), HERMES (cited reported), and SparseVILA (cited reported), each with C-CEILING-decomposed e2e numbers and explicit `predicted` vs `actual` columns. This is the single most valuable item if external reviewers are likely to ask "where's the comparison?"

**Decision required from user before launch.** (a) confirm FasterVLM is the right local baseline (vs FastV), (b) confirm the 1.51V cell choice (Qwen 7B 16f VideoMME holdout), (c) confirm we cite peer numbers from their papers without re-running them.

## Item 3 — Natural-dialogue many-turn C-PERSIST

**Hypothesis.** Adaptive post-Q2 cache reuse holds at zero observed paired drift for at least 20 turns when the schedule is a *natural multi-turn dialogue* (each turn references the prior answer or asks a content-conditioned follow-up), not the repeated-question stateless cycle that A6 (1.55L) tested. Falsification = paired choice or correctness drift exceeds the 3% gate at any horizon ≤ 20.

**Why this matters.** A6 explicitly labels itself "deliberately not a natural-dialogue benchmark" because the same three questions cycle. A reviewer can reasonably ask whether drift accumulates faster when the dialogue has actual content dependencies (Q3 references Q2's answer, etc.). Closing this gap is the single most defensible claim-strengthening move for C-PERSIST.

**Method.**

- 7-clip × 20-turn natural dialogue corpus on the same VideoMME short tranche A6 used. Each clip gets a hand-curated 20-turn dialogue with content dependencies (turn k+1 may reference turn k's answer, ask follow-up "and then what?", "what color was the X you mentioned?", etc.). Curated by a human or by GPT-4 with manual review; not auto-generated by the same model under test.
- Three policies: `fixed_k1`, `adaptive_post_q2`, `refresh10` (same as A6).
- Cold baseline: each turn cold-prefilled, deterministic.
- Gates: same 3% gate per cell, plus a stricter pathological-format gate (≤ 1/140 hits).

**Pitfalls + mitigations.**

- *Curated dialogue is small.* 7 × 20 = 140 paired rows total. Not an aggregate-accuracy claim; a paired-stability claim. Wide CI is acceptable; the question is whether drift cliffs.
- *Curator bias.* Curate dialogues blinded to the cache policies to avoid "easy" turns. A 50/50 split between content-referential and content-independent turns helps.
- *Memory pressure.* 20-turn schedule × 3 policies × 7 clips = 420 session-runs on a 16 GB Mac. Same memory footprint as A6 (~10 GB peak); should fit.

**Wall clock estimate.** 7 clips × 3 policies × 20 turns × ~7 s/turn ≈ 50 min compute, plus the cold-baseline arm at 7 × 20 × ~75 s ≈ 175 min. Total ~3.8 h on M3 16 GB. About 4 h with overhead.

**Paper outcome.** Either confirms C-PERSIST extends to natural dialogue (much stronger headline) or surfaces a paired drift cliff that the paper must mark as a real boundary. Both are paper-grade.

**Decision required.** (a) approve curating the 7-clip × 20-turn dialogue pack, (b) approve ~4 h compute on the user's Mac, (c) decide whether to start the curation work in this session or defer.

## Item 4 — C-STREAM throughput-axis closure (the 4th-headline path)

**Hypothesis.** When measured on the **throughput axis** (per-frame ViT-fire reduction at matched accuracy under matched event windows), native-rate streaming state reuse beats the trivial baselines low-FPS-dense / screenshot-polling / recency-last-K by ≥ 2× at Δacc within ±0.05 of fresh-oracle-dense, with paired choice/correctness diffs zero on the ground-truth multiple-choice rows and at least one stale-cache failure case documented.

**Why this is the only credible headline path.** Sub-agent audit (`acde90438878a81bd`) found that the matched-evidence accuracy regime favors the trivial `low_fps_dense` baseline (B3: 17/22 vs 13/22 for `sam_policy`). C-STREAM cannot win on accuracy at matched evidence — that has been tested twice (B3, 1.30) and lost both times. The achievable win is the throughput axis: *at the same accuracy, fire the ViT less often*. That is what makes the per-frame ViT reduction the headline number, not an accuracy lift.

**Falsification of the hypothesis** = c_stream_native does not beat low_fps_dense on either the throughput axis at matched accuracy or the accuracy axis at matched throughput. Either failure mode means C-STREAM stays a candidate.

**Method.**

- Corpus: 60 events × 3 video families. Two screen-content families (terminal session, twitter scroll) plus one non-screen content family (driving footage or sports highlight) so the headline cannot be dismissed as "screen-only."
- Frame regimes: 8f / 16f / 32f event-window evidence.
- Five arms: `low_fps_dense` (K uniform), `screenshot_polling` (1 frame at t_event), `recency_last_K` (K most recent), `fresh_oracle_dense` (8 uniform — gold), `c_stream_native` (per-frame cache update, ViT fires only on rebuild trigger).
- Gates: Δacc within ±0.05 vs `fresh_oracle_dense` on ≥ 40 ground-truth multiple-choice rows; paired choice/correctness diffs zero on those 40; ≥ 1 stale-cache failure case included by construction; ≥ 2× ViT-fire reduction vs low_fps_dense at matched accuracy.
- Artifacts: raw paired JSONL + cache-correctness sidecar + paper-table generator.

**Pitfalls + mitigations.**

- *Scope creep.* The throughput-axis pivot requires the paper to re-title the contribution (C-STREAM = ingestion-density anti-recomputation). Lock the wording before the experiment runs so the paper claim and the experiment design match.
- *Curated stale-cache case selection bias.* Pick the stale-cache case from a separate held-out clip set so the failure is genuinely outside the training-distribution of the policy.
- *Memory at 32f.* M3 16 GB has been fragile at 32f under thermal pairing (per `project_1_51V_expansion_2026-04-21` memory). Run 32f rows last, with single-thread mode, and accept the option of dropping 32f if RSS exceeds 14 GB.
- *Cache-correctness.* The B0b lessons say don't trust default cross-turn cache reuse on mixed-SWA — but Qwen 7B is full-attention only, so this is not blocked. Cache-correctness check still in scope.
- *Long runtime.* ~20-32 h on M3 16 GB per sub-agent estimate. Schedule against thermal headroom; plan two sessions if needed.

**Wall clock estimate.** 20-32 h continuous on M3 16 GB. The lower bound assumes thermal stability; the upper bound assumes typical M3 throttling.

**Paper outcome.** If clean → C-STREAM promotes from candidate to 4th headline with the throughput-axis framing. If unclean → C-STREAM stays a candidate; the paper edits would soften it further. Either way, the rigorous test closes the question.

**Decision required.** (a) approve the throughput-axis re-titling, (b) approve curating the 60-event × 3-family corpus, (c) approve 20-32 h of M3 compute, (d) confirm the gate definitions before launch (these are the bar; can be tightened but should be locked pre-run to avoid post-hoc reframing).

## Item 5 — 1.30AG finite-audit rerun ✅ in flight

**Status:** running as background task `bq9skegzv`, sandbox off, ETA ~08:40 (started 08:11). The probe has been instrumented in `6cc5d32` to emit per-window NaN/Inf/max-abs telemetry on both the valid window and the buffer tail past `valid_tokens`, plus a per-layer fp32 control cosine, plus strict `allow_nan=False` JSON serialization with explicit `nonfinite_count` fields.

**First-row evidence (already discriminative):**

| arm/layer | bf16 cosine | fp32 cosine | left_audit.has_nan | left_audit.max_abs | tail_max_abs |
|---|---|---|---|---|---|
| reuse layer 0 keys | NaN (scrubbed → null) | 1.0 | False | 174.0 | 0.0 |
| pruned layer 0 keys | NaN (scrubbed → null) | 0.99972 | False | 174.0 | – |

Hypothesis (b) (bf16 cosine sum-of-squares overflow) is confirmed at the first-row level: cache contents are finite, fp32 cosine is finite and physically meaningful (1.0 for bit-identical reuse cache, 0.99972 for pruned-vs-dense). bf16 cosine NaN is purely the bf16 reduction. Buffer-tail audit shows `max_abs = 0.0`, which means the slice DOES narrow the view in the reduction path — the alternative "lazy view leaks padding" hypothesis is also ruled out.

**When the rerun lands.** Update `findings doc` + registry to "diagnosis CLOSED-EARNED: bf16 cosine reduction overflow, finite cache." Then either (a) repurpose `cosine_fp32` as the primary metric and re-evaluate the H4 saturation gate (no further compute), or (b) leave the probe documented as "captured but bf16 cosine bug; fp32 control cosine works; H4 saturation finally adjudicable from the in-flight rerun."

**Paper outcome.** Mechanism instrumentation, not paper claim-bearing. Closes the 1.30 root-cause Phase B (Q0 parity vs 1.51V) question one notch tighter once the H4 saturation result is read off the fp32 cosine column.

## Recommendation summary

Three independent paths forward, ordered by paper-impact-per-compute:

1. **Item 2 (competitor positioning)** — highest ROI. ~2 h total compute. Single most defensible move.
2. **Item 3 (natural-dialogue many-turn C-PERSIST)** — second-highest. ~4 h compute. Closes the conversational-stability gap at low cost.
3. **Item 4 (C-STREAM throughput-axis)** — only if a 4th headline is the goal. ~20-32 h compute. Real gamble.

Items 1 and 5 are already done or nearly done. The user gets to pick which of 2 / 3 / 4 to fund.

## Memory + safety guardrails

- `mx.set_memory_limit(12 * 1024**3)` is set in the cache-distance probe; reuse the same pattern for any new MLX-backed experiment driver.
- Item 4's 32f arms are the most fragile. Stage them after 8f/16f and bail at 14 GB RSS.
- All new experiments run with `B0B_DISABLE_RUNTIME_GUARD` set deliberately if and only if cache reuse correctness is the test (not the case for items 2/3/4).
- Sandbox off is required for any MLX-Metal-backed run; Item 5 already proves this.

## 2026-05-01 supervisor-review addendum

The post-integration review tightened the plan in three places:

1. **Natural dialogue should not be faked.** A templated prompt-variation
   run is still useful, but it is not a natural-dialogue benchmark. If run
   locally, label it "dense-anchored content-conditional prompt variation":
   every cached and dense arm must receive the exact same rendered prompt
   hash at each turn, and any prior answer text spliced into turn \(k+1\)
   must come from a canonical dense pre-pass. This isolates cache-policy
   drift from self-conditioning drift. A true natural-dialogue result needs
   a curated 7-clip × 20-turn corpus with reviewed prompts before compute.
2. **Do not run a named FastV/FasterVLM proxy unless the implemented metric
   is faithful.** The current Qwen MLX path does not expose decoder attention
   scores through the fused attention kernels, and an attention-output
   magnitude scorer would be a new proxy, not FastV. The landed
   `uniform_random` row is therefore only a sanity baseline. The cheap
   hardening path is a multi-seed random_keep sweep; a true adjacent-method
   comparison remains a separate implementation/reproduction project.
3. **C-STREAM already has a short negative pilot.** Sam B3 is the cheap trial:
   `low_fps_dense` wins 17/22 versus `sam_policy` 13/22 at matched evidence.
   A one-hour rerun is unlikely to promote C-STREAM; it can only validate
   harness mechanics. Promotion still requires the larger throughput-axis
   experiment with matched low-FPS/screenshot/recency baselines and stale-cache
   cases. Until then C-STREAM stays candidate evidence.

Revised near-term recommendation:

1. **Run the multi-seed random_keep sweep** if the random sanity table remains
   in the paper. Hypothesis: `magnitude_norm` stays at least 10 pp above the
   random_keep seed distribution at matched keep-rate. Runtime: about
   3–5 hours for seeds `42 137 999 2024` on the local Qwen 7B 8f dev30 cell.
2. **Run true natural-dialogue C-PERSIST only after curation.** If no curated
   corpus is ready, defer rather than spending 4 hours on a result that will
   still need narrow wording.
3. **Ask Sam for a 32f prefix-snapshot expansion only if M5 time is cheap.**
   It would harden the Gemma 26B cross-architecture result from 9 rows toward
   the 21-row B0b-style set. It is not required for the current paper claim.
