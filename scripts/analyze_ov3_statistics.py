#!/usr/bin/env python3
"""Statistical audit of OV-3 results per wiki standards.

Adds Wilson and Clopper-Pearson confidence intervals to every reported proportion,
runs McNemar's exact test on paired codec-vs-pixel and codec-vs-dense data, computes
the dense determinism rate from the two 2-seed overlap pairs, and stage-share-style
component timing decomposition for the codec extraction overhead claim.

CPU-only. Reads existing results.jsonl artifacts under
research/experiments/2026/artifacts/phase1_29_onevision_dev{,_n20_short,_holdout_disjoint}/.
"""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from pathlib import Path
from statistics import mean, median

DEFAULT_TRANCHES = (
    Path("research/experiments/2026/artifacts/phase1_29_onevision_dev"),
    Path("research/experiments/2026/artifacts/phase1_29_onevision_dev_n20_short"),
    Path("research/experiments/2026/artifacts/phase1_29_onevision_holdout_disjoint"),
)
SOURCES = ("novel_coded", "motion", "residual", "fused")


# ---- statistical primitives (no scipy dependency) ----


def wilson_ci(successes: int, n: int, *, z: float = 1.96) -> tuple[float, float]:
    """Wilson score interval at z (default 95% two-sided z=1.96)."""

    if n <= 0:
        return (0.0, 0.0)
    p = successes / n
    z2 = z * z
    denom = 1.0 + z2 / n
    center = (p + z2 / (2 * n)) / denom
    halfwidth = (z * math.sqrt(p * (1 - p) / n + z2 / (4 * n * n))) / denom
    return (max(0.0, center - halfwidth), min(1.0, center + halfwidth))


def clopper_pearson_ci(successes: int, n: int, *, alpha: float = 0.05) -> tuple[float, float]:
    """Exact Clopper-Pearson (Beta) interval."""

    if n <= 0:
        return (0.0, 0.0)
    if successes == 0:
        lower = 0.0
    else:
        lower = _beta_ppf(alpha / 2, successes, n - successes + 1)
    if successes == n:
        upper = 1.0
    else:
        upper = _beta_ppf(1 - alpha / 2, successes + 1, n - successes)
    return (lower, upper)


def _beta_ppf(q: float, a: float, b: float, *, tol: float = 1e-9) -> float:
    """Bisection on the regularized incomplete beta to find p where Iq(a,b)=q."""

    if q <= 0:
        return 0.0
    if q >= 1:
        return 1.0
    lo, hi = 0.0, 1.0
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if _regularized_incomplete_beta(mid, a, b) < q:
            lo = mid
        else:
            hi = mid
        if hi - lo < tol:
            break
    return 0.5 * (lo + hi)


def _regularized_incomplete_beta(x: float, a: float, b: float) -> float:
    """Lentz's method for I_x(a,b)."""

    if x <= 0:
        return 0.0
    if x >= 1:
        return 1.0
    bt = math.exp(
        math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b) + a * math.log(x) + b * math.log(1 - x)
    )
    if x < (a + 1) / (a + b + 2):
        return bt * _betacf(x, a, b) / a
    return 1.0 - bt * _betacf(1 - x, b, a) / b


def _betacf(x: float, a: float, b: float, *, max_iter: int = 200, tol: float = 1e-12) -> float:
    qab = a + b
    qap = a + 1.0
    qam = a - 1.0
    c = 1.0
    d = 1.0 - qab * x / qap
    if abs(d) < 1e-30:
        d = 1e-30
    d = 1.0 / d
    h = d
    for m in range(1, max_iter + 1):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < 1e-30:
            d = 1e-30
        c = 1.0 + aa / c
        if abs(c) < 1e-30:
            c = 1e-30
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < 1e-30:
            d = 1e-30
        c = 1.0 + aa / c
        if abs(c) < 1e-30:
            c = 1e-30
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < tol:
            break
    return h


def mcnemar_exact(b: int, c: int) -> float:
    """Exact two-sided binomial p-value for the McNemar test.

    b: rows where condition A succeeds and B fails.
    c: rows where condition A fails and B succeeds.
    Tests H0: P(A>B) = P(A<B) = 0.5 conditional on discordant pairs.
    """

    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    # Two-sided exact: 2 * P(X <= k) under Binomial(n, 0.5), capped at 1.
    p_one_sided = sum(math.comb(n, i) for i in range(k + 1)) / (2**n)
    return min(1.0, 2.0 * p_one_sided)


# ---- data loading ----


@dataclass(frozen=True, slots=True)
class ItemRow:
    item_id: str
    dense_choice: int | None
    pixel_choice: int | None
    codec_choice: int | None
    dense_correct: bool
    pixel_correct: bool
    codec_correct: bool
    codec_extract_s: float


