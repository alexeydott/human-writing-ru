# Pass 11 — external held-out before threshold changes

## Цель

Не менять линтер. Не менять пять активных порогов. Сначала получить достаточный внешний held-out, проверить границы документов и дубли, затем повторить уже существующий `old → candidate → off` ablation.

Baseline code hashes зафиксированы в `benchmark/external-heldout/UNCHANGED_CODE_SHA256.json`.

## Приоритет 1: prose / media / blog

### Blog

Основной источник — LJSearch saved copies. Это важно для `one-sentence-paragraphs`: search snippets, sentence corpora и tokenized treebanks не сохраняют реальную авторскую абзацную композицию достаточно надёжно.

Materializer:

1. выполняет несколько тематических запросов;
2. извлекает `savedcopy?post=...`;
3. скачивает сохранённую страницу;
4. выделяет связный текст с абзацами;
5. требует минимум 250 слов и 8 абзацев для источника LJ;
6. записывает post id, original/source URL при обнаружении, saved-copy URL, SHA-256;
7. не включает raw posts в release ZIP.

Второй кандидат — Zenodo LiveJournal Dataset. Record подтверждает ZIP, размер и лицензию, но не описывает его внутреннюю схему; поэтому он остаётся `catalogued_format_unverified` и не используется до проверки, что архив содержит реальные post bodies и document boundaries.

### Media

`factRuEval-2016` используется как document-level источник. Исходные `book_*.txt` не дробятся. Это обеспечивает независимые новостные документы для `sentence-uniformity` и `long-sentence`, но media не должен заменять blog-stratum для абзацной структуры.

## Приоритет 2: oral

Главная ошибка, которую нужно предотвратить, — считать отдельные короткие utterances независимыми длинными документами или склеивать их произвольно.

В freeze допускаются естественные единицы:

- полный диалог;
- монолог/ответ, если он сам достаточно длинный;
- разговорная сессия с сохранённой границей;
- интервью/беседа как документ.

Отдельно фиксируется speaker/session concentration.

## Приоритет 3: product / business

RBC Companies и Ruward подходят как реальные опубликованные кейсы. Для freeze нужны разные компании/агентства/типы продукта. Validator показывает source concentration; future manual review должен также проверять publisher/author concentration.

Raw copyrighted pages — только local research workspace.

## Приоритет 4: official / legal

RusLawOD v3 позволяет набирать полные длинные правовые документы. Sampling должен разнообразить годы и issuing bodies; шаблонные amendment acts и near-copies должны схлопываться до одного независимого вклада.

## Приоритет 5: social

Social остаётся `channel=social` при `profile=prose`. До завершения текущего ablation новый linter profile не добавляется. Distribution analysis по social проводится отдельно от blog/media, даже если финальный runner группирует по существующему profile.

## Независимость

Validator применяет три уровня и после кластеризации пишет отдельный `manifest.validated.csv`; именно его, а не raw acquisition manifest, получает неизменённый `ablate_signals.py`:

1. exact SHA duplicate → один cluster;
2. одинаковый explicit `independence_group` → один cluster;
3. very-high near-copy Jaccard → один cluster.

Near-copy cutoff — benchmark-эвристика для обнаружения репостов. Это не стилистический порог и не правило русского языка.

Повтор одного автора не автоматически схлопывает документы, но author/source concentration выводится отдельно.

## Freeze

Неизменный дизайн:

- 50 независимых документов на основной profile;
- 10 000 анализируемых слов;
- отдельная sample-eligibility статистика для каждого из пяти сигналов;
- после gate — тот же `scripts/ablate_signals.py`;
- после corpus decision — отдельный редакторский/generative A/B.

## Фактический результат сборочной среды

Bulk materialization не состоялся из-за отсутствия outbound DNS/network у container runtime. Проверочный вызов GitHub API из materializer завершился ошибкой разрешения имени. Web research при этом позволил проверить registry, licensing pages и seed saved-copy URLs.

Поэтому release 1.5 имеет статус acquisition-ready, но **не freeze-complete**. Ноль внешних документов в build environment лучше ложных 50 документов, собранных из snippets или нарезки нескольких текстов.
