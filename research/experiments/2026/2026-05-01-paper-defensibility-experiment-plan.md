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

| Cell | Δacc | Warm (per-follow-up) | Q=1 | Q=2 | Q=10 | Q=50 |
|---|---|---|---|---|---|---|
| 7B / 16f | 0.00 | 83.00× | 1.04 | 2.05 | 9.33 | 32.17 |
| 7B / 24f | -0.43 | 124.12× | 1.08 | 2.14 | 10.01 | 37.85 |
| 3B / 20f | -0.05 | 132.21× | 1.05 | 2.08 | 9.79 | 37.78 |

Numbers refreshed 2026-05-01 after `ee41f3f` fixed the warm-column denominator
to share the mean-timing basis used by the Q=k columns. Earlier text in this
doc and in commit `82b1ad8` quoted 91.06× / 121.58× / 136.07× from the
`speedup_first_over_follow` artifact field, which is the ratio of median
first-query timing to median follow-up timing. That remains valid as an
after-ingest median speedup, but it does not share the mean-timing denominator
used by the setup-inclusive Q=k totals — those Warm-column values are
superseded for this table.

**Paper outcome.** Honestly defends C-PERSIST against the "but the warm
multiplier hides the warm-up cost" reviewer criticism. The Q=10 column is
plausibly the most relevant single number for serving (a chat session of 10
follow-ups on the same video) and shows ~9–10×, well clear of trivial-baseline
territory. Gemma 26B prefix-snapshot rows under the
`prefix_snapshot_then_queries` model now also live in the same table per
`ee41f3f`.

**No further compute.** Recommendation to paper editor in `2026-05-01-paper-editor-feedback.md`.

## Item 2 — Random-keep robustness and the separate peer-method gap

**2026-05-01 validation update.** The launch plan in this section is retained
for provenance but is superseded for immediate execution. The currently landed
paper table is a
`uniform_random` sanity baseline, not a peer-method comparison. Do **not**
launch a "FastV-spirit" scorer based on attention-output magnitude and call it
FastV/FasterVLM: the current MLX fused-attention path does not expose the
attention weights those methods use. A faithful peer comparison remains a
separate engineering/reproduction project. The low-risk local follow-up is
only the multi-seed `uniform_random` robustness sweep.

**Immediate runnable experiment.** Run the existing 1.51VC `uniform_random`
baseline across seeds `42,137,999,2024` at the already-landed Qwen 7B 8f
VideoMME dev30 cell, L=2, kr=0.50. Seed 42 is already present under
`research/experiments/2026/artifacts/phase1_51VC_random_keep_baseline/`; the
wrapper skips completed seeds unless `PHASE1_51VC_FORCE=1`.

**Hypothesis.** `magnitude_norm` stays at least 10 percentage points above the
random-keep seed distribution at matched keep-rate. Falsification = random
seeds overlap or beat the structured scorer often enough that the sanity table
cannot be described as a robust structured-vs-random gap.

**Launch command.**

```bash
bash scripts/run_phase1_51VC_random_keep_multiseed.sh
```

**Gates.**

- All requested seed summaries exist and pair against the same dense Qwen 8f
  reference.
- The generated positioning snapshot reports the seed distribution rather than
  a single lucky random seed.
- Caption and findings wording keep saying `uniform_random` is a trivial
  sanity baseline, not a matched-runtime peer method.

**Wall clock estimate.** 3–5 h for the full four-seed set, likely 2–4 h for
the three missing seeds because seed 42 already exists.

**Separate peer-method gap.** A named adjacent-method comparison
(FastV/FasterVLM/HERMES/SparseVILA) remains open. It requires either a faithful
local implementation that exposes the method's actual attention/token scores,
or a carefully bounded literature comparison. The current `magnitude_norm`
scorer is our structured scorer; it must not be rebranded as FastV/FasterVLM.

## Item 3 — Controlled dense-anchored C-PERSIST stress, ready to launch

**2026-05-01 readiness update.** The controlled dense-anchored path is now
launch-ready via `scripts/run_phase1_55M_dense_anchored_cpersist.sh`. The A6
driver preserves its default stateless mode, and adds `--prompt-variant-mode
dense_anchored`, which keys baselines by exact rendered prompt hash and injects
the previous canonical dense answer into both arms. This is still **not** human
natural dialogue. A true natural-dialogue result additionally needs a reviewed
7-clip × 20-turn corpus before compute.

**Two valid variants.**

- **Dense-answer-anchored prompt-variation stress.** Synthetic turns reference
  the canonical dense answer from turn `k` when constructing turn `k+1`. Both
  dense and cached arms receive the exact same rendered prompt text at each
  turn. This is controlled prompt-variation evidence, not human natural
  dialogue.
- **True natural-dialogue stress.** A reviewed 7-clip × 20-turn dialogue corpus
  supplies content-dependent turns. This is the stronger reviewer-defense
  result, but it needs curation before GPU time.

**Hypothesis.** Adaptive post-Q2 cache reuse and refresh10 stay within the 3%
paired drift gate through 20 dense-answer-anchored prompt-variation turns.
Falsification = paired choice or correctness drift exceeds the 3% gate at any
horizon ≤ 20.

