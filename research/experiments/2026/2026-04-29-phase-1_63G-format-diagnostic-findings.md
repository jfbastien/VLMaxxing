# 2026-04-29 Phase 1.63G Format Diagnostic Findings

Prereg / intent: diagnose whether Gemma Track-B parse failures are parser
strictness or model-output failures before the paper frames Gemma 1.63G as
cross-architecture sparse-ViT evidence.

Command:

```bash
scripts/run_phase1_63G_format_diagnostic.sh
```

Artifact:

- `research/experiments/2026/artifacts/phase1_63G_gemma_track_b/format_diagnostic_summary.json`

Result:

| frame budget | dense parse failures | sparse parse failures | matched failures | permissive recoveries |
|---:|---:|---:|---:|---:|
| 8f | 11 | 11 | 11 | 0 |
| 16f | 3 | 3 | 3 | 0 |
| 32f | 4 | 4 | 4 | 0 |

The matched-failure diagnostic passes. A deliberately conservative permissive
parser recovers 0/18 failure items. The earlier tempting false positives came
from uppercasing prose and converting the article "a" into option `A`; the
diagnostic now avoids that failure mode.

Interpretation:

Gemma Track B should be framed as matched dense/sparse format failures with
zero paired drift among the scored rows, not as a format-clean run. The failure
mode is model/instruction-following limited rather than a parser policy that can
be safely repaired post hoc.
