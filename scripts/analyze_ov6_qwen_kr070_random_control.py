#!/usr/bin/env python3
"""Analyze the M5 Qwen kr=0.7 codec-vs-random clean control.

This audit answers one narrow paper gate: does the same-run M5
``codec_novel_coded`` arm at Qwen VideoMME-short N=57, 8 frames, layer 2, and
keep-rate 0.7 meet or exceed a four-seed matched random-keep distribution?
It intentionally does not reuse the kr=0.5 random-vs-magnitude analyzer because
that script answers a different scientific question.
"""

from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
import tomllib
from pathlib import Path
from typing import Any, cast

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.analyze_ov3_statistics import mcnemar_exact, wilson_ci  # noqa: E402

DEFAULT_ROOT = Path("research/experiments/2026/artifacts/m5_ov6_qwen_n57_kr070_l2_random_control")
EXPECTED_MANIFEST = Path("research/benchmark_manifests/videomme_short_present_v1_n57.toml")
EXPECTED_MODEL_NAME = "Qwen2.5-VL-7B-Instruct-4bit"
EXPECTED_FRAME_COUNT = 8
EXPECTED_MAX_TOKENS = 32
EXPECTED_LAYER = 2
EXPECTED_KEEP_RATE = 0.70
EXPECTED_CODEC_GEOMETRY = "qwen_merged_groups_v1"
EXPECTED_WRAPPER = "scripts/run_ov6_m5_qwen_kr070_random_control.sh"
EXPECTED_ROOT_NAME = "m5_ov6_qwen_n57_kr070_l2_random_control"
SEEDS = (1, 7, 42, 100)
REQUIRED_ARMS = (
    "dense",
    "magnitude_norm",
    "codec_novel_coded",
    *(f"uniform_random_seed{seed}" for seed in SEEDS),
)
SPARSE_ARMS = REQUIRED_ARMS[1:]
PROVENANCE_FIELDS = ("generated_at", "git_commit", "git_dirty", "git_dirty_scope")


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(path)
    payload = json.loads(path.read_text())
    if not isinstance(payload, dict):
        raise ValueError(f"expected object JSON: {path}")
    return cast(dict[str, Any], payload)


def _load_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(path)
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    with path.open() as handle:
        for line_number, line in enumerate(handle, start=1):
            payload = json.loads(line)
            if not isinstance(payload, dict):
                raise ValueError(f"expected object JSONL row at {path}:{line_number}")
            row = cast(dict[str, Any], payload)
            item_id = str(row["item_id"])
            if item_id in seen:
                raise ValueError(f"duplicate item_id {item_id!r} in {path}")
            seen.add(item_id)
            rows.append(row)
    return rows


def _norm_path(value: str | Path) -> str:
    return str(Path(value).expanduser().resolve(strict=False))


def _assert_equal(actual: object, expected: object, field: str) -> None:
    if actual != expected:
        raise ValueError(f"{field} mismatch: actual={actual!r} expected={expected!r}")


def _assert_float_close(actual: object, expected: float, field: str, *, tol: float = 1e-9) -> None:
    if not isinstance(actual, int | float) or not math.isfinite(float(actual)):
        raise ValueError(f"{field} must be finite numeric, got {actual!r}")
    if abs(float(actual) - expected) > tol:
        raise ValueError(f"{field} mismatch: actual={actual!r} expected={expected!r}")


def _prop(successes: int, n: int) -> dict[str, Any]:
    lo, hi = wilson_ci(successes, n)
    return {
        "successes": successes,
        "n": n,
        "rate": successes / n if n else 0.0,
        "wilson_95_ci": [round(lo, 4), round(hi, 4)],
    }


