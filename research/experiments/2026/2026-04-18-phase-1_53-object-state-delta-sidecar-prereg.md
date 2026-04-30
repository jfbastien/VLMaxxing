# Phase 1.53: Object / State Delta Sidecar

**Status:** DEFERRED preregistration — not on the paper critical path.
Added 2026-04-18 per the Codex 2026-04-18 review as a new
representation-side branch that should be tracked but not folded into
the current earned-claim path. Explicitly distinct from phase 1.29
(codec-native routing signal) — this branch proposes a compact
structured memory for the prompt, not a routing statistic.

## Preregistration

### Objective

Prototype a machine-oriented sidecar that carries object / state
deltas instead of dense repeated visual evidence, and measure whether
it helps on the object-and-motion subset of MVBench without hurting
on unrelated task types. The cheap hypothesis: one dense I-frame
establishes entities and layout once; subsequent frames contribute
only query-relevant changes (movement, interaction, state transition)
via a short structured prompt addition.

This is a **new representation**, not a routing variant or anchor
tweak. It is a separate idea from the current temporal-reuse
mechanism, and the prereg is filed as a *deferred* branch so the
project can track it without pretending it is in scope for the current
paper.

### Example sidecar payload (illustrative, not committed format)

```
{
  "anchors": {
    "person_1": {"role": "actor",  "entered_at": 0.0},
    "cup_2":    {"role": "object", "entered_at": 0.0},
    "door_1":   {"role": "object", "entered_at": 0.0}
  },
  "deltas": [
    {"t": 1.2, "subj": "person_1", "event": "moved_left_to_center"},
    {"t": 2.8, "subj": "cup_2",    "event": "picked_up", "by": "person_1"},
    {"t": 4.1, "subj": "door_1",   "event": "unchanged"}
  ]
}
```

The sidecar is fed to the LLM **only** when the question type is
object / state / action centric — gating on question classification,
not on every item, to prevent prompt-growth from erasing the compute
gain.

### Why the pre-release source matters here

the pre-release source's codec-native extractor (see phase 1.29 rewrite,
`2026-04-16-phase-1_29-mv-only-signal-path.md`) is the substrate that
makes a low-cost motion / state timeline plausible. Skip-MB and
B-frame correctness let the extractor propagate object identity across
frames cheaply without re-running a full detector on every frame.

The pre-release live pipeline prototype already modeled decoder-integrated
classification. A sidecar produced inside that decoder pass would
close the loop: the paper's "real codec-guided system" becomes a
system that also emits an LLM-consumable structured memory.

### Claim register targets

- **None in the current claim matrix.** This is explicitly a deferred
  branch. If it earns evidence locally, it will unlock a new row in
  the matrix framed as "representation-side extension of codec-guided
  VLM reasoning." Do not retcon existing claims to include it.

### Hypotheses

- **H1 (helps on object / motion subsets)**: on MVBench
  `object_interaction`, `moving_direction`, `moving_attribute` at
  N=30 each, sidecar-augmented cached inference matches or beats
  dense baseline accuracy within 1 item (2σ on 30).
- **H2 (hurts on OCR / fine-detail subsets)**: on MVBench subsets
  where the sidecar cannot encode the decision-relevant evidence
  (OCR-heavy, texture-sensitive, small-object-detail), sidecar-
  augmented cached inference is *not worse than* the no-sidecar
  cached inference by more than 1 item. This is the caveat axis —
  we need to rule out that the sidecar causes silent regressions on
  task types it cannot help.
- **H3 (prompt growth is bounded)**: sidecar addition keeps per-item
  prompt-token count within 15% of the no-sidecar path on the full
  30-item run, averaged. Target: total prompt ≤ 1.15× unmodified.
- **H4 (compute savings survive the sidecar)**: end-to-end wall-clock
  on sidecar + pruned (at the 1.51R winning operating point) is
  faster than pruned-without-sidecar by ≤ 10% overhead — the sidecar
  generation must not dominate.

### Acceptance band

- H1: sidecar cached_accuracy ≥ dense_accuracy − 1 item (Δ ≥ −0.033).
- H2: sidecar cached_accuracy ≥ no-sidecar cached_accuracy − 1 item.
- H3: mean prompt tokens ≤ 1.15× baseline.
- H4: end-to-end sidecar+pruned ≤ 1.10× pruned-without-sidecar.

