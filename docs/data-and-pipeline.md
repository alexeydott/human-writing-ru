[← Architecture](architecture.md) · [Back to README](../README.md) · [Release →](release.md)

# Данные и pipeline held-out

Где живут корпуса, откуда берутся наборы и как воспроизвести рабочий конвейер локально.

## Каталог данных

| Путь | Содержимое | В Git/ZIP |
|------|------------|-----------|
| `data/<source_id>/` | Скачанные архивы/PDF и подготовленные тексты по источникам | нет (gitignored) |
| `data/heldout-work/` | Результаты локального workflow v3 | нет (gitignored) |
| `data/README.md`, `data/corpus_manifest.example.csv` | Краткое руководство и шаблон манифеста | да (единственные файлы `data/` в пакете) |

Корень переопределяется переменной окружения `HUMAN_WRITING_RU_DATA_DIR`.
Полные сторонние тексты, защищённые авторским правом, в выпуск не включаются: в пакете
схемы, ссылки, хеши и инструменты. Условия использования каждого внешнего набора проверяются
отдельно и записываются в его манифест.

## Профили и основные источники

Детальный provenance — в [SOURCES.md](../SOURCES.md) и `benchmark/external-heldout/LINKS.md`;
руководство по локальному воспроизведению — в `data/README.md`.

| Профиль | Основной путь источников |
|---------|--------------------------|
| `prose` / blog | LJSearch по original-URL (saved-copy-маршрут детерминированно блокируется по RU-IP; 58 документов в прогоне 1.6); Zenodo LiveJournal отклонён (бинарный граф bcsr без текста) |
| `prose` / social | Taiga (`taiga_social`, user-level provenance из заголовков записей) |
| `prose` / media | Исходные документы factRuEval |
| product | Реальные кейсы RBC (страницы отдельных материалов) и Ruward (содержательные блоки) |
| official | RusLawOD (полные нормативные документы, контроль near-copies; шар `ruslawod_11`, локальное дерево, селекция v2 с капом 4000 слов) + pravo |
| oral | Готовые речи, Q&A/интервью, спонтанные диалоги; короткие ASR-высказывания не склеиваются |
| technical | Русская документация Kubernetes + Yandex Cloud Docs (обход поддерева `ru/`) |

Схема данных для оценочных наборов — [DATA_PLAN.md](../DATA_PLAN.md).

## Локальный workflow (эквивалент CI-пайплайна)

Требует исходящего HTTPS и опциональных зависимостей:

```bash
python -m pip install datasets PyYAML pypdf
python scripts/fetch_local_heldout_corpora.py     # корпуса в data/<source_id>/
python scripts/run_local_heldout_workflow.py       # результаты в data/heldout-work/
```

CI-вариант с внешними корпусами описывает `.github/workflows/heldout-gate.yml`.
В среде без сети получение может закончиться 0 документами — это ограничение среды,
а не баг логики; фиксация — пустой манифест со схемой и статус-JSON, а не «пройденный» gate.

## Протокол принятия решений v3

Порядок фиксирован; исполнитель вызывает только v3:

1. Сетевое/локальное получение источников (`materialize_external_heldout.py`).
2. Exact/near-copy dedup c областью `(profile, sha256)` → `manifest.validated.csv`.
3. Size + diversity gates **по всем пяти профилям** (≥50 независимых документов и ≥10 000 слов;
   `unknown`/`n/a` не считаются разнообразием; проверяется концентрация источника).
4. Signal eligibility + signal diversity per applicable signal.
5. Связанный split calibration/validation без пересечения известного
   `author` / `split` / `source-document` / `independence`.
6. Кандидатские пороги строятся **только на calibration**.
7. Разметка natural alerts на validation: решающие метки `actionable` / `non_actionable`;
   `uncertain` сохраняется в отчёте, но не влияет на точность `actionable`.
8. Решение `keep old / candidate / off` принимает человек; active profile не меняется автоматически.

Статус: первый полный цикл завершён прогоном `data/heldout-work-policy-1.6` (911
валидированных документов, все пять профилей прошли gates, 217 natural alerts размечены
слепо); решения человека применены политикой **1.5.0** (детали —
[POLICY_RERUN_PLAN.md](../POLICY_RERUN_PLAN.md) и CHANGELOG).

Промежуточные факты фиксируются артефактами: `MATERIALIZATION_STATUS.json`,
`FREEZE_GATE_STATUS.json`, `ABLATION_NOT_RUN.json`, `probes/PROBE_REPORT.json`.

## Калибровка на собственной выборке

```bash
# 1) Извлечь признаки по манифесту (образец: data/corpus_manifest.example.csv)
python scripts/extract_corpus_features.py \
  --manifest data/corpus_manifest.csv \
  --output data/features.csv

# 2) Построить распределения по группам
python scripts/calibrate_profiles.py data/features.csv \
  --group-by channel,target_register \
  --min-docs 20 --min-words-per-doc 100 \
  --output data/distributions.json
```

Полученные квантили — **описание выборки, не языковая норма**. Для коротких чатов/соцсетей
размер документа и группы задаётся отдельно.

## See Also

- [Architecture](architecture.md) — место pipeline в структуре проекта
- [Release](release.md) — что попадает в выпуск и чего нет
- [Contributing](contributing.md) — как добавлять новые источники и сигналы
