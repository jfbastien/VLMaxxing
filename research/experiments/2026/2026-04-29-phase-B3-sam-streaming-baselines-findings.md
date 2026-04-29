# 2026-04-29 Phase B3 — Sam matched streaming baselines

- **Status:** **closed-earned** for the protocol; **closed-partial** for
  the codec-through claim (the `sam_policy` row in this run uses a
  T0-anchored simplification, not the full cache-shift mechanism — see
  *Caveats* below).
- **Verdict:** at matched 4-frame evidence budget on 22 events across
  twitter + terminal scroll recordings, **`low_fps_dense` (4 uniform
  frames over a 4 s observation window) is the strongest baseline,
  matching the fresh-oracle answer 17/22 (77.3%).** All other arms —
  including the simplified `sam_policy` proxy used here — are
  competitive but lower. Reviewer-defense framing for the paper:
  cannot claim "we beat all simple baselines" at matched fixed-frame
  evidence budget; we **can** claim sam_policy is comparable to
  screenshot_polling and beats recency_last_k.
- **Validator gate:** PASS (0 schema errors, 0 parse failures,
  4 arms × 22 events = 88 rows, ≥20 pair_keys, ≥2 videos, ≥1 stale-cache
  case — actually 11 stale-cache cases, half the events).

## Per-arm accuracy table

LLM-as-judge YES/NO grading. `session_correct = True` ⇔ judge said
"the candidate description matches the reference".

| arm                | overall (n=22) | terminal (n=11) | twitter (n=11) | stale-cache subset (n=11) |
|--------------------|---------------:|----------------:|---------------:|--------------------------:|
| `low_fps_dense`     | **77.3%** | 72.7% | 81.8% | **72.7%** |
| `screenshot_polling`| 59.1%     | 45.5% | 72.7% | 63.6% |
| `sam_policy` (proxy)| 59.1%     | 72.7% | 45.5% | 54.5% |
| `recency_last_k`    | 54.5%     | 36.4% | 72.7% | 54.5% |

`stale-cache subset` is the 11 events where a prior detected event
landed inside the 4-second observation window — i.e., screen content
was actively changing leading up to the query, so a cache that hadn't
refreshed would be stale. `changed_answer_expected = True` on those
rows.

## Provenance

| field | value |
|---|---|
| `model_id` | `google/gemma-4-26B-A4B-it` |
| `model_sha` | `7d4c97e54145f8ffd1a4dd1b4986a5015a517842` |
| `quantization` | `bf16_native` |
| `runtime` | `mlx_vlm-0.4.4` |
| `mlx_version` | `0.31.1` |
| `metal_version` | `Metal 4` |
| `hardware` | Apple M5 Max, 128 GB unified memory |
| `os_version` | `Darwin 25.4.0` |
| `commit_sha` | `7ad325c...` (HEAD at run start) |
| `decoding` | greedy (`temperature=0.0`, `seed=0`) |
| `evidence_budget` | 4 frames per arm except `screenshot_polling` (1) |
| `observation_window_s` | 4.0 |

## Protocol

**Recordings:** twitter + terminal screen scrolls, 1080×702 @ 30 fps,
44–64 s duration each (re-encoded from the 3600×2338 originals; same
recordings as E3).

**Event detection:** pixel-diff z-score on the recording at 1 Hz
sampling cadence. Events are timestamps where the diff jumped >1.5 MAD
above the moving median. Padded with uniform anchors when the detector
under-fired so each video has 11 events.

**Question (constant across all arms):**

> "Describe what is currently on screen. Be specific about text, names,
> or identifiable content. Keep it under 2 sentences."

**Per-event protocol (22 events × 5 LLM calls = 110 inference calls
beyond the model load):**

1. Run **`fresh_oracle_dense`** (8 uniform frames over the 4 s
   observation window) → **gold-standard reference answer**.
2. Run each of the 4 arms with that arm's frame selection → 4 candidate
   answers.
3. For each arm, run an LLM-as-judge call against the oracle answer:
   `"Reference: ‘…’. Candidate: ‘…’. Does candidate match reference?
   Answer YES or NO."` → `session_correct`.
4. Emit one schema-compliant row per (event, arm). 4 × 22 = 88 rows.

**Frame-selection per arm:**

| arm | frames |
|---|---|
| `screenshot_polling` | 1 frame at `t_event` |
| `low_fps_dense` | 4 uniform frames over `[t_event-4s, t_event]` |
| `recency_last_k` | 4 frames at `t_event - 0..1.5 s`, 0.5 s spacing |
| `sam_policy` (proxy) | T0 anchor (start of clip) + 2 mid-window samples + `t_event` |

## Smoking-gun examples

A few telling cases where arms diverged on the same event:

`terminal_e07` (t=24.5 s, mid-scroll): oracle described a specific
command output with timestamps; `low_fps_dense` matched closely;
`recency_last_k` only saw the bottom of the visible region and missed
the context above; `sam_policy` (T0 anchor) saw the original prompt
the user typed several seconds earlier.

`twitter_e02` (t=4.5 s, early scroll): all four arms got similar
answers; judge agreed for screenshot_polling and low_fps_dense, less
for recency and sam_policy because their frame selections happened to
omit a tweet that the oracle had captured.

## What this means for the paper

1. **Reviewer-defense headline (write this in §S6 / streaming baselines
   section):**

   > Compared at a matched 4-frame fixed-evidence budget, low-FPS dense
   > sampling matches the dense oracle answer on 77.3% of events, while
   > screenshot polling and last-K recency are at 59.1% / 54.5%. The
   > simplified codec-through proxy used in this run sits between
   > screenshot polling and low-FPS dense at 59.1%. The matched-budget
   > comparison does not separate codec-through from low-FPS dense at
   > N=22; doing so requires evaluating codec-through at its native
   > variable-evidence budget (T0 + rebuild events) where the
   > comparable polling cost is much higher.

