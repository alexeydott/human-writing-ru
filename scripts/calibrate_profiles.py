#!/usr/bin/env python3
"""Строит распределения признаков по размеченной локальной выборке.

Результат — диагностический отчёт, а не готовая языковая норма. Квантили нельзя
автоматически копировать в активный профиль без eval-проверки ложных срабатываний.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
from collections import defaultdict
from pathlib import Path

METRICS = (
    "sentence_mean_words", "sentence_cv", "sentence_p90_words", "sentence_p95_words",
    "sentence_max_words", "one_sentence_paragraph_ratio", "dash_per_1000", "colon_per_1000",
    "road_per_1000", "hype_per_1000", "jargon_per_1000", "nominal_per_1000",
    "bureau_per_1000", "pivot_per_1000", "filler_per_1000", "ellipsis_per_1000",
)


def percentile(values: list[float], quantile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    k = (len(ordered) - 1) * quantile
    lo, hi = math.floor(k), math.ceil(k)
    if lo == hi:
        return ordered[lo]
    return ordered[lo] + (ordered[hi] - ordered[lo]) * (k - lo)


def group_key(row: dict[str, str], columns: list[str]) -> str:
    return " | ".join(f"{column}={row.get(column, '')}" for column in columns)


def main() -> int:
    parser = argparse.ArgumentParser(description="Построить распределения редакторских признаков")
    parser.add_argument("csv")
    parser.add_argument("--output", required=True)
    parser.add_argument("--group-by", default="label", help="колонки через запятую, например channel,target_register")
    parser.add_argument("--min-docs", type=int, default=20)
    parser.add_argument("--min-words-per-doc", type=int, default=0, help="исключить слишком короткие документы из калибровки")
    args = parser.parse_args()

    group_columns = [column.strip() for column in args.group_by.split(",") if column.strip()]
    groups = defaultdict(lambda: defaultdict(list))
    counts = defaultdict(int)
    words_total = defaultdict(int)
    excluded_short = defaultdict(int)

    with open(args.csv, encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise SystemExit("Пустой CSV")
        missing = [column for column in group_columns if column not in reader.fieldnames]
        if missing:
            raise SystemExit(f"Нет колонок для группировки: {', '.join(missing)}")
        for row in reader:
            key = group_key(row, group_columns)
            try:
                words = int(float(row.get("words", 0) or 0))
            except ValueError:
                words = 0
            if words < args.min_words_per_doc:
                excluded_short[key] += 1
                continue
            counts[key] += 1
            words_total[key] += words
            for metric in METRICS:
                try:
                    groups[key][metric].append(float(row[metric]))
                except (ValueError, KeyError, TypeError):
                    pass

    output = {
        "schema_version": 2,
        "status": "corpus_distribution_candidate_needs_validation",
        "group_by": group_columns,
        "min_docs": args.min_docs,
        "min_words_per_doc": args.min_words_per_doc,
        "warning": (
            "Квантили описывают конкретную выборку, а не норму русского языка. "
            "Не переносить их автоматически в активный профиль; сначала проверить "
            "false positives, отдельные классы ошибок и A/B evals."
        ),
        "groups": {},
    }

    for key, metrics in groups.items():
        output["groups"][key] = {
            "documents": counts[key],
            "words_total": words_total[key],
            "excluded_short_documents": excluded_short[key],
            "sufficient_for_candidate": counts[key] >= args.min_docs,
            "metrics": {
                metric: {
                    "p10": round(percentile(values, 0.10), 4),
                    "p25": round(percentile(values, 0.25), 4),
                    "p50": round(percentile(values, 0.50), 4),
                    "p75": round(percentile(values, 0.75), 4),
                    "p90": round(percentile(values, 0.90), 4),
                    "p95": round(percentile(values, 0.95), 4),
                }
                for metric, values in metrics.items()
            },
        }

    Path(args.output).write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"groups={len(output['groups'])} output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
