# human-writing-ru 1.9.0-beta.2


> Версия пакета: **1.9.0-beta.2**. Замороженная лингвистическая/линтерная policy остаётся **1.4.0**; эти номера намеренно разделены.

Русская адаптация `human-writing`, ориентированная на генерацию, редактуру и адаптацию русских текстов **в разных условиях**, а не на одну модель «хорошей публицистики».

## Что изменено в 1.9.0-beta.2

- Добавлен русскоязычный адаптационный слой по `blader/humanizer` 2.11.0: `references/ai-writing-patterns.md`.
- Humanization теперь явно работает как редакторский проход, а не как детектор авторства: одиночные признаки не считаются доказательством, факты и голос имеют приоритет.
- Не перенесены буквально англоязычные правила про запрет тире, прямые кавычки и дефисные пары.
- Добавлено MIT-attribution в `THIRD_PARTY_NOTICES.md`; policy линтера 1.4.0 не менялась.


1. Добавлен встроенный режим нормализации и редакторской проверки технических заданий без изменения frozen linguistic policy 1.4.0.
2. `references/technical-specification.md` задаёт workflow безопасной переработки требований: инвентаризация смысла → редактура → integrity check → повторный requirements audit.
3. Новый `check_tz_ru.py` проверяет placeholders, субъективные критерии, слабую/конфликтующую модальность, возможную неатомарность, неочевидную проверяемость, неоднозначные ссылки, неизмеримые сроки, слишком общую безопасность, повторы, трассируемость и наличие приёмки.
4. Русские сообщения/правила вынесены в `profiles/tz-rules.ru.json`; структурные профили — `generic`, `gost34`, `gost19`. ГОСТ-профили не включаются автоматически и не заявляют сертификацию соответствия.
5. Safe normalization меняет только пробельное оформление; смысловые autofix запрещены. После смысловой правки используется существующий `check_edit_integrity.py`.
6. Проведены отдельные passes 15–18: gap analysis, rule design, false-positive pruning и integration/safety review; добавлены targeted positive/negative controls.



## Что изменено в 1.7.0-beta.2

1. **Packaging/spec:** install-root стабилен как `human-writing-ru/`; `SKILL.md` использует YAML frontmatter с `license`, `compatibility`, `metadata.version=1.7.0-beta.2` и отдельно `metadata.policy_version=1.4.0`. Self-validator проверяет имя каталога, version split, ссылки, literal `\n`, registry/eval contracts и frozen SHA.
2. **Decision protocol v3:** candidate строится только на calibration-компонентах и оценивается на untouched validation. Connected split объединяет известные author/split/source-document/independence связи; case/whitespace-варианты человеческих provenance labels нормализуются, а opaque IDs остаются case-sensitive.
3. **Evidence gates:** кроме 50 документов / 10 000 слов действуют profile/source/channel/author diversity и signal-specific eligibility/diversity/minimum split. `unknown`, `n/a` и другие sentinel values не считаются разнообразием; source concentration проверяется по документам и word mass.
4. **Natural-alert adjudication:** `actionable` и `non_actionable` — decisive labels; `uncertain` сохраняется в отчёте, но не улучшает и не ухудшает actionable precision и не помогает evidence gate. Annotation IDs должны ссылаться на реальный document/signal pair и не могут конфликтовать.
5. **Acquisition/validation integrity:** exact dedupe acquisition scoped по `(profile, sha256)`, чтобы межпрофильный routing conflict не исчез до validator. Validator блокирует одинаковый текст в разных profiles, rebase-ит пути при custom output и создаёт только representative `manifest.validated.csv`. v3 повторно проверяет файл SHA и exact-dedup перед решением.
6. **Network runner:** current orchestrator вызывает только v3, требует clean validator result, использует fresh workspace по умолчанию и разрешает resume только явно и только для выбранных source IDs. Источники с `format_unverified` не участвуют в decision-run по умолчанию.
7. **Source feasibility/provenance:** technical default-set дополнен русской документацией Kubernetes; local corpora могут передавать проверенные speaker/author/split/document boundaries через sidecar `manifest.csv`. Duma добавлена как отдельный oral stratum; Putin XML не получает фиктивного единого автора.
8. **Runtime bug fixes:** исправлен LJSearch adapter, который после успешной загрузки мог обращаться к неопределённым `profile/channel`; regression-тест теперь воспроизводит успешный сетевой ответ без реального интернета.
9. **Edit integrity:** `check_edit_integrity.py` отслеживает числа, даты, валюты, URL, число+единица, модальность, отрицание, условия, attribution, quotes и консервативные entity-like изменения. URL path/query сохраняют регистр; отсутствие findings не трактуется как доказательство смысловой эквивалентности.
10. **Generative A/B:** workspace фиксирует current/previous skill IDs, SHA eval-набора и копирует input artifacts с SHA. Aggregator требует полную матрицу по умолчанию; diagnostic incomplete mode не выдаёт непарные headline deltas и сравнивает только совпадающие `(case, run_index)`.
11. **Что намеренно не изменено:** `check_prose_ru.py`, historical `ablate_signals.py` и `editorial-baseline.json` остаются byte-identical frozen policy 1.4. Никакие новые threshold или claims о generative superiority не активируются без внешнего v3 held-out и реального A/B.

