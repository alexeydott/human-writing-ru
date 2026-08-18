#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RULES = json.loads((ROOT/'profiles/tz-rules.ru.json').read_text(encoding='utf-8'))
PROFILES = json.loads((ROOT/'profiles/tz-profiles.json').read_text(encoding='utf-8'))['profiles']
RULE_BY_ID = {r['id']: r for r in RULES['rules']}

REQ_MARKER_RE = re.compile(r'(?i)(?:\b(?:долж(?:ен|на|но|ны)|обязан\w*|требуется|необходимо|запрещается)\b|\bне\s+допускается\b)')
REQ_ID_RE = re.compile(r'^\s*(?:[-*+]\s*)?(?:REQ|FR|NFR|ТР|ТЗ)[-_ ]?\d+[\w.-]*\s*[:.)-]?', re.I)
BULLET_RE = re.compile(r'^\s*(?:[-*+]\s+|\d+(?:\.\d+)*[.)]\s+)')
HEADING_RE = re.compile(r'^\s{0,3}#{1,6}\s+(.+?)\s*#*\s*$')
PLACEHOLDER_RE = re.compile(r'(?i)(?:\bTODO\b|\bTBD\b|\bFIXME\b|\bXXX\b|\[\s*(?:уточнить|заполнить|согласовать|tbd|todo)[^\]]*\]|\b(?:уточнить|согласовать позднее|определить позднее)\b)')
SUBJECTIVE_RE = re.compile(r'(?i)\b(?:быстр(?:о|ый|ая|ое|ые)|удобн\w*|современн\w*|качественн\w*|интуитивн\w*|оптимальн\w*|высок\w*\s+производительност\w*|наилучш\w*)\b')
WEAK_RE = re.compile(r'(?i)\b(?:желательно|по\s+возможности|рекомендуется|предпочтительно)\b')
CONFLICT_RE = re.compile(r'(?i)\bдолж(?:ен|на|но|ны)\b.{0,80}\b(?:по\s+возможности|желательно|при\s+необходимости)\b')
VAGUE_TIME_RE = re.compile(r'(?i)\b(?:в\s+кратчайш\w*\s+срок\w*|оперативно|своевременно|регулярно|периодически|без\s+задержек|немедленно)\b')
SECURITY_RE = re.compile(r'(?i)\b(?:обеспеч(?:ить|ивает|ивать|иваться)\s+(?:информационную\s+)?безопасност\w*|обеспеч(?:ить|ивает|ивать)\s+защищ[её]нност\w*|долж(?:ен|на|но|ны).{0,60}(?:быть\s+)?безопасн\w*)\b')
AMBIG_OBJECT_RE = re.compile(r'(?i)\b(?:обработать|сохранить|использовать|передать|удалить|учитывать|вернуть|изменить|проверить)\s+(?:это|этот|эту|эти|данн(?:ый|ую|ые)|указанн(?:ый|ую|ые)|соответствующ(?:ий|ую|ие))\b')
VERIFY_HINT_RE = re.compile(r'(?i)(?:\bне\s+(?:более|менее)\b|\b(?:не\s+позднее|не\s+ранее)\b|\bв\s+течение\b|\bесли\b|\bпосле\b|\bдо\b|\bпри\s+нагрузке\b|\bпровер(?:яется|ить|ка)\b|\bиспытан\w*\b|\bкритери\w*\b|\bкод\s+ответа\b|\bстатус\w*\b|\bошибк\w*\b|\d\s*(?:мс|с|сек\.?|мин\.?|ч|%|МБ|ГБ|шт\.?|запрос\w*/с))')
ACCEPT_HEADING_RE = re.compile(r'(?i)(?:порядок\s+контроля\s+и\s+при[её]мки|критерии\s+при[её]мки|при[её]мочн\w*\s+(?:испытан\w*|критери\w*)|verification|acceptance)')
NORM_FORMS = {
    'должен': re.compile(r'(?i)\bдолж(?:ен|на|но|ны)\b'),
    'необходимо': re.compile(r'(?i)\bнеобходимо\b'),
    'требуется': re.compile(r'(?i)\bтребуется\b'),
    'обязан': re.compile(r'(?i)\bобязан\w*\b'),
    'следует': re.compile(r'(?i)\bследует\b'),
}

