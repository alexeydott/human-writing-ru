#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import os
import re
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
MAT = ROOT / "scripts/materialize_external_heldout.py"
VAL = ROOT / "scripts/validate_external_heldout.py"
BASELINE = ROOT / "benchmark/external-heldout/UNCHANGED_CODE_SHA256.json"

spec = importlib.util.spec_from_file_location("mat_ext", MAT)
mod = importlib.util.module_from_spec(spec)
assert spec.loader
spec.loader.exec_module(mod)

# HTML extraction preserves paragraph boundaries and ignores navigation/scripts.
html = """<html><body><nav>Меню сайта</nav><main><h1>Заголовок</h1>
<p>Первый абзац с русским текстом и подробным описанием события.</p>
<p>Второй абзац продолжает рассказ и содержит достаточно слов для проверки.</p>
</main><script>плохой текст</script></body></html>"""
text, _ = mod.html_to_text(html)
assert "Меню сайта" not in text
assert "плохой текст" not in text
assert "Первый абзац" in text and "Второй абзац" in text

# A source-specific content selector must not fall back to page chrome when a
# public page has no semantic <main> or <article> element.
case_html = """<html><body><nav>Рейтинги Войти</nav>
<div class=\"caseblock\"><p>Содержательная часть кейса с русским текстом.</p></div>
<footer>Памятка агентствам</footer></body></html>"""
case_text, _ = mod.html_to_text(case_html, r"\bcaseblock\b")
assert "Содержательная часть" in case_text
assert "Рейтинги" not in case_text and "Памятка" not in case_text

# GitHub truncates recursive root trees for very large repositories.  Sources
# that declare tree_root must traverse that subtree rather than silently yield
# zero documents.
old_fetch = mod.fetch_text
try:
    calls = []
    def tree_fetch(url, **kwargs):
        calls.append(url)
        if url.endswith("trees/master?recursive=1"):
            return json.dumps({"truncated": True, "tree": []}), url
        if url.endswith("trees/master"):
            return json.dumps({"tree": [{"path": "ru", "type": "tree", "sha": "ru-sha"}]}), url
        if url.endswith("trees/ru-sha?recursive=1"):
            return json.dumps({"truncated": False, "tree": [{"path": "docs/a.md", "type": "blob"}]}), url
        raise AssertionError(url)
    mod.fetch_text = tree_fetch
    source = {"repository": "owner/repo", "ref": "master", "tree_root": "ru", "path_regex": r"^ru/docs/.+\.md$"}
    args = type("Args", (), {"timeout": 1.0, "user_agent": "test"})()
    paths, errors = mod.github_tree_paths(source, args)
    assert paths == ["ru/docs/a.md"] and not errors
finally:
    mod.fetch_text = old_fetch

# Generic ZIP reader handles JSONL records without splitting one text into fake docs.
with tempfile.TemporaryDirectory() as td:
    zpath = Path(td) / "sample.zip"
    with zipfile.ZipFile(zpath, "w") as zf:
        zf.writestr("posts.jsonl", json.dumps({"id": 1, "author": "a", "text": "Русский текст первого документа."}, ensure_ascii=False) + "\n" + json.dumps({"id": 2, "author": "b", "content": "Русский текст второго документа."}, ensure_ascii=False))
    records = list(mod.iter_zip_records(zpath))
    assert len(records) == 2
    assert records[0][2] == "a" and records[1][2] == "b"

# External-heldout pass must not alter linter or ablation runner bytes.
baseline = json.loads(BASELINE.read_text(encoding="utf-8"))["sha256"]
for rel, expected in baseline.items():
    actual = hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()
    assert actual == expected, (rel, actual, expected)

