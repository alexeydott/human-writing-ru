# План re-run held-out v3 до повышения policy_version

Цель: получить полные evidence gates для всех пяти профилей, закрыть разметку
natural alerts и подготовить основание для человека, чтобы принять решение
`keep old / candidate / off` и — только при полном проходе — повысить
`metadata.policy_version` (сейчас 1.4.0) с цитатой прошедшего прогона.

Дисциплина: конвенции §4 (кандидат только на calibration, проверка на
независимой validation, запрет авто-смены порога), `benchmark/ablation/spec-v3.json`,
ROADMAP §1. Отрицательный результат (gate не пройден, пороги не меняем) —
нормальный исход и фиксируется как таковой.

## Исходное состояние (прогон `data/heldout-work-beta4-final`)

687 валидных документов, точных дублей нет, 3 near-duplicate пары учтены.

| Профиль | Size gate (50/10k) | Diversity gate | Провалы |
|---|---|---|---|
| product | ✅ | ✅ | — |
| technical | ✅ | ✅ | — |
| official | ✅ | ❌ | `minimum_sources` (1<2), доля одного источника 1.0>0.8 (доки и слова) |
| oral | ✅ | ❌ | `author_metadata_coverage`: 100/170 = 58.8% < 60% |
| prose | ✅ | ❌ | `minimum_sources` (2<3), `minimum_channels` (2<3), авторы 0% < 50% |

Сигнальные пары product и technical уже полностью готовы к решению; по
prose/oral/official все применимые сигналы заблокированы gates профилей.
Разметка natural alerts: 43 алерта product, `label` пуст у всех 43.

## Этап 0. Разметка алертов product (не зависит от данных, старт сразу)

Вход: `data/heldout-work-beta4-final/alert-adjudication.csv` (43 строки) и
сгенерированный разбор `data/heldout-work-beta4-final/alert-adjudication-review.md`
(фрагменты срабатываний по каждому алерту: предложения ≥ порога, однофразовые
абзацы, доли и счётчики).

Два решения ждут разметки:

1. **`one-sentence-paragraphs` / product — кандидат** (порог 0.9133 против old 0.70).
   Порог активации: ≥10 размеченных removed-алертов, среди решающих
   (`actionable`+`non_actionable`) ≥80% `non_actionable`.
   Доступно 17 removed-алертов (rbc 6, rurebus 2, ruward 9 из 11; у 2 алертов
   candidate тоже срабатывает — они не removed).
2. **`long-sentence` / product — только `off`** (кандидат 97 слов
   `keep_old_candidate_loses_positive_control` — включить нельзя).
   Порог off: ≥20 размеченных алертов, actionable-precision ≤0.25.
   Доступно 24 алерта (22 removed + 2 общих).

### Разбор для разметки (паттерны из review-отчёта)

**long-sentence (24):** 22 — rurebus (муниципальные программы, положения,
отчёты — `business_document`), 2 — ruward (55 слов). Максимальные предложения
47–133 слова; у 15 из 24 документов максимум ≤60 слов. Типовое содержание —
административные перечисления исполнителей/мероприятий; длинные предложения в
этом жанре нормативны. Ожидаемый уклон: `non_actionable`; `actionable` —
там, где предложение действительно теряет управляемость (заклиниться надо по
тексту, не по источнику).

**one-sentence-paragraphs (19):** ratio 0.71–0.95 (p50 ≈ 0.80). Это бизнес-кейсы
RBC/Ruward с короткими ударными абзацами — жанровая норма product-текстов,
но 5% из 1099 однофразовых абзацев (50) — навигационный мусор веба
(хлебные крошки «Главная…», даты, «Источник изображения:», пустые заголовки
«Задача и причина Задача:», в основном rbc: 42 абзаца в 6 документах).
Мусор — основание `non_actionable`, но и не редакционная проблема автора:
флаг данных (см. риск R2), а не автора.

