#!/usr/bin/env python3
"""Phase 1.65v2 — richer dense-oracle stability predictor.

This analysis consumes the already-scored 1.65 rows. It does not run the VLM.
The goal is to test whether margin plus simple metadata beats margin alone as
an exploratory predictor of stable rows inside the 1.30 cache-boundary setting.
"""

from __future__ import annotations

import argparse
import json
import math
import random
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np

DEFAULT_INPUT = Path(
    "research/experiments/2026/artifacts/phase1_65_logit_margin_failure_predictor/scored_rows.jsonl"
)
DEFAULT_OUTPUT = Path(
    "research/experiments/2026/artifacts/phase1_65v2_richer_predictor/prediction_summary.json"
)


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open() as handle:
        for line in handle:
            stripped = line.strip()
            if stripped:
                rows.append(json.loads(stripped))
    return rows


def _entropy_from_logprobs(logprobs: dict[str, float]) -> float:
    values = np.array([float(value) for value in logprobs.values()], dtype=np.float64)
    shifted = values - np.max(values)
    probs = np.exp(shifted)
    probs = probs / probs.sum()
    return float(-(probs * np.log(probs + 1e-12)).sum())


def _duration_from_item_id(item_id: str) -> str:
    parts = item_id.split(":")
    return parts[1] if len(parts) >= 3 else "unknown"


