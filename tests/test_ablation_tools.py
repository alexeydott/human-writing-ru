#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ABLATE = ROOT / "scripts/ablate_signals.py"
CHECK = ROOT / "scripts/check_prose_ru.py"
SPEC = json.loads((ROOT / "benchmark/ablation/spec.json").read_text(encoding="utf-8"))
PROFILE = json.loads((ROOT / "profiles/editorial-baseline.json").read_text(encoding="utf-8"))["profiles"]

EXPECTED_13 = {
    "prose": {"road_per_1000_warn": 10, "sentence_cv_min_info": 0.32, "long_sentence_words_info": 42, "one_sentence_paragraph_ratio_info": 0.70, "jargon_per_1000_info": 12},
    "oral": {"road_per_1000_warn": 10, "sentence_cv_min_info": 0.28, "long_sentence_words_info": 32, "one_sentence_paragraph_ratio_info": 0.75, "jargon_per_1000_info": 10},
    "product": {"road_per_1000_warn": 10, "sentence_cv_min_info": 0.30, "long_sentence_words_info": 46, "one_sentence_paragraph_ratio_info": 0.70, "jargon_per_1000_info": 18},
    "technical": {"road_per_1000_warn": 15, "sentence_cv_min_info": 0.25, "long_sentence_words_info": 55, "one_sentence_paragraph_ratio_info": 0.80, "jargon_per_1000_info": 28},
    "official": {"road_per_1000_warn": 18, "sentence_cv_min_info": 0.22, "long_sentence_words_info": 60, "one_sentence_paragraph_ratio_info": 0.85, "jargon_per_1000_info": 32},
}

# This release intentionally does not move the five active thresholds without the freeze gate.
for mode, expected in EXPECTED_13.items():
    for key, value in expected.items():
        assert float(PROFILE[mode][key]) == float(value), (mode, key, PROFILE[mode][key], value)

# Each synthetic positive control must still trigger its intended signal in prose mode.
controls = {
    "road-sign-density": "road.txt",
    "sentence-uniformity": "uniform.txt",
    "long-sentence": "long.txt",
    "one-sentence-paragraphs": "one-paragraph.txt",
    "context-jargon-density": "jargon.txt",
}
for code, filename in controls.items():
    p = subprocess.run(
        [sys.executable, str(CHECK), "--json", "--mode", "prose", str(ROOT / "benchmark/ablation/controls" / filename)],
        capture_output=True, text=True, check=True,
    )
    data = json.loads(p.stdout)
    assert code in {item["code"] for item in data["findings"]}, (code, data["findings"])

# Runner smoke test with two independent small documents.
with tempfile.TemporaryDirectory() as td:
    td = Path(td)
    a = td / "a.txt"
    b = td / "b.txt"
    a.write_text("Команда проверила журнал. Ошибок не нашли. Результат записали в отчёт. " * 8, encoding="utf-8")
    b.write_text("Пользователь открыл файл. Система проверила поля. Оператор подтвердил результат. " * 8, encoding="utf-8")
    manifest = td / "manifest.csv"
    with manifest.open("w", encoding="utf-8", newline="") as h:
        w = csv.DictWriter(h, fieldnames=["id", "profile", "path", "calibration_eligible", "lexical_only"])
        w.writeheader()
        w.writerow({"id":"a","profile":"prose","path":str(a),"calibration_eligible":"1","lexical_only":"0"})
        w.writerow({"id":"b","profile":"prose","path":str(b),"calibration_eligible":"1","lexical_only":"0"})
    out = td / "out.json"
    subprocess.run([sys.executable, str(ABLATE), "--manifest", str(manifest), "--output", str(out)], check=True, capture_output=True, text=True)
    result = json.loads(out.read_text(encoding="utf-8"))
    assert set(result["signals"]) == set(SPEC["signals"])
    for signal, sdata in result["signals"].items():
        pdata = sdata["profiles"]["prose"]
        direction = SPEC["signals"][signal]["direction"]
        if direction == "high":
            assert pdata["candidate_threshold"] >= pdata["old_threshold"]
        else:
            assert pdata["candidate_threshold"] <= pdata["old_threshold"]
        assert pdata["positive_control"]["off"] is False

print("OK")
