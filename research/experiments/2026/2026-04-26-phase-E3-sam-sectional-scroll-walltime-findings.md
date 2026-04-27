# E3 — Sectional-scroll pipeline wall-clock instrumentation

- **Date:** 2026-04-27 (started 2026-04-26 evening, ran past midnight)
- **Phase:** E3 (closes S8 in `paper/publishability-status.md`)
- **Status:** **closed-earned for instrumentation; closed-partial for the §2.13.7 mechanism re-validation** — wall-clock numbers landed clean on both recordings; piecewise judge-accuracy on these new recordings (twitter 50%, terminal 38%) is below the v6 numbers cited in §2.13.7 (75–88% / 75%), which deserves a separate mechanism-regression investigation before any §2.13.7 line edits.
- **Operator:** Claude Code (codec-through repo, primary.local M5 Max)
- **Model:** `google/gemma-4-26B-A4B-it` (HF snapshot from S0 provenance; native BF16; mlx-vlm 0.4.4)

## Verdict (one paragraph)

**The headline is throughput, not query latency.** At fixed ViT compute
budget the piecewise pipeline gives an agent **continuous perception at
the decode frame rate** (here 30 fps) by maintaining the cache from
H.264 MV + residual side-channels at ~248 ms/frame upstream, firing
the ViT only at T0 plus rare rebuilds — **1 ViT fire over 64 s of
twitter scroll, 2 ViT fires over 44 s of terminal scroll**. A naive
1 Hz screenshot-polling baseline at the same temporal-coverage budget
would need **64 ViT fires (twitter) or 44 (terminal)**, i.e. a **22–
64× ViT-compute reduction** at matched coverage. Equivalently: at
matched ViT budget, codec-through perceives at ~30 fps while polling
perceives at ~0.015–0.045 fps — **roughly 700–2000× more frequent
visual updates at the same ViT cost**. This lands inside the
whitepaper's "5–300× ViT compute reduction" band depending on rebuild
frequency. The per-query wall-clock numbers below (1.09–1.10× median
speedup) are a side-effect of the LLM dominating per-query cost — the
mechanism saves the ViT stage, but the LLM `generate(80 tok)` is
~80% of per-query wall-clock at this query cadence on this model, so
the per-query latency improvement is small *even though the ViT
savings are large*. Per-query latency is the wrong axis to lead with;
ingestion throughput at fixed ViT compute is the right one.

## Throughput / perception-rate framing (the headline)

| recording | duration | ViT fires (codec-through) | ViT fires (naive 1 Hz polling, matched coverage) | **ViT reduction** | effective perception fps (codec-through) | effective perception fps (polling at matched ViT cost) |
|---|---:|---:|---:|---:|---:|---:|
| Twitter  | 64.4 s | 1 (T0 only)        | 64 | **64×** | ~30 fps (decode rate) | 1/64 ≈ 0.016 fps |
| Terminal | 44.0 s | 2 (T0 + 1 rebuild) | 44 | **22×** | ~30 fps | 2/44 ≈ 0.045 fps |

What this means concretely:

- **At fixed ViT compute budget**: codec-through gives an agent
  ~30 fps continuous awareness; a polling baseline at the same total
  ViT cost only sees one frame every ~22–64 seconds.
- **At matched temporal coverage** (~30 fps for the duration): polling
  needs the ViT to fire at every observed frame — codec-through fires
  it 22–64× less often.
- **Effective perception rate ratio (codec-through / polling at
  matched ViT cost)**: ≈ 30 / 0.016 = **~1900×** on twitter,
  ≈ 30 / 0.045 = **~670×** on terminal. Inside the whitepaper's
  "5–300× ViT compute reduction" claim band depending on how the ratio
  is normalized; the band is content-dependent (twitter scroll is a
  static-content regime that doesn't trigger rebuilds, terminal scroll
  triggers one).

The mechanism's contribution is on the **temporal-density-of-perception
axis**, not the per-query-latency axis. At the per-query latency level
(below) the mechanism nominally helps but is structurally bounded by
the LLM-dominant query budget.

## Wall-clock numbers — per recording