def _accuracy(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return _prop(sum(1 for row in rows if bool(row["correct"])), len(rows))


def _item_ids(rows: list[dict[str, Any]]) -> list[str]:
    return [str(row["item_id"]) for row in rows]


def _expected_item_ids() -> list[str]:
    payload = tomllib.loads(EXPECTED_MANIFEST.read_text())
    item_ids = payload.get("item_ids")
    if not isinstance(item_ids, list):
        raise ValueError(f"expected item_ids list in {EXPECTED_MANIFEST}")
    return [str(item_id) for item_id in item_ids]


def _validate_run_marker(root: Path) -> str:
    marker = _load_json(root / "clean_control_run_marker.json")
    _assert_equal(
        marker.get("schema"),
        "ov6_qwen_kr070_random_control_run_v1",
        "run marker schema",
    )
    _assert_equal(marker.get("wrapper"), EXPECTED_WRAPPER, "run marker wrapper")
    _assert_equal(marker.get("root"), EXPECTED_ROOT_NAME, "run marker root")
    _assert_equal(marker.get("manifest"), str(EXPECTED_MANIFEST), "run marker manifest")
    _assert_equal(marker.get("model"), EXPECTED_MODEL_NAME, "run marker model")
    _assert_equal(marker.get("frame_count"), str(EXPECTED_FRAME_COUNT), "run marker frame_count")
    _assert_equal(marker.get("layer"), str(EXPECTED_LAYER), "run marker layer")
    _assert_equal(
        marker.get("configured_keep_rate"),
        f"{EXPECTED_KEEP_RATE:.2f}",
        "run marker configured_keep_rate",
    )
    _assert_equal(
        marker.get("seeds"),
        " ".join(str(seed) for seed in SEEDS),
        "run marker seeds",
    )
    prereg = marker.get("preregistration")
    if not isinstance(prereg, str) or not prereg.startswith("research/experiments/2026/"):
        raise ValueError(
            f"run marker preregistration must be a repo-relative prereg path: {prereg!r}"
        )
    if "qwen" not in prereg or "kr070" not in prereg or "random" not in prereg:
        raise ValueError(
            f"run marker preregistration does not name qwen kr070 random control: {prereg!r}"
        )
    if not isinstance(marker.get("git_commit"), str) or not marker["git_commit"]:
        raise ValueError("run marker missing git_commit")
    return str(marker["git_commit"])


def _parse_failures(rows: list[dict[str, Any]]) -> int:
    return sum(1 for row in rows if bool(row.get("parse_failure", False)))


def _require_provenance(summary: dict[str, Any], *, arm: str) -> None:
    missing = [field for field in PROVENANCE_FIELDS if field not in summary]
    if missing:
        raise ValueError(f"{arm} summary missing provenance fields: {missing}")
    if bool(summary.get("git_dirty", False)):
        raise ValueError(f"{arm} artifact was generated from a dirty git tree")


def _summary_keep_rate(summary: dict[str, Any], *, arm: str) -> float:
    value = summary.get("mean_effective_keep_rate")
    if not isinstance(value, int | float) or not math.isfinite(float(value)):
        raise ValueError(f"{arm} mean_effective_keep_rate must be finite numeric")
    return float(value)


def _validate_common_config(
    summary: dict[str, Any],
    *,
    arm: str,
    reference_manifest: str,
    reference_model_name: str,
    expected_n: int,
) -> None:
    _assert_equal(int(summary["n_items"]), expected_n, f"{arm} n_items")
    _assert_equal(
        _norm_path(str(summary["manifest"])),
        reference_manifest,
        f"{arm} manifest",
    )
    model_name = Path(str(summary["model_path"])).name
    _assert_equal(model_name, reference_model_name, f"{arm} model_path.name")
    _assert_equal(int(summary["frame_count"]), EXPECTED_FRAME_COUNT, f"{arm} frame_count")
    _assert_equal(int(summary["max_tokens"]), EXPECTED_MAX_TOKENS, f"{arm} max_tokens")
    _require_provenance(summary, arm=arm)


def _validate_dense(summary: dict[str, Any]) -> None:
    _assert_equal(bool(summary["vision_tower_patched"]), False, "dense vision_tower_patched")
    _assert_equal(summary["vision_tower_layer"], None, "dense vision_tower_layer")
    _assert_equal(summary["vision_tower_keep_rate"], None, "dense vision_tower_keep_rate")
    _assert_equal(summary["score_mode"], None, "dense score_mode")
    _assert_equal(summary["codec_score_source"], None, "dense codec_score_source")


def _validate_sparse_summary(summary: dict[str, Any], *, arm: str) -> None:
    _assert_equal(bool(summary["vision_tower_patched"]), True, f"{arm} vision_tower_patched")
    _assert_equal(int(summary["vision_tower_layer"]), EXPECTED_LAYER, f"{arm} vision_tower_layer")
    _assert_float_close(
        summary["vision_tower_keep_rate"],
        EXPECTED_KEEP_RATE,
        f"{arm} vision_tower_keep_rate",
    )


def _validate_magnitude(summary: dict[str, Any]) -> None:
    _validate_sparse_summary(summary, arm="magnitude_norm")
    _assert_equal(summary["score_mode"], "magnitude_norm", "magnitude_norm score_mode")
    _assert_equal(summary["score_seed"], None, "magnitude_norm score_seed")
    _assert_equal(summary["codec_score_source"], None, "magnitude_norm codec_score_source")


def _validate_codec(summary: dict[str, Any]) -> None:
    _validate_sparse_summary(summary, arm="codec_novel_coded")
    _assert_equal(summary["score_mode"], "codec_grid", "codec_novel_coded score_mode")
    _assert_equal(summary["score_seed"], None, "codec_novel_coded score_seed")
    _assert_equal(
        summary["codec_score_source"], "novel_coded", "codec_novel_coded codec_score_source"
    )
    _assert_equal(
        summary.get("codec_score_runtime_source"),
        "sidecar",
        "codec_novel_coded codec_score_runtime_source",
    )
    _assert_equal(
        summary.get("codec_score_sidecar_geometry"),
        EXPECTED_CODEC_GEOMETRY,
        "codec_novel_coded codec_score_sidecar_geometry",
    )
    sidecar_load = summary.get("codec_sidecar_load_mean_s_per_item")
    if not isinstance(sidecar_load, int | float) or not math.isfinite(float(sidecar_load)):
        raise ValueError("codec_novel_coded missing finite codec_sidecar_load_mean_s_per_item")


def _validate_random(summary: dict[str, Any], *, seed: int) -> None:
    arm = f"uniform_random_seed{seed}"
    _validate_sparse_summary(summary, arm=arm)
    _assert_equal(summary["score_mode"], "uniform_random", f"{arm} score_mode")
    _assert_equal(summary["score_seed"], seed, f"{arm} score_seed")
    _assert_equal(summary["codec_score_source"], None, f"{arm} codec_score_source")


def _load_arm(root: Path, arm: str) -> dict[str, Any]:
    arm_dir = root / arm
    summary = _load_json(arm_dir / "summary.json")
    rows = _load_rows(arm_dir / "results.jsonl")
    if int(summary["n_items"]) != len(rows):
        raise ValueError(
            f"{arm} summary n_items does not match results rows: "
            f"{summary['n_items']!r} != {len(rows)}"
        )
    parse_failures = _parse_failures(rows)
    if parse_failures:
        raise ValueError(f"{arm} contains parse failures: {parse_failures}")
    return {
        "summary": summary,
        "rows": rows,
    }


def _paired(
    candidate_rows: list[dict[str, Any]], baseline_rows: list[dict[str, Any]]
) -> dict[str, Any]:
    if _item_ids(candidate_rows) != _item_ids(baseline_rows):
        raise ValueError("paired rows must have identical ordered item_ids")
    fixes = 0
    breaks = 0
    choice_agree = 0
    for candidate, baseline in zip(candidate_rows, baseline_rows, strict=True):
        candidate_correct = bool(candidate["correct"])
        baseline_correct = bool(baseline["correct"])
        fixes += int(candidate_correct and not baseline_correct)
        breaks += int(baseline_correct and not candidate_correct)
        choice_agree += int(candidate.get("choice_index") == baseline.get("choice_index"))
    n = len(candidate_rows)
    return {
        "codec_correct_random_wrong": fixes,
        "codec_wrong_random_correct": breaks,
        "mcnemar_exact_p_two_sided": round(mcnemar_exact(fixes, breaks), 4),
        "choice_agreement": _prop(choice_agree, n),
        "n": n,
    }


def _arm_payload(root: Path, arm: str, arm_data: dict[str, Any]) -> dict[str, Any]:
    summary = cast(dict[str, Any], arm_data["summary"])
    rows = cast(list[dict[str, Any]], arm_data["rows"])
    e2e = summary.get("mean_dense_end_to_end_ms")
    e2e_score = summary.get("mean_end_to_end_including_codec_score_runtime_ms")
    return {
        "summary_path": str(root / arm / "summary.json"),
        "results_path": str(root / arm / "results.jsonl"),
        "accuracy": _accuracy(rows),
        "parse_failures": _parse_failures(rows),
        "effective_keep_rate": _summary_keep_rate(summary, arm=arm),
        "mean_vision_ms": summary.get("mean_dense_vision_ms"),
        "mean_e2e_ms_excluding_score_runtime": e2e,
        "mean_e2e_ms_including_score_runtime": e2e_score,
        "score_mode": summary.get("score_mode"),
        "score_seed": summary.get("score_seed"),
        "codec_score_source": summary.get("codec_score_source"),
        "codec_score_runtime_source": summary.get("codec_score_runtime_source"),
        "codec_sidecar_load_mean_s_per_item": summary.get("codec_sidecar_load_mean_s_per_item"),
        "codec_extract_mean_s_per_item": summary.get("codec_extract_mean_s_per_item"),
    }


def _validate_all(root: Path, arms: dict[str, dict[str, Any]]) -> None:
    marker_commit = _validate_run_marker(root)
    dense_summary = cast(dict[str, Any], arms["dense"]["summary"])
    reference_manifest = _norm_path(EXPECTED_MANIFEST)
    reference_model_name = EXPECTED_MODEL_NAME
    expected_ids = _expected_item_ids()
    expected_n = len(expected_ids)
    if expected_n != 57:
        raise ValueError(f"expected N=57 manifest, got {expected_n} items")

    for arm, arm_data in arms.items():
        summary = cast(dict[str, Any], arm_data["summary"])
        rows = cast(list[dict[str, Any]], arm_data["rows"])
        _validate_common_config(
            summary,
            arm=arm,
            reference_manifest=reference_manifest,
            reference_model_name=reference_model_name,
            expected_n=expected_n,
        )
        _assert_equal(summary.get("git_commit"), marker_commit, f"{arm} git_commit")
        if _item_ids(rows) != expected_ids:
            raise ValueError(f"{arm} ordered item_ids differ from manifest")

    _validate_dense(dense_summary)
    _validate_magnitude(cast(dict[str, Any], arms["magnitude_norm"]["summary"]))
    _validate_codec(cast(dict[str, Any], arms["codec_novel_coded"]["summary"]))
    for seed in SEEDS:
        _validate_random(
            cast(dict[str, Any], arms[f"uniform_random_seed{seed}"]["summary"]), seed=seed
        )

    sparse_keep_rates = {
        arm: _summary_keep_rate(cast(dict[str, Any], arms[arm]["summary"]), arm=arm)
        for arm in SPARSE_ARMS
    }
    keep_values = list(sparse_keep_rates.values())
    if max(keep_values) - min(keep_values) > 1e-9:
        raise ValueError(f"sparse effective keep-rate mismatch: {sparse_keep_rates}")

    if not root.match(f"**/{EXPECTED_ROOT_NAME}"):
        raise ValueError(f"unexpected clean-control root name: {root}")


def analyze(root: Path = DEFAULT_ROOT) -> dict[str, Any]:
    arms = {arm: _load_arm(root, arm) for arm in REQUIRED_ARMS}
    _validate_all(root, arms)

    codec_rows = cast(list[dict[str, Any]], arms["codec_novel_coded"]["rows"])
    codec_correct = int(_accuracy(codec_rows)["successes"])
    random_corrects: dict[str, int] = {}
    paired: dict[str, Any] = {}
    for seed in SEEDS:
        arm = f"uniform_random_seed{seed}"
        random_rows = cast(list[dict[str, Any]], arms[arm]["rows"])
        random_corrects[arm] = int(_accuracy(random_rows)["successes"])
        paired[f"codec_novel_coded_vs_{arm}"] = _paired(codec_rows, random_rows)

    random_counts = list(random_corrects.values())
    random_mean = statistics.mean(random_counts)
    seeds_random_le_codec = [
        arm for arm, count in random_corrects.items() if count <= codec_correct
    ]
    seeds_random_gt_codec_by_ge_3 = [
        arm for arm, count in random_corrects.items() if count - codec_correct >= 3
    ]
    passes_positive_gate = (
        codec_correct >= random_mean
        and len(seeds_random_le_codec) >= 3
        and not seeds_random_gt_codec_by_ge_3
    )
    falsified = random_mean > codec_correct or len(seeds_random_gt_codec_by_ge_3) >= 2
    inconclusive = not passes_positive_gate and not falsified
    if passes_positive_gate:
        interpretation = (
            "Positive gate passes: same-run codec_novel_coded meets or exceeds the "
            "matched four-seed random-control distribution by point estimate. "
            "This remains a bounded operating-point claim, not a broad superiority claim."
        )
    elif falsified:
        interpretation = (
            "Falsified for a positive codec-over-random sentence: random-control "
            "performance exceeds same-run codec_novel_coded under the preregistered gate."
        )
    else:
        interpretation = (
            "Inconclusive: random-control results neither pass the positive gate nor "
            "meet the falsifier. Do not use this as a codec-over-random claim."
        )

    first_sparse = cast(dict[str, Any], arms["magnitude_norm"]["summary"])
    return {
        "schema": "codec_vs_random_multiseed_audit_v1",
        "root": str(root),
        "question": (
            "Does same-run M5 codec_novel_coded at Qwen N=57/8f/layer=2/kr=0.7 "
            "meet or exceed a matched four-seed random-keep control?"
        ),
        "gate": (
            "Positive only if codec correct count is >= the random-seed mean, at "
            "least 3/4 random seeds are <= codec by point estimate, and no random "
            "seed beats codec by >=3 items."
        ),
        "falsification": (
            "Falsified if the random mean exceeds codec, or if at least two random "
            "seeds beat codec by >=3 items."
        ),
        "config": {
            "manifest": str(EXPECTED_MANIFEST),
            "model": EXPECTED_MODEL_NAME,
            "frame_count": EXPECTED_FRAME_COUNT,
            "max_tokens": EXPECTED_MAX_TOKENS,
            "vision_tower_layer": EXPECTED_LAYER,
            "configured_keep_rate": EXPECTED_KEEP_RATE,
            "measured_effective_keep_rate": _summary_keep_rate(first_sparse, arm="magnitude_norm"),
            "seeds": list(SEEDS),
        },
        "arms": {arm: _arm_payload(root, arm, arm_data) for arm, arm_data in arms.items()},
        "paired_comparisons": paired,
        "random_distribution": {
            "correct_counts": random_corrects,
            "mean_correct": random_mean,
            "min_correct": min(random_counts),
            "max_correct": max(random_counts),
            "median_correct": statistics.median(random_counts),
            "mean_rate": random_mean / len(codec_rows),
            "min_rate": min(random_counts) / len(codec_rows),
            "max_rate": max(random_counts) / len(codec_rows),
        },
        "gate_status": {
            "codec_correct": codec_correct,
            "random_mean_correct": random_mean,
            "seeds_random_le_codec": seeds_random_le_codec,
            "n_seeds_random_le_codec": len(seeds_random_le_codec),
            "seeds_random_gt_codec_by_ge_3": seeds_random_gt_codec_by_ge_3,
            "passes_positive_gate": passes_positive_gate,
            "falsified": falsified,
            "inconclusive": inconclusive,
            "interpretation": interpretation,
        },
    }


def _markdown(payload: dict[str, Any]) -> str:
    status = payload["gate_status"]
    lines = [
        "# M5 Qwen kr=0.7 Codec-vs-Random Clean-Control Audit",
        "",
        f"Question: {payload['question']}",
        "",
        f"Gate: {payload['gate']}",
        f"Falsification: {payload['falsification']}",
        "",
        (
            "Denominator: this compares sparse-ranking choices at the same model, "
            "manifest, frame budget, layer, configured keep-rate, and sidecar-backed "
            "codec score path. It is not an end-to-end model speedup claim."
        ),
        "",
        "| arm | accuracy | Wilson 95% CI | effective keep | score source |",
        "| --- | ---: | --- | ---: | --- |",
    ]
    for arm, value in payload["arms"].items():
        acc = value["accuracy"]
        ci = acc["wilson_95_ci"]
        score_source = str(value["score_mode"])
        if value.get("codec_score_source") is not None:
            score_source += f":{value['codec_score_source']}"
        if value.get("score_seed") is not None:
            score_source += f":seed{value['score_seed']}"
        lines.append(
            "| "
            + " | ".join(
                [
                    arm,
                    f"{acc['successes']}/{acc['n']} = {acc['rate']:.3f}",
                    f"[{ci[0]:.3f}, {ci[1]:.3f}]",
                    f"{float(value['effective_keep_rate']):.3f}",
                    score_source,
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "| comparison | codec fixes | codec breaks | McNemar p | choice agreement |",
            "| --- | ---: | ---: | ---: | --- |",
        ]
    )
    for name, comparison in payload["paired_comparisons"].items():
        choice = comparison["choice_agreement"]
        lines.append(
            "| "
            + " | ".join(
                [
                    name,
                    str(comparison["codec_correct_random_wrong"]),
                    str(comparison["codec_wrong_random_correct"]),
                    f"{comparison['mcnemar_exact_p_two_sided']:.4f}",
                    f"{choice['successes']}/{choice['n']} = {choice['rate']:.3f}",
                ]
            )
            + " |"
        )
    random_dist = payload["random_distribution"]
    lines.extend(
        [
            "",
            (
                "Random correct counts: "
                f"{random_dist['correct_counts']} "
                f"(mean {random_dist['mean_correct']:.2f}, "
                f"range {random_dist['min_correct']}--{random_dist['max_correct']})."
            ),
            "",
            f"Gate result: {status['interpretation']}",
            (
                "Status flags: "
                f"passes_positive_gate={status['passes_positive_gate']}, "
                f"falsified={status['falsified']}, "
                f"inconclusive={status['inconclusive']}."
            ),
            "",
            (
                "Paper-safe use: report the exact point estimates and paired tests. "
                "Do not present this audit as broad codec superiority."
            ),
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--out-json", type=Path, default=None)
    parser.add_argument("--out-md", type=Path, default=None)
    args = parser.parse_args()

    payload = analyze(args.root)
    out_json = args.out_json or args.root / "codec_vs_random_multiseed_audit.json"
    out_md = args.out_md or args.root / "codec_vs_random_multiseed_audit.md"
    out_json.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    out_md.write_text(_markdown(payload))
    print(out_json)
    print(out_md)


if __name__ == "__main__":
    main()
