---
date: 2026-04-29
status: peer review of Codex's phase-2 implementation (commit a2d2709)
related:
  - research/experiments/2026/2026-04-29-phase-2-experiment-design.md
  - research/experiments/2026/2026-04-29-phase-1_63G-format-diagnostic-findings.md
  - research/experiments/2026/2026-04-29-phase-1_65v2-richer-predictor-findings.md
---

# Peer review — Phase 2 implementation (a2d2709)

Codex landed 26 files / 3,400+ lines: chain runner, 7 wrapper scripts, 3 analyzers, 2 summarizers, 2 findings docs, Sam handoff schema. Two cells (A1, A2) already produced committed artifacts.

This review combines my own reads with three parallel sub-agent audits (1.30AG cache-distance, 1.55L many-turn driver, chain runner + 1.65v2 leakage).

## Bottom line

- **A1, A2, A6 ready to run.** Science is sound; minor framing risks documented below.
- **A3, A4, A7 should run cleanly** (extensions of already-validated drivers; lower audit priority).
- **A5 (1.30AG) has P0 issues that will likely crash or produce non-physical numbers.** Needs ~30–50 LOC of fixes to the cache-distance computation before running. Recommend either a Codex follow-up commit or skip A5 from this chain run.
- **Chain runner is solid** for fail-closed default behavior; sandbox concern means we must launch with `dangerouslyDisableSandbox` (same as the deep-mechanism queue).
- **A1 + A2 findings as committed are correct and paper-grade.**

## Verified against the design intent

### A1 — 1.63G Gemma format diagnostic ✅

Already landed: 18/18 matched failures, 0 permissive recoveries across 8f/16f/32f. The committed `format_diagnostic_summary.json` shows representative failure texts that match my sub-agent prediction exactly: apologies ("I am sorry, but you have not provided the video..."), prose ("The images you provided are video stills from basketball games..."). Codex correctly chose a conservative permissive parser that avoids the false-positive trap of upper-casing prose and converting "a" → option `A`. **The Gemma headline reframe is now defensible.**

### A2 — 1.65v2 richer predictor ⚠️ needs framing caveat

Already landed:

| variant | held-out AUC | 95% CI | signal gate | safe-filter prec / cov |
|---|---:|---:|---|---:|
| margin-only | 0.713 | [0.553, 0.845] | fail | 1.000 / 0.087 |
| label-free | 0.642 | [0.478, 0.796] | fail | 0.818 / 0.239 |
| oracle | 0.652 | [0.474, 0.806] | fail | 0.941 / 0.370 |

**Surprising negative result**: richer features actually *reduced* AUC vs margin-only (0.713 → 0.642). At n=228 with item-grouped split, the additional features add noise faster than signal. This is honest — Codex didn't post-hoc fish for a positive result.

**P1 caveat audit found**: the "label-free" variant includes `top_second_gap` (max minus second-max of 4-way candidate logprobs). The 1.65 upstream probe filters out rows where `logit_choice_matches_baseline = False` by default, so on this 228-row artifact `top_second_gap == dense_answer_margin` exactly (verified 228/228). The "label-free" variant is **label-free in principle but answer-aware in practice on this artifact**, because the upstream filter rejects rows where dense argmax disagrees with gold.

**Recommended fix**: update the findings doc / paper text to read:

> "On the within-1.30 paired-rows artifact where the upstream probe excludes dense-argmax-disagree rows, the `top_second_gap` feature is empirically equivalent to `dense_answer_margin`. A genuinely label-free predictor would require either re-running 1.65 with `--allow-logit-choice-mismatch` or removing `top_second_gap` from the feature set."

Not a P0; the gate verdicts (all three signal gates fail) are right and the paper conclusion ("dense-side confidence features are insufficient for a runtime guard") stands.

### A3 — 1.62D low-FPS dense ✅ (lower-risk, not deeply audited)

