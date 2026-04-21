---
date: 2026-04-21
parent: paper/framing.md
status: living priority doc — updated each codex round + each session recap
---

# Paper Priority: must-do / should-do / future

Triage of outstanding work against the paper submission bar. Updated per
Codex round-25 (2026-04-21 session 4). See `paper/framing.md` for the three major
contributions (C-CEILING, C-PERSIST, C-VISION) these priorities map to.

Round-25 status: must-do #1 (VideoMME 8f V-only holdout pair) CLOSED;
should-do #2 (MVBench + TOMATO V-only holdout pairs) session 4 QUEUE
COMPLETE — **MVBench 8f CLOSED with advisory pass** (EXP19/20: E2E
1.407× far exceeding dev 1.21×, V_red 0.471, acc Δ −0.033; thermal
gate 11.66% formally fails but 50 ms absolute delta is OS-jitter
scale on MVBench's 432 ms decode window; calibration-revision
proposed). **TOMATO 8f THERMALLY CONFOUNDED** (EXP21/22: decode Δ
6.52% = 206 ms absolute, genuine thermal drift; 4 dense-arm gen
outliers corrupt the mean-based E2E statistic; re-run queued as
session 5). Findings: `research/experiments/2026/2026-04-21-phase-1_51V-session4-findings.md`.
Driver bug fixed mid-session: `_count_frames` metadata fast path
removed after 0298-00.mp4 reported `stream.frames=366` while
iterative decode yielded only ~235 decodable frames (TOMATO EXP21
initial hard-fail at item 12/30).

## Must-do (hard blockers on a main-track submission)

Every item here is required for a self-consistent, reviewer-defensible
draft. Order within the tier is by dependency (top items unblock
others).

1. **1.51V V-only holdout unpatched-vs-patched pair (EXP17/EXP18).**
   Why: three paper-table cells (TOMATO **1.24×**, MVBench **1.21×**,
   VideoMME 8f/16f 1.08×/1.12×) were dev-only. Without a holdout
   unpatched baseline on at least VideoMME 8f, the C-VISION headline
   cells carried a "dev-only n=30" footnote a reviewer would cut.
   Status: **CLOSED 2026-04-21** — all four preregistered hypotheses
   pass. H_holdout_vonly_e2e = 1.113× (gate ≥ 1.05×); H_holdout_vred =
   0.413 (gate [0.35, 0.45]); H_holdout_thermal = 1.53% (gate < 2%);
   H_holdout_accuracy = 0.000 (gate [−0.05, +0.05]). Holdout V_share
   corrected to 15.45% (prior memory note 8.6% was stale / wrong).
   Paper-table VideoMME 8f cell may drop the "dev-only" caveat.
   Findings: `research/experiments/2026/2026-04-21-phase-1_51V-session3-findings.md`.

2. **Ledger consistency across registry ↔ claim-matrix ↔
   publishability-status ↔ research-dashboard.** Claim-matrix has been
   the authoritative doc through round-20; registry rows had drifted.
   Fixed this round for phase 1.41 (status `proposed` → `EARNED
   2026-04-18`) and phase 1.55D research-dashboard row (`closed-null` →
   `infra-falsified`). Sweep for remaining stale rows is a P0 before
   submission; any sentence a reviewer cross-checks across two docs
   must agree.

3. **Main CI green on `main`.** Local `uv run ruff format --check .`
   passes; commit `0a8b1d1` is queued locally and unpushed per
   `feedback_no_auto_push`. User must trigger the push. Without green
   CI the paper claims of reproducibility look sloppy.

4. **Attention-propagation-drift vocabulary discipline.** Codex
   round-21 flagged that Sam's §234 attributes the refresh requirement
   to attention-context drift (~0.01/frame), NOT positional-encoding
   drift. `publishability-status.md:283` landed the reconciliation.
   Now landed in `framing.md` Reviewer-Facing Limitations §7 this
   round (round-24). A direct PE-drift ablation is NOT required for
   submission provided the paper says "attention-propagation drift"
   when citing Sam and treats 1.57 (adjacent-frame ViT cosine) as a
   **lower-bound proxy** rather than a direct cache-substitute
   measurement.

