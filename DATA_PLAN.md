# План данных для развития human-writing-ru

Цель — не обучать внутри пакета собственную языковую модель и не собирать «корпус хорошего русского» в одну кучу. Нужны **раздельные eval-, negative-control- и calibration-наборы**, потому что хорошие нормы для статьи, чата, перевода, learner Russian и технической инструкции различаются.

## 1. Какие измерения хранить у каждого примера

Минимальный манифест:

1. `operation`: generation / proofreading / light_edit / rewrite / adaptation / oral;
2. `origin`: native_original / L2 / translated / unknown;
3. `factuality`: factual / fiction / mixed / unknown;
4. `channel`: article / media / social / chat / technical / official / speech / fiction / other;
5. `audience`: expert / general / child_or_student / L2 / accessibility_specific / unknown;
6. `length`: sentence / short / medium / long;
7. `embedded_material`: none / quotes / code / urls / tables / mixed;
8. `risk`: ordinary / high_stakes_factual;
9. `target_register`: neutral / colloquial_written / professional / official / literary / oral / unknown;
10. `correction_goal`: norm_only / naturalness / clarity / accessibility / voice_preservation / mixed;
11. `source_period`: период создания текста, чтобы не смешивать историческую и современную норму;
12. для L2 — `learner_l1`, если законно и реально известно;
13. для перевода — `translation_source`, если известен исходный язык/семья;
14. `corpus` и `license_note` — происхождение и условия использования данных.

Пример: `data/corpus_manifest.example.csv`.

Метаданные L1, региона, возраста, пола и т. п. допустимы **только для анализа устойчивости и ложных срабатываний**. Не использовать их как инструкцию, «как должен писать человек такой группы».

## 2. Проход 1 — жанр, канал и современная вариативность

### Что изучать

Раздельные срезы НКРЯ и сопоставимых современных источников:

- Main — общий письменный reference;
- Media — журналистика;
- Social/GICR — интернет- и платформенная речь;
- Spoken — публичная и бытовая устная речь;
- SynTagRus/синтаксическая разметка — диагностические синтаксические признаки.

### Что измерять

Не только длину предложения:

- распределение длины, а не среднее;
- долю однофразовых абзацев;
- пунктуационные частоты;
- служебные переходы;
- номинализацию/пассивные оболочки;
- частоты разговорных частиц;
- цитатность и код/URL;
- разницу между каналами.

### Что нельзя делать

Нельзя смешать все жанры, посчитать один p95 и объявить его «нормой русского».

## 3. Проход 2 — неродной и переводной русский

### Learner Russian / GEC

Использовать RLC, RULEC-GEC, ReLCo, multi-reference GEC, LORuGEC и новые rule-level диагностические наборы.

Проверять отдельно:

- согласование;
- управление и падеж;
- предлоги;
- вид/время;
- порядок слов;
- пунктуационные правила;
- коллокации;
- семантическую приемлемость;
- unnecessary edits.

Multi-reference данные нужны потому, что у одного learner-предложения могут быть несколько корректных редакций.

### Переводной русский

Изучать параллельные оригинал/перевод выборки и исследования translationese. Группировать по исходному языку или языковой близости, если данные позволяют.

Главные метрики:

- сохранение смысла и модальности;
- естественность русского;
- устранение реальных калек;
- отсутствие «натурализации», меняющей факт, отрицание, условие или причинность.

Статистически отличимая черта переводов не является автоматически ошибкой.

## 4. Проход 3 — аудитория, читаемость и доступность

Использовать RuAdapt, русские исследования читаемости и специализированные наборы (например, юридическое упрощение), а также W3C WAI как требования к понятности для конкретных аудиторий.

Изучать:

- лексическую частотность;
- незнакомые термины/сокращения;
- вложенность синтаксиса;
- явность последовательности действий;
- сохранение обязательных условий;
- полезность примеров и навигационной структуры.

Не оценивать доступность одной длиной предложения и не переносить L2-упрощение на любого взрослого читателя.

## 5. Проход 4 — связность и сохранение смысла

Использовать RuCoCo, RusConText и ручные пары исходник/редактура.

Проверять:

- coreference;
- неоднозначные местоимения;
- эллипсис;
- дискурсивные связи;
- логическую последовательность;
- сохранение причинности и условий после редактуры.

Для длинных текстов нужен уровень документа: предложение может быть грамматичным и при этом разрушать связность абзаца.

## 6. Проход 5 — rule-level диагностика и negative controls

Свежие русские GEC-работы показывают, что общий score способен скрывать деградацию отдельного правила. Поэтому каждый релиз должен иметь:

- отчёт по типам ошибок, а не только общий pass rate;
- `evals/false_positive_cases.json` — корректные конструкции, которые нельзя «лечить»;
- отдельный over-edit rate;
- диагностику по сложным правилам пунктуации/морфологии для задач корректуры;
- ручную проверку случаев, где система изменила уже нормативный текст.

## 7. Отдельно изучать false positives / alert burden линтера

Собрать минимум по каждому профилю:

- **целевой дизайн**, а не языковая норма: стремиться минимум к 50 независимым документам и 10 000 словам на основной профиль до freeze порогов, если корпус и лицензия позволяют;
- внутри каждого профиля иметь отдельные published/neutral controls и intentionally-problematic controls;
- для редких конструкций добирать targeted negative controls, но не смешивать их с оценкой естественной частоты;
- отдельные тексты с цитатами, кодом, URL, версиями, диапазонами, прямой речью.

Числа здесь — **план размера тестовой выборки**, а не языковые пороги. Для статистически надёжного релиза размер следует пересмотреть по реальной вариативности результатов.

## 8. Калибровка профилей

1. Получить тексты законным способом; не складывать закрытые или несовместимые по лицензии корпуса в релиз.
2. Создать манифест с условиями происхождения и лицензии.
3. Извлечь признаки:

```bash
python3 scripts/extract_corpus_features.py --manifest data/corpus_manifest.csv --output data/features.csv
```

4. Строить распределения **по выбранным группам**, например:

```bash
python3 scripts/calibrate_profiles.py data/features.csv \
  --group-by channel,target_register \
  --min-docs 20 \
  --min-words-per-doc 100 \
  --output data/distributions.json
```

5. Квантили использовать только как кандидаты для предупреждений.
6. Проверить кандидаты на `false_positive_cases.json` и реальных evals.
7. Сравнить со старым профилем и вариантом без предупреждения.
8. Активировать новый порог только если он приносит измеримую пользу.

Для очень коротких каналов (чат, соцсеть) использовать отдельную выборку и другой `--min-words-per-doc`; не смешивать их с длинной прозой.

## 9. Evals для каждого релиза

### Trigger

- около 20 реалистичных positive/near-miss запросов;
- несколько запусков;
- фиксированный train/validation split;
- не оптимизировать description по validation.

### Output

- новая версия vs предыдущая версия на одинаковых задачах;
- несколько независимых запусков;
- объективные assertions;
- отдельные критерии фактов, модальности и цитат;
- слепое попарное сравнение стиля;
- токены/время как стоимость улучшения;
- результаты по dimensions, а не только среднее.

`evals/METRICS.md` описывает рекомендуемые метрики.

## 10. Что не включать в релиз как «обучающие данные»

- большие копии сторонних корпусов без явной совместимой лицензии;
- пользовательские конфиденциальные тексты;
- точные демографические профили для имитации речи;
- синтетический «плохой русский» как единственный источник ошибок;
- автоматически сгенерированные «эталоны» без человеческой проверки.

В репозитории достаточно хранить схемы, маленькие собственные eval-примеры, производные агрегированные признаки и ссылки на источники данных.


## 11. Результат pilot 1.3

Первый одинаковый прогон 1.1/1.2 не показал различий в детерминированном линтере. После контекстного разбора отключены пользовательские сигналы плотности тире/двоеточий, а лексический `hype` переведён с одиночных совпадений на серию/плотность и отключён в technical/official. Сырые признаки сохранены для будущего анализа.

`benchmark/PILOT_RESULTS.json` фиксирует измерения и ограничения. Pilot **не** заменяет полный corpus benchmark и не доказывает улучшение генеративной части Skill.


## 12. Ablation 1.4: preregistered freeze

Пять сигналов теперь нельзя менять «по ощущению». Для каждого релиза runner сравнивает: `old threshold`, консервативный `candidate`, `off`.

Порядок решения:

1. natural held-out оценивает alert burden;
2. targeted controls оценивают только чувствительность;
3. candidate не может становиться более чувствительным только из-за малого корпуса;
4. chunks одного исходного документа не считаются независимыми документами;
5. candidate не активируется до целевого freeze gate: стремиться минимум к 50 независимым документам и 10 000 словам на основной профиль, где это реально и законно;
6. после corpus gate всё равно нужен отдельный редакторский/generative A/B.

### Результат текущего прохода

Доступный natural probe содержит только 5 in-scope связных документов / 2161 слово по `technical` и `product`. Ещё 4 каталога локализации использованы только как secondary lexical controls; художественный фрагмент — только как domain guard. На такой выборке ни один из пяти порогов не заморожен и не изменён.

`one-sentence-paragraphs` сейчас наиболее data-starved: для него нужны независимые статьи/посты с ≥8 абзацами. Для `sentence-uniformity` особенно нужны `prose`, `oral`, `product`; `technical`/`official` в текущем профиле отключают rhythm checks.