# Validator freeze-gate logic on synthetic TEST fixtures only. These are not benchmark data.
with tempfile.TemporaryDirectory() as td:
    base = Path(td)
    raw = base / "raw"
    raw.mkdir()
    manifest = base / "manifest.csv"
    columns = ["id", "path", "profile", "channel", "source_id", "source_url", "archive_url", "final_url", "author_or_group", "independence_group", "license_or_terms", "redistribution", "sha256", "words", "paragraphs", "russian_share", "calibration_eligible", "lexical_only"]
    rows = []
    # 50 independent docs x 205 words = >10k words. Repeated body structure is okay here;
    # near-duplicate clustering is intentionally disabled for this gate unit test.
    for i in range(50):
        unique = chr(0x0430 + (i % 32)) * 5 + chr(0x0430 + ((i // 32) % 32)) * 4
        sentence = f"Документ {unique} содержит отдельный проверочный материал и нормальные русские предложения. "
        body = (sentence * 24).strip()
        p = raw / f"p{i}.txt"
        p.write_text(body + "\n", encoding="utf-8")
        digest = hashlib.sha256((body + "\n").encode("utf-8")).hexdigest()
        rows.append({
            "id": f"p{i}", "path": f"raw/p{i}.txt", "profile": "prose", "channel": "media",
            "source_id": "fixture", "source_url": "fixture", "archive_url": "", "final_url": "",
            "author_or_group": f"author{i}", "independence_group": f"doc{i}", "license_or_terms": "own-test", "redistribution": "test-only",
            "sha256": digest, "words": "0", "paragraphs": "1", "russian_share": "1", "calibration_eligible": "1", "lexical_only": "0"
        })
    with manifest.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=columns); w.writeheader(); w.writerows(rows)
    out = base / "report.json"
    p = subprocess.run([sys.executable, str(VAL), "--manifest", str(manifest), "--output", str(out), "--near-duplicate-threshold", "1.1"], text=True, capture_output=True)
    assert p.returncode == 0, p.stderr
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["profiles"]["prose"]["independent_documents"] == 50
    assert data["profiles"]["prose"]["independent_words"] >= 10000
    assert data["profiles"]["prose"]["freeze_gate_met"] is True
    assert data["profile_size_gate"]["source_key"] == "profile_gate"
    assert data["gate_spec"].endswith("spec-v3.json")
    assert data["ready_for_unchanged_ablation"] is False  # other profiles are intentionally absent
    validated = Path(data["validated_representative_manifest"])
    assert validated.exists()
    with validated.open(encoding="utf-8", newline="") as fh:
        validated_rows = list(csv.DictReader(fh))
    assert len(validated_rows) == 50

# Exact duplicates must be collapsed in the manifest passed to the unchanged ablation runner.
with tempfile.TemporaryDirectory() as td:
    base = Path(td)
    raw = base / "raw"; raw.mkdir()
    body = (("Это один и тот же русский документ для проверки дедупликации. " * 30).strip() + "\n")
    for name in ("a.txt", "b.txt"):
        (raw / name).write_text(body, encoding="utf-8")
    digest = hashlib.sha256(body.encode("utf-8")).hexdigest()
    manifest = base / "manifest.csv"
    columns = ["id", "path", "profile", "channel", "source_id", "source_url", "archive_url", "final_url", "author_or_group", "independence_group", "license_or_terms", "redistribution", "sha256", "words", "paragraphs", "russian_share", "calibration_eligible", "lexical_only"]
    rows = []
    for i, name in enumerate(("a.txt", "b.txt")):
        rows.append({"id": f"dup{i}", "path": f"raw/{name}", "profile": "prose", "channel": "blog", "source_id": "fixture", "source_url": "fixture", "archive_url": "", "final_url": "", "author_or_group": f"author{i}", "independence_group": f"different-doc-{i}", "license_or_terms": "own-test", "redistribution": "test-only", "sha256": digest, "words": "0", "paragraphs": "1", "russian_share": "1", "calibration_eligible": "1", "lexical_only": "0"})
    with manifest.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=columns); w.writeheader(); w.writerows(rows)
    out = base / "report.json"
    p = subprocess.run([sys.executable, str(VAL), "--manifest", str(manifest), "--output", str(out)], text=True, capture_output=True)
    assert p.returncode == 0, p.stderr
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["valid_files"] == 2
    assert data["independence_clusters"] == 1
    assert data["validated_representative_rows"] == 1
    with Path(data["validated_representative_manifest"]).open(encoding="utf-8", newline="") as fh:
        assert len(list(csv.DictReader(fh))) == 1

print("OK")

# Freeze readiness must include technical. A four-profile corpus may not unlock ablation.
with tempfile.TemporaryDirectory() as td:
    base = Path(td)
    raw = base / "raw"; raw.mkdir()
    manifest = base / "manifest.csv"
    columns = ["id", "path", "profile", "channel", "source_id", "source_url", "archive_url", "final_url", "author_or_group", "independence_group", "license_or_terms", "redistribution", "sha256", "words", "paragraphs", "russian_share", "calibration_eligible", "lexical_only"]
    rows = []
    for i, profile in enumerate(("prose", "oral", "product", "official")):
        body = f"Уникальный проверочный документ профиля {profile} номер {i}.\n"
        pth = raw / f"{profile}.txt"
        pth.write_text(body, encoding="utf-8")
        rows.append({
            "id": profile, "path": f"raw/{profile}.txt", "profile": profile, "channel": "fixture",
            "source_id": "fixture", "source_url": "fixture", "archive_url": "", "final_url": "",
            "author_or_group": f"a{i}", "independence_group": f"d{i}", "license_or_terms": "own-test",
            "redistribution": "test-only", "sha256": hashlib.sha256(body.encode("utf-8")).hexdigest(),
            "words": "0", "paragraphs": "1", "russian_share": "1", "calibration_eligible": "1", "lexical_only": "0",
        })
    with manifest.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=columns); w.writeheader(); w.writerows(rows)
    custom_spec = json.loads((ROOT / "benchmark/ablation/spec.json").read_text(encoding="utf-8"))
    custom_spec["freeze_gate"]["minimum_independent_documents_per_profile"] = 1
    custom_spec["freeze_gate"]["minimum_words_per_profile"] = 1
    spec_path = base / "spec.json"
    spec_path.write_text(json.dumps(custom_spec, ensure_ascii=False), encoding="utf-8")
    out = base / "report.json"
    p = subprocess.run([sys.executable, str(VAL), "--manifest", str(manifest), "--output", str(out), "--spec", str(spec_path), "--near-duplicate-threshold", "1.1"], text=True, capture_output=True)
    assert p.returncode == 0, p.stderr
    data = json.loads(out.read_text(encoding="utf-8"))
    assert set(data["required_profiles_for_freeze"]) == {"prose", "oral", "product", "technical", "official"}
    assert all(data["profiles"][name]["freeze_gate_met"] for name in ("prose", "oral", "product", "official"))
    assert data["profiles"]["technical"]["freeze_gate_met"] is False
    assert data["ready_for_unchanged_ablation"] is False

