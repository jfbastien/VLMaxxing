#!/usr/bin/env python3
"""Compare one unpatched/patched phase-1.51V summary pair."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def _load(path: Path) -> dict:
    return json.loads(path.read_text())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--unpatched", type=Path, required=True)
    parser.add_argument("--patched", type=Path, required=True)
    args = parser.parse_args()

    u = _load(args.unpatched)
    p = _load(args.patched)

    u_v = float(u["mean_dense_vision_ms"])
    p_v = float(p["mean_dense_vision_ms"])
    u_e2e = float(u["mean_dense_end_to_end_ms"])
    p_e2e = float(p["mean_dense_end_to_end_ms"])
    u_decode = float(u["mean_decode_ms"])
    p_decode = float(p["mean_decode_ms"])
    u_acc = float(u["dense_accuracy"])
    p_acc = float(p["dense_accuracy"])

    v_red = 1.0 - (p_v / u_v)
    e2e_speedup = u_e2e / p_e2e
    decode_drift = (p_decode - u_decode) / u_decode if u_decode else 0.0
    acc_delta = p_acc - u_acc
    v_share = u_v / u_e2e if u_e2e else 0.0
    ceiling = 1.0 / (1.0 - (v_share * v_red)) if v_share * v_red < 1.0 else float("inf")

    print(f"unpatched: {args.unpatched}")
    print(f"patched:   {args.patched}")
    print(f"V_red:            {v_red:+.4f}")
    print(f"E2E speedup:      {e2e_speedup:.4f}x")
    print(f"Decode drift:     {decode_drift:+.4%}")
    print(f"Accuracy delta:   {acc_delta:+.4f}")
    print(f"V_share (dense):  {v_share:+.4f}")
    print(f"Ceiling@V_red:    {ceiling:.4f}x")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
