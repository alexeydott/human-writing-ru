#!/usr/bin/env python3
from __future__ import annotations
import hashlib
import subprocess
import sys
import tempfile
from pathlib import Path
import zipfile

ROOT=Path(__file__).resolve().parents[1]
BUILDER=ROOT/'scripts/build_release.py'
VERSION=(ROOT/'VERSION').read_text(encoding='utf-8').strip()
NAME=f'human-writing-ru-{VERSION}-full.zip'

def digest(p:Path)->str: return hashlib.sha256(p.read_bytes()).hexdigest()

def main()->None:
    git_head=ROOT/'.git'/'HEAD'
    git_head_before=git_head.read_bytes() if git_head.is_file() else None
    with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
        for d in (a,b):
            p=subprocess.run([sys.executable,str(BUILDER),'--output-dir',d],cwd=ROOT,text=True,capture_output=True,env={**__import__('os').environ,'PYTHONDONTWRITEBYTECODE':'1'})
            assert p.returncode==0,p.stdout+p.stderr
            if git_head_before is not None:
                assert git_head.read_bytes()==git_head_before, 'release builder modified .git/HEAD'
        za,zb=Path(a)/NAME,Path(b)/NAME
        assert digest(za)==digest(zb), 'release ZIP is not deterministic'
        with zipfile.ZipFile(za) as z:
            names=z.namelist()
            assert names and all(n.startswith('human-writing-ru/') for n in names)
            assert 'human-writing-ru/SKILL.md' in names
            assert 'human-writing-ru/quality/RELEASE_INTEGRITY.json' in names
            integrity=__import__('json').loads(z.read('human-writing-ru/quality/RELEASE_INTEGRITY.json').decode('utf-8'))
            assert integrity['package_version']==VERSION and integrity['skill_root']=='human-writing-ru'
            assert integrity['frozen_inputs_match'] is True
            forbidden_parts={'__pycache__','.pytest_cache','.mypy_cache','.ruff_cache','.git','.agents','.ai-factory','.codex','.opencode','.venv','node_modules'}
            assert not any(any(part in forbidden_parts for part in Path(n).parts) or n.endswith('.pyc') or Path(n).name in {'.coverage','.DS_Store'} for n in names)
            assert 'human-writing-ru/data/README.md' in names
            assert 'human-writing-ru/data/corpus_manifest.example.csv' in names
            assert 'human-writing-ru/dist/human-writing-ru-lite.md' in names
            assert not any('/data/taiga_social/' in n or '/data/heldout-work/' in n for n in names)
            assert not any(n.endswith('.zip') or n.endswith('.sha256.txt') for n in names)
            assert 'human-writing-ru/.gitignore' not in names
            assert not any(n.startswith('human-writing-ru-1.') for n in names)
            tracked=integrity['tracked_sha256']
            for rel in [
                'references/technical-specification.md',
                'evals/tz_rule_cases.json',
                'TZ_NORMALIZATION.md',
                'references/ai-writing-patterns.md',
                'evals/humanizer_adaptation_cases.json',
                'THIRD_PARTY_NOTICES.md',
            ]:
                assert rel in tracked, f'missing integrity coverage for {rel}'
    print('test_release_builder: OK')

if __name__=='__main__': main()
