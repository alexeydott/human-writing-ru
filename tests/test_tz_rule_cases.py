#!/usr/bin/env python3
from __future__ import annotations
import importlib.util,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('tz',ROOT/'scripts/check_tz_ru.py')
mod=importlib.util.module_from_spec(spec); assert spec and spec.loader; spec.loader.exec_module(mod)
data=json.loads((ROOT/'evals/tz_rule_cases.json').read_text(encoding='utf-8'))
for case in data['cases']:
    got={f['code'] for f in mod.analyze(case['text'],'generic')['findings']}
    for code in case.get('expect_present',[]): assert code in got,(case['id'],code,got)
    for code in case.get('expect_absent',[]): assert code not in got,(case['id'],code,got)
print('test_tz_rule_cases: OK')
