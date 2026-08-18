# External held-out acquisition

Этот каталог хранит **код и provenance для внешнего benchmark**, а не сам corpus. Цель — получить естественно ограниченные документы пяти профилей и пройти current decision protocol, не меняя frozen policy 1.4.

## Статусы источников

- `catalogued` — источник/условия зафиксированы;
- `fetched` — raw data реально получены во внешнюю workspace;
- `validated` — document-boundary, UTF-8/integrity и duplicate checks пройдены;
- profile-size eligible — после дедупликации профиль имеет ≥50 независимых документов и ≥10 000 слов;
- decision-evidence eligible — дополнительно пройдены v3 provenance diversity, signal eligibility/diversity и split minima.

URL или search snippet сам по себе никогда не считается materialized document.

## Рекомендуемый сетевой запуск

```bash
python3 -m pip install datasets PyYAML pypdf
python3 scripts/fetch_local_heldout_corpora.py
python3 scripts/run_local_heldout_workflow.py
```

Prepared corpora live under ignored `examples/<source_id>/` directories and are
auto-discovered by both the orchestrator and materializer. Use
`--local-corpus-root` or `HUMAN_WRITING_RU_EXAMPLES_DIR` for another location.
The local workflow also reuses `GITHUB_TOKEN`/`GH_TOKEN`, or the active `gh auth`
credential, for authenticated GitHub API reads without forwarding it to other hosts.

Current default source selection включает эти manual/local strata. Без соответствующих путей run остаётся diagnostic и не может честно пройти все v3 diversity gates.

Current orchestrator выполняет `acquisition → dedup validator → profile-size stage → v3 evidence protocol`. Historical `scripts/ablate_signals.py` сохранён byte-identical для воспроизведения 1.4, но **не используется current orchestrator для новых решений**.

Frozen `scripts/check_prose_ru.py`, historical `scripts/ablate_signals.py` и `profiles/editorial-baseline.json` сверяются с `FROZEN_INPUT_SHA256.json` до/после критических stages.

Подробные exit states и outputs: `NETWORK_GATE.md`.

## Ручная материализация

Примеры:

```bash
python3 scripts/materialize_external_heldout.py \
  --sources ljsearch_saved_copies factrueval_2016 \
  --output-dir ../heldout-work
```

```bash
python3 scripts/materialize_external_heldout.py \
  --sources yandex_cloud_docs_ru \
  --output-dir ../heldout-work
```

Для RusLawOD streaming нужен optional package `datasets`:

```bash
python3 -m pip install datasets
python3 scripts/materialize_external_heldout.py \
  --sources ruslawod_v3 \
  --output-dir ../heldout-work
```

Большие/вручную скачанные источники импортируются без изменения raw-файлов:

```bash
python3 scripts/materialize_external_heldout.py \
  --sources taiga_social \
  --local-corpus-root examples \
  --output-dir ../heldout-work
```

Нельзя нарезать один исходный документ на псевдонезависимые документы ради выполнения gate и нельзя произвольно склеивать несвязанные ASR utterances.

Для локального источника предпочтителен `<local-root>/manifest.csv`: `path` обязателен, а `author_or_group`, `split_group`, `source_document_id`, `independence_group`, `channel` позволяют передать уже проверенный provenance без угадывания. Без sidecar действует только `one .txt = one document`; автор не выводится из имени файла/URL.

Current network orchestrator начинает fresh workspace по умолчанию. `--resume` нужно указывать явно; старый manifest не может содержать source IDs вне текущего selection. `format_unverified` sources блокируются для decision use.

## Dedup/validation

```bash
python3 scripts/validate_external_heldout.py \
  --manifest ../heldout-work/manifest.csv \
  --output ../heldout-work/VALIDATION_REPORT.json \
  --validated-manifest ../heldout-work/manifest.validated.csv
```

`manifest.csv` — acquisition log. `manifest.validated.csv` содержит по одному представителю exact/near-copy/explicit-independence cluster и является **единственным допустимым входом current decision protocol**.

Validator требует уникальные непустые document IDs. Explicit source-local `source_document_id`/`independence_group` scope-ятся источником, чтобы одинаковые локальные IDs разных corpora не склеивали независимые документы; exact/near-copy detection остаётся cross-source.

## Decision protocol

```bash
python3 scripts/ablate_signals_v3.py \
  --manifest ../heldout-work/manifest.validated.csv \
  --output ../heldout-work/ABLATION_DECISION_V3.json \
  --annotation-template ../heldout-work/alert-adjudication.csv
```

Это не shortcut вокруг network gate: v3 самостоятельно повторно проверяет profile diversity, signal-specific eligibility/diversity и connected split minima. Candidate строится только на calibration и оценивается на untouched validation. Natural-alert usefulness требует отдельной adjudication.

`social`, `blog`, `media` остаются channel strata внутри существующих profiles; profile schema активного линтера этим benchmark не меняется.

## Release policy

Raw third-party texts по умолчанию **не включаются** в release ZIP. В пакет входят registry, ссылки, acquisition/validation code, hashes, provenance и агрегированные результаты. Условия конкретных источников остаются source-specific.

## Integrity snapshots

`benchmark/external-heldout/RELEASE_INTEGRITY.json` относится только к release `1.6.1-beta.1` и помечен `historical_snapshot=true`; его старые hashes не являются manifest текущего дерева. Текущую целостность package builder записывает в `quality/RELEASE_INTEGRITY.json`.

## Историческое состояние materialization

В build runtime проходов 1.6/1.6.1 внешний filesystem transport был недоступен. Поэтому packaged historical `materialized/manifest.validated.csv` содержит 0 data rows, а `FREEZE_GATE_STATUS.json`/`ABLATION_NOT_RUN.json` фиксируют только тот прошлый факт. Эти historical snapshots не являются current corpus result и не должны интерпретироваться как выполненный v3 benchmark.