def _standardize(train: np.ndarray, test: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    mean = train.mean(axis=0)
    std = train.std(axis=0)
    std[std < 1e-8] = 1.0
    return (train - mean) / std, (test - mean) / std


def _features(rows: list[dict[str, Any]], *, variant: str) -> tuple[np.ndarray, list[str]]:
    if variant == "margin_only":
        names = ["dense_answer_margin"]
    elif variant == "label_free":
        names = [
            "top_second_gap",
            "candidate_entropy",
            "prompt_tokens",
            "q_index_is_2",
            "source_is_cache_invalidated",
            "duration_short",
            "duration_medium",
            "duration_long",
        ]
    elif variant == "oracle":
        names = [
            "dense_answer_margin",
            "answer_letter_logprob",
            "top_second_gap",
            "candidate_entropy",
            "prompt_tokens",
            "q_index_is_2",
            "baseline_correct",
            "source_is_cache_invalidated",
            "duration_short",
            "duration_medium",
            "duration_long",
        ]
    else:
        raise ValueError(f"unknown feature variant {variant!r}")
    matrix: list[list[float]] = []
    for row in rows:
        logprobs = {str(k): float(v) for k, v in row["candidate_logprobs"].items()}
        ranked = sorted(logprobs.values(), reverse=True)
        top_second_gap = ranked[0] - ranked[1] if len(ranked) >= 2 else 0.0
        duration = _duration_from_item_id(str(row["item_id"]))
        source = str(row["source"])
        common = {
            "top_second_gap": float(top_second_gap),
            "candidate_entropy": _entropy_from_logprobs(logprobs),
            "prompt_tokens": float(row.get("prompt_tokens", 0.0)),
            "q_index_is_2": 1.0 if int(row["q_index"]) == 2 else 0.0,
            "source_is_cache_invalidated": 1.0 if "cache-invalidated" in source else 0.0,
            "duration_short": 1.0 if duration == "short" else 0.0,
            "duration_medium": 1.0 if duration == "medium" else 0.0,
            "duration_long": 1.0 if duration == "long" else 0.0,
            "dense_answer_margin": float(row["dense_answer_margin"]),
            "answer_letter_logprob": float(row["answer_letter_logprob"]),
            "baseline_correct": 1.0 if bool(row["baseline_correct"]) else 0.0,
        }
        matrix.append([common[name] for name in names])
    return np.array(matrix, dtype=np.float64), names


def _labels(rows: list[dict[str, Any]]) -> np.ndarray:
    return np.array([0.0 if bool(row["any_drift"]) else 1.0 for row in rows], dtype=np.float64)


def _sigmoid(values: np.ndarray) -> np.ndarray:
    values = np.clip(values, -50.0, 50.0)
    return 1.0 / (1.0 + np.exp(-values))


def _fit_logistic(
    train_x: np.ndarray,
    train_y: np.ndarray,
    *,
    learning_rate: float,
    l2: float,
    steps: int,
) -> np.ndarray:
    x = np.concatenate([np.ones((train_x.shape[0], 1)), train_x], axis=1)
    weights = np.zeros(x.shape[1], dtype=np.float64)
    for _ in range(steps):
        probs = _sigmoid(x @ weights)
        grad = (x.T @ (probs - train_y)) / len(train_y)
        grad[1:] += l2 * weights[1:]
        weights -= learning_rate * grad
    return weights


def _predict(weights: np.ndarray, x: np.ndarray) -> np.ndarray:
    with_bias = np.concatenate([np.ones((x.shape[0], 1)), x], axis=1)
    return _sigmoid(with_bias @ weights)


def _auc(scores: list[float], labels: list[bool]) -> float | None:
    positives = [score for score, label in zip(scores, labels, strict=True) if label]
    negatives = [score for score, label in zip(scores, labels, strict=True) if not label]
    if not positives or not negatives:
        return None
    wins = 0.0
    for positive in positives:
        for negative in negatives:
            if positive > negative:
                wins += 1.0
            elif positive == negative:
                wins += 0.5
    return wins / (len(positives) * len(negatives))


def _safe_filter(
    scores: np.ndarray, labels: np.ndarray, *, precision_floor: float
) -> dict[str, Any]:
    best = {
        "threshold": None,
        "precision_stable": None,
        "coverage": 0.0,
        "n_selected": 0,
        "n_stable_selected": 0,
    }
    for threshold in sorted(set(float(score) for score in scores)):
        selected = scores >= threshold
        n_selected = int(selected.sum())
        if n_selected == 0:
            continue
        n_stable = int(labels[selected].sum())
        precision = n_stable / n_selected
        coverage = n_selected / len(scores)
        if precision >= precision_floor and coverage > float(best["coverage"]):
            best = {
                "threshold": float(threshold),
                "precision_stable": precision,
                "coverage": coverage,
                "n_selected": n_selected,
                "n_stable_selected": n_stable,
            }
    return best


def _eval_threshold(
    scores: np.ndarray, labels: np.ndarray, threshold: float | None
) -> dict[str, Any]:
    if threshold is None:
        return {
            "threshold": None,
            "precision_stable": None,
            "coverage": 0.0,
            "n_selected": 0,
            "n_stable_selected": 0,
            "brier": float(((scores - labels) ** 2).mean()) if len(scores) else None,
        }
    selected = scores >= float(threshold)
    n_selected = int(selected.sum())
    n_stable = int(labels[selected].sum()) if n_selected else 0
    return {
        "threshold": float(threshold),
        "precision_stable": (n_stable / n_selected) if n_selected else None,
        "coverage": (n_selected / len(scores)) if len(scores) else 0.0,
        "n_selected": n_selected,
        "n_stable_selected": n_stable,
        "brier": float(((scores - labels) ** 2).mean()) if len(scores) else None,
    }


def _bootstrap_auc_by_item(
    rows: list[dict[str, Any]],
    scores: np.ndarray,
    labels: np.ndarray,
    *,
    n_resamples: int,
    seed: int,
) -> list[float] | None:
    by_item: dict[str, list[int]] = defaultdict(list)
    for index, row in enumerate(rows):
        by_item[str(row["item_id"])].append(index)
    item_ids = sorted(by_item)
    rng = random.Random(seed)
    aucs: list[float] = []
    for _ in range(n_resamples):
        indices: list[int] = []
        for item_id in rng.choices(item_ids, k=len(item_ids)):
            indices.extend(by_item[item_id])
        auc = _auc(
            [float(scores[index]) for index in indices],
            [bool(labels[index]) for index in indices],
        )
        if auc is not None and math.isfinite(auc):
            aucs.append(auc)
    if not aucs:
        return None
    aucs.sort()
    return [
        aucs[int(0.025 * (len(aucs) - 1))],
        aucs[int(0.975 * (len(aucs) - 1))],
    ]


def _calibration(
    scores: np.ndarray, labels: np.ndarray, *, n_bins: int = 5
) -> list[dict[str, Any]]:
    if len(scores) == 0:
        return []
    order = np.argsort(scores)
    bins: list[dict[str, Any]] = []
    for bin_index in range(n_bins):
        start = round(bin_index * len(order) / n_bins)
        end = round((bin_index + 1) * len(order) / n_bins)
        indices = order[start:end]
        if len(indices) == 0:
            continue
        bins.append(
            {
                "bin": bin_index,
                "n": int(len(indices)),
                "score_min": float(scores[indices].min()),
                "score_max": float(scores[indices].max()),
                "mean_predicted_stable": float(scores[indices].mean()),
                "observed_stable_fraction": float(labels[indices].mean()),
            }
        )
    return bins


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scored-rows", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--n-resamples", type=int, default=2000)
    parser.add_argument("--learning-rate", type=float, default=0.05)
    parser.add_argument("--l2", type=float, default=0.01)
    parser.add_argument("--steps", type=int, default=5000)
    parser.add_argument("--precision-floor", type=float, default=0.85)
    parser.add_argument("--coverage-floor", type=float, default=0.15)
    parser.add_argument("--auc-lower-ci-floor", type=float, default=0.65)
    args = parser.parse_args()

    rows = _load_jsonl(args.scored_rows)
    if not rows:
        raise SystemExit(f"no rows loaded from {args.scored_rows}")
    train_rows = [row for row in rows if row.get("split") == "train"]
    test_rows = [row for row in rows if row.get("split") == "test"]
    if not train_rows or not test_rows:
        raise SystemExit("1.65v2 requires scored rows with train/test split labels")

    train_y = _labels(train_rows)
    test_y = _labels(test_rows)

    variants: dict[str, Any] = {}
    for variant in ("margin_only", "label_free", "oracle"):
        train_x_raw, feature_names = _features(train_rows, variant=variant)
        test_x_raw, _ = _features(test_rows, variant=variant)
        train_x, test_x = _standardize(train_x_raw, test_x_raw)
        weights = _fit_logistic(
            train_x,
            train_y,
            learning_rate=args.learning_rate,
            l2=args.l2,
            steps=args.steps,
        )
        train_scores = _predict(weights, train_x)
        test_scores = _predict(weights, test_x)
        train_auc = _auc(
            [float(score) for score in train_scores],
            [bool(label) for label in train_y],
        )
        test_auc = _auc(
            [float(score) for score in test_scores],
            [bool(label) for label in test_y],
        )
        test_auc_ci95 = _bootstrap_auc_by_item(
            test_rows,
            test_scores,
            test_y,
            n_resamples=args.n_resamples,
            seed=20260429,
        )
        train_filter = _safe_filter(train_scores, train_y, precision_floor=args.precision_floor)
        test_filter = _eval_threshold(test_scores, test_y, train_filter["threshold"])
        coefficients = {
            name: float(weight)
            for name, weight in zip(["intercept", *feature_names], weights, strict=True)
        }
        variants[variant] = {
            "feature_names": feature_names,
            "coefficients": coefficients,
            "train_auc_stability": train_auc,
            "test_auc_stability": test_auc,
            "test_auc_stability_ci95": test_auc_ci95,
            "train_safe_filter": train_filter,
            "test_safe_filter_at_train_threshold": test_filter,
            "test_calibration_bins": _calibration(test_scores, test_y),
            "pass_multifeature_signal": bool(
                test_auc_ci95 is not None and test_auc_ci95[0] >= args.auc_lower_ci_floor
            ),
            "pass_safe_filter": bool(
                test_filter["precision_stable"] is not None
                and float(test_filter["precision_stable"]) >= args.precision_floor
                and float(test_filter["coverage"]) >= args.coverage_floor
            ),
        }

    payload = {
        "phase": "1.65v2",
        "input": args.scored_rows.as_posix(),
        "n_rows": len(rows),
        "n_train_rows": len(train_rows),
        "n_test_rows": len(test_rows),
        "n_train_stable": int(train_y.sum()),
        "n_train_drift": int(len(train_y) - train_y.sum()),
        "n_test_stable": int(test_y.sum()),
        "n_test_drift": int(len(test_y) - test_y.sum()),
        "variants": variants,
        "pass_margin_only_signal": bool(variants["margin_only"]["pass_multifeature_signal"]),
        "pass_label_free_signal": bool(variants["label_free"]["pass_multifeature_signal"]),
        "pass_oracle_signal": bool(variants["oracle"]["pass_multifeature_signal"]),
        "auc_lower_ci_floor": args.auc_lower_ci_floor,
        "safe_filter_precision_floor": args.precision_floor,
        "safe_filter_coverage_floor": args.coverage_floor,
        "interpretation": (
            "The margin_only and oracle variants use answer-aware dense features "
            "and are mechanism evidence only. The label_free variant excludes "
            "gold-answer and dense-correctness features and is the only guard-like "
            "variant."
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(f"[1.65v2] wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