def clean_heading(s: str) -> str:
    s = re.sub(r'^\s*(?:\d+(?:\.\d+)*[.)]?\s+)', '', s)
    s = re.sub(r'[`*_]+', '', s)
    return re.sub(r'\s+', ' ', s.strip().lower().replace('ё', 'е'))

def requirement_lines(text: str):
    out = []
    in_code = False
    for i, line in enumerate(text.splitlines(), 1):
        stripped = line.strip()
        if stripped.startswith('```'):
            in_code = not in_code
            continue
        if in_code or not stripped or HEADING_RE.match(line):
            continue
        if REQ_MARKER_RE.search(line) or REQ_ID_RE.match(line):
            out.append((i, line))
    return out

def finding(code, line, excerpt, detail=None, severity=None):
    r = RULE_BY_ID[code]
    d = {
        'code': code, 'severity': severity or r['severity'], 'line': line,
        'title': r['title_ru'], 'message': r['message_ru'], 'fix': r['fix_ru'],
        'excerpt': re.sub(r'\s+', ' ', excerpt.strip())[:240]
    }
    if detail is not None:
        d['detail'] = detail
    return d

def analyze(text: str, profile='generic'):
    if profile not in PROFILES:
        raise ValueError(f'unknown profile: {profile}')
    findings = []
    lines = text.splitlines()
    reqs = requirement_lines(text)

    in_code = False
    for ln, line in enumerate(lines, 1):
        if line.strip().startswith('```'):
            in_code = not in_code
            continue
        if not in_code and PLACEHOLDER_RE.search(line):
            findings.append(finding('TZ001', ln, line))

    for ln, line in reqs:
        if SUBJECTIVE_RE.search(line):
            findings.append(finding('TZ002', ln, line))
        conflict = bool(CONFLICT_RE.search(line))
        if WEAK_RE.search(line) and not conflict:
            findings.append(finding('TZ003', ln, line))
        if conflict:
            findings.append(finding('TZ009', ln, line))
        if VAGUE_TIME_RE.search(line):
            findings.append(finding('TZ007', ln, line))
        if REQ_MARKER_RE.search(line) and AMBIG_OBJECT_RE.search(line):
            findings.append(finding('TZ006', ln, line))
        if SECURITY_RE.search(line) and not VERIFY_HINT_RE.search(line):
            findings.append(finding('TZ008', ln, line))

        req_marks = len(REQ_MARKER_RE.findall(line))
        branch_count = len(re.findall(r'(?i)\b(?:а\s+также|либо|или)\b', line))
        if req_marks >= 2 or (branch_count >= 2 and len(re.findall(r'[,;]', line)) >= 2 and len(line) > 170):
            findings.append(finding('TZ004', ln, line))

        nonfunc = bool(re.search(r'(?i)\b(?:производительност|доступност|надежност|над[её]жност|масштабируемост|безопасност|врем[яе]\s+отклика|скорост|нагрузк|RTO|RPO|SLA)\b', line))
        if REQ_MARKER_RE.search(line) and (nonfunc or SUBJECTIVE_RE.search(line) or VAGUE_TIME_RE.search(line)) and not VERIFY_HINT_RE.search(line):
            findings.append(finding('TZ005', ln, line))

    seen = {}
    for ln, line in reqs:
        norm = REQ_ID_RE.sub('', line)
        norm = re.sub(r'\W+', ' ', norm.lower().replace('ё', 'е')).strip()
        if len(norm) < 25:
            continue
        if norm in seen:
            findings.append(finding('TZ010', ln, line, detail={'first_line': seen[norm]}))
        else:
            seen[norm] = ln

    obligation_reqs = [(ln, l) for ln, l in reqs if REQ_MARKER_RE.search(l)]
    with_ids = sum(1 for _, l in obligation_reqs if REQ_ID_RE.match(l))
    if len(obligation_reqs) >= 8 and with_ids / len(obligation_reqs) < 0.5:
        findings.append(finding('TZ011', 1, 'Документ содержит много обязательных требований без стабильных ID.', detail={'requirements': len(obligation_reqs), 'with_ids': with_ids}))

    if obligation_reqs and PROFILES[profile].get('require_acceptance_section') and not ACCEPT_HEADING_RE.search(text):
        findings.append(finding('TZ012', 1, 'В документе не найден явный раздел контроля/приёмки.'))

    forms = {name: len(rx.findall(text)) for name, rx in NORM_FORMS.items()}
    active = {k: v for k, v in forms.items() if v >= 2}
    if len(active) >= 3 and sum(active.values()) >= 8:
        findings.append(finding('TZ013', 1, 'Используются разные нормативные формы.', detail=active))

    headings = []
    for ln, line in enumerate(lines, 1):
        m = HEADING_RE.match(line)
        if m:
            headings.append((ln, clean_heading(m.group(1))))
        elif re.match(r'^\s*\d+(?:\.\d+)*[.)]?\s+[А-ЯЁA-Z]', line):
            headings.append((ln, clean_heading(line)))

    if profile in {'gost34', 'gost19'}:
        corpus = '\n'.join(h for _, h in headings)
        for variants in PROFILES[profile]['required_sections']:
            variants_clean = [clean_heading(v) for v in variants]
            if not any(v in corpus for v in variants_clean):
                findings.append(finding('TZ014', 1, variants[0], detail={'expected_section': variants[0], 'profile': profile}))

    uniq, keys = [], set()
    for f in findings:
        k = (f['code'], f['line'], f['excerpt'])
        if k not in keys:
            keys.add(k)
            uniq.append(f)
    counts = Counter(f['severity'] for f in uniq)
    return {
        'schema_version': 1, 'rules_version': RULES['rules_version'], 'profile': profile,
        'status': 'review_required' if uniq else 'no_heuristic_tz_risks_found',
        'scope_note': RULES['scope_note'],
        'summary': {'warning': counts['warning'], 'info': counts['info'], 'total': len(uniq), 'requirement_lines': len(reqs), 'obligation_lines': len(obligation_reqs)},
        'findings': uniq
    }

