#!/usr/bin/env python3
"""Извлекает редакторские признаки из локальной корпусной выборки.

Поддерживает два режима:
1) каталог/файл + --label;
2) CSV-манифест с колонкой path и произвольными метаданными.

Скрипт не скачивает корпуса и не интерпретирует признаки как норму.
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_prose_ru as cp

TEXT_SUFFIXES = {".txt", ".md"}


def read_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except (UnicodeError, OSError):
        return None


def feature_row(path: Path, metadata: dict[str, str], include_quotes: bool) -> dict:
    text = read_text(path)
    if text is None:
        return {}
    features = cp.public_features(cp.compute_features(text, include_quotes))
    return {**metadata, "path": str(path), **features}


def from_manifest(manifest: Path, include_quotes: bool) -> list[dict]:
    rows: list[dict] = []
    with manifest.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames or "path" not in reader.fieldnames:
            raise SystemExit("Манифест должен содержать колонку path")
        for item in reader:
            raw_path = (item.get("path") or "").strip()
            if not raw_path:
                continue
            path = Path(raw_path)
            if not path.is_absolute():
                path = (manifest.parent / path).resolve()
            metadata = {key: value for key, value in item.items() if key != "path" and value is not None}
            row = feature_row(path, metadata, include_quotes)
            if row:
                rows.append(row)
    return rows


def from_input(root: Path, label: str, include_quotes: bool) -> list[dict]:
    if root.is_file():
        files = [root]
    else:
        files = sorted(path for path in root.rglob("*") if path.is_file() and path.suffix.lower() in TEXT_SUFFIXES)
    rows = []
    for path in files:
        row = feature_row(path, {"label": label}, include_quotes)
        if row:
            rows.append(row)
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description="Извлечь стилевые признаки из локальной корпусной выборки")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--input", help="каталог с .txt/.md или один файл")
    source.add_argument("--manifest", help="CSV с колонкой path и метаданными")
    parser.add_argument("--output", required=True)
    parser.add_argument("--label", help="метка для режима --input")
    parser.add_argument("--include-quotes", action="store_true")
    args = parser.parse_args()

    if args.input:
        if not args.label:
            raise SystemExit("Для --input требуется --label")
        rows = from_input(Path(args.input), args.label, args.include_quotes)
    else:
        rows = from_manifest(Path(args.manifest), args.include_quotes)

    if not rows:
        raise SystemExit("Нет читаемых текстов")

    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    print(f"files={len(rows)} output={output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
