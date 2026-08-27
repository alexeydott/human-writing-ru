[← Release](release.md) · [Back to README](../README.md)

# Contributing

Как менять проект, не сломав замороженные области и научную честность калибровки.

## Конвенции (где они зафиксированы)

- `.ai-factory/rules/base.md` — автоопределённые конвенции кода (называние, модули, ошибки, тесты);
- `AGENTS.md` — карта проекта и правила для агентов;
- навык `human-writing-ru-conventions` (`.qwen/skills/`) — напоминание о замороженных областях и проверках.

Краткая выжимка: Python 3.10+ stdlib-first; файлы `snake_case`; CLI с `argparse` и `--json`;
`ROOT = Path(__file__).resolve().parents[1]`; `#!/usr/bin/env python3` +
`from __future__ import annotations`; docstring/комментарии правил — на русском; тесты —
плоские assert-скрипты без pytest, вывод `OK`.

## Цикл разработки

```
изменение → целевой тест (tests/test_<модуль>.py) → полный набор проверок → commit
```

Полный набор — блок «Полный набор проверок» в [Getting Started](getting-started.md).
Успех = каждый скрипт завершается кодом 0 и печатает `OK`.

Git: базовая ветка `main`, feature-ветки с префиксом `feature/` (см. `.ai-factory/config.yaml`).

## Новые инструменты и сигналы

1. Новый инструмент — новый файл в `scripts/` по образцу существующих (один файл = один инструмент).
2. Тест `tests/test_<имя>.py` с положительными **и отрицательными** контрольными примерами.
3. Новый user-facing style signal — только со своим positive/negative set и held-out precision.
4. Изменение активного порога линтера — только через полный цикл held-out v3
   (см. [Data и pipeline](data-and-pipeline.md)); кандидат строится отдельным скриптом
   (паттерн `ablate_signals_v3.py`), активный frozen-файл не правится.

## Запрещено

- Редактировать byte-stable файлы «по пути»: `scripts/check_prose_ru.py`,
  `scripts/ablate_signals.py`, `profiles/editorial-baseline.json`
  (SHA-контракт — `benchmark/external-heldout/FROZEN_INPUT_SHA256.json`).
- Автоматически переключать active профиль/порог по локальному (не held-out) результату.
- Коммитить содержимое `data/` и полные сторонние тексты.
- Тяжёлый NLP/morphosyntax как обязательная зависимость core Skill — только отдельная опциональная ветка.
- Exact-string match как основная метрика редакторских задач.
- Повышать `metadata.policy_version` иначе как по итогам внешнего held-out v3 с решением
  человека (полный цикл — [Data и pipeline](data-and-pipeline.md), прецедент 1.5.0 —
  `POLICY_RERUN_PLAN.md` Этап 3). Номер policy не привязан к версии пакета: повышение
  допустимо раздельно или вместе, но каждое — своим задокументированным решением
  (конвенция: `metadata.policy_version` в `SKILL.md` не привязывается к версии пакета).

## Частые ловушки

| Симптом | Причина / действие |
|---------|--------------------|
| `validate_skill.py`: README не упоминает VERSION | Синхронизировать версию во всех четырёх местах при релизе |
| SHA замороженного файла сошёлся с контрактом | Drift от параллельного незавершённого прохода; вернуть byte-stable версию из git |
| Fetch даёт 0 документов | Нет исходящей сети; зафиксировать статус, не «чинить» gate |
| Сборка упала до ZIP | `validate_skill.py` не прошёл — читать его вывод, а не обходить флаг |

## See Also

- [Architecture](architecture.md) — границы модулей и правила зависимостей
- [Release](release.md) — процесс сборки и контроля целостности
