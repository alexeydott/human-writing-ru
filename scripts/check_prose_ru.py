#!/usr/bin/env python3
"""Лёгкий редакторский анализатор русской прозы.

Не является детектором ИИ, грамматическим корректором или языковой нормой.
Числовые пороги в profiles/editorial-baseline.json — экспертный baseline до
корпусной калибровки.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LETTERS = "А-Яа-яЁёA-Za-z"
TOKEN_RE = re.compile(rf"[{LETTERS}]+(?:-[{LETTERS}]+)*|\d+(?:[.,]\d+)*")
RAW_SENT_RE = re.compile(r"[^.!?…\n]+(?:[.!?…]+|$)")
SENTINEL = "∯"

ROAD_SIGNS = (
    "важно отметить", "стоит отметить", "следует отметить",
    "необходимо отметить", "необходимо подчеркнуть", "важно понимать",
    "ключевой момент", "таким образом", "более того", "кроме того",
    "вместе с тем", "с другой стороны", "в конечном счёте",
    "в конечном счете", "подводя итог", "в заключение",
)

HYPE = (
    re.compile(r"\bсинерги\w*\b", re.I),
    re.compile(r"\bбесшовн\w*\b", re.I),
    re.compile(r"\bдрайвер\w*\s+рост\w*\b", re.I),
    re.compile(r"\bточк\w*\s+рост\w*\b", re.I),
    re.compile(r"\bнов\w*\s+уровн\w*\b", re.I),
    re.compile(r"\bпереосмыслен\w*\b", re.I),
    re.compile(r"\bнов\w*\s+реальност\w*\b", re.I),
    re.compile(r"\bреволюционн\w*\b", re.I),
    re.compile(r"\bфлагманск\w*\b", re.I),
    re.compile(r"\bкак\s+никогда\b", re.I),
)

JARGON = (
    re.compile(r"\bэкосистем\w*\b", re.I),
    re.compile(r"\bтрансформаци\w*\b", re.I),
    re.compile(r"\bмасштабировани\w*\b", re.I),
    re.compile(r"\bоптимизаци\w*\b", re.I),
    re.compile(r"\bэффективност\w*\b", re.I),
    re.compile(r"\bинновационн\w*\b", re.I),
    re.compile(r"\bкомплексн\w*\b", re.I),
    re.compile(r"\bценностн\w*\s+предложени\w*\b", re.I),
)

NOMINAL = (
    re.compile(
        r"\b(?:осуществить|осуществлять|осуществлено|осуществляется|осуществлялось)"
        r"\s+(?:проведение|реализацию|настройку|проверку|анализ|обработку)\b",
        re.I,
    ),
    re.compile(
        r"\b(?:произвести|производить|произведено|производится)"
        r"\s+(?:настройку|проверку|анализ|обработку|расч[её]т|оценку)\b",
        re.I,
    ),
    re.compile(r"\bбыло\s+принято\s+решение\s+(?:о|об)\b", re.I),
    re.compile(
        r"\b(?:была|было|были)\s+"
        r"(?:проведена|проведено|проведены|осуществлена|осуществлено|осуществлены)\b",
        re.I,
    ),
    re.compile(r"\bреализован[аоы]?\s+возможност\w*\b", re.I),
)

BUREAU = (
    re.compile(r"\bв\s+рамках\b", re.I),
    re.compile(r"\bв\s+целях\b", re.I),
    re.compile(r"\bв\s+части\b", re.I),
    re.compile(r"\bпо\s+причине\s+наличия\b", re.I),
    re.compile(r"\bимеет\s+место\b", re.I),
    re.compile(r"\bимеется\s+возможность\b", re.I),
)

PIVOTS = (
    re.compile(r"\bэто\s+не\s+просто\b", re.I),
    re.compile(r"\bне\s+просто\b.{0,100}\b(?:а|но)\b", re.I),
    re.compile(r"\bне\s+столько\b.{0,100}\bсколько\b", re.I),
    re.compile(r"\bна\s+первый\s+взгляд\b", re.I),
    re.compile(r"\bказалось\s+бы\b", re.I),
    re.compile(r"\bна\s+самом\s+деле\b", re.I),
    re.compile(r"\b(?:истинная|настоящая)\s+проблема\b", re.I),
)

FILLERS = ("ну", "вот", "короче", "собственно", "как бы", "типа", "в общем", "скажем так")


@dataclass
class Finding:
    level: str
    code: str
    line: int
    message: str
    excerpt: str = ""


def tokens(text: str) -> list[str]:
    return TOKEN_RE.findall(text)


def line_number(text: str, pos: int) -> int:
    return text.count("\n", 0, pos) + 1


def excerpt(value: str, limit: int = 110) -> str:
    value = re.sub(r"\s+", " ", value).strip()
    return value if len(value) <= limit else value[: limit - 1] + "…"


def _mask(match: re.Match[str]) -> str:
    return "".join("\n" if char == "\n" else " " for char in match.group())


def mask_non_prose(text: str) -> str:
    patterns = (
        re.compile(r"\A---\s*\n.*?\n---\s*(?:\n|$)", re.S),
        re.compile(r"```.*?```", re.S),
        re.compile(r"`[^`\n]*`"),
        re.compile(r"https?://[^\s)>]+"),
        re.compile(r"\[[^\]]*\]\([^)]+\)"),
        re.compile(r"<[^>\n]+>"),
    )
    for pattern in patterns:
        text = pattern.sub(_mask, text)
    return text


def mask_quotes(text: str) -> str:
    """Исключает дословные цитаты из стилевой статистики по умолчанию."""
    text = re.sub(r"(?m)^\s*>[^\n]*(?:\n|$)", _mask, text)
    for pattern in (re.compile(r"«[^»\n]*»"), re.compile(r"“[^”\n]*”")):
        text = pattern.sub(_mask, text)
    return text


def protect_periods(text: str) -> str:
    """Защищает точки в версиях, времени, инициалах и ряде сокращений."""
    text = re.sub(r"(?<=\d)\.(?=\d)", SENTINEL, text)
    text = re.sub(
        r"(?:\b[А-ЯЁA-Z]\.\s*){1,3}(?=[А-ЯЁA-Z][а-яёa-z-]{2,})",
        lambda match: match.group().replace(".", SENTINEL),
        text,
    )
    multi = re.compile(r"\bт\.\s*[екдпн]\.", re.I)

    def protect_multi(match: re.Match[str]) -> str:
        chars = list(match.group())
        dots = [index for index, char in enumerate(chars) if char == "."]
        # Внутренняя точка всегда часть сокращения. Последняя остаётся границей
        # предложения перед новой фразой с прописной, но защищается перед
        # продолжением со строчной/цифрой.
        for index in dots[:-1]:
            chars[index] = SENTINEL
        tail = text[match.end() : match.end() + 24]
        if re.match(r"\s+(?:[а-яё]|\d)", tail):
            chars[dots[-1]] = SENTINEL
        return "".join(chars)

    text = multi.sub(protect_multi, text)

    # Сокращения перед продолжением фразы со строчной/цифрой.
    text = re.sub(
        r"\b(?i:г|гг|ул|д|кв|стр|рис|табл|см|им|др|напр|млн|млрд|руб)\."
        r"(?=\s+(?:[а-яё]|\d))",
        lambda match: match.group()[:-1] + SENTINEL,
        text,
    )
    # Несколько адресно-именных сокращений перед именем собственным.
    text = re.sub(
        r"(?<!\d\s)\b(?:г|ул|им)\.(?=\s+[А-ЯЁ])",
        lambda match: match.group()[:-1] + SENTINEL,
        text,
    )
    return text


def sentence_spans(text: str) -> list[tuple[int, int, str, int]]:
    protected = protect_periods(text)
    result = []
    for match in RAW_SENT_RE.finditer(protected):
        original = text[match.start() : match.end()]
        count = len(tokens(original))
        if count >= 2:
            result.append((match.start(), match.end(), original, count))
    return result


def paragraphs(text: str) -> list[tuple[int, str]]:
    result = []
    cursor = 0
    for block in re.split(r"\n\s*\n+", text):
        pos = text.find(block, cursor)
        if pos < 0:
            continue
        cursor = pos + len(block)
        clean = block.strip()
        if (
            clean
            and not clean.startswith(("#", "```"))
            and not re.match(r"^(?:[-*+]|\d+[.)])\s", clean)
            and len(tokens(clean)) >= 3
        ):
            result.append((pos, clean))
    return result


def phrase_re(phrase: str) -> re.Pattern[str]:
    return re.compile(rf"(?<![{LETTERS}]){re.escape(phrase)}(?![{LETTERS}])", re.I)


def phrase_hits(text: str, phrases: tuple[str, ...]):
    return sorted(
        (match.start(), phrase, match.group())
        for phrase in phrases
        for match in phrase_re(phrase).finditer(text)
    )


def pattern_hits(text: str, patterns: tuple[re.Pattern[str], ...]):
    return sorted(
        (match for pattern in patterns for match in pattern.finditer(text)),
        key=lambda match: match.start(),
    )


def punctuation_positions(text: str):
    dashes = [match.start() for match in re.finditer(r"—|(?<=\s)–(?=\s)", text)]
    colons = []
    for match in re.finditer(":", text):
        pos = match.start()
        if pos > 0 and pos + 1 < len(text) and text[pos - 1].isdigit() and text[pos + 1].isdigit():
            continue
        colons.append(pos)
    return dashes, colons


def percentile(values: list[int], quantile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    k = (len(ordered) - 1) * quantile
    lo = math.floor(k)
    hi = math.ceil(k)
    if lo == hi:
        return float(ordered[lo])
    return float(ordered[lo] + (ordered[hi] - ordered[lo]) * (k - lo))


def rate(count: int, words: int) -> float:
    return count * 1000.0 / words if words else 0.0


def compute_features(text: str, include_quotes: bool = False) -> dict:
    prose = mask_non_prose(text)
    style = prose if include_quotes else mask_quotes(prose)
    words = len(tokens(style))
    sents = sentence_spans(style)
    lengths = [item[3] for item in sents]
    paras = paragraphs(style)
    dashes, colons = punctuation_positions(style)
    road = phrase_hits(style, ROAD_SIGNS)
    hype = pattern_hits(style, HYPE)
    jargon = pattern_hits(style, JARGON)
    nominal = pattern_hits(style, NOMINAL)
    bureau = pattern_hits(style, BUREAU)
    pivots = pattern_hits(style, PIVOTS)
    fillers = phrase_hits(style, FILLERS)
    ellipses = list(re.finditer(r"(?:\.\.\.|…)", style))
    one_sentence = sum(1 for _, paragraph in paras if len(sentence_spans(paragraph)) <= 1)
    mean = sum(lengths) / len(lengths) if lengths else 0.0
    cv = (
        math.sqrt(sum((value - mean) ** 2 for value in lengths) / len(lengths)) / mean
        if lengths and mean
        else 0.0
    )
    return {
        "words": words,
        "sentences": len(lengths),
        "paragraphs": len(paras),
        "sentence_mean_words": round(mean, 4),
        "sentence_cv": round(cv, 4),
        "sentence_p90_words": round(percentile(lengths, 0.90), 4),
        "sentence_p95_words": round(percentile(lengths, 0.95), 4),
        "sentence_max_words": max(lengths) if lengths else 0,
        "one_sentence_paragraph_ratio": round(one_sentence / len(paras), 4) if paras else 0.0,
        "dash_per_1000": round(rate(len(dashes), words), 4),
        "colon_per_1000": round(rate(len(colons), words), 4),
        "road_per_1000": round(rate(len(road), words), 4),
        "hype_per_1000": round(rate(len(hype), words), 4),
        "jargon_per_1000": round(rate(len(jargon), words), 4),
        "nominal_per_1000": round(rate(len(nominal), words), 4),
        "bureau_per_1000": round(rate(len(bureau), words), 4),
        "pivot_per_1000": round(rate(len(pivots), words), 4),
        "filler_per_1000": round(rate(len(fillers), words), 4),
        "ellipsis_per_1000": round(rate(len(ellipses), words), 4),
        "_counts": {
            "dashes": len(dashes), "colons": len(colons), "road": len(road),
            "hype": len(hype), "jargon": len(jargon), "nominal": len(nominal),
            "bureau": len(bureau), "pivots": len(pivots), "fillers": len(fillers),
            "ellipses": len(ellipses),
        },
        "_style_text": style,
        "_sentences": sents,
        "_paragraphs": paras,
        "_hits": {
            "road": road, "hype": hype, "jargon": jargon, "nominal": nominal,
            "bureau": bureau, "pivots": pivots, "fillers": fillers,
        },
        "_punct": (dashes, colons),
    }


def public_features(features: dict) -> dict:
    return {key: value for key, value in features.items() if not key.startswith("_")}


def load_profiles(path: str | Path) -> dict:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return data["profiles"]


def analyze(raw: str, mode: str, include_quotes: bool, profiles: dict):
    features = compute_features(raw, include_quotes)
    config = profiles[mode]
    findings: list[Finding] = []

    def add(level: str, code: str, pos: int, message: str, sample: str = ""):
        findings.append(Finding(level, code, line_number(raw, pos), message, excerpt(sample)))

    hits = features["_hits"]
    counts = features["_counts"]
    nominal_level = config.get("nominalization_level", "warning")
    hype_level = config.get("hype_level", "warning")

    for match in hits["nominal"]:
        add(
            nominal_level,
            "nominalization",
            match.start(),
            "Действие может быть спрятано в номинализации или пассивной конструкции. Проверьте уместность для регистра.",
            match.group(),
        )

    if counts["bureau"] >= config.get("min_bureau_hits", 3) and features["bureau_per_1000"] >= config["bureau_per_1000_warn"]:
        for match in hits["bureau"][:8]:
            add("warning", "bureaucratic-density", match.start(), "Высокая для выбранного профиля плотность канцелярских связок; это не автоматически ошибка.", match.group())

    if counts["pivots"] >= config.get("min_pivot_hits", 2) and features["pivot_per_1000"] >= config["pivot_per_1000_warn"]:
        for match in hits["pivots"][:8]:
            add("warning", "rhetorical-pivot", match.start(), "Повторяется риторическая переоценка; сохраните её только при реальном противопоставлении или изменении взгляда.", match.group())

    if counts["road"] >= config.get("min_road_hits", 3) and features["road_per_1000"] >= config["road_per_1000_warn"]:
        for pos, phrase, _ in hits["road"][:10]:
            add("warning", "road-sign-density", pos, "Связность часто строится служебными переходами. Проверьте сцепление предметом, действием или причинностью.", phrase)

    if (
        hype_level != "off"
        and counts["hype"] >= config.get("min_hype_hits", 2)
        and features["hype_per_1000"] >= config.get("hype_per_1000_emit", 5)
    ):
        examples = ", ".join(dict.fromkeys(match.group() for match in hits["hype"][:5]))
        add(
            hype_level,
            "hype-density",
            hits["hype"][0].start(),
            f"Повторяется промо/корпоративная лексика ({counts['hype']} совпадения; {features['hype_per_1000']:.1f}/1000 слов). Проверьте, имеет ли она конкретное значение в этом контексте.",
            examples,
        )

    if counts["jargon"] >= config.get("min_jargon_hits", 4) and features["jargon_per_1000"] >= config["jargon_per_1000_info"]:
        add("info", "context-jargon-density", hits["jargon"][0].start(), "Высокая плотность абстрактной профессиональной лексики; проверьте наличие субъектов, действий и результатов.")

    dashes, colons = features["_punct"]
    dash_level = config.get("dash_level", "info")
    colon_level = config.get("colon_level", "info")
    if (
        dash_level != "off"
        and features["words"] >= config.get("punctuation_min_words", 120)
        and dashes
        and features["dash_per_1000"] >= config["dash_per_1000_info"]
    ):
        add(dash_level, "dash-density", dashes[0], f"Пунктуационное тире встречается часто ({features['dash_per_1000']:.1f} на 1000 слов). Сам знак нормативен; проверьте однообразие.")
    if (
        colon_level != "off"
        and features["words"] >= config.get("punctuation_min_words", 120)
        and colons
        and features["colon_per_1000"] >= config["colon_per_1000_info"]
    ):
        add(colon_level, "colon-density", colons[0], f"Двоеточие встречается часто ({features['colon_per_1000']:.1f} на 1000 слов). Сам знак нормативен; проверьте повтор одной модели.")

    if config.get("rhythm_checks", True) and features["sentences"] >= config.get("min_sentences_for_cv", 10) and features["sentence_cv"] < config["sentence_cv_min_info"]:
        add("info", "sentence-uniformity", 0, f"Длины предложений относительно ровные (CV {features['sentence_cv']:.2f}); порог профильный и не является нормой.")

    for start, _, value, count in features["_sentences"]:
        if count >= config["long_sentence_words_info"]:
            add("info", "long-sentence", start, f"Длинное для профиля предложение: {count} слов. Проверьте иерархию, а не сокращайте автоматически.", value)

    if config.get("rhythm_checks", True) and features["paragraphs"] >= config.get("min_paragraphs_for_ratio", 8) and features["one_sentence_paragraph_ratio"] >= config["one_sentence_paragraph_ratio_info"]:
        add("info", "one-sentence-paragraphs", features["_paragraphs"][0][0], f"Доля однофразовых абзацев {features['one_sentence_paragraph_ratio']:.0%}; проверьте, оправдан ли ритм жанром.")

    if mode == "oral" and counts["fillers"] >= config.get("min_filler_hits", 3) and features["filler_per_1000"] >= config["filler_per_1000_info"]:
        add("info", "filler-density", hits["fillers"][0][0], f"Разговорные частицы часты ({features['filler_per_1000']:.1f}/1000 слов); проверьте, функциональны ли они.")

    return features, findings


def main() -> int:
    parser = argparse.ArgumentParser(description="Редакторская проверка русской прозы")
    parser.add_argument("path", help="UTF-8 Markdown/текст или - для stdin")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--features-only", action="store_true", help="только числовые признаки без предупреждений")
    parser.add_argument("--include-quotes", action="store_true")
    parser.add_argument("--profile-file", default=str(ROOT / "profiles/editorial-baseline.json"))
    parser.add_argument("--mode", choices=("prose", "oral", "product", "technical", "official"), default="prose")
    parser.add_argument("--oral", action="store_true", help="алиас --mode oral")
    args = parser.parse_args()

    mode = "oral" if args.oral else args.mode
    try:
        raw = sys.stdin.read() if args.path == "-" else Path(args.path).read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        print(f"Не удалось прочитать текст: {error}", file=sys.stderr)
        return 2

    profiles = load_profiles(args.profile_file)
    if mode not in profiles:
        print(f"Профиль {mode!r} отсутствует в {args.profile_file}", file=sys.stderr)
        return 2

    features, findings = analyze(raw, mode, args.include_quotes, profiles)
    public = public_features(features)

    if args.features_only:
        payload = {"mode": mode, "profile_file": args.profile_file, "features": public}
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            for key, value in public.items():
                print(f"{key}: {value}")
        return 0

    output = {
        "mode": mode,
        "profile_file": args.profile_file,
        "profile_status": profiles[mode].get("status", "unknown"),
        "features": public,
        "findings": [asdict(item) for item in findings],
        "note": "Сигналы требуют редакторской проверки. Профиль может быть экспертным или корпусно-кандидатным; ни один порог не является языковой нормой.",
    }

    if args.json:
        print(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        print(f"Режим: {mode}; слов: {public['words']}; предложений: {public['sentences']}; абзацев: {public['paragraphs']}")
        if not findings:
            print("Предупреждений нет.")
        for item in findings:
            suffix = f" — {item.excerpt}" if item.excerpt else ""
            print(f"[{item.level}] L{item.line} {item.code}: {item.message}{suffix}")
        print("\nПримечание: это редакторские сигналы, не определение «человек/ИИ» и не проверка всей грамматики.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
