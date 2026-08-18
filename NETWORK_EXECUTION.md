# Network execution — decision protocol v3

Для реальной внешней материализации используется GitHub Actions workflow `.github/workflows/heldout-gate.yml` или обычная машина с Python 3.10+ и исходящим HTTPS.

## Один operational pipeline

```bash
python3 -m pip install datasets PyYAML pypdf
python3 scripts/fetch_local_heldout_corpora.py
python3 scripts/run_local_heldout_workflow.py
```

Загрузчик сохраняет raw-архивы, PDF и подготовленные sidecar-деревья в `./data`.
Каталог целиком локальный: он игнорируется Git и исключён из release builder. Runner
автоматически находит `data/<source_id>/manifest.csv`; альтернативный корень можно
передать через `--local-corpus-root` или `HUMAN_WRITING_RU_DATA_DIR`.
Для запросов к GitHub API локальный wrapper использует `GITHUB_TOKEN`/`GH_TOKEN`, а при
их отсутствии — credential активной сессии `gh auth`. Токен передаётся только на
`api.github.com`; GitHub Actions использует `${{ github.token }}` с `contents: read`.

Эквивалентный низкоуровневый запуск:

```bash
python3 scripts/run_external_heldout_gate.py \
  --output-dir data/heldout-work \
  --local-corpus-root data
```

`taiga_social`, `duma_speeches_1994_2021` и `pravo_open_data` входят в default source selection как необходимые потенциальные strata для текущих prose/oral/official diversity/author-provenance gates. Если локальные деревья не найдены, acquisition продолжится как диагностический запуск, но full v3 evidence gate ожидаемо останется недостижимым. Raw third-party corpora не следует помещать в публичный release только ради CI.

Runner выполняет строго:

1. проверку SHA frozen policy inputs;
2. acquisition источников независимо друг от друга;
3. dedup/validation и создание `manifest.validated.csv`;
4. profile-size stage для всех пяти профилей;
5. **только после него** запуск `scripts/ablate_signals_v3.py`;
6. v3 profile diversity + signal eligibility/diversity + connected calibration/validation split;
7. создание `alert-adjudication.csv`;
8. повторный запуск с `--annotations` после natural-alert adjudication;
9. повторную проверку frozen hashes.

Исторический `scripts/ablate_signals.py` сохраняется для воспроизведения 1.4, но current network runner его для новых решений не вызывает.

## Fresh workspace и resume

По умолчанию orchestrator начинает **fresh run**: удаляет прежние generated manifests/reports/decision outputs и не наследует старые строки `manifest.csv`. Сырые файлы могут физически оставаться в workspace, но в новый decision input попадают только строки текущего acquisition.

Продолжение предыдущего acquisition разрешается только явно через `--resume`. Existing manifest при этом должен содержать только source IDs из текущего `--sources`; иначе runner останавливается до benchmark. Это защищает gate от незаметного смешивания разных экспериментов.

## Local sidecar provenance

Для локальных corpora естественные границы и проверенную speaker/author metadata лучше передавать файлом `<local-root>/manifest.csv`. Минимальное поле — `path`; поддерживаются `id`, `author_or_group`, `split_group`, `source_document_id`, `independence_group`, `channel`. Путь обязан оставаться внутри local root, IDs должны быть уникальны, а channel — объявлен для source в registry.

Если sidecar отсутствует, fallback остаётся консервативным: **один `.txt` = один естественный документ**, без выдумывания автора. Например, публичный RUB TSV содержит дату/URL/text, но не отдельный speaker field, поэтому speaker нельзя восстанавливать эвристически из URL.

Источники со статусом `format_unverified` не допускаются в current decision run. Их можно исследовать materializer-ом только через явный research override; такой override network decision orchestrator не использует.

## Exit states

- `3` — один или несколько профилей не прошли 50 независимых документов / 10 000 слов; создаётся `DECISION_NOT_RUN.json`;
- `6` — profile-size stage пройден, но v3 diversity/signal/split evidence недостаточно; создаётся `DECISION_NOT_READY.json`;
- `7` — evidence gates пройдены, но natural-alert adjudication ещё требуется;
- `0` — все требуемые evidence/adjudication stages завершены; это **не** разрешение автоматически менять `editorial-baseline.json`, а только вход для явного policy review;
- другие ненулевые коды — integrity/subprocess failures.

Основной decision artifact — `ABLATION_DECISION_V3.json`. Даже `ready_for_decision_evaluation=true` означает достаточность preregistered evidence gates, а не доказанную языковую норму.
