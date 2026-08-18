# External held-out: ссылки на источники и сохранённые копии

Этот файл — каталог источников. Наличие ссылки **не означает**, что документ уже материализован или допущен к freeze. Актуальный локальный статус фиксируется в `MATERIALIZATION_STATUS.json`, а после загрузки — в `MATERIALIZATION_REPORT.json` и отчёте `validate_external_heldout.py`.

## 1. LiveJournal / blog — основной источник для абзацной структуры

### LJSearch

- Главная: https://ljsear.ch/
- Поиск: https://ljsear.ch/search?q=
- FAQ и описание архива: https://ljsear.ch/faq

LJSearch используется именно как архив/поисковый индекс русскоязычного ЖЖ 2000–2017. Для benchmark предпочтительна **сохранённая копия конкретного поста**, а не текущая страница журнала.

### Seed-ссылки на сохранённые копии

1. https://ljsear.ch/savedcopy?post=402698938
   - упоминается как сохранённый русскоязычный материал о Никосе Гаврииле Пендзикисе;
   - discovery mirror: https://2ch.life/fl/arch/2022-10-26/res/495181.html
2. https://ljsear.ch/savedcopy?post=471370346
   - сохранённый материал о Йоргосе Сеферисе;
   - discovery mirror: https://2ch.life/fl/arch/2022-10-26/res/495181.html
3. https://ljsear.ch/savedcopy?post=409740080
   - исходная запись: http://kisochka-yu.livejournal.com/147568.html
   - альтернативная сохранённая копия: http://www.webcitation.org/6C2cGxvAF
   - provenance/discovery: https://www.db.chgk.info/tour/ovsch18.3_u
4. https://ljsear.ch/savedcopy?post=689758469
   - provenance/discovery: https://cyclowiki.org/wiki/Пётр_Валентинович_Турчин
5. https://ljsear.ch/savedcopy?post=420678034
   - provenance/discovery: https://www.holywarsoo.net/viewtopic.php?id=15&p=1391

Эти пять ссылок проверены как найденные адреса/provenance, но их полный текст и длина **не считаются проверенными**, пока materializer реально не получит страницу. Машиночитаемая очередь находится в `LJSEARCH_SAVED_COPY_SEEDS.csv`. Эти ссылки — **seed**, а не готовый corpus. Materializer дополнительно выполняет тематические запросы LJSearch, извлекает `savedcopy?post=...`, оставляет только длинные русские записи, проверяет минимальный объём и абзацы, затем validator удаляет вклад exact/near duplicates из freeze-count.


### Тематические поисковые входы LJSearch

Materializer использует несколько независимых тематических запросов, чтобы не калибровать стиль по одной теме. Примеры прямых входов:

- https://ljsear.ch/search?q=путешествие
- https://ljsear.ch/search?q=архитектура
- https://ljsear.ch/search?q=наука
- https://ljsear.ch/search?q=книги
- https://ljsear.ch/search?q=технологии
- https://ljsear.ch/search?q=история

Поисковая выдача служит только discovery-слоем: в held-out попадает сохранённая копия конкретного поста после проверки объёма, абзацев и дедупликации.

### Архивный LiveJournal dataset

- Zenodo record: https://zenodo.org/records/7139731
- Прямая загрузка: https://zenodo.org/records/7139731/files/livejournal.zip?download=1
- DOI: https://doi.org/10.5281/zenodo.7139731
- MD5 `livejournal.zip`: `e1abe6d11f28b10deb252508c26a66b2`
- Лицензия на странице Zenodo: CC BY 4.0.

Это только потенциальный bulk fallback. Страница Zenodo не описывает внутреннюю схему архива, поэтому до использования нужно сначала проверить, что ZIP действительно содержит тексты постов и восстановимые границы документов. Название набора само по себе недостаточно для допуска в benchmark.

## 2. Media / published prose

### factRuEval-2016

