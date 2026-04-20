---
date: 2026-04-20
phase: 1.55A
status: findings
parent_prereg: 2026-04-20-phase-1_55A-7b-40f-symmetry-prereg.md
siblings:
  - 2026-04-20-phase-1_55A-3b-40f-deeper-plateau-findings.md
---

# Phase 1.55A — 7B 40f basin-symmetry probe (FINDINGS)

## Bottom line

**H1-symmetric EARNS; H1-novel FAILS.** The 7B basin is ~93%
closed under depth: 13/14 session follow-ups land in the
established `addCriterion` basin set; 1/14 is novel
(empty-response on clip 120-2). Δacc = −0.476 sits inside the
pre-registered symmetric-basin band [−0.55, −0.35]. The
shifted-onset-same-basin revision of Claim #14 (from
`2026-04-20-phase-1_55A-3b-40f-deeper-plateau-findings.md`)
is **symmetrically supported** on 7B at double its basin-onset
depth.

## Numerical results

| Metric                                         | Value       | Verdict     |
|------------------------------------------------|-------------|-------------|
| Session accuracy (n=21)                        | 7/21 = 0.333 | —          |
| Baseline accuracy (n=21)                       | 17/21 = 0.810 | —         |
| **Δacc (session − baseline)**                  | **−0.476**   | H1-sym ✓  |
| Session Q1 accuracy (n=7)                      | 6/7 = 0.857 | —          |
| Session follow-up accuracy (n=14)              | 1/14 = 0.071 | —         |
| Prefix coverage (follow-ups)                   | 0.9964      | H3 ✓      |
| Speedup (first over follow-up, median)         | 157.6×      | H2 part ✓ |
| Median follow-up elapsed                       | 1497 ms     | H2 part ✗ |
| Peak RSS                                       | 4.25 GB     | H3-RSS ✓  |
| Wall time (end-to-end, 42 queries)             | ~110 min    | on-budget |

## Attractor identity tally (n=14 session follow-ups)

| Attractor class                                     | Count | Established? |
|-----------------------------------------------------|-------|--------------|
| Plain `addCriterion` (→ parses as "A")              | 7     | yes          |
| `addCriterion(…)` Java-code method-chain            | 6     | yes          |
| `自动生成` Chinese auto-generate                    | 0     | yes          |
| Long-garbage repetition (>16 gen tokens)            | 0     | yes          |
| Empty-response (`generation_tokens=1`)              | 1     | **novel**    |
| Clean 2-token letter (any)                          | 0     | N/A          |
| Non-letter non-addCriterion non-Chinese             | 0     | novel cat.   |

**Established-basin share: 13/14 = 92.9%**, comfortably above
the H1-symmetric threshold of ≥10/14.

### Per-query breakdown

Follow-ups (Q2+Q3 per clip, 14 total):

- **037-2** Java-code: `addCriterion("index").setIndex(100);` (14 gen)
- **037-3** plain addCriterion → A (wrong; truth=D)
- **100-2** plain addCriterion → A (wrong; truth=B)
- **100-3** plain addCriterion → A (**correct by luck**; truth=A)
- **116-2** Java-code: `addCriterion("1.` (7 gen)
- **116-3** plain addCriterion → A (wrong; truth=B)
- **120-2** **empty response** (generation_tokens=1) — novel
- **120-3** plain addCriterion → A (wrong; truth=A — lucky? yes,
  parses to same letter as baseline wrong answer)
- **158-2** plain addCriterion → A (wrong; truth=D)
- **158-3** Java-code: `addCriterion("match_status").asInt() == 1` (14 gen)
- **160-2** Java-code: `addCriterion("The coach of the team…").` (25 gen)
- **160-3** Java-code: `addCriterion("1.0").` (9 gen)
- **210-2** plain addCriterion → A (wrong; truth=B)
- **210-3** Java-code: `addCriterion` (4 gen)

The sole correct follow-up (100-3) is a coincidence: the
`addCriterion` attractor parses to "A" and the ground truth for
100-3 is "A". Baseline also answered A on 100-3. This is NOT
evidence of preserved capability — the model is still in the
basin; the basin's exit token just happens to match the truth.

## Cross-architectural note: clip 120-2

**Clip 120-2 emits empty-response on BOTH 3B-40f AND 7B-40f.**

- 3B-40f, clip 120-2: `generation_tokens=1`, response=""
- 7B-40f, clip 120-2: `generation_tokens=1`, response=""

