# Seed Audit: Revised Pre-release source (2026-04-16)

## Provenance

Source: pre-release external source, imported during the private
research phase. The raw import was removed from the OSS tree and is preserved
in git history; durable claim summaries live in `docs/claim-register.md`.

The revised pre-release source adds three major claim families beyond the
original we've been targeting:

1. **VideoMME** as a primary benchmark (300 questions, 100 videos,
   32 frames, 100% byte-identical on Qwen, 90%/−3.3% on Gemma 4)
2. **Cross-architecture generalization** on Gemma 4 26B with the
   architectural hypothesis: windowed attention (Qwen) → exact
   reuse, global attention (Gemma 4 SigLIP) → approximate reuse
3. **Wall-clock throughput** on Apple M5 Max: 6.0× ViT, 4.2× E2E,
   130 fps on 32-frame conferencing
4. **Strict-parse audit** methodology: 413 Qwen items with raw
   response logging, 0 parse failures
5. **New competitors**: FlashVID (ICLR 2026 Oral, 6.3× prefill,
   99.1% accuracy), STC-Cacher (CVPR 2026, in-ViT caching),
   DyCoke, EVS, NVILA
6. **Thinking-amplification finding**: Gemma 4 thinking-on drops
   strict agreement from 82% → 58%, byte-identical from 82% → 12%

## What we import as provenance, NOT as trusted claims

All of the above are imported as seed material with the same
epistemics we apply to the original pre-release source: useful hypotheses
and comparison targets, NOT claims we inherit without local
reproduction.

Specific trust boundaries:

| Claim | Our status | Required to trust |
|---|---|---|
| Qwen2.5-VL 100% agreement on TOMATO (1,484 items) | Local partial (0.833 on 30 items) — not yet at the pre-release source's level | Full TOMATO run with our strict parser |
| Qwen 100% on VideoMME (300 items) | Not attempted | Local VideoMME lane (phase 1.41) |
| Qwen 100% on MVBench (160 items) | Local partial (0.870 on 54 items) | Full hosted + NTU run |
| Gemma 4 90% on VideoMME | Not attempted | Local Gemma 4 setup (may not fit M3 Air 16GB) |
| Windowed-attention → exact, global → approximate | Not tested | Local Qwen vs Gemma comparison |
| Thinking amplification | Not tested | Gemma 4 thinking-on/off comparison |
| Wall-clock 6.0× / 4.2× / 130 fps | Not attempted (M5 Max, not our M3 Air) | Local Track B harness |
| Strict-parse 0/413 failures on Qwen | Plausible — our parser also gets 0 failures locally | Already confirmed on our smaller slices |
| FlashVID 6.3× prefill, 99.1% | Not verified locally | External reference |
| STC-Cacher CVPR 2026 | Not verified locally | External reference |

## What changes in our plan

### New claims to register

- `WP-2.7`: VideoMME evaluation (Qwen + Gemma 4)
- `WP-2.8`: Strict-parse audit methodology (413+ items, 0 failures)
- `WP-2.9`: Cross-architecture generalization (windowed vs global
  attention topology) — **scoped**: not a strict binary. the pre-release source's
  pre-release source §2.9 line 237 says Qwen+InternVL3 → byte-identical,
  Gemma 4 SigLIP → approximate; but §2.7 line 171 notes InternVL3
  is all-global with 0% byte-identical and still works. Evidence
  supports a spectrum (windowed-mostly = byte-identical; global
  with certain pretraining = high-fidelity approximate), not a
  one-line law.
- `WP-2.10`: Thinking-amplification finding
- `WP-2.11`: InternVL3 third architecture (all-global attention,
  95% strict agreement, +3.3% accuracy delta, 57% avg reuse)
- `WP-2.12`: EgoSchema low-reuse robustness (29.9% avg reuse,
  100% byte-identical, 0.0% accuracy delta on Qwen2.5-VL-7B).
  Useful because it shows cache value is preserved EVEN when
  most frames are NOVEL — falsifies naive "caching only helps
  high-reuse content" counterclaim.
- `WP-2.13`: Hard spatial token pruning on variable-token models
  (Gemma 4): at 50% keep ratio, 3.9× prefill speedup with −1.7%
  accuracy. Orthogonal to our temporal axis. NOT applicable to
  fixed-token Qwen2.5-VL without post-processor surgery.
- `WP-4.1`: Wall-clock throughput (ViT speedup, E2E speedup, FPS)
- `WP-4.2`: Combined temporal+spatial pipeline measured E2E at
  32/64/128 frames — 4–5× speedup sustains with frame count.
  Relevant as an upper-bound target for our Track B work.
