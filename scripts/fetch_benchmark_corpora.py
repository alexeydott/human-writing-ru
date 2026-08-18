#!/usr/bin/env python3
from __future__ import annotations
import argparse,urllib.request
from pathlib import Path
SOURCES={
 'rucola':('https://raw.githubusercontent.com/RussianNLP/RuCoLA/main/data/in_domain_train.csv','rucola_in_domain_train.csv','permissive'),
 'ria20':('https://raw.githubusercontent.com/RossiyaSegodnya/ria_news_dataset/master/ria_20.json','ria_20.json','restricted'),
}
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('sources',nargs='+',choices=sorted(SOURCES)); ap.add_argument('--output-dir',type=Path,required=True); ap.add_argument('--allow-restricted',action='store_true'); args=ap.parse_args(); args.output_dir.mkdir(parents=True,exist_ok=True)
    for key in args.sources:
        url,name,policy=SOURCES[key]
        if policy=='restricted' and not args.allow_restricted: raise SystemExit(f'{key}: source has redistribution/use restrictions; re-run with --allow-restricted only after reviewing upstream terms.')
        dst=args.output_dir/name; urllib.request.urlretrieve(url,dst); print(dst)
if __name__=='__main__': main()