Правила разметки: метка — про **пользы предупреждения редактору** для данного
текста, а не про «правильность» текста. `uncertain` допустим, не влияет на
precision, но не в счёт минимума. Слепость к arm не обязательна для этих пар
(cand/off решаются независимо), но не смотреть, какой arm сработал, легче
разметить честно.

### Возврат разметки

Заполнить `label` в `alert-adjudication.csv` (значения: `actionable`,
`non_actionable`, `uncertain`; конфликты дубликатов по `document_id+signal`
скрипт отклонит). CSV передаётся в re-run флагом `--annotations`.

**Важно:** split считается per-profile (seed `human-writing-ru-ablation-v3`,
digest `{seed}|{profile}|{component}`). Пока корпус product не меняется,
validation-набор product в re-run будет тем же — разметка текущего CSV
остаётся действительной. Если в product добавить/убрать документы — разметку
переделывать.

## Этап 1. Заполнение данных

Все правки — provenance-метаданные и новые источники, не policy. Замороженные
входы (`check_prose_ru.py`, `ablate_signals.py`, `editorial-baseline.json`)
не трогаются; SHA сверяет `FROZEN_INPUT_SHA256.json` на каждом прогоне.

### 1.1 oral — авторы (мелкая правка, без сети)

Пробел: 100/170 (duma 100/100; rub 0/40; putin 0/30).

Правка: в `SOURCE_REGISTRY.json` у `putin_corpus_github_v1` задать
`"author_or_group": "Владимир Путин"`. Корпус односпикерный по определению
(levshina/Putin_Corpus); адаптер `materialize_github_tree_text` уже читает
registry-level `author_or_group` — менять код не нужно.

Эффект: 130/170 = 76.5% ≥ 60% ✅. Концентрация: 30/170 = 17.6% ≤ 50% ✅
(30 документов одного спикера образуют один split-компонент — так и задумано).

Резерв, если после re-run пробел сохранится (переселекция документов):
`iter_zip_records` для rub уже читает `author/speaker/user` из JSON-записей —
проверить, есть ли speaker в zip RUCORPUS, и при необходимости добить там.

### 1.2 prose — третий источник/канал + авторы

Пробелы: 2 источника (нужно 3), 2 канала (нужно 3), авторы 0% (нужно ≥50%).

**Авторы taiga (без сети).** Исходные файлы в
`data/_downloads/taiga-extracted/home/tsha/social/texts/` (`fbtexts.txt`,
`vktexts.txt`): заголовок записи `DataBaseItem: <user>_<hash>`, user-id —
анонимизированный, но стабильный идентификатор пользователя (Taiga
дистрибутирует user-id именно для user-level группировки). Пересобрать
sidecar `data/taiga_social/manifest.csv`: `author_or_group =
"taiga-fb-user-<user>"` / `"taiga-vk-user-<user>"` по тому же правилу, что и
doc-id (id документа уже кодирует user). Эффект: 80/80 taiga-документов с
автором; максимальная доля одного пользователя ≤ ~0.05 ≤ 0.5 ✅.
Документировать в `data/taiga_social/provenance.json` (сейчас там
«no author inferred» — заменить описание).

**Третий канал (blog), вариант A — `ljsearch_saved_copies`.** Реестр:
priority 1, 60 документов / 20k слов, автор — journal-имя из URL (
`LJ_AUTHOR_RE`). Сеть ljsear.ch; текущие seeds — 5 сохранённых копий, новые
запросы даёт `max-index-pages`-обход адаптера. Риск R1 (сеть/урожай).

**Вариант B (ослабленный) — `ud_russian_taiga`** (blog, GitHub,
`manual_or_local_tree`): формально даёт третий source_id и канал, но
исходный датасет тот же Taiga, что и `taiga_social` — независимость
происхождения ниже. Допустимо только явным решением человека с записью в
прогон (в отчёт и в CHANGELOG), не по умолчанию.

