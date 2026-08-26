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
