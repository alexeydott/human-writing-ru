[← Data и pipeline](data-and-pipeline.md) · [Back to README](../README.md) · [Contributing →](contributing.md)

# Release

Детерминированная сборка установочного пакета: состав, контроль целостности и публикация.

## Сборка

```bash
python scripts/build_release.py
```

Без параметров скрипт пишет в `dist/`:

- `human-writing-ru-<версия>-full.zip` — установочный пакет (корень архива — стабильное имя
  каталога `human-writing-ru/`, версия — только в имени архива и метаданных);
- `human-writing-ru-<версия>-full.zip.sha256.txt` — контрольная сумма;
- обновлённые `FILES.sha256` и `PACKAGE_CONTENTS.md`;
- `quality/RELEASE_INTEGRITY.json` — snapshot целостности текущего пакета.

`--output-dir <каталог>` — вынести артефакты в другое место (например, временный при тестах).

Требование: корневой каталог репозитория обязан называться `human-writing-ru`.

## Что происходит внутри (порядок шагов)

1. `clean_generated()` — удаление локальных runtime-артефактов (`__pycache__`, `.pytest_cache`,
   `.coverage`, `.pyc`) перед расчётом манифестов.
2. `write_lite()` — генерация автономной краткой инструкции `human-writing-ru-lite.md`.
3. `write_release_integrity()` — сверка SHA замороженных входов и ключевых файлов, запись
   `quality/RELEASE_INTEGRITY.json` с флагом `frozen_inputs_match`.
4. `write_hash_manifest()` — `FILES.sha256` по всем упаковываемым файлам.
5. `write_inventory()` — `PACKAGE_CONTENTS.md` со счётчиками по каталогам.
6. `validate()` — запуск `scripts/validate_skill.py`; **сборка останавливается**, если самопроверка упадёт.
7. Формирование ZIP (детерминированные timestamps `FIXED_DT`, deflate level 9, отсортированные пути)
   и записи SHA-256.

Скрипт готовит только локальные файлы для последующей публикации. Он **не создаёт и не
публикует GitHub-релиз** — это отдельный шаг человека.

## Что попадает в пакет / что исключается

Источники истины: константы в `scripts/build_release.py` и автогенерируемый `PACKAGE_CONTENTS.md`.

**Всегда включаются:** `SKILL.md`, `VERSION`, `LICENSE`, `references/*`, `profiles/*`,
`scripts/*`, `tests/*`, `benchmark/**`, `evals/**`, `research/**`, `quality/**`, `agents/*`,
`.github/workflows/heldout-gate.yml`, `data/README.md`, `data/corpus_manifest.example.csv`
и прочие доковые файлы в корне.

**Исключаются из архива:**

- каталоги: `.git`, `.agents`, `.ai-factory`, `.claude`, `.codex`, `.opencode`, `.qwen`,
  `.venv`, `.vscode`, `node_modules`,
  все cache-каталоги (`__pycache__`, `.pytest_cache`, `.mypy_cache`, `.ruff_cache`);
- `.github/skills/` — каталог навыков локального установщика агента;
  из `.github` в пакет попадает только `.github/workflows/heldout-gate.yml`;
- `Taskfile.yml` — dev-автоматизация локальной машины, не часть Skill;
- файлы локального AI-agent-контекста (зеркало `.gitignore`): `.mcp.json`, `.ai-factory.json`,
  `.agentready.yml`, `opencode.json`, `skills-lock.json`, `AGENTS.md`, `CLAUDE.md`, `RULES.md`;
- содержимое `data/` кроме двух «упаковываемых» файлов (см. выше);
- предыдущие архивы и их `.sha256.txt` внутри `dist/` (чтобы релиз не поглощал сам себя);
- `FILES.sha256` и `PACKAGE_CONTENTS.md` исключены из самого себя (защита от само-ссылки в хеш-манифесте).

Полные сторонние корпуса и результаты workflow **никогда** не попадают в архив.

Каталоги локальных агентов-контекстов (`.claude/`, `.qwen/` и т.п.) установлены в дереве
junction-ссылками на сторонние skill-пакеты; обход дерева в сборщике пропускает битые
репар-точки, а `clean_generated()` не заходит в исключаемые каталоги, чтобы не трогать
runtime-артефакты глобальных skill-пакетов пользователя. Регрессионное отсутствие этих
каталогов в архиве проверяет `tests/test_release_builder.py`.

## Контроль целостности

- `FILES.sha256` хеширует каждый упакованный файл, кроме самого себя и `PACKAGE_CONTENTS.md`.
- `quality/RELEASE_INTEGRITY.json` отслеживает ключевые файлы ТЗ-нормализации, Humanizer-адаптации
  и frozen-входов; поле `frozen_inputs_match` должно быть `true`.
- Regression-тест сборщика (`tests/test_release_builder.py`) проверяет отсутствие локальных
  cache/build artifacts и наличие ключевых integration-файлов в integrity snapshot.

## Лицензии и third-party

Авторство и лицензии сторонних материалов (upstream Human Writing MIT, blader/humanizer 2.11.0)
зафиксированы в [THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md). Перед включением нового
внешнего набора проверьте условия использования и запишите их в манифест.

## Публикация

После локальной сборки человек вручную публикует архив на GitHub (release/asset) или иным
согласованным способом. Номер версии в имени архива берётся из `VERSION` и обязан совпадать с
frontmatter `SKILL.md`, верхним разделом `CHANGELOG.md` и заголовком `README.md`.

## See Also

- [Data и pipeline](data-and-pipeline.md) — что исключается из пакета и почему
- [Contributing](contributing.md) — правила версионирования и самопроверки
- [Getting Started](getting-started.md) — установка из релиз-архива