print("OK technical-freeze regression")

# Generic ZIP materialization must honor registry profile/channel; it must not hardcode prose/blog.
with tempfile.TemporaryDirectory() as td:
    out = Path(td)
    cache = out / ".cache"; cache.mkdir()
    source = {
        "id": "oral_zip_fixture", "profiles": ["oral"], "channels": ["prepared_speech"],
        "download_url": "https://example.invalid/oral.zip", "source_url": "fixture",
        "license_or_terms": "own-test", "redistribution": "test-only",
        "target_documents": 1, "minimum_words_per_document": 10, "minimum_paragraphs_per_document": 1,
    }
    body = ("Это естественно ограниченный русский устный документ для проверки профиля. " * 20).strip()
    with zipfile.ZipFile(cache / "oral_zip_fixture.zip", "w") as zf:
        zf.writestr("speech.jsonl", json.dumps({"id": "speech-1", "text": body}, ensure_ascii=False) + "\n")
    class Args:
        target_docs = 1
        timeout = 1.0
        user_agent = "test"
    rows = []; hashes = set()
    rep = mod.materialize_zip_text_records(source, out, Args(), rows, hashes)
    assert rep["accepted"] == 1, rep
    assert rows[0]["profile"] == "oral" and rows[0]["channel"] == "prepared_speech", rows[0]
    assert Path(rows[0]["path"]).parts[:2] == ("raw", "oral"), rows[0]["path"]

print("OK zip profile routing")

# factRuEval adapter regression: profile/channel come from the registry and a valid
# network response must not fail on an undefined local variable.
with tempfile.TemporaryDirectory() as td:
    out = Path(td)
    source = {
        "id": "fact_fixture", "profiles": ["prose"], "channels": ["media"],
        "source_url": "fixture", "license_or_terms": "own-test", "redistribution": "test-only",
        "target_documents": 1, "minimum_words_per_document": 20, "minimum_paragraphs_per_document": 1,
    }
    tree = {"tree": [{"path": "devset/book_1.txt", "type": "blob"}]}
    body = ("Это независимый русский новостной документ с естественной границей и достаточным количеством слов. " * 8).strip()
    old_fetch = mod.fetch_text
    def fake_fetch(url, *, timeout, user_agent):
        if "git/trees/master" in url:
            return json.dumps(tree), url
        if url.endswith("devset/book_1.txt"):
            return body, url
        raise AssertionError(url)
    mod.fetch_text = fake_fetch
    class Args:
        target_docs = 1
        timeout = 1.0
        user_agent = "test"
        delay = 0.0
    rows = []; hashes = set()
    try:
        rep = mod.materialize_factrueval(source, out, Args(), rows, hashes)
    finally:
        mod.fetch_text = old_fetch
    assert rep["accepted"] == 1, rep
    assert rows[0]["profile"] == "prose" and rows[0]["channel"] == "media"

