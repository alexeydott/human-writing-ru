#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXTRACT = ROOT / "scripts/extract_corpus_features.py"
CALIBRATE = ROOT / "scripts/calibrate_profiles.py"

with tempfile.TemporaryDirectory() as temp:
    base = Path(temp)
    texts = base / "texts"
    texts.mkdir()
    (texts / "a.txt").write_text("Команда проверила отчёт. Результат оказался понятным.", encoding="utf-8")
    (texts / "b.txt").write_text("Документ подготовили позже — после проверки данных. Ошибку исправили.", encoding="utf-8")
    manifest = base / "manifest.csv"
    manifest.write_text(
        "path,channel,target_register,corpus,license_note\n"
        "texts/a.txt,article,neutral,test,own\n"
        "texts/b.txt,technical,professional,test,own\n",
        encoding="utf-8",
    )
    features = base / "features.csv"
    p = subprocess.run(
        [sys.executable, str(EXTRACT), "--manifest", str(manifest), "--output", str(features)],
        text=True,
        capture_output=True,
    )
    assert p.returncode == 0, p.stderr
    rows = list(csv.DictReader(features.open(encoding="utf-8")))
    assert len(rows) == 2
    assert {row["channel"] for row in rows} == {"article", "technical"}
    assert all("sentence_cv" in row for row in rows)

    distribution = base / "distribution.json"
    p = subprocess.run(
        [
            sys.executable,
            str(CALIBRATE),
            str(features),
            "--group-by",
            "channel,target_register",
            "--min-docs",
            "1",
            "--output",
            str(distribution),
        ],
        text=True,
        capture_output=True,
    )
    assert p.returncode == 0, p.stderr
    data = json.loads(distribution.read_text(encoding="utf-8"))
    assert len(data["groups"]) == 2
    assert data["status"] == "corpus_distribution_candidate_needs_validation"

print("OK")
