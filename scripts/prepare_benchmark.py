#!/usr/bin/env python3
from __future__ import annotations
import argparse,csv,html,json,re
from pathlib import Path

TAG_RE=re.compile(r'<[^>]+>')

def clean_html(value:str)->str:
    value=html.unescape(value)
    value=TAG_RE.sub(' ',value)
    value=re.sub(r'\\"','"',value)
    value=re.sub(r'\s+',' ',value).strip()
    return value

def add_rucola(path:Path,out:Path,rows:list,accepted:int,unaccepted:int):
    ok=[]; bad=[]
    with path.open(encoding='utf-8',newline='') as f:
        for row in csv.DictReader(f):
            (ok if row.get('acceptable')=='1' else bad).append(row['sentence'])
    for label,seq,limit in [('acceptable',ok,accepted),('unacceptable',bad,unaccepted)]:
        if not seq or limit<=0: continue
        text='\n'.join(seq[:limit])
        fn=f'rucola_{label}.txt'; (out/fn).write_text(text,encoding='utf-8')
        rows.append({'path':fn,'mode':'prose','channel':'diagnostic','origin':'mixed','corpus':'RuCoLA','expected':label,'license_note':'Apache-2.0'})

def add_ria(path:Path,out:Path,rows:list,limit:int):
    count=0
    for raw in path.open(encoding='utf-8'):
        if count>=limit: break
        raw=raw.strip()
        if not raw: continue
        obj=json.loads(raw)
        text=clean_html(obj.get('text',''))
        if not text: continue
        count+=1; fn=f'ria_{count:03d}.txt'; (out/fn).write_text(text,encoding='utf-8')
        rows.append({'path':fn,'mode':'prose','channel':'media','origin':'native_original','corpus':'RIA','expected':'published','license_note':'CC BY-ND-NC; do not redistribute prepared text in Skill release'})

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--rucola-csv',type=Path)
    ap.add_argument('--ria-jsonl',type=Path)
    ap.add_argument('--rucola-accepted',type=int,default=100)
    ap.add_argument('--rucola-unacceptable',type=int,default=100)
    ap.add_argument('--ria-limit',type=int,default=50)
    ap.add_argument('--output-dir',type=Path,required=True)
    args=ap.parse_args(); out=args.output_dir; out.mkdir(parents=True,exist_ok=True); rows=[]
    if args.rucola_csv: add_rucola(args.rucola_csv,out,rows,args.rucola_accepted,args.rucola_unacceptable)
    if args.ria_jsonl: add_ria(args.ria_jsonl,out,rows,args.ria_limit)
    if not rows: raise SystemExit('No supported input supplied. Use --rucola-csv and/or --ria-jsonl.')
    fields=['path','mode','channel','origin','corpus','expected','license_note']
    with (out/'manifest.csv').open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)
    print(out/'manifest.csv')
if __name__=='__main__': main()