print("OK factRuEval adapter regression")

# ZIP reader preserves natural TSV row boundaries rather than treating the whole
# table as one document.
with tempfile.TemporaryDirectory() as td:
    zpath = Path(td) / "rows.zip"
    body1 = ("Первая отдельная речь содержит самостоятельный русский текст для проверки. " * 8).strip()
    body2 = ("Вторая отдельная речь также сохраняет исходную границу документа при чтении. " * 8).strip()
    with zipfile.ZipFile(zpath, "w") as zf:
        zf.writestr("speeches.tsv", "id\tspeaker\ttext\n1\tИванов\t" + body1 + "\n2\tПетров\t" + body2 + "\n")
    records = list(mod.iter_zip_records(zpath))
    assert len(records) == 2, records
    assert records[0][0] == "1" and records[0][2] == "Иванов"
    assert records[1][0] == "2" and records[1][2] == "Петров"

print("OK TSV natural boundaries")

# Multi-archive sources (e.g. RuREBus) retain one source_id, process all upstream
# archive parts, and preserve the actual archive URL in provenance.
with tempfile.TemporaryDirectory() as td:
    out = Path(td)
    cache = out / ".cache"; cache.mkdir()
    source = {
        "id": "multi_zip_fixture", "profiles": ["product"], "channels": ["business_document"],
        "source_url": "fixture", "download_urls": ["https://example.invalid/a.zip", "https://example.invalid/b.zip"],
        "license_or_terms": "own-test", "redistribution": "test-only", "target_documents": 2,
        "minimum_words_per_document": 20, "minimum_paragraphs_per_document": 1,
    }
    for idx, label in enumerate(("Первый", "Второй")):
        body = ((label + " независимый деловой документ содержит русский текст и естественную границу. ") * 8).strip()
        with zipfile.ZipFile(cache / f"multi_zip_fixture-{idx:02d}.zip", "w") as zf:
            zf.writestr(f"part{idx}.jsonl", json.dumps({"id": "same-member-id", "text": body}, ensure_ascii=False) + "\n")
    class Args:
        target_docs = 2
        timeout = 1.0
        user_agent = "test"
    rows = []; hashes = set()
    rep = mod.materialize_zip_text_records(source, out, Args(), rows, hashes)
    assert rep["accepted"] == 2 and rep["archives"] == 2, rep
    assert {r["archive_url"] for r in rows} == set(source["download_urls"])
    assert len({r["id"] for r in rows}) == 2
    assert all(r["source_id"] == "multi_zip_fixture" for r in rows)

print("OK multi-ZIP acquisition")

# GitHub-tree adapter: raw path components must use URL percent-encoding, not '+',
# and Markdown boilerplate/code are acquisition-normalized before eligibility.
with tempfile.TemporaryDirectory() as td:
    out = Path(td)
    repo_path = "ru/test folder/документ.md"
    source = {
        "id": "github_tree_fixture", "profiles": ["technical"], "channels": ["technical_docs"],
        "adapter": "github_tree_text", "repository": "owner/repo", "ref": "main",
        "path_regex": r"^ru/.*\.md$", "source_url": "fixture", "license_or_terms": "own-test",
        "redistribution": "test-only", "target_documents": 1,
        "minimum_words_per_document": 30, "minimum_paragraphs_per_document": 3,
    }
    para = ("Русская техническая инструкция описывает действие пользователя, условие выполнения и ожидаемый результат. " * 4).strip()
    markdown = "---\ntitle: test\n---\n# Заголовок\n\n" + para + "\n\n```bash\necho secret\n```\n\n" + para + "\n\n" + para
    tree = {"tree": [{"path": repo_path, "type": "blob"}]}
    seen = []
    old_fetch = mod.fetch_text
    def fake_fetch(url, *, timeout, user_agent):
        seen.append(url)
        if "git/trees/main" in url:
            return json.dumps(tree, ensure_ascii=False), url
        return markdown, url
    mod.fetch_text = fake_fetch
    class Args:
        target_docs = 1
        timeout = 1.0
        user_agent = "test"
        delay = 0.0
    rows = []; hashes = set()
    try:
        rep = mod.materialize_github_tree_text(source, out, Args(), rows, hashes)
    finally:
        mod.fetch_text = old_fetch
    assert rep["accepted"] == 1, rep
    raw_urls = [u for u in seen if "raw.githubusercontent.com" in u]
    assert raw_urls and "%20" in raw_urls[0] and "+" not in raw_urls[0], raw_urls
    saved = (out / rows[0]["path"]).read_text(encoding="utf-8")
    assert "echo secret" not in saved and "title: test" not in saved and "Русская техническая" in saved

