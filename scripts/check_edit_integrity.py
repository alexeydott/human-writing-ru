#!/usr/bin/env python3
"""Deterministic safety diff for Russian text editing.

The tool is deliberately conservative: it does not claim semantic equivalence.
It surfaces high-risk changes that deserve review after rewriting. It is not a
style score, grammar checker, NER system, or authorship detector.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
import re
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

NUMBER_RE = re.compile(r"(?<![\w])(?:\d{1,4}(?:[ .]\d{3})+|\d+)(?:[,.]\d+)?(?:\s*[%‰])?(?![\w])")
DATE_RE = re.compile(r"\b(?:\d{1,2}[./-]\d{1,2}[./-]\d{2,4}|\d{4}-\d{2}-\d{2})\b")
URL_RE = re.compile(r"https?://[^\s)\]}>]+", re.I)
CURRENCY_RE = re.compile(r"(?<!\w)(?:[$€₽¥£]\s*\d[\d\s.,]*|\d[\d\s.,]*\s*(?:₽|руб\.?|рублей|доллар(?:а|ов)?|евро))(?!\w)", re.I)
QUOTE_RE = re.compile(r"«([^«»\n]{2,300})»|\"([^\"\n]{2,300})\"")

WEAK_MODAL = {
    "может", "могут", "мог", "могла", "возможно", "вероятно", "предположительно",
    "похоже", "ожидается", "предполагается", "способен", "способна", "можно",
}
STRONG_MODAL = {
    "точно", "однозначно", "обязательно", "гарантированно", "неизбежно", "доказано",
    "всегда", "никогда", "безусловно", "несомненно",
}
NEGATION = {"не", "нет", "нельзя", "никогда", "ни"}
CONDITION = {"если", "при условии", "в случае", "только если", "если только"}
ATTRIBUTION = {
    "по данным", "по словам", "согласно", "сообщил", "сообщила", "сообщает", "заявил",
    "заявила", "отмечает", "отметил", "отметила", "как сообщил", "как заявила", "как заявил",
}
CAUSAL = {"потому что", "поскольку", "поэтому", "из-за", "вследствие", "привело к", "приводит к"}

MEASURE_RE = re.compile(
    r"(?<![\w])(?:\d+(?:[,.]\d+)?)\s*(?:%|‰|°C|°F|м²|м³|м3|мм|см|км|м|кг|мг|г|мл|л|сек\.?|с|мин\.?|ч|час(?:а|ов)?|дн(?:я|ей)?|КБ|МБ|ГБ|ТБ|KB|MB|GB|TB|кбит/с|Мбит/с|Гбит/с|kbps|Mbps|Gbps)(?![\w])",
    re.I,
)
# Conservative entity-like patterns only: multi-token title-case names and all-caps acronyms.
# Single capitalized words are deliberately ignored because sentence starts would dominate.
ENTITY_SEQ_RE = re.compile(r"(?<![\w])(?:[А-ЯЁA-Z][а-яёa-z]+(?:[-’'][А-ЯЁA-Z]?[а-яёa-z]+)?)(?:\s+[А-ЯЁA-Z][а-яёa-z]+(?:[-’'][А-ЯЁA-Z]?[а-яёa-z]+)?)+(?![\w])")
ACRONYM_RE = re.compile(r"(?<![\w])(?:[А-ЯЁA-Z]{2,}[0-9]*)(?![\w])")


def norm_space(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def counter_matches(regex: re.Pattern, text: str) -> Counter:
    return Counter(norm_space(x.group(0)) for x in regex.finditer(text))




def url_counter(text: str) -> Counter:
    out: Counter = Counter()
    for match in URL_RE.finditer(text):
        raw = match.group(0).strip()
        parts = urlsplit(raw)
        # Scheme and hostname are case-insensitive. Path/query/fragment are not
        # generally safe to lowercase, so preserve them exactly.
        netloc = parts.netloc.lower()
        normalized = urlunsplit((parts.scheme.lower(), netloc, parts.path, parts.query, parts.fragment))
        out[normalized] += 1
    return out

def phrase_count(text: str, phrases: set[str]) -> int:
    low = norm_space(text)
    total = 0
    for phrase in phrases:
        if " " in phrase:
            total += len(re.findall(rf"(?<!\w){re.escape(phrase)}(?!\w)", low))
        else:
            total += len(re.findall(rf"(?<!\w){re.escape(phrase)}(?!\w)", low))
    return total


def token_set(text: str, words: set[str]) -> Counter:
    low = norm_space(text)
    return Counter({w: len(re.findall(rf"(?<!\w){re.escape(w)}(?!\w)", low)) for w in words})


def add_counter_diff(findings: list[dict], code: str, severity: str, before: Counter, after: Counter, message: str) -> None:
    removed = list((before - after).elements())
    added = list((after - before).elements())
    if removed or added:
        findings.append({
            "code": code, "severity": severity, "message": message,
            "removed": removed, "added": added,
        })


def analyze(source: str, edited: str) -> dict:
    findings: list[dict] = []
    add_counter_diff(findings, "numeric-change", "high", counter_matches(NUMBER_RE, source), counter_matches(NUMBER_RE, edited),
                     "Изменился набор числовых значений/процентов; требуется ручная проверка контекста.")
    add_counter_diff(findings, "date-change", "high", counter_matches(DATE_RE, source), counter_matches(DATE_RE, edited),
                     "Изменилась дата или дата исчезла/появилась.")
    add_counter_diff(findings, "currency-change", "high", counter_matches(CURRENCY_RE, source), counter_matches(CURRENCY_RE, edited),
                     "Изменилась денежная величина или обозначение суммы.")
    add_counter_diff(findings, "url-change", "high", url_counter(source), url_counter(edited),
                     "Изменился URL; проверь, что ссылка не потеряна и не подменена.")
    add_counter_diff(findings, "measurement-change", "high", counter_matches(MEASURE_RE, source), counter_matches(MEASURE_RE, edited),
                     "Изменилось сочетание числа и единицы измерения; проверь масштаб/единицу.")
    entity_before = counter_matches(ENTITY_SEQ_RE, source) + counter_matches(ACRONYM_RE, source)
    entity_after = counter_matches(ENTITY_SEQ_RE, edited) + counter_matches(ACRONYM_RE, edited)
    add_counter_diff(findings, "entity-like-change", "medium", entity_before, entity_after,
                     "Изменилась высокоточно распознаваемая последовательность имени/названия или аббревиатура; проверь сущность вручную.")

    weak_before = phrase_count(source, WEAK_MODAL)
    weak_after = phrase_count(edited, WEAK_MODAL)
    strong_before = phrase_count(source, STRONG_MODAL)
    strong_after = phrase_count(edited, STRONG_MODAL)
    if weak_after < weak_before and strong_after > strong_before:
        findings.append({
            "code": "modality-strengthened", "severity": "high",
            "message": "Слабая/вероятностная модальность могла быть заменена более категоричной.",
            "before": {"weak": weak_before, "strong": strong_before},
            "after": {"weak": weak_after, "strong": strong_after},
        })
    elif weak_after < weak_before:
        findings.append({
            "code": "modality-marker-loss", "severity": "high",
            "message": "Исчез или сократился маркер вероятности/возможности; утверждение могло стать категоричнее без явного усилителя.",
            "before": {"weak": weak_before, "strong": strong_before},
            "after": {"weak": weak_after, "strong": strong_after},
        })

    for code, phrases, severity, message in [
        ("negation-loss", NEGATION, "high", "После редактуры стало меньше маркеров отрицания; смысл мог инвертироваться."),
        ("condition-loss", CONDITION, "high", "После редактуры исчезло условие/оговорка."),
        ("attribution-loss", ATTRIBUTION, "high", "После редактуры ослабла или исчезла атрибуция утверждения."),
        ("causal-relation-change", CAUSAL, "medium", "Изменилось число явных причинно-следственных связок; проверь причинность."),
    ]:
        b, a = phrase_count(source, phrases), phrase_count(edited, phrases)
        if a < b:
            findings.append({"code": code, "severity": severity, "message": message, "before": b, "after": a})

    # Exact quotes are protected only as a review signal; a quote may legitimately
    # become attributed paraphrase, so this is medium rather than automatic error.
    def quote_counter(text: str) -> Counter:
        return Counter(norm_space(a or b) for a, b in QUOTE_RE.findall(text))
    qb = quote_counter(source)
    qa = quote_counter(edited)
    removed_quotes = list((qb - qa).elements())
    if removed_quotes:
        findings.append({
            "code": "quote-changed-or-removed", "severity": "medium",
            "message": "Точная цитата изменилась или исчезла; допустимо только при осознанном переходе к пересказу.",
            "removed": removed_quotes,
        })

    high = sum(1 for f in findings if f["severity"] == "high")
    medium = sum(1 for f in findings if f["severity"] == "medium")
    return {
        "schema_version": 1,
        "status": "review_required" if findings else "no_deterministic_integrity_risks_found",
        "scope_note": "Отсутствие находок не доказывает семантическую эквивалентность; это детерминированная страховочная проверка.",
        "summary": {"high": high, "medium": medium, "total": len(findings)},
        "findings": findings,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Check high-risk factual/modality changes between source and edited Russian text")
    ap.add_argument("source", type=Path)
    ap.add_argument("edited", type=Path)
    ap.add_argument("--json", dest="json_path", type=Path, default=None)
    ap.add_argument("--fail-on-high", action="store_true")
    args = ap.parse_args()
    source = args.source.read_text(encoding="utf-8")
    edited = args.edited.read_text(encoding="utf-8")
    out = analyze(source, edited)
    if args.json_path:
        args.json_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    for f in out["findings"]:
        print(f"{f['severity'].upper()} {f['code']}: {f['message']}")
    if not out["findings"]:
        print("OK: no deterministic integrity risks found")
    return 2 if args.fail_on_high and out["summary"]["high"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