2. **What the matched-fixed-frame budget hides.** The codec-through
   value proposition is on the **throughput / ingestion-density** axis
   (per E3): codec-through fires the ViT at scene-change events, not
   at every frame; at a fixed ViT cost, polling-style baselines see
   one frame every 22–64 seconds while codec-through sees ~30 fps via
   cache maintenance. B3 here measures something different: matched
   *evidence* budget per query. The two regimes give different
   answers about which approach "wins."

3. **The `sam_policy` row in this run is an approximation.** The
   actual codec-through native streaming pipeline lives in
   `experiments/exp_sectional_scroll.py` (sdamico) and does cache-shift
   updates per frame, with ViT firing only on rebuild triggers. A fair
   codec-through evaluation against `low_fps_dense` would compare
   answers at codec-through's *native* evidence rate vs polling at
   matched ViT cost — that is the throughput-axis comparison E3 already
   delivered (22–64× ViT reduction). What this B3 row tells us is:
   if you flatten codec-through into "T0 + observation-window samples"
   without the per-frame cache update, it is no better than other
   simple low-density samplers. That is honest negative information,
   and it should appear as a sub-paragraph rather than be erased.

4. **Section assignment.** This finding belongs in
   `paper/arxiv/sections/08_real_applications.tex` as a **streaming
   baselines** sub-section, paired with the throughput-axis claim from
   E3. The two together say: codec-through's contribution is on
   ingestion-density, not on per-event accuracy at matched 4-frame
   budgets.

## Caveats

- **N=22 events × 4 arms = 88 rows.** Bootstrap CIs not computed here;
  the per-arm accuracy differences (low_fps_dense 77 % vs recency 55 %)
  are large enough to suggest signal, but a paper-grade claim should
  include a paired McNemar-style test or bootstrap CI on the per-event
  agreement matrix.
- **`sam_policy` simplification.** As noted, this run uses a 4-frame
  proxy (T0 + observation-window samples) instead of the full
  cache-shift mechanism. Re-running with the actual mechanism is a
  follow-up; it requires either porting `experiments/exp_sectional_scroll.py`
  into JF's repo or invoking it from this scripts/ dir. Out of scope
  for the B3 first pass.
- **LLM-as-judge cost.** Each event runs a judge call that is itself a
  Gemma 4 26B inference. Judge variance is real but greedy decoding
  with the same anchor frame should make it reproducible.
- **Event detector.** Pixel-diff z-score is a coarser stand-in for the
  H.264 MV-inflection detector that codec-through uses in production
  (§2.13.4). For the matched-baselines comparison this is fine —
  events drive *when* we ask the question, not which arm gets which
  frames — but the event timestamps are not the same set the production
  mechanism would pick.

## Validator output

```json
{
  "n_rows": 88,
  "phases": {"B3": 88},
  "arms": {
    "screenshot_polling": 22,
    "low_fps_dense": 22,
    "recency_last_k": 22,
    "sam_policy": 22
  },
  "policies": {
    "streaming_screenshot_polling": 22,
    "streaming_low_fps_dense": 22,
    "streaming_recency_last_k": 22,
    "streaming_sam_policy": 22
  },
  "choice_diffs": 33,
  "correctness_diffs": 33,
  "text_diffs": 88,
  "parse_failures": 0,
  "schema_or_gate_errors": 0,
  "first_errors": [],
  "pass": true
}
```

`text_diffs=88` is expected (no arm produces literally the same text
as the oracle; that is what the LLM-as-judge is for).
`input_hash_mismatches=88` and `frame_hash_mismatches=88` are also
expected (each arm shows the model different frames than the oracle;
the matched fields the validator cares about — `raw_prompt`, etc. —
are identical across the pair_key group).

## Artifacts

- Paired JSONL (88 rows, schema-validated):
  `research/experiments/2026/artifacts/sam_scaleout_m5_20260429/sam_b3_streaming_baselines.jsonl`
- Validator summary:
  `research/experiments/2026/artifacts/sam_scaleout_m5_20260429/sam_b3_streaming_baselines_summary.json`
- Run log:
  `research/experiments/2026/artifacts/sam_scaleout_m5_20260429/sam_b3_streaming_baselines.log`
- Runner: `scripts/run_sam_b3_streaming_baselines.py`

## Re-run command

```bash
cd /Users/sam/repos/codec-through-jfb
HF_TOKEN=... python3 scripts/run_sam_b3_streaming_baselines.py
python3 scripts/validate_sam_scaleout_artifact.py \
  --jsonl research/experiments/2026/artifacts/sam_scaleout_m5_20260429/sam_b3_streaming_baselines.jsonl \
  --phase B3 --min-rows 80 --min-pair-keys 20 --min-videos 2 \
  --require-arms screenshot_polling,low_fps_dense,recency_last_k,sam_policy \
  --require-zero-parse-failures --require-b3-matched-events \
  --summary-output ...
```

Wall time: ~20 min on M5 Max for 22 events.

## Cross-reference

- `research/experiments/2026/2026-04-29-sam-scaleout-handoff.md` § B3
- E3 throughput finding (sdamico/codec-through, commit `6594a7b`):
  `research/2026-04-26-e3-sectional-scroll-walltime/findings.md` —
  documents the throughput-axis story (22–64× ViT reduction at matched
  temporal coverage) that this B3 finding intentionally does NOT
  claim.
