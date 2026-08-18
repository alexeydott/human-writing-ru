# Локальные данные и воспроизведение рабочего конвейера held-out

`data/` — единый локальный корень. Загруженные корпуса, OCR-инструменты,
кэши и отчёты здесь не публикуются и исключены из архива выпуска. В Git
остаются только этот файл и маленький шаблон `corpus_manifest.example.csv`.

## Быстрый запуск

Из корня репозитория:

```powershell
python -m pip install datasets PyYAML pypdf pyarrow pandas
python scripts/fetch_local_heldout_corpora.py
python scripts/run_local_heldout_workflow.py
```

Загрузчик создаёт `data/<source_id>/manifest.csv`, а рабочий конвейер записывает все
результаты в `data/heldout-work/`. Для другого каталога используйте
`--data-dir`, `--local-corpus-root` или переменную `HUMAN_WRITING_RU_DATA_DIR`.

## Что скачивается и откуда

- `taiga_social` — 80 естественных записей из социальной коллекции Taiga;
  исходная страница загрузки: <https://tatianashavrina.github.io/taiga_site/downloads.html>.
- `duma_speeches_1994_2021` — 100 естественных парламентских выступлений из
  набора Discuss Data, Open Data Commons Attribution (ODC-By) 1.0:
  <https://discuss-data.net/dataset/fb52dac2-66e3-47a3-86c5-b2a3dadf41bf/>.
- `pravo_open_data` — 50 официальных документов с портала открытых данных:
  <https://publication.pravo.gov.ru/OpenData>. PDF при необходимости проходят
  локальный OCR.

Точные URL, SHA-256, правила отбора, лицензии и число документов сохраняются в
`data/LOCAL_CORPORA_REPORT.json` и сопроводительном файле происхождения `provenance.json` каждого источника.

## Средства

Нужны Python 3.10+, `datasets`, `PyYAML`, `pypdf`, `pyarrow`, `pandas`, Poppler
(`pdftoppm`) и Tesseract с `rus.traineddata` для OCR Pravo. Скрипт автоматически
ищет переносимый Tesseract в `data/_tools/tesseract/`; пути можно переопределить
переменными `PDFTOPPM_CMD` и `TESSERACT_CMD`. Для GitHub API локальный исполнитель
использует `GITHUB_TOKEN`/`GH_TOKEN`, либо учётные данные активной `gh auth`-сессии.

## Что проверяется

`run_local_heldout_workflow.py` сначала выполняет предварительную проверку пакета и
оценочного набора, затем запускает получение, проверку UTF-8/SHA-256/дубликатов,
представительный `manifest.validated.csv`, пять проверок размера профилей и только после них
`ablate_signals_v3.py`. Коды `3`, `6`, `7` означают неполный последующий gate,
а не повреждение корпуса; подробности находятся в
`data/heldout-work/NETWORK_GATE_RUN_REPORT.json` и
`data/heldout-work/ABLATION_DECISION_V3.json`.

Исходные сторонние тексты не добавляйте в коммит и не используйте для профилей
конкретных людей. Сохраняйте границы естественных документов и provenance
сопроводительный манифест; пример полей находится в `corpus_manifest.example.csv`.