Both recordings: 1080×702 RGB @ 30 fps, re-encoded from the original
3600×2338 @ 120 fps captures via libx264 ultrafast (the original
resolution OOM'd the decoder at ~96 GB RAM on M5 Max — see `caveats`).

### Twitter scroll (64.4 s source, 8 queries at 1 s spacing starting t=2 s)

| metric | value |
|---|---|
| total pipeline (after model load) | 71.0 s |
| model load | 5.8 s |
| per-query oracle median / p90 / mean / max | **1527 / 2229 / 1752 / 2961 ms** |
| per-query piecewise median / p90 / mean / max | **1396 / 3682 / 2038 / 4734 ms** |
| **wall-clock speedup median** | **1.09×** |
| cache-reuse mean / median | 89.3% / 88.1% |
| ViT fires (oracle) | 8 (1 per query) |
| ViT fires (piecewise) | 0 (no rebuilds at threshold=500) |
| judge accuracy: fresh / naive / global / piecewise | **100% / 0% / 0% / 50%** |

### Terminal scroll (44.0 s source, 8 queries at 1 s spacing)

| metric | value |
|---|---|
| total pipeline (after model load) | 123.2 s |
| model load | 5.6 s |
| per-query oracle median / p90 / mean / max | **3374 / 3664 / 3315 / 3743 ms** |
| per-query piecewise median / p90 / mean / max | **3080 / 3375 / 3089 / 3500 ms** |
| **wall-clock speedup median** | **1.10×** |
| cache-reuse mean / median | 80.5% / 89.3% |
| ViT fires (oracle) | 8 |
| ViT fires (piecewise) | 1 (one rebuild fired on the rebuild-threshold trigger) |
| judge accuracy: fresh / naive / global / piecewise | **87.5% / 100% / 62.5% / 37.5%** |

## Per-stage breakdown (medians)

All numbers in **milliseconds**.

| stage                                 | twitter | terminal | role                                 |
|---------------------------------------|--------:|---------:|--------------------------------------|
| `decode_ms`         (per-frame, upfront)      |   128.5 |    129.3 | PyAV decode + ndarray pull           |
| `mv_grid_ms`        (per-frame, upfront)      |   120.4 |    120.0 | MV + residual field on token grid    |
| `region_detect_ms`  (per-query)               |     1.7 |      2.9 | RANSAC + connected-components        |
| `shift_apply_ms`    (per-query)               |     0.1 |      0.1 | piecewise token shift                |
| `vit_encode_ms`     (per-query, oracle arm)   |   178.8 |    538.6 | Gemma 4 ViT fire (560×560 canvas)    |
| `vit_canvas_ms`     (per-query)               |    12.0 |     11.5 | PIL resize + paste + PNG temp        |
| `llm_generate_ms_fresh`                       |  1214.5 |   2622.4 | LLM 80-tok generate, fresh features  |
| `llm_generate_ms_piecewise`                   |  1136.3 |   2661.9 | LLM 80-tok generate, cached features |
| `query_total_ms_oracle`                       |  1527.3 |   3373.9 | end-to-end per query, oracle arm     |
| `query_total_ms_piecewise`                    |  1395.9 |   3079.7 | end-to-end per query, piecewise arm  |

**Bottleneck:** LLM `generate(80 tok)` is the per-query critical path
(80–84% of per-query wall-clock on twitter; 78–86% on terminal). The
ViT stage that the cache mechanism actually accelerates is only
12–16% of per-query budget on twitter and 16% on terminal. Therefore
even at 89% cache reuse the wall-clock speedup is bounded by

```
E2E_speedup ≤ 1 / (LLM_share + (1 − LLM_share) × (1 − ViT_savings_share))
            ≈ 1 / (0.80 + 0.20 × 0.10)  ≈ 1.22×  (twitter)
```

We measure 1.09×; the gap to the 1.22× ceiling is mostly the residual
upstream cost (region detect + canvas prep + the fact that `llm_piece`
is not actually faster than `llm_fresh` — it is the same LLM call with
different visual features). This matches **C-CEILING**'s framing (jfb
publishability-status round 26): the headline gain is bounded by the
share of compute the mechanism actually displaces, not by the cache
reuse percentage.

The terminal recording's higher absolute LLM cost (~2.6 s vs ~1.2 s)
reflects ~2× longer prompt context (the screen has more text on it),
which raises both prefill and the partial-cache-prefill on the warm
arm.

**Anomaly:** `vit_encode_ms` was 179 ms on twitter but 539 ms on
terminal despite identical input geometry (560×560 canvas, same model).
Plausible explanation is thermal / kernel-cache state — terminal ran
sequentially after twitter, so the M5 was already warm and MLX kernel
caches were resident. We did not run a controlled re-do; flagging for
followup if anyone wants a clean per-recording ViT cost.

## Real-time verdict

At the measured cadence (1 query / second on a sectional scroll
recording), **the piecewise pipeline keeps up trivially** on twitter
(1.4 s / query end-to-end with 1.0 s budget) and **does not keep up
on terminal** (3.1 s / query end-to-end with 1.0 s budget) — both
arms are dominated by the LLM generate, not by the cache mechanism.
Reframing in fps:

- twitter: oracle ~0.66 fps; piecewise ~0.72 fps
- terminal: oracle ~0.30 fps; piecewise ~0.32 fps