**Why this matters.** A6 explicitly labels itself "deliberately not a natural-dialogue benchmark" because the same three questions cycle. A reviewer can reasonably ask whether drift accumulates faster when the dialogue has actual content dependencies (Q3 references Q2's answer, etc.). Closing this gap is the single most defensible claim-strengthening move for C-PERSIST.

**Driver invariants.**

- Baseline rows must be keyed by exact rendered prompt hash, not
  `(video_id, source_q_index)`.
- The rendered prompt hash must be recorded in raw rows and paired rows.
- Any prior-answer text used in turn `k+1` must come from a canonical dense
  pre-pass and be injected into both arms before generation.
- The driver hard-fails if dense and cached arms do not see identical prompt
  hashes for a paired turn.

**Pitfalls + mitigations.**

- *Curated dialogue is small.* 7 × 20 = 140 paired rows total. Not an aggregate-accuracy claim; a paired-stability claim. Wide CI is acceptable; the question is whether drift cliffs.
- *Curator bias.* Curate dialogues blinded to the cache policies to avoid "easy" turns. A 50/50 split between content-referential and content-independent turns helps.
- *Memory pressure.* 20-turn schedule × 3 policies × 7 clips = 420 session-runs on a 16 GB Mac. Same memory footprint as A6 (~10 GB peak); should fit.

**Launch command.**

```bash
bash scripts/run_phase1_55M_dense_anchored_cpersist.sh
```

**Wall clock estimate.** ~4 h on M3 16 GB.

**Paper outcome.** Content-conditional stress would close most of the
stateless-repetition objection. True natural dialogue would close it more
cleanly, but only if the corpus is curated and reviewed before launch.

**Decision required.** Approve ~4 h compute for the controlled dense-anchored
run. Curated natural dialogue remains a stronger future variant, not a blocker
for this controlled stress.

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

1. **Item 2 (multi-seed random_keep)** — highest immediate ROI. No new code;
   2–4 h for the missing seeds.
2. **Item 3 (dialogue-like C-PERSIST)** — highest remaining C-PERSIST payoff.
   The controlled dense-anchored path is now ready; true natural dialogue still
   needs corpus curation.
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
2. **Run controlled dense-anchored C-PERSIST now if we want the low-risk
   C-PERSIST hardening result.** If the paper needs literal human natural
   dialogue, curate a corpus first; otherwise use the dense-anchored wording.
3. **Ask Sam for a 32f prefix-snapshot expansion only if M5 time is cheap.**
   It would harden the Gemma 26B cross-architecture result from 9 rows toward
   the 21-row B0b-style set. It is not required for the current paper claim.

## 2026-05-01 launch-readiness correction

**RETRACTED 2026-05-01 (post-validation review).** An earlier version of
this section (commit `c00cc36`) claimed that
`research/experiments/2026/artifacts/phase1_51V_expansion/` already
contained a Qwen 8f kr=0.25/0.50/0.75 curve with predicted-vs-actual
e2e speedups within ±0.05, and quoted the values 1.088/1.078/1.058
(actual) and 1.104/1.063/1.030 (predicted). **Those numbers do not
exist in the repo.** Direct inspection of every `*_summary.json` under
`phase1_51V_expansion/` shows:

- `model_path` = `<model:gemma-4-e4b-it-4bit>` for **every** cell, not
  Qwen.
- `effective_keep_ratio` = 1.0 for cells exp01–exp08 and exp11–exp12,
  meaning the prune planner returned a no-op at those configs (likely
  because the Gemma-side window-aligned planner with `anchor_arm: none`
  did not actually drop any groups). The only cells with effective
  pruning are exp09 (`anchor_arm: gemma_structural`, eff=0.5) and
  exp10 (`anchor_arm: novelty030_none`, eff≈0.30).
- Observed `end_to_end_speedup_mean` for exp01..exp04 is in the range
  0.99–1.01×, not the claimed 1.058–1.088×.

The retracted table is therefore a fabricated artifact. The Qwen-side
C-CEILING timing evidence that genuinely exists in the repo as of this
writing is a **single** Qwen cell with excellent predicted-vs-actual
timing agreement but a fidelity caveat:

| cell | artifact | n | actual E2E× | predicted E2E× | actual − predicted | fidelity |
|---|---|---:|---:|---:|---:|---|
| Qwen 8f kr=0.50 (1.63E) | `research/experiments/2026/artifacts/phase1_63E_track_b_frame_scaling/pair_summary_8f.json` | 60 | 1.042 | 1.047 | −0.005 | `pass_fidelity=false`, Δacc=−0.0667, choice agreement=0.7167 |

Plus a regime-broken Qwen 16f kr=0.50 cell in 1.63E (22/60 parse
failures, Δacc=−0.42 — fidelity contract is broken before C-CEILING
applies, so its +0.058 deviation is uninformative) and three 16f
fine-bracket cells in 1.63I that are similarly fidelity-broken at the
high keep-rates.

**Conclusion:** the Qwen C-CEILING evidence remains single-cell and should be
framed as timing/arithmetic validation with a fidelity caveat, not as a
fidelity-clean Qwen claim. The "E3" kr sweep (kr=0.25 and kr=0.75 at Qwen 8f)
is a real, non-redundant experiment, and is now launch-ready via
`scripts/run_phase1_63J_qwen_8f_kr_sweep.sh`, but its gates must keep timing
agreement separate from fidelity. A faster alternative is to reuse the existing
1.63E Qwen 8f kr=0.50 cell as the sole Qwen-side timing evidence point and
avoid claiming a clean Qwen kr curve.

**Lesson logged.** This is a variant of an earlier issue in this same
session: a co-scientist agent posted plausible-looking numbers that
were not in the underlying artifacts. Future plans should cite the
exact `summary.json` field path for every quoted number so an
independent reviewer can verify by `grep`. The corrective practice
for this repo is: **every numeric claim in a plan or findings doc
must include the artifact path it was read from.**
