#!/usr/bin/env python3
from __future__ import annotations
import os
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
ENV={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'}

def copy_root(base:Path,name='human-writing-ru')->Path:
    dst=base/name
    # Agent/dev catalogs hold third-party skill templates and Windows junctions created by
    # skill installers; neither belongs to the validation surface or survives copytree.
    skip={'__pycache__','.git','node_modules','.agents','.ai-factory','.claude','.codex','.opencode','.qwen','.venv'}
    shutil.copytree(ROOT,dst,ignore=lambda d,n:{x for x in n if x in skip or x.endswith('.pyc')})
    return dst

def validate(dst:Path):
    return subprocess.run([sys.executable,str(dst/'scripts/validate_skill.py')],cwd=dst,text=True,capture_output=True,env=ENV)

def assert_fails(mutator,name='human-writing-ru',contains:str|None=None):
    with tempfile.TemporaryDirectory() as td:
        dst=copy_root(Path(td),name)
        mutator(dst)
        p=validate(dst)
        assert p.returncode!=0, f'mutation unexpectedly passed: {mutator.__name__}'
        if contains: assert contains in p.stdout+p.stderr,(contains,p.stdout,p.stderr)

def main()->None:
    assert_fails(lambda d: None,name='wrong-skill-directory',contains='skill name must match parent directory')

    def bad_version(d:Path):
        p=d/'SKILL.md'; t=p.read_text(encoding='utf-8'); current=(d/'VERSION').read_text(encoding='utf-8').strip(); t=t.replace(f'version: "{current}"','version: "9.9.9"',1); p.write_text(t,encoding='utf-8')
    assert_fails(bad_version,contains='metadata.version != VERSION')

    def escaped_newline(d:Path):
        p=d/'references/editing.md'; p.write_text(p.read_text(encoding='utf-8')+'\\n\\n## broken\\n',encoding='utf-8')
    assert_fails(escaped_newline,contains='literal escaped newline')

    def mutate_frozen(d:Path):
        p=d/'profiles/editorial-baseline.json'; p.write_text(p.read_text(encoding='utf-8')+'\n',encoding='utf-8')
    assert_fails(mutate_frozen,contains='frozen input hash mismatch')

    def make_second_technical_source_unverified(d:Path):
        p=d/'benchmark/external-heldout/SOURCE_REGISTRY.json'
        data=json.loads(p.read_text(encoding='utf-8'))
        for source in data['sources']:
            if source.get('id')=='kubernetes_docs_ru':
                source['status']='catalogued_format_unverified'
        p.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    assert_fails(make_second_technical_source_unverified,contains='cannot satisfy v3 minimum_sources for technical')

    def stale_source_manifest(d:Path):
        p=d/'benchmark/external-heldout/SOURCE_MANIFEST.csv'
        lines=p.read_text(encoding='utf-8').splitlines()
        p.write_text('\n'.join(line for line in lines if not line.startswith('kubernetes_docs_ru,'))+'\n',encoding='utf-8')
    assert_fails(stale_source_manifest,contains='SOURCE_MANIFEST projection != SOURCE_REGISTRY')

    def remove_prose_author_provenance(d:Path):
        p=d/'benchmark/external-heldout/SOURCE_REGISTRY.json'
        data=json.loads(p.read_text(encoding='utf-8'))
        for source in data['sources']:
            if 'prose' in source.get('profiles',[]):
                source['author_provenance_capable']=False
        p.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    assert_fails(remove_prose_author_provenance,contains='cannot satisfy v3 author provenance for prose')

    print('test_validation_mutations: OK')

if __name__=='__main__': main()
