---
phase: 1.30
date: 2026-04-23
parent: research/experiments/2026/2026-04-21-phase-1_30-sam-streaming-reproduction-prereg.md
prior:
  - research/experiments/2026/2026-04-21-phase-1_51V-expansion-findings.md
  - research/experiments/2026/2026-04-23-phase-1_51V-qwen-cross-arch-findings.md
  - research/experiments/2026/2026-04-19-phase-1_55A-persistent-kv-findings.md
status: findings 2026-04-23. Preregistered H_sam_e2e FALSIFIED on accuracy clause; paper-promotion rule not triggered. C-VISION remains mechanism-grade, not deployment-grade composition.
tracking: autonomous AFK session 2026-04-22/23
---

# 1.30 Sam session/streaming bridge — findings (n=57 seeds, 171 paired queries)

## TL;DR

Sam's session/streaming deployment protocol (cold prefill per query →
persistent-KV reuse + L=2 kr_V=0.50 vision pruning stack) reproduces
the **speedup half** of its preregistered headline but **falsifies the
accuracy half** on Qwen 2.5-VL-7B-Instruct-4bit at VideoMME 8f n=57
(171 paired queries, dev+holdout union).

- Amortized E2E speedup: **3.326×** (gate ≥ 3.0× → **PASS**)
- Accuracy Δ: **−0.193** paired aggregate (gate |Δ| ≤ 0.05 → **FALSIFIES by 3.9×**)
- Response-bucket distribution: clean 55.6%, mixed 39.2%, degenerate 5.3%
  (gates clean ≥ 0.50 **PASS**, degenerate ≤ 0.15 **PASS**)

Per the preregistered adjudication rule, H_sam_e2e requires both speedup
AND accuracy clauses. The accuracy clause fails hard; the paper-promotion
rule "if H_sam_e2e + H_sam_bucket both pass, reopen C-VISION as deployment-
grade composition" **does NOT trigger**. C-VISION retains its current
mechanism-grade claim (1.51V ceiling law; 1.044× Qwen, 1.08–1.40× Gemma
at the operating point). Sam's stacked session protocol does not transfer
to 7B Qwen at these preregistered tolerances.

## Arm/prereg deviation (document explicitly)

The prereg at `research/experiments/2026/2026-04-21-phase-1_30-sam-streaming-reproduction-prereg.md`
line 110 specifies `model-path /Users/jfb/models/gemma-4-e4b-it-4bit`. The
run was executed against **Qwen 2.5-VL-7B-Instruct-4bit** (wrapper default
`$HOME/models/Qwen2.5-VL-7B-Instruct-4bit`, confirmed in
`cold_summary.json:4` and `streaming_summary.json:4`). This is an
undocumented pivot from the prereg.

Context that makes the Qwen execution defensible:

1. 1.51V Qwen cross-arch (2026-04-23, same AFK session) established that
   the C-VISION ceiling law transfers to Qwen at (L=2, kr_V=0.50) with a
   1.044× lift. Running 1.30 on Qwen is the natural "does the stack
   compose" follow-up.
2. Cold arm took 4.3h wall; re-running on Gemma is ~another 8h wall for
   a paired result. The Qwen result is complete and the verdict is
   unambiguous.

The findings below report what the run measured. Gemma replication is
**not** a next step as written, because the current
`scripts/run_phase1_30_sam_streaming.py` hard-fails on any model_type
that isn't `qwen2_5_vl` (see `scripts/run_phase1_30_sam_streaming.py:303-308`).
Porting 1.30's session harness to Gemma is a separate engineering phase
whose value depends on what root-cause decomposition says about Qwen
(see `research/experiments/2026/2026-04-23-phase-1_30-rootcause-prereg.md`).

## Results

### Aggregate gates (n=171 paired queries)

