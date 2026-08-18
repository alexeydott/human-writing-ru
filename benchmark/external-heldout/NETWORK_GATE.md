# Network held-out gate — v3

Этот orchestrator материализует внешний held-out и допускает current decision runner только после обязательных предварительных gates. Он не меняет лингвистические правила или active thresholds.

## Запуск

```bash
python3 -m pip install datasets PyYAML pypdf
python3 scripts/fetch_local_heldout_corpora.py
python3 scripts/run_local_heldout_workflow.py
```

По умолчанию runner автоматически использует `data/<source_id>/manifest.csv`.
Другой корень задаётся `--local-corpus-root` или `HUMAN_WRITING_RU_DATA_DIR`.

Без нужных local strata default run остаётся полезным acquisition probe, но current `prose` channel/author, `oral` author/source и `official` source-diversity gates не могут быть объявлены пройденными.

Для локально скачанного корпуса можно повторять:

```bash
--local-source SOURCE_ID=/path/to/corpus
```

По умолчанию запуск fresh: generated manifests/reports предыдущего experiment удаляются. Для явного продолжения используйте `--resume`; runner проверит, что существующий manifest не содержит чужих source IDs. Локальный `<local-root>/manifest.csv` может передать проверенный speaker/author/split provenance; без него materializer не выдумывает автора. Источники `format_unverified` в current decision-run запрещены.

После получения `alert-adjudication.csv` повторный запуск принимает:

```bash
  --annotations data/heldout-work/alert-adjudication.csv
```

## Жёсткий порядок

1. Проверить SHA-256 frozen `check_prose_ru.py`, historical `ablate_signals.py` и `profiles/editorial-baseline.json`.
2. Материализовать выбранные sources независимо друг от друга в acquisition `manifest.csv`.
3. Запустить `validate_external_heldout.py` и получить representative-only `manifest.validated.csv`.
4. Проверить все пять профилей: каждый должен иметь ≥50 независимых документов и ≥10 000 слов.
5. Только после шага 4 вызвать **`ablate_signals_v3.py`**, никогда не historical runner для новых решений.
6. Внутри v3 проверить profile/source/channel/author diversity, signal-specific eligibility и connected calibration/validation split.
7. Сформировать natural-alert annotation template.
8. После adjudication повторить v3; candidate/off остаются `pending_human_review` даже при поддерживающих данных.
9. Повторно проверить frozen hashes.

## Exit codes

- `3` — profile-size stage не достигнут; `DECISION_NOT_RUN.json`;
- `6` — profile stage пройден, но v3 evidence gate неполон; `DECISION_NOT_READY.json`;
- `7` — v3 evidence достаточно, требуется natural-alert adjudication;
- `0` — preregistered evidence/adjudication stage завершён; требуется явный policy review;
- `2/4/5` — acquisition/validator/frozen-integrity/decision subprocess failure.

## Основные outputs

- `manifest.csv` — acquisition log, **не** статистическая выборка;
- `manifest.validated.csv` — deduplicated representative-only decision input;
- `VALIDATION_REPORT.json` — profile-size/dedup diagnostics;
- `ABLATION_DECISION_V3.json` — current decision-protocol result;
- `alert-adjudication.csv` — natural-alert review template;
- `NETWORK_GATE_RUN_REPORT.json` — network/protocol/frozen-hash provenance;
- `DECISION_NOT_RUN.json` или `DECISION_NOT_READY.json` — явные блокирующие состояния.

Raw third-party texts не включаются в release ZIP без отдельной проверки прав конкретного источника.
