# Research report — foundation through policy 1.4

> Этот файл фиксирует исследовательскую основу, на которой была заморожена policy 1.4. Актуальный critical-review и decision protocol описаны в `research/pass-14-critical-review-v3.md`, `benchmark/ablation/spec-v3.json` и `quality/QUALITY_MODEL.md`.


## Цель

Проверить, какие данные нужны, чтобы Skill одинаково осторожно работал не только с нейтральной статьёй, но и с устной речью, соцсетями, learner Russian, переводным русским, технической/официальной прозой, доступностью, художественным голосом и high-stakes фактической редактурой.

## Проход 1. Корпусное покрытие

Нельзя калибровать «русский стиль» одним смешанным корпусом. НКРЯ предоставляет разные функциональные массивы, включая современную письменную, устную и интернет-речь; новый ГИКР VK добавляет масштабные социальные данные и социолингвистическую разметку.

Решение: ввели dimensions `channel`, `target_register`, `source_period`; калибровка строится по группам, а не по общей смеси.

Источники:
- https://ruscorpora.ru/corpus/main
- https://ruscorpora.ru/corpus/spoken
- https://ruscorpora.ru/news/281

## Проход 2. Происхождение текста

Learner Russian требует диагностики согласования, управления, морфологии и синтаксических отношений; переводной русский требует независимой проверки естественности и сохранения смысла. Translationese статистически обнаружим на уровне распределений, но это не превращает отличительные конструкции в ошибки.

Решение: отдельные references `non-native-russian.md` и `translated-russian.md`; dimensions `origin`, `learner_l1`, `translation_source`.

Источники:
- https://aclanthology.org/2024.lrec-main.1241/
- https://aclanthology.org/Q19-1001/
- https://aclanthology.org/2024.eacl-long.76/
- https://aclanthology.org/2021.ranlp-1.84/

## Проход 3. Аудитория и доступность

Понятность не сводится к коротким предложениям. Нужны знания аудитории, терминологическая нагрузка, структура и явность условий. Параллельные наборы упрощённого русского полезнее одной формулы читаемости.

Решение: `audience-accessibility.md`; отдельный `correction_goal=accessibility`; evals для обычного пользователя и школьника; запрет на инфантилизацию.

Источники:
- https://aclanthology.org/2021.bsnlp-1.8/
- https://aclanthology.org/2024.readi-1.6/
- https://www.w3.org/WAI/WCAG2/supplemental/objectives/o3-clear-content/
- https://www.w3.org/WAI/WCAG22/Understanding/unusual-words.html

## Проход 4. Оценка редактуры и связности

У одной исходной фразы могут быть несколько корректных редакций. Multi-reference Russian GEC демонстрирует различия между редакторами, особенно на лексическом уровне. Для текста уровня документа дополнительно нужны coreference, ellipsis и discourse.

Решение: exact-string не используется как основная метрика; добавлены критерии meaning/fact/modality/voice preservation и document-level задачи.

Источники:
- https://aclanthology.org/2024.eacl-long.76/
- https://arxiv.org/abs/2206.04925
- https://aclanthology.org/2025.acl-srw.91/

## Проход 5. Rule-level диагностика и over-editing

Общая метрика может улучшаться, пока отдельное правило деградирует. Поэтому нужен отчёт по классам ошибок и negative controls, где корректные конструкции должны остаться нетронутыми.

Решение: `false_positive_cases.json`, `grammar_diagnostic_plan.json`, over-edit rate в `METRICS.md`, rule-level план и новые регрессионные тесты.

Источники:
- https://aclanthology.org/2025.bea-1.38/
- https://aclanthology.org/2026.bea-1.32/

## Архитектурный проход

Agent Skills рекомендует реалистичные evals, baseline/previous-version сравнение, несколько запусков, assertions, human review и progressive disclosure. Эти принципы отражены в `SKILL.md`, `evals/` и `DATA_PLAN.md`.

Источники:
- https://agentskills.io/skill-creation/evaluating-skills
- https://agentskills.io/skill-creation/optimizing-descriptions
- https://agentskills.io/skill-creation/best-practices

## Что реализовано в beta.2

- 5 исследовательских проходов;
- 16 output eval scenarios;
- 20 trigger queries + train/validation split;
- 10 false-positive negative controls;
- rule-level grammar diagnostic plan;
- manifest-based corpus feature extraction;
- condition-aware grouping in calibration;
- filter for short documents;
- external expert-baseline profiles;
- eval coverage audit;
- checker regression tests and corpus-tool tests;
- исправленная обработка сокращений, инициалов, версий, времени, диапазонов, цитат и URL/code masking.

## Что ещё нельзя подтвердить

- Нельзя подтвердить, что beta.2 объективно лучше beta.1 на реальной работе, пока не выполнены многократные A/B прогоны агента.
- Нельзя считать активные числовые пороги корпусно обоснованными: они всё ещё помечены `expert_baseline_not_corpus_calibrated`.
- Нельзя считать 16 evals репрезентативными для всего русского письма.
- Не закрыты реальные данные по разным L1 learner-авторов, нескольким исходным языкам переводов, историческим периодам, таблицам и URL-heavy документам.

Эти пробелы намеренно отражены в `ROADMAP.md` и выводе `scripts/audit_eval_coverage.py`, а не заполнены синтетическими «доказательствами».