- `WP-5.1`: Composition projection with TurboQuant (~175×)

### New phases to preregister

- **Phase 1.41 VideoMME lane**: stand up local VideoMME on Qwen 7B
  MLX. This is the de facto standard for video VLM efficiency papers.
  Matches the pre-release source's setup at 32 frames. Priority: high, after N=30.
- **Phase 1.42 Attention-topology experiment**: test the hypothesis
  that windowed attention gives exact reuse while global attention
  gives approximate. If we can run Gemma 4 4B (edge variant) on
  M3 Air, that would be the second architecture. Priority: medium.
  Update per the pre-release source §2.7 + §2.9: test should allow THREE cells
  (windowed-mostly = byte-identical, global-1 high-fidelity
  approximate, global-2 lossless) not a binary.
- **Phase 1.43 EgoSchema low-reuse robustness** (preregister): if
  our planner still shows benefit at low reuse (≤30%), claim #4
  (budget-placement) is strengthened. Reuse the pre-release source's EgoSchema
  corpus scaffolding.
- **Phase 1.44 VideoMME scaling**: 32/64/128 frame sweep after
  1.41 lands. the pre-release source's WP-4.2 shows 4–5× speedup sustains; our
  Track B harness should test the same sustain property.

### New competitors to track

Add to `docs/related-work-table.md`:
- **FlashVID** (ICLR 2026 Oral): post-ViT tree-based token merge,
  6.3× prefill, 99.1% accuracy. Qwen2.5-VL tested. **Composable
  with us** (multiplicatively: we skip ViT, FlashVID merges
  remaining tokens).
- **STC-Cacher** (CVPR 2026): in-ViT activation caching via Key
  projection cosine similarity, 24.5% ViT reduction. Partially
  composable.
- **DyCoke** (CVPR 2025): LLM-side token merge + KV pruning.
- **EVS** (Oct 2025): post-ViT prune by pixel L1 diff. Closest to
  our signal (both use pixel diff!) but operates at per-token
  granularity within frames rather than per-frame binary.

### What this does NOT change

- Our planner-2.0 direction (child-veto, feature-change oracle,
  placement ablations) is still the correct next method step.
- Track B is still unbuilt and mandatory for SOTA comparison.
- The MVBench holdout sticky4 result (phase 1.26.B) is still our
  strongest local signal.
- Phase 1.21 N=30 is still the hardening gate.

## 2026-04-17 addendum: Codex cross-check of seed pre-release source

Codex re-read the pre-release source alongside this audit and flagged a
**second** internal inconsistency on InternVL3 attention topology:

- `pre-release external source:171`: "InternVL3 uses InternViT-300M
  (24 layers, all-global attention, learned absolute position embeddings)"
- `pre-release external source:243`: "On windowed-attention
  architectures (Qwen2.5-VL, InternVL3), embedding caching is
  mathematically lossless"

These two lines are mutually exclusive. The earlier §2.9/§2.7
tension (lines 171 vs 237) was already flagged; line 243 adds a third
data point that puts InternVL3 in BOTH camps within the same
document. Consequence for our docs:

- We must NOT cite the pre-release source's "windowed = lossless, global = approximate"
  as a validated binary. The pre-release source's own data shows InternVL3
  (whatever its attention topology) at **95% strict agreement, not
  byte-identical**, which is empirically between Qwen (100%
  byte-identical) and Gemma 4 (88% byte-identical). That is a
  spectrum, not a topology-determined binary.
- Our `WP-2.9` remains **scoped** (not a binary; attention-topology
  conditioned on a spectrum, pretraining matters). This is already
  reflected in `paper/framing.md § Reviewer-Facing Limitations`.

Codex also verified two **false positives** in an earlier review
summary: (a) the pre-release source does NOT claim "mean-diff is universally best" —
the pre-release source never ablates statistics, so there is no such claim
to import or refute; (b) the pre-release source's combined temporal+spatial pipeline
table (lines 264–274) IS measured end-to-end on Gemma 4 26B at
32/64/128 frames with 4–5× speedup sustained (not projected), so
our literature-map should cite it as a measured result (with the
"Gemma 4, not our hardware or architecture" caveat).

Over-binary language we must flag when importing:

1. `pre-release external source:243` "mathematically lossless —
   a strict guarantee, not a statistical one" — valid ONLY for
   Qwen2.5-VL's specific 28-of-32 windowed geometry, not as a
   topology-class property. Our phrasing: "byte-identical on Qwen
   2.5-VL with 28 of 32 windowed layers; high-fidelity but not
   byte-identical on all-global ViTs."
