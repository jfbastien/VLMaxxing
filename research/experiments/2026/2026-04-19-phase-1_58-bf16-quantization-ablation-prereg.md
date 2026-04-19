# Phase 1.58 — bf16 vs 4bit Qwen long-context ablation (PREREG, DEFERRED)

**Status:** preregistration 2026-04-19. **DEFERRED** — requires
bf16 Qwen 2.5-VL-7B checkpoint download (~15 GB) and a feasibility
check that bf16 long-context fits on 16 GB Mac (uncertain — likely
requires swap or rejecting long bucket).

**Provenance.** Third candidate mechanism from the 2026-04-19 16f
findings (non-monotonic bucket scaling). Not a reproduction of
any whitepaper claim; it tests a local hypothesis about 4bit-
induced long-context quality regression.

## Motivation

The 16f follow-up found long-bucket acc dropping from 0.30 (8f)
to 0.10 (16f) while medium lifted +30pp. Three candidate
mechanisms:

- **H-A**: temporal resolution trade-off (stride vs distractors).
- **H-B**: attention-context drift compounds with frame count.
- **H-C**: 4bit quantization × long-context interaction (this
  phase).

H-C says: at 16f the prompt-token count is ~6,500, which for a
`Qwen2.5-VL-7B-Instruct-4bit` model may cross a quality-regression
threshold that bf16 does not exhibit. This would mean the long-
bucket regression is a **quantization artifact**, not a
model-architectural limitation.

## Scope

- Model A: `Qwen2.5-VL-7B-Instruct-4bit` (already have; prior
  runs use this).
- Model B: `Qwen2.5-VL-7B-Instruct` (bf16 or fp16; **not
  downloaded yet — ~15 GB**).
- Benchmark: VideoMME dev n=30 (same manifest as 8f and 16f runs).
- Frame counts: 8 and 16 (paired; 32 only if memory allows).
- Cache: identity.

## Pre-registered hypotheses

- **H1 (long-bucket quantization gap at 16f).** bf16 long-acc(16f)
  − 4bit long-acc(16f) ≥ +0.20. Equivalently, bf16 does not
  regress from 8f → 16f on long items. **Falsification:** bf16
  regresses by the same −20pp (Δ ≤ 0.05) → quantization is NOT
  responsible for the long-bucket regression; H-A or H-B must
  account for it.

- **H2 (no short-bucket gap).** At short, bf16 and 4bit agree
  within ±0.10 at both 8f and 16f. **Falsification:** any gap
  > 0.15 means quantization hits short too — a more pervasive
  quality issue than specifically long-context.

- **H3 (memory feasibility).** bf16 16f n=30 peak RSS < 14 GB on
  16 GB Mac without swap. **Falsification:** RSS > 14.5 GB or
  system swapping → Phase 1.58 long-context path is infeasible
  on this hardware; defer to cloud/larger Mac.

- **H4 (prefill time roughly 4× 4bit).** bf16 16f prefill ≈ 4×
  4bit prefill (bit-width × matmul FLOPs). Not a hypothesis under
  test, just a sanity-check expectation. **Violation** → MLX fast
  path is different across precisions in a way that matters for
  reporting.

## Confounds to pre-screen

- **Template/tokenizer drift.** bf16 and 4bit checkpoints must
  produce bit-identical prompt tokenizations. Pre-run smoke:
  concat(prompt_text) through `AutoProcessor` should match across
  precisions.
- **Decoder temperature.** max_tokens=32, greedy. Match across
  runs.
- **Feature-cache conflation.** Disable feature-cache replay for
  this ablation (cache was hashed on the 4bit model weights; bf16
  needs its own or no cache).

## Decision rules

- H1 earned (Δ ≥ 0.20) → add "4bit quantization causes long-bucket
  regression at 16f+" to claim #8 strengthener; suggests Phase
  1.57 attention-entropy ablation is secondary, and **the long-
  bucket path goes through model precision, not mechanism
  redesign**.
- H1 falsified (Δ ≤ 0.05) → definitively rule out H-C; long-bucket
  regression is architectural/mechanistic. Phase 1.57 becomes
  primary.
- H1 middle (0.05 < Δ < 0.20) → mixed; quantization contributes
  but is not sole cause. Report as-is.

## Runtime estimate

- bf16 8f n=30: ~50-60 min (4× 4bit 15 min run).
- bf16 16f n=30: ~2.5-3 h.
- Total: **~3.5-4 h wall-clock** if feasible. Plus one-time
  ~15 GB checkpoint download (~10-20 min depending on connection).

Not including implementation time (model-path plumbing for mlx-vlm
bf16 checkpoint, cache-disable toggle, output-dir scoping). All
straightforward; deferred to user approval on the checkpoint
download.

## Gating

- [ ] User approves bf16 checkpoint download (~15 GB disk, one-time).
- [ ] Cache isolation verified (no cross-precision feature-cache
      contamination).
- [ ] 8f bf16 dense n=30 smoke (confirms feasibility before 16f).
- [ ] 16f bf16 dense n=30 (primary experiment).
- [ ] Findings doc + claim-matrix update.

## Cross-references

- `2026-04-19-phase-1_41-qwen-videomme-16f-findings.md` (H-C)
- Phase 1.57 (mechanism ablation — alternative to this phase)
- Claim-matrix row 8 (VideoMME — this phase could strengthen or
  re-interpret it)

## Status

- [ ] Gating items above
- [ ] Run executed
- [ ] Findings committed
