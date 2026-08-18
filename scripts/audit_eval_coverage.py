#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description='Показать покрытие eval-набора по измерениям')
    parser.add_argument('--evals', default=str(ROOT/'evals/evals.json'))
    parser.add_argument('--matrix', default=str(ROOT/'evals/coverage_matrix.json'))
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args()

    eval_data=json.loads(Path(args.evals).read_text(encoding='utf-8'))
    matrix=json.loads(Path(args.matrix).read_text(encoding='utf-8'))
    counters=defaultdict(Counter)
    missing=defaultdict(list)
    cases=eval_data.get('evals',[])

    for case in cases:
        dims=case.get('dimensions',{})
        for dim, allowed in matrix['dimensions'].items():
            value=dims.get(dim)
            if value is None:
                missing[dim].append(case.get('id','?'))
            else:
                counters[dim][str(value)] += 1

    report={'cases':len(cases),'dimensions':{}}
    for dim, allowed in matrix['dimensions'].items():
        report['dimensions'][dim]={
            'counts':dict(counters[dim]),
            'uncovered_values':[value for value in allowed if counters[dim][value]==0],
            'cases_missing_dimension':missing[dim],
        }

    if args.json:
        print(json.dumps(report,ensure_ascii=False,indent=2))
    else:
        print(f"cases: {len(cases)}")
        for dim, info in report['dimensions'].items():
            print(f"\n[{dim}]")
            print('counts:', ', '.join(f'{k}={v}' for k,v in info['counts'].items()) or '—')
            print('uncovered:', ', '.join(info['uncovered_values']) or '—')
            print('missing in:', ', '.join(info['cases_missing_dimension']) or '—')
    return 0

if __name__=='__main__':
    raise SystemExit(main())