2. `pre-release external source:16` (abstract) "Three
   architectures confirm that attention pattern determines output
   stability" — "confirm" is too strong with one cleanly windowed
   model, one cleanly all-global model, and one self-contradicted
   architecture.
3. `pre-release external source:241` thinking-amplification
   "confirming these are random fluctuations" — a sign flip is
   *consistent with* noise but does not confirm it; we should
   report this as suggestive evidence, not a confirmed finding.

### What this changes in the plan

- Phase 1.42 preregistration is correct as written (three-cell
  topology test), no edits needed.
- Phase 1.41 VideoMME can cite the pre-release source's N=300 result as "comparable
  setup but different hardware/model-size, not a number we
  reproduce."
- Phase 1.43 (new) — **EgoSchema low-reuse robustness** — is now
  a first-class recommended phase, per codex. the pre-release source's EgoSchema
  N=100 result (100% byte-identical at 29.9% mean token reuse)
  is the strongest counterexample to "caching only helps
  high-reuse content" in the current literature; locally
  reproducing or falsifying it at N=30 on Qwen2.5-VL-7B 4-bit
  would close the low-reuse robustness gap our paper currently
  has.
- Phase 1.44 (new) — **VideoMME 64/128-frame scaling** — becomes a
  required follow-on if phase 1.41 lands. the pre-release source's result says reuse
  climbs monotonically with frame count on conferencing content
  (86.5→90.8→93.1% at 32→64→128). If the **accuracy** also climbs
  or at least stays flat at our geometry, we gain a frame-count
  scaling axis the paper currently doesn't have.
- **Phase 1.45 (new)** — **Combined temporal+spatial pipeline on
  our stack**. the pre-release source's measured 4–5× E2E speedup is on Gemma 4 26B
  (MoE ~4B active) at M5 Max; we don't know if the arithmetic
  composes on Qwen2.5-VL-7B 4bit at M3 Air. This is the closest
  direct the pre-release source-vs-us apples-to-apples gate.

## What the pre-release source does better that we should learn from

1. **Scope of benchmarking**: 1,837 items across 3 benchmarks vs
   our ~150 items across 2 benchmarks. We need VideoMME.
2. **Cross-architecture testing**: two architecturally distinct VLMs.
   We have only Qwen.
3. **Strict-parse audit at scale**: the pre-release source has 413 items with raw
   response logging and 0 parse failures. Our coverage:
   - **Exact**: 30 TOMATO benchmark-native items (0 parse failures,
     `docs/reproduction-status.md` row WP-2.5) + 54 MVBench hosted
     items (0 parse failures, row WP-2.6) = **84 saved benchmark
     items**, all with 0 parse failures.
   - **Approximate**: an additional set of motion dev/holdout items
     evaluated in phases 1.10–1.12 (15 TOMATO dev + 15 TOMATO
     holdout + 15 MVBench dev + 15 MVBench holdout = 60 motion-
     slice items, all 0 parse failures). Some of these overlap with
     the 84 saved items above (TOMATO dev v1 is a subset of
     tomato_dev_v1), so the deduplicated total is **between 84 and
     144 unique items** with 0 parse failures.
   - Scaling to 413+ (matching the pre-release source) is the remaining step.
4. **Honest weakness section**: per-frame binary can't prune within
   novel frames. We already know this from our planner work.

## What we do better than the pre-release source

1. **Dev/holdout discipline**: the pre-release source runs on everything once. We split
   dev vs holdout and preregister.
2. **Matched dense frame-budget baselines**: the pre-release source compares cached vs
   dense-same-frames. We compare at matched effective fresh frames.
3. **Content-conditioned planner search**: the pre-release source uses default
   thresholds (STATIC < 3, SHIFTED < 8). We ran 30-policy grid
   sweeps across 4 statistics × thresholds × reuse classes × max_age
   (phases 1.10–1.11) and SEPARATELY tested sticky-dynamic (phase
   1.26) — these are distinct experimental families, not one sweep.
4. **Pareto analysis**: we compute real Pareto frontiers; the pre-release source reports
   binary agreement.
5. **Falsified-hypotheses ledger**: we track what doesn't work.
6. **Post-CodecSight positioning**: we've already absorbed
   CodecSight, CoPE, FrameFusion, STTM, T3S. the pre-release source's comparison table
   is broader but our methodology context is deeper.
