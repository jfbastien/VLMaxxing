#!/usr/bin/env python3
"""Phase 1.65 — within-1.30 dense logit-margin probe.

The experiment re-scores 1.30 cache-boundary follow-up rows with the dense Qwen
prompt, records the answer-letter logprob margin, and tests on held-out item IDs
whether high dense margin predicts paired stability. This is a predictor scout,
not a deployed runtime guard: it uses the dense reference model as an oracle
feature and intentionally excludes 1.55F-style zero-drift sources so the probe
does not learn experiment identity instead of item stability.
"""

from __future__ import annotations

import argparse
import gc
import importlib.util
import json
import math
import random
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, cast

import mlx.core as mx
import numpy as np
from mlx_vlm import load
from mlx_vlm.generate import generate_step

from codec_through.memory_guard import check_rss_guard

REPO_ROOT = Path(__file__).resolve().parents[1]
QWEN_RUNNER_PATH = REPO_ROOT / "scripts" / "run_phase1_51V.py"
DEFAULT_MODEL_PATH = Path.home() / "models" / "Qwen2.5-VL-7B-Instruct-4bit"
ARTIFACT_ROOT = REPO_ROOT / "research/experiments/2026/artifacts"


@dataclass(frozen=True, slots=True)
class SourceSpec:
    label: str
    path: Path
    frame_count: int
    schema: Literal["phase155", "phase130"]


@dataclass(frozen=True, slots=True)
class PairRow:
    source: str
    source_path: str
    item_id: str
    frame_count: int
    q_index: int
    baseline_choice: str | None
    candidate_choice: str | None
    baseline_correct: bool
    candidate_correct: bool
    choice_drift: bool
    correctness_drift: bool

    @property
    def any_drift(self) -> bool:
        return self.choice_drift or self.correctness_drift


DEFAULT_SOURCES = (
    SourceSpec(
        "1.30AD-cache-reuse-negative",
        ARTIFACT_ROOT / "phase1_30AD_instrumented_w_rerun/paired_queries.jsonl",
        8,
        "phase130",
    ),
    SourceSpec(
        "1.30AC-cache-invalidated-negative",
        ARTIFACT_ROOT / "phase1_30AC_cache_invalidated_followups/paired_queries.jsonl",
        8,
        "phase130",
    ),
)