## Что изменено в 1.6.1

1. Лингвистическая политика и пороги 1.4 по-прежнему заморожены. SHA-256 `check_prose_ru.py`, `ablate_signals.py` и `profiles/editorial-baseline.json` фиксируются в `benchmark/external-heldout/FROZEN_INPUT_SHA256.json` и проверяются до/после network gate.
2. Добавлен `scripts/run_external_heldout_gate.py`: автоматизированный порядок `network acquisition → deduplicating validator → old → candidate → off`. Последний этап физически не вызывается, пока все пять профилей не проходят ≥50 независимых документов и ≥10 000 слов.
3. Исправлены acquisition-only дефекты: factRuEval profile/channel, percent-encoding GitHub paths, multi-ZIP provenance, CSV/TSV natural-row boundaries. Yandex Cloud docs и Putin Corpus получили прямые GitHub-tree adapters; RuREBus — multi-part ZIP adapter.
4. Добавлен hard process timeout на один сетевой источник, чтобы недоступный endpoint не блокировал сбор остальных профилей.
5. В build runtime реальная materialization всё ещё дала 0 документов: проверочный сетевой запуск заблокирован transport-ограничением среды, а RusLawOD дополнительно требует optional `datasets`. Поэтому `manifest.validated.csv` остаётся пустым и `old → candidate → off` **не запускался**.
6. Подробности: `research/pass-12-network-materialization-gate.md`, `benchmark/external-heldout/NETWORK_GATE.md`, `benchmark/external-heldout/LINKS.md`.

## Что изменено в 1.6.0

1. Этот проход не меняет лингвистическую политику 1.4: активные пороги заморожены, `check_prose_ru.py` и `ablate_signals.py` имеют те же SHA-256, что и до прохода.
2. Freeze-validator исправлен: готовность теперь вычисляется по **всем пяти** профилям из `profiles/editorial-baseline.json`, включая `technical`.
3. Для `technical` добавлен реальный внешний источник — русская документация Yandex Cloud. Для `oral` добавлены естественно длинные корпуса речей/устных выступлений; короткие ASR utterances по-прежнему нельзя произвольно объединять.
4. В текущем build runtime bulk materialization внешних текстов не состоялась. Реально созданный `benchmark/external-heldout/materialized/manifest.validated.csv` содержит только заголовок; validation-report показывает 0 документов / 0 слов во всех пяти профилях.
5. Поэтому `old → candidate → off` **не запускался**. Это зафиксировано машинно в `benchmark/external-heldout/ABLATION_NOT_RUN.json`; пороги 1.4 не изменены.
6. Подробный результат исследования: `research/pass-11-external-heldout-freeze.md`; ссылки и provenance: `benchmark/external-heldout/LINKS.md`.

