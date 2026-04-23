#!/usr/bin/env python3
"""Phase 1.30 root-cause 6-arm decomposition analyzer.

Reads the six <arm>_summary.json files (plus the matching per-arm jsonl
rows) produced by `scripts/run_phase1_30_rootcause_decompose.sh` and prints:

 1. Raw per-arm accuracy (all_queries, first_queries, follow_ups), wall time,
    parse failures, degenerate count.
 2. Accuracy deltas vs cold_dense, with exact paired 95% McNemar-style
    bootstrap CIs when the per-item jsonl rows are available.
 3. V-only / K-only / combined decomposition and the interaction term, each
    with paired bootstrap CI.
 4. Hard-reset recovery for the dense and pruned streaming arms.

Codex round-29 asked for effect sizes + paired uncertainty, not just
pass/fail labels. This analyzer computes paired bootstrap CIs (default
5000 resamples) over the `correct` flag at matched `(item_id, q_index)`
keys; when the jsonl rows are missing, falls back to reporting point
estimates with unpaired binomial-proportion normal-approximation SE and
flags the degraded estimate.

No pandas, no numpy; pure stdlib so it runs in any venv.
"""

from __future__ import annotations

import argparse
import json
import math
import random
from pathlib import Path
from typing import Any

ARMS = [
    "cold_dense",
    "cold_pruned",
    "streaming_dense_off",
    "streaming_pruned_off",
    "streaming_dense_reset",
    "streaming_pruned_reset",
]

Slice = str  # "all_queries" | "first_queries" | "follow_ups"


def _load_summary(path: Path) -> dict[str, Any]:
    with path.open() as handle:
        return json.load(handle)


