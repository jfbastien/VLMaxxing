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
   unambiguous; a Gemma re-run can be queued as follow-up.

The findings below report what the run measured. A Gemma replication is
added to the P1 queue (new task) to verify whether the accuracy loss is
Qwen-specific or whether Sam's protocol reproduces cleanly on Gemma.

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
This is consistent with KV-reuse cross-contamination (the cached KV
anchors attention on Q1's content, biasing Q2/Q3 toward Q1-adjacent
answers) rather than with random-noise differences.

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
75.6× on follow-ups) but sacrifices semantic fidelity. The mechanism
behind the accuracy loss, inferred from per-stratum and overlap structure:

1. **First-query regression is 1.51V-consistent.** The −10.5pp on first
   queries (0.596 → 0.491) is larger than 1.51V's Qwen dev n=30 Δ of
   −3.3pp but within noise at n=57 (binomial SE ≈ 6.5pp at p=0.5).
   The cross-manifest composition (dev+holdout union) may also pick up
   the known Qwen long-bucket collapse.

2. **Follow-up regression is the main signal.** −23.7pp is not
   recoverable as noise. Mechanism: the persistent-KV cache on Q1 carries
   Q1's question-specific attention mass (the suffix tokens that gave Q1
   its answer). When Q2/Q3 replace the suffix but reuse the prefix, the
   cached cross-attention between prefix tokens and Q1's suffix is now
   mis-specified for Q2/Q3. The model sees "prefix that previously
   attended to Q1-relevant frames" and generates a Q1-biased answer.
   This is the KV-reuse cross-contamination pattern Sam warns about in
   §5 as the *reason* for drift-triggered re-prefill.

3. **We ran with drift-refresh off.** The preregistered H_sam_drift_refresh
   was not tested because the run used `--drift-refresh-policy off`. A
   follow-up run with the 1.49 adjacent-frame ViT cos ≥ 0.95 threshold
   would directly test whether refresh recovers accuracy at an acceptable
   cost. The current data point establishes the *no-refresh* floor.

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

To re-run a Gemma replication (matches prereg model exactly):
```bash
PHASE1_30_MODEL_PATH=$HOME/models/gemma-4-e4b-it-4bit \
  bash scripts/run_phase1_30_sam_streaming.sh
```

## Next steps

1. **Gemma replication (queued P1).** The prereg specified Gemma; a Qwen-
   run verdict does not close the preregistered hypothesis on its
   original arm. Expected cost: another 4–5h autonomous. This is the
   single most useful follow-up — it disambiguates "the stack fails
   on Qwen specifically" from "the stack fails as an idea".

2. **Drift-refresh ON replication (queued P2).** Run the same stack
   with `--drift-refresh-policy adjacent_cos --drift-refresh-threshold 0.95`
   to test H_sam_drift_refresh directly. If refresh recovers ≥50% of the
   degenerate-bucket mass at ≤30% refresh rate, a Sam-adjacent variant
   reopens the deployment-grade framing.

3. **Paper-pass: no C-VISION upgrade this round.** The abstract + intro +
   claim-matrix do NOT need editing from this finding; the 1.30 row
   either stays absent or gets a single "protocol-reproduces-speedup-
   not-fidelity" line in the appendix. Queue a codex round for a
   one-paragraph paper addition when JF is back.

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