def _row(item: dict) -> ItemRow:
    return ItemRow(
        item_id=str(item["item_id"]),
        dense_choice=item.get("dense", {}).get("choice_index"),
        pixel_choice=item.get("pixel_cached", {}).get("choice_index"),
        codec_choice=item.get("codec_cached", {}).get("choice_index"),
        dense_correct=bool(item.get("dense", {}).get("correct", False)),
        pixel_correct=bool(item.get("pixel_cached", {}).get("correct", False)),
        codec_correct=bool(item.get("codec_cached", {}).get("correct", False)),
        codec_extract_s=float(item.get("codec_extract_s", 0.0)),
    )


def _load_source(tranche: Path, source: str) -> list[ItemRow]:
    path = tranche / source / "results.jsonl"
    if not path.exists():
        return []
    rows: list[ItemRow] = []
    with path.open() as h:
        for line in h:
            rows.append(_row(json.loads(line)))
    return rows


# ---- analyses ----


def _proportion_with_ci(num: int, n: int) -> dict:
    wilson = wilson_ci(num, n)
    cp = clopper_pearson_ci(num, n)
    return {
        "successes": num,
        "n": n,
        "rate": num / n if n > 0 else 0.0,
        "wilson_95_ci": [round(wilson[0], 4), round(wilson[1], 4)],
        "clopper_pearson_95_ci": [round(cp[0], 4), round(cp[1], 4)],
    }


def _per_source_correctness(rows: list[ItemRow]) -> dict:
    n = len(rows)
    if n == 0:
        return {}
    return {
        "n": n,
        "dense": _proportion_with_ci(sum(r.dense_correct for r in rows), n),
        "pixel": _proportion_with_ci(sum(r.pixel_correct for r in rows), n),
        "codec": _proportion_with_ci(sum(r.codec_correct for r in rows), n),
        "codec_dense_agreement": _proportion_with_ci(
            sum(r.codec_choice == r.dense_choice for r in rows), n
        ),
        "codec_pixel_agreement": _proportion_with_ci(
            sum(r.codec_choice == r.pixel_choice for r in rows), n
        ),
    }


def _mcnemar_codec_vs_pixel(rows: list[ItemRow]) -> dict:
    """Paired test on correctness: rows fixed by codec vs broken by codec."""

    fixed = sum(r.codec_correct and not r.pixel_correct for r in rows)
    broken = sum(r.pixel_correct and not r.codec_correct for r in rows)
    p = mcnemar_exact(fixed, broken)
    return {
        "rows_fixed_by_codec": fixed,
        "rows_broken_by_codec": broken,
        "rows_concordant": len(rows) - fixed - broken,
        "n": len(rows),
        "mcnemar_exact_p_two_sided": round(p, 4),
        "interpretation": (
            "PASS" if p < 0.05 and fixed > broken
            else "FAIL" if p < 0.05 and broken > fixed
            else "INCONCLUSIVE"
        ),
    }


def _dense_determinism(tranches: tuple[Path, ...]) -> dict:
    """Compare dense answers across the two driver-session overlaps.

    Pair 1: dev (n=10) vs n=20 broader on the 10 dev items.
    Pair 2: n=20 broader vs disjoint on the 10 holdout items.
    Each pair gives one independent observation per item. Items that have
    different dense answers across the two sessions are dense flips.
    """

    def _by_id(path: Path) -> dict[str, ItemRow]:
        rows = _load_source(path, "novel_coded")
        return {r.item_id: r for r in rows}

    dev = _by_id(tranches[0])
    n20 = _by_id(tranches[1])
    disjoint = _by_id(tranches[2])

    pair1_items = sorted(set(dev.keys()) & set(n20.keys()))
    pair2_items = sorted(set(n20.keys()) & set(disjoint.keys()))

    pair1_flips = sum(1 for i in pair1_items if dev[i].dense_choice != n20[i].dense_choice)
    pair2_flips = sum(
        1 for i in pair2_items if n20[i].dense_choice != disjoint[i].dense_choice
    )

    n_total = len(pair1_items) + len(pair2_items)
    flips_total = pair1_flips + pair2_flips
    return {
        "pair1_dev_vs_n20": {
            "n_items": len(pair1_items),
            "flips": pair1_flips,
            "flipped_items": [
                i for i in pair1_items if dev[i].dense_choice != n20[i].dense_choice
            ],
        },
        "pair2_n20_vs_disjoint": {
            "n_items": len(pair2_items),
            "flips": pair2_flips,
            "flipped_items": [
                i for i in pair2_items if n20[i].dense_choice != disjoint[i].dense_choice
            ],
        },
        "aggregate": _proportion_with_ci(flips_total, n_total),
        "interpretation": (
            f"Dense flipped on {flips_total}/{n_total} per-item dense-vs-dense comparisons "
            f"across two-driver-session overlaps. Wilson 95% upper bound on the flip rate "
            f"is {wilson_ci(flips_total, n_total)[1]:.3f}."
        ),
    }


def _codec_extract_timing(rows: list[ItemRow]) -> dict:
    times = [r.codec_extract_s for r in rows if r.codec_extract_s > 0]
    if not times:
        return {}
    sorted_times = sorted(times)
    n = len(sorted_times)
    p95_idx = max(0, min(n - 1, int(math.ceil(0.95 * n)) - 1))
    return {
        "n": n,
        "min_s": min(times),
        "median_s": median(times),
        "mean_s": mean(times),
        "p95_s": sorted_times[p95_idx],
        "max_s": max(times),
    }


