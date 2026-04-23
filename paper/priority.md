---
date: 2026-04-23
parent: paper/framing.md
status: living priority doc — updated each codex round + each session recap
---

# Paper Priority: must-do / should-do / future

Triage of outstanding work against the paper submission bar. Updated per
Codex round-26 (2026-04-21, ledger-contradiction sweep: elevate 1.29 in
should-do, drop "currently dev-only" phrasing from reviewer-path §,
re-confirm 1.51V as primary local Gemma story and 1.51R as the EXP10
n=60 gate plus Stage-5 anchor default). Priority.md is now the
authoritative venue-readiness / submission-gate doc; claim-matrix.md
and publishability-status.md are expected to conform to this file.
See `paper/framing.md` for the three major contributions (C-CEILING,
C-PERSIST, C-VISION) these priorities map to, and `paper/abstract.md`
+ `paper/intro.md` for the paper-facing three-contributions narrative
(landed 2026-04-21).

Autonomous session 2026-04-21 status: EXP10 n=60 H_stack composition
re-check (should-do #1) **CLOSED-NULL** (task #152). Pooled n=60
E2E 1.042× / lift 2.6pp / agreement 0.65; ceiling model reproduces
observation to within 0.2pp — pooled fixed_frac = 0.875 is decode-
dominated, arithmetic ceiling at per-token speedup 1.446× is 1.041×.
Composition-appendix claim does not land; three-contribution spine
unchanged. See `research/experiments/2026/2026-04-21-phase-1_51V-exp10-n60-findings.md`.

Round-25 status: must-do #1 (VideoMME 8f V-only holdout pair) CLOSED;
should-do #2 (MVBench + TOMATO V-only holdout pairs) **three-benchmark
C-VISION trifecta effectively closed** with differentiated advisory
strength — **VideoMME 8f CLOSED clean** (session 3 EXP17/18); **MVBench
8f CLOSED-ADVISORY** (session 4 EXP19/20: E2E 1.407× far exceeding dev
1.21×, V_red 0.471, acc Δ −0.033; thermal gate 11.66% formally fails
but 50 ms absolute delta is OS-jitter scale on MVBench's 432 ms decode
window; calibration-revision proposed); **TOMATO 8f EARNED-ADVISORY**
(session 5 EXP23/24 rerun 2026-04-21: E2E 1.194× sum-ratio mean, median
1.232×, clears 1.15× gate; V_red 0.350 below [0.38, 0.48] band by 0.03;
decode Δ 119.7 ms = 3.51% rel in FAVORABLE direction — patched arm
cooler than reference, observed speedup conservatively under-stated
not inflated; ceiling model predicts 1.155×, observed + friendly drift
consistent). Session 4 TOMATO EXP21/22 had hostile +206 ms drift and
was unreliable; session 5 is qualitatively much cleaner (favorable
direction + zero dense-arm outliers). Findings:
`research/experiments/2026/2026-04-21-phase-1_51V-session5-findings.md`.
Driver bug fixed session 4: `_count_frames` metadata fast path removed
after 0298-00.mp4 reported `stream.frames=366` while iterative decode
yielded only ~235 decodable frames.

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

1. **EXP10 n=60 H_stack thermally-paired re-check.** **CLOSED-NULL
   2026-04-21 (task #152).** Pooled n=60 arm B (V+novelty kr=0.30)
   E2E = **1.0420×**, V-only reference arm A = **1.0159×**; lift
   2.6pp FAILS the ≥4pp gate AND agreement 0.650 FAILS the ≥0.75
   gate (acc Δ −0.017 passes the −0.067 gate). Prereg primary 1.10×
   gate FAILS (below 1.08× partial-confirm by 3.8pp); thermal gate
   FAILS (decode Δ +2040 ms / 3.07% rel, adverse direction); thermal-
   correction does not cross 1.08×. Ceiling model reproduces observed
   1.042× to within 0.2pp: pooled fixed_frac = 0.875 (V_share dropped
   to 6.26% vs dev's 15.2% — pooled session concentrated long-decode
   items / warm-decoder state), so arithmetic ceiling at the observed
   per-token generate speedup (1.446×) is 1.041×. Mechanism intact;
   regime binds. **Composition appendix claim does NOT land**; the
   paper's three-contribution spine is unchanged. Remove from
   should-do queue. Findings:
   `research/experiments/2026/2026-04-21-phase-1_51V-exp10-n60-findings.md`.

2. **1.51V MVBench and TOMATO holdout unpatched-vs-patched pairs.**
   **CLOSED 2026-04-21** — three-benchmark C-VISION trifecta achieved
   with differentiated advisory strength. **MVBench 8f CLOSED-ADVISORY**
   (EXP19/20: E2E 1.407× far exceeding dev 1.21×, V_red 0.471 OOB+
   favorable, acc Δ −0.033; thermal gate formally fails at 11.66% but
   50 ms absolute is OS-jitter on MVBench's 432 ms decode window —
   calibration revision: `|Δ| < max(0.02 × decode_ms, 100 ms)`).
   **TOMATO 8f EARNED-ADVISORY** (session 5 EXP23/24 2026-04-21:
   E2E sum-ratio mean **1.194×** clears 1.15× gate, median 1.232×;
   V_red 0.350 below [0.38, 0.48] band by 0.03; decode Δ 119.7 ms =
   3.51% in FAVORABLE direction — EXP24 patched arm ran cooler than
   EXP23 reference, so observed speedup is conservatively under-stated,
   not inflated; scatter-back ceiling predicts 1.155×; consistent with
   ceiling + small friendly thermal correction; acc Δ −0.067).
   Findings: `research/experiments/2026/2026-04-21-phase-1_51V-session5-findings.md`.
   Paper-table impact: MVBench 8f cell drops "dev-only n=30" caveat
   with thermal-calibration footnote; TOMATO 8f cell drops "dev-only
   n=30" caveat with favorable-drift footnote. No further TOMATO rerun
   required for paper-grade claim.

3. **1.51V cross-architecture transfer probe (Qwen 2.5-VL-4bit).**
   **CLOSED 2026-04-23.** The scatter-back ceiling now transfers from
   Gemma 4-E4B-4bit to Qwen 2.5-VL-7B-4bit at matched
   \(L=2\), \(kr_V=0.50\) on VideoMME 8f dev n=30. All preregistered
   gates passed: `V_red = 0.398`, `E2E = 1.044× observed vs 1.043×
   predicted`, aggregate `Δacc = −0.033`. **Paper impact:** C-VISION
   upgrades from single-architecture mechanism to two-architecture
   mechanism evidence. The remaining optional follow-up is broader
   benchmark coverage on Qwen, not proof-of-transfer.

4. **Local paired streaming-protocol reproduction of Sam's N=60 line.**
   **SPEEDUP PASS / FIDELITY FALSIFIED 2026-04-23.** The local Qwen
   7B 8f dev+holdout-union bridge mirrors the session/streaming
   composition enough to test the paper-promotion rule: paired
   amortized speedup lands at 3.326×, but accuracy drops by 19.3 pp and
   fails the preregistered ±0.05 budget. The next work is root-cause
   decomposition (H_V / H_K / H_interaction / H_reset / H_path), not
   unqualified promotion of the stacked result.

5. **1.55D v2 selective re-prefill (fidelity recovery).** The 1.55D v1
   driver is infra-falsified on partial image-block reuse; v2 with
   `pixel_values` / `image_grid_thw` / `attention_mask` co-slicing in a
   mlx-vlm fork is ~3-5h implementation. Qwen-only v2 driver scaffolding
   landed 2026-04-22 in `scripts/run_kv_selective_reprefill_v2.py` and
   `scripts/run_phase1_55D_v2.sh`; what remains is the auxiliary-tensor
   co-slicing work inside mlx-vlm. Recovery of Δacc from −0.38 at 20f
   to ≤ −0.15 would reopen C-PERSIST as a **fidelity** contribution,
   not just a safety-boundary contribution. **Do not confuse this with
   1.55B**, which is the later persistent-KV × decode-acceleration
   composition phase and still depends on 1.54 landing first.

6. **1.58 bf16 KV control at 20f.** Isolates quantization as a
   causal driver of the 7B basin collapse. Runtime ~2-4h; one clean
   experiment would let C-PERSIST narrative say "the basin is
   quantization-induced" or "the basin is attention-OOD" — currently
   we cannot discriminate. Wrapper + analyzer landed 2026-04-22 in
   `scripts/run_phase1_58_bf16_control.sh` and
   `scripts/analyze_phase1_58_bf16_control.py`; remaining blockers are
   the bf16 checkpoint and 16 GB RSS feasibility.

7. **1.41 Qwen 16f holdout.** **LANDED 2026-04-21 (autonomous session,
   task #160).** Ran n=30 on `videomme_holdout_v1.toml`, identity cache,
   16f. **H1 pass (edge)** — aggregate 0.700 (21/30) at upper bound of
   [0.50, 0.70]; **H2 FALSIFIES** — long-bucket regression at 16f is
   dev-only (holdout 16f long **0.900** vs dev 16f long 0.100 / dev 8f
   long 0.300; non-monotone shape did NOT replicate). H3/H4/H5 pass;
   parse_failures=0, agreement=1.000, peak RSS 7.23 GB. **Paper impact:**
   the "16f long-bucket regresses by 20pp" claim must soften to
   "dev-split observation; does not replicate on disjoint holdout";
   1.57 attention-mixing co-saturation framing stays intact but is
   local to dev. Claim 8 (VideoMME breadth gate) now covers dev+holdout.
   No C-VISION / C-PERSIST / C-CEILING cells move. Findings:
   `research/experiments/2026/2026-04-21-phase-1_41-qwen-videomme-16f-holdout-findings.md`.

8. **1.29 local codec-native benchmark slice.** **Promoted from future
   per codex round-26** — this is the biggest single missing Sam bridge.
   Sam's H.264-metadata pipeline already exists in-repo (task #114
   `h264_metadata.py` port landed); the remaining gap is running it on
   a 30-clip subset and measuring MV/CBF agreement vs our pixel-diff
   baseline. Closing this elevates the paper's codec-through thesis
   from "analog implementation" to "codec-native implementation with
   local benchmark evidence". Runtime ~1-2 h benchmark-only; blocker is
   harness wire-up (not a prereg — prereg landed task #98 2026-04-20).
   **PRE-INTEGRATION AUDIT 2026-04-22**: full-bucket pilot (5 items
   stratified short/medium/long) exceeded session compute budget; native-
   rate H.264 extract over long-bucket VideoMME clips dominates runtime.
   Short-bucket-only follow-up pilot (5 short items, ~100s compute)
   **HARD-FALSIFIED 2026-04-22**: codec OR-aggregated class shares
   degenerate to **100% NOVEL on every sparse pair of every item**; mean
   |Δ| vs pixel-diff = **53.8pp** (gate: 10pp). Root cause: at sparse 8f
   sampling, ~250-400 native-rate frames per pair-span include ~30-60
   I-frames; MAX-over-span locks every MB to NOVEL.
   **CONTINUOUS-SCORE PARTIAL PASS 2026-04-22**: redesign option (b)
   implemented as
   `scripts/pilot_1_29_continuous_codec_score.py` — continuous per-MB
   `fraction_of_native_frames_with_intra_or_cbf` + global quantile
   calibration to match pixel-diff aggregate. On the same 5 short items:
   aggregate max|Δ| = **7.9pp (PASSES 10pp gate)** but per-item
   max|Δ| = **16-25pp (FAILS per-item gate)**; Spearman ρ(pix_STATIC,
   codec_STATIC) = +0.40 (n=5, not significant at α=0.05). Two failure
   modes: extreme-STATIC items saturate (037-2 → 100% STATIC) and
   moderately-dynamic items over-predict NOVEL. **PLANNER-ACCURACY
   PROBE FIRST-POINT CONFIRMED 2026-04-23** (commit 495a57b): n=10
   short-bucket VideoMME Qwen 2.5-VL-7B-4bit paired run of codec-
   planner + per-item live-pixel calibration vs dense — **codec-dense
   agreement 1.00 (10/10)**, codec-accuracy = dense-accuracy = 0.80,
   codec-minus-pixel = +0.10 pp, reuse-ratio parity within 1pp. The
   preregistered accuracy-within-decision-band clause PASSES at first-
   point but is holdout-blind at this n. Next: n=30 short replication,
   medium/long bucket extension, and a calibration-mode ablation
   (ratio-only vs RD-like). Findings doc:
   `research/experiments/2026/2026-04-23-phase-1_29-planner-accuracy-probe-findings.md`.

9. **Paper figures: C-PERSIST safe-deployment table + V_share-governs-
   C-VISION-gains plot.** **LANDED 2026-04-21 (autonomous session).**
   Both figures rendered from already-landed experimental data via
   `scripts/plot_c_persist_safe_budget.py` and
   `scripts/plot_v_share_v_red_ceiling.py`. Artifacts:
   `paper/figures/c_persist_safe_budget.{png,_data.json}` — two-panel
   Δacc vs frames + follow-up speedup vs frames, 7B/3B overlaid with
   safe-deploy shading; threshold scaling ratio 14500/8100 ≈ 1.79
   matches the ~1.6× basin-onset-depth-scaling claim. And
   `paper/figures/v_share_v_red_ceiling.{png,_data.json}` — 9 rendered
   regimes (4 Gemma dev + 3 Gemma holdout + 1 matched Qwen dev +
   1 pooled EXP10 n=60) against the
   `1/(1 − V_share × V_red)` curve; dev median |Δ| = 2.2pp, holdout
   max 11.6pp (MVBench 8f, thermal-inflated and advisory per Session 4
   findings). Pooled n=60 cell sits at product 0.027 / E2E 1.042× —
   the CLOSED-NULL data-point visible at the bottom-left of the curve.
   No new runs; paper-draft work only. Commit: follow-up.

## Future / documented (scope for subsequent draft)

Capture ideas as we find them; park until paper draft is submitted OR
a must-do slot opens.

- **1.30 Sam session/streaming bridge — NEGATIVE RESULT + root-cause
  decomposition in flight 2026-04-23.** The reproduction landed (1ecfeb9
  / e9d1223) as a paired cold-vs-streaming Qwen 2.5-VL-7B-4bit VideoMME
  8f **dev+holdout union n=57 sessions / 171 queries**: cold 0.561 /
  streaming 0.368 → **3.326× paired amortized speedup PASS, Δacc =
  −0.193 FALSIFIES the ±0.05 preregistered budget**; the deployment-
  grade C-VISION composition promotion rule does NOT trigger. Codex
  round-28 observed the paired data: Q0 (first query) alone drops
  0.596 → 0.491 (Δ = −0.105), violating the budget before any KV reuse —
  so the negative cannot be attributed purely to follow-up KV-
  contamination.
  A 2×2 decomposition prereg (commit 92350ad) factorizes the stack into
  V-only (kr_V=0.50 vision pruning) × K-only (persistent-KV reuse) plus
  two hard-reset controls and a Q0 parity check against the mechanism-
  grade 1.51V pipeline. Five hypotheses (H_V / H_K / H_interaction /
  H_reset / H_path) with quantitative gates and interpretation rules.
  Runtime: Phase A short scout ~75 min (6 arms × short-only dev),
  Phase B Q0 parity ~10 min, Phase C conditional full ~6h (dev+holdout
  union). Gemma port (driver hard-fails on non-Qwen, lines 303-308) and
  adjacent-cos refresh policy (threshold branch hard-fails as not-
  implemented, lines 286-290) explicitly deferred behind Phase A
  adjudication. Prereg:
  `research/experiments/2026/2026-04-23-phase-1_30-rootcause-prereg.md`.
  Findings (pre-decomposition):
  `research/experiments/2026/2026-04-23-phase-1_30-sam-streaming-findings.md`.

- **1.42 Gemma temporal-reuse (`_mix_gemma_features`).** Second-arch
  fidelity test for claim #7 (architecture-conditioned reuse). Blocked
  on task #62 (_mix_gemma_features implementation). Runtime ~30 min
  n=30 8f VideoMME after impl.

- **1.43 EgoSchema breadth gate.** Long-form egocentric. Blocked on
  loader + manifest build. Runtime unknown (3-min clips at 22 s
  inter-frame gap; likely 2-3× VideoMME per-item cost).

- **1.52R composition (temporal × spatial).** Depends on 1.42 landing
  AND 1.51R re-run on V-patched.

- **Phase 1.60 scroll/pan subset** (CLOSED 2026-04-23 as a VideoMME
  corpus limitation). Codex rounds 24-25 identified scroll/pan as a
  plausible C-VISION boundary, and the preregistration landed in
  `research/experiments/2026/2026-04-21-phase-1_60-scroll-pan-subset-prereg.md`.
  The wider Path-A VideoMME audit scanned 60 natural items stratified
  20 short / 20 medium / 20 long across 8f, 16f, and 32f feature-drift
  passes. Result: **0/60** items cleared the relaxed
  `shifted_fraction >= 0.30` gate; the maximum observed shifted fraction
  was **0.125** (`videomme:long:669-1` at 16f), far below both the
  relaxed gate and the original 0.60 prereg threshold. This is not a
  C-VISION model failure; it says natural VideoMME is montage/cut-heavy
  and lacks the sustained egomotion/scroll regime needed for this probe.
  Source note:
  `research/experiments/2026/2026-04-23-phase-1_60-corpus-limitation-findings.md`.
  Reopen only with a different corpus (EgoSchema, EPIC-Kitchens, Ego4D)
  or a clearly-labeled synthetic/hand-labeled scroll/pan set.

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
   summary. C-VISION remains the top first-pass cell. The holdout V-only
   trifecta is closed with differentiated status and should be cited
   that way everywhere: VideoMME 8f clean, MVBench 8f advisory on the
   thermal-calibration footnote, TOMATO 8f earned-advisory on the
   favorable-direction drift footnote. Dev-only phrasing should no
   longer survive anywhere in the manuscript for the three-benchmark
   cells.
2. **Limitations.** Reviewer looks for the six-point limitations list
   (Reviewer-Facing Limitations in `framing.md`). Round-24 added §7
   on attention-propagation-drift discipline.
3. **Ceiling model.** Reviewer cross-references C-CEILING predictions
   against observed E2E. Two counts appear in the paper and both must
   be self-consistent: the C-CEILING **7 regime dimensions** on Gemma
   (8/32-frame × benchmark × keep-rate × anchor arm, median 2.1% /
   worst 5.2% error) and the C-VISION **5 scatter-back points** in the
   n=30 ceiling-validation table (4 vision-axis cells + 1 H_stack
   LLM-axis cell, predictive within 2.7 pp). The rendered figure adds
   3 holdout cells + 1 pooled EXP10 n=60 for 8 scatter points total.
   Already satisfied per claim-matrix row 13 and row 15.
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
