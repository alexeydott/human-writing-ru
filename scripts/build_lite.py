#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "dist/human-writing-ru-lite.md"

# У сетевых служб нет единого предела. Проектный предел в 2000 знаков
# оставляет запас для полей, ограниченных 2048 знаками.
MAX_LITE_CHARACTERS = 2000


def package_versions() -> tuple[str, str]:
    package_version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    match = re.search(r'^\s*policy_version:\s*"([^"]+)"\s*$', skill, re.MULTILINE)
    if not match:
        raise ValueError("в SKILL.md не найдена версия правил")
    return package_version, match.group(1)


def render_lite() -> str:
    package_version, policy_version = package_versions()
    return f"""# Живое русское письмо — инструкция
Пакет {package_version}; правила {policy_version}.

Создавай и редактируй точный, естественный и уместный русский текст. Не имитируй «человечность» ошибками, жаргоном или разговорностью.

1. Определи задачу: новый текст, корректура, правка, глубокая переработка, переработка для иной аудитории или текст для произнесения. Исходник не меняй сильнее, чем просили.
2. Учитывай назначение, читателя, жанр, степень официальности и известное происхождение текста. Не угадывай свойства автора по отдельным оборотам и не своди разные жанры к одной манере.
3. Не выдумывай опыт, события, числа, даты, цитаты, причины, источники и подробности. Сохраняй имена, термины, ссылки, условия, отрицание и степень уверенности. Предположение не превращай в факт, последовательность событий — в причинность.
4. Различай правильность, естественность, ясность, доступность и авторский голос. Не улучшай одно ценой другого. Сохраняй словарь, дистанцию, намеренный ритм, разговорность и категоричность автора.
5. Исправляй реальные ошибки, но не навязывай шаблон. Не запрещай сами по себе тире, двоеточие, пассив, причастия, повтор точного термина и длинные предложения. Меняй форму, когда она мешает смыслу или чтению.
6. Убирай пустые вступления, повторные выводы, рекламные усилители и заготовки без содержания. Один признак не доказывает шаблонность или происхождение текста.
7. Для неродного и переводного русского сохраняй смысл и не стирай особенности речи без просьбы. При упрощении объясняй термины и явно называй действия и условия, но не инфантилизируй читателя.
8. Если данных мало, задай короткий вопрос, обозначь неопределённость или сузь утверждение — не заполняй пробелы вымыслом.

Работай только с текстом и сведениями диалога. Не обещай проверок недоступными средствами. Перед ответом молча проверь факты, смысл, степень уверенности, условия, отрицание, уместность, ясность и голос. Если просят готовый текст, выдай только его, сохранив нужное оформление.
"""


def validate_lite(text: str) -> None:
    package_version, _ = package_versions()
    if len(text) > MAX_LITE_CHARACTERS:
        raise ValueError(
            f"краткая инструкция занимает {len(text)} знаков; "
            f"предел — {MAX_LITE_CHARACTERS}"
        )

    # Идентификатор версии — единственное место, где допустима латиница.
    text_without_version = text.replace(package_version, "")
    if re.search(r"[A-Za-z]", text_without_version):
        raise ValueError("в краткой инструкции осталась латиница вне номера версии")

    forbidden = ("```", "scripts/", ".py", "python", "линтер", "запусти", "команда")
    found = [fragment for fragment in forbidden if fragment in text.casefold()]
    if found:
        raise ValueError("краткая инструкция зависит от внешних средств: " + ", ".join(found))


def write_lite() -> str:
    text = render_lite()
    validate_lite(text)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", encoding="utf-8", newline="\n") as stream:
        stream.write(text)
    return text


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Сформировать краткую автономную инструкцию для вставки в диалог"
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="проверить, что сохранённый файл совпадает с результатом генерации",
    )
    args = parser.parse_args()

    expected = render_lite()
    validate_lite(expected)
    if args.check:
        if not OUTPUT.exists() or OUTPUT.read_text(encoding="utf-8") != expected:
            raise SystemExit("dist/human-writing-ru-lite.md требует пересборки")
        print(f"lite: OK ({len(expected)}/{MAX_LITE_CHARACTERS} знаков)")
        return 0

    text = write_lite()
    print(f"lite={OUTPUT}")
    print(f"characters={len(text)}/{MAX_LITE_CHARACTERS}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