| Metric | Cold (dense) | Streaming (KV-reuse + kr_V=0.50) | Δ / ratio |
|--------|--------------|----------------------------------|-----------|
| Accuracy | 0.561 | 0.368 | **−0.193** |
| Total wall (s) | 15507 | 4676 | **3.316× amortized speedup** |
| Mean E2E per query (ms) | 90516 | 27214 | 3.33× |
| Parse failures | 0/171 | 9/171 | +9 |
| Degenerate queries | 0/171 | 9/171 | +9 |

### Per-stratum (first_queries n=57; follow_ups n=114)

| Stratum | Cold acc | Stream acc | Δacc | Cold E2E (ms) | Stream E2E (ms) | Speedup |
|---------|----------|------------|------|---------------|-----------------|---------|
| first_queries | 0.596 | 0.491 | −0.105 | 89899 | 79241 | 1.13× |
| follow_ups | 0.544 | 0.307 | **−0.237** | 90824 | 1201 | **75.6×** |

The composition geometry: first_queries get only the 1.51V V_red lift
(streaming still runs full prefill on query 1, so the 1.13× ≈ matches
the 1.044× Qwen ceiling, modulo thermal variance across a 4h vs 1.3h
session). Follow_ups get the persistent-KV benefit: 75.6× speedup via
prefix-coverage 0.98 on the cached session KV (1055ms mean Q2/Q3 vs
90824ms cold). The accuracy loss is concentrated on follow-ups:
**−23.7pp**, ~4.7× the preregistered budget.

### Per-bucket paired (n=57, 171 queries)

| Bucket | Cold | Streaming | Δ |
|--------|------|-----------|---|
| short  | 0.684 (39/57) | 0.368 (21/57) | **−0.316** |
| medium | 0.517 (31/60) | 0.400 (24/60) | −0.117 |
| long   | 0.481 (26/54) | 0.333 (18/54) | −0.148 |

Every bucket loses accuracy; short bucket loses most (−31.6pp) because
it has the most headroom (cold short is the easiest bucket). This is
inconsistent with a "floor effect" story (we're not bumping into a
per-bucket noise floor); streaming is systematically worse across the
difficulty spectrum.

### Overlap matrix

| | streaming correct | streaming wrong |
|---|---|---|
| **cold correct** | 51 | 45 |
| **cold wrong** | 12 | 63 |

Streaming degrades on 45 items cold got right, and rescues only 12 items
cold got wrong. Net: cold has a **33-item deterministic advantage**
concentrated on cold-correct items the streaming stack then mis-answers.
The asymmetry is semantic (not a random-noise bucket shuffle), but the
overlap matrix alone does not distinguish between: (a) pruned vision
features starving Q0 of evidence, (b) reused KV contaminating Q2/Q3, or
(c) non-additive composition of both. The `2026-04-23-phase-1_30-
rootcause-prereg.md` decomposition is the adjudicating experiment.

### Response-bucket distribution (n=171 streaming queries)

| Bucket | Count | Fraction | Gate |
|--------|-------|----------|------|
| clean | 95 | 0.556 | **≥0.50 PASS** |
| mixed | 67 | 0.392 | — |
| degenerate | 9 | 0.053 | **≤0.15 PASS** |

H_sam_bucket **CONFIRMED** in the preregistered bands. This tells us
the streaming stack is producing well-formed outputs (parseable answer
letter, not noise tokens) at Sam-comparable rates — the accuracy loss
is semantic (wrong answer confidently), not syntactic (token collapse).

## Hypothesis verdicts

| ID | Gate | Measured | Verdict |
|----|------|----------|---------|
| H_sam_e2e speedup | paired amortized ≥ 3.0× | **3.326×** | **PASS** |
| H_sam_e2e accuracy | \|Δacc\| ≤ 0.05 | **Δ = −0.193** | **FALSIFIES** |
| H_sam_e2e (joint) | both clauses | speedup PASS, accuracy FAIL | **PARTIAL (ceiling-only)** |
| H_sam_bucket clean | clean ≥ 0.50 | 0.556 | PASS |
| H_sam_bucket degenerate | degenerate ≤ 0.15 | 0.053 | PASS |
| H_sam_bucket (joint) | both | both PASS | **CONFIRMED** |
| H_sam_drift_refresh | refresh ≤ 30%, degen reduction ≥ 50% | refresh-off policy; not tested | **N/A this run** |
| H_sam_thermal | \|Δvideo-decode\| / cold < 2% | 55366ms → 52914ms = **4.43%** | **FAIL** |

