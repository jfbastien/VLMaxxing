# 2026-04-29 Phase 1.65v2 Richer Predictor Findings

Prereg / intent: test whether existing 1.65 dense-logprob rows contain enough
signal for a richer stability predictor after the margin-only scout failed its
held-out gate.

Command:

```bash
scripts/run_phase1_65v2_richer_predictor.sh
```

Artifact:

- `research/experiments/2026/artifacts/phase1_65v2_richer_predictor/prediction_summary.json`

Result:

| variant | held-out AUC | 95% CI | signal gate | safe-filter precision / coverage |
|---|---:|---:|---|---:|
| margin-only | 0.713 | [0.553, 0.845] | fail | 1.000 / 0.087 |
| label-free | 0.642 | [0.478, 0.796] | fail | 0.818 / 0.239 |
| oracle | 0.652 | [0.474, 0.806] | fail | 0.941 / 0.370 |

Definitions:

- `margin-only` is the same-split dense-answer-margin comparator.
- `label-free` uses top-second gap, candidate entropy, prompt tokens, q-index,
  source policy, and duration.
- `oracle` additionally uses answer-aware dense features
  (`dense_answer_margin`, `answer_letter_logprob`, `baseline_correct`).

Important caveat: on the current 228-row artifact, `top_second_gap` is
empirically identical to `dense_answer_margin` because the upstream 1.65 probe
rejects rows where the dense logit argmax disagrees with the recorded dense
choice. The `label-free` variant is therefore label-free by field list, but not
a deployable guard on this artifact. A genuinely label-free rerun would need
`--allow-logit-choice-mismatch` or a feature set that removes `top_second_gap`.

Interpretation:

The richer predictor does not produce a defensible deployable guard. The oracle
safe filter finds a high-precision slice, but the held-out AUC CI is too wide
and the features are answer-aware; this supports only a limited mechanism note.
For the paper, phrase 1.65/1.65v2 as a useful negative: simple dense-side
confidence features are insufficient for a runtime recache policy, and richer
predictors remain future work.
