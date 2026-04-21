# Session 4 run 1 — CONFOUNDED (DO NOT USE)

Artifacts moved here 2026-04-21 because a concurrent 7-GB Python
(`mtg_ingest_dry_run.py` from a different project, PID 65111) started
mid-queue and inflated memory pressure during EXP20.

Observed anomalies vs prereg / session-3 pattern:
- EXP19 → EXP20 paired E2E: **1.092×** (below the 1.10× MVBench gate)
- V_red cross-arm (dense_vision 7430 → 5876 ms): **20.9%** (prereg band [0.35, 0.45])
- `mean_decode_ms` jumped **439 → 711 ms** (+62%), far outside the 2% thermal gate

EXP21 was killed partway through to free memory; its jsonl/log are
truncated and are preserved here only for context.

Session 4 run 2 (in the parent directory) is the authoritative measurement.
Root-cause: external memory contention, not a 1.51V mechanism regression.
