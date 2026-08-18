# Нормализация ТЗ

## Быстрый запуск

```bash
python3 scripts/check_tz_ru.py --profile generic spec.md
python3 scripts/check_tz_ru.py --profile gost34 spec.md
python3 scripts/check_tz_ru.py --profile gost19 spec.md
python3 scripts/check_tz_ru.py --profile generic --json spec.md
python3 scripts/check_tz_ru.py --safe-normalize-output spec.normalized.md spec.md
python3 scripts/check_edit_integrity.py spec.md spec.edited.md
```

`--safe-normalize-output` меняет только пробельное оформление. Он намеренно не исправляет требования по смыслу. Смысловая редактура выполняется по `references/technical-specification.md` с последующим integrity check.

## Выход checker

Каждая находка содержит `code`, `severity`, `line`, русские `title/message/fix`, excerpt и при необходимости detail. Правила вынесены в `profiles/tz-rules.ru.json`.

## Профили

- `generic` — универсальное проектное ТЗ;
- `gost34` — структурный профиль ГОСТ 34.602-2020 для АС;
- `gost19` — структурный профиль ГОСТ 19.201-78 для программ/программных изделий.

Профиль ГОСТ — помощник по структуре, а не доказательство соответствия стандарту.