- Repository: https://github.com/dialogue-evaluation/factRuEval-2016
- Source documents: https://github.com/dialogue-evaluation/factRuEval-2016/tree/master/devset
- Test documents: https://github.com/dialogue-evaluation/factRuEval-2016/tree/master/testset
- LICENSE: https://github.com/dialogue-evaluation/factRuEval-2016/blob/master/LICENSE

`book_*.txt` сохраняют исходный текст документов; README отдельно указывает, что абзацы представлены двойным переводом строки. Это делает набор пригодным для sentence-level сигналов и частично для анализа абзацев без искусственного восстановления структуры.

### RIA News Dataset

- https://github.com/RossiyaSegodnya/ria_news_dataset

Использовать только как дополнительную медиа-стратификацию и с учётом upstream-ограничений; full text не включать в release ZIP.

## 3. Social

- Taiga downloads: https://tatianashavrina.github.io/taiga_site/downloads.html
- UD Russian Taiga: https://github.com/UniversalDependencies/UD_Russian-Taiga

Social остаётся отдельным `channel` внутри существующего `profile=prose`: новый профиль линтера в этом проходе не создаётся.

## 4. Oral

- Russian Everyday Dialogues: https://huggingface.co/datasets/kukunechka/russian-everyday-dialogues
- Common Voice Spontaneous Speech 4.0 — Russian: https://mozilladatacollective.com/datasets/cmqi2c2eu0062o5075atr17rs
- Russian National Corpus — spoken search: https://ruscorpora.ru/new/search-spoken.html
- Corpus of speeches 2012–2022, Zenodo: https://zenodo.org/records/7057103
- Связанный GitHub corpus: https://github.com/levshina/Putin_Corpus/tree/v1.0
- Duma Speeches 1994–2021: https://doi.org/10.48320/FB52DAC2-66E3-47A3-86C5-B2A3DADF41BF

Zenodo-набор содержит естественно ограниченные речи/обращения и часть ответов журналистам; Duma Speeches описывает более 385 000 расшифровок речей и устных выступлений. Они добавлены, чтобы `oral` не зависел от коротких ASR utterances. Один естественный монолог/выступление/диалог считается одним документом. Речи одного политика не могут быть единственным oral-источником: validator отдельно показывает концентрацию автора/источника.

Короткие ASR utterances нельзя произвольно склеивать в длинные псевдодокументы. Freeze для `oral` требует естественных границ диалога/монолога/сессии и отдельной проверки концентрации говорящих.


### RUB Corpus — дополнительная oral-страта

- Описание: https://pjbraga.github.io/rub_corpus_and_code/corpus/
- Repository: https://github.com/pjbraga/rub_corpus_and_code
- Russia TSV ZIP: https://raw.githubusercontent.com/pjbraga/rub_corpus_and_code/main/_corpus/russia_all_texts.tsv.zip

Adapter сохраняет одну строку TSV как один естественно ограниченный исходный текст; строки не склеиваются. Лицензию именно на повторное распространение corpus text в ходе этого аудита однозначно установить не удалось, поэтому raw остаётся внешним, а в release по умолчанию идут только manifest/hash/aggregates.

### Putin Corpus — прямой GitHub transport

- Tag/tree: https://github.com/levshina/Putin_Corpus/tree/v1.0
- XML speeches: https://github.com/levshina/Putin_Corpus/tree/v1.0/Speeches_XML
- Repository LICENSE: https://github.com/levshina/Putin_Corpus/blob/v1.0/LICENSE

`github_tree_text` использует один upstream XML-файл как один oral document. Эта страта ограничена меньшим target, потому что не должна единолично определять oral-калибровку.

## 5. Product / business

### RBC Companies cases

- Index: https://companies.rbc.ru/cases/
- Пример реального кейса: https://companies.rbc.ru/news/A0EZbM6BGe/korporativnyij-portal-s-gejmifikatsiej-kejs-vnedreniya-v-food-tech/
- Пример: https://companies.rbc.ru/news/qnOtfrXYWT/kak-transformirovat-servis-v-pribyilnyij-kanal-kejs-ingosstraha/