## Что изменено в 1.5

1. Код линтера и пять исследуемых порогов **не изменялись**. Контрольные SHA-256 для `scripts/check_prose_ru.py` и `scripts/ablate_signals.py` сохранены в `benchmark/external-heldout/UNCHANGED_CODE_SHA256.json`.
2. Добавлен внешний held-out acquisition layer: `benchmark/external-heldout/SOURCE_REGISTRY.json`, `SOURCE_MANIFEST.csv`, `LJSEARCH_SAVED_COPY_SEEDS.csv`, `LINKS.md` и `MATERIALIZATION_STATUS.json`.
3. Для `prose/blog` основной путь — LJSearch saved copies; Zenodo LiveJournal Dataset оставлен только как format-unverified fallback; для `media` — исходные документы factRuEval; для `product` — реальные RBC/Ruward cases; для `official` — RusLawOD; для `oral` — несколько разговорных источников с сохранением естественных границ диалогов/сессий.
4. `scripts/materialize_external_heldout.py` получает raw-данные **во внешнюю рабочую директорию**, сохраняет URL/provenance/SHA и формирует acquisition `manifest.csv`; при полном/частичном сбое возвращает ненулевой код. После дедупликации неизменённому `ablate_signals.py` передаётся только `manifest.validated.csv`.
5. `scripts/validate_external_heldout.py` не считает дубли и очевидные репосты независимыми документами, отдельно показывает channel/source concentration и sample eligibility для пяти сигналов и создаёт deduplicated `manifest.validated.csv` для неизменённого ablation-runner.
6. В среде сборки outbound network контейнера недоступен, поэтому каталог источников не выдаётся за materialized benchmark: фактически материализовано 0 внешних документов, freeze gate не объявлен достигнутым.
7. Full raw copyrighted LiveJournal/media/product texts в ZIP не включаются; релиз хранит ссылки, код получения, provenance, hashes и будущие агрегаты.

См. `benchmark/external-heldout/README.md` и особенно `benchmark/external-heldout/LINKS.md`.

## Что изменено в 1.4

1. Проведён отдельный ablation-pass пяти оставшихся сигналов: `road-sign-density`, `sentence-uniformity`, `long-sentence`, `one-sentence-paragraphs`, `context-jargon-density`.
2. Для каждого сигнал сравнивается строго как `старый порог → консервативный candidate → off`, без одновременной перенастройки остальных.
3. Добавлен `scripts/ablate_signals.py`, preregistered `benchmark/ablation/spec.json` и targeted positive controls.
4. Small local probe отделяет natural held-out, lexical secondary controls и out-of-domain guards; тексты сторонних пакетов не перераспространяются.
5. Freeze gate 50 независимых документов + 10 000 слов на основной профиль **не достигнут**, поэтому ни один из пяти активных порогов не изменён. Это отрицательный, но полезный результат: версия не выдаёт недостаточную выборку за корпусную калибровку.
6. Предыдущий pilot 1.3 используется только как дополнительное подтверждение низкого alert burden; без per-document feature vectors он не участвует в расчёте новых квантилей.

См. `benchmark/ablation/README.md` и `benchmark/ablation/LOCAL_PROBE_RESULTS.json`.

## Что изменено в 1.3

1. Выполнен малый real-corpus pilot для детерминированного линтера на одинаковых текстах.
2. 1.1 и 1.2 в pilot дали одинаковый результат, поэтому архитектурные изменения 1.2 не выдаются за доказанное улучшение линтера.
3. Плотность тире/двоеточий оставлена как исследовательский признак, но отключена как пользовательское предупреждение.
4. `hype` стал контекстно-профильным: серия + плотность; в technical/official отключён.
5. Добавлена воспроизводимая папка `benchmark/` и runner для сравнения распакованных версий.