print("OK GitHub-tree acquisition")

# Registry-level technical source must exclude Yandex Cloud reusable _includes,
# which are fragments rather than independent technical documents.
registry = json.loads((ROOT / "benchmark/external-heldout/SOURCE_REGISTRY.json").read_text(encoding="utf-8"))
yc = next(s for s in registry["sources"] if s["id"] == "yandex_cloud_docs_ru")
yc_re = __import__("re").compile(yc["path_regex"])
assert yc_re.search("ru/compute/operations/vm-create.md")
assert not yc_re.search("ru/_includes/authentication.md")

print("OK Yandex standalone-document routing")

# Speech XML acquisition must exclude editorial metadata while preserving the
# naturally bounded multi-speaker event as one document.
xml_fixture = """<top><meta><description>Редакционное описание не является устной речью.</description></meta>
<speech><p speaker="А">Первая устная реплика участника события.</p><p speaker="Б">Вторая устная реплика другого участника.</p></speech></top>"""
xml_text = mod.xml_to_text(xml_fixture)
assert "Редакционное описание" not in xml_text
assert "Первая устная реплика" in xml_text and "Вторая устная реплика" in xml_text
assert mod.paragraph_count(xml_text) == 2

print("OK speech XML body routing")

# Validator IDs are annotation keys and must be globally unique.
with tempfile.TemporaryDirectory() as td:
    base = Path(td); raw = base / "raw"; raw.mkdir()
    columns = ["id","path","profile","channel","source_id","author_or_group","independence_group","sha256","calibration_eligible","lexical_only"]
    rows=[]
    for i in range(2):
        body=(f"Уникальный документ номер {i} для проверки повторяющегося идентификатора. "*12).strip()+"\n"
        path=raw/f"{i}.txt"; path.write_text(body,encoding="utf-8")
        rows.append({"id":"same-id","path":f"raw/{i}.txt","profile":"prose","channel":"blog","source_id":f"s{i}","author_or_group":f"a{i}","independence_group":f"d{i}","sha256":hashlib.sha256(body.encode()).hexdigest(),"calibration_eligible":"1","lexical_only":"0"})
    manifest=base/"manifest.csv"
    with manifest.open("w",encoding="utf-8",newline="") as fh:
        w=csv.DictWriter(fh,fieldnames=columns); w.writeheader(); w.writerows(rows)
    report=base/"report.json"
    p=subprocess.run([sys.executable,str(VAL),"--manifest",str(manifest),"--output",str(report),"--near-duplicate-threshold","1.1"],text=True,capture_output=True)
    assert p.returncode==2,(p.returncode,p.stdout,p.stderr)
    data=json.loads(report.read_text(encoding="utf-8"))
    assert sum(1 for x in data["invalid_files"] if x["reason"]=="duplicate_id")==2
    assert data["validated_representative_rows"]==0
print("OK duplicate document-id rejection")

# Independence IDs are source-scoped: unrelated corpora may legitimately reuse '1'.
with tempfile.TemporaryDirectory() as td:
    base=Path(td); raw=base/"raw"; raw.mkdir()
    columns=["id","path","profile","channel","source_id","author_or_group","independence_group","sha256","calibration_eligible","lexical_only"]
    rows=[]
    for i,source in enumerate(("s1","s2")):
        body=(("Первый" if i==0 else "Второй")+" независимый русский документ из отдельного корпуса. ")*16+"\n"
        path=raw/f"{i}.txt"; path.write_text(body,encoding="utf-8")
        rows.append({"id":f"{source}:1","path":f"raw/{i}.txt","profile":"prose","channel":"blog","source_id":source,"author_or_group":f"a{i}","independence_group":"1","sha256":hashlib.sha256(body.encode()).hexdigest(),"calibration_eligible":"1","lexical_only":"0"})
    manifest=base/"manifest.csv"
    with manifest.open("w",encoding="utf-8",newline="") as fh:
        w=csv.DictWriter(fh,fieldnames=columns); w.writeheader(); w.writerows(rows)
    report=base/"report.json"
    p=subprocess.run([sys.executable,str(VAL),"--manifest",str(manifest),"--output",str(report),"--near-duplicate-threshold","1.1"],text=True,capture_output=True)
    assert p.returncode==0,(p.returncode,p.stdout,p.stderr)
    data=json.loads(report.read_text(encoding="utf-8"))
    assert data["independence_clusters"]==2,data
    assert data["validated_representative_rows"]==2,data