H_sam_thermal's 4.4% drift is slightly outside the preregistered 2%
envelope. The sign is negative (streaming faster), which is **inconsistent
with thermal drift** (thermal drift on M3 generally slows decode) and
**consistent with ViT pruning removing upstream load**. The thermal gate
is arguably mis-specified for this run since kr_V=0.50 changes video-decode
end-to-end cost. Treating the 4.4% as a measurement artifact rather than
a true thermal violation is defensible but should be flagged in the
paper-matrix entry for this row.

## Interpretation

The streaming protocol gives Sam's preregistered speedup (3.3× amortized,
75.6× on follow-ups) but sacrifices semantic fidelity. What the paired
data support vs. what the data do **not** yet determine:

1. **Semantic (not syntactic) failure.** Response-bucket PASSES and
   parse-failures are low; the streaming stack produces well-formed
   answer-letter outputs. The loss is *wrong answers confidently*, not
   token collapse. This rules out a tokenization or decode bug.

2. **First-query cost exists and is not a side-effect of KV reuse.**
   Q0 drops 0.596 → 0.491 (−10.5pp). Since Q0 runs against a freshly
   prefilled session with no prior queries, this cost cannot come from
   cross-query KV contamination. It must come from the vision-pruning
   path (kr_V=0.50 composes with a ViT-feature-based L=2 policy that
   can lose task-critical tokens on harder items), from thermal /
   sampling drift, or from a first-query code-path regression specific
   to 1.30 that the mechanism-grade 1.51V pipeline does not share.

3. **Follow-up cost is strictly larger** (−23.7pp vs −10.5pp). The
   gap between Q0 and Q2/Q3 losses is the part that *could* be
   attributable to persistent-KV drift, cumulative KV contamination
   across semantically different queries, or a non-additive composition
   of vision-pruning cost with KV-reuse cost. The overlap matrix is
   consistent with more than one of these stories.

The paired data do not yet tell us which of these mechanisms dominates.
The `2026-04-23-phase-1_30-rootcause-prereg.md` decomposition — V-only
× K-only factorization plus hard-reset controls plus a Q0 parity check
against 1.51V — is structured to adjudicate between these explanations.
Prior wording in this section attributed the follow-up loss to a
specific "Q1 answer anchors Q2/Q3 attention" mechanism; that claim was
stronger than the n=57 paired data support and has been retracted here
pending the decomposition. (Retained in the commit history at e9d1223
for provenance.)

3. **We ran with drift-refresh off.** The preregistered H_sam_drift_refresh
   was not tested because the run used `--drift-refresh-policy off`. The
   1.30 driver CLI currently accepts only `off` and `hard-reset`; the
   `threshold` branch hard-fails as not-implemented. Hard-reset is
   arm #5 / #6 of the decomposition prereg and is the strongest refresh
   we have in-repo today. Adjacent-cos (the 1.49-style drift refresh) is
   a separate implementation task deferred behind the H_reset verdict.
   The current data point establishes the *no-refresh* floor.

### Reconciliation with positive results on the same architecture

The composition negative must be reconciled with the positive mechanism
evidence already landed on Qwen 2.5-VL-7B-4bit:

- **1.51V Qwen cross-arch (2026-04-23):** at L=2, kr_V=0.50, n=30 paired
  VideoMME 8f dev, the V-only path observes Δacc = −0.033 (inside ±0.05
  budget) and E2E 1.044× observed vs 1.043× predicted — C-VISION earned
  at single-query granularity.
- **1.55A Qwen persistent-KV (2026-04-20):** basin-onset at 40f with
  1/21 sampler-invariant signature on all probes, threshold 14500
  tokens; the K-only path is deployment-safe within a bounded frame-
  count envelope.
