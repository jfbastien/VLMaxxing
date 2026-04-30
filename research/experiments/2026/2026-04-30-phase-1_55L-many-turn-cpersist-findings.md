# Phase 1.55L — many-turn C-PERSIST stress findings

## Preregistered question

Does the after-ingest C-PERSIST repair policy remain stable past the
two-follow-up envelope used by the broad 0/93 result?

## Protocol

- Model/runtime: Qwen2.5-VL-7B-Instruct-4bit on the local MLX stack.
- Corpus: seven 20-frame short VideoMME videos.
- Schedule: repeated stateless question cycle at horizons 10, 20, and 50.
- Arms: fixed \(K=1\), adaptive post-\(Q2\), and scheduled refresh-10.
- Pairing: dense rows are deterministic replicas of 21 unique stateless dense
  runs for turn-matched drift pairing.

## Result

- Adaptive post-\(Q2\): 0/343 follow-up choice drift and 0/343 follow-up
  correctness drift at the 50-turn horizon; no pathological outputs.
- Scheduled refresh-10: 0/343 follow-up choice drift and 0/343 follow-up
  correctness drift at the 50-turn horizon; no pathological outputs.
- Fixed \(K=1\): 3/343 choice drift and 2/343 correctness drift at the 50-turn
  horizon; below the 3% gate but no longer drift-free.

## Interpretation

This closes the simplest horizon attack on the two-follow-up C-PERSIST claim:
there is no observed drift cliff through 50 repeated-question turns under the
tested stress. It does not close natural conversational drift, because the
questions repeat in a stateless schedule and the dense baseline rows are not
independent timing samples.

## Artifacts

- `research/experiments/2026/artifacts/phase1_55L_many_turn_cpersist/summary.json`
- `research/experiments/2026/artifacts/phase1_55L_many_turn_cpersist/paired_many_turn.jsonl`
- `research/experiments/2026/artifacts/phase1_55L_many_turn_cpersist/session_many_turn.jsonl`