## Проход 6–9: real-corpus pilot и pruning

- На одинаковом pilot-наборе checker 1.1 и 1.2 показали одинаковую нагрузку; различий не приписывали без данных.
- Пунктуационные density alerts переведены в feature-only по умолчанию.
- Контекстный аудит `hype` выявил ложные сигналы на техническом «бесшовный единый вход» и фактическом «флагманский проект»; сигнал теперь требует серии и выключен в technical/official.
- RuCoLA отделён от style benchmark: он нужен как грамматический diagnostic/negative control, но отсутствие style-сигнала на ошибочном предложении не является failure.
- Релиз хранит только агрегаты и metadata сторонних корпусов, не сырые тексты.


### Точные агрегаты pilot

Одинаковый 15-документный набор, 1838 анализируемых слов:

- 1.1.0-beta.1: 11 findings, 8 документов с сигналом, 5.985 findings/1000 слов; `dash-density=3`, `colon-density=1`, `hype=6`, `nominalization=1`.
- 1.2.0-beta.2: результат совпал с 1.1.
- 1.3.0-beta.1 candidate: 1 finding на одном документе, 0.544/1000; остался `nominalization=1`.

Снижение количества emitted findings составляет 90.91% относительно 1.2 на этой выборке. Это **alert-burden reduction**, а не измерение числа языковых ошибок и не полноценный false-positive rate.


## Проход 10: ablation пяти оставшихся сигналов

Проверены `road-sign-density`, `sentence-uniformity`, `long-sentence`, `one-sentence-paragraphs`, `context-jargon-density` в режиме old → candidate → off. Natural held-out и synthetic positive controls разделены.

Доступный clean probe не достиг freeze gate и не показал целевого alert burden на in-scope документах. Поэтому ни один активный порог не изменён. Художественный фрагмент дал `long-sentence` при prose-mode, но оставлен только как domain guard: использовать его для подъёма нейтрального порога означало бы смешать жанры.

Добавлены `benchmark/ablation/`, `scripts/ablate_signals.py` и `tests/test_ablation_tools.py`. Следующая калибровка должна использовать те же preregistered arms на существенно большей отложенной выборке.


## Проход 11: внешний held-out и архивы LiveJournal

Цель прохода — перестать обсуждать пороги на маленьком probe и сначала построить воспроизводимый внешний held-out. Код линтера и ablation runner заморожены контрольными SHA-256.

### LiveJournal

LJSearch описывает себя как поиск по архиву русскоязычной части LiveJournal 2000–2017, полученному от Яндекса, и прямо указывает, что архив содержит в том числе давно удалённые записи. Поэтому для blog-stratum введён adapter, который ищет посты по нескольким нейтральным темам и забирает именно `savedcopy?post=...`. Seed URLs и discovery mirrors перечислены в `benchmark/external-heldout/LINKS.md`.

Дополнительная масштабная опора — Zenodo `LiveJournal Dataset`, DOI `10.5281/zenodo.7139731`: архив `livejournal.zip` 202.9 MB, CC BY 4.0, MD5 зафиксирован в registry. Это позволяет не зависеть только от динамического LJSearch.

### Media

`factRuEval-2016` полезнее sentence-level treebank для этой задачи, потому что публикует исходные `book_*.txt` documents. README указывает, что текст предложений сохранён из источника, а абзацы разделены двойным переводом строки. Репозиторий содержит MIT LICENSE. Эти документы подходят для независимого media-held-out без искусственного восстановления предложения из токенов.

### Product/business

RBC Companies cases и Ruward дают реальные русскоязычные кейсы с задачей, реализацией и результатами. Они используются только как локальный исследовательский web corpus: copyrighted bodies не входят в release. Validator отдельно показывает source concentration, потому что 50 кейсов одного агентства не должны интерпретироваться как широкое покрытие деловой прозы.

### Official/legal

RusLawOD v3 заявляет 304 382 акта и 194 425 905 tokens за 1991–2025. Проект указывает, что тексты правовых актов можно перераспространять как неохраняемые авторским правом, а прочие материалы проекта имеют отдельную CC BY-NC 4.0 лицензию. Для benchmark предпочтителен streaming sample полных acts с разнообразием органов/лет.

### Oral

Основная методическая проблема — document boundary. Russian Everyday Dialogues содержит только 20 коротких диалогов, а Common Voice Spontaneous Speech состоит из отдельных ответов/записей. Поэтому 50-документный oral freeze нельзя получать механическим склеиванием utterances. Нужны естественные разговоры/монологи/сессии и контроль speaker concentration.

### Что реально материализовано в сборочной среде

Web layer позволил проверить источники, лицензии и конкретные сохранённые LJSearch links, но container runtime не имеет рабочего outbound DNS. Direct acquisition probe к GitHub API завершился `Temporary failure in name resolution`. Поэтому в 1.5 не делается ложного заявления о freeze: `external_documents_materialized_in_release_build = 0`.

Это не меняет исследовательский дизайн: пакет теперь содержит acquisition/validation harness, который в сетевой среде получает raw corpus во внешнюю директорию, проверяет SHA/duplicates/document boundaries и только затем передаёт manifest неизменённому `ablate_signals.py`.