print("OK source-scoped independence identifiers")


# Registry feasibility regression: technical diversity must have at least two source families.
registry=json.loads((ROOT/'benchmark/external-heldout/SOURCE_REGISTRY.json').read_text(encoding='utf-8'))
technical=[s for s in registry['sources'] if 'technical' in s.get('profiles',[]) and s.get('adapter')!='manual_reference_only']
assert len({s['id'] for s in technical}) >= 2, technical
k8s=next(s for s in technical if s['id']=='kubernetes_docs_ru')
path_re=re.compile(k8s['path_regex'])
assert path_re.search('content/ru/docs/tasks/run-application/run-stateless-application-deployment.md')
assert not path_re.search('content/ru/docs/templates/concept.md')
assert not path_re.search('content/ru/docs/home/_index.md')
assert not path_re.search('content/ru/docs/concepts/_index.md')
print('OK technical registry diversity feasibility')

# Format-unverified sources are blocked by default; research inspection requires explicit override.
with tempfile.TemporaryDirectory() as td:
    base = Path(td)
    registry = base / "registry.json"
    registry.write_text(json.dumps({
        "schema_version": 1,
        "sources": [{
            "id": "unverified_fixture", "profiles": ["prose"], "channels": ["blog"],
            "adapter": "manual_reference_only", "source_url": "fixture",
            "redistribution": "test-only", "status": "catalogued_format_unverified"
        }]
    }), encoding="utf-8")
    out = base / "out"
    proc = subprocess.run([sys.executable, str(MAT), "--registry", str(registry), "--sources", "unverified_fixture", "--output-dir", str(out)], cwd=ROOT, text=True, capture_output=True)
    assert proc.returncode != 0
    assert "format-unverified" in (proc.stdout + proc.stderr)

print("OK format-unverified source blocking")

# LJSearch adapter must route a successful saved copy without relying on globals.
with tempfile.TemporaryDirectory() as td:
    base = Path(td)
    source = {
        "id": "lj_fixture", "profiles": ["prose"], "channels": ["blog"],
        "seed_saved_copies": ["https://ljsear.ch/savedcopy?post=123"], "queries": [],
        "target_documents": 1, "minimum_words_per_document": 5, "minimum_paragraphs_per_document": 1,
        "source_url": "https://ljsear.ch/", "license_or_terms": "test", "redistribution": "test-only"
    }
    html = "<main><p>Это достаточно длинный русский текст для отдельной записи блога и проверки маршрутизации.</p></main><a href='https://tester.livejournal.com/123.html'>orig</a>"
    old_fetch = mod.fetch_text
    try:
        mod.fetch_text = lambda *a, **k: (html, "https://ljsear.ch/savedcopy?post=123")
        args = type("Args", (), {"target_docs": None, "timeout": 1.0, "user_agent": "test", "delay": 0.0})()
        rows, hashes = [], set()
        rep = mod.materialize_ljsearch(source, base, args, rows, hashes)
        assert rep["accepted"] == 1, rep
        assert rows[0]["profile"] == "prose" and rows[0]["channel"] == "blog"
        assert rows[0]["author_or_group"] == "tester"
    finally:
        mod.fetch_text = old_fetch

print("OK LJSearch successful-routing regression")

