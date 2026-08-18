#!/usr/bin/env python3
from __future__ import annotations
import json
from collections import Counter
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
errors=[]; warnings=[]

def load(rel): return json.loads((ROOT/rel).read_text(encoding='utf-8'))

evals=load('evals/evals.json')
matrix=load('evals/coverage_matrix.json')['dimensions']
cases=evals.get('evals',[])
ids=[c.get('id') for c in cases]
if len(ids)!=len(set(ids)): errors.append('duplicate eval ids')
if len(cases)<24: errors.append(f'generative eval suite too small: {len(cases)} < 24')

for c in cases:
    cid=c.get('id','?')
    if not c.get('prompt'): errors.append(f'{cid}: missing prompt')
    if not c.get('expected_output'): errors.append(f'{cid}: missing expected_output')
    assertions=c.get('assertions',[])
    if len(assertions)<3: errors.append(f'{cid}: fewer than 3 assertions')
    dims=c.get('dimensions',{})
    for key, allowed in matrix.items():
        if key not in dims: errors.append(f'{cid}: missing dimension {key}')
        elif dims[key] not in allowed: errors.append(f'{cid}: invalid {key}={dims[key]!r}')
    for rel in c.get('files',[]):
        if not (ROOT/rel).exists(): errors.append(f'{cid}: missing input file {rel}')

# Coverage: every declared value should have at least one test by this stage.
for dim, allowed in matrix.items():
    counts=Counter(str(c.get('dimensions',{}).get(dim)) for c in cases)
    missing=[x for x in allowed if counts[x]==0]
    if missing: warnings.append(f'{dim}: uncovered values {missing}')

train=load('evals/train_queries.json'); val=load('evals/validation_queries.json'); allq=load('evals/eval_queries.json')
train_q={x['query'] for x in train}; val_q={x['query'] for x in val}; all_q={x['query'] for x in allq}
if train_q & val_q: errors.append('trigger train/validation overlap')
if train_q | val_q != all_q: errors.append('eval_queries != train union validation')
for name, items in [('train',train),('validation',val)]:
    positives=sum(bool(x['should_trigger']) for x in items)
    negatives=len(items)-positives
    if not positives or not negatives: errors.append(f'{name} trigger split lacks positive or negative cases')

policy=evals.get('evaluation_policy',{})
if policy.get('runs_per_case_recommended',0)<3: errors.append('runs_per_case_recommended < 3')
if not policy.get('clean_context_required'): errors.append('clean_context_required must be true')
compare_against=str(policy.get('compare_against','')).lower()
if 'previous' in compare_against:
    previous_skill_id=str(policy.get('previous_skill_id','')).strip()
    if not previous_skill_id:
        errors.append('evaluation_policy.previous_skill_id required when compare_against includes previous skill')
    elif previous_skill_id == f"human-writing-ru@{(ROOT/'VERSION').read_text(encoding='utf-8').strip()}":
        errors.append('evaluation_policy.previous_skill_id must identify a different package version')
if not (ROOT/'evals/AB_EVAL_PROTOCOL.md').exists(): errors.append('AB_EVAL_PROTOCOL.md missing')
if not (ROOT/'evals/judge_schema.json').exists(): errors.append('judge_schema.json missing')
for rel in ['scripts/prepare_ab_eval.py','scripts/aggregate_ab_eval.py','tests/test_ab_eval_tools.py']:
    if not (ROOT/rel).exists(): errors.append(f'{rel} missing')

# Validate the package's actual judge-result template contract. It is a template object, not JSON Schema.
try:
    judge=load('evals/judge_schema.json')
    if not isinstance(judge,dict):
        errors.append('judge_schema.json must be an object')
    else:
        for key in ('schema_version','case_id','arm_a','arm_b','assertion_results','scores','preference','reason'):
            if key not in judge: errors.append(f'judge_schema.json missing {key}')
        if not isinstance(judge.get('assertion_results'),list): errors.append('judge_schema.json assertion_results must be a list template')
        if not isinstance(judge.get('scores'),dict) or not judge.get('scores'): errors.append('judge_schema.json scores must be a non-empty object')
except Exception as exc:
    errors.append(f'judge_schema.json unreadable: {exc}')

print(f'cases={len(cases)} errors={len(errors)} warnings={len(warnings)}')
for x in errors: print('ERROR:',x)
for x in warnings: print('WARN:',x)
raise SystemExit(1 if errors else 0)
