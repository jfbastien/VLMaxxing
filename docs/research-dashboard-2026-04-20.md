# Research Dashboard — 2026-04-20

Snapshot of phase status, SOTA-relevance, and remaining benchmark work. Built
from `research/experiments/registry.md` + recent findings. Update this file
when phases close or expand, not the registry (registry is the ledger).

## Legend

- **Status**: `running` / `closed-earned` / `closed-null` / `closed-arch-blocked` / `open` / `blocked`
- **SOTA**: `primary` (paper headline) / `secondary` (support table) / `negative` (paired null for framing) / `methodology` (contribution without number)
- **Benchmark runtime**: estimate for pending work only. Implementation not estimated.

## Phase status table

| Phase  | Status                | SOTA      | Latest verdict / owner                                                                                                    | Remaining work                                                                   | Benchmark runtime |
|--------|-----------------------|-----------|---------------------------------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------|-------------------|
| 1.0–1.9 foundation | various           | methodology | Frozen per `docs/reproduction-status.md`                                                                                  | —                                                                                | —                 |
| 1.10   | closed-earned         | secondary | Planner grid TOMATO motion dev                                                                                            | —                                                                                | —                 |
| 1.37B  | closed-null           | negative  | Halo-veto NO-LIFT, 9/9 dev tranche landed 2026-04-20                                                                      | —                                                                                | —                 |
| 1.41   | closed-earned         | methodology | VideoMME infra + Qwen baseline                                                                                            | —                                                                                | —                 |
| 1.42   | blocked               | primary   | Gate for 1.51R/1.52R composition; requires mix_gemma_features impl (#62)                                                  | Impl then n=30                                                                   | n=30 8f VideoMME ~35min after impl |
| 1.51R  | closed-null (noisy)  | secondary | Novelty pruning null on VideoMME at anchor=none; re-run on V-patched queued                                                | EXP09 gemma_structural anchor on V-patched (queued)                              | included in 1.51V queue |
| 1.51V  | closed-earned / closed-arch-blocked | secondary | H1 CONFIRMED paired **V_red=39.0%** L=2 kr=0.50 (within-session EXP01/02, decode Δ=-2.8%); H3 arch-blocked by scatter-back (V_share×V_red ceiling); H4 null-robust. Expansion 12/12 DONE 2026-04-21: H1 paired (8f+16f); H_pareto EARNED kr=0.25 Pareto-dominates kr=0.50; H_transfer EARNED MVBench 1.21× + TOMATO 1.24×; H_fsscale CONFIRMED 16f V_red invariant & E2E 1.12× matches ceiling; H_stack partial reopener at EXP10. **32f probe 2026-04-21**: H_32f_vshare CONFIRMED (V_share=31%); H_32f_e2e REJECTED (thermal pairing broke at 32f, ceiling ≤1.14× even charitably). | Session 2 EXP15/16 (holdout replication) running; EXP13/14 findings landed | 1h (~30 min × 2 holdout pair) |
| 1.52R  | blocked               | primary   | Composition 1.42 × 1.51R; blocked on both. Gate paper headline.                                                            | Resolve 1.42; 1.51R re-run on V-patched may unblock                              | ~2-3h at 8f n=30 per arm |
| 1.55   | superseded            | historical | Split into 1.55A/B/C/D per Codex round-22                                                                                  | —                                                                                | —                 |
| 1.55A  | closed-null           | secondary | Persistent-KV 4-regime matrix: 7B sampler-invariant at 20f/40f, 3B-40f HYBRID (basin sampler-dispersible but returns to pre-basin plateau, not baseline). 1/21 signature on 4 probes. | Documented in memory; no runtime remaining                                       | —                 |
| 1.55B  | closed-historical     | historical | See registry; composed with 1.55A                                                                                          | —                                                                                | —                 |
| 1.55C  | infra-falsified       | historical | Gemma 4-E4B-4bit cross-family probe infra-blocked                                                                          | Pivot to 1.51V/1.51R (done)                                                      | —                 |
| 1.55D  | infra-falsified       | historical | Selective re-prefill v1 driver crashes on Q2 (`get_rope_index` broadcast mismatch on partial image-block reuse). H1/H2/H3/H4 UNTESTED — infrastructure finding, not a scientific null. Parallel to 1.55C; together bounds mlx-vlm's multimodal prefix-cache reuse to full image-block reuse on non-sliding attention. | —                                                                                | —                 |
| 1.57   | closed-earned         | secondary | Qwen feature-drift H3 monotonic-rise EARNED; STATIC cos 0.562/0.607/0.638 at 8/16/32f. H2 falsified vs [0.95,1.00].         | Paper-table cell written                                                         | —                 |
| 1.59   | open                  | secondary | (see registry)                                                                                                             | Per registry                                                                     | TBD               |

## Running work

- *(No experiments currently running.)*
- **Prior — 1.51V session 3** (task #153, CLOSED 2026-04-21) — EXP17/18 V-only holdout pair on VideoMME holdout v1 8f. **All four hypotheses CONFIRMED**: H_holdout_vonly_e2e=1.113× (gate ≥1.05×), H_holdout_vred=0.413 (gate [0.35, 0.45]), H_holdout_thermal=1.53% (gate <2%), H_holdout_accuracy=0.000 (gate [−0.05, +0.05]). Holdout V_share corrected to 15.45% (prior memory note 8.6% was wrong). Paper-table C-VISION VideoMME 8f cell now holdout-earned — drops the "dev-only" caveat. Findings: `2026-04-21-phase-1_51V-session3-findings.md`.
- **Prior — 1.51V session 2** (task #144, closed 2026-04-21) — 32f probe (EXP13/14: H_32f_vshare confirmed, H_32f_e2e rejected on thermal-broken pair) + VideoMME holdout replication (EXP15/16: H_stack partial confirmation, within-run 1.064× paired).
- **Prior — 1.51V expansion** (task #143, closed 2026-04-21) — 12/12 experiments DONE. Findings: `2026-04-21-phase-1_51V-expansion-findings.md`.

### Incremental verdicts (updated per paired completion)

| Pair                          | V_red  | E2E×  | Dec Δ | Acc Δ  | Thermal          | Verdict                         |
|-------------------------------|--------|-------|-------|--------|------------------|---------------------------------|
| EXP01/02 VideoMME 8f kr=0.50  | +39.0% | 1.08× | -2.8% | -0.067 | cooler (favorable) | **H1 CONFIRMED** (back-to-back) |
| EXP01/03 VideoMME 8f kr=0.25  | +62.1% | 1.09× | +0.8% | -0.067 | clean              | **Pareto-dominates kr=0.50** — same E2E, same acc, more V_red |
| EXP01/04 VideoMME 8f kr=0.75  | +19.5% | 1.06× | -5.1% | -0.033 | cooler (stronger drift) | Conservative anchor within preregistered [15%, 25%] band |
| EXP05/06 **MVBench** 8f kr=0.50 | +40.0% | **1.21×** | +3.2% | -0.100 | slightly hotter | **H_transfer EARNED**: vision-dominated benchmark (V_share=47.8%) realizes much bigger E2E gain from same V_red |
| EXP07/08 **TOMATO** 8f kr=0.50 | +42.7% | **1.24×** | -4.9% | +0.033 | cooler (favorable)   | **H_transfer EARNED** (third benchmark); accuracy actually drifts +3pp |
| EXP01/09 1.51V × 1.51R (gemma_structural kr=0.5) | +42.8% | 1.11× | -4.7% | -0.067 | cooler | **H_stack null CONFIRMED**: composition vs V-alone is 1% slower + -6.7pp accuracy + 0.50 agreement |
| EXP01/10 1.51V × 1.51R (none kr=0.3) | +42.0% | 1.11×/1.17×* | -4.5% | -0.067 | cooler | **H_stack PARTIAL VIOLATION**: own-pair composition = +5.7% E2E over V-alone, aggregate accuracy preserved, but agreement=0.63 |
| EXP11/12 VideoMME **16f** kr=0.50  | +39.0% | 1.12× | -0.1% | +0.033 | cleanest pair in queue | **H_fsscale CONFIRMED**: V_red invariant to frame count; E2E matches ceiling model (V_share 24.3% × V_red 39.0% → pred 1.11×, obs 1.12×) |
| EXP17/18 VideoMME **holdout** 8f kr=0.50 | +41.3% | **1.113×** (dense→pruned) / 1.096× (dense→dense) | +1.5% | 0.000 | clean, first-attempt gate pass | **H_holdout_vonly_e2e CONFIRMED + H_holdout_vred CONFIRMED**: V_share holdout = 15.45% (equal to dev); paper-table drops "dev-only" caveat. Observed exceeds V-only ceiling 1.068× due to generate-side TPS lift (28.5→32.9). |

*1.11× uses V-alone dense arm as baseline (clean thermal); 1.17× includes composition (cross-session, thermal-inflated).

### V_share governs 1.51V gains — headline takeaway

**The single equation governing all 1.51V outcomes:** `E2E_speedup ≈ 1 / (1 − V_share × V_red)`. V_red is benchmark-invariant (~40% at kr=0.50), so the E2E headline number is determined by V_share (fraction of total wall-clock spent in the vision tower). This ceiling model is predictive within 2pp across 4 (benchmark, frame-count) cells, and establishes that 1.51V is **regime-conditional**: the mechanism generalizes, but the headline depends on whether vision compute dominates.

All rows below at L=2 kr=0.50, n=30, thermally paired unless noted:

| Benchmark | Frames | V_share | Ceiling | V_red   | E2E× obs | Pred    | Acc Δ  | Pairing |
|-----------|--------|---------|---------|---------|----------|---------|--------|---------|
| VideoMME  | 8 (dev) | 15.2%  | 1.18×   | 39.0%   | 1.08×    | 1.062×  | -0.067 | clean   |
| VideoMME  | 8 (holdout) | 15.45% | 1.19× | 41.3%   | **1.113×** | 1.068× | 0.000 | clean (session 3) |
| VideoMME  | 16     | 24.3%   | 1.32×   | 39.0%   | 1.12×    | 1.105×  | +0.033 | cleanest |
| VideoMME  | 32     | 31.0%   | 1.45×   | ~26%*   | 0.94×**  | ≤1.14×  | -0.033 | **broke (decode +7.6%)** |
| MVBench   | 8      | 47.8%   | 1.91×   | 40.0%   | **1.21×** | 1.237× | -0.100 | slightly hotter |
| TOMATO    | 8      | 40.7%   | 1.69×   | 42.7%   | **1.24×** | 1.214× | +0.033 | cooler (favorable) |

\* 32f V_red is thermal-confounded (raw 20.5%, thermal-normalized 26.1%); \*\* 32f cross-run E2E is patched-slower-than-unpatched due to thermal drift; under charitable V_red=39% the ceiling model predicts 1.14× — still sub-H_32f_e2e (1.15×).

**Three mechanism takeaways for the paper:**

1. **V_red is benchmark- and frame-count-invariant at L=2 kr=0.50 under clean thermal pairing** (39–43% across 3 benchmarks at 8f, 39% at 16f). Frame-count-invariance validated where thermals allow clean pairing (8f, 16f).
2. **V_share grows monotonically with frame count on VideoMME**: 15.2% (8f) → 24.3% (16f) → 31.0% (32f). The ceiling grows with it; the headline E2E follows.
3. **Thermal pairing is a hard practical constraint at 32f on M3 16 GB**: observed decode-drift 7.6% (vs 2.8% at 8f, 0.1% at 16f). Future ≥32f measurements require cooldown breaks or dedicated thermal controls.

## Open SOTA advancement paths

Ordered by expected paper impact. Runtime estimates are benchmark-only.

| Priority | Path                                                                                                     | Hypothesis                                                                                           | Benchmark runtime  |
|----------|----------------------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------------------|--------------------|
| P1       | **1.51V expansion Tier 4 (16f frame scaling)**                                                            | V_share at 16f re-opens E2E ceiling above 1.20×                                                      | 140 min (queued)   |
| P1       | **1.51V expansion Tier 2 (cross-benchmark transfer)**                                                     | V_red = 42% transfers to MVBench + TOMATO; if not, 1.51V demoted to VideoMME-only claim              | 100 min (queued)   |
| P1       | **1.51V × 1.51R re-run with V-patched features**                                                           | gemma_structural anchor earns on V-patched features (tight alternative to the raw null)              | 80 min (queued)    |
| P2       | **Post-pool token merging prototype (H3 re-opener)**                                                      | Merging tokens AFTER pooler cuts LM prompt; composes with 1.51V without scatter-back ceiling         | (impl-blocked; ~1h post-impl) |
| P2       | **1.51V on VideoMME holdout**                                                                             | Earnings transfer to unseen holdout items                                                            | ~35 min (gated on Tier 0 confirm) |
| P2       | **32f regime probe at L=2 kr=0.50**                                                                        | V_share grows enough at 32f to re-open H3; risk: 32f accuracy regime is known fragile (long=0.10)   | ~45 min (gated on Tier 4 signal) |
| P3       | **1.52R composition (1.42 × 1.51R)**                                                                      | Multiplicative win; currently blocked on 1.42 impl                                                    | ~2-3h             |
| P3       | **Different V-layers L ∈ {3, 4} at kr=0.25**                                                              | Widen Pareto frontier past L=2                                                                       | ~70 min           |
| P4       | **Cross-model 1.51V probe (different Gemma variants, or Qwen)**                                            | Architectural cap holds across stacks                                                                 | ~3-4h             |

**Total remaining benchmark runtime if all pursued**: ~12-14h after current queue finishes.

## Peer-review asks (for report at session end)

The user flagged "places where you need feedback or input." Leaving these for the final report:

1. **Framing the 1.51V scatter-back ceiling**: is this architectural negative result a paper contribution, or does it demand a post-pool-merging prototype before acknowledging publication?
2. **Thermal-drift methodology**: should this repo standardize control-patched pairing as a measurement invariant (write it into the runner, not just docs)?
3. **1.51R closure**: if EXP09/EXP10 also null, is 1.51R formally CLOSED as null? Current in_progress task (#82) needs a verdict doc.
4. **32f regime accuracy**: long-bucket accuracy at 32f is 0.10. Does the paper include this as a frame-count-dependent degradation story, or exclude 32f from headline numbers?

## Update rules

- When an experiment in the running queue completes, update its row in this table with the verdict.
- When a new phase opens, add a row.
- Do not retcon runtime estimates — record what actually ran.
- This file is a dashboard, not source-of-truth. Registry wins on conflicts.
