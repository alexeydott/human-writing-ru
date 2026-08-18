# Получение внешнего held-out

Этот каталог хранит **код и происхождение данных для внешнего контрольного набора**, а не сам корпус. Цель — получить естественно ограниченные документы пяти профилей и пройти текущий протокол принятия решения, не меняя замороженную политику 1.4.

## Статусы источников

- `catalogued` — источник/условия зафиксированы;
- `fetched` — исходные данные реально получены во внешний рабочий каталог;
- `validated` — проверены границы документов, UTF-8/целостность и дубли;
- пригоден по размеру профиля — после устранения дублей профиль имеет ≥50 независимых документов и ≥10 000 слов;
- пригоден по доказательствам решения — дополнительно пройдены проверки происхождения данных, пригодности/разнообразия сигналов и минимальных split v3.

URL или search snippet сам по себе никогда не считается materialized document.

## Рекомендуемый сетевой запуск

```bash
python3 -m pip install datasets PyYAML pypdf
python3 scripts/fetch_local_heldout_corpora.py
python3 scripts/run_local_heldout_workflow.py
```

Подготовленные корпуса находятся в игнорируемых каталогах `data/<source_id>/` и
автоматически обнаруживаются координатором и средством получения. Для другого
расположения используйте `--local-corpus-root` или `HUMAN_WRITING_RU_DATA_DIR`.
Локальный рабочий конвейер также использует `GITHUB_TOKEN`/`GH_TOKEN` или учётные данные
активной `gh auth` для авторизованных запросов к GitHub API, не передавая их другим узлам.

Текущий набор источников по умолчанию включает эти локальные слои. Без соответствующих
путей запуск остаётся диагностическим и не может честно пройти все проверки разнообразия v3.

Текущий координатор выполняет `acquisition → dedup validator → profile-size stage → v3 evidence protocol`. Исторический `scripts/ablate_signals.py` сохранён побайтно неизменным для воспроизведения 1.4, но **не используется текущим координатором для новых решений**.

Замороженные `scripts/check_prose_ru.py`, исторический `scripts/ablate_signals.py` и `profiles/editorial-baseline.json` сверяются с `FROZEN_INPUT_SHA256.json` до/после критических этапов.

Подробные exit states и outputs: `NETWORK_GATE.md`.

## Ручная материализация

Примеры:

```bash
python3 scripts/materialize_external_heldout.py \
  --sources ljsearch_saved_copies factrueval_2016 \
  --output-dir data/heldout-work
```

```bash
python3 scripts/materialize_external_heldout.py \
  --sources yandex_cloud_docs_ru \
  --output-dir data/heldout-work
```

Для потокового чтения RusLawOD нужен необязательный пакет `datasets`:

```bash
python3 -m pip install datasets
python3 scripts/materialize_external_heldout.py \
  --sources ruslawod_v3 \
  --output-dir data/heldout-work
```

Большие/вручную скачанные источники импортируются без изменения исходных файлов:

```bash
python3 scripts/materialize_external_heldout.py \
  --sources taiga_social \
  --local-corpus-root data \
  --output-dir data/heldout-work
```

Нельзя нарезать один исходный документ на псевдонезависимые документы ради выполнения проверки и нельзя произвольно склеивать несвязанные высказывания ASR.

Для локального источника предпочтителен `<local-root>/manifest.csv`: `path` обязателен, а `author_or_group`, `split_group`, `source_document_id`, `independence_group`, `channel` позволяют передать уже проверенное происхождение данных без угадывания. Без сопроводительного манифеста действует только правило `one .txt = one document`; автор не выводится из имени файла/URL.

Текущий сетевой координатор начинает новый рабочий каталог по умолчанию. `--resume` нужно указывать явно; старый манифест не может содержать ID источников вне текущего набора. Источники `format_unverified` блокируются для принятия решения.

## Устранение дублей и проверка

```bash
python3 scripts/validate_external_heldout.py \
  --manifest data/heldout-work/manifest.csv \
  --output data/heldout-work/VALIDATION_REPORT.json \
  --validated-manifest data/heldout-work/manifest.validated.csv
```

`manifest.csv` — журнал получения. `manifest.validated.csv` содержит по одному представителю кластера точных/близких копий или явно независимых документов и является **единственным допустимым входом текущего протокола решения**.

Проверка требует уникальные непустые ID документов. Явные локальные для источника
`source_document_id`/`independence_group` ограничиваются этим источником, чтобы одинаковые
локальные ID разных корпусов не склеивали независимые документы; поиск точных/близких
копий остаётся межисточниковым.

## Протокол принятия решения

```bash
python3 scripts/ablate_signals_v3.py \
  --manifest data/heldout-work/manifest.validated.csv \
  --output data/heldout-work/ABLATION_DECISION_V3.json \
  --annotation-template data/heldout-work/alert-adjudication.csv
```

Это не обход сетевой проверки: v3 самостоятельно повторно проверяет разнообразие профилей,
пригодность/разнообразие сигналов и минимумы связанного split. Кандидат строится только
на калибровке и оценивается на независимой проверке. Практическая ценность естественных
срабатываний требует отдельной разметки.

`social`, `blog`, `media` остаются слоями каналов внутри существующих профилей; схема профилей активного линтера этим контрольным набором не меняется.

## Правила выпуска

Исходные сторонние тексты по умолчанию **не включаются** в ZIP релиза. В пакет входят
реестр, ссылки, код получения/проверки, происхождение данных, хеши и агрегированные результаты.
Условия конкретных источников остаются отдельными для каждого источника.

## Снимки целостности

`benchmark/external-heldout/RELEASE_INTEGRITY.json` относится только к выпуску `1.6.1-beta.1` и помечен `historical_snapshot=true`; его старые хеши не являются манифестом текущего дерева. Текущую целостность сборщик релиза записывает в `quality/RELEASE_INTEGRITY.json`.

## Историческое состояние materialization

В среде сборки проходов 1.6/1.6.1 внешний транспорт файловой системы был недоступен. Поэтому включённый исторический `materialized/manifest.validated.csv` содержит 0 строк данных, а `FREEZE_GATE_STATUS.json`/`ABLATION_NOT_RUN.json` фиксируют только тот прошлый факт. Эти исторические снимки не являются результатом текущего корпуса и не должны интерпретироваться как выполненный контрольный набор v3.
