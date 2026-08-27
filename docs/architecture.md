[← Getting Started](getting-started.md) · [Back to README](../README.md) · [Data и pipeline →](data-and-pipeline.md)

# Архитектура

Структура проекта, границы модулей и неподвижные области. Полные guidelines для разработки —
в `.ai-factory/ARCHITECTURE.md` (файл существует только в рабочем дереве; в релиз-пакет не входит).

## Двойная природа репозитория

1. **Пакет Agent Skill** — `SKILL.md` + `references/` + инструменты самопроверки; устанавливается
   целиком в каталог навыков агента под стабильным именем `human-writing-ru/`.
2. **Исследовательский контур** — воспроизводимая калибровка детерминированного линтера на
   held-out корпусах с протоколом принятия решений v3.

## Разделение версий

| Номер | Где | Когда меняется |
|-------|-----|----------------|
| Версия пакета | `VERSION`, `metadata.version` в `SKILL.md` | каждый релиз |
| Лингвистическая политика | `metadata.policy_version` (= 1.5.0) | только по итогам внешнего held-out v3 evidence run |

Синхронно при повышении версии обновляются: `VERSION`, frontmatter `SKILL.md`, верхний раздел
`CHANGELOG.md` и заголовок `README.md`.

## Карта модулей

Роль модуля играет топ-уровневый функциональный каталог с мягкой границей.

| Модуль | Состав | Назначение |
|--------|--------|------------|
| Знания skill | `references/` (18 веток .md) | Погружаемые инструкции по условию задачи |
| Профили | `profiles/` | Пороги и правила линтера/TZ-нормализации |
| Лinting | `scripts/check_prose_ru.py`, `check_tz_ru.py`, `check_edit_integrity.py` | Детерминированные проверки текстов |
| Calibration | `scripts/extract_corpus_features.py`, `calibrate_profiles.py`, `ablate_signals*.py` | Извлечение признаков и ablation old→candidate→off |
| Corpus-pipeline | `scripts/fetch_*.py`, `materialize_external_heldout.py`, `validate_external_heldout.py`, `run_*_heldout_*.py` | Получение, дедупликация и валидация корпусов |
| Evaluation | `evals/`, `scripts/prepare_ab_eval.py`, `aggregate_ab_eval.py`, `audit_eval_coverage.py`, `validate_eval_design.py` | Оценочные наборы и A/B-протокол |
| Packaging | `scripts/build_release.py`, `build_lite.py`, `validate_skill.py` | Самопроверка и детерминированный выпуск |
| Доказательства | `benchmark/`, `research/` | Воспроизводимые артефакты прогонов и отчёты |
| Runtime-данные | `data/` (gitignored) | Скачанные корпуса и результаты workflow |

## Правила зависимостей

Направление строго «слева направо», обратных связей нет:

```
references/ profiles/ evals/  ←  scripts/  →  data/  →  benchmark|dist
     (входные данные)          (логика)      (runtime)   (доказательства/выпуск)
```

- ✅ скрипт читает профили, оценочные наборы и реестры как входные данные
- ✅ связь между скриптами — только прямой импорт явного общего помощника
  (пример: `validate_skill.py` импортирует `build_lite.py`)
- ❌ `data/` — только чтение файлов, никогда источник импортов
- ❌ замороженные файлы не зависят ни от чего runtime
- ❌ циклические импорты инструментов

## Замороженные области (byte-stable)

Файлы, не изменяемые в рамках политики 1.5.0:

- `scripts/check_prose_ru.py`
- `scripts/ablate_signals.py`
- `profiles/editorial-baseline.json`

Контрольные SHA-256 хранятся в `benchmark/external-heldout/FROZEN_INPUT_SHA256.json`;
сборщик релиза сверяет их заново и фиксирует `frozen_inputs_match` в
`quality/RELEASE_INTEGRITY.json`. Любое изменение активного порога — отдельная задача с полным
циклом held-out v3 и решением человека; автоматического переключения active profile нет.

## Поток данных

```
внешние источники → data/<source_id>/ → manifest.csv
   → dedup (profile, sha256) → manifest.validated.csv
   → size/diversity gates по 5 профилям → candidate на calibration
   → разметка natural alerts (actionable / non_actionable / uncertain)
   → решение человека: keep old / candidate / off
```

Каждый этап оставляет машиночитаемый артефакт (JSON/CSV); отсутствие результата не трактуется
как доказательство отсутствия проблемы.

## Ключевые принципы

1. Один файл = один инструмент; новый сигнал = новый скрипт + тесты + контрольные примеры.
2. Доказательность: отрицательные результаты фиксируются артефактами, недостаточная выборка не выдаётся за калибровку.
3. Тяжёлый NLP — только отдельной опциональной веткой, не обязательной зависимостью core Skill.

## See Also

- [Getting Started](getting-started.md) — установка и первый прогон
- [Data и pipeline](data-and-pipeline.md) — источники и held-out v3 подробно
- [Contributing](contributing.md) — конвенции для новых инструментов
