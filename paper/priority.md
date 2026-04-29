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
C-PERSIST, C-VISION) these priorities map to. The canonical paper-facing
narrative now lives in `paper/arxiv/sections/01_abstract.tex` and
`paper/arxiv/sections/02_introduction.tex`; superseded Markdown scratchpads
were removed from the release tree.

Narrative update 2026-04-26B: the manuscript should present the central
scientific object as the quality-compute frontier of fresh visual evidence over
time. The three regimes are still separate, but the throughline is placement:
where the runtime must buy fresh evidence, where cached state is enough, and
which evidence class proves each point.

Narrative update 2026-04-27: adaptive C-PERSIST breadth is no longer pending.
It is the current follow-up-reuse headline: n=93 / 0 observed paired drift
across 20f short/medium/long plus 32f short, 14.90×--35.92× same-class
follow-up speedup, and a 15.28×--35.97× cold-all-query ratio. Fixed K=1 remains the simple
no-coordination baseline. The 1.30AC/AD family is now a negative composition
boundary: cache reuse preserves speed but drifts, cache invalidation forces
follow-up V-pruning but kills speed, and both land at the same net aggregate
loss through different any-paired-drift sets.

Narrative update 2026-04-26: the arXiv draft now carries the larger
anti-recomputation-to-VLM-native-media agenda. That agenda is important for
the paper's shape, but it is not a new submission blocker. Machine-oriented
sidecars, sensor-fusion/world-state streams, AI-native codecs, compute-denial
robustness, and driving/robotics/screen specialization stay future work unless
the experiment registry records new local evidence.