def _load_qwen_runner() -> Any:
    name = "_phase1_65_qwen_runner"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, QWEN_RUNNER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot build spec for {QWEN_RUNNER_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(name, None)
        raise
    return module


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open() as handle:
        for line in handle:
            stripped = line.strip()
            if stripped:
                rows.append(json.loads(stripped))
    return rows


def _choice(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip().upper()
    return text if len(text) == 1 and text.isalpha() else None


def _load_pair_rows(spec: SourceSpec) -> list[PairRow]:
    raw_rows = _load_jsonl(spec.path)
    rows: list[PairRow] = []
    for raw in raw_rows:
        if spec.schema == "phase155":
            baseline_choice = _choice(raw.get("baseline_choice"))
            candidate_choice = _choice(raw.get("session_choice"))
            baseline_correct = bool(raw.get("baseline_correct"))
            candidate_correct = bool(raw.get("session_correct"))
        else:
            baseline_choice = _choice(raw.get("cold_choice"))
            candidate_choice = _choice(raw.get("streaming_choice"))
            baseline_correct = bool(raw.get("cold_correct"))
            candidate_correct = bool(raw.get("streaming_correct"))
        choice_drift = (
            baseline_choice is not None
            and candidate_choice is not None
            and baseline_choice != candidate_choice
        )
        correctness_drift = baseline_correct != candidate_correct
        rows.append(
            PairRow(
                source=spec.label,
                source_path=spec.path.as_posix(),
                item_id=str(raw["item_id"]),
                frame_count=spec.frame_count,
                q_index=int(raw.get("q_index", -1)),
                baseline_choice=baseline_choice,
                candidate_choice=candidate_choice,
                baseline_correct=baseline_correct,
                candidate_correct=candidate_correct,
                choice_drift=choice_drift,
                correctness_drift=correctness_drift,
            )
        )
    return rows


def _sample_rows(rows: list[PairRow], *, max_rows: int) -> list[PairRow]:
    if max_rows <= 0 or len(rows) <= max_rows:
        return sorted(rows, key=lambda row: (row.source, row.item_id, row.q_index))

    by_source: dict[str, list[PairRow]] = defaultdict(list)
    for row in rows:
        by_source[row.source].append(row)

    selected: list[PairRow] = []
    per_source = max(1, max_rows // len(by_source))
    for source in sorted(by_source):
        source_rows = sorted(
            by_source[source], key=lambda row: (row.any_drift, row.item_id, row.q_index)
        )
        stable = [row for row in source_rows if not row.any_drift]
        drift = [row for row in source_rows if row.any_drift]
        target_drift = min(len(drift), per_source // 2)
        target_stable = min(len(stable), per_source - target_drift)
        selected.extend(drift[:target_drift])
        selected.extend(stable[:target_stable])

    if len(selected) < max_rows:
        used = {(row.source, row.item_id, row.q_index) for row in selected}
        for row in sorted(
            rows, key=lambda row: (row.source, row.any_drift, row.item_id, row.q_index)
        ):
            key = (row.source, row.item_id, row.q_index)
            if key in used:
                continue
            selected.append(row)
            used.add(key)
            if len(selected) == max_rows:
                break
    return sorted(selected, key=lambda row: (row.source, row.item_id, row.q_index))


def _split_rows_by_item(
    rows: list[PairRow], *, test_fraction: float, seed: int
) -> tuple[list[PairRow], list[PairRow]]:
    """Grouped, class-stratified split so the same item never leaks across folds."""
    if not 0.0 < test_fraction < 1.0:
        raise ValueError(f"test_fraction must be in (0, 1), got {test_fraction}")

    by_item: dict[str, list[PairRow]] = defaultdict(list)
    for row in rows:
        by_item[row.item_id].append(row)

    stable_items: list[str] = []
    drift_items: list[str] = []
    for item_id, item_rows in by_item.items():
        if any(row.any_drift for row in item_rows):
            drift_items.append(item_id)
        else:
            stable_items.append(item_id)

    rng = random.Random(seed)
    rng.shuffle(stable_items)
    rng.shuffle(drift_items)

    def _test_subset(items: list[str]) -> set[str]:
        if len(items) <= 1:
            return set(items)
        n_test = max(1, round(len(items) * test_fraction))
        n_test = min(n_test, len(items) - 1)
        return set(items[:n_test])

    test_items = _test_subset(stable_items) | _test_subset(drift_items)
    train_rows: list[PairRow] = []
    test_rows: list[PairRow] = []
    for row in rows:
        if row.item_id in test_items:
            test_rows.append(row)
        else:
            train_rows.append(row)
    return train_rows, test_rows


def _token_ids_for_letter(tokenizer: Any, letter: str) -> list[int]:
    candidates = (letter, f" {letter}")
    token_ids: list[int] = []
    for text in candidates:
        encoded = tokenizer.encode(text, add_special_tokens=False)
        if len(encoded) == 1:
            token_id = int(encoded[0])
            if token_id not in token_ids:
                token_ids.append(token_id)
    if not token_ids:
        raise ValueError(f"no single-token encoding for answer letter {letter!r}")
    return token_ids


def _score_answer_margin(
    *,
    qwen_runner: Any,
    base_runner: Any,
    model: Any,
    processor: Any,
    item_id: str,
    frame_count: int,
    max_tokens: int,
) -> dict[str, Any]:
    del max_tokens  # first-step logprobs only; kept for provenance symmetry.
    item = base_runner._load_items_by_id("videomme", [item_id])[0]
    raw, decode_ms, processor_ms = qwen_runner._prepare_item(
        base_runner,
        processor,
        item,
        frame_count=frame_count,
    )
    features, vision_ms, _prune_info = qwen_runner._compute_qwen_features(model, raw)
    input_ids = mx.array(raw["input_ids"])
    pixel_values = mx.array(raw["pixel_values"])
    mask = mx.array(raw["attention_mask"])
    kwargs = {
        key: mx.array(value)
        for key, value in raw.items()
        if key not in {"input_ids", "pixel_values", "attention_mask"}
    }
    kwargs["cached_image_features"] = features
    step = generate_step(
        input_ids,
        model,
        pixel_values,
        mask,
        max_tokens=1,
        temperature=0.0,
        **kwargs,
    )
    token, logprobs = next(step)
    mx.eval(token, logprobs)
    logprobs_np = np.asarray(logprobs, dtype=np.float64)
    if logprobs_np.ndim != 1:
        raise ValueError(f"expected 1-D logprobs for {item_id}, got {logprobs_np.shape}")

    scores: dict[str, float] = {}
    token_ids_by_letter: dict[str, list[int]] = {}
    for index, _candidate in enumerate(item.candidates):
        letter = chr(ord("A") + index)
        token_ids = _token_ids_for_letter(processor.tokenizer, letter)
        token_ids_by_letter[letter] = token_ids
        scores[letter] = max(float(logprobs_np[token_id]) for token_id in token_ids)
    ranked = sorted(scores.items(), key=lambda pair: pair[1], reverse=True)
    if len(ranked) < 2:
        raise ValueError(f"need at least two answer choices for {item_id}")
    answer_letter = chr(ord("A") + int(item.answer_index))
    margin = ranked[0][1] - ranked[1][1]
    payload = {
        "item_id": item_id,
        "frame_count": frame_count,
        "answer_letter": answer_letter,
        "top_candidate_letter": ranked[0][0],
        "second_candidate_letter": ranked[1][0],
        "top_candidate_logprob": ranked[0][1],
        "second_candidate_logprob": ranked[1][1],
        "answer_letter_logprob": scores[answer_letter],
        "dense_answer_margin": margin,
        "candidate_logprobs": scores,
        "candidate_token_ids": token_ids_by_letter,
        "scoring_timing_ms": {
            "decode": decode_ms,
            "processor": processor_ms,
            "vision": vision_ms,
        },
        "prompt_tokens": int(input_ids.shape[-1]),
    }
    gc.collect()
    mx.clear_cache()
    return payload


def _auc(scores: list[float], labels: list[bool]) -> float | None:
    positives = [score for score, label in zip(scores, labels, strict=True) if label]
    negatives = [score for score, label in zip(scores, labels, strict=True) if not label]
    if not positives or not negatives:
        return None
    wins = 0.0
    total = len(positives) * len(negatives)
    for positive in positives:
        for negative in negatives:
            if positive > negative:
                wins += 1.0
            elif positive == negative:
                wins += 0.5
    return wins / total


def _safe_filter(rows: list[dict[str, Any]]) -> dict[str, Any]:
    thresholds = sorted({float(row["dense_answer_margin"]) for row in rows})
    best: dict[str, Any] = {
        "threshold": None,
        "precision_stable": None,
        "coverage": 0.0,
        "n_selected": 0,
        "n_stable_selected": 0,
    }
    for threshold in thresholds:
        selected = [row for row in rows if float(row["dense_answer_margin"]) >= threshold]
        if not selected:
            continue
        stable_selected = sum(not bool(row["any_drift"]) for row in selected)
        precision = stable_selected / len(selected)
        coverage = len(selected) / len(rows)
        if precision >= 0.95 and coverage > float(best["coverage"]):
            best = {
                "threshold": threshold,
                "precision_stable": precision,
                "coverage": coverage,
                "n_selected": len(selected),
                "n_stable_selected": stable_selected,
            }
    return best


def _evaluate_threshold(rows: list[dict[str, Any]], threshold: float | None) -> dict[str, Any]:
    if threshold is None:
        return {
            "threshold": None,
            "precision_stable": None,
            "coverage": 0.0,
            "n_selected": 0,
            "n_stable_selected": 0,
            "brier_binary": None,
        }
    selected = [row for row in rows if float(row["dense_answer_margin"]) >= threshold]
    stable_selected = sum(not bool(row["any_drift"]) for row in selected)
    precision = stable_selected / len(selected) if selected else None
    coverage = len(selected) / len(rows) if rows else 0.0
    stable_targets = [0.0 if bool(row["any_drift"]) else 1.0 for row in rows]
    predictions = [1.0 if float(row["dense_answer_margin"]) >= threshold else 0.0 for row in rows]
    brier = (
        sum(
            (prediction - target) ** 2
            for prediction, target in zip(predictions, stable_targets, strict=True)
        )
        / len(stable_targets)
        if stable_targets
        else None
    )
    return {
        "threshold": threshold,
        "precision_stable": precision,
        "coverage": coverage,
        "n_selected": len(selected),
        "n_stable_selected": stable_selected,
        "brier_binary": brier,
    }


def _margin_bins(rows: list[dict[str, Any]], *, n_bins: int = 5) -> list[dict[str, Any]]:
    if not rows:
        return []
    ordered = sorted(rows, key=lambda row: float(row["dense_answer_margin"]))
    bins: list[dict[str, Any]] = []
    for bin_index in range(n_bins):
        start = round(bin_index * len(ordered) / n_bins)
        end = round((bin_index + 1) * len(ordered) / n_bins)
        bucket = ordered[start:end]
        if not bucket:
            continue
        stable = sum(not bool(row["any_drift"]) for row in bucket)
        bins.append(
            {
                "bin": bin_index,
                "n": len(bucket),
                "margin_min": float(bucket[0]["dense_answer_margin"]),
                "margin_max": float(bucket[-1]["dense_answer_margin"]),
                "stable_fraction": stable / len(bucket),
                "drift_fraction": 1.0 - stable / len(bucket),
            }
        )
    return bins


def _bootstrap_auc_ci_by_item(
    rows: list[dict[str, Any]], *, n_resamples: int, seed: int
) -> list[float] | None:
    if not rows:
        return None
    by_item: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_item[str(row["item_id"])].append(row)
    item_ids = sorted(by_item)
    rng = random.Random(seed)
    aucs: list[float] = []
    for _ in range(n_resamples):
        sampled_rows: list[dict[str, Any]] = []
        for item_id in rng.choices(item_ids, k=len(item_ids)):
            sampled_rows.extend(by_item[item_id])
        margins = [float(row["dense_answer_margin"]) for row in sampled_rows]
        stable_labels = [not bool(row["any_drift"]) for row in sampled_rows]
        auc = _auc(margins, stable_labels)
        if auc is not None:
            aucs.append(auc)
    if not aucs:
        return None
    aucs.sort()
    return [
        aucs[int(0.025 * (len(aucs) - 1))],
        aucs[int(0.975 * (len(aucs) - 1))],
    ]


def _summarize_split(
    scored_rows: list[dict[str, Any]],
    *,
    train_rows: list[dict[str, Any]],
    test_rows: list[dict[str, Any]],
    n_resamples: int,
    seed: int,
) -> dict[str, Any]:
    margins = [float(row["dense_answer_margin"]) for row in scored_rows]
    drift_rows = [row for row in scored_rows if bool(row["any_drift"])]
    stable_rows = [row for row in scored_rows if not bool(row["any_drift"])]
    train_safe_filter = _safe_filter(train_rows) if train_rows else {}
    threshold = train_safe_filter.get("threshold")
    test_threshold_eval = _evaluate_threshold(test_rows, threshold)
    train_auc = _auc(
        [float(row["dense_answer_margin"]) for row in train_rows],
        [not bool(row["any_drift"]) for row in train_rows],
    )
    test_auc = _auc(
        [float(row["dense_answer_margin"]) for row in test_rows],
        [not bool(row["any_drift"]) for row in test_rows],
    )
    test_auc_ci95 = _bootstrap_auc_ci_by_item(test_rows, n_resamples=n_resamples, seed=seed)
    return {
        "n_scored_rows": len(scored_rows),
        "n_train_rows": len(train_rows),
        "n_test_rows": len(test_rows),
        "n_stable_rows": len(stable_rows),
        "n_drift_rows": len(drift_rows),
        "n_train_stable_rows": sum(not bool(row["any_drift"]) for row in train_rows),
        "n_train_drift_rows": sum(bool(row["any_drift"]) for row in train_rows),
        "n_test_stable_rows": sum(not bool(row["any_drift"]) for row in test_rows),
        "n_test_drift_rows": sum(bool(row["any_drift"]) for row in test_rows),
        "n_choice_drift_rows": sum(bool(row["choice_drift"]) for row in scored_rows),
        "n_correctness_drift_rows": sum(bool(row["correctness_drift"]) for row in scored_rows),
        "source_counts": dict(Counter(str(row["source"]) for row in scored_rows)),
        "train_source_counts": dict(Counter(str(row["source"]) for row in train_rows)),
        "test_source_counts": dict(Counter(str(row["source"]) for row in test_rows)),
        "q_index_counts": {
            str(key): value
            for key, value in Counter(int(row["q_index"]) for row in scored_rows).items()
        },
        "mean_margin_all": float(np.mean(margins)) if margins else None,
        "mean_margin_stable": float(np.mean([row["dense_answer_margin"] for row in stable_rows]))
        if stable_rows
        else None,
        "mean_margin_drift": float(np.mean([row["dense_answer_margin"] for row in drift_rows]))
        if drift_rows
        else None,
        "median_margin_stable": float(
            np.median([row["dense_answer_margin"] for row in stable_rows])
        )
        if stable_rows
        else None,
        "median_margin_drift": float(np.median([row["dense_answer_margin"] for row in drift_rows]))
        if drift_rows
        else None,
        "train_auc_stability_from_dense_margin": train_auc,
        "test_auc_stability_from_dense_margin": test_auc,
        "test_auc_stability_from_dense_margin_ci95": test_auc_ci95,
        "train_safe_filter": train_safe_filter,
        "test_safe_filter_at_train_threshold": test_threshold_eval,
        "test_margin_calibration_bins": _margin_bins(test_rows),
        "pass_class_presence": (
            sum(not bool(row["any_drift"]) for row in train_rows) > 0
            and sum(bool(row["any_drift"]) for row in train_rows) > 0
            and sum(not bool(row["any_drift"]) for row in test_rows) > 0
            and sum(bool(row["any_drift"]) for row in test_rows) > 0
        ),
        "pass_margin_signal": bool(test_auc_ci95 is not None and test_auc_ci95[0] >= 0.60),
        "pass_safe_filter": bool(
            test_threshold_eval.get("precision_stable") is not None
            and float(test_threshold_eval["precision_stable"]) >= 0.90
            and float(test_threshold_eval["coverage"]) >= 0.15
        ),
        "margin_signal_lower_ci_threshold": 0.60,
        "safe_filter_test_precision_threshold": 0.90,
        "safe_filter_test_coverage_threshold": 0.15,
    }


def _parse_source(raw: str) -> SourceSpec:
    parts = raw.split("=", 3)
    if len(parts) != 4:
        raise argparse.ArgumentTypeError(
            "--source must be label=frame_count=schema=path, where schema is phase155 or phase130"
        )
    label, frame_count, schema, path = parts
    if schema not in {"phase155", "phase130"}:
        raise argparse.ArgumentTypeError(f"invalid source schema {schema!r}")
    return SourceSpec(
        label, Path(path), int(frame_count), cast(Literal["phase155", "phase130"], schema)
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-path", type=Path, default=DEFAULT_MODEL_PATH)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--max-rows", type=int, default=0, help="0 scores all loaded rows")
    parser.add_argument("--max-tokens", type=int, default=1)
    parser.add_argument("--rss-guard-mb", type=int, default=0)
    parser.add_argument("--test-fraction", type=float, default=0.20)
    parser.add_argument("--split-seed", type=int, default=20260427)
    parser.add_argument("--n-resamples", type=int, default=2000)
    parser.add_argument(
        "--include-q0",
        action="store_true",
        help=(
            "Include q_index=0 rows. Default is follow-up-only because the "
            "1.65 claim is about cache/reuse stability after Q0."
        ),
    )
    parser.add_argument(
        "--allow-logit-choice-mismatch",
        action="store_true",
        help=(
            "Keep rows where first-step dense logit argmax does not match the "
            "artifact dense choice. Default rejects them because the margin "
            "would not explain the recorded dense decision."
        ),
    )
    parser.add_argument("--source", action="append", type=_parse_source, default=None)
    args = parser.parse_args()

    sources = tuple(args.source) if args.source is not None else DEFAULT_SOURCES
    missing = [spec.path for spec in sources if not spec.path.exists()]
    if missing:
        raise SystemExit(
            f"missing paired source artifacts: {[path.as_posix() for path in missing]}"
        )

    loaded_rows: list[PairRow] = []
    for spec in sources:
        loaded_rows.extend(_load_pair_rows(spec))
    raw_loaded_rows = len(loaded_rows)
    if not args.include_q0:
        loaded_rows = [row for row in loaded_rows if row.q_index > 0]
    selected_rows = _sample_rows(loaded_rows, max_rows=args.max_rows)
    train_pair_rows, test_pair_rows = _split_rows_by_item(
        selected_rows,
        test_fraction=args.test_fraction,
        seed=args.split_seed,
    )
    for label, rows in (("train", train_pair_rows), ("test", test_pair_rows)):
        if not any(row.any_drift for row in rows):
            raise SystemExit(f"{label} split contains no drift examples")
        if not any(not row.any_drift for row in rows):
            raise SystemExit(f"{label} split contains no stable examples")

    qwen_runner = _load_qwen_runner()
    base_runner = qwen_runner._load_runner_module()
    model, processor = cast(tuple[Any, Any], load(str(args.model_path)))
    if getattr(model.config, "model_type", None) != "qwen2_5_vl":
        raise SystemExit(
            f"run_phase1_65_logit_margin_probe.py supports qwen2_5_vl only; got "
            f"{getattr(model.config, 'model_type', None)!r}"
        )
    if args.rss_guard_mb > 0:
        check_rss_guard(args.rss_guard_mb, stage="post_model_load")

    score_cache: dict[tuple[str, int], dict[str, Any]] = {}
    split_by_key: dict[tuple[str, str, int], str] = {
        (row.source, row.item_id, row.q_index): "train" for row in train_pair_rows
    }
    split_by_key.update({(row.source, row.item_id, row.q_index): "test" for row in test_pair_rows})
    scored_rows: list[dict[str, Any]] = []
    rejected_rows: list[dict[str, Any]] = []
    args.output_dir.mkdir(parents=True, exist_ok=True)
    scored_path = args.output_dir / "scored_rows.jsonl"
    rejected_path = args.output_dir / "rejected_rows.jsonl"
    with scored_path.open("w") as handle:
        for row in selected_rows:
            cache_key = (row.item_id, row.frame_count)
            if cache_key not in score_cache:
                score_cache[cache_key] = _score_answer_margin(
                    qwen_runner=qwen_runner,
                    base_runner=base_runner,
                    model=model,
                    processor=processor,
                    item_id=row.item_id,
                    frame_count=row.frame_count,
                    max_tokens=args.max_tokens,
                )
            score_payload = score_cache[cache_key]
            logit_choice_matches_baseline = (
                row.baseline_choice is not None
                and score_payload["top_candidate_letter"] == row.baseline_choice
            )
            merged = {
                "source": row.source,
                "source_path": row.source_path,
                "item_id": row.item_id,
                "frame_count": row.frame_count,
                "q_index": row.q_index,
                "baseline_choice": row.baseline_choice,
                "candidate_choice": row.candidate_choice,
                "baseline_correct": row.baseline_correct,
                "candidate_correct": row.candidate_correct,
                "choice_drift": row.choice_drift,
                "correctness_drift": row.correctness_drift,
                "any_drift": row.any_drift,
                "split": split_by_key[(row.source, row.item_id, row.q_index)],
                "logit_choice_matches_baseline": logit_choice_matches_baseline,
                **score_payload,
            }
            if not math.isfinite(float(merged["dense_answer_margin"])):
                raise ValueError(f"non-finite margin for {row.item_id}")
            if not args.allow_logit_choice_mismatch and not logit_choice_matches_baseline:
                rejected_rows.append(
                    {
                        "source": row.source,
                        "item_id": row.item_id,
                        "q_index": row.q_index,
                        "split": split_by_key[(row.source, row.item_id, row.q_index)],
                        "baseline_choice": row.baseline_choice,
                        "logit_top_candidate_letter": score_payload["top_candidate_letter"],
                        "reason": "dense_logit_argmax_mismatched_artifact_dense_choice",
                    }
                )
                continue
            scored_rows.append(merged)
            handle.write(json.dumps(merged, sort_keys=True) + "\n")
            handle.flush()
            if args.rss_guard_mb > 0:
                check_rss_guard(args.rss_guard_mb, stage=f"post_score:{row.item_id}")

    if rejected_rows:
        with rejected_path.open("w") as handle:
            for row in rejected_rows:
                handle.write(json.dumps(row, sort_keys=True) + "\n")

    train_scored_rows = [row for row in scored_rows if row["split"] == "train"]
    test_scored_rows = [row for row in scored_rows if row["split"] == "test"]
    for label, rows in (("train", train_scored_rows), ("test", test_scored_rows)):
        if not any(row["any_drift"] for row in rows):
            raise SystemExit(f"{label} scored split contains no drift examples")
        if not any(not row["any_drift"] for row in rows):
            raise SystemExit(f"{label} scored split contains no stable examples")
    summary = _summarize_split(
        scored_rows,
        train_rows=train_scored_rows,
        test_rows=test_scored_rows,
        n_resamples=args.n_resamples,
        seed=args.split_seed,
    )
    summary.update(
        {
            "phase": "1.65",
            "model_path": str(args.model_path),
            "sources": [
                {
                    "label": spec.label,
                    "path": spec.path.as_posix(),
                    "frame_count": spec.frame_count,
                    "schema": spec.schema,
                }
                for spec in sources
            ],
            "n_loaded_rows_raw": raw_loaded_rows,
            "n_loaded_rows": len(loaded_rows),
            "n_selected_rows": len(selected_rows),
            "n_rejected_logit_choice_mismatch": len(rejected_rows),
            "max_rows": args.max_rows,
            "rss_guard_mb": args.rss_guard_mb if args.rss_guard_mb > 0 else None,
            "n_unique_scored_prompts": len(score_cache),
            "include_q0": args.include_q0,
            "allow_logit_choice_mismatch": args.allow_logit_choice_mismatch,
            "test_fraction": args.test_fraction,
            "split_seed": args.split_seed,
            "n_resamples": args.n_resamples,
            "scored_rows_jsonl": scored_path.as_posix(),
            "rejected_rows_jsonl": rejected_path.as_posix() if rejected_rows else None,
            "interpretation_scope": (
                "Within-1.30 predictor scout using dense-reference answer-letter "
                "logprob margin. It is not a deployed guard because it requires a "
                "dense pass; it scores follow-up rows only and tests whether the "
                "1.30 cache-boundary drift concentrates on intrinsically uncertain "
                "items after excluding rows where the dense logit argmax does not "
                "match the recorded dense answer."
            ),
        }
    )
    summary_path = args.output_dir / "prediction_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(f"[1.65] wrote {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
