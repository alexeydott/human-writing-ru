#!/usr/bin/env python3
"""Materialize external held-out documents without changing the prose linter.

The release package contains source metadata and acquisition code, not third-party
raw corpora. This script is intentionally run OUTSIDE the release tree, e.g.:

  python scripts/materialize_external_heldout.py \
      --sources ljsearch_saved_copies factrueval_2016 \
      --output-dir data/heldout-work

It writes:
  raw/<profile>/<source>/<doc>.txt
  manifest.csv                  # compatible with scripts/ablate_signals.py
  MATERIALIZATION_REPORT.json

Copyrighted web pages are local research inputs only. Do not copy the raw/ tree
into a release unless the upstream license explicitly allows redistribution and
all attribution/other conditions have been reviewed.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import html
from html.parser import HTMLParser
import io
import json
import os
from pathlib import Path
import re
import shutil
import sys
import time
from typing import Iterable, Iterator
from urllib.error import HTTPError, URLError
from urllib.parse import quote, quote_plus, urljoin, urlparse
from urllib.request import Request, urlopen
import zipfile

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "benchmark/external-heldout/SOURCE_REGISTRY.json"
DEFAULT_LOCAL_CORPUS_ROOT = Path(
    os.environ.get("HUMAN_WRITING_RU_DATA_DIR", str(ROOT / "data"))
)
WORD_RE = re.compile(r"[А-Яа-яЁёA-Za-z]+(?:[-'][А-Яа-яЁёA-Za-z]+)*", re.UNICODE)
RUS_RE = re.compile(r"[А-Яа-яЁё]")
LJ_SAVED_RE = re.compile(r"(?:https?://ljsear\.ch)?/savedcopy\?post=(\d+)", re.I)
LJ_AUTHOR_RE = re.compile(r"https?://([A-Za-z0-9_-]+)\.livejournal\.com/", re.I)
BLOCK_TAGS = {
    "p", "div", "article", "main", "section", "li", "blockquote", "br",
    "h1", "h2", "h3", "h4", "h5", "h6", "pre", "tr", "td", "dd", "dt",
}
SKIP_TAGS = {"script", "style", "svg", "noscript", "form", "nav", "header", "footer"}
TEXT_FIELD_NAMES = (
    "text", "content", "body", "post", "message", "article", "description",
    "full_text", "plaintext", "textips",
)


class ProseHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.skip_depth = 0
        self.focus_depth = 0
        self.all_parts: list[str] = []
        self.focus_parts: list[str] = []
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        tag = tag.lower()
        attr = dict(attrs)
        if tag in SKIP_TAGS:
            self.skip_depth += 1
        if tag in {"article", "main"}:
            self.focus_depth += 1
        if tag in BLOCK_TAGS:
            self._append("\n")
        if tag == "a" and attr.get("href"):
            self.links.append(html.unescape(attr["href"]))

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in BLOCK_TAGS:
            self._append("\n")
        if tag in {"article", "main"} and self.focus_depth:
            self.focus_depth -= 1
        if tag in SKIP_TAGS and self.skip_depth:
            self.skip_depth -= 1

    def handle_data(self, data: str) -> None:
        if not self.skip_depth:
            self._append(data)

    def _append(self, value: str) -> None:
        if self.skip_depth:
            return
        self.all_parts.append(value)
        if self.focus_depth:
            self.focus_parts.append(value)


def normalize_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = html.unescape(text).replace("\xa0", " ")
    lines = []
    for line in text.splitlines():
        line = re.sub(r"[\t \f\v]+", " ", line).strip()
        if line:
            lines.append(line)
        elif lines and lines[-1] != "":
            lines.append("")
    text = "\n".join(lines)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return text


def html_to_text(raw: str) -> tuple[str, list[str]]:
    parser = ProseHTMLParser()
    parser.feed(raw)
    focused = normalize_text("".join(parser.focus_parts))
    all_text = normalize_text("".join(parser.all_parts))
    # Prefer semantic main/article only when it contains substantial Russian prose.
    text = focused if len(WORD_RE.findall(focused)) >= 100 and RUS_RE.search(focused) else all_text
    return text, parser.links


def word_count(text: str) -> int:
    return len(WORD_RE.findall(text))


def paragraph_count(text: str) -> int:
    return sum(1 for p in re.split(r"\n\s*\n", text) if word_count(p) >= 3)


def russian_share(text: str) -> float:
    letters = re.findall(r"[A-Za-zА-Яа-яЁё]", text)
    if not letters:
        return 0.0
    ru = sum(1 for ch in letters if RUS_RE.match(ch))
    return ru / len(letters)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def slug(value: str, max_len: int = 80) -> str:
    value = re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip("-.")
    return (value or "doc")[:max_len]


def request_headers(url: str, user_agent: str) -> dict[str, str]:
    headers = {"User-Agent": user_agent, "Accept": "*/*"}
    if urlparse(url).netloc.lower() == "api.github.com":
        token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
        if token:
            headers["Authorization"] = f"Bearer {token}"
            headers["Accept"] = "application/vnd.github+json"
    return headers


def fetch_bytes(url: str, *, timeout: float, user_agent: str, retries: int = 2) -> tuple[bytes, str]:
    last: Exception | None = None
    for attempt in range(retries + 1):
        try:
            req = Request(url, headers=request_headers(url, user_agent))
            with urlopen(req, timeout=timeout) as resp:
                return resp.read(), resp.geturl()
        except (HTTPError, URLError, TimeoutError, OSError) as exc:
            last = exc
            if attempt < retries:
                time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"fetch failed: {url}: {last}")


def fetch_text(url: str, *, timeout: float, user_agent: str) -> tuple[str, str]:
    data, final = fetch_bytes(url, timeout=timeout, user_agent=user_agent)
    # Most sources are UTF-8. A replacement decode is preferable to dropping a document.
    return data.decode("utf-8", errors="replace"), final


def write_document(out: Path, profile: str, source_id: str, doc_id: str, text: str) -> Path:
    folder = out / "raw" / profile / source_id
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{slug(doc_id)}.txt"
    # Collision-resistant suffix if a source reuses an identifier.
    if path.exists() and path.read_text(encoding="utf-8") != text:
        path = folder / f"{slug(doc_id)}-{sha256_text(text)[:10]}.txt"
    path.write_text(text.rstrip() + "\n", encoding="utf-8")
    return path


def make_row(*, path: Path, out: Path, profile: str, channel: str, source_id: str,
             doc_id: str, source_url: str, archive_url: str, independence_group: str,
             license_or_terms: str, redistribution: str, text: str, author: str = "",
             final_url: str = "", source_document_id: str = "", split_group: str = "") -> dict:
    return {
        "id": f"{source_id}:{doc_id}",
        "path": str(path.relative_to(out)),
        "profile": profile,
        "channel": channel,
        "source_id": source_id,
        "source_url": source_url,
        "archive_url": archive_url,
        "final_url": final_url,
        "author_or_group": author,
        "split_group": split_group,
        "source_document_id": source_document_id or doc_id,
        "independence_group": independence_group or source_document_id or doc_id,
        "license_or_terms": license_or_terms,
        "redistribution": redistribution,
        # Hash the decoded UTF-8 text written by write_document(), including
        # its canonical trailing newline. This matches the validator and is
        # independent of Windows CRLF byte translation.
        "sha256": sha256_text(path.read_text(encoding="utf-8")),
        "words": word_count(text),
        "paragraphs": paragraph_count(text),
        "russian_share": round(russian_share(text), 4),
        "calibration_eligible": "1",
        "lexical_only": "0",
    }


def eligible(text: str, source: dict) -> bool:
    return (
        word_count(text) >= int(source.get("minimum_words_per_document", 0))
        and paragraph_count(text) >= int(source.get("minimum_paragraphs_per_document", 1))
        and russian_share(text) >= 0.65
    )


def dedupe_append(row: dict, rows: list[dict], hashes: set[tuple[str, str]]) -> bool:
    # Exact duplicates must not inflate a source/profile target, but cross-profile
    # copies are retained so the validator can detect contradictory routing.
    key = (str(row.get("profile") or ""), row["sha256"])
    if key in hashes:
        return False
    hashes.add(key)
    rows.append(row)
    return True


def materialize_ljsearch(source: dict, out: Path, args, rows: list[dict], hashes: set[tuple[str, str]]) -> dict:
    saved: list[str] = list(source.get("seed_saved_copies", []))
    errors: list[str] = []
    # Search pages are discovery only; saved copies are the document source.
    for query in source.get("queries", []):
        url = source["search_url_template"].format(query=quote_plus(query))
        try:
            raw, _ = fetch_text(url, timeout=args.timeout, user_agent=args.user_agent)
            for m in LJ_SAVED_RE.finditer(raw):
                saved.append(f"https://ljsear.ch/savedcopy?post={m.group(1)}")
        except Exception as exc:
            errors.append(str(exc))
        time.sleep(args.delay)
    saved = list(dict.fromkeys(saved))
    accepted = 0
    target = args.target_docs or int(source.get("target_documents", 50))
    profile = source["profiles"][0]
    channel = source["channels"][0]
    for archive_url in saved:
        if accepted >= target:
            break
        post = LJ_SAVED_RE.search(archive_url)
        doc_id = post.group(1) if post else hashlib.sha1(archive_url.encode()).hexdigest()[:12]
        try:
            raw, final_url = fetch_text(archive_url, timeout=args.timeout, user_agent=args.user_agent)
            text, _ = html_to_text(raw)
            if not eligible(text, source):
                continue
            author_match = LJ_AUTHOR_RE.search(raw)
            author = author_match.group(1).lower() if author_match else ""
            original_match = re.search(r"https?://[A-Za-z0-9_-]+\.livejournal\.com/[^\"'<>\s]+", raw, re.I)
            original = html.unescape(original_match.group(0)) if original_match else ""
            path = write_document(out, profile, source["id"], doc_id, text)
            row = make_row(
                path=path, out=out, profile=profile, channel=channel, source_id=source["id"],
                doc_id=doc_id, source_url=original or source["source_url"], archive_url=archive_url,
                independence_group=f"lj-post-{doc_id}", license_or_terms=source.get("license_or_terms", ""), redistribution=source["redistribution"],
                text=text, author=author, final_url=final_url,
            )
            if dedupe_append(row, rows, hashes):
                accepted += 1
        except Exception as exc:
            errors.append(str(exc))
        time.sleep(args.delay)
    return {"source_id": source["id"], "discovered_savedcopies": len(saved), "accepted": accepted, "errors": errors[:20]}


def materialize_factrueval(source: dict, out: Path, args, rows: list[dict], hashes: set[tuple[str, str]]) -> dict:
    tree_url = "https://api.github.com/repos/dialogue-evaluation/factRuEval-2016/git/trees/master?recursive=1"
    errors: list[str] = []
    accepted = 0
    try:
        raw, _ = fetch_text(tree_url, timeout=args.timeout, user_agent=args.user_agent)
        tree = json.loads(raw).get("tree", [])
    except Exception as exc:
        return {"source_id": source["id"], "accepted": 0, "errors": [str(exc)]}
    paths = sorted(
        item["path"] for item in tree
        if item.get("type") == "blob" and re.fullmatch(r"(?:devset|testset)/book_\d+\.txt", item.get("path", ""))
    )
    target = args.target_docs or int(source.get("target_documents", 50))
    for repo_path in paths:
        if accepted >= target:
            break
        url = f"https://raw.githubusercontent.com/dialogue-evaluation/factRuEval-2016/master/{repo_path}"
        try:
            raw, final_url = fetch_text(url, timeout=args.timeout, user_agent=args.user_agent)
            text = normalize_text(raw)
            if not eligible(text, source):
                continue
            doc_id = repo_path.replace("/", "-").removesuffix(".txt")
            profile = source["profiles"][0]
            channel = source["channels"][0]
            path = write_document(out, profile, source["id"], doc_id, text)
            row = make_row(
                path=path, out=out, profile=profile, channel=channel, source_id=source["id"],
                doc_id=doc_id, source_url=url, archive_url="", independence_group=doc_id,
                license_or_terms=source.get("license_or_terms", ""), redistribution=source["redistribution"], text=text, final_url=final_url,
            )
            if dedupe_append(row, rows, hashes):
                accepted += 1
        except Exception as exc:
            errors.append(str(exc))
        time.sleep(args.delay)
    return {"source_id": source["id"], "candidates": len(paths), "accepted": accepted, "errors": errors[:20]}


def iter_json_texts(obj, prefix: str = "record") -> Iterator[tuple[str, str, str]]:
    """Yield (id, text, author/group) from loosely structured JSON."""
    if isinstance(obj, list):
        for i, item in enumerate(obj):
            yield from iter_json_texts(item, f"{prefix}-{i}")
        return
    if not isinstance(obj, dict):
        return
    text = ""
    for key in TEXT_FIELD_NAMES:
        value = obj.get(key)
        if isinstance(value, str) and word_count(value) > word_count(text):
            text = value
    if text:
        rid = str(obj.get("id") or obj.get("post_id") or obj.get("url") or prefix)
        author = str(obj.get("author") or obj.get("username") or obj.get("user") or obj.get("journal") or "")
        yield rid, normalize_text(text), author
        return
    for key, value in obj.items():
        if isinstance(value, (dict, list)):
            yield from iter_json_texts(value, f"{prefix}-{key}")


def markdown_to_text(raw: str) -> str:
    """Conservatively turn Markdown into prose while preserving source punctuation.

    This is acquisition normalization, not a style heuristic: YAML front matter,
    fenced code and pure include/template directives are excluded because they are
    not rendered prose. Link labels and headings are kept as text.
    """
    raw = raw.replace("\r\n", "\n").replace("\r", "\n")
    raw = re.sub(r"\A---\n.*?\n---\n", "", raw, flags=re.S)
    raw = re.sub(r"```.*?```", "\n", raw, flags=re.S)
    raw = re.sub(r"~~~.*?~~~", "\n", raw, flags=re.S)
    lines = []
    for line in raw.splitlines():
        stripped = line.strip()
        if re.fullmatch(r"\{[%{].*?[}%]\}", stripped):
            continue
        if re.fullmatch(r"\{%.*?%\}", stripped):
            continue
        # Preserve visible link text, drop destination URL.
        line = re.sub(r"!\[([^\]]*)\]\([^)]*\)", r"\1", line)
        line = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", line)
        line = re.sub(r"^\s{0,3}#{1,6}\s+", "", line)
        line = re.sub(r"^\s*>\s?", "", line)
        line = re.sub(r"^\s*[-*+]\s+", "", line)
        line = re.sub(r"^\s*\d+[.)]\s+", "", line)
        # Remove table separator rows, but retain prose cells as ordinary text.
        if re.fullmatch(r"\s*\|?\s*:?-{3,}:?\s*(?:\|\s*:?-{3,}:?\s*)+\|?\s*", line):
            continue
        if "|" in line and not re.search(r"https?://", line):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) > 1:
                line = ". ".join(c for c in cells if c)
        lines.append(line)
    return normalize_text("\n".join(lines))


def xml_to_text(raw: str) -> str:
    # Some speech corpora wrap editorial metadata (<meta>, <description>,
    # <introduction>) around the actual transcript. When an explicit <speech>
    # container exists, it is the natural document body for oral analysis.
    speech = re.search(r"<speech(?:\s[^>]*)?>(.*?)</speech\s*>", raw, flags=re.I | re.S)
    body = speech.group(1) if speech else raw
    raw2 = re.sub(r"</(?:p|text|post|entry|body|turn|utterance|s)\s*>", "\n\n", body, flags=re.I)
    raw2 = re.sub(r"<speaker[^>]*>", "\n", raw2, flags=re.I)
    return normalize_text(re.sub(r"<[^>]+>", " ", raw2))


def source_file_to_text(name: str, raw: str) -> str:
    suffix = Path(name).suffix.lower()
    if suffix in {".html", ".htm"}:
        return html_to_text(raw)[0]
    if suffix == ".xml":
        return xml_to_text(raw)
    if suffix in {".md", ".markdown"}:
        return markdown_to_text(raw)
    return normalize_text(raw)


def iter_zip_records(path: Path) -> Iterator[tuple[str, str, str]]:
    with zipfile.ZipFile(path) as zf:
        for info in sorted(zf.infolist(), key=lambda x: x.filename):
            if info.is_dir() or info.file_size > 250 * 1024 * 1024:
                continue
            suffix = Path(info.filename).suffix.lower()
            if suffix not in {".txt", ".md", ".markdown", ".json", ".jsonl", ".csv", ".tsv", ".xml", ".html", ".htm"}:
                continue
            data = zf.read(info)
            raw = data.decode("utf-8", errors="replace")
            stem = Path(info.filename).stem
            if suffix in {".html", ".htm", ".xml", ".md", ".markdown"}:
                yield stem, source_file_to_text(info.filename, raw), ""
            elif suffix == ".jsonl":
                for i, line in enumerate(raw.splitlines()):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        obj = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    yield from iter_json_texts(obj, f"{stem}-{i}")
            elif suffix == ".json":
                try:
                    obj = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                yield from iter_json_texts(obj, stem)
            elif suffix in {".csv", ".tsv"}:
                try:
                    reader = csv.DictReader(io.StringIO(raw), delimiter="\t" if suffix == ".tsv" else ",")
                    for i, record in enumerate(reader):
                        # Prefer an explicitly named prose field, then fall back to the longest cell.
                        best = ""
                        for key in TEXT_FIELD_NAMES:
                            if isinstance(record.get(key), str) and word_count(record[key]) > word_count(best):
                                best = record[key]
                        if not best:
                            best = max((v or "" for v in record.values()), key=word_count, default="")
                        if best:
                            rid = str(record.get("id") or record.get("post_id") or record.get("url") or f"{stem}-{i}")
                            author = str(record.get("author") or record.get("speaker") or record.get("user") or "")
                            yield rid, normalize_text(best), author
                except csv.Error:
                    continue
            else:
                # One member == one document. We deliberately do not split an arbitrary
                # long text into pseudo-documents.
                yield stem, normalize_text(raw), ""


def _zip_downloads(source: dict) -> list[tuple[str, str | None]]:
    """Return (url, expected_md5) pairs for one- or multi-part ZIP sources."""
    urls = source.get("download_urls")
    if urls:
        md5s = source.get("archive_md5s") or []
        return [(str(url), str(md5s[i]) if i < len(md5s) and md5s[i] else None) for i, url in enumerate(urls)]
    return [(str(source["download_url"]), source.get("archive_md5"))]


def materialize_zip_text_records(source: dict, out: Path, args, rows: list[dict], hashes: set[tuple[str, str]]) -> dict:
    cache = out / ".cache"
    cache.mkdir(parents=True, exist_ok=True)
    errors: list[str] = []
    accepted = 0
    scanned = 0
    target = args.target_docs or int(source.get("target_documents", 50))
    profile = source["profiles"][0]
    channel = source["channels"][0]
    downloads = _zip_downloads(source)

    for archive_index, (download_url, md5_expected) in enumerate(downloads):
        if accepted >= target:
            break
        suffix = "" if len(downloads) == 1 else f"-{archive_index:02d}"
        archive = cache / f"{source['id']}{suffix}.zip"
        if not archive.exists():
            try:
                data, _ = fetch_bytes(download_url, timeout=max(args.timeout, 120), user_agent=args.user_agent, retries=3)
                archive.write_bytes(data)
            except Exception as exc:
                errors.append(f"{download_url}: {exc}")
                continue
        if md5_expected:
            md5 = hashlib.md5(archive.read_bytes()).hexdigest()
            if md5.lower() != str(md5_expected).lower():
                errors.append(f"{download_url}: archive md5 mismatch: {md5}")
                continue
        try:
            for rid, text, author in iter_zip_records(archive):
                scanned += 1
                if accepted >= target:
                    break
                if not eligible(text, source):
                    continue
                # Archive index is part of the provenance identifier so equal member
                # names in separate upstream ZIP parts cannot collide. Exact text
                # duplicates are still removed by sha256 below and by the validator.
                rid_scoped = f"a{archive_index}-{rid}" if len(downloads) > 1 else str(rid)
                doc_id = slug(rid_scoped) + "-" + sha256_text(text)[:10]
                path = write_document(out, profile, source["id"], doc_id, text)
                row = make_row(
                    path=path, out=out, profile=profile, channel=channel, source_id=source["id"],
                    doc_id=doc_id, source_url=source["source_url"], archive_url=download_url,
                    independence_group=f"{source['id']}:{rid_scoped}",
                    license_or_terms=source.get("license_or_terms", ""), redistribution=source["redistribution"],
                    text=text, author=author,
                )
                if dedupe_append(row, rows, hashes):
                    accepted += 1
        except Exception as exc:
            errors.append(f"{archive}: {exc}")
    return {
        "source_id": source["id"], "archives": len(downloads), "records_scanned": scanned,
        "accepted": accepted, "errors": errors[:20],
    }


def materialize_github_tree_text(source: dict, out: Path, args, rows: list[dict], hashes: set[tuple[str, str]]) -> dict:
    repo = source["repository"]
    ref = source.get("ref", "main")
    path_re = re.compile(source["path_regex"])
    tree_url = f"https://api.github.com/repos/{repo}/git/trees/{ref}?recursive=1"
    errors: list[str] = []
    try:
        raw, _ = fetch_text(tree_url, timeout=args.timeout, user_agent=args.user_agent)
        tree = json.loads(raw).get("tree", [])
    except Exception as exc:
        return {"source_id": source["id"], "accepted": 0, "errors": [str(exc)]}
    paths = sorted(
        item["path"] for item in tree
        if item.get("type") == "blob" and path_re.search(item.get("path", ""))
    )
    target = args.target_docs or int(source.get("target_documents", 50))
    profile = source["profiles"][0]
    channel = source["channels"][0]
    accepted = 0
    scanned = 0
    for repo_path in paths:
        if accepted >= target:
            break
        scanned += 1
        safe_path = "/".join(quote(part, safe="") for part in repo_path.split("/"))
        url = f"https://raw.githubusercontent.com/{repo}/{ref}/{safe_path}"
        try:
            raw_text, final_url = fetch_text(url, timeout=args.timeout, user_agent=args.user_agent)
            text = source_file_to_text(repo_path, raw_text)
            if not eligible(text, source):
                continue
            doc_id = slug(repo_path.replace("/", "-").rsplit(".", 1)[0]) + "-" + sha256_text(text)[:10]
            path = write_document(out, profile, source["id"], doc_id, text)
            row = make_row(
                path=path, out=out, profile=profile, channel=channel, source_id=source["id"],
                doc_id=doc_id,
                source_url=f"https://github.com/{repo}/blob/{ref}/{repo_path}",
                archive_url="", independence_group=repo_path,
                license_or_terms=source.get("license_or_terms", ""), redistribution=source["redistribution"],
                text=text, author=source.get("author_or_group", ""), final_url=final_url,
            )
            if dedupe_append(row, rows, hashes):
                accepted += 1
        except Exception as exc:
            errors.append(f"{repo_path}: {exc}")
        time.sleep(args.delay)
    return {"source_id": source["id"], "candidates": len(paths), "records_scanned": scanned, "accepted": accepted, "errors": errors[:20]}


def discover_index_urls(source: dict, args) -> tuple[list[str], list[str]]:
    host = urlparse(source["source_url"]).netloc
    article_re = re.compile(source.get("article_path_regex", r"$^"))
    crawl_re = re.compile(source.get("crawl_path_regex", r"$^"))
    queue = [source["source_url"]]
    seen_pages: set[str] = set()
    articles: list[str] = list(source.get("seed_urls", []))
    errors: list[str] = []
    while queue and len(seen_pages) < args.max_index_pages:
        url = queue.pop(0)
        if url in seen_pages:
            continue
        seen_pages.add(url)
        try:
            raw, final = fetch_text(url, timeout=args.timeout, user_agent=args.user_agent)
            _, links = html_to_text(raw)
            for href in links:
                abs_url = urljoin(final, href)
                parsed = urlparse(abs_url)
                if parsed.netloc != host:
                    continue
                clean = parsed._replace(fragment="").geturl()
                if article_re.search(parsed.path):
                    articles.append(clean)
                elif crawl_re.search(parsed.path) and clean not in seen_pages and clean not in queue:
                    queue.append(clean)
        except Exception as exc:
            errors.append(str(exc))
        time.sleep(args.delay)
    return list(dict.fromkeys(articles)), errors


def materialize_web_index(source: dict, out: Path, args, rows: list[dict], hashes: set[tuple[str, str]]) -> dict:
    urls, errors = discover_index_urls(source, args)
    accepted = 0
    target = args.target_docs or int(source.get("target_documents", 50))
    profile = source["profiles"][0]
    channel = source["channels"][0]
    for url in urls:
        if accepted >= target:
            break
        try:
            raw, final = fetch_text(url, timeout=args.timeout, user_agent=args.user_agent)
            text, _ = html_to_text(raw)
            if not eligible(text, source):
                continue
            parsed = urlparse(final)
            base_id = slug(parsed.path.strip("/").replace("/", "-")) or "page"
            # Some publishers route every article through one path (for
            # example /news) and put the real document identity in the query.
            # Include the requested URL so distinct articles cannot collapse
            # to a duplicate manifest id.
            doc_id = f"{base_id}-{hashlib.sha1(url.encode()).hexdigest()[:12]}"
            # Publisher/agency extraction is deliberately conservative. If unknown,
            # source+doc remains independent but validator reports concentration.
            path = write_document(out, profile, source["id"], doc_id, text)
            row = make_row(
                path=path, out=out, profile=profile, channel=channel, source_id=source["id"],
                doc_id=doc_id, source_url=url, archive_url="", independence_group=doc_id,
                license_or_terms=source.get("license_or_terms", ""), redistribution=source["redistribution"], text=text, final_url=final,
            )
            if dedupe_append(row, rows, hashes):
                accepted += 1
        except Exception as exc:
            errors.append(str(exc))
        time.sleep(args.delay)
    return {"source_id": source["id"], "urls_discovered": len(urls), "accepted": accepted, "errors": errors[:20]}


def materialize_huggingface_stream(source: dict, out: Path, args, rows: list[dict], hashes: set[tuple[str, str]]) -> dict:
    try:
        from datasets import load_dataset  # type: ignore
    except Exception:
        return {"source_id": source["id"], "accepted": 0, "errors": ["optional dependency 'datasets' is not installed"]}
    errors: list[str] = []
    accepted = 0
    target = args.target_docs or int(source.get("target_documents", 50))
    profile = source["profiles"][0]
    channel = source["channels"][0]
    try:
        ds = load_dataset(source["dataset_id"], split="train", streaming=True)
        for i, obj in enumerate(ds):
            if accepted >= target:
                break
            candidates = list(iter_json_texts(obj, f"row-{i}"))
            if not candidates:
                continue
            rid, text, author = max(candidates, key=lambda x: word_count(x[1]))
            if not eligible(text, source):
                continue
            doc_id = slug(str(rid)) + "-" + sha256_text(text)[:10]
            path = write_document(out, profile, source["id"], doc_id, text)
            row = make_row(
                path=path, out=out, profile=profile, channel=channel, source_id=source["id"],
                doc_id=doc_id, source_url=source["source_url"], archive_url=source.get("dataset_url", ""),
                independence_group=doc_id, license_or_terms=source.get("license_or_terms", ""), redistribution=source["redistribution"],
                text=text, author=author,
            )
            if dedupe_append(row, rows, hashes):
                accepted += 1
    except Exception as exc:
        errors.append(str(exc))
    return {"source_id": source["id"], "accepted": accepted, "errors": errors[:20]}


def import_local_tree(source: dict, local_root: Path, out: Path, args, rows: list[dict], hashes: set[tuple[str, str]]) -> dict:
    """Import naturally bounded local documents, optionally with provenance sidecar.

    If ``local_root/manifest.csv`` exists, each row names one document via
    ``path`` and may provide ``id``, ``author_or_group``, ``split_group``,
    ``source_document_id``, ``independence_group`` and ``channel``.  This is the
    preferred route for corpora where author/speaker identity matters for
    leakage/diversity gates.  Without a sidecar, the historical one-*.txt-file
    == one-document import remains available but does not invent author data.
    """
    errors: list[str] = []
    accepted = 0
    target = args.target_docs or int(source.get("target_documents", 50))
    profile = source["profiles"][0]
    default_channel = source["channels"][0]
    declared_channels = set(source.get("channels", []))
    local_root = local_root.resolve()
    sidecar = local_root / "manifest.csv"

    candidates: list[dict] = []
    if sidecar.exists():
        try:
            with sidecar.open(encoding="utf-8", newline="") as fh:
                reader = csv.DictReader(fh)
                if not reader.fieldnames or "path" not in reader.fieldnames:
                    return {"source_id": source["id"], "accepted": 0, "errors": ["local manifest.csv must contain path"], "sidecar_used": True}
                seen_local_ids: set[str] = set()
                for line_no, meta in enumerate(reader, start=2):
                    rel = (meta.get("path") or "").strip()
                    if not rel:
                        errors.append(f"manifest.csv row {line_no}: path is required")
                        continue
                    candidate = (local_root / rel).resolve()
                    try:
                        candidate.relative_to(local_root)
                    except ValueError:
                        errors.append(f"manifest.csv row {line_no}: path escapes local root: {rel}")
                        continue
                    local_id = (meta.get("id") or meta.get("source_document_id") or rel).strip()
                    if not local_id:
                        errors.append(f"manifest.csv row {line_no}: id/source_document_id is required")
                        continue
                    if local_id in seen_local_ids:
                        errors.append(f"manifest.csv row {line_no}: duplicate local id: {local_id}")
                        continue
                    seen_local_ids.add(local_id)
                    channel = (meta.get("channel") or default_channel).strip()
                    if channel not in declared_channels:
                        errors.append(f"manifest.csv row {line_no}: undeclared channel {channel!r}")
                        continue
                    candidates.append({
                        "path": candidate,
                        "local_id": local_id,
                        "channel": channel,
                        "author": (meta.get("author_or_group") or "").strip(),
                        "split_group": (meta.get("split_group") or "").strip(),
                        "source_document_id": (meta.get("source_document_id") or local_id).strip(),
                        "independence_group": (meta.get("independence_group") or meta.get("source_document_id") or local_id).strip(),
                    })
        except Exception as exc:
            return {"source_id": source["id"], "accepted": 0, "errors": [f"local manifest.csv: {exc}"], "sidecar_used": True}
    else:
        candidates = [
            {
                "path": p.resolve(), "local_id": str(p.relative_to(local_root)),
                "channel": default_channel, "author": "", "split_group": "",
                "source_document_id": str(p.relative_to(local_root)),
                "independence_group": str(p.relative_to(local_root)),
            }
            for p in sorted(local_root.rglob("*.txt"))
        ]

    for meta in candidates:
        if accepted >= target:
            break
        p = meta["path"]
        if not p.exists() or not p.is_file():
            errors.append(f"missing local document: {p}")
            continue
        try:
            raw = p.read_text(encoding="utf-8", errors="strict")
            text = source_file_to_text(p.name, raw)
        except Exception as exc:
            errors.append(f"{p}: {exc}")
            continue
        if not eligible(text, source):
            continue
        local_id = str(meta["local_id"])
        doc_id = slug(local_id) + "-" + sha256_text(text)[:10]
        dest = write_document(out, profile, source["id"], doc_id, text)
        row = make_row(
            path=dest, out=out, profile=profile, channel=str(meta["channel"]), source_id=source["id"],
            doc_id=doc_id, source_url=source["source_url"], archive_url="",
            independence_group=str(meta["independence_group"]), license_or_terms=source.get("license_or_terms", ""),
            redistribution=source["redistribution"], text=text, author=str(meta["author"]),
            source_document_id=str(meta["source_document_id"]), split_group=str(meta["split_group"]),
        )
        if dedupe_append(row, rows, hashes):
            accepted += 1
    return {"source_id": source["id"], "accepted": accepted, "errors": errors[:20], "sidecar_used": sidecar.exists()}


def write_manifest(out: Path, rows: list[dict]) -> None:
    columns = [
        "id", "path", "profile", "channel", "source_id", "source_url", "archive_url", "final_url",
        "author_or_group", "split_group", "source_document_id", "independence_group", "license_or_terms", "redistribution", "sha256", "words", "paragraphs",
        "russian_share", "calibration_eligible", "lexical_only",
    ]
    with (out / "manifest.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=columns)
        w.writeheader()
        w.writerows(rows)


def main() -> int:
    ap = argparse.ArgumentParser(description="Materialize external held-out corpus into a local research directory")
    ap.add_argument("--registry", type=Path, default=REGISTRY)
    ap.add_argument("--sources", nargs="+", required=True)
    ap.add_argument("--output-dir", type=Path, required=True)
    ap.add_argument("--local-source", action="append", default=[], metavar="SOURCE_ID=PATH",
                    help="Import an already downloaded local text tree for manual_or_local_tree sources")
    ap.add_argument("--local-corpus-root", type=Path, default=DEFAULT_LOCAL_CORPUS_ROOT,
                    help="Auto-discover SOURCE_ID/manifest.csv trees here (default: data or HUMAN_WRITING_RU_DATA_DIR)")
    ap.add_argument("--no-auto-local-sources", action="store_true",
                    help="Disable local corpus auto-discovery")
    ap.add_argument("--target-docs", type=int, default=0, help="Override per-source target (testing/small runs)")
    ap.add_argument("--timeout", type=float, default=30.0)
    ap.add_argument("--delay", type=float, default=0.35, help="Polite delay between web requests")
    ap.add_argument("--max-index-pages", type=int, default=12)
    ap.add_argument("--allow-unverified-format", action="store_true",
                    help="Research-only override for sources explicitly marked format_unverified; network decision runner never enables this")
    package_version = (ROOT / "VERSION").read_text(encoding="utf-8").strip() if (ROOT / "VERSION").exists() else "unknown"
    ap.add_argument("--user-agent", default=f"human-writing-ru-heldout/{package_version} research benchmark (+source links in package)")
    args = ap.parse_args()
    if args.target_docs < 0:
        ap.error("--target-docs must be >= 0")
    args.target_docs = args.target_docs or None

    registry = json.loads(args.registry.read_text(encoding="utf-8"))
    sources = {s["id"]: s for s in registry["sources"]}
    unknown = [s for s in args.sources if s not in sources]
    if unknown:
        ap.error(f"unknown source ids: {', '.join(unknown)}")
    unverified = [
        sid for sid in args.sources
        if "format_unverified" in str(sources[sid].get("status", ""))
    ]
    if unverified and not args.allow_unverified_format:
        ap.error(
            "refusing format-unverified source(s) for benchmark materialization: "
            + ", ".join(unverified)
            + "; verify document boundaries first or use --allow-unverified-format for research-only inspection"
        )
    local_map: dict[str, Path] = {}
    for item in args.local_source:
        if "=" not in item:
            ap.error("--local-source must be SOURCE_ID=PATH")
        sid, path = item.split("=", 1)
        local_map[sid] = Path(path).expanduser().resolve()
    if not args.no_auto_local_sources:
        local_root = args.local_corpus_root.expanduser().resolve()
        for sid in args.sources:
            candidate = local_root / sid
            if (
                sources[sid].get("adapter") == "manual_or_local_tree"
                and sid not in local_map
                and (candidate / "manifest.csv").is_file()
            ):
                local_map[sid] = candidate
    invalid_local = [f"{sid}={path}" for sid, path in local_map.items() if not (path / "manifest.csv").is_file()]
    if invalid_local:
        ap.error("local corpus path must contain manifest.csv: " + ", ".join(invalid_local))

    out = args.output_dir.resolve()
    out.mkdir(parents=True, exist_ok=True)
    rows: list[dict] = []
    hashes: set[tuple[str, str]] = set()
    # Resume from prior manifest without silently changing already selected documents.
    manifest_path = out / "manifest.csv"
    if manifest_path.exists():
        with manifest_path.open(encoding="utf-8", newline="") as fh:
            for row in csv.DictReader(fh):
                p = out / row["path"]
                if p.exists():
                    rows.append(row)
                    if row.get("sha256"):
                        hashes.add(((row.get("profile") or "").strip(), row["sha256"]))

    reports = []
    for sid in args.sources:
        source = sources[sid]
        adapter = source["adapter"]
        before = len(rows)
        if adapter == "ljsearch":
            rep = materialize_ljsearch(source, out, args, rows, hashes)
        elif adapter == "factrueval_github":
            rep = materialize_factrueval(source, out, args, rows, hashes)
        elif adapter == "zip_text_records":
            rep = materialize_zip_text_records(source, out, args, rows, hashes)
        elif adapter == "web_index":
            rep = materialize_web_index(source, out, args, rows, hashes)
        elif adapter == "huggingface_stream":
            rep = materialize_huggingface_stream(source, out, args, rows, hashes)
        elif adapter == "github_tree_text":
            rep = materialize_github_tree_text(source, out, args, rows, hashes)
        elif adapter == "manual_or_local_tree":
            if sid not in local_map:
                rep = {"source_id": sid, "accepted": 0, "errors": ["requires --local-source SOURCE_ID=PATH"]}
            else:
                rep = import_local_tree(source, local_map[sid], out, args, rows, hashes)
        else:
            rep = {"source_id": sid, "accepted": 0, "errors": [f"adapter {adapter!r} is reference/manual only"]}
        rep["new_manifest_rows"] = len(rows) - before
        reports.append(rep)
        print(f"{sid}: +{len(rows) - before} docs")
        write_manifest(out, rows)

    error_count = sum(len(rep.get("errors", [])) for rep in reports)
    if error_count and not rows:
        status = "materialization_failed_no_documents"
        exit_code = 2
    elif error_count:
        status = "materialization_partial_with_errors"
        exit_code = 1
    else:
        status = "materialized_local_research_data"
        exit_code = 0
    report = {
        "schema_version": 1,
        "status": status,
        "registry": str(args.registry),
        "output_dir": str(out),
        "documents_total": len(rows),
        "words_total": sum(int(r.get("words") or 0) for r in rows),
        "error_count": error_count,
        "sources": reports,
        "release_warning": "Do not package raw/ automatically. Review each source license/terms; package manifests, links, hashes and aggregates by default.",
    }
    (out / "MATERIALIZATION_REPORT.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
