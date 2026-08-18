#!/usr/bin/env python3
from __future__ import annotations
import argparse,csv,json,subprocess,sys
from collections import Counter
from pathlib import Path

def parse_version(value:str):
    if '=' not in value: raise argparse.ArgumentTypeError('--version must be NAME=SKILL_ROOT')
    name,path=value.split('=',1); return name,Path(path)

def normalize(result:dict):
    findings=result.get('findings',[])
    words=result.get('features',{}).get('words',result.get('words',0))
    return words,findings

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--manifest',type=Path,required=True)
    ap.add_argument('--version',action='append',type=parse_version,required=True)
    ap.add_argument('--output',type=Path,required=True)
    args=ap.parse_args(); rows=list(csv.DictReader(args.manifest.open(encoding='utf-8'))); base=args.manifest.parent
    report={'schema_version':1,'manifest':str(args.manifest),'versions':{}}
    for name,root in args.version:
        checker=root/'scripts/check_prose_ru.py'
        if not checker.exists(): raise SystemExit(f'Missing checker for {name}: {checker}')
        total_words=0; findings=[]; docs_with=0; per_doc=[]
        for row in rows:
            path=base/row['path']; mode=row.get('mode') or 'prose'
            p=subprocess.run([sys.executable,str(checker),'--json','--mode',mode,str(path)],text=True,capture_output=True)
            if p.returncode: raise SystemExit(f'{name} failed on {path}: {p.stderr}')
            result=json.loads(p.stdout); words,items=normalize(result); total_words+=words
            if items: docs_with+=1
            findings.extend(items)
            per_doc.append({'path':row['path'],'words':words,'findings':len(items),'codes':[x.get('code') for x in items]})
        levels=Counter(x.get('level','unknown') for x in findings); codes=Counter(x.get('code','unknown') for x in findings)
        report['versions'][name]={
            'documents':len(rows),'words':total_words,'findings':len(findings),'documents_with_findings':docs_with,
            'findings_per_1000_words':round(len(findings)*1000/total_words,3) if total_words else 0,
            'levels':dict(levels),'codes':dict(codes),'documents_detail':per_doc
        }
    args.output.parent.mkdir(parents=True,exist_ok=True); args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8'); print(args.output)
if __name__=='__main__': main()