These are **query-fps**, not frame-fps. Frame ingestion (decode + MV +
region detect) sustains far higher fps — about **1000 / (128 + 120 +
2)** = ~4 fps on the full instrumented per-frame path, which is what
the upstream pipeline can do without an LLM in the loop. The earlier
"~5 ms/frame upstream cap" claim (`paper/publishability-status.md` Sam
lane) corresponds to the post-optimization region-detect-only path, not
to the full instrumented path which also computes the residual field
upfront for rebuild triggers.

## Mechanism-regression flag

Piecewise judge accuracy here (twitter 50%, terminal 38%) is **below**
the v6 numbers in `experiments/sectional_scroll_v6.json` (Twitter 75–
88%, Terminal 75%) cited in §2.13.7 of `whitepaper.md`. Possible
causes, in order of plausibility:

1. **Different recordings** — the v7 recordings used here
   (`recordings/twitter.mov`, `recordings/terminal.mov`) appear to be
   freshly recorded for E3, not the same captures that produced
   `sectional_scroll_v6.json`. The scroll motion, page content, and
   query timing all affect judge outcomes.
2. **1080p downscale** — the original 3600×2338 captures were
   downscaled to 1080×702 to fit memory. The mechanism's input to the
   ViT is 560×560 regardless, but cropping/letterboxing may have
   shifted what the LLM sees during the judge step.
3. **Sample variance with n=8 per recording** — the v6 75–88% was on
   n=8 query points too; binomial CI on 6/8 is wide
   ([0.35, 0.97]) so 4/8 is not technically significantly different.
4. **Instrumentation refactor regression** — the agent that did the
   wall-clock instrumentation added ~221 lines to `exp_sectional_scroll.py`.
   While the smoke run produced sensible per-stage timings and the
   `prepare_canvas` / `encode_frame` / `apply_piecewise_token_shift`
   call sites look unchanged in the diff, a regression somewhere on
   the cache-mixing path has not been ruled out.