def _load_rows(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    with path.open() as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def _row_key(row: dict[str, Any]) -> tuple[str, int]:
    return (str(row["item_id"]), int(row["q_index"]))


def _correct_map(rows: list[dict[str, Any]]) -> dict[tuple[str, int], int]:
    return {_row_key(r): int(bool(r.get("correct", False))) for r in rows}


def _slice_keys(rows: list[dict[str, Any]], slice_name: Slice) -> set[tuple[str, int]]:
    if slice_name == "all_queries":
        return {_row_key(r) for r in rows}
    if slice_name == "first_queries":
        return {_row_key(r) for r in rows if int(r["q_index"]) == 0}
    if slice_name == "follow_ups":
        return {_row_key(r) for r in rows if int(r["q_index"]) >= 1}
    raise ValueError(f"unknown slice {slice_name}")


def _acc(summary: dict[str, Any], key: str) -> float:
    return float(summary[key]["accuracy"])


def _wall_s(summary: dict[str, Any]) -> float:
    return float(summary["total_wall_ms"]) / 1000.0


def _int_field(summary: dict[str, Any], key: str) -> int:
    return int(summary.get(key, 0))


def _fmt(value: float) -> str:
    return f"{value:.3f}"


def _paired_bootstrap_delta_ci(
    treatment: dict[tuple[str, int], int],
    control: dict[tuple[str, int], int],
    keys: set[tuple[str, int]],
    n_resamples: int,
    rng: random.Random,
) -> tuple[float, float, float, int]:
    """Paired delta (treatment_acc − control_acc) with BCa-free percentile CI.

    Both arms must cover every key in `keys`; missing keys are dropped and the
    effective n is returned. Resampling is done over the paired (t_i, c_i)
    tuples, which is the right unit when two arms ran the same queries.
    """
    pairs = [
        (treatment[k], control[k])
        for k in keys
        if k in treatment and k in control
    ]
    n = len(pairs)
    if n == 0:
        return (float("nan"), float("nan"), float("nan"), 0)

    point = sum(t - c for t, c in pairs) / n

    deltas: list[float] = []
    for _ in range(n_resamples):
        resampled = [pairs[rng.randrange(n)] for _ in range(n)]
        deltas.append(sum(t - c for t, c in resampled) / n)
    deltas.sort()
    lo = deltas[int(0.025 * n_resamples)]
    hi = deltas[int(0.975 * n_resamples) - 1]
    return (point, lo, hi, n)


def _binomial_se(p: float, n: int) -> float:
    if n == 0:
        return float("nan")
    return math.sqrt(max(p * (1.0 - p), 0.0) / n)


def _slice_n(summary: dict[str, Any], slice_name: Slice) -> int:
    return int(summary[slice_name]["n"])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "artifact_dir",
        type=Path,
        help="Directory holding <arm>_summary.json + <arm>.jsonl files.",
    )
    parser.add_argument(
        "--n-resamples",
        type=int,
        default=5000,
        help="Paired bootstrap resamples (default 5000).",
    )
    parser.add_argument("--seed", type=int, default=20260423)
    args = parser.parse_args()

    summaries: dict[str, dict[str, Any]] = {}
    correct_by_arm: dict[str, dict[tuple[str, int], int]] = {}
    rows_by_arm: dict[str, list[dict[str, Any]]] = {}
    for arm in ARMS:
        summary_path = args.artifact_dir / f"{arm}_summary.json"
        jsonl_path = args.artifact_dir / f"{arm}.jsonl"
        if summary_path.exists():
            summaries[arm] = _load_summary(summary_path)
        rows = _load_rows(jsonl_path)
        rows_by_arm[arm] = rows
        correct_by_arm[arm] = _correct_map(rows)

    if "cold_dense" not in summaries:
        raise SystemExit(f"missing {args.artifact_dir}/cold_dense_summary.json")

    base = summaries["cold_dense"]
    rng = random.Random(args.seed)
    paired_ok = bool(correct_by_arm["cold_dense"])

    print("\n== Raw summary ==")
    header = (
        f"{'arm':24s} {'all':>6s} {'q0':>6s} {'q23':>6s} "
        f"{'wall_s':>8s} {'parse':>6s} {'degen':>6s}"
    )
    print(header)
    print("-" * len(header))
    for arm in ARMS:
        summary = summaries.get(arm)
        if summary is None:
            continue
        print(
            f"{arm:24s} "
            f"{_fmt(_acc(summary, 'all_queries')):>6s} "
            f"{_fmt(_acc(summary, 'first_queries')):>6s} "
            f"{_fmt(_acc(summary, 'follow_ups')):>6s} "
            f"{_wall_s(summary):8.1f} "
            f"{_int_field(summary, 'parse_failures'):6d} "
            f"{_int_field(summary, 'degenerate_queries'):6d}"
        )

    print("\n== Accuracy deltas vs cold_dense (paired 95% CI) ==")
    base_correct = correct_by_arm["cold_dense"]
    base_rows = rows_by_arm["cold_dense"]
    slices: list[Slice] = ["all_queries", "first_queries", "follow_ups"]
    slice_labels = {"all_queries": "all", "first_queries": "q0", "follow_ups": "q23"}
    for arm in ARMS:
        summary = summaries.get(arm)
        if arm == "cold_dense" or summary is None:
            continue
        arm_correct = correct_by_arm[arm]
        line = f"{arm:24s} "
        for slice_name in slices:
            if paired_ok and arm_correct:
                keys = _slice_keys(base_rows, slice_name)
                delta, lo, hi, n = _paired_bootstrap_delta_ci(
                    arm_correct, base_correct, keys, args.n_resamples, rng
                )
                if not math.isnan(delta):
                    line += (
                        f"{slice_labels[slice_name]} {delta:+.3f} "
                        f"[{lo:+.3f},{hi:+.3f}] n={n}  "
                    )
                    continue
            # fallback: unpaired point estimate + binomial SE ~= +/- 1.96*SE
            arm_p = _acc(summary, slice_name)
            base_p = _acc(base, slice_name)
            delta = arm_p - base_p
            arm_n = _slice_n(summary, slice_name)
            base_n = _slice_n(base, slice_name)
            se = math.sqrt(
                _binomial_se(arm_p, arm_n) ** 2
                + _binomial_se(base_p, base_n) ** 2
            )
            lo = delta - 1.96 * se
            hi = delta + 1.96 * se
            line += (
                f"{slice_labels[slice_name]} {delta:+.3f} "
                f"[{lo:+.3f},{hi:+.3f}] (unpaired)  "
            )
        print(line.rstrip())

    needed = {"cold_pruned", "streaming_dense_off", "streaming_pruned_off"}
    if needed.issubset(summaries):
        v_only_pt = _acc(summaries["cold_pruned"], "all_queries") - _acc(base, "all_queries")
        k_only_pt = (
            _acc(summaries["streaming_dense_off"], "all_queries")
            - _acc(base, "all_queries")
        )
        combined_pt = (
            _acc(summaries["streaming_pruned_off"], "all_queries")
            - _acc(base, "all_queries")
        )
        interaction_pt = combined_pt - (v_only_pt + k_only_pt)

        print("\n== Composition decomposition (all_queries) ==")
        if paired_ok:
            all_keys = _slice_keys(base_rows, "all_queries")
            for label, arm_name in [
                ("V-only", "cold_pruned"),
                ("K-only", "streaming_dense_off"),
                ("Combined", "streaming_pruned_off"),
            ]:
                delta, lo, hi, n = _paired_bootstrap_delta_ci(
                    correct_by_arm[arm_name],
                    base_correct,
                    all_keys,
                    args.n_resamples,
                    rng,
                )
                print(
                    f"{label:9s} ({arm_name:22s} − cold_dense): "
                    f"{delta:+.3f} [{lo:+.3f}, {hi:+.3f}] n={n}"
                )
            # interaction: bootstrap the linearity residual with paired keys.
            # NB: `keys` must be a sequence (not a set) so that bootstrap
            # resamples with replacement preserve duplicate draws — the
            # whole point of the bootstrap is to let items be re-picked.
            # Coercing to a set collapsed duplicates and destroyed the
            # variance estimate (Codex round-30 regression; fixed here).
            def _interaction_stat(
                pruned: dict[tuple[str, int], int],
                dense_off: dict[tuple[str, int], int],
                pruned_off: dict[tuple[str, int], int],
                baseline: dict[tuple[str, int], int],
                keys: list[tuple[str, int]],
            ) -> float:
                m = len(keys)
                v = sum(pruned[k] - baseline[k] for k in keys) / m
                k_ = sum(dense_off[k] - baseline[k] for k in keys) / m
                c = sum(pruned_off[k] - baseline[k] for k in keys) / m
                return c - (v + k_)

            keys = [
                k
                for k in all_keys
                if k in correct_by_arm["cold_pruned"]
                and k in correct_by_arm["streaming_dense_off"]
                and k in correct_by_arm["streaming_pruned_off"]
                and k in base_correct
            ]
            if keys:
                n = len(keys)
                # Point estimate: unique paired items (one draw per key).
                point = _interaction_stat(
                    correct_by_arm["cold_pruned"],
                    correct_by_arm["streaming_dense_off"],
                    correct_by_arm["streaming_pruned_off"],
                    base_correct,
                    keys,
                )
                stats_samples: list[float] = []
                for _ in range(args.n_resamples):
                    # Sample WITH replacement; pass the resampled list
                    # (duplicates intact) to the statistic.
                    resampled = [keys[rng.randrange(n)] for _ in range(n)]
                    stats_samples.append(
                        _interaction_stat(
                            correct_by_arm["cold_pruned"],
                            correct_by_arm["streaming_dense_off"],
                            correct_by_arm["streaming_pruned_off"],
                            base_correct,
                            resampled,
                        )
                    )
                stats_samples.sort()
                lo_i = stats_samples[int(0.025 * args.n_resamples)]
                hi_i = stats_samples[int(0.975 * args.n_resamples) - 1]
                print(
                    f"Interaction (combined − V − K):     "
                    f"{point:+.3f} [{lo_i:+.3f}, {hi_i:+.3f}] n={n}"
                )
                includes_zero = lo_i <= 0 <= hi_i
                non_additive_by_point = abs(point) > max(
                    abs(v_only_pt), abs(k_only_pt)
                )
                print(
                    f"  → interaction CI {'includes' if includes_zero else 'excludes'} 0; "
                    f"point term {'IS' if non_additive_by_point else 'is NOT'} "
                    f"larger than max(|V|,|K|)"
                )
        else:
            print(f"V-only (cold_pruned − cold_dense):            {v_only_pt:+.3f}")
            print(f"K-only (streaming_dense_off − cold_dense):    {k_only_pt:+.3f}")
            print(f"Combined (streaming_pruned_off − cold_dense): {combined_pt:+.3f}")
            print(f"Interaction term (combined − V − K):          {interaction_pt:+.3f}")

        # H_V / H_K adjudication (preregistered gates)
        print("\n== Preregistered gate summary ==")
        abs_combined = abs(combined_pt)
        h_v = abs(v_only_pt) >= 0.5 * abs_combined
        h_k = abs(k_only_pt) >= 0.5 * abs_combined
        h_interaction_point = abs(interaction_pt) > max(abs(v_only_pt), abs(k_only_pt))
        print(f"H_V (V-only dominates): |V|={abs(v_only_pt):.3f} vs 0.5×|combined|={0.5*abs_combined:.3f}  → {'PASS' if h_v else 'FAIL'}")
        print(f"H_K (K-only dominates): |K|={abs(k_only_pt):.3f} vs 0.5×|combined|={0.5*abs_combined:.3f}  → {'PASS' if h_k else 'FAIL'}")
        print(f"H_interaction (non-additive, point): |interact|={abs(interaction_pt):.3f} vs max(|V|,|K|)={max(abs(v_only_pt), abs(k_only_pt)):.3f}  → {'PASS' if h_interaction_point else 'FAIL'}")

    if {"streaming_dense_off", "streaming_dense_reset"}.issubset(summaries):
        off = summaries["streaming_dense_off"]
        reset = summaries["streaming_dense_reset"]
        print("\n== Hard-reset recovery: dense streaming ==")
        off_q23 = _acc(off, "follow_ups")
        reset_q23 = _acc(reset, "follow_ups")
        cold_q23 = _acc(base, "follow_ups")
        recovered = reset_q23 - off_q23
        loss = cold_q23 - off_q23
        frac = recovered / loss if loss > 1e-9 else float("nan")
        print(
            f"q23 acc off={off_q23:.3f}  reset={reset_q23:.3f}  "
            f"delta={recovered:+.3f}  recovered_frac={frac:.3f} (H_reset PASS if ≥ 0.50)"
        )
        print(
            f"q0  acc off={_acc(off, 'first_queries'):.3f}  "
            f"reset={_acc(reset, 'first_queries'):.3f}  "
            f"delta={_acc(reset, 'first_queries') - _acc(off, 'first_queries'):+.3f}"
        )

    if {"streaming_pruned_off", "streaming_pruned_reset"}.issubset(summaries):
        off = summaries["streaming_pruned_off"]
        reset = summaries["streaming_pruned_reset"]
        print("\n== Hard-reset recovery: pruned streaming ==")
        print(
            f"q23 acc off={_acc(off, 'follow_ups'):.3f}  "
            f"reset={_acc(reset, 'follow_ups'):.3f}  "
            f"delta={_acc(reset, 'follow_ups') - _acc(off, 'follow_ups'):+.3f}"
        )
        print(
            f"q0  acc off={_acc(off, 'first_queries'):.3f}  "
            f"reset={_acc(reset, 'first_queries'):.3f}  "
            f"delta={_acc(reset, 'first_queries') - _acc(off, 'first_queries'):+.3f}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
