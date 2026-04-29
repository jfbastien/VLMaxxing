---
date: 2026-04-21
parent: paper/priority.md
status: prereg — queued after EXP10 n=60, EXP17/18 replication, and any should-do #3-5 of the C-VISION cross-arch probe
phase: 1.60
---

# Phase 1.60 — Scroll / Pan Subset: where C-VISION breaks (and why)

## Why this exists

Codex rounds 24 and 25 flagged that token-merging / spatial-pruning
methods (ours and comparables) are structurally weakest on content
with **dominant camera motion** (scroll, pan, dolly, egomotion): the
static background that permits token reuse is replaced by a moving
background where almost every vision-token shifts coordinates
between adjacent frames. C-VISION's current three-benchmark
transfer (TOMATO 1.24×, MVBench 1.21×, VideoMME 1.12×) leans on
mostly-static content. We do not yet have a local number that
quantifies *where C-VISION breaks* and *how gracefully*.

This is a deliberately adversarial probe of the C-VISION
operating point. The science goal is not "can we still win on
scroll/pan" — it is "characterize the regime boundary so reviewers
can calibrate the claim to their content distribution."

The pre-release pre-release source's SHIFTED-content framing is the natural comparison
pointer: SHIFTED is structurally narrow on VideoMME but dominates
on scroll-like content; the pre-release external prototype reported 5–300× live-camera
ViT savings exactly because the low end of that range is SHIFTED
regimes. We need the **local, benchmark-grade counterpart**.

## Hypotheses

### Primary

**H_vision_scroll_breaks**: at L=2, kr_V=0.50 on Gemma 4-E4B-4bit,
end-to-end speedup on a 20-item scroll/pan subset falls to
≤ 1.05× (vs the 1.08–1.24× on static-dominant content).

- Falsification: E2E ≥ 1.10× (→ surprising: scroll/pan does not break
  the operating point; revisit SHIFTED claim positioning).
- Earning: E2E ≤ 1.05× AND V_red ≤ 0.25 (→ expected: moving
  background reduces the redundancy the pruner can exploit).

**H_vision_scroll_v_red_drops**: V_red drops monotonically from the
static baseline (0.39–0.43) as scroll density increases, measured
as a fraction of inter-frame pixel-diff area above threshold.

- Falsification: V_red stays in [0.35, 0.45] regardless of scroll
  density (→ pruner is ignoring the motion signal).
- Earning: V_red at "heavy scroll" items ≤ 0.25 AND at "light
  scroll" items ≥ 0.30 (→ clean monotone relation; usable as a
  deployment gate).

### Secondary

**H_vision_scroll_acc_holds**: accuracy degradation is bounded to
Δacc ≥ −0.10 even on the breakage subset (the pruner should
*drop to no-op*, not fail).

- Falsification: Δacc < −0.10 on heavy-scroll items (→ fidelity
  regression beyond the localized object-binding failures observed
  on MVBench).
- Earning: Δacc ≥ −0.05 everywhere (→ graceful degradation claim;
  deployable).

