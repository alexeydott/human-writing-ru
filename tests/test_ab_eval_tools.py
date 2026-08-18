#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
PREP=ROOT/'scripts/prepare_ab_eval.py'
AGG=ROOT/'scripts/aggregate_ab_eval.py'

with tempfile.TemporaryDirectory() as td:
    base=Path(td)
    evals=base/'evals.json'
    evals.write_text(json.dumps({
        'skill_name':'human-writing-ru',
        'evaluation_policy':{'runs_per_case_recommended':2,'clean_context_required':True,'previous_skill_id':'test@previous'},
        'evals':[{'id':'case-one','prompt':'Исправь текст','expected_output':'Исправленный текст','assertions':['a','b','c'],'files':[],'dimensions':{}}]
    },ensure_ascii=False),encoding='utf-8')
    workspace=base/'ws'
    p=subprocess.run([sys.executable,str(PREP),'--evals',str(evals),'--workspace',str(workspace),'--arms','current_skill','previous_skill'],cwd=ROOT,text=True,capture_output=True)
    assert p.returncode==0,(p.stdout,p.stderr)
    iteration=workspace/'iteration-1'
    manifest=json.loads((iteration/'run-manifest.json').read_text(encoding='utf-8'))
    assert len(manifest['runs'])==4
    assert manifest['arm_provenance']['previous_skill']['id']=='test@previous'
    assert manifest['source_evals_sha256']
    assert manifest['path_base']=='iteration_dir'
    for run in manifest['runs']:
        (iteration/Path(run['grading_path'])).write_text(json.dumps({'summary':{'pass_rate':1.0 if run['arm']=='current_skill' else 0.5}}),encoding='utf-8')
        (iteration/Path(run['timing_path'])).write_text(json.dumps({'total_tokens':100 if run['arm']=='current_skill' else 80,'duration_ms':1000}),encoding='utf-8')
    p=subprocess.run([sys.executable,str(AGG),'--iteration-dir',str(iteration)],cwd=ROOT,text=True,capture_output=True)
    assert p.returncode==0,(p.stdout,p.stderr)
    report=json.loads((iteration/'benchmark.json').read_text(encoding='utf-8'))
    assert report['planned_runs']==4 and report['completed_runs']==4
    assert report['arms']['current_skill']['pass_rate']['mean']==1.0
    assert report['pass_rate_deltas']['current_minus_previous_skill']==0.5
    assert report['paired_pass_rate_deltas']['current_minus_previous_skill']['complete_pairs'] is True
    assert report['complete'] is True and report['diagnostic_only'] is False
# Duplicate arms are invalid because they would point multiple planned runs at the same files.
with tempfile.TemporaryDirectory() as td:
    base=Path(td); evals=base/'evals.json'
    evals.write_text(json.dumps({'skill_name':'x','evaluation_policy':{'runs_per_case_recommended':1,'previous_skill_id':'test@previous'},'evals':[{'id':'c','prompt':'p','assertions':['a']}]},ensure_ascii=False),encoding='utf-8')
    p=subprocess.run([sys.executable,str(PREP),'--evals',str(evals),'--workspace',str(base/'ws'),'--arms','current_skill','current_skill'],cwd=ROOT,text=True,capture_output=True)
    assert p.returncode!=0 and 'duplicates' in (p.stdout+p.stderr)

# Incomplete diagnostics must not publish an unpaired headline delta.
with tempfile.TemporaryDirectory() as td:
    base=Path(td); evals=base/'evals.json'
    evals.write_text(json.dumps({'skill_name':'x','evaluation_policy':{'runs_per_case_recommended':2,'previous_skill_id':'test@previous'},'evals':[{'id':'c','prompt':'p','assertions':['a']}]},ensure_ascii=False),encoding='utf-8')
    workspace=base/'ws'
    p=subprocess.run([sys.executable,str(PREP),'--evals',str(evals),'--workspace',str(workspace),'--arms','current_skill','previous_skill'],cwd=ROOT,text=True,capture_output=True)
    assert p.returncode==0
    iteration=workspace/'iteration-1'; manifest=json.loads((iteration/'run-manifest.json').read_text(encoding='utf-8'))
    for run in manifest['runs']:
        # Leave previous_skill run-02 missing, concentrating missingness on one arm.
        if run['arm']=='previous_skill' and run['run_index']==2: continue
        (iteration/Path(run['grading_path'])).write_text(json.dumps({'summary':{'pass_rate':1.0 if run['arm']=='current_skill' else 0.0}}),encoding='utf-8')
        (iteration/Path(run['timing_path'])).write_text(json.dumps({'total_tokens':100,'duration_ms':1000}),encoding='utf-8')
    p=subprocess.run([sys.executable,str(AGG),'--iteration-dir',str(iteration),'--allow-incomplete'],cwd=ROOT,text=True,capture_output=True)
    assert p.returncode==0,(p.stdout,p.stderr)
    report=json.loads((iteration/'benchmark.json').read_text(encoding='utf-8'))
    assert report['complete'] is False and report['diagnostic_only'] is True
    assert 'current_minus_previous_skill' not in report['pass_rate_deltas']
    detail=report['paired_pass_rate_deltas']['current_minus_previous_skill']
    assert detail['paired_runs']==1 and detail['planned_pairs']==2 and detail['complete_pairs'] is False

# Non-finite timing values are invalid evidence.
with tempfile.TemporaryDirectory() as td:
    base=Path(td); iteration=base/'iteration-1'; run_dir=iteration/'c'/'current_skill'/'run-01'; run_dir.mkdir(parents=True)
    grade=run_dir/'grading.json'; timing=run_dir/'timing.json'
    grade.write_text(json.dumps({'summary':{'pass_rate':1.0}}),encoding='utf-8')
    timing.write_text(json.dumps({'total_tokens':'NaN','duration_ms':1}),encoding='utf-8')
    manifest={'iteration':1,'arms':['current_skill'],'runs':[{'case_id':'c','arm':'current_skill','run_index':1,'grading_path':str(grade),'timing_path':str(timing)}]}
    (iteration/'run-manifest.json').write_text(json.dumps(manifest),encoding='utf-8')
    p=subprocess.run([sys.executable,str(AGG),'--iteration-dir',str(iteration)],cwd=ROOT,text=True,capture_output=True)
    assert p.returncode!=0 and 'evaluation incomplete' in (p.stdout+p.stderr)



# Referenced eval input files are copied into the iteration with hashes.
with tempfile.TemporaryDirectory() as td:
    base=Path(td); sample=base/'sample.txt'; sample.write_text('Исходный файл для A/B.\n',encoding='utf-8')
    evals=base/'evals.json'
    evals.write_text(json.dumps({'skill_name':'x','evaluation_policy':{'runs_per_case_recommended':1},'evals':[{'id':'with-file','prompt':'p','assertions':['a'],'files':[str(sample)]}]},ensure_ascii=False),encoding='utf-8')
    workspace=base/'ws'
    p=subprocess.run([sys.executable,str(PREP),'--evals',str(evals),'--workspace',str(workspace),'--arms','current_skill'],cwd=ROOT,text=True,capture_output=True)
    assert p.returncode==0,(p.stdout,p.stderr)
    iteration=workspace/'iteration-1'; manifest=json.loads((iteration/'run-manifest.json').read_text(encoding='utf-8'))
    meta=manifest['input_artifacts']['with-file'][0]
    copied=iteration/meta['path']
    assert copied.exists() and copied.read_text(encoding='utf-8')==sample.read_text(encoding='utf-8')
    assert manifest['runs'][0]['input_files']==[meta['path']]

print('test_ab_eval_tools: OK')