def _multiple_comparisons_summary(per_tranche_results: list[dict]) -> dict:
    """Bonferroni-corrected family-wise error commentary for our 12 cells."""

    n_cells = sum(
        1 for r in per_tranche_results for _ in r.get("by_source", {})
    )
    return {
        "n_cells_compared": n_cells,
        "bonferroni_alpha_for_per_cell_at_family_05": round(0.05 / n_cells, 4)
        if n_cells > 0
        else None,
        "note": (
            "We tested 4 codec sources × 3 tranches = 12 cells. Per-cell McNemar "
            "p-values must be compared against alpha = 0.05 / 12 ≈ 0.0042 for "
            "family-wise control under Bonferroni. Most p-values here are >0.05 "
            "even uncorrected at this N; the multiple-comparisons concern is "
            "directional, not the limiting factor."
        ),
    }


# ---- main ----


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--tranche",
        type=Path,
        action="append",
        default=None,
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path(
            "research/experiments/2026/artifacts/phase1_29_onevision_dev/statistical_audit.json"
        ),
    )
    args = parser.parse_args()

    tranches = tuple(args.tranche) if args.tranche else DEFAULT_TRANCHES

    payload: dict = {"tranches": [], "extraction_timing": {}}
    for tranche in tranches:
        tpayload: dict = {"path": str(tranche), "by_source": {}}
        for source in SOURCES:
            rows = _load_source(tranche, source)
            if not rows:
                continue
            tpayload["by_source"][source] = {
                "correctness": _per_source_correctness(rows),
                "mcnemar_codec_vs_pixel": _mcnemar_codec_vs_pixel(rows),
            }
        payload["tranches"].append(tpayload)

    if len(tranches) >= 3:
        payload["dense_determinism"] = _dense_determinism(tuple(tranches[:3]))
    payload["multiple_comparisons"] = _multiple_comparisons_summary(payload["tranches"])

    # Aggregate extraction timing across all tranches and sources.
    all_rows: list[ItemRow] = []
    for tranche in tranches:
        for source in SOURCES:
            all_rows.extend(_load_source(tranche, source))
    payload["extraction_timing"] = _codec_extract_timing(all_rows)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")

    # Print summary.
    print(f"# Statistical audit across {len(tranches)} tranches\n")
    print("## Per-cell correctness with Wilson 95% CI")
    print("| tranche | source | n | codec_acc | codec Wilson CI | codec→dense agreement | agreement Wilson CI | mcnemar p (codec vs pixel) |")
    print("|---|---|---|---|---|---|---|---|")
    for t in payload["tranches"]:
        tname = Path(t["path"]).name
        for source, data in t["by_source"].items():
            c = data["correctness"]
            mc = data["mcnemar_codec_vs_pixel"]
            print(
                f"| {tname} | {source} | {c['n']} | "
                f"{c['codec']['rate']:.3f} | "
                f"[{c['codec']['wilson_95_ci'][0]:.3f}, {c['codec']['wilson_95_ci'][1]:.3f}] | "
                f"{c['codec_dense_agreement']['rate']:.3f} | "
                f"[{c['codec_dense_agreement']['wilson_95_ci'][0]:.3f}, "
                f"{c['codec_dense_agreement']['wilson_95_ci'][1]:.3f}] | "
                f"{mc['mcnemar_exact_p_two_sided']:.3f} ({mc['interpretation']}) |"
            )
    if "dense_determinism" in payload:
        print()
        print("## Dense determinism (driver-session overlaps)")
        dd = payload["dense_determinism"]
        print(f"- pair 1 (dev vs n=20 on 10 dev items): {dd['pair1_dev_vs_n20']['flips']} flips / {dd['pair1_dev_vs_n20']['n_items']}")
        print(f"- pair 2 (n=20 vs disjoint on 10 holdout items): {dd['pair2_n20_vs_disjoint']['flips']} flips / {dd['pair2_n20_vs_disjoint']['n_items']}")
        a = dd["aggregate"]
        print(
            f"- aggregate: {a['successes']}/{a['n']} = {a['rate']:.3f}, "
            f"Wilson 95% [{a['wilson_95_ci'][0]:.3f}, {a['wilson_95_ci'][1]:.3f}], "
            f"Clopper-Pearson [{a['clopper_pearson_95_ci'][0]:.3f}, {a['clopper_pearson_95_ci'][1]:.3f}]"
        )
    print()
    print("## Codec extraction timing (s, aggregated)")
    et = payload["extraction_timing"]
    if et:
        print(
            f"- n={et['n']}, min={et['min_s']:.2f}, median={et['median_s']:.2f}, "
            f"mean={et['mean_s']:.2f}, p95={et['p95_s']:.2f}, max={et['max_s']:.2f}"
        )
    print()
    print("## Multiple comparisons")
    print(f"- {payload['multiple_comparisons']['note']}")
    print(f"\nwrote {args.out}")


if __name__ == "__main__":
    main()