См. `benchmark/PILOT_RESULTS.json` и `benchmark/METHODOLOGY.md`.

## Что изменилось в 1.2

- задача теперь описывается по осям operation × origin × factuality × channel/register × audience;
- добавлены ветки `non-native-russian.md`, `translated-russian.md`, `audience-accessibility.md`, `language-variation.md`;
- проведено пять исследовательских проходов; выводы находятся в `research/`;
- `DATA_PLAN.md` задаёт схему данных для жанровой, L2, переводной, доступной и диагностической оценки;
- пороги `check_prose_ru.py` вынесены в `profiles/editorial-baseline.json` и явно считаются экспертным baseline, а не нормой языка;
- `--features-only` отдаёт измеряемые признаки без стилистического вердикта;
- `extract_corpus_features.py` поддерживает CSV-манифест с метаданными условий;
- `calibrate_profiles.py` умеет строить распределения по произвольным группам и фильтровать слишком короткие документы;
- eval-набор расширен до native/L2/translated, accessibility, coreference, media, social, technical, oral, fiction и high-stakes factual;
- добавлены `false_positive_cases.json` и rule-level `grammar_diagnostic_plan.json`;
- exact-string match запрещён как основная метрика редакторских задач;
- добавлен аудит покрытия eval-набора `scripts/audit_eval_coverage.py`.

## Проверка пакета

```bash
python3 scripts/validate_skill.py
python3 tests/test_check_prose_ru.py
python3 tests/test_corpus_tools.py
python3 tests/test_benchmark_tools.py
python3 tests/test_ablation_tools.py
python3 tests/test_ablation_v3.py
python3 tests/test_external_heldout_tools.py
python3 tests/test_external_gate_runner.py
python3 tests/test_edit_integrity.py
python3 tests/test_ab_eval_tools.py
python3 tests/test_validation_mutations.py
python3 scripts/validate_eval_design.py
python3 scripts/audit_eval_coverage.py
```

Локальный GitHub Actions-equivalent held-out workflow с обязательными внешними
корпусами запускается отдельно:

```bash
python3 -m pip install datasets PyYAML pypdf
python3 scripts/fetch_local_heldout_corpora.py
python3 scripts/run_local_heldout_workflow.py
```

Скачанные archives/PDF, подготовленные тексты и результаты находятся в
игнорируемом `data/` и не входят в release ZIP. Краткое руководство по
источникам, инструментам и локальному воспроизведению находится в
`data/README.md`.

## Калибровка на локальной выборке

Создайте манифест по образцу `data/corpus_manifest.example.csv`, затем:

```bash
python3 scripts/extract_corpus_features.py \
  --manifest data/corpus_manifest.csv \
  --output data/features.csv

python3 scripts/calibrate_profiles.py data/features.csv \
  --group-by channel,target_register \
  --min-docs 20 \
  --min-words-per-doc 100 \
  --output data/distributions.json
```

Для коротких чатов/соцсетей размер документа и группы следует задавать отдельно. Полученные квантили — **описание выборки, не языковая норма**.

## Данные и лицензии

Большие сторонние корпуса не включены в ZIP. В релизе находятся только схемы, маленькие собственные eval-примеры, инструменты извлечения признаков и ссылки. Для каждого внешнего набора нужно отдельно проверить условия использования и записать их в манифесте. См. `DATA_PLAN.md` и `SOURCES.md`.

## Ограничения beta

- выполнен только малый real-corpus pilot детерминированного линтера; он не является репрезентативной корпусной калибровкой;
- generative A/B между версиями Skill ещё не проведён: pilot сравнивает только `check_prose_ru.py`;
- rule-level GEC и coreference представлены планом/evals, а не встроенным тяжёлым NLP-анализатором;
- незакрытые измерения видны через `scripts/audit_eval_coverage.py`.

## Лицензия

MIT; upstream-лицензия сохранена.