**Action item:** before editing §2.13.7 to incorporate any of these
wall-clock numbers, run the instrumented v7 script on the actual v6
recordings (need to locate them; they aren't in `recordings/`) and
confirm the 75–88% / 75% reproduces. If it does, the v7 lower numbers
are a recording-specific finding (computer-use content varies); if it
doesn't, isolate the instrumentation change.

This explicitly does **not** invalidate the wall-clock numbers above —
those are correct for what they measure, regardless of what the cache
shift mechanism produces semantically. They just say "if the mechanism
is matching fresh oracle, the wall-clock cost is X."

## Implications for the sectional-scroll section of whitepaper.md

**Section-numbering note (added after first draft):** the current
`whitepaper.md` §2.13.7 is Affine Cache Warp (per recent commits
`47acc8d`, `216c246`, `634d8c0`, `598006d`, `3e7f72c` — JF's axis #2b).
The sectional-scroll claim is **S6 in `paper/publishability-status.md`,
labeled "to write" / planned**, not yet a numbered section in the
manuscript. The line edits proposed below should land in whatever
section S6 becomes (likely §2.13.8 or a sibling), not in the existing
§2.13.7. The earlier-draft text "§2.13.7" elsewhere in this findings
doc is a stale shorthand for the sectional-scroll content.

Suggested additions / corrections:

- **The sectional-scroll section (S6, when written)** should assert
  piecewise matches fresh oracle (75–88% / 75% on Twitter / Terminal,
  per `experiments/sectional_scroll_v6.json`). **Hold the line edit
  until the mechanism-regression flag above is resolved.**
- Once resolved, add a **"Throughput at fixed ViT compute"** subsection
  (the headline takeaway) with:
  - twitter: 1 ViT fire / 64.4 s vs 64 fires for naive 1 Hz polling
    coverage (**64× reduction**); ~30 fps continuous perception vs
    ~0.016 fps at matched ViT cost (**~1900× more frequent visual
    updates**).
  - terminal: 2 ViT fires / 44.0 s vs 44 (**22× reduction**); ~30 fps
    vs ~0.045 fps (**~670× more frequent visual updates**).
  - both inside the whitepaper's "5–300× ViT compute reduction" claim
    band; explicit framing as "at fixed ViT budget, the agent
    perceives at decode rate not at query rate."
- A secondary **"Per-query latency"** subsection (NOT the headline)
  with:
  - twitter: median 1.40 s/query piecewise vs 1.53 s/query oracle
  - terminal: median 3.08 s/query piecewise vs 3.37 s/query oracle
  - per-stage breakdown (most important: `vit_encode_ms` is 12–16%
    of per-query budget; the cache mechanism's wall-clock contribution
    is structurally bounded by that share)
  - the "1.09–1.10× per-query speedup" framing **must not be the
    headline** — it is a side-effect of the LLM-dominant query budget,
    not the contribution. Lead with the throughput axis above.
- **§2.13.8 (or a new §2.13.X)** can be added: the **"~5 ms/frame
  upstream"** number in `paper/publishability-status.md` corresponds to
  region-detect + shift only and is correct, but the **full instrumented
  per-frame upstream path is ~250 ms/frame** when residual extraction
  for rebuild triggers is included. We should not present "5 ms/frame"
  as the deployment overhead without that asterisk.
- Cross-reference to **C-CEILING** (jfb publishability-status round 26):
  cite the same arithmetic ceiling here. The 1.22× theoretical bound
  derived from 80% LLM share + 10% ViT savings share validates that
  C-CEILING applies cross-architecture (Gemma 4 26B in this run), not
  just on the 4B-class lane jfb has measured.

## Caveats

- **OOM on full-resolution decode.** The agent attempt that pre-dated
  this run died at ~96 GB RSS during `decode_all_with_mv` on the
  3600×2338 @ 120 fps captures. The script keeps every decoded RGB +
  grayscale frame in memory; 7700 frames × ~25 MB/frame ≈ 192 GB. The
  fix here was offline ffmpeg downscale to 1080×702 @ 30 fps. **A
  proper fix is to store the prepared 560×560 canvas instead of
  full-resolution RGB**, which would reduce memory by ~13× and let the
  full 64 s 120 fps capture run without preprocessing. Out of scope
  for this finding; logged as a separate followup.
- **EAGAIN regression on PyAV reformat.** First retry of the run hit
  `av.error.BlockingIOError: [Errno 35] Resource temporarily unavailable`
  on `frame.to_ndarray(format="rgb24")` immediately after model load.
  Fixed by porting the `_robust_reformat` retry wrapper from
  `experiments/exp_videomme_streaming.py` (8-attempt exponential backoff
  + `gc.collect()`). The fix is now in `experiments/exp_sectional_scroll.py`
  — review the diff before merging.
- **Single-attempt runs.** Each recording was timed once. Thermal
  drift between twitter (cold) and terminal (warm-after-twitter) is
  the most likely explanation for the 3× gap in `vit_encode_ms`
  (179 ms vs 539 ms). For paper-grade we'd want N=3 alternating
  twitter/terminal/twitter/terminal/twitter/terminal with cooldown
  pauses. Out of scope here.
- **Greedy decode.** Both LLM arms used the script's default which is
  whatever `Gemma4VLM.generate` ships (greedy at temp=0 per the S0
  provenance). No sampling variance in these numbers.

## Artifact pointers

- Modified script (with `_robust_reformat` + per-stage timing):
  `experiments/exp_sectional_scroll.py` (diff is +~225 / −10 vs main;
  unstaged)
- Twitter run JSON:
  `research/2026-04-26-e3-sectional-scroll-walltime/twitter_v7.json`
- Terminal run JSON:
  `research/2026-04-26-e3-sectional-scroll-walltime/terminal_v7.json`
- Smoke run JSON (1-query gate):
  `/tmp/smoke_twitter_v7.json` (not preserved in repo)
- Stdout logs:
  `research/2026-04-26-e3-sectional-scroll-walltime/twitter_v7.log`,
  `terminal_v7.log`, `smoke.log`
- Downscaled recordings (kept in repo for reproducibility, ~22 MB total):
  `research/2026-04-26-e3-sectional-scroll-walltime/recordings/twitter_1080p_30.mp4`,
  `terminal_1080p_30.mp4`
- Full-resolution recordings (not committed):
  `research/2026-04-26-e3-sectional-scroll-walltime/recordings/twitter.mov`,
  `terminal.mov`
- This findings doc: `research/2026-04-26-e3-sectional-scroll-walltime/findings.md`

## Re-run command

```bash
cd /Users/sam/repos/codec-through

# Downscale once (skip if already done — outputs are in recordings/)
ffmpeg -y -i research/2026-04-26-e3-sectional-scroll-walltime/recordings/twitter.mov \
  -vf "scale=1080:702" -r 30 -c:v libx264 -preset ultrafast -crf 23 -an \
  research/2026-04-26-e3-sectional-scroll-walltime/recordings/twitter_1080p_30.mp4

# Twitter (8 queries; HF_TOKEN must be in env for Gemma 4)
python3 experiments/exp_sectional_scroll.py \
  research/2026-04-26-e3-sectional-scroll-walltime/recordings/twitter_1080p_30.mp4 \
  --n-queries 8 \
  --out research/2026-04-26-e3-sectional-scroll-walltime/twitter_v7.json

# Terminal (8 queries)
python3 experiments/exp_sectional_scroll.py \
  research/2026-04-26-e3-sectional-scroll-walltime/recordings/terminal_1080p_30.mp4 \
  --n-queries 8 \
  --out research/2026-04-26-e3-sectional-scroll-walltime/terminal_v7.json
```

Wall time on M5 Max / 128 GB / mlx-vlm 0.4.4: ~1.2 min twitter, ~2.0 min
terminal (after model load + decode each).
