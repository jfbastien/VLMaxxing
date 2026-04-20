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
| 1.51V  | closed-earned / closed-arch-blocked | secondary | H1 EARNED V_red=42% L=2 kr=0.50 (thermally normalized); H3 arch-blocked at 1.16× by scatter-back; H4 null-robust | **Expansion queue running** (12 exps Tier 0-4: pair confirm, Pareto, MVBench/TOMATO transfer, 16f, stack re-run) | **~7.7h running** |
| 1.52R  | blocked               | primary   | Composition 1.42 × 1.51R; blocked on both. Gate paper headline.                                                            | Resolve 1.42; 1.51R re-run on V-patched may unblock                              | ~2-3h at 8f n=30 per arm |
| 1.55   | superseded            | historical | Split into 1.55A/B/C/D per Codex round-22                                                                                  | —                                                                                | —                 |
| 1.55A  | closed-null           | secondary | Persistent-KV 4-regime matrix: 7B sampler-invariant at 20f/40f, 3B-40f HYBRID (basin sampler-dispersible but returns to pre-basin plateau, not baseline). 1/21 signature on 4 probes. | Documented in memory; no runtime remaining                                       | —                 |
| 1.55B  | closed-historical     | historical | See registry; composed with 1.55A                                                                                          | —                                                                                | —                 |
| 1.55C  | infra-falsified       | historical | Gemma 4-E4B-4bit cross-family probe infra-blocked                                                                          | Pivot to 1.51V/1.51R (done)                                                      | —                 |
| 1.55D  | closed-null           | negative  | Selective re-prefill null                                                                                                  | —                                                                                | —                 |
| 1.57   | closed-earned         | secondary | Qwen feature-drift H3 monotonic-rise EARNED; STATIC cos 0.562/0.607/0.638 at 8/16/32f. H2 falsified vs [0.95,1.00].         | Paper-table cell written                                                         | —                 |
| 1.59   | open                  | secondary | (see registry)                                                                                                             | Per registry                                                                     | TBD               |

## Running work

- **1.51V expansion** (this session, task #143) — started 2026-04-20 12:07 UTC. Runner: `scripts/run_phase1_51V_expansion.sh`. Monitor: `b9ute7uca`. ETA 7.7h ± model-load overhead. Each experiment commits incrementally after analyst validation (via `scripts/analyze_phase1_51V_expansion.py`).

### Incremental verdicts (updated per paired completion)

| Pair                          | V_red  | E2E×  | Dec Δ | Acc Δ  | Thermal          | Verdict                         |
|-------------------------------|--------|-------|-------|--------|------------------|---------------------------------|
| EXP01/02 VideoMME 8f kr=0.50  | +39.0% | 1.08× | -2.8% | -0.067 | cooler (favorable) | **H1 CONFIRMED** (back-to-back) |
| EXP01/03 VideoMME 8f kr=0.25  | +62.1% | 1.09× | +0.8% | -0.067 | clean              | **Pareto-dominates kr=0.50** — same E2E, same acc, more V_red |
| EXP01/04 VideoMME 8f kr=0.75  | +19.5% | 1.06× | -5.1% | -0.033 | cooler (stronger drift) | Conservative anchor within preregistered [15%, 25%] band |
| EXP05/06 **MVBench** 8f kr=0.50 | +40.0% | **1.21×** | +3.2% | -0.100 | slightly hotter | **H_transfer EARNED**: vision-dominated benchmark (V_share=47.8%) realizes much bigger E2E gain from same V_red |
| EXP07/08 **TOMATO** 8f kr=0.50 | +42.7% | **1.24×** | -4.9% | +0.033 | cooler (favorable)   | **H_transfer EARNED** (third benchmark); accuracy actually drifts +3pp |
| EXP01/09 1.51V × 1.51R (gemma_structural kr=0.5) | +42.8% | 1.11× | -4.7% | -0.067 | cooler | **H_stack null CONFIRMED**: composition vs V-alone is 1% slower + -6.7pp accuracy + 0.50 agreement |

Three-benchmark summary (all at L=2 kr=0.50, 8f, n=30 each, thermally paired):

| Benchmark | V_share | Ceiling | V_red | E2E× | Acc Δ  |
|-----------|---------|---------|-------|------|--------|
| VideoMME  | 15.2%   | 1.18×   | 39%   | 1.08× | -0.067 |
| MVBench   | 47.8%   | 1.91×   | 40%   | 1.21× | -0.100 |
| TOMATO    | 40.7%   | 1.69×   | 43%   | 1.24× | +0.033 |

**V_red is benchmark-invariant (~40% at kr=0.50)**; E2E scales with V_share as the architectural ceiling model predicts. 1.51V is a regime-conditional speedup: the mechanism generalizes, the headline number depends on whether vision tower dominates E2E. On the two vision-dominated benchmarks (TOMATO, MVBench) 1.51V delivers >1.2× E2E at ~40% V_red.

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
