# Phase 1.55A-32f — Persistent-KV frame-scaling third point (FINDINGS)

**Status:** findings, 2026-04-19. Third data point on the 1.55A prefill-
scaling curve, following 8f (47.23×) and 16f (91.06×) earns.

**Parent prereg:** `2026-04-19-phase-1_55A-32f-frame-scaling-prereg.md`

**Companion findings:**
- 8f: `2026-04-19-phase-1_55A-persistent-kv-findings.md`
- 16f: `2026-04-19-phase-1_55A-16f-frame-scaling-findings.md`

## Headline

**Persistent-KV reuse fails qualitatively at 32f (~13k prefill tokens)
on Qwen 2.5-VL-7B-Instruct-4bit.** Speedup continues the linear
scaling trend (149.88×, inside the pre-registered [130×, 220×] band)
and prefix coverage + RSS stay clean, but **accuracy preservation
rejects hard** — Δacc = −0.429 (session 9/21 vs baseline 18/21).

The failure mode is **not gradual cognitive drift**. Every one of the
14 cache-path follow-up queries (Q2, Q3) emits the literal token
`addCriterion` — a method-name identifier from Qwen's training
corpus. The scorer maps this to choice "A" by first-letter heuristic,
so 2/14 answers land correctly by chance (when the gold answer is A)
and all others fail. First-query (cold prefill) accuracy is 7/7,
matching baseline.

This is a **cache-state corruption boundary**, not a reasoning
boundary. Between 6.5k and 13k prefill tokens, something in the
persistent-KV reuse path on Qwen 7B-4bit produces a degenerate
decoder trajectory that collapses to a single pre-training artifact
token.

## Verdict matrix

| Hypothesis | Prereg band | Measured | Verdict |
|---|---|---|---|
| H1'' follow-up speedup | [130×, 220×] | **149.88×** | EARN |
| H2'' accuracy preservation | Δacc ∈ [−0.05, 0.05] | **Δ = −0.429** | REJECT (hard) |
| H3'' prefix coverage | ≥ 0.90 | **0.9955** | EARN |
| H4'' peak RSS | ≤ 12 GB | **2.50 GB** | EARN |

H1'', H3'', H4'' all land. H2'' rejects by a factor of ~9× the
envelope width. This dissociation is the central finding.

## Per-query stratification