Wraps existing `run_phase1_62D_lowfps_dense_videomme.sh` with a new aggregation summarizer. The `pass_complete_pairing` and `pass_format` required gates are right (a low-FPS run that doesn't fully pair is a script bug; one with parse failures means Qwen got disoriented). Estimated runtime 5h is consistent with 4f arm taking ~half of 8f's 84 min × 60 + decode overhead.

### A4 — 1.63I Qwen kr fine-bracket ✅

Direct variant of the validated 1.63H script, with `KEEP_RATES="0.78 0.80 0.82"` and reuse of the committed dense_16f reference. The summarizer's `complete = all(pass_complete_pairing && pass_format for cell in cells)` gate is right: a low-gain envelope confirmation (negative paper result) still passes "complete" so the chain proceeds.

### A5 — 1.30AG K/V cache-distance probe 🚨 P0 issues

**Audit verdict: needs fixes before running.** Three P0 issues:

**P0-1: Distance computed over zero-padded buffer, not valid token window.**
`mlx_lm.models.cache.KVCache` allocates `self.keys` with shape `(B, n_kv_heads, n_steps×256, head_dim)`, padded with zeros beyond `self.offset`. The probe does `getattr(entry, "keys")` which returns the buffer including zero padding. This biases cosine artificially toward 1.0 by an amount proportional to `offset / (n_steps×256)`, in a content-dependent way. **Fix**: use `entry.state` (returns the trimmed view) or slice `entry.keys[..., :entry.offset, :]` before flattening.

**P0-2: Pruned-arm offset ≠ dense-arm offset.**
V-pruning at kr=0.50 reduces image-token count, so the prune-arm cache is shorter than the dense arm. The hard equality check `if left.shape[2] != right.shape[2]: raise ValueError` will fire on most rows. **Fix**: align to `min(left.offset, right.offset)` or define an explicit semantic (e.g., compare only the trailing text-tail tokens).

**P0-3: H4 gate uses `mean_abs`, prereg says cosine.**
The prereg §Protocol says "layer-wise cosine distance"; the script computes the saturation gap on `mean_abs`. **Fix**: switch to cosine, or amend the prereg.

**P1 issues** (rigor): stratification target_per_class=5 may shortfall on stable rows; no per-layer reporting in summary; reuse-arm prefill state may diverge from 1.30AD recipe; pruned-arm leaves model in `keep_rate=0.50` state if exception escapes (no try/finally).

**Recommended action: skip A5 from this chain run, file a fix note for Codex.** The fix is ~30–50 LOC and well-specified, but adding it ourselves blocks the autonomous launch by another implementation cycle. A5's negative ("equal aggregate is empirical, not causal") is acceptable for the paper if it doesn't run.

### A6 — 1.55L many-turn C-PERSIST ✅ (with linguistic caveat)

**Audit verdict: science is valid as scoped.** Confirmed:

1. Question cycle is `[Q1, Q2, Q3, Q1, Q2, Q3, ...]` from VideoMME's 3 questions per video — no Q4+ fabrication.
2. **Both arms see identical prompt text per turn** (only current Qk, no chat history). The "stateless" framing in Codex's commit is technically right: the prompt is stateless per-turn, but the adaptive arm's *cache* state accumulates across turns. This is exactly what we want for a C-PERSIST horizon test.
3. Drift reference is turn-matched dense baseline (`baseline_by_key[(vid, horizon, turn_index)]`).
4. Refresh policies are encoded as policy strings (`refresh10`, `refresh5`); off-by-one means refresh fires at turns {1, 10, 20, 30, 40} for `refresh10` not {0, 10, 20, 30, 40} (turn 0 is cold by definition). Functional but undocumented.
5. Pathological detection (`addCriterion`/自动) is wired into both arms.

**P1 risks**:

- "Stateless" is a terminology hazard: the analyzer / findings doc must explicitly say "stateless repeated-query horizon, not conversational history" or a reviewer will compare against true multi-turn chat benchmarks. Codex's design doc gets this right at lines 152, 163, 253; we must propagate to the findings doc when 1.55L lands.
- 1.55L bypasses `selective_reprefill_policy.reprefill_k_for_query` entirely. Functional but breaks the forward-compat contract. Document.
- Hard-coded thresholds (3% drift, 10% bucket cliff). Acceptable but should be in findings.

**Recommended smoke test before chain launch** (10 min):
```bash
PHASE1_55L_VIDEO_IDS=037 PHASE1_55L_TURN_COUNTS=4 PHASE1_55L_POLICIES=fixed_k1,adaptive_post_q2,refresh10 \
  ./scripts/run_phase1_55L_many_turn_cpersist.sh
```
Expected: at horizon=4, `source_q_index` cycles 0,1,2,0; cache_source = `cold_q0, reprefill_k=1, post_previous_repaired, post_previous_repaired`. If this matches, the driver is correct.

### A7 — 1.55K-extended ✅ (lower-risk, not deeply audited)

Wraps `run_kv_selective_reprefill_v2.py` with a `--seed` plumbing and 3-seed × 5-temperature sweep. Codex notes: "tests seed robustness on the same short tranche, not broader clip coverage." That's an honest scoping; for the paper, the claim becomes "seed-stable on the short tranche" not "cross-bucket seed-stable." Acceptable.

### Chain runner ✅ (with sandbox + commit caveats)

**Audit verdict: solid fail-closed semantics, two operational issues:**

1. **Sandbox**: the chain will fail at A3+ (any MLX-using step) when invoked from a sandboxed agent harness. **Solution**: launch with `dangerouslyDisableSandbox: true`, same as the deep-mechanism queue did.
2. **Auto-commit scope**: only commits `step.artifact_paths` + `STATUS_PATH`. Findings docs landed outside `artifact_paths` will be left dangling. **Mitigation**: I'll commit findings docs manually after the chain completes.

P1: A6 + A7 have empty `required_gates`. They will mark "completed" even if no useful science came out. Acceptable for negative-result-acceptable phases, but a `pass_complete_pairing`-equivalent gate would be tighter.

P2: `--continue-on-failure` is opt-in, not default. Means a single MLX panic kills the chain. Default-fail-closed is right, but for an autonomous overnight run I want `--continue-on-failure` so A5's crash doesn't kill A6 + A7.

### Sam handoff schema ✅ (read-only audit)

Schema at `research/schemas/sam_scaleout_artifact_v1.schema.json` and handoff doc at `research/experiments/2026/2026-04-29-sam-scaleout-handoff.md`. I did not deeply audit but the per-row schema mirrors what we capture locally. **Recommend** Sam confirm the schema against his runtime's actual outputs before committing to the format.

## Recommended action plan

### Option 1 (cleanest): Codex fixes A5 first, then I launch full chain

Pros: full slate runs, A5 produces meaningful science.
Cons: blocks an additional implementation cycle.

### Option 2 (ship now): I launch chain with `--continue-on-failure`, skip A5 manually

Concretely:
1. Modify the chain to skip A5 (either via `--start-at A6` after A4 completes, or remove A5 from the steps list temporarily).
2. Or launch with `--continue-on-failure` and accept A5 will fail visibly; A6 + A7 still run.

Pros: ships A1–A4 + A6 + A7 today; A5 fix is a follow-up.
Cons: missing causal-mechanism evidence for the 1.30 boundary.

### Option 3 (hybrid): Run A1–A4 and A6 + A7 in chain; I write a 1.30AG fix in parallel

Pros: maximum throughput; A5 fix can be reviewed before re-launch.
Cons: I need to context-switch between monitoring + fixing.

**My recommendation: Option 2 with `--continue-on-failure`.** A5's negative result ("equal aggregate is empirical, not causal") is acceptable paper material. The other six experiments are paper-defining; we should not block them. Codex (or I) can fix A5 in a follow-up commit, and re-run that one cell.

## Can I run autonomously? Yes, with caveats

**Conditions for autonomous run:**

1. Launch with `dangerouslyDisableSandbox: true` (mandatory, same as deep-mechanism queue).
2. Launch with `--auto-commit --continue-on-failure`.
3. Pre-commit current state (chain runner expects clean tree; we're at +1 commit ahead since a2d2709, with this peer-review doc, but worktree should be clean once committed).
4. After chain completes, manually:
   - Commit findings docs that land outside `artifact_paths`.
   - Update the 1.65v2 findings doc with the leakage caveat.
   - Update the 1.55L findings doc to call out "stateless cache horizon, not conversational" framing.
5. The chain ETA is ~28h compute + ~5 min between phases for git commits. With `--continue-on-failure` and A5 likely failing fast (probably crashes within 5–10 min on its first row), the effective compute time is ~28h. I'll need a Monitor armed and 30-min `/loop` heartbeats.

**Things I'm NOT confident about:**

1. The 1.30AG fix: even if I attempt it, MLX-internal cache manipulation is subtle. I'd rather have Codex review my fix than land it blindly.
2. The 1.55L 50-turn cell time estimate: I expect ~7h based on 1.55K timing × turn count, but cache state at turn 50 might trigger different memory behavior. Worth a 10-turn smoke first.
3. The 1.62D 4f arm is fast; the 2f arm should be even faster, but I haven't verified the script doesn't have a frame-count assumption that breaks at 2f.

## What I would change in the implementation

1. **Add a `default_required_gate = "complete_pairing"` to A6 and A7.** Empty required_gates is too permissive.
2. **Add a `--commit-findings-docs` flag** to the chain runner that also git-adds `*-findings.md` matching the phase prefix.
3. **Land Codex's A5 fix as a separate prereg-bound iteration**, not as part of this chain.

## Open questions for the user (before launch)

1. Approve Option 2 (skip A5 / continue-on-failure)?
2. Smoke-test 1.55L at horizon=4 first (10 min), or trust Codex's pre-flight verification?
3. Want me to write a peer-review reply to Codex with the leakage caveat + A5 fix list?
4. Any objection to my launching with `--commit-failed-artifacts` so we capture A5's crash for diagnostics?