# Web-index IDs must remain unique when articles share one path and differ only
# by query parameters, as on publishers that route all cases through /news.
with tempfile.TemporaryDirectory() as td:
    base = Path(td)
    source = {
        "id": "web_fixture", "profiles": ["product"], "channels": ["business_case"],
        "source_url": "https://example.test/", "target_documents": 2,
        "minimum_words_per_document": 5, "minimum_paragraphs_per_document": 1,
        "license_or_terms": "test", "redistribution": "test-only",
    }
    urls = ["https://example.test/news?id=1", "https://example.test/news?id=2"]
    old_discover = mod.discover_index_urls
    old_fetch = mod.fetch_text
    try:
        mod.discover_index_urls = lambda *a, **k: (urls, [])
        mod.fetch_text = lambda url, **k: (
            f"<p>Это отдельный русский материал номер {url[-1]} с достаточным количеством слов для проверки.</p>",
            url,
        )
        args = type("Args", (), {
            "target_docs": None, "timeout": 1.0, "user_agent": "test",
            "delay": 0.0, "max_index_pages": 1,
        })()
        rows, hashes = [], set()
        rep = mod.materialize_web_index(source, base, args, rows, hashes)
        assert rep["accepted"] == 2, rep
        assert len({row["id"] for row in rows}) == 2, rows
    finally:
        mod.discover_index_urls = old_discover
        mod.fetch_text = old_fetch

print("OK web-index query identity regression")

# GitHub API requests use an available token, but other hosts never receive it.
old_token = os.environ.get("GITHUB_TOKEN")
try:
    os.environ["GITHUB_TOKEN"] = "fixture-secret"
    github_headers = mod.request_headers("https://api.github.com/repos/o/r", "test")
    other_headers = mod.request_headers("https://example.test/data", "test")
    assert github_headers["Authorization"] == "Bearer fixture-secret"
    assert "Authorization" not in other_headers
finally:
    if old_token is None:
        os.environ.pop("GITHUB_TOKEN", None)
    else:
        os.environ["GITHUB_TOKEN"] = old_token

print("OK scoped GitHub authentication regression")

# Local sidecar preserves verified author/split provenance instead of inventing it.
with tempfile.TemporaryDirectory() as td:
    base = Path(td)
    local = base / "local"; local.mkdir()
    text = "Это достаточно длинный русский документ из локального корпуса для проверки метаданных автора и границ документа.\n"
    (local / "speech.txt").write_text(text, encoding="utf-8")
    (local / "manifest.csv").write_text(
        "id,path,author_or_group,split_group,source_document_id,independence_group,channel\n"
        "speech-1,speech.txt,speaker-42,session-7,upstream-99,event-99,parliamentary_speech\n", encoding="utf-8"
    )
    source = {
        "id": "local_fixture", "profiles": ["oral"], "channels": ["parliamentary_speech"],
        "source_url": "fixture", "redistribution": "test-only", "minimum_words_per_document": 5,
        "minimum_paragraphs_per_document": 1, "target_documents": 1
    }
    args = type("Args", (), {"target_docs": None})()
    rows, hashes = [], set()
    rep = mod.import_local_tree(source, local, base / "out", args, rows, hashes)
    assert rep["accepted"] == 1 and rep["sidecar_used"] is True, rep
    row = rows[0]
    assert row["author_or_group"] == "speaker-42"
    assert row["split_group"] == "session-7"
    assert row["source_document_id"] == "upstream-99"
    assert row["independence_group"] == "event-99"
    imported = base / "out" / row["path"]
    assert row["sha256"] == hashlib.sha256(
        imported.read_text(encoding="utf-8").encode("utf-8")
    ).hexdigest()

print("OK local sidecar provenance regression")

# Acquisition exact dedupe is profile-scoped so contradictory cross-profile routing reaches validator.
rows, hashes = [], set()
row_a = {"profile": "prose", "sha256": "same", "id": "a"}
row_b = {"profile": "prose", "sha256": "same", "id": "b"}
row_c = {"profile": "official", "sha256": "same", "id": "c"}
assert mod.dedupe_append(row_a, rows, hashes) is True
assert mod.dedupe_append(row_b, rows, hashes) is False
assert mod.dedupe_append(row_c, rows, hashes) is True
assert [r["id"] for r in rows] == ["a", "c"]
print("OK profile-scoped acquisition dedupe")

# Validator must block an exact text routed to different profiles instead of choosing an arbitrary representative.
with tempfile.TemporaryDirectory() as td:
    base = Path(td); raw = base / "raw"; raw.mkdir()
    body = ("Одинаковый русский документ не должен одновременно калибровать разные профили. " * 25).strip() + "\n"
    for name in ("a.txt", "b.txt"):
        (raw / name).write_text(body, encoding="utf-8")
    digest = hashlib.sha256(body.encode("utf-8")).hexdigest()
    manifest = base / "manifest.csv"
    manifest.write_text(
        "id,path,profile,channel,source_id,sha256,calibration_eligible,lexical_only\n"
        f"a,raw/a.txt,prose,blog,s1,{digest},1,0\n"
        f"b,raw/b.txt,official,legal,s2,{digest},1,0\n", encoding="utf-8"
    )
    out = base / "report.json"
    proc = subprocess.run([sys.executable, str(VAL), "--manifest", str(manifest), "--output", str(out)], cwd=ROOT, text=True, capture_output=True)
    assert proc.returncode != 0
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["validation_clean"] is False
    assert len(data["cross_profile_exact_duplicate_groups"]) == 1
    assert data["validated_representative_rows"] == 0
    assert data["ready_for_decision_protocol_input"] is False