Autonomous session 2026-04-21 status: EXP10 n=60 composition audit
(should-do #1) **CLOSED-NULL** (task #152). n=60
E2E 1.042× / lift 2.6pp / agreement 0.65; ceiling model reproduces
observation to within 0.2pp — fixed_frac = 0.875 is decode-
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
   publishability-status.** Claim-matrix has been the authoritative doc
   through round-20; registry rows had drifted. Fixed this round for phase
   1.41 (status `proposed` → `EARNED 2026-04-18`) and phase 1.55D status
   (`closed-null` → `infra-falsified`). Sweep for remaining stale rows is a
   P0 before submission; any sentence a reviewer cross-checks across two
   docs must agree.

3. **Main CI green on `main`.** Local release checks are green in the current
   cleanup tree (`make check`, `git diff --check`, `make paper-doctor`, and
   `make paper-bundle`). Remote CI should be rerun after the release-hygiene
   branch lands; without green CI the paper claims of reproducibility look
   sloppy. The PDF build is a separate local toolchain issue in this sandbox:
   Tectonic panics before TeX compilation, while the source bundle builds.

4. **Attention-propagation-drift vocabulary discipline.** Codex
   round-21 flagged that the pre-release source attributes the refresh requirement
   to attention-context drift (~0.01/frame), NOT positional-encoding
   drift. `publishability-status.md:283` landed the reconciliation.
   Now landed in `framing.md` Reviewer-Facing Limitations §7 this
   round (round-24). A direct PE-drift ablation is NOT required for
   submission provided the paper says "attention-propagation drift"
   when citing the pre-release source and treats 1.57 (adjacent-frame ViT cosine) as a
   **lower-bound proxy** rather than a direct cache-substitute
   measurement.

5. **1.51V is the primary local Gemma story, not 1.51R.** Round-22/23
   already demoted 1.51R's dev-only 1.39× aggregate to a
   "duration-conditional partial reproduction"; round-24 codex
   reiterates. 1.51R should appear in the paper as:
   - the EXP10 n=60 composition-audit gate on VideoMME holdout (one explicit
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

1. **EXP10 n=60 composition-audit thermally-paired re-check.** **CLOSED-NULL
   2026-04-21 (task #152).** n=60 arm B (V+novelty kr=0.30)
   E2E = **1.0420×**, V-only reference arm A = **1.0159×**; lift
   2.6pp FAILS the ≥4pp gate AND agreement 0.650 FAILS the ≥0.75
   gate (acc Δ −0.017 passes the −0.067 gate). Prereg primary 1.10×
   gate FAILS (below 1.08× partial-confirm by 3.8pp); thermal gate
   FAILS (decode Δ +2040 ms / 3.07% rel, adverse direction); thermal-
   correction does not cross 1.08×. Ceiling model reproduces observed
   1.042× to within 0.2pp: composition-audit fixed_frac = 0.875
   (V_share dropped to 6.26% vs dev's 15.2% — the audited session concentrated long-decode
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

4. **Local paired streaming-protocol reproduction of the pre-release N=60 line.**
   **CLOSEOUT QUEUE EXECUTED 2026-04-25; THE `kr_Q0 = 0.67` LONG-BUCKET
   CANDIDATE IS FALSIFIED.** The 1.30Z generalization test on the full
   long bucket (n=18 sessions / 54 paired queries) returned
   `Δacc = −0.130`, well past the `−0.10` rescue threshold (CI95
   `[−0.278, +0.019]`, speedup `3.12×`, format clean). The duration-
   conditioned admission policy at `kr_Q0=0.67 + kr_followup=0.50` is
   closed in this configuration, and `1.30AB` closes the neighboring
   long-Q0 sweep as well: `kr_Q0 ∈ {0.75, 0.80, 0.85, 0.90}` all fail the
   target fidelity/speed band on the full long-bucket tranche. The queue correctly
   skipped the conditional full-union rerun (`1.30AE`). The 1.30Y
   residual-pair scout was selection-biased.

   The 1.30Z/AB runs also produce the mechanism boundary: `kr_followup =
   0.50` is mechanically a no-op under prompt-cache reuse. Every
   long-bucket candidate measures
   `streaming_follow_up_vision_pruning_active_fraction = 0.0` and
   `streaming_follow_up_all_image_tokens_reused_fraction = 1.0`. **All
   1.30 lane wording must say "Q0 admission + K-cache reuse," never
   "follow-up vision pruning."**

   The best landed bridge result remains `1.30W` (full-union dense Q0,
   n=171, `Δacc = −0.0585`, `2.79×`) — a "bounded near-miss" against the
   `3.0×` rescue floor. The high-keep-rate AB cells are useful because
   they restore aggregate Q0 accuracy but still lose follow-up accuracy
   by ~19pp; do **not** describe that as exact per-row Q0 preservation.
   It shows that first-answer aggregate correctness is insufficient to
   certify the reused cache state.

   Completed follow-ups:

   - **1.30AC** forced cache invalidation so follow-up V-pruning actually
     fires. It lands at **1.06×** and the same net aggregate loss as the
     cache-reuse lane, so it is a negative composition result rather than an
     active follow-up-pruning win.
   - **1.30AD** instruments the `1.30W` path and confirms the near-miss
     mechanism: dense Q0 + K-cache reuse gives **3.02×** but still loses
     follow-up accuracy. The AC/AD drift sets are not row-identical (Jaccard
     0.3125), so paper wording should say "same net aggregate boundary," not
     "byte-equivalent."

   Remaining follow-ups (ordered by current paper leverage):

   - **Direct cache-state instrumentation** — K-cache distance or equivalent
     per-layer state probe to explain why the AC and AD mechanisms meet the
     same aggregate boundary.
   - **1.30AB-fine @ 0.95** — optional boundary cleanup (~30 min). Useful
     only if we need to characterize the sharp 0.90→1.0 transition.

   1.30X remains important, but its `Δacc = 0.0000`, `3.0781×` point is
   an **oracle upper bound**, not a deployable policy. The lane is closed
   at the tested keep-rates pending direct cache-state instrumentation.

5. **1.55 selective re-prefill frontier (fidelity recovery).** The v1
   driver was infra-falsified, but that is no longer the live state.
   Repo-local v2 now runs the intended multimodal tail-reprefill regime.
   **Fixed K=1** now spans 20f short, medium, long, plus 32f short. The
   adaptive post-Q2-state policy now spans the same breadth and is the current
   headline result.

   | run | regime | n_paired | paired diffs | speedup (same-class) | pathology | RSS |
   | --- | --- | --- | --- | --- | --- | --- |
   | 1.55D K=1 | 20f short, 7 clips | 21 | 0/21 / 0/21 | 9.48× | 0/14 follow-up, 0/7 Q3 | 4.886 GB |
   | 1.55G K=1 | 20f medium, 10 clips | 30 | 0/30 / 0/30 | 10.76× | 0/20 follow-up, 0/10 Q3 | 6.097 GB |
   | 1.55I K=1 | 20f long, 7 clips | 21 | 0/21 / 0/21 | 11.24× | 0/14 follow-up, 0/7 Q3 | 5.940 GB |
   | 1.55H K=1 | 32f short, 7 clips | 21 | 0/21 / 0/21 | 20.37× | 0/14 follow-up, 0/7 Q3 | 5.821 GB |
   | **fixed combined** | 20f short/medium/long + 32f short | **93** | **0/93 / 0/93** | 9.48-20.37× | **0/62 follow-up, 0/31 Q3** | 4.9-6.1 GB |
   | **1.55F adaptive breadth** | 20f short/medium/long + 32f short, post-Q2 state | **93** | **0/93 / 0/93** | **14.90-35.92× same-class** (**15.28-35.97× all-query**) | **0/62 follow-up, 0/31 Q3** | 1.44-6.09 GB |

   RSS in this table is the summary-level peak reported by each run summary.
   The separate 1.66 memory characterization reads row-level JSONL memory
   signals too and sees larger transient peaks in some C-PERSIST artifacts
   (up to 13.61 GB). The 1.63 family now has clearly marked measured
   sparse-execution boundary cells and one clean Gemma operating point, so use
   1.66 to keep manuscript memory claims denominator-specific. Do not say the
   observed process working set stayed under the 12 GB MLX allocation cap.

   K=2 and K=4 remain useful lower-speed comparison points (`6.72×`
   and `3.66×`). With n=93 zero observed paired drift in the fixed lane,
   the upper one-sided 95% CI on the diff rate is ≈ 3.2% (rule-of-three
   on n=93); the paper claim should remain "no observed paired drift."
   The long-bucket fixed cell preserves a weak baseline (`7/21`), so it
   is a fidelity repair result under a hard regime, not a long-bucket
   quality result.

   **1.55E (`Q2=K1`, `Q3=K0`) FALSIFIES cleanly** with
   `Δacc = -0.0952`, paired correctness diffs `4/21`, paired choice
   diffs `6/21`, and pathological-like outputs on `7/7` third queries.
   **1.55F (`Q2=K1`, `Q3=K0` with `q3_cache_source=post_q2_repaired`)
   now PASSES** across the broad tranche with `0/93` paired diffs. This is the
   clearest mechanism result: the 1.55E Q3 catastrophe was caused by inheriting
   the wrong cache state, not by adaptive repair being impossible. Stage timing
   explains the additional speedup over fixed K=1: adaptive Q3 reuses the
   post-Q2-repaired cache and re-prefills only the question tail, while fixed
   K=1 re-prefills the last-frame block on every Q3.

   Pending follow-ups, in order of paper leverage:

   - **Many-turn stability stress** — 10/20/50 follow-ups to test whether
     paired drift remains flat or accumulates after the current two-follow-up
     sessions.
   - **Sampler sweep closed for the short mechanism cell (1.55K)** — adaptive
     reuse was tested at \(T=0.0,0.5,0.7,1.0,1.5\). It is reviewer-defense
     evidence that the mechanism is not greedy-only; because the sweep is one
     short-cell tranche and has small nonzero diffs at \(T=0.7/1.0\), the
     remaining paper claim should be "practical temperature sweep," not
     universal sampler invariance.
   - **Cross-architecture C-PERSIST** — blocked on Gemma sliding-window /
     RotatingKVCache prompt-cache semantics, not on model availability.

   **Do not confuse this with 1.55B**, which is the later persistent-KV
   × decode-acceleration composition phase and still depends on 1.54
   landing first.

6. **1.58 bf16 KV control at 20f.** Isolates quantization as a
   causal driver of the 7B basin collapse. Runtime ~2-4h; one clean
   experiment would let C-PERSIST narrative say "the basin is
   quantization-induced" or "the basin is attention-OOD" — currently
   we cannot discriminate. Wrapper + analyzer landed 2026-04-22 in
   `scripts/run_phase1_58_bf16_control.sh` and
   `scripts/analyze_phase1_58_bf16_control.py`; remaining blockers are
   now concrete rather than abstract: the local preflight confirms the
   bf16 checkpoint is absent at the configured `$QWEN_BF16_MODEL_PATH`,
   and the current single-laptop plan keeps autonomous runs near a `10 GB`
   RSS ceiling. Since the prereg's own feasibility bar was much looser
   (`<14 GB`), this lane is blocked locally even if the weights appear unless
   we explicitly relax the machine policy.

**Supporting closeout analysis:** no MLX time. The paper now has three separate
observations that all say "aggregate metrics alone are incomplete": `1.30`
V-only Q0 flips, `1.42` Gemma aggregate-preserved-but-identity-drifting
MVBench reuse, and `1.55A` persistent-KV pathological attractors.
`scripts/build_per_item_drift_summary.py` now builds a single JSON payload for
that figure. The manuscript now surfaces this as a generated paired-drift
table; the remaining upgrade is editorial/visual polish, not evidence
collection.

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
   per codex round-26** — this is the biggest single missing scale-out bridge.
   The H.264-metadata pipeline already exists in-repo (task #114
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
   point but is holdout-blind at this n. **REPLICATION/BREADTH 2026-04-23**
   (Codex continuation): corrected the impossible "n=30 short" follow-up to
   dev-short n=10 + holdout-short n=10 + all-duration dev n=30. Short
   dev+holdout n=20 passes on the -5pp boundary; all-duration dev n=30
   passes strongly with codec-dense agreement **1.000 (30/30)**,
   codec-accuracy = dense-accuracy = **0.533**, codec-pixel agreement 0.933,
   reuse gap 1.6pp, parse failures 0. This is now a local codec-native
   planner-substitution row, not a systems speed row: offline codec extraction
   took 7290s on dev n=30. **CALIBRATION ABLATIONS CLOSED 2026-04-24**:
   short n=20 pooled/per-item and live-pixel/artifact runs were answer-level
   identical, and the all-duration dev n=30 artifact-source rerun exactly
   reproduced the live-pixel breadth row (all headline metrics unchanged,
   answer-level diffs = 0). The remaining gate is streaming-decoder
   integration, not semantic calibration. Findings doc:
   `research/experiments/2026/2026-04-23-phase-1_29B-codec-native-replication-prereg.md`.

9. **Paper figures: C-PERSIST tested-envelope table + V_share-governs-
   C-VISION-gains plot.** **LANDED 2026-04-21 (autonomous session).**
   Both figures rendered from already-landed experimental data via
   `scripts/plot_c_persist_safe_budget.py` and
   `scripts/plot_v_share_v_red_ceiling.py`. Artifacts:
   `paper/figures/c_persist_safe_budget.{png,_data.json}` — two-panel
   Δacc vs frames + follow-up speedup vs frames, 7B/3B overlaid with
   tested/tolerated envelope shading; the 3B basin is now bracketed to
   (36f, 40f] rather than treated as a clean-safe range. And
   `paper/figures/v_share_v_red_ceiling.{png,_data.json}` — Gemma
   dev/holdout, Qwen cross-arch, measured sparse-execution, and
   composition-audit regimes against the
	   `1/(1 − V_share × V_red)` curve; dev median |Δ| = 2.2pp, holdout
	   max 13.6pp (MVBench 8f, thermal-inflated and advisory per Session 4
	   findings). The n=60 composition-audit cell sits at product 0.027 / E2E 1.042× —
   the CLOSED-NULL data-point visible at the bottom-left of the curve.
   No new runs; paper-draft work only. Commit: follow-up.

## Future / documented (scope for subsequent draft)

Capture ideas as we find them; park until paper draft is submitted OR
a must-do slot opens.

- **1.30 session/streaming bridge — INITIAL NEGATIVE, THEN 1.30W
  NEAR-MISS 2026-04-24.** The original reproduction landed as a paired
  cold-vs-streaming Qwen 2.5-VL-7B-4bit VideoMME 8f **dev+holdout union
  n=57 sessions / 171 queries**: cold 0.561 / streaming 0.368 →
  **3.326× paired amortized speedup PASS, Δacc = −0.193 FALSIFIES the
  ±0.05 preregistered budget**. Codex round-28 then decomposed the stack
  and showed the dominant error is V-only Q0 pruning (H_V PASS; H_K and
  H_interaction FAIL; H_reset PASS; H_path PASS against 1.51V), which
  motivated the dense-Q0 rerun. The successor `1.30W` policy ("Q0 dense,
  Q2/Q3 pruned") substantially improves fidelity: cold 0.561 /
  streaming 0.503 → **Δacc = −0.0585**, paired speedup **2.7869×**,
  `0` parse failures, `0` degenerates. Q0 is solved exactly
  (`34/57` in both arms); every remaining miss is follow-up-only. But
  the preregistered rescue gate still fails because speed remains below
  `3.0×`, and that miss is structural under the 3-query protocol: dense
  Q0 alone already exceeds the `3.0×` target even if follow-ups were
  free. The next meaningful continuation is therefore **not** another
  same-protocol follow-up tweak; it is either a cheaper safe-Q0 policy
  or a longer-session protocol that can honestly amortize dense Q0.
  Findings:
  `research/experiments/2026/2026-04-24-phase-1_30W-q0-dense-followup-pruned-full-findings.md`.
  Immediate fixed-rate rescue also fails: 1.30V Q0 scout at kr=0.67 and
  kr=0.75 still lands at 0.70 accuracy on the same Q0 items, so the next
  paper-relevant move is an admission policy (skip pruning on risky Q0),
  not another blind fixed-kr composition run.

- **1.42 Gemma temporal-reuse (`_mix_gemma_features`).** Second-arch
  fidelity test for claim #7 (architecture-conditioned reuse).
  **LANDED 2026-04-24 as a split result.** Infrastructure and mechanism
  work are both complete: the Track A Gemma mixing path, cached-feature
  extraction, checked launchers, and the 1.57 mechanism lane are now in
  `main`. The second-architecture holdout pair now says something
  concrete: **TOMATO motion N=30 passes** (`agreement=0.933`,
  `dense_acc=cached_acc=0.267`), but **MVBench motion N=30 fails the
  strict-agreement gate** (`agreement=0.733`,
  `dense_acc=cached_acc=0.200`) while preserving aggregate accuracy
  exactly. This means claim #7 is no longer blocked on execution; it is
  blocked only if we want to upgrade it beyond a benchmark-conditional
	  spectrum story. Gemma measured-sparse-execution baselines are now exploratory rather
  than claim-bearing because the prereg promotion rule required both
  holdout cells to pass.

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
   worst 5.2% error) and the C-VISION rendered view with **9 points**
   total: 4 Gemma dev cells, 3 Gemma holdout cells, 1 matched Qwen
   cross-architecture point, and 1 composition-audit null. Already
   satisfied per claim-matrix row 13 and row 15.
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
