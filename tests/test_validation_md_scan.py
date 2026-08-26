#!/usr/bin/env python3
"""Регрессия: обход Markdown в validate_skill.py игнорирует dev/agent-каталоги.

Локальные AI-контексты (.qwen/, .claude/, .agents/, .opencode/node_modules и т.п.) не входят
в пакет; их сторонние шаблонные ссылки не должны ронять самопроверку. Сканированные каталоги
продолжают проверяться.
"""
from __future__ import annotations
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
ENV = {**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'}
PROBE_LINK_MD = '# probe\n\n[x](missing-target.md)\n'
PROBE_ESCAPE_MD = '# probe\n\nпример текста \\n\\n## далее\n\n[x](missing-target.md)\n'


def copy_root(base: Path, name='human-writing-ru') -> Path:
    # Agent/dev catalogs are skipped wholesale: they are excluded from validation scans,
    # and the external-skill installer creates Windows junctions there that copytree cannot read.
    skip_dirs = {
        '__pycache__', '.git', 'data', 'node_modules', '.agents', '.ai-factory', '.claude',
        '.codex', '.opencode', '.qwen', '.venv',
    }

    def ignore(_dirpath: str, names):
        return {n for n in names if n in skip_dirs or n.endswith('.pyc')}

    dst = base / name
    shutil.copytree(ROOT, dst, ignore=ignore)
    # Keep the two packaged data files (see PACKAGE_DATA_FILES in build_release.py);
    # local corpora stay out of the copy no matter their size.
    for rel in ("data/README.md", "data/corpus_manifest.example.csv"):
        src = ROOT / rel
        if src.exists():
            out_path = dst / rel
            out_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, out_path)
    return dst


def validate(dst: Path):
    return subprocess.run([sys.executable, str(dst / 'scripts/validate_skill.py')],
                          cwd=dst, text=True, capture_output=True, env=ENV)


def run_case(mutator, expect_rc0: bool, must_contain=None, must_not_contain=None):
    with tempfile.TemporaryDirectory() as td:
        dst = copy_root(Path(td))
        mutator(dst)
        p = validate(dst)
        out = p.stdout + p.stderr
        if expect_rc0:
            assert p.returncode == 0, f'unexpected validation failure:\n{out}'
        else:
            assert p.returncode != 0, f'mutation unexpectedly passed:\n{out}'
        if must_contain:
            assert must_contain in out, (must_contain, out)
        if must_not_contain:
            assert must_not_contain not in out, (must_not_contain, out)


def main() -> None:
    # Чистая копия с реальными dev-каталогами агента должна проходить самопроверку.
    run_case(lambda d: None, expect_rc0=True)

    # Повреждённая ссылка внутри пропущенного каталога (.qwen/skills) не фиксируется.
    def probe_qwen(d: Path):
        p = d / '.qwen' / 'skills' / 'tmp-link-probe'
        p.mkdir(parents=True, exist_ok=True)
        (p / 'SKILL.md').write_text(PROBE_ESCAPE_MD, encoding='utf-8')
    run_case(probe_qwen, expect_rc0=True, must_not_contain='tmp-link-probe')

    # То же для .github/skills и вложенного node_modules.
    def probe_github_skills(d: Path):
        p = d / '.github' / 'skills' / 'tmp-link-probe'
        p.mkdir(parents=True, exist_ok=True)
        (p / 'SKILL.md').write_text(PROBE_LINK_MD, encoding='utf-8')
    run_case(probe_github_skills, expect_rc0=True, must_not_contain='tmp-link-probe')

    def probe_node_modules(d: Path):
        p = d / 'tools' / 'node_modules' / 'some-pkg'
        p.mkdir(parents=True, exist_ok=True)
        (p / 'README.md').write_text(PROBE_LINK_MD, encoding='utf-8')
    run_case(probe_node_modules, expect_rc0=True, must_not_contain='some-pkg')

    # Сканированный каталог по-прежнему фиксирует битую ссылку...
    def broken_link_in_docs(d: Path):
        (d / 'docs' / 'probe-broken-link.md').write_text(PROBE_LINK_MD, encoding='utf-8')
    run_case(broken_link_in_docs, expect_rc0=False,
             must_contain='broken Markdown link', must_not_contain='tmp-link-probe')

    # ...и литеральный \n escape.
    def escaped_newline_in_scanned_dir(d: Path):
        (d / 'docs' / 'probe-escaped-newline.md').write_text(PROBE_ESCAPE_MD, encoding='utf-8')
    run_case(escaped_newline_in_scanned_dir, expect_rc0=False,
             must_contain='literal escaped newline')

    print('test_validation_md_scan: OK')


if __name__ == '__main__':
    main()