n=1 so this is not load-bearing as a claim. But it is the only
clip in either run that produces empty-response. That the SAME
clip triggers it on TWO independently-trained architectures at
matched basin-onset depth is consistent with a clip-specific
prefix-geometry effect rather than architecture-specific noise.
Flagged for follow-up; not a publishable finding on its own.

## Verdicts against preregistered hypotheses

### H1-symmetric (primary) — **EARNS**

- Δacc ∈ [−0.55, −0.35]: ✓ (−0.476)
- ≥10/14 in established basin set: ✓ (13/14)

Both conditions satisfied.

### H1-novel (primary, competing) — **FAILS**

- Δacc worse than −0.55: ✗ (−0.476)
- ≥4/14 in novel attractor: ✗ (1/14)

Neither condition satisfied.

### H2 (secondary, speedup) — **PARTIAL**

- Speedup ≥ 140×: ✓ (157.6×, extrapolating cleanly from 32f's 150×)
- Median follow-up ≤ 1200 ms: ✗ (1497 ms)

The median-miss mirrors the 18f observation: when generators
emit 7–25 long-garbage tokens (Java-code method-chain), per-token
latency inflates the median. The `addCriterion(…)` variants here
spent 4.5 s (160-2), 2.9 s (158-3), 2.0 s (037-2, 116-2) — these
are the tail that pulls the median above 1200 ms. Mechanism is
understood; speedup headline (157.6×) remains the load-bearing
number.

### H3 (tertiary, RSS) — **EARNS**

- Peak RSS ≤ 8 GB: ✓ (4.25 GB).

## Paper impact

**Claim #14 (3-D decomposition) is symmetrically supported at
both parameter counts.**

The 3B-40f run (matching `16.1k` prefill on a smaller model)
earned the latent-basin hypothesis with 4/14 novel tokens and
Δacc = −0.238. The 7B-40f run (matching `16.1k` prefill on the
larger model, at 2× the 7B basin-onset depth of 20f) earns the
symmetric-basin interpretation with 13/14 in established basin
and Δacc = −0.476.

Read together:

1. **Basin identity is cross-architectural.** Both models route
   to the `addCriterion` family under deep-prefill follow-up.
   The 7B basin is also observed at 3B (albeit less dominantly
   at 40f where 3B still has latent-basin headroom).
2. **Basin-onset depth is architecture-dependent.** 7B hits its
   closed basin at 8k tokens (20f); 3B needs 16k tokens (40f).
   Ratio ≈ 2×, consistent with parameter-count scaling.
3. **Within-basin structure is depth-stable at 7B.** At 40f
   (20→40 is the 7B basin's 2× depth probe), the attractor class
   distribution does not fragment — it stays in the 4-member
   established set plus one clip-specific empty-response.
   H1-novel's prediction of within-basin depth fragmentation
   fails.

The 3-D decomposition now reads:

> **threshold × basin-onset-depth × basin-geometry**, where
> basin-geometry is cross-architectural and basin-onset-depth
> scales ~2× with parameter count. Within-basin structure is
> depth-invariant once the basin is entered.

This is structurally cleaner than the "architecture-specific
ceilings" phrasing in the prior draft — the basin is one object,
and the architecture decides only when you fall into it, not what
the floor looks like.

## What this probe does NOT test

- 3B 36f interpolation (does 3B have a basin-open→closed
  transition between 32f and 40f?). Preregistered as task #141.
- 3B 40f temperature probe (does sampler-invariance extend to
  3B's novel-basin regime?). Preregistered as reopen condition
  (h).
- 7B 48f or 64f (is the 7B basin closed arbitrarily deep?).
  Not currently preregistered; low priority given the 40f
  result.
- Gemma cross-family (blocked on 1.55C infra).
- Selective re-prefill at 40f (blocked on 1.55D infra).

## Next action recommendation

The symmetric-basin interpretation is now the leading
explanation and is supported at both parameter counts. Next
highest-value probe is **3B 36f interpolation** (task #141):
if 3B's novel attractors appear at 36f (not just 40f), the
basin-onset boundary is sharp; if 36f looks clean like 32f,
there's a transition depth to characterize. Estimated runtime
~45 min on same 7-clip bucket with 3B-4bit.

## Artifact paths

- Prereg: `2026-04-20-phase-1_55A-7b-40f-symmetry-prereg.md`
- Run dir: `research/experiments/2026/artifacts/phase1_55A_7b_40f_symmetry/`
- `run.log`, `session_qwen7b_n7.jsonl`, `baseline_qwen7b_n7.jsonl`, `summary.json`
