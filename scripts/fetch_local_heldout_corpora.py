#!/usr/bin/env python3
"""Download and prepare the manual/local held-out corpora under examples/.

Raw third-party archives and prepared text samples stay local and are excluded
from Git and release packages.  Each prepared source gets a manifest.csv with
natural document boundaries and only provenance present in the upstream data.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import heapq
import html
import io
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tarfile
import tempfile
import time
from typing import Iterable, Iterator
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import zipfile

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EXAMPLES = ROOT / "examples"
USER_AGENT = "human-writing-ru local held-out corpus fetcher"

TAIGA_PUBLIC_URL = "https://yadi.sk/d/1eM_U29k3URn3v"
TAIGA_API = "https://cloud-api.yandex.net/v1/disk/public/resources"
TAIGA_SHA256 = "68d75f009d473761cc29edcfc4bb4eae51601a4f454082ccbf1f6452231d9376"
TAIGA_MEMBERS = {
    "home/tsha/social/texts/fbtexts.txt": 40,
    "home/tsha/social/texts/vktexts.txt": 40,
}

DUMA_URL = (
    "https://discuss-data.net/dataset/"
    "fb52dac2-66e3-47a3-86c5-b2a3dadf41bf/files/"
    "b6a693ce-0586-4e2f-a71c-df79e582ee19/"
)
DUMA_SHA256 = "0fb9272a8390fe6645274fc85f6ab2ce4bee694998c9185ab9fec24fc77aca20"
DUMA_SOURCE_URL = "https://doi.org/10.48320/FB52DAC2-66E3-47A3-86C5-B2A3DADF41BF"

PRAVO_BASE = "http://publication.pravo.gov.ru"
PRAVO_SOURCE_URL = "https://publication.pravo.gov.ru/OpenData"

WORD_RE = re.compile(r"[А-Яа-яЁёA-Za-z]+(?:[-'][А-Яа-яЁёA-Za-z]+)*")
RUS_RE = re.compile(r"[А-Яа-яЁё]")
TAIGA_MARKER_RE = re.compile(r"^DataBaseItem:\s*(\S+)\s*$")
MANIFEST_FIELDS = [
    "id", "path", "author_or_group", "split_group",
    "source_document_id", "independence_group", "channel",
]


def normalize_text(text: str) -> str:
    text = html.unescape(text).replace("\r\n", "\n").replace("\r", "\n").replace("\xa0", " ")
    lines: list[str] = []
    for line in text.splitlines():
        line = re.sub(r"[\t \f\v]+", " ", line).strip()
        if line:
            lines.append(line)
        elif lines and lines[-1] != "":
            lines.append("")
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()


def word_count(text: str) -> int:
    return len(WORD_RE.findall(text))


def paragraph_count(text: str) -> int:
    return sum(1 for part in re.split(r"\n\s*\n", text) if word_count(part) >= 3)


def russian_share(text: str) -> float:
    letters = re.findall(r"[A-Za-zА-Яа-яЁё]", text)
    return (sum(bool(RUS_RE.match(ch)) for ch in letters) / len(letters)) if letters else 0.0


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fetch_json(url: str, timeout: float, retries: int = 4) -> dict:
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        request = Request(url, headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
            "Connection": "close",
        })
        try:
            with urlopen(request, timeout=timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except (OSError, TimeoutError, ConnectionError) as exc:
            last_error = exc
            if attempt < retries:
                time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"JSON request failed after {retries + 1} attempts: {url}: {last_error}")


def download(
    url: str, destination: Path, timeout: float, expected_sha256: str | None = None, retries: int = 4
) -> Path:
    if destination.exists() and (expected_sha256 is None or sha256_file(destination) == expected_sha256):
        print(f"reuse {destination}")
        return destination
    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_suffix(destination.suffix + ".part")
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        offset = partial.stat().st_size if partial.exists() else 0
        headers = {"User-Agent": USER_AGENT, "Accept": "*/*", "Connection": "close"}
        if offset:
            headers["Range"] = f"bytes={offset}-"
        request = Request(url, headers=headers)
        try:
            with urlopen(request, timeout=timeout) as response:
                append = offset > 0 and getattr(response, "status", None) == 206
                mode = "ab" if append else "wb"
                if not append:
                    offset = 0
                total = response.headers.get("Content-Length")
                expected_size = offset + int(total) if total and total.isdigit() else None
                last_report = time.monotonic()
                with partial.open(mode) as out:
                    while True:
                        chunk = response.read(1024 * 1024)
                        if not chunk:
                            break
                        out.write(chunk)
                        if time.monotonic() - last_report >= 10:
                            size = out.tell()
                            suffix = f"/{expected_size}" if expected_size else ""
                            print(f"download {destination.name}: {size}{suffix} bytes", flush=True)
                            last_report = time.monotonic()
            break
        except (OSError, TimeoutError, ConnectionError) as exc:
            last_error = exc
            if attempt >= retries:
                raise RuntimeError(f"download failed after {retries + 1} attempts: {url}: {last_error}") from exc
            print(f"retry download {destination.name}: {exc}", flush=True)
            time.sleep(1.5 * (attempt + 1))
    partial.replace(destination)
    actual = sha256_file(destination)
    if expected_sha256 and actual != expected_sha256:
        raise RuntimeError(f"checksum mismatch for {destination}: expected {expected_sha256}, got {actual}")
    return destination


def write_prepared(root: Path, records: Iterable[dict], provenance: dict) -> dict:
    documents = root / "documents"
    if documents.exists():
        shutil.rmtree(documents)
    documents.mkdir(parents=True, exist_ok=True)
    rows: list[dict] = []
    total_words = 0
    for record in records:
        document_id = str(record["id"])
        filename = re.sub(r"[^A-Za-z0-9._-]+", "-", document_id).strip("-.")[:120] or "document"
        path = documents / f"{filename}.txt"
        text = normalize_text(str(record["text"]))
        path.write_text(text + "\n", encoding="utf-8")
        total_words += word_count(text)
        rows.append({
            "id": document_id,
            "path": path.relative_to(root).as_posix(),
            "author_or_group": record.get("author_or_group", ""),
            "split_group": record.get("split_group", ""),
            "source_document_id": record.get("source_document_id", document_id),
            "independence_group": record.get("independence_group", document_id),
            "channel": record["channel"],
        })
    with (root / "manifest.csv").open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=MANIFEST_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    provenance = {**provenance, "documents": len(rows), "words": total_words}
    (root / "provenance.json").write_text(
        json.dumps(provenance, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return provenance


def bounded_by_hash(records: Iterable[tuple[str, str]], limit: int) -> list[tuple[str, str]]:
    heap: list[tuple[int, str, str]] = []
    for document_id, text in records:
        score = int(hashlib.sha256(document_id.encode("utf-8")).hexdigest(), 16)
        item = (-score, document_id, text)
        if len(heap) < limit:
            heapq.heappush(heap, item)
        elif score < -heap[0][0]:
            heapq.heapreplace(heap, item)
    return [(document_id, text) for _, document_id, text in sorted(heap, key=lambda x: (-x[0], x[1]))]


def iter_taiga_records(stream: Iterable[str]) -> Iterator[tuple[str, str]]:
    document_id: str | None = None
    lines: list[str] = []
    for line in stream:
        marker = TAIGA_MARKER_RE.match(line.rstrip("\r\n"))
        if marker:
            if document_id is not None:
                yield document_id, normalize_text("".join(lines))
            document_id = marker.group(1)
            lines = []
        elif document_id is not None:
            lines.append(line)
    if document_id is not None:
        yield document_id, normalize_text("".join(lines))


def prepare_taiga(archive: Path, examples: Path) -> dict:
    prepared: list[dict] = []
    with tarfile.open(archive, "r:gz") as tf:
        for member_name, quota in TAIGA_MEMBERS.items():
            member = tf.getmember(member_name)
            raw = tf.extractfile(member)
            if raw is None:
                raise RuntimeError(f"missing Taiga member: {member_name}")
            import codecs
            stream = codecs.getreader("utf-8")(raw, errors="strict")
            candidates = (
                (document_id, text)
                for document_id, text in iter_taiga_records(stream)
                if word_count(text) >= 190 and russian_share(text) >= 0.65
            )
            platform = Path(member_name).stem.replace("texts", "") or "social"
            for document_id, text in bounded_by_hash(candidates, quota):
                prepared.append({
                    "id": f"{platform}-{document_id}",
                    "text": text,
                    "channel": "social",
                    "source_document_id": document_id,
                    "independence_group": document_id,
                })
    if len(prepared) < 80:
        raise RuntimeError(f"Taiga preparation produced only {len(prepared)} documents")
    return write_prepared(examples / "taiga_social", prepared, {
        "source_id": "taiga_social",
        "source_url": TAIGA_PUBLIC_URL,
        "archive": str(archive),
        "archive_sha256": sha256_file(archive),
        "selection": "40 deterministic hash-ranked natural records each from Facebook and VK; no author inferred",
    })


def prepare_duma(archive: Path, examples: Path) -> dict:
    try:
        import pyarrow.parquet as parquet
    except ImportError as exc:
        raise RuntimeError("Duma preparation requires pyarrow (installed by the datasets dependency)") from exc
    pool: list[dict] = []
    with zipfile.ZipFile(archive) as zf:
        names = sorted(
            (name for name in zf.namelist() if name.endswith(".parquet.gzip")),
            key=lambda name: int(re.search(r"(\d{4})", name).group(1)),
        )
        for name in names:
            table = parquet.read_table(
                io.BytesIO(zf.read(name)),
                columns=["deputy_id", "name", "date", "meeting_number", "start_line", "end_line", "text", "year"],
            )
            candidates: list[tuple[str, str, dict]] = []
            for row in table.to_pylist():
                text = normalize_text(str(row.get("text") or ""))
                author = str(row.get("name") or "").strip()
                if not author or word_count(text) < 400 or russian_share(text) < 0.65:
                    continue
                date = str(row.get("date") or "")[:10]
                document_id = (
                    f"{row.get('year')}-{row.get('meeting_number')}-"
                    f"{row.get('start_line')}-{row.get('end_line')}-{row.get('deputy_id')}"
                )
                score = hashlib.sha256(document_id.encode("utf-8")).hexdigest()
                candidates.append((score, document_id, {
                    "id": document_id,
                    "text": text,
                    "author_or_group": author,
                    "split_group": f"meeting-{date}-{row.get('meeting_number')}",
                    "source_document_id": document_id,
                    "independence_group": document_id,
                    "channel": "parliamentary_speech",
                    "year": int(row.get("year") or 0),
                }))
            pool.extend(record for _, _, record in sorted(candidates)[:24])
    selected: list[dict] = []
    selected_ids: set[str] = set()
    author_counts: dict[str, int] = {}
    year_counts: dict[int, int] = {}
    for author_cap in (1, 2, 3, 5):
        for record in sorted(pool, key=lambda r: hashlib.sha256(str(r["id"]).encode()).hexdigest()):
            if len(selected) >= 100:
                break
            if record["id"] in selected_ids:
                continue
            author = str(record["author_or_group"])
            year = int(record["year"])
            if author_counts.get(author, 0) >= author_cap or year_counts.get(year, 0) >= 5:
                continue
            selected.append(record)
            selected_ids.add(str(record["id"]))
            author_counts[author] = author_counts.get(author, 0) + 1
            year_counts[year] = year_counts.get(year, 0) + 1
    if len(selected) < 100:
        raise RuntimeError(f"Duma preparation produced only {len(selected)} documents")
    for record in selected:
        record.pop("year", None)
    return write_prepared(examples / "duma_speeches_1994_2021", selected, {
        "source_id": "duma_speeches_1994_2021",
        "source_url": DUMA_SOURCE_URL,
        "archive_url": DUMA_URL,
        "archive": str(archive),
        "archive_sha256": sha256_file(archive),
        "license": "Open Data Commons Attribution License (ODC-By) v1.0",
        "selection": "100 deterministic natural speech records, at least 400 words, capped by year and speaker",
    })


def find_pdftoppm() -> Path:
    configured = os.environ.get("PDFTOPPM_CMD")
    candidates = [Path(configured)] if configured else []
    found = shutil.which("pdftoppm.exe") or shutil.which("pdftoppm")
    if found:
        candidates.append(Path(found))
        wrapper = Path(found)
        if wrapper.suffix.lower() == ".cmd" and wrapper.parent.name == "override":
            candidates.append(wrapper.parents[2] / "native" / "poppler" / "Library" / "bin" / "pdftoppm.exe")
    for candidate in candidates:
        if candidate.is_file() and candidate.suffix.lower() == ".exe":
            return candidate.resolve()
    raise RuntimeError("PDF OCR requires pdftoppm; install Poppler or set PDFTOPPM_CMD")


def find_tesseract(examples: Path) -> Path:
    configured = os.environ.get("TESSERACT_CMD")
    candidates = [Path(configured)] if configured else []
    candidates.append(examples / "_tools" / "tesseract" / "tesseract.exe")
    found = shutil.which("tesseract.exe") or shutil.which("tesseract")
    if found:
        candidates.append(Path(found))
    for candidate in candidates:
        if candidate.is_file():
            return candidate.resolve()
    raise RuntimeError("image-only Pravo PDFs require Tesseract OCR with Russian data; set TESSERACT_CMD")


def extract_pdf_text(path: Path, examples: Path, max_pages: int = 12) -> tuple[str, str]:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise RuntimeError("Pravo preparation requires pypdf") from exc
    reader = PdfReader(path)
    pages = [normalize_text(page.extract_text() or "") for page in reader.pages]
    embedded = "\n\n".join(page for page in pages if page)
    if word_count(embedded) >= 100:
        return embedded, "embedded-text"
    pdftoppm = find_pdftoppm()
    tesseract = find_tesseract(examples)
    with tempfile.TemporaryDirectory(prefix="human-writing-ru-ocr-") as td:
        base = Path(td)
        prefix = base / "page"
        rendered = subprocess.run(
            [str(pdftoppm), "-f", "1", "-l", str(min(len(reader.pages), max_pages)),
             "-r", "180", "-png", str(path), str(prefix)],
            text=True, capture_output=True, timeout=180,
        )
        if rendered.returncode:
            raise RuntimeError(f"pdftoppm failed: {rendered.stderr[-1000:]}")
        ocr_pages: list[str] = []
        for image in sorted(base.glob("page-*.png"), key=lambda item: int(item.stem.rsplit("-", 1)[1])):
            recognized = subprocess.run(
                [str(tesseract), str(image), "stdout", "-l", "rus", "--psm", "6"],
                text=True, capture_output=True, timeout=180, encoding="utf-8", errors="replace",
            )
            if recognized.returncode:
                raise RuntimeError(f"tesseract failed: {recognized.stderr[-1000:]}")
            text = normalize_text(recognized.stdout)
            if text:
                ocr_pages.append(text)
        return "\n\n".join(ocr_pages), "tesseract-rus"


def prepare_pravo(examples: Path, downloads: Path, timeout: float) -> dict:
    pdf_root = downloads / "pravo-pdf"
    pdf_root.mkdir(parents=True, exist_ok=True)
    selected: list[dict] = []
    authority_counts: dict[str, int] = {}
    extraction_counts: dict[str, int] = {}
    seen: set[str] = set()
    for page in range(1, 13):
        query = urlencode({
            "PeriodType": "monthly", "PageSize": 200, "Index": page,
            "SortedBy": 4, "SortDestination": 1,
        })
        listing = fetch_json(f"{PRAVO_BASE}/api/Documents?{query}", timeout)
        items = listing.get("items") or []
        if not items:
            break
        for item in items:
            if len(selected) >= 50:
                break
            eo_number = str(item.get("eoNumber") or "")
            pages_count = int(item.get("pagesCount") or 0)
            if not eo_number or eo_number in seen or pages_count < 3 or pages_count > 12:
                continue
            seen.add(eo_number)
            detail = fetch_json(f"{PRAVO_BASE}/api/Document?{urlencode({'eoNumber': eo_number})}", timeout)
            authorities = detail.get("signatoryAuthorities") or []
            main = next((a for a in authorities if a.get("isMain")), authorities[0] if authorities else {})
            author = str(main.get("name") or item.get("signatoryAuthorityId") or "").strip()
            if not author or authority_counts.get(author, 0) >= 5:
                continue
            pdf_path = download(
                f"{PRAVO_BASE}/File/Pdf?{urlencode({'eoNumber': eo_number})}",
                pdf_root / f"{eo_number}.pdf", timeout,
            )
            try:
                text, extraction = extract_pdf_text(pdf_path, examples)
            except Exception as exc:
                print(f"skip {eo_number}: PDF text extraction failed: {exc}")
                continue
            if word_count(text) < 400 or paragraph_count(text) < 3 or russian_share(text) < 0.65:
                continue
            selected.append({
                "id": eo_number,
                "text": text,
                "author_or_group": author,
                "split_group": f"authority-{main.get('id') or item.get('signatoryAuthorityId')}",
                "source_document_id": eo_number,
                "independence_group": eo_number,
                "channel": "legal",
            })
            authority_counts[author] = authority_counts.get(author, 0) + 1
            extraction_counts[extraction] = extraction_counts.get(extraction, 0) + 1
            print(f"pravo: accepted {len(selected)}/50 {eo_number} ({extraction})", flush=True)
        if len(selected) >= 50:
            break
    if len(selected) < 50:
        raise RuntimeError(f"Pravo preparation produced only {len(selected)} eligible documents")
    return write_prepared(examples / "pravo_open_data", selected, {
        "source_id": "pravo_open_data",
        "source_url": PRAVO_SOURCE_URL,
        "api": f"{PRAVO_BASE}/api/Documents",
        "raw_pdf_directory": str(pdf_root),
        "selection": "50 official PDFs with extractable Russian text, at least 400 words and three pages/paragraphs; max five per authority",
        "attribution": "Официальный интернет-портал правовой информации, publication.pravo.gov.ru",
        "text_extraction": extraction_counts,
    })


def main() -> int:
    parser = argparse.ArgumentParser(description="Download and prepare local held-out corpora under examples/")
    parser.add_argument("--examples-dir", type=Path, default=DEFAULT_EXAMPLES)
    parser.add_argument(
        "--sources", nargs="+",
        choices=("taiga_social", "duma_speeches_1994_2021", "pravo_open_data"),
        default=("taiga_social", "duma_speeches_1994_2021", "pravo_open_data"),
    )
    parser.add_argument("--timeout", type=float, default=120.0)
    args = parser.parse_args()
    examples = args.examples_dir.resolve()
    downloads = examples / "_downloads"
    downloads.mkdir(parents=True, exist_ok=True)
    reports: dict[str, dict] = {}
    for source_id in ("taiga_social", "duma_speeches_1994_2021", "pravo_open_data"):
        provenance = examples / source_id / "provenance.json"
        if provenance.is_file():
            reports[source_id] = json.loads(provenance.read_text(encoding="utf-8"))
    if "taiga_social" in args.sources:
        api_url = TAIGA_API + "?" + urlencode({"public_key": TAIGA_PUBLIC_URL})
        taiga_url = str(fetch_json(api_url, args.timeout)["file"])
        archive = download(taiga_url, downloads / "taiga-social.tar.gz", args.timeout, TAIGA_SHA256)
        reports["taiga_social"] = prepare_taiga(archive, examples)
    if "duma_speeches_1994_2021" in args.sources:
        archive = download(DUMA_URL, downloads / "duma-transcripts.zip", args.timeout, DUMA_SHA256)
        reports["duma_speeches_1994_2021"] = prepare_duma(archive, examples)
    if "pravo_open_data" in args.sources:
        reports["pravo_open_data"] = prepare_pravo(examples, downloads, args.timeout)
    (examples / "LOCAL_CORPORA_REPORT.json").write_text(
        json.dumps({"schema_version": 1, "sources": reports}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    for source_id, report in reports.items():
        print(f"{source_id}: documents={report['documents']} words={report['words']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
