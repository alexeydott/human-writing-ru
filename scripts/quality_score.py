#!/usr/bin/env python3
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

ROOT=Path(__file__).resolve().parents[1]
PYTHON=sys.executable
ENV={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'}


def run(cmd):
    p=subprocess.run(cmd,cwd=ROOT,text=True,capture_output=True,env=ENV)
    return {'ok':p.returncode==0,'returncode':p.returncode,'stdout':p.stdout[-6000:],'stderr':p.stderr[-6000:]}

criteria=[]
def add(name,weight,ok,evidence):
    criteria.append({'name':name,'weight':weight,'earned':weight if ok else 0,'ok':bool(ok),'evidence':evidence})

# 1. Spec/package hygiene.
v=run([PYTHON,'scripts/validate_skill.py'])
add('agent_skills_spec_and_package_hygiene',14,v['ok'],v)

# 2. Regression suite.
tests=[
 'tests/test_check_prose_ru.py','tests/test_corpus_tools.py','tests/test_benchmark_tools.py','tests/test_ablation_tools.py',
 'tests/test_ablation_v3.py','tests/test_external_heldout_tools.py','tests/test_external_gate_runner.py','tests/test_edit_integrity.py',
 'tests/test_ab_eval_tools.py','tests/test_release_builder.py','tests/test_lite_builder.py','tests/test_validation_mutations.py','tests/test_check_tz_ru.py','tests/test_tz_rule_cases.py','tests/test_humanizer_adaptation.py'
]
tr=[]
with ThreadPoolExecutor(max_workers=min(6,len(tests))) as pool:
    futures={pool.submit(run,[PYTHON,test]):test for test in tests}
    for future in as_completed(futures):
        test=futures[future]
        tr.append({'test':test,**future.result()})
tr.sort(key=lambda x:x['test'])
add('regression_suite',24,all(x['ok'] for x in tr),tr)

# 3. Eval design and declared coverage, including reproducible A/B mechanics.
ed=run([PYTHON,'scripts/validate_eval_design.py'])
ac=run([PYTHON,'scripts/audit_eval_coverage.py','--json'])
coverage_ok=False
try:
    data=json.loads(ac['stdout'])
    coverage_ok=ac['ok'] and all(not d['uncovered_values'] and not d['cases_missing_dimension'] for d in data['dimensions'].values())
except Exception:
    coverage_ok=False
ab_tools_ok=all((ROOT/x).exists() for x in ['scripts/prepare_ab_eval.py','scripts/aggregate_ab_eval.py']) and next(x for x in tr if x['test']=='tests/test_ab_eval_tools.py')['ok']
add('eval_design_and_declared_coverage',16,ed['ok'] and coverage_ok and ab_tools_ok,{'design':ed,'coverage':ac,'ab_tools_ok':ab_tools_ok})

# 4. Methodology v3 safeguards are specified and regression-tested.
try:
    s=json.loads((ROOT/'benchmark/ablation/spec-v3.json').read_text(encoding='utf-8'))
    split=s.get('split',{})
    prose_div=s.get('diversity_gate',{}).get('prose',{})
    method_ok=(
        s.get('schema_version')==3 and 'signal_gate' in s and 'diversity_gate' in s and 'split' in s and 'adjudication' in s
        and float(split['calibration_fraction'])<1 and int(s['signal_gate']['validation_minimum_documents'])>0
        and set(split.get('group_fields',[])) >= {'author_or_group','split_group','source_document_id','independence_group'}
        and set(split.get('source_scoped_group_fields',[])) >= {'source_document_id','independence_group'}
        and 'maximum_source_word_share' in prose_div and 'minimum_known_source_coverage' in prose_div
        and (ROOT/'scripts/ablate_signals_v3.py').exists()
        and next(x for x in tr if x['test']=='tests/test_ablation_v3.py')['ok']
        and next(x for x in tr if x['test']=='tests/test_external_gate_runner.py')['ok']
    )
except Exception as exc:
    method_ok=False; s={'error':str(exc)}
add('ablation_protocol_v3_safeguards',22,method_ok,s)

# 5. Edit-integrity safety.
integrity_ok=(ROOT/'scripts/check_edit_integrity.py').exists() and next(x for x in tr if x['test']=='tests/test_edit_integrity.py')['ok']
tz_ok=(ROOT/'scripts/check_tz_ru.py').exists() and next(x for x in tr if x['test']=='tests/test_check_tz_ru.py')['ok'] and next(x for x in tr if x['test']=='tests/test_tz_rule_cases.py')['ok']
add('edit_integrity_and_tz_safety',10,integrity_ok and tz_ok,{'edit_integrity':'scripts/check_edit_integrity.py','tz_checker':'scripts/check_tz_ru.py','tz_rules':'profiles/tz-rules.ru.json'})

# 6. Frozen reproducibility independent from validate_skill output.
frozen=json.loads((ROOT/'benchmark/external-heldout/FROZEN_INPUT_SHA256.json').read_text(encoding='utf-8'))['sha256']
actual={rel:hashlib.sha256((ROOT/rel).read_bytes()).hexdigest() for rel in frozen}
frozen_ok=all(actual[k]==v for k,v in frozen.items())
add('frozen_policy_reproducibility',6,frozen_ok,{'expected':frozen,'actual':actual})

# 7. Version split and progressive disclosure.
version=(ROOT/'VERSION').read_text(encoding='utf-8').strip()
skill=(ROOT/'SKILL.md').read_text(encoding='utf-8')
doc_ok=(
    version in (ROOT/'README.md').read_text(encoding='utf-8')
    and version in (ROOT/'dist/human-writing-ru-lite.md').read_text(encoding='utf-8')
    and 'policy_version: "1.5.0"' in skill
    and all((ROOT/f'references/{x}.md').exists() for x in ['product-case','portfolio','ai-feature','technical-specification'])
    and (ROOT/'references/product-story.md').stat().st_size < 3000
)
add('documentation_and_progressive_disclosure',4,doc_ok,{'version':version,'product_router_bytes':(ROOT/'references/product-story.md').stat().st_size})

# 8. Independent reference validator if actually available; never award points for absence.
ref=shutil.which('skills-ref')
if ref:
    rr=run([ref,'validate',str(ROOT)])
    add('external_skills_ref_validation',4,rr['ok'],rr)
else:
    add('external_skills_ref_validation',4,False,{'status':'not_available_in_runtime','points_deliberately_not_awarded':True})

score=sum(x['earned'] for x in criteria)
report={
 'schema_version':2,
 'score':score,
 'max_score':100,
 'target':'>90',
 'target_met':score>90,
 'score_scope':'engineering_and_methodological_readiness_only',
 'empirical_threshold_confidence':'not_established_until_external_heldout_v3',
 'generative_superiority_confidence':'not_established_until_real_ab_eval',
 'criteria':criteria,
}
out=ROOT/'quality/QUALITY_SCORE.json'
out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'score':score,'target_met':score>90,'external_skills_ref_available':bool(ref),'empirical_threshold_confidence':report['empirical_threshold_confidence'],'generative_superiority_confidence':report['generative_superiority_confidence']},ensure_ascii=False))
raise SystemExit(0 if score>90 else 1)
