---
date: 2026-04-21
parent: paper/framing.md
status: paper-facing draft abstract — three-contributions structure (C-CEILING / C-PERSIST / C-VISION)
---

# Abstract (codec-through-2, draft)

Token-level and frame-level compression methods for video VLMs advertise
multiplicative speedups, but the gains that translate to end-to-end wall
clock are regime-dependent and often overstated. We make the
relationship between compression and wall-clock precise, then
instantiate it in three independent efficiency settings on commodity
hardware.

**Three contributions.**

*C-CEILING*: we derive and validate an arithmetic ceiling for
token-pruning speedup, `E2E ≤ 1 / (fixed_frac + (1 − fixed_frac) / s)`,
showing that an end-to-end win is bounded by the wall-clock fraction the
compressed stage actually owns. The ceiling is predictive within
≤ 5.2 % across 7 regime dimensions on Gemma 4-E4B-4bit (8/32-frame
counts × two benchmarks × three keep-rates × two anchor arms), and is
sharp enough to rule out several compositions a priori. This explains
why per-token wins on large models frequently fail to survive on small
models, and why decode-heavy regimes resist prefill acceleration.

*C-PERSIST*: under persistent-KV reuse on commodity 4-bit quantized
checkpoints, once the first-query prefill is paid, subsequent questions
on the same video return in sub-second time inside a
**safe-deployment envelope** that is architecture-specific: Qwen
2.5-VL-7B-4bit at ≤ 16 frames / 6.5 k prefill tokens with Δacc = 0
(clean), and 3B-4bit at ≤ 36 frames / 14.5 k prefill tokens at a
Δacc = −0.19 pre-basin plateau. Outside the envelope, a narrow soft
transition exits into a non-letter-attractor basin; basin-onset depth
scales ~1.6× with parameter count and sampler-side intervention is
architecture-conditional (sampler-invariant at 7 B; sampler-dispersible
at 3 B only back to the pre-basin plateau). Paired follow-up-query
latency, not first-query latency, is the right reporting unit for
conversational deployment.

*C-VISION*: training-free vision-tower pruning at the same operating
point (`L = 2`, keep-rate = 0.50 on Gemma 4-E4B-4bit) delivers
roughly **0.35–0.47 V-reduction depending on benchmark and protocol**,
with the dev tranche clustering in the **39–43 %** range across
VideoMME (8 f / 16 f), MVBench (8 f), and TOMATO (8 f). End-to-end speedups
follow the vision-axis analog of C-CEILING,
`E2E ≤ 1 / (1 − V_share × V_red)`, predictive within 2.7 pp of observed
across four vision-axis cells plus a fifth (H-stack with
novelty-pruning) at 1.064×. Dev-n=30 headline cells are
**TOMATO 1.24×, MVBench 1.21×, VideoMME 1.12× @ 16 f / 1.08× @ 8 f**,
with a held-out VideoMME 8 f paired measurement at 1.113× confirming
the dev signal.

**Scope and evidence mix.** Qwen routing (our original "Lane A") serves
as the mechanism-validation backbone: a bounded-staleness,
concentration-aware pixel-diff planner matches dense-8 on MVBench
motion holdout (0.600 @ 4.06 fresh frames) and ties dense-8 on TOMATO
motion holdout (0.333 @ 3.55 fresh frames), and six intuitive
refinements (naive mean-diff, sticky-dynamic on TOMATO,
positional-encoding correction, 1.51R novelty-pruning on VideoMME,
1.55D selective re-prefill) fail under matched conditions — establishing
what is and is not load-bearing on temporal redundancy. The
**deployment-scale evidence** comes from the sibling codec-through-sam
system, which exercises the full streaming stack on a 26 B-class
model — real-video 4.2–4.5× end-to-end speedups, ~50× dominant-pipeline
compute reduction, 13× ViT reduction, 5.4× prefill, and 5–300× live ViT
savings on camera feeds — anchoring the product-facing claims that
C-PERSIST and C-VISION predict at 4 B-class scale. The two repos share
an analytical frame (C-CEILING) and a shared definition of
attention-propagation drift as the fidelity mechanism, but run on
disjoint model-size and protocol regimes, which we treat as a feature
rather than a flaw.

**Negative results, preserved.** We report what did not work:
positional-encoding-only correction does not recover cached-feature
fidelity on its own; sticky-dynamic quantity without placement hurts
TOMATO; 1.51R novelty-pruning is a null on its own axis on Gemma
VideoMME; 1.55D partial image-block re-prefill is infrastructure-
falsified by mlx-vlm's image-block contract. These set hard limits on
what training-free temporal reuse is and is not.

**Limitations.** All C-VISION E2E cells above come from Gemma 4-E4B-4bit
with on-device Metal execution; a cross-architecture transfer of the
`L=2, kr=0.50` operating point (Qwen 2.5-VL at a matched point) is
outstanding. Measured end-to-end gain in a sparse-execution path
(claim 5) remains unmeasured at local scale; the sparse-path evidence
lives in codec-through-sam. Our frame-count operating point (≤ 32 f
locally) is lower than some adjacent work (64–256 f), and VideoMME
frame-scaling is non-monotonic on Qwen 2.5-VL at 4-bit: on dev, 16 f
medium buckets gain ≈ +30 pp and 32 f does not recover the aggregate.
The 16 f long-bucket regression of ≈ −20 pp seen on dev **does not
replicate on a disjoint n = 30 holdout** (holdout 16 f long 0.900 vs
dev 0.100); we treat the long-bucket shape as a dev-split
observation. The broader point — frame-count scaling is not a linear
quality knob on the models we study — survives.