print("OK cross-profile exact-routing conflict")

# A validated manifest written to another directory must rebase relative document paths.
with tempfile.TemporaryDirectory() as td:
    base=Path(td); raw=base/"raw"; raw.mkdir(); nested=base/"validated"; nested.mkdir()
    body=("Отдельный русский документ для проверки переноса относительного пути. "*20).strip()+"\n"
    (raw/"doc.txt").write_text(body,encoding="utf-8")
    digest=hashlib.sha256(body.encode("utf-8")).hexdigest()
    manifest=base/"manifest.csv"
    manifest.write_text(
        "id,path,profile,channel,source_id,sha256,calibration_eligible,lexical_only\n"
        f"d1,raw/doc.txt,prose,blog,s1,{digest},1,0\n",encoding="utf-8")
    report=base/"report.json"; validated=nested/"manifest.validated.csv"
    proc=subprocess.run([sys.executable,str(VAL),"--manifest",str(manifest),"--output",str(report),"--validated-manifest",str(validated)],cwd=ROOT,text=True,capture_output=True)
    assert proc.returncode==0, proc.stderr
    with validated.open(encoding="utf-8",newline="") as fh:
        row=next(csv.DictReader(fh))
    resolved=(validated.parent/row["path"]).resolve()
    assert resolved==(raw/"doc.txt").resolve(), (row["path"], resolved)
print("OK validated-manifest path rebasing")

# Validator diagnostics must not let unknown sentinels or case variants fake provenance diversity.
with tempfile.TemporaryDirectory() as td:
    base=Path(td); raw=base/'raw'; raw.mkdir()
    columns=['id','path','profile','channel','source_id','author_or_group','independence_group','sha256','calibration_eligible','lexical_only']
    fixtures=[
        ('d1','Источник один описывает независимое событие с несколькими подробностями и отдельным контекстом. '*10,'Source-A','Иван Иванов','Blog'),
        ('d2','Второй независимый текст обсуждает совсем другую тему и содержит собственные факты для проверки. '*10,'source-a','иван   иванов','blog'),
        ('d3','Третий самостоятельный материал нужен для проверки неизвестного provenance и отдельной границы документа. '*10,'UNKNOWN-SOURCE','N/A','unknown'),
    ]
    rows=[]
    for idx,(doc_id,body,source,author,channel) in enumerate(fixtures):
        path=raw/f'{idx}.txt'; path.write_text(body,encoding='utf-8')
        rows.append({'id':doc_id,'path':f'raw/{idx}.txt','profile':'prose','channel':channel,'source_id':source,'author_or_group':author,'independence_group':doc_id,'sha256':hashlib.sha256(body.encode()).hexdigest(),'calibration_eligible':'1','lexical_only':'0'})
    manifest=base/'manifest.csv'
    with manifest.open('w',encoding='utf-8',newline='') as fh:
        w=csv.DictWriter(fh,fieldnames=columns); w.writeheader(); w.writerows(rows)
    report=base/'report.json'
    p=subprocess.run([sys.executable,str(VAL),'--manifest',str(manifest),'--output',str(report),'--near-duplicate-threshold','1.1'],text=True,capture_output=True)
    assert p.returncode==0,(p.returncode,p.stdout,p.stderr)
    stats=json.loads(report.read_text(encoding='utf-8'))['profiles']['prose']
    assert stats['sources']=={'source-a':2},stats
    assert stats['channels']=={'blog':2},stats
    assert stats['distinct_known_author_groups']==1,stats
    assert stats['known_source_documents']==2 and stats['known_source_document_coverage']==0.6667,stats
    assert stats['known_channel_documents']==2 and stats['known_channel_document_coverage']==0.6667,stats
    assert stats['largest_source_share_of_all_documents']==0.6667,stats
    assert stats['largest_source_share_of_known_documents']==1.0,stats
print('OK validator provenance diagnostics normalization')