Ожидаемо после этапа: prose = factrueval 80 (media) + taiga 80 (social) +
LJ ~60 (blog): 3 источника, 3 канала, покрытие авторов ≈ (80+60)/220 ≈ 64% ≥ 50% ✅,
доля крупнейшего источника 36% ≤ 60% ✅.

### 1.3 official — второй источник

Правка: материализовать `ruslawod_v3` (huggingface_stream, цель 80 документов /
40k слов): `python -m pip install datasets` + сеть на HuggingFace.
Эффект: pravo 50 + ruslawod ≥20 → доля pravo ≤ 50/70 ≈ 71% ≤ 80% ✅ (цель
забронировать с запасом ≥20 документов; 13 даёт 79% — впритык).
Риск R1 (HF/`datasets`).

Фолбэк при недоступности: official остаётся неготовым — в прогоне фиксируется
отрицательный результат, решения по official-сигналам не принимаются, это не
блокирует product-решения (см. Этап 3).

### Фактические результаты этапа 1 (2026-08-27)

**1.1 oral — исполнено с отклонением от плана. Gate закрыт.**

- Подход плана (registry-level `author_or_group: "Владимир Путин"` у
  `putin_corpus_github_v1`) **отклонён**: metadata реестра по этому корпусу
  — «mixed-speaker XML events; do not collapse to a fictitious single
  author/group»; корпус многоспикерный, единый автор был бы фабрикацией
  provenance.
- Резерв плана (speaker в rub) **недоступен**: TSV
  `russia_all_texts.tsv.zip` содержит только колонки `date/href/text`,
  speaker-метаданных нет; тексты — многоспикерные протоколы (кабинетные
  совещания, инлайновые теги «В.Путин»/«А.Миллер» внутри одного документа).
  Флаг `author_provenance_capable: false` подтверждён.
- **Обнаружен просчёт плана**: gate v3 проверяет author coverage по
  документам **и** по словам (`author_doc_coverage >= min AND
  author_word_coverage >= min`), план считал только долю документов.
- Фактически: расширение duma с 100 до **185** документов (3 партии: +25 —
  по 1 в год, +50 — два round-robin прохода по годам, +10 — третий проход;
  везде: `type == '-'`, ≥400 слов, новый `deputy_id`, неиспользованное
  заседание, first match по `date/meeting/start_line`; все авторы
  различны). Детерминированно, офлайн, из того же архива (SHA в
  provenance.json).
- Итог: oral = 255 документов (duma 185 + rub 40 + putin 30), 208 303 слова
  (duma 129 877). Покрытие авторов: **72.5% по документам, 62.4% по словам**
  (порог 60%) ✅; доля duma 72.5% ≤ 75% ✅ (и по словам: 62.4%).
- Registry: `duma_speeches_1994_2021.target_documents` 100 → 185
  (`target_words` 50000 без изменений); строка SOURCE_MANIFEST.csv
  синхронизирована.

**1.2 prose — частично исполнено; gate НЕ закрыт, решение за человеком.**

- Авторы taiga: **исполнено** — `data/taiga_social/manifest.csv` rebuilt,
  80/80 документов с `author_or_group = taiga-fb-user-<user>` /
  `taiga-vk-user-<user>` (12 пользователей, максимум 13/80 = 16.3% taiga,
  8.1% prose), provenance.json обновлён.
- LJSearch (вариант A): **негативный результат, риск R1 материализовался**.
  Проба: `discovered_savedcopies: 200, accepted: 0, errors: []`. Диагностика
  по seed-URL: все saved-copy-страницы — идентичные stub'ы на 2506 символов
  («Это сохраненная версия поста. Оригинал: …»); ljsear.ch не отдаёт тела
  постов. Клиентского фикса нет; источник фактически мёртв для этого
  назначения.
- **Обнаружен второй просчёт плана**: prose word coverage авторов =
  26 797 / 61 425 = **43.6% < 50%** (по документам 80/160 = 50.0% — ровно на
  пороге). План это не учитывал.
