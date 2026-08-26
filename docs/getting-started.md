[Back to README](../README.md) · [Architecture →](architecture.md)

# Начало работы

Установка Skill, проверка целостности пакета и первый запуск линтера.

## Требования

| Компонент | Версия | Зачем |
|-----------|--------|-------|
| Python | 3.10+ | Встроенные проверки и инструменты |
| `PyYAML` | любая актуальная | Самопроверка пакета (`validate_skill.py` парсит frontmatter) |
| `datasets`, `pypdf` | опционально | Только для получения внешних корпусов, см. [Data и pipeline](data-and-pipeline.md) |
| git | опционально | Установка из репозитория вместо релиз-архива |

Сеть для основного использования **не требуется**: сам Skill работает локально,
внешний held-out нужен только исследователю для калибровки порогов.

## Установка

Корень установки стабилен как `human-writing-ru/` — кладите его в каталог навыков вашего агента:

```bash
# Вариант 1: из git
git clone https://github.com/alexeydott/human-writing-ru.git \
  .claude/skills/human-writing-ru

# Вариант 2: из релиз-архива (корень ZIP уже называется human-writing-ru/)
unzip dist/human-writing-ru-1.9.0-beta.4-full.zip -d .claude/skills/
```

Для других рантаймов те же пути: `.qwen/skills/`, `.github/skills/`, `.opencode/skills/`,
`.agents/skills/` — структура одна.

## Проверка целостности пакета

```bash
cd human-writing-ru
python -m pip install PyYAML   # один раз
python scripts/validate_skill.py
```

Успех — код возврата 0 без строк `error:`. Проверка включает имя каталога, разделение
version/policy_version, ссылки, контракты реестров и оценочных наборов, фиксированные SHA.

## Полный набор проверок

Прогоняется после любых изменений кода (см. также [Contributing](contributing.md)):

```bash
python scripts/validate_skill.py
python tests/test_check_prose_ru.py
python tests/test_corpus_tools.py
python tests/test_benchmark_tools.py
python tests/test_ablation_tools.py
python tests/test_ablation_v3.py
python tests/test_external_heldout_tools.py
python tests/test_external_gate_runner.py
python tests/test_edit_integrity.py
python tests/test_ab_eval_tools.py
python tests/test_lite_builder.py
python tests/test_validation_mutations.py
python tests/test_validation_md_scan.py
python scripts/validate_eval_design.py
python scripts/audit_eval_coverage.py
```

Каждый тест выводит `OK` при успехе.

## Первый прогон линтера

```bash
# Текстовый отчёт для заданного режима (prose | technical | oral)
python scripts/check_prose_ru.py --mode prose article.md

# Машинный вывод + измеряемые признаки без стилистического вердикта
python scripts/check_prose_ru.py --json --features-only article.md
```

Набор флагов: `--json`, `--mode <reжим>`, `--include-quotes`, `--features-only`.
Пороги в `profiles/editorial-baseline.json` — экспертный baseline до корпусной калибровки,
не языковая норма; файлы линтера заморожены в политике 1.4.0 (см. [Architecture](architecture.md)).

## Краткая инструкция для диалога

Автономная версия Skill (без локальных файлов и программ, ≤2000 знаков) формируется
сборщиком через `scripts/build_lite.py` и лежит рядом с выпуском в `dist/`.

## Дальше

- [Architecture](architecture.md) — структура проекта и замороженные области
- [Data и pipeline](data-and-pipeline.md) — корпуса, источники, held-out v3
- [Release](release.md) — сборка выпуска
- [Contributing](contributing.md) — правила разработки

## See Also

- [Architecture](architecture.md) — модули и правила зависимостей
- [Contributing](contributing.md) — цикл разработки и проверки
