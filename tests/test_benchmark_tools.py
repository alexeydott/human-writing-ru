#!/usr/bin/env python3
from __future__ import annotations
import csv,json,subprocess,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PREP=ROOT/'scripts/prepare_benchmark.py'
RUN=ROOT/'scripts/benchmark_checkers.py'

with tempfile.TemporaryDirectory() as tmp:
    base=Path(tmp)
    rucola=base/'rucola.csv'
    rucola.write_text(
        'id,sentence,acceptable,error_type,detailed_source\n'
        '1,"Москва — столица России.",1,0,test\n'
        '2,"Этим летом не никуда ездили.",0,Syntax,test\n',encoding='utf-8')
    ria=base/'ria.jsonl'
    ria.write_text(json.dumps({'text':'<p>Причина проста: сервер ответил вовремя.</p>','title':'t'},ensure_ascii=False)+'\n',encoding='utf-8')
    prepared=base/'prepared'
    p=subprocess.run([sys.executable,str(PREP),'--rucola-csv',str(rucola),'--ria-jsonl',str(ria),'--rucola-accepted','1','--rucola-unacceptable','1','--ria-limit','1','--output-dir',str(prepared)],text=True,capture_output=True)
    assert p.returncode==0,p.stderr
    rows=list(csv.DictReader((prepared/'manifest.csv').open(encoding='utf-8')))
    assert len(rows)==3,rows
    out=base/'results.json'
    p=subprocess.run([sys.executable,str(RUN),'--manifest',str(prepared/'manifest.csv'),'--version',f'current={ROOT}','--output',str(out)],text=True,capture_output=True)
    assert p.returncode==0,p.stderr
    data=json.loads(out.read_text(encoding='utf-8'))
    assert data['versions']['current']['documents']==3
    assert data['versions']['current']['words']>0
print('OK')