- Статус: `minimum_sources` (2<3), `minimum_channels` (2<3),
  `author_metadata_coverage` (слова) не пройдены.
- **Решение человека (2026-08-27): третий канал — `zenodo_livejournal_7139731`**
  (blog, 100/30k, CC BY 4.0) вместо вариант B. **Верификация формата
  (обязательный шаг по selection_policy источника) — провалена, источник
  непригоден:** архив `livejournal.zip` (MD5 совпадает с registry) содержит
  единственный бинарный член `livejournal.bcsr` (381 MB извлечённых):
  0 русских слов в UTF-8 и UTF-16, никаких маркеров постов/метаданных.
- **Формат bcsr идентифицирован (2026-08-27)** — бинарный граф
  (BCSR-подобный CSR), а не текстовый корпус: 12-байтовый заголовок
  (`u32 num_nodes=4 846 609`, `u32 num_edges=85 702 474`, `u32 0`), затем
  `num_nodes+1` u64 row-pointers и `num_edges` u32 vertex IDs
  (little-endian). Полная проверка пройдена: точное совпадение размера
  `12 + 8(N+1) + 4M = 381 582 788`, `offsets[0]=0`,
  `offsets[-1]=num_edges`, монотонность всех 4 846 610 offsets, все
  85 702 474 adjacency-ID в диапазоне `[0, N-1]`. Граф: 4 846 609 вершин,
  85 702 474 рёбер, средний градус 17.7 (min 1, max 20 333) — согласуется
  с графом подписок LiveJournal (вершины = юзеры, рёбра = follows); тел
  постов, имён и документных границ в файле нет. Reader и валидация:
  `data/_downloads/zenodo_livejournal_7139731/read_livejournal_bcsr.py`
  (локальные скрипты, в пакет не входят). Статус источника:
  `catalogued_format_unverified` → `rejected_format_binary_graph_no_text`;
  в зачёт diversity источник не входит.
- **LJSearch (вариант A) — рабочий маршрут найден, тексты получены (2026-08-27).**
  savedcopy детерминированно блокируется по RU-IP (stub 2506 B; 52/52 прямых
  HTTP-попыток, Firefox оператора и чистый Edge — один и тот же stub), НО
  оригинальные URL, которые отдаёт страница поиска (livejournal.com),
  доступны напрямую и несут полное тело поста
  (`div.aentry-post__text`, современный schemius-тема). Собрано
  интерактивно через DevTools-протокол msedge (CDP): 12 запросов реестра +
  страница 2 «путешествие», 124 тела, **60 документов / 56 авторов /
  56 386 слов** проходят eligibility (≥250 слов, ≥8 абзацев; удалены 4
  зеркальные near-duplicate копии по 4-грам Jaccard >0.5; максимум 2
  документа на автора). По `release_policy` в репозитории закреплён
  manifest + per-document text-хэши:
  `benchmark/external-heldout/ljsearch_browser_collection/` (manifest.csv,
  COLLECTION_REPORT.json); полные тексты — локальная research-копия
  `data/_lj_probe/lj_corpus_candidates.jsonl` (gitignored, SHA-256 в
  отчёте). Registry: `ljsearch_saved_copies.status =
  collected_manifest_only`. Формальная материализация для re-run
  (адаптер / локальное дерево `data/ljsearch_saved_copies/`) — решение
  перед Этапом 2.
- **`ud_russian_taiga` (вариант B) проверен на пригодность — не закрывает
  gate:** (a) документные границы ненадёжны — `# newdoc`/`# newdoc_id` есть в
  dev-файле (9 документов), в train-файлах их нет (только
  `# sent_id/#genre/#text/#newpar`), а selection_policy источника запрещает
  считать независимыми документами одни sentences; (b) per-document
  авторства нет — `# speaker` встречается лишь в одном многоспикерном
  документе с анонимизированными метками (`screened-N`); (в) при добавлении
  документов без авторов авторское покрытие prose **ухудшается**: по
  документам 80/(160+N) < 50%, по словам 43.6% → ниже порога. Вариант B
  закрыл бы только `minimum_sources`/`minimum_channels`, но
  `author_metadata_coverage` остался бы проваленным.