def safe_normalize(text: str) -> str:
    """Conservative formatting normalization that avoids semantic rewrites.

    Preserves fenced code verbatim and does not collapse interior whitespace, because
    it may be meaningful in tables, inline examples or fixed-width fragments.
    """
    out = []
    in_code = False
    for raw in text.splitlines():
        if raw.strip().startswith('```'):
            in_code = not in_code
            out.append(raw)
            continue
        if in_code:
            out.append(raw)
            continue
        line = raw.replace('\u00a0', ' ')
        # One accidental trailing space is safe to remove. Two or more are
        # preserved because Markdown uses them as an explicit line break.
        if line.endswith(' ') and not line.endswith('  '):
            line = line[:-1]
        out.append(line)
    s = '\n'.join(out)
    s = re.sub(r'\n{4,}', '\n\n\n', s)
    if text.endswith('\n'):
        s += '\n'
    return s

def main() -> int:
    ap = argparse.ArgumentParser(description='Russian technical-specification requirement checker and safe normalizer')
    ap.add_argument('file', type=Path)
    ap.add_argument('--profile', choices=sorted(PROFILES), default='generic')
    ap.add_argument('--json', action='store_true')
    ap.add_argument('--safe-normalize-output', type=Path, default=None)
    ap.add_argument('--fail-on-warning', action='store_true')
    args = ap.parse_args()
    text = args.file.read_text(encoding='utf-8')
    if args.safe_normalize_output is not None:
        args.safe_normalize_output.write_text(safe_normalize(text), encoding='utf-8')
    result = analyze(text, args.profile)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        for f in result['findings']:
            print(f"{f['severity'].upper()} {f['code']} line {f['line']}: {f['message']} :: {f['excerpt']}")
        if not result['findings']:
            print('OK: no heuristic TZ risks found')
    return 2 if args.fail_on_warning and result['summary']['warning'] else 0

if __name__ == '__main__':
    raise SystemExit(main())