### Ruward cases

- https://ruward.ru/award/2026/311750/
- https://ruward.ru/award/2026/311753/
- https://ruward.ru/award/2025/571371/
- https://ruward.ru/award/2024/87712/
- https://ruward.ru/award/2023/87259/

### Sostav business blogs

- https://www.sostav.ru/blogs/tags/13043

### RuREBus — business-domain supplement

- https://github.com/dialogue-evaluation/RuREBus

Upstream описывает около 300 размеченных документов и большой корпус отчётов/стратегических планов Минэкономразвития. Это полезная независимая `business_document`-страта, но **не замена реальным product/customer cases**: при анализе paragraph/rhythm её нельзя смешивать с case pages без отдельного channel-среза.

Автоматический adapter использует четыре upstream ZIP без их склейки в один документ:

- https://raw.githubusercontent.com/dialogue-evaluation/RuREBus/master/train_data/train_part_1.zip
- https://raw.githubusercontent.com/dialogue-evaluation/RuREBus/master/train_data/train_part_2.zip
- https://raw.githubusercontent.com/dialogue-evaluation/RuREBus/master/train_data/train_part_3.zip
- https://raw.githubusercontent.com/dialogue-evaluation/RuREBus/master/test_data/test_full.zip

Все части сохраняют один `source_id=rurebus_business_documents`; номер архива используется только в provenance/document id. Поэтому разбиение upstream-архива не создаёт искусственной source diversity.

Это copyrighted/web/business prose: если права на конкретный источник не разрешают перераспространение, в release сохраняются URL, metadata, hashes/features/aggregates, но не полные тексты страниц.

## 6. Technical

### Yandex Cloud documentation — Russian

- Repository: https://github.com/yandex-cloud/docs
- Russian tree: https://github.com/yandex-cloud/docs/tree/master/ru
- LICENSE: https://github.com/yandex-cloud/docs/blob/master/LICENSE

Русские Markdown-документы `ru/**` дают естественные границы технических документов. Репозиторий лицензирован CC BY 4.0. Для held-out исключаются короткие навигационные заглушки, generated index-файлы и документы, состоящие преимущественно из таблиц/API-схем без связной прозы. Один Markdown-файл остаётся одним документом.

## 7. Official / legal

### RusLawOD v3

- Repository: https://github.com/irlcode/RusLawOD/
- Hugging Face dataset: https://huggingface.co/datasets/irlspbru/RusLawOD

RusLawOD v3 охватывает правовые акты РФ 1991–2025. Для bulk sampling предпочтителен streaming dataset: он позволяет брать полные документы без скачивания всего многогигабайтного массива.

### Официальный портал правовой информации

- Open Data: https://publication.pravo.gov.ru/OpenData

Используется прежде всего для provenance/сверки современных документов.

## 8. Что именно считать готовностью

Для **каждого из пяти профилей** (`prose`, `oral`, `product`, `technical`, `official`) freeze остаётся прежним:

- ≥ 50 независимых документов;
- ≥ 10 000 анализируемых слов;
- exact duplicates не увеличивают счётчик;
- очевидные near-copy/repost clusters дают один вклад в freeze;
- один исходный документ нельзя нарезать на несколько «независимых» документов;
- после freeze всё равно выполняется прежний `old → candidate → off` ablation.

Это исследовательский размер benchmark-выборки, а не языковая норма.

## Kubernetes Russian documentation (`technical`)

- Repository: https://github.com/kubernetes/website
- Russian docs root: https://github.com/kubernetes/website/tree/main/content/ru/docs
- License: https://github.com/kubernetes/website/blob/main/LICENSE — CC BY 4.0.
- Benchmark boundary: one eligible standalone Markdown page = one document; navigation `_index.md`, `templates/` and `home/` are excluded.