- **Итог 1.2: prose формально остаётся неготовым, но данные собраны.**
  Ни один каталогизированный источник не закрывал все три sub-gates
  одновременно; после отклонения zenodo (бинарный граф) и варианта B
  (UD Taiga — без авторов) найден и пройден рабочий LJ-маршрут
  (original-URL, см. выше): 60 blog-документов с author-provenance
  закреплены manifest-only. Осталось решение о формальной
  материализации (локальное дерево `data/ljsearch_saved_copies/`), после
  чего по прогнозу prose проходит все sub-gates: 3 источника, 3 канала,
  авторы ≈ (80+60)/220 = 63.6% по документам и ≈70% по словам, доля
  крупнейшего источника 36%. Решения по готовым профилям (product,
  technical, oral, official) не блокируются.

**1.3 official — исполнен с отклонением от плана (adapter). Gate закрыт.**

- `huggingface_stream` **нежизнеспособен**: датасет = 11 шаров, ~6.2 GB;
  стриминг через `datasets` скачивает шар целиком; соединение с HF-CDN
  рвётся (457 MB получено ~46 MB до разрыва, 5 ретраев безрезультатны).
  Каждый re-run требовал бы повторного многогигабайтного скачивания.
- Фактически: скачан один шар `ruslawod_11.parquet` (95.8 MB) resumable-
  загрузчиком `huggingface_hub`; 4864 строки, **1155 eligible** (≥300 слов,
  ≥3 абзацев, russian ≥ 0.65). Материализовано **80 документов** в
  `data/ruslawod_v3/` (детерминированная стратификация: ячейки
  «органы, год», в ячейке — длинные документы, капы 8 на орган / 6 на год,
  шаблонные поправки «О внесении изменений/Об изменении» исключены).
  534 652 слова, ≥8 органов, 1992–2025; полный audit-trail в
  `data/ruslawod_v3/provenance.json` (включая SHA-256 шара).
- Registry: `ruslawod_v3.adapter` `huggingface_stream` →
  `manual_or_local_tree` (+ `local_import_note`); SOURCE_MANIFEST.csv
  синхронизирован; `quality/RELEASE_INTEGRITY.json` перегенерирован
  (`write_release_integrity`), `validate_skill.py` — 0 ошибок.
- Итог: official = pravo 50 + ruslawod 80 = 130 документов / 103 294 слова.
  Источников 2 ✅; доля pravo: **38.5% по документам, 48.2% по словам**
  (порог 80%) ✅.

**Сводный прогноз gates после этапа 1** (product/technical — без изменений
с прогона beta4-final; product-разметка остаётся действительной, корпус
product не тронут):

| Профиль | Size gate | Diversity gate | Статус |
|---|---|---|---|
| product | ✅ | ✅ | готов |
| technical | ✅ | ✅ | готов |
| oral | ✅ | ✅ 72.5% / 62.4% | готов |
| official | ✅ | ✅ 2 источника, 38.5% / 48.2% | готов |
| prose | ✅ | ❌ 2<3 источника, 2<3 канала, 43.6%<50% слов | **неготов** (данные собраны: 60 LJ blog-документов, manifest-only; ждёт материализации) |

## Этап 2. Re-run

Новый рабочий каталог (не переиспользовать `heldout-work-beta4-final`):

```bash
python scripts/run_local_heldout_workflow.py ^
  --data-dir data ^
  --output-dir data/heldout-work-policy-1.5 ^
  --annotations data/heldout-work-beta4-final/alert-adjudication.csv
```

(на Linux/macOS: одна строка; `--annotations` — заполненный CSV Этапа 0).