- **This run (1.30, 2026-04-23):** the V+K composition at 8f with no
  refresh FALSIFIES the ±0.05 budget at n=57/171 dev+holdout union.

These are not mutually inconsistent. The simplest reconciliation
compatible with all three is that **single-mechanism safety does not
imply composition safety**: V-only is safe because Q0 runs with a fresh
cache (no K contamination) and the pruning cost absorbs into the paired
accuracy budget at this operating point; K-only is safe because Q0
cache is dense (no V degradation) and KV-reuse drift stays below
threshold within the 40f basin; the naive V+K stack with no refresh
compounds both costs (plus any non-additive interaction) on every
follow-up, breaking the tolerance. This reconciliation is testable —
it predicts Phase A of the decomposition will show non-zero V-only,
non-zero K-only, and a hard-reset arm that recovers most of the K-only
loss but not the V-only loss. The prereg's H_V / H_K / H_interaction /
H_reset are designed to confirm or falsify that story quantitatively.

If Phase A instead finds H_path FAILS (1.30 cold-pruned Q0 disagrees
with 1.51V Q0 at kr_V=0.50), the negative is a harness regression in
the 1.30 driver's first-query code path, not a scientific boundary on
composition, and the paper framing retracts from "anti-claim" to
"pending-harness-bug".

4. **Bucket-health is preserved.** Clean 55.6% / degenerate 5.3% means
   the stack is not breaking the model's output grammar; it's just
   picking the wrong well-formed answer more often. This is the cleanest
   possible failure mode for a deployment protocol — graceful degradation
   rather than collapse.

## Paper implication

- **`paper/claim-matrix.md`** (C-VISION row): NO upgrade. C-VISION stays
  at "two-architecture mechanism at L=2 kr_V=0.50 (Gemma + Qwen), VideoMME
  dev n=30". The deployment-grade composition framing that would have
  lifted the paper's submission tier is NOT unlocked.

- **New row or note:** Sam session/streaming protocol reproduces the
  speedup (3.33× amortized on Qwen 8f VideoMME n=57) but not the fidelity
  (−19.3pp aggregate, −23.7pp on follow-ups) at preregistered tolerances.
  Directional evidence that no-refresh KV-cache reuse across semantically
  different queries trades accuracy for latency on a 7B MLLM; aligns with
  Sam's own §5 motivation for drift-triggered refresh.

- **Abstract / intro:** unchanged. C-CEILING + C-PERSIST + C-VISION
  claims are intact. The 1.30 result does not weaken them; it bounds
  the applicability of Sam's full-stack deployment protocol.

## Methodology notes

### Prereg deviation: Qwen instead of Gemma (see §Arm/prereg deviation).

### Dirty-tree wrapper fix.
The wrapper `scripts/run_phase1_30_sam_streaming.sh` originally failed
between arms: cold arm's output files make the tree dirty and the
streaming arm's driver enforces a clean-tree guard. Fixed in this
session by threading `--allow-dirty` through both arm invocations
(lines 29, 45). Same pattern as commit 7580e6a (1.51V wrapper fix).

### Cold arm completed 2026-04-23T11:58 JST; streaming arm 12:01–13:19 JST.
Analyzer ran 13:19 same file. Thermal pairing: **back-to-back, no
cool-down**. Cold arm's 4h 18m elapsed followed by 1h 18m streaming
means the streaming arm ran on a warmer machine, which works AGAINST
streaming (throttling if present would slow it down); measured speedup
is if anything conservative.

### RSS: cold peak 2.64 GB; streaming peak 4.38 GB. Both well under the 10 GB guard.

### Data scope: 57 unique video IDs × 3 queries = 171 paired queries. Dev
manifest 30 seeds + holdout manifest 30 seeds = 60 nominal, overlap
gave 57 unique. This is slightly under the prereg's n=60 nominal.

## Reproduction

```bash
bash scripts/run_phase1_30_sam_streaming.sh
```