## 13. External held-out 1.5: materialization before threshold work

В этом проходе запрещено менять `check_prose_ru.py`, `ablate_signals.py` и активные пороги. Сначала должен появиться достаточный внешний held-out.

### Приоритеты

1. `prose/blog/media` — длинные LJ/blog тексты и независимые media documents. Для абзацного сигнала приоритет у документов с ≥8 естественными абзацами.
2. `oral` — естественно ограниченные разговоры/монологи/сессии; utterance-level записи не объединяются произвольно.
3. `product/business` — реальные кейсы с различными авторами/компаниями/типами проектов.
4. `official/legal` — полные правовые документы, а не отдельные предложения.
5. `social` — отдельная channel stratum; не смешивать с blog/media при анализе распределений, даже если все они routed в `profile=prose`.

### Provenance и release policy

Каждый materialized document обязан иметь source URL, archive URL при наличии, source id, channel, profile, SHA-256 и независимый document id. Для LJSearch предпочтительна ссылка `savedcopy?post=...`; текущая LiveJournal-страница может быть вторичным provenance.

Copyrighted web text хранится только во внешней research workspace. В release по умолчанию входят registry/manifest, ссылки, hashes/features и aggregates. Open/CC/public-domain источники всё равно предпочтительно держать внешними, чтобы пакет оставался компактным и чтобы условия attribution не терялись.

### Independence

- exact copy даёт один вклад;
- очевидный repost/near-copy cluster даёт один вклад в freeze;
- chunks одного исходного документа не считаются независимыми;
- повторяющийся автор/издатель не автоматически делает документы зависимыми, но концентрация отдельно показывается в отчёте;
- near-duplicate similarity threshold — техническая benchmark-эвристика, не языковой порог.

### Freeze workflow

```bash
python3 scripts/materialize_external_heldout.py --sources ... --output-dir data/heldout-work
python3 scripts/validate_external_heldout.py \
  --manifest data/heldout-work/manifest.csv \
  --output data/heldout-work/VALIDATION.json \
  --validated-manifest data/heldout-work/manifest.validated.csv
python3 scripts/ablate_signals_v3.py \
  --manifest data/heldout-work/manifest.validated.csv \
  --output data/heldout-work/ABLATION_DECISION_V3.json \
  --annotation-template data/heldout-work/alert-adjudication.csv
```

Третья команда имеет смысл только после profile-size/dedup stage; сам v3 runner дополнительно блокирует решения по diversity, signal eligibility и split minima. Для полного сетевого сценария предпочтителен `scripts/run_external_heldout_gate.py`, который физически не вызывает decision stage до profile gate. Каталог URL или search snippets не считаются materialized corpus.

### 13.4. Deduplicated ablation input

Raw `manifest.csv` — журнал получения данных, а не статистическая выборка. После exact/explicit/near-copy clustering `validate_external_heldout.py` создаёт `manifest.validated.csv` с одним представителем на cluster. Любой decision runner должен получать только этот manifest, иначе репосты могут искусственно изменить квантили и evidence counts. Исторический `ablate_signals.py` сохранён только для воспроизведения 1.4; новые решения используют v3.

Для архивного Zenodo `LiveJournal Dataset` действует отдельный preflight: record подтверждает архив и лицензию, но не структуру записей. До подтверждения наличия post bodies и document boundaries его статус остаётся `catalogued_format_unverified`.

## 14. Decision protocol v3 (1.7)

`50 документов / 10 000 слов` является только **profile size stage**. Для решения по конкретному сигналу дополнительно требуются:

- не менее 50 signal-eligible документов / 10 000 eligible слов для применимого profile;
- connected-component split: любой общий известный `author_or_group`, `split_group`, `source_document_id` или `independence_group` связывает документы; source-local identifiers scope-ятся `source_id`; минимум 30 документов / 6000 слов calibration и 20 / 4000 validation;
- source/channel diversity gate из `benchmark/ablation/spec-v3.json`; неизвестный provenance не считается diversity и не разбавляет концентрацию; source concentration проверяется и по document share, и по word share;
- для `prose`/`oral` достаточное author metadata coverage и author concentration являются частью evidence gate;
- candidate вычисляется только по calibration; validation до этого не используется;
- targeted synthetic controls остаются вне квантилей;
- candidate/off не активируются по одному снижению числа alerts: нужна ручная/слепая разметка natural alerts как `actionable / non_actionable / uncertain`;
- конфликтующие повторные labels для одного `(document_id, signal)` запрещены.

Исторический `scripts/ablate_signals.py` и `benchmark/ablation/spec.json` сохраняются byte-identical для воспроизведения 1.4. Решения после 1.7 должны опираться на `scripts/ablate_signals_v3.py` и `spec-v3.json`; ни один runner не редактирует active profile автоматически.