Скрипт сам прогоняет pre-checks, материализует все `DEFAULT_SOURCES`
(локальные деревья `data/<source_id>/` подхватываются автоматически),
валидирует, строит split и пишет:

- `manifest.validated.csv` + SHA-256,
- `VALIDATION_REPORT.json` (gates по профилям),
- `ABLATION_DECISION_V3.json` (решения по парам),
- новый `alert-adjudication.csv` — сверить: алерты product должны совпасть с
  размеченным набором; новые алерты (если появились) разметить до финала.

Коды возврата: 0 — evidence+разметка завершены (решение всё равно за
человеком); 6 — v3 evidence неполна; 7 — ждёт разметки.

Проверка перед Этапом 3 (по `VALIDATION_REPORT.json` + `ABLATION_DECISION_V3.json`):
`gate_met: true` у всех пяти профилей и у всех применимых сигналов,
`natural_alert_adjudication_complete_where_required: true`.

## Этап 3. Решение и повышение policy

1. Человек по финальному `ABLATION_DECISION_V3.json` принимает решение по
   каждой паре «профиль × сигнал» с evidence. Только пары, прошедшие все
   gates; пары с `blocked_evidence_gate_not_met` остаются как есть.
2. Изменение: `metadata.policy_version` в `SKILL.md` (например 1.4.0 → 1.5.0) +
   конкретные пороги в `profiles/editorial-baseline.json` (только принятые
   пары) + запись в `CHANGELOG.md`.
3. В коммит/CHANGELOG цитировать прогон: рабочий каталог
   (`data/heldout-work-policy-1.5`), SHA-256 `manifest.validated.csv`, путь
   `ABLATION_DECISION_V3.json`, метрики разметки (precision по removed-алертам).
4. Замороженные входы не меняются; `frozen_inputs_match` в
   `quality/RELEASE_INTEGRITY.json` обязан остаться `true`.
5. Версия пакета (`VERSION`) может повышаться отдельно или вместе — номера
   независимы (конвенция §1); после изменения `SKILL.md`/`editorial-baseline.json`
   пересобрать пакет (`python scripts/build_release.py`).

## Риски

- **R1. Сеть:** ljsear.ch и HuggingFace могут быть недоступны/урожай
  низкий. Тогда соответствующие profiles остаются неготовыми — фиксируем
  отрицательный результат; решения по готовым парам (product) не блокируются.
  **Статус (этап 1): LJSearch — savedcopy мёртв (RU-IP-блок, 0 из 200),
  но original-URL-маршрут жив: собрано 60 документов, manifest-only
  (см. 1.2); HuggingFace — решён локальным шаром `ruslawod_11.parquet`
  (см. 1.3).**
- **R2. Веб-мусор в product-кейсах:** 5% однофразовых абзацев — навигация/
  шаблон (rbc: 42 абзаца в 6 документах). Если разметка массово даёт
  `non_actionable` из-за мусора, кандидат «пройдёт», но сигнал на product
  будет мерить сайт, а не ритм автора. Тогда: либо `off` по
  one-sentence-paragraphs/product, либо сначала почистить экстракцию RBC/Ruward
  (отсечь крошки/даты/подписи к картинкам) и пересчитать. Решение — за
  человеком, по тексту review-отчёта.
- **R3. Переселекция при re-run:** если в product/прошем профиле изменится
  состав документов — split-наборы пересчитаются, разметка product
  переделывается. Корпус product в этом плане не менять.
- **R4. `datasets` (ruslawod)** — опциональная зависимость; установка только
  в локальном окружении, в пакет не входит.

## Вне плана

- Никакого автопереключения active profile (протокол и код это запрещают).
- Новых сигналов/профилей линтера (ROADMAP §4 — только после собственного
  evidence).
- Генеративного A/B — отдельная рабочая нить (ROADMAP §3), для stable-релиза
  обязательна, для бета-бампа policy по линтерным порогам — параллельна.