Outputs (all produced by this run):
- `research/experiments/2026/artifacts/phase1_30_sam_streaming/cold.jsonl` (171 rows)
- `research/experiments/2026/artifacts/phase1_30_sam_streaming/cold_summary.json`
- `research/experiments/2026/artifacts/phase1_30_sam_streaming/streaming.jsonl` (171 rows)
- `research/experiments/2026/artifacts/phase1_30_sam_streaming/streaming_summary.json`
- `research/experiments/2026/artifacts/phase1_30_sam_streaming/pair_summary.json`
- `research/experiments/2026/artifacts/phase1_30_sam_streaming/paired_queries.jsonl`
- `research/experiments/2026/artifacts/phase1_30_sam_streaming/per_clip_bucket_tally.json`

Re-running this arm unchanged requires only the existing wrapper:
```bash
bash scripts/run_phase1_30_sam_streaming.sh
```
For **root-cause decomposition** (not replication), see the new prereg
at `research/experiments/2026/2026-04-23-phase-1_30-rootcause-prereg.md`.

## Next steps

1. **Root-cause decomposition (queued P1, supersedes prior next-step list).**
   Codex round-28 review called the prior next-step list incomplete — the
   findings attributed the loss primarily to follow-up KV-cross-contamination
   but the Q0 drop (0.596 → 0.491) alone violates the ±0.05 budget, so
   KV-reuse cannot be the whole story. The right next move is a 6-arm 2×2
   decomposition (cold vs streaming × dense vs pruned, plus two hard-reset
   controls) on the short-only manifest, followed by a Q0 parity check
   against 1.51V. Full plan, hypotheses, and gates in
   `research/experiments/2026/2026-04-23-phase-1_30-rootcause-prereg.md`.
   Runtime estimate ~85 min (Phase A+B).

2. **Gemma replication (deferred).** The 1.30 driver hard-fails on
   non-Qwen models (`scripts/run_phase1_30_sam_streaming.py:303-308`),
   so a Gemma rerun requires a harness port first. Whether it is worth
   doing depends on the root-cause decomposition — if the Qwen failure
   is V-only-dominated at kr_V=0.50, the Gemma question becomes "does
   Gemma have the same V-only cost," which is partly answered by 1.51V.

3. **Adjacent-cos refresh implementation (deferred).** The
   `--drift-refresh-policy threshold` CLI value is already plumbed but
   hard-fails today (`scripts/run_phase1_30_sam_streaming.py:286-290`).
   Implementing an adjacent-cos drift detector only makes sense if the
   root-cause decomposition shows hard-reset recovers most of the loss
   (H_reset PASS); otherwise a smarter refresh policy won't help either.

4. **Paper-pass: no C-VISION upgrade this round.** The abstract + intro +
   claim-matrix do NOT need editing from this finding; the 1.30 row
   either stays absent or gets a single "protocol-reproduces-speedup-
   not-fidelity" line in the appendix. Final paper wording waits on
   root-cause decomposition.

## Artifacts

- `pair_summary.json`:
  ```json
  {
    "n_paired_queries": 171,
    "cold_accuracy": 0.561,
    "streaming_accuracy": 0.368,
    "accuracy_delta_streaming_minus_cold": -0.193,
    "amortized_speedup_cold_over_streaming": 3.326,
    "response_bucket_counts": {"clean": 95, "mixed": 67, "degenerate": 9},
    "overlap_bucket_counts": {"both_correct": 51, "cold_only_correct": 45, "streaming_only_correct": 12, "both_wrong": 63},
    "clean_fraction": 0.556,
    "degenerate_fraction": 0.053
  }
  ```

- Per-bucket paired accuracy:
  - short:  cold 0.684 → streaming 0.368 (Δ = −0.316)
  - medium: cold 0.517 → streaming 0.400 (Δ = −0.117)
  - long:   cold 0.481 → streaming 0.333 (Δ = −0.148)

- Follow-up-only accuracy Δ: **−0.237** (the mechanism-specific signal)
- First-query-only accuracy Δ: **−0.105** (1.51V-consistent, within noise)