**H_vision_scroll_ceiling_holds**: the
`1/(1 − V_share × V_red)` ceiling remains predictive within 2.7 pp
on the scroll/pan subset (i.e. the formula still works even when
the pruner's effective gain shrinks).

- Falsification: observed E2E departs from ceiling prediction by
  > 5 pp (→ either thermal contamination or a mechanism outside
  C-CEILING; investigate).
- Earning: within ± 2.7 pp (→ extends C-CEILING's empirical
  coverage to the regime boundary).

## Design

### Subset construction

Build **`research/benchmark_manifests/scroll_pan_subset_v1.toml`**
with 20 items drawn from:

1. **VideoMME** (any duration bucket): filter for items whose
   existing pixel-diff statistic (from Phase 1.57 feature-drift
   driver's STATIC / SHIFTED decomposition if available, else a
   fresh pass) shows > 60 % of inter-frame motion concentrated in
   a single spatial axis (vertical scroll or horizontal pan).
2. **Synthesised / augmented clips**: if (1) does not yield
   ≥ 20 items, synthesize by applying a constant-velocity crop
   over 5 still VideoMME medium-bucket items (2-second sustained
   pan) for 10 synthetic items, and combine with 10 natural items.
   Document the synthetic/natural split in the manifest frontmatter.
3. Avoid content overlap with EXP15/16 (V-patched baseline +
   H-stack holdout) and EXP17/18 (V-only holdout pair) to keep
   the subset independent of already-landed cells.

Stratify the 20 items by **scroll intensity**: 7 light / 7 medium /
6 heavy, where intensity is the fraction of the frame whose
pixel-diff mass lies in the dominant motion axis averaged over the
clip.

### Experimental arms

Two arms, thermally paired back-to-back per 1.51V protocol:

- **EXP60_a** (reference): Gemma 4-E4B-4bit, 8 frames, no vision
  pruning (`--anchor-arm none --keep-rate 1.0`), max-tokens 32.
- **EXP60_b** (C-VISION): same model, same frames, vision-tower
  pruning at `L=2, kr_V=0.50`, same max-tokens.

Each arm writes per-item V_red, decode time, generate time,
RSS, answer parsed, answer correct.

### Promotion rules

All four hypotheses adjudicated together; the phase
promotes to C-VISION paper-body as:

- **CLEAN FAILURE CLAIM** if H_vision_scroll_breaks AND
  H_vision_scroll_v_red_drops AND H_vision_scroll_acc_holds all
  earn: C-VISION breaks gracefully on scroll/pan. Deployable.
  Paper-body table row "scroll/pan 20-item subset: 1.0×–1.05×
  E2E, Δacc bounded".
- **BROKEN DEPLOYMENT CLAIM** if H_vision_scroll_breaks earns
  but H_vision_scroll_acc_holds fails: fidelity regression
  beyond expected; deployment guide must include a
  scroll-detection bail-out. Paper-body adverse note.
- **SHIFTED-DOES-NOT-BREAK** if H_vision_scroll_breaks fails
  (observed E2E ≥ 1.10×): this is a surprising non-result. Revisit
  the pre-release source/SHIFTED positioning; C-VISION may be more robust than the
  token-merging literature suggests.

Thermal gate same as 1.51V sessions 3-5: `|decode Δ| <
max(0.02 × decode_ms, 100 ms)` or EARNED-ADVISORY with a favourable-
direction note.

## Runtime estimate

Two arms × 20 items × 8 f × ~25–60 s / item (bucket mix; static-
background medium items on Gemma 4-E4B-4bit track ~25 s; VideoMME
long ~150 s but we restrict to medium-duration content for the
scroll/pan subset).

Point estimate: **~35 min per arm × 2 arms = ~70 min total**.
Upper bound (if long items creep in): ~90 min.

## Manifest + driver

- New manifest:
  `research/benchmark_manifests/scroll_pan_subset_v1.toml`
  (to be authored after EXP10 n=60 lands, to avoid
  compute contention with the existing queue).
- Driver: reuse `scripts/run_novelty_pruning_gemma.py` with
  `$VT_FLAGS` as in 1.51V sessions 3–5; no driver changes
  required. The phase is a manifest-only extension.

## Dependencies / ordering

This phase runs **after**:

1. EXP10 n=60 H_stack composition re-check lands (currently
   running).
2. Cross-arch C-VISION probe on Qwen (should-do #3 in
   `paper/priority.md`) — if scroll/pan also runs on Qwen,
   we get two architectures for free; if not, Gemma-only is
   acceptable for a first paper-body result.

It does NOT depend on:

- 1.29 codec-native benchmark (orthogonal pipeline).
- 1.30 the pre-release source streaming reproduction (different protocol; scroll/pan
  is still a sparse-sampled benchmark probe).
- 1.55B / 1.54 decode-composition (C-VISION is
  vision-axis-only; decode-axis is a separate claim).

## Paper integration

If CLEAN FAILURE CLAIM earns, add one paragraph to
`paper/arxiv/sections/08_real_applications.tex` and a table row in the
C-VISION section:

> On a 20-item scroll/pan subset (7 light / 7 medium / 6 heavy,
> manifest `scroll_pan_subset_v1.toml`), C-VISION's operating
> point at `L=2, kr_V=0.50` reduces end-to-end speedup to 1.0×–
> 1.05× (vs 1.08–1.24× on static-dominant content), with V_red
> falling monotonically with scroll intensity and accuracy
> bounded within Δacc ≥ −0.05. The pruner degrades gracefully on
> moving-background regimes; deployers with pan-heavy content
> should expect near-zero speedup from this operating point and
> use a scroll-detection bail-out for fidelity-critical paths.

If BROKEN DEPLOYMENT CLAIM earns, add a more severe warning and
the scroll-detection bail-out becomes a deploy-guide prerequisite.

## Knowledge-base updates on landing

- `paper/claim-matrix.md` row 15 gets a new sub-row documenting
  the scroll/pan boundary.
- `paper/framing.md` Reviewer-Facing Limitations gets an
  explicit line on "scroll/pan degrades C-VISION gracefully" or
  "scroll/pan exceeds the bounded fidelity envelope; use
  scroll-detection bail-out".
- `research/falsified-hypotheses.md` gets the outcome.
- Memory: new project memory documenting the scroll/pan boundary
  (only if non-obvious from claim-matrix).

## Anti-anti-claims

We will not claim, based on this phase alone:

- "C-VISION generalizes to all video types" (it generalizes to
  the three mostly-static benchmarks we tested).
- "Scroll/pan is a small content slice" (20 items is a probe,
  not a representativeness measurement).
- "Graceful degradation is architectural" (Gemma-only here; Qwen
  cross-arch is a separate phase).

## Future phases this unblocks

- **Phase 1.60b**: egomotion / FPV subset, mirroring the pre-release source's
  live-camera SHIFTED regime at benchmark grade.
- **Phase 1.60c**: scroll-detection bail-out policy (if the
  BROKEN DEPLOYMENT branch earns): a runtime classifier that
  toggles `kr_V` between 0.50 and 1.00 on per-clip scroll
  intensity; would compose with 1.56 VLM-signaled refresh.
- **Phase 1.60d**: cross-architecture scroll/pan on Qwen (paired
  to any Qwen C-VISION cell that lands).
