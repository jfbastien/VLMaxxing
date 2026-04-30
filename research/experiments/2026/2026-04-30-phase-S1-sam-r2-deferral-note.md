---
date: 2026-04-30
phase: S1 (r2)
status: deferred (env setup blocker; no scientific yield gap)
related:
  - 2026-04-30-sam-r2-handoff.md (Step 4 -- S1 spec)
---

# 2026-04-30 Phase S1 — DEFERRED in r2

## What S1 was supposed to do

Per the r2 handoff, S1 = "Qwen 7B C-PERSIST at 32 f / 64 f (~1–2 h)"
to extend C-PERSIST evidence to frame budgets that the local 16 GB
Air can't collect. The runner is `scripts/run_phase1_55L_many_turn_cpersist.sh`,
driving `scripts/run_phase1_55L_many_turn_cpersist.py`, against
`mlx-community/Qwen2.5-VL-7B-Instruct-4bit`.

## Why deferred in r2

Three blockers, each independently sufficient:

1. **`codec_through` package not installed on this M5's Python.**
   The runner imports
   `from codec_through.qwen_selective_reprefill import (...)`. The
   homebrew Python 3.14 on this M5 has PEP 668 enforcement and
   refuses `pip install -e .` without `--break-system-packages` or a
   venv. Setting up a venv just for this run is a separate setup
   commit; we punted it for r2.

2. **Qwen 2.5-VL processor requires `torchvision`.** mlx-vlm's load
   of any Qwen-VL model imports the HF `Qwen2VLVideoProcessor`,
   which hard-fails without torchvision. Same install constraint
   as (1).

3. **Qwen 2.5-VL-7B-Instruct-4bit weights not on disk.** The runner
   defaults `MODEL_PATH=$HOME/models/Qwen2.5-VL-7B-Instruct-4bit`
   (a local path, not an HF identifier). The HF cache on this M5
   has the **non-quantized** Qwen2.5-VL-7B-Instruct, not the 4-bit
   MLX-community version. Downloading the 4-bit variant is ~4 GB;
   not a hard blocker but it does require the env from (1)+(2) to
   be set up first.

## Why NOT scientifically blocking

**M5-5b already provides cross-architecture C-PERSIST evidence** on
Gemma 4 26B-A4B:

- 21 paired rows at 8 f, 9 paired rows at 32 f.
- 0 / 30 choice diffs, 0 / 30 correctness diffs.
- 22 / 30 byte-identical (8 paraphrases, all semantically equivalent).
- Median per-follow-up speedup: **9.11× at 8 f, 26.59× at 32 f**.

That is the science S1 was reaching for, just on a different model
family. Spending r2 budget to set up the Qwen 7B-4bit environment
(install codec_through, install torchvision, download weights, launch
runner) for an additional curve at 32 f / 64 f is lower-priority than
unblocking B0b r2 (which we did) and locking the bundle.

## What an S1 follow-up looks like

If the paper's reviewer process specifically asks for a Qwen 7B-4bit
long-context C-PERSIST curve on M5, the path is straightforward and
takes ~30 min env + ~1–2 h run on Sam's next M5 session:

```bash
# 1. Set up the env (one-time)
python3 -m venv ~/.venv-codec-through
source ~/.venv-codec-through/bin/activate
pip install -e /Users/sam/repos/codec-through-jfb
pip install torchvision

# 2. Download Qwen 7B-4bit weights (~4 GB) from mlx-community
hf download mlx-community/Qwen2.5-VL-7B-Instruct-4bit \
  --local-dir ~/models/Qwen2.5-VL-7B-Instruct-4bit

# 3. Run the 32 f sweep (no SWA on Qwen, mlx-vlm trim is safe)
PYTHON=~/.venv-codec-through/bin/python \
PHASE1_55L_OUT_DIR=research/experiments/2026/artifacts/sam_S1_qwen_long_evidence_cpersist_32f \
PHASE1_55L_VIDEO_IDS=037,100,116 \
PHASE1_55L_TURN_COUNTS=10,20 \
PHASE1_55L_POLICIES=fixed_k1,adaptive_post_q2 \
PHASE1_55L_FRAME_COUNT=32 \
RSS_GUARD_MB=80000 \
bash scripts/run_phase1_55L_many_turn_cpersist.sh

# 4. Same for 64 f if 32 f healthy
```

## What we did instead (S2)

Step 4 also asked for **S2 (M5 memory envelope)**. That is doable
without env setup because every existing schema-validated artifact
already records `peak_memory_gb`. See
`2026-04-30-phase-S2-sam-r2-m5-memory-envelope-findings.md` for the
extracted Gemma 4 26B-A4B envelope (49–52 GB at 8–128 f via direct
mlx-vlm load; 39 GB via `Gemma4VLM` wrapper). That covers the
paper's reproducibility-section memory question for Gemma 26B. The
Qwen 7B-4bit and Gemma E4B-4bit cells in S2 are deferred for the
same env-setup reason as S1 and would naturally land alongside the
S1 follow-up run.

## Cross-reference

- M5-5b 8 f findings: `2026-04-29-phase-M5-5b-sam-prefix-snapshot-fix-findings.md`
- M5-comp 32 f findings: `2026-04-29-phase-M5-comp-sam-prefix-snapshot-32f-composition-findings.md`
- S2 envelope findings: `2026-04-30-phase-S2-sam-r2-m5-memory-envelope-findings.md`
- r2 handoff Step 4 spec: `2026-04-30-sam-r2-handoff.md`