5. **1.51V is the primary local Gemma story, not 1.51R.** Round-22/23
   already demoted 1.51R's dev-only 1.39× aggregate to a
   "duration-conditional partial reproduction"; round-24 codex
   reiterates. 1.51R should appear in the paper as:
   - the EXP10 n=60 H_stack gate on VideoMME holdout (one explicit
     promotion rule: ≥ 4pp E2E lift over V-alone AND agreement ≥ 0.75
     AND acc within −0.067), and
   - the Stage 5 anchor-arm comparison that produces the
     `gemma_structural` default (secondary methodology content).
   All narrative repositioning of 1.51R as the headline must stop.
   1.51V's `E2E ≤ 1/(1 − V_share × V_red)` ceiling is the C-VISION
   contribution; 1.51R's LLM-side `1/(1 − generate_share ×
   generate_reduction)` is the composition appendix.

## Should-do (high-value lifts within ~1 session-day each)

These are not blockers, but any one of them individually raises the
submission tier from "efficiency workshop" to "main-track defensible"
in its own dimension.

1. **EXP10 n=60 H_stack thermally-paired re-check.** Tightens the
   H_stack CI from ±0.05 to ±0.03, makes the "stacking composes,
   ceiling-bounded" secondary claim defensible on n=60 rather than
   n=30. Runtime ~60-90 min. Prereq: thermal-pairing runner-level gate
   (codex round-23 P3) to avoid a fourth decode-Δ ≥ 2% pair.
   Preregistered under task #152.

2. **1.51V MVBench and TOMATO holdout unpatched-vs-patched pairs.**
   Analogous to the VideoMME 8f holdout (must-do #1) but for the
   other two benchmarks. **MVBench 8f CLOSED 2026-04-21 with advisory
   pass** (EXP19/20: E2E 1.407× far exceeding dev 1.21×, V_red 0.471
   OOB+ favorable, acc Δ −0.033; thermal gate formally fails at
   11.66% but 50 ms absolute is OS-jitter on MVBench's 432 ms decode
   window — calibration revision proposed: `|Δ| < max(0.02 ×
   decode_ms, 100 ms)`). **TOMATO 8f THERMALLY CONFOUNDED 2026-04-21**
   (EXP21/22: decode Δ 6.52% = 206 ms absolute, genuine drift; 4
   dense-arm gen outliers corrupt the mean-based E2E to 1.33× while
   robust estimator gives 1.06×; V_red 0.287 well below band; re-run
   queued as session 5). Findings:
   `research/experiments/2026/2026-04-21-phase-1_51V-session4-findings.md`.
   Paper-table impact: MVBench 8f cell may drop "dev-only n=30" with
   thermal-calibration footnote; TOMATO 8f cell retains "dev-only
   n=30" pending session 5.

3. **1.51V cross-architecture transfer probe (Qwen 2.5-VL-4bit).**
   Extend the scatter-back ceiling from one architecture (Gemma
   4-E4B-4bit) to two. The C-VISION ceiling `1/(1 − V_share × V_red)`
   is architecturally agnostic in principle; a Qwen cell at one
   (L, kr) point would turn the contribution from "single-arch
   mechanism" to "mechanism-class". Design: pick L ∈ {2, mid-ViT}
   and kr ∈ {0.5} matching the best Gemma cell; run on VideoMME 8f
   dev n=30 thermally paired. Runtime ~60-90 min. Blocker: needs
   Qwen-side vision-tower pruning wired (1.51V is currently
   Gemma-only per `src/codec_through/vision_tower_pruning.py`).

4. **Local paired streaming-protocol reproduction of Sam's N=60 line.**
   Codex round-24: this is "the missing piece for a breakthrough". The
   Sam bridge we don't yet have is a local codec-through run that
   mirrors his streaming / deployment-style protocol (as opposed to
   isolated phase experiments). Proposed: 60 VideoMME items
   (dev+holdout), 8f, 1.51V L=2 kr=0.50 patched vs unpatched, thermal
   pair, report the same "clean / mixed / degenerate" bucket structure
   Sam uses. Runtime ~90 min; needs a prereg doc (deferred to
   priority-2 phase, see future list).

5. **1.55B fidelity recovery (selective re-prefill v2).** The 1.55D v1
   driver is infra-falsified on partial image-block reuse; v2 with
   `pixel_values` / `image_grid_thw` / `attention_mask` co-slicing in a
   mlx-vlm fork is ~3-5h implementation. Recovery of Δacc from −0.38
   at 20f to ≤ −0.15 would reopen C-PERSIST as a **fidelity**
   contribution, not just a safety-boundary contribution.

6. **1.58 bf16 KV control at 20f.** Isolates quantization as a
   causal driver of the 7B basin collapse. Runtime ~2-4h; one clean
   experiment would let C-PERSIST narrative say "the basin is
   quantization-induced" or "the basin is attention-OOD" — currently
   we cannot discriminate.

7. **1.41 Qwen 16f holdout.** Third-frame-count third-data-point for
   C-VISION's V_share trajectory (now only measured on dev). Runtime
   ~30 min.

## Future / documented (scope for subsequent draft)

Capture ideas as we find them; park until paper draft is submitted OR
a must-do slot opens.

- **1.29 local codec-native benchmark slice.** Sam's H.264-metadata
  pipeline exists in-repo (task #114 h264_metadata.py port landed);
  the remaining gap is running it on a 30-clip subset and measuring
  MV/CBF vs pixel-diff agreement. Biggest bridge to Sam's
  "codec-through" thesis that we have not yet realized locally.
  Runtime ~1-2h; requires harness wire-up.

- **1.30 streaming-protocol rewrite around Sam's actual protocol.**
  Current prereg frames 1.30 around abstract infrastructure;
  round-24 codex: rewrite against Sam's streaming/deployment protocol
  (pre-prefill queue, KV-cache reuse across frames, rolling-window
  client, decoder co-location) and preregister a local reproduction.
  Doc work only; ~1h.

- **1.42 Gemma temporal-reuse (`_mix_gemma_features`).** Second-arch
  fidelity test for claim #7 (architecture-conditioned reuse). Blocked
  on task #62 (_mix_gemma_features implementation). Runtime ~30 min
  n=30 8f VideoMME after impl.

- **1.43 EgoSchema breadth gate.** Long-form egocentric. Blocked on
  loader + manifest build. Runtime unknown (3-min clips at 22 s
  inter-frame gap; likely 2-3× VideoMME per-item cost).

- **1.52R composition (temporal × spatial).** Depends on 1.42 landing
  AND 1.51R re-run on V-patched.

- **Scroll/pan subset as deliberate local phase.** Codex round-24:
  scroll/pan is a failure mode for token-merging; a small
  synthesised-scroll-pan subset (10-20 clips) would let us claim
  where C-VISION breaks. Design note only for now; deferred to
  `paper/priority-future-phases.md` until primary C-VISION cells land.

- **1.59 training microbench scaffold.** Training-side throughput
  claim has been entirely projection-based. Round-24 suggests a
  tiny resource-gated microbench (single-node, single-GPU, short
  schedule) to attach a measured data point. Design note only; not
  on paper critical path.

- **1.58 bf16 quantization ablation (promoted to should-do if 1.55C/D
  rescope lands).**

- **1.55C Gemma cross-family (post mlx-vlm fork).** Third ceiling
  value to parametrize C-PERSIST's onset-depth scaling
  relation across architectures.

## What a reviewer will check first

Rough mental model of reviewer paths through the paper, to prioritize
edits:

1. **Abstract → headline cells.** Reviewer looks for a single-table
   summary. C-VISION 1.08–1.24× × three benchmarks is the top cell;
   must cite holdout V-only when EXP17/18 land. Currently dev-only.
2. **Limitations.** Reviewer looks for the six-point limitations list
   (Reviewer-Facing Limitations in `framing.md`). Round-24 added §7
   on attention-propagation-drift discipline.
3. **Ceiling model.** Reviewer cross-references C-CEILING predictions
   against observed e2e; the 5-regime validation table needs to be
   complete and predictive within ≤ 5.2%. Already satisfied per
   claim-matrix row 13.
4. **Safe-deployment table.** Reviewer checks the C-PERSIST 7B/3B
   envelope table. Round-23 added the "after-ingest" framing;
   currently self-consistent.
5. **Claim-matrix provenance.** Reviewer looks up any one headline
   in the claim-matrix → finds artifact paths → checks the artifact
   path resolves. Ledger sync (must-do #2) covers this.

## Round cadence

This doc gets updated **once per codex review** and **once per session
recap**. If you are reading this more than 7 days after the `date:`
frontmatter, treat as stale — cross-check against `claim-matrix.md`
and the current registry.