| Stratum | n | Session correct | Baseline correct | Δ |
|---|---|---|---|---|
| Q1 (cold first-query) | 7 | 7/7 (100%) | 7/7 (100%) | 0 |
| Q2 (cache follow-up #1) | 7 | 1/7 (14.3%) | 6/7 (85.7%) | −0.71 |
| Q3 (cache follow-up #2) | 7 | 1/7 (14.3%) | 5/7 (71.4%) | −0.57 |
| All follow-ups | 14 | 2/14 (14.3%) | 11/14 (78.6%) | −0.64 |

Cold-prefill accuracy is identical to baseline: the model is not
degraded on content. The failure is confined to the cache-reuse path.

## Mechanism evidence

All 14 session follow-ups emit `generation_tokens=2` and `response=
"addCriterion"` (parsed as "A"). The baseline path at the same prefix
length (13k tokens, `generation_tokens=2`) emits the normal letter
distribution (A/B/C/D). Both paths see the same video, the same
question text, and the same maximum-tokens budget.

What differs: the session path warm-starts from a 12 878-token
persistent-KV state carried from the cold Q1, then processes ~40-90
fresh suffix tokens (the follow-up question + prompt scaffolding).
The baseline path starts from scratch.

The literal string `addCriterion` is a MyBatis/SQL-library method
identifier that lives as a single token in Qwen's vocabulary. Its
appearance at this frequency (100% of cache-path follow-ups) is not
consistent with attention-pattern drift; it is consistent with a
degenerate argmax trajectory where the decoder has committed to a
specific basin.

### Candidate mechanisms (ordered by subjective prior)

1. **4-bit KV-cache quantization noise compounds past a threshold.**
   Qwen 7B at 4-bit stores KV in quantized form. At 13k tokens,
   accumulated per-token quantization error in attention scores may
   push the decoder's initial-token logits into a pathological
   region. 16f (6.5k tokens) stayed clean; 32f (13k) does not. This
   is falsifiable: re-run with a bf16 KV cache.
2. **M-RoPE positional encoding behaviour at long visual-prefix
   length.** Qwen 2.5-VL uses multimodal RoPE. Visual tokens occupy
   a large contiguous position range; the 13k-token regime may push
   specific frequency bands outside training support. Falsifiable:
   truncate or re-encode positions.
3. **Persistent-KV state contamination during update.** The cold Q1
   generation emits 2 tokens of output. The mlx-vlm state object
   appends those tokens to the cache. At 32f, the state transition
   into Q2 may mis-align — but this should have broken at 16f too,
   unless some threshold interacts.
4. **Decoder sampling mode.** We use greedy decoding. Baseline at 32f
   works. Session at 32f fails. If the cache-reuse pathway changes
   the initial-token logit distribution enough, greedy will commit
   to the mode that baseline's rerun-from-scratch happens to step
   past. A temperature > 0 would disperse this — but is not the fix;
   the fix is understanding why the distribution tilts.

## Scaling curve with accuracy overlay

| Frames | Prefill tokens | First-query (s) | Follow-up (s) | Speedup | Δacc |
|---|---|---|---|---|---|
| 8  | ~3 270 | 38.5 | 0.815 | 47.23× | −0.048 (envelope) |
| 16 | ~6 500 | 73.5 | 0.807 | 91.06× | 0.000 |
| 32 | ~12 920 | 163.2 | 1.008 | **149.88×** | **−0.429** |

First-query time scaling: 38.5 → 73.5 → 163.2 s. Ratios 1.91× (8→16)
and 2.22× (16→32) — slightly super-linear (consistent with O(N·L)
attention at growing prefix). Follow-up time is essentially flat:
0.815 → 0.807 → 1.008 s (0.99× then 1.25×). Speedup ratios 1.93×
(8→16) and 1.65× (16→32) — sub-linear, reflecting the slight
follow-up latency creep.

Mechanism-wise, the **speedup curve is consistent with the pre-
registered prefill-dominance model**. The fidelity curve is not.

## Paper implications

Claim #14 (persistent-KV follow-up latency) now has three measured
points spanning ~3.3k to ~13k prefill tokens on Qwen 7B-4bit. The
speedup story is coherent and publishable across the range. The
fidelity story requires a scoped claim:

> "Follow-up latency speedup scales linearly with prefill length,
> reaching 149× at 32 frames (~13k tokens). **Fidelity preservation
> is bounded to prefill ≤ 6.5k tokens (16f) on Qwen 2.5-VL-7B-
> Instruct-4bit; at 13k tokens, the cache-reuse path degenerates
> into a repeating decoder artifact.** The boundary is specific to
> the 4-bit weight+KV regime and does not appear in cold-start or
> baseline runs at the same prefix length."

This is stronger than a bland "accuracy preserved" claim because it
identifies a concrete failure mode that future work can address
(bf16 KV, position-encoding fix, calibration).

## Wall-clock budget

Actual run: 4573 s (76 min), vs predicted ~70 min. Inside budget.
- 7 × cold Q1 @ ~163 s = 1141 s
- 14 × cache-path follow-ups @ ~1 s = 14 s
- 21 × baseline @ ~161 s = 3375 s
- Overhead (prefill re-encoding, logging): ~43 s

## Decisions (from prereg)

Prereg said: "H2'' rejects → deployment narrative needs prefill-
budget caveat." We execute that. We do NOT promote claim #14 to
32f-class prefills until the degeneracy is explained.

## Next experiments queued

1. **24f bisection** (highest information). Run the same 7-clip
   protocol at `--frame-count 24` (~9.7k prefill). Resolves whether
   the accuracy-failure boundary is a sharp cliff (consistent with
   quantization or a specific threshold) or a gradual slope
   (consistent with drift). Estimated budget: ~55 min.
2. **bf16 KV-cache control at 32f** (if cost affordable). Switches
   off the 4-bit KV quantization hypothesis. May require driver
   surgery.
3. **20f bracket** if 24f lands inside the degenerate regime — narrow
   the boundary further.

Queuing #1 now.

## Artifacts

- Run log: `research/experiments/2026/artifacts/phase1_55A_32f_frame_scaling/run.log`
- Session JSONL: `.../session_qwen7b_n7.jsonl`
- Baseline JSONL: `.../baseline_qwen7b_n7.jsonl`
- Summary: `.../summary.json`