### Rejection band

- H1: sidecar cached_accuracy < dense − 0.10 (3+ items worse) on the
  three targeted MVBench subsets.
- H2: sidecar cached_accuracy < no-sidecar cached_accuracy − 0.10
  on any non-targeted MVBench subset (silent regression).
- H3: mean prompt tokens > 1.30× baseline (prompt growth erases the
  compute budget the sidecar was supposed to preserve).
- H4: end-to-end sidecar+pruned > 1.25× pruned-without-sidecar
  (sidecar generation dominates).

### Inconclusive

- Question-type classification fails frequently enough that the
  sidecar is gated off on > 40% of target items. Drop the classifier;
  feed the sidecar unconditionally and re-measure.
- Codec-native entity propagation is too noisy on MVBench's video
  encoding profile. Fall back to one detector pass per I-frame only,
  measure how much that costs.

### Caveats to state explicitly in the paper (if / when this lands)

- Likely helpful: object-interaction, moving-direction / attribute,
  state-change, simple-action questions.
- Likely harmful or insufficient: OCR, fine texture, small-object
  detail, subtle appearance changes. These require the visual
  pathway, not a symbolic delta.
- Prompt growth can erase compute gains if the sidecar is not
  bounded and query-aware. H3 / H4 exist specifically to falsify
  the "free accuracy" framing a naive reading would suggest.

### Prerequisites

1. Phase 1.29 (the pre-release source codec-native extractor port) landed, because the
   cheap entity-propagation substrate relies on codec metadata.
2. MVBench subset-level scoring lane, so H1 / H2 can be evaluated per
   subset rather than only in aggregate.
3. A detector / descriptor for the I-frame anchor pass. Initial
   candidate: whatever Gemma's vision tower extracts on the I-frame,
   summarized to a compact entity list via a short LLM call (or a
   symbolic detector if one is on hand).

### Execution plan (when unblocked)

1. Pilot: hand-construct a sidecar payload for 2 MVBench
   object_interaction items. Verify the LLM uses it (ablate by
   removing the sidecar and comparing answers).
2. Automated sidecar generator via one I-frame detector call +
   codec-native delta propagation on 15 MVBench object_interaction
   dev items. Measure H1 / H3 / H4 at this scale.
3. Target-subset N=30 holdout on the three MVBench subsets
   (object_interaction, moving_direction, moving_attribute) + a
   non-target N=30 control (OCR-heavy or small-object) to falsify
   H2.

### Runtime estimates (benchmark compute only)

| stage                      | scope                | ~wall-clock | notes                                           |
|----------------------------|----------------------|-------------|-------------------------------------------------|
| pilot (hand sidecar)       | 2 items              | < 5 min     | smoke only                                      |
| dev tranche                | 15 items × 1 subset  | ~15 min     | target subset only, 1 config                    |
| target holdout N=30        | 30 items × 3 subsets | ~90 min     | three separate MVBench subsets                  |
| non-target control N=30    | 30 items × 1 subset  | ~30 min     | H2 falsifier                                    |

Total runtime: ~2.3 h benchmark wall-clock (target + control),
assuming generator is already on disk. Pilot + dev are ~20 min.

### Links

- VidCtx (openreview id=KNpbR9z8OU, arxiv 2412.17415) — training-free
  VideoQA with question-aware textual context from other frames.
- SG-VLM (arxiv 2509.11862) — scene-graph grounding for frozen-VLM
  VideoQA.
- pre-release source §3 (codec-native extractor substrate)
- Phase 1.29 rewrite
  (`research/experiments/2026/2026-04-16-phase-1_29-mv-only-signal-path.md`)
  — the codec substrate this branch rides on.
- `paper/framing.md` — new future-work bullet `machine-oriented
  object / state delta sidecars`.
- [docs/claim-register.md](../../../docs/claim-register.md) and
  [research/decision-log.md](../../decision-log.md) — public release-facing
  ledgers for imported-target status and deferred branches.

### Result

Pending (deferred — not on the current paper critical path).

### Interpretation

Pending.
