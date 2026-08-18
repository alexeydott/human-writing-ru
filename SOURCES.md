# Источники и основания адаптации

Русская версия не является дословным переводом upstream Skill. Источники ниже разделены по статусу: нормативная база, описательная грамматика и корпуса, редакторская традиция, продуктовые/ИИ-практики. Последние две группы не являются нормами русского языка и не должны превращаться в абсолютные запреты.

## Upstream

- Human Writing Skill 1.1.0:
  https://github.com/KKKKhazix/human-writing
- Issue #2 — отдельная ветка для продуктовых кейсов и проектных историй:
  https://github.com/KKKKhazix/human-writing/issues/2

## 1. Нормативная база русского письма

### Полный академический справочник

- «Правила русской орфографии и пунктуации», В. В. Лопатин (ред.). Современная академическая редакция правил на «Грамоте.ру»:
  https://gramota.ru/biblioteka/spravochniki/pravila-russkoy-orfografii-i-punktuatsii

Используется как основной ориентир по нормативной пунктуации. Именно поэтому Skill не вводит самостоятельный запрет на тире или двоеточие.

### Тире

- Тире между подлежащим и сказуемым:
  https://gramota.ru/biblioteka/spravochniki/pravila-russkoy-orfografii-i-punktuatsii/tire-mezhdu-podlezhashchim-i-skazuemym
- Тире между членами предложения:
  https://gramota.ru/biblioteka/spravochniki/pravila-russkoy-orfografii-i-punktuatsii/tire-mezhdu-chlenami-predlozheniya
- Тире в функции соединения:
  https://gramota.ru/biblioteka/spravochniki/pravila-russkoy-orfografii-i-punktuatsii/tire-v-funktsii-soedineniya

### Двоеточие и сложные конструкции

- Взаимодействие знаков препинания в сложных конструкциях:
  https://gramota.ru/biblioteka/spravochniki/pravila-russkoy-orfografii-i-punktuatsii/vzaimodeystvie-znakov-prepinaniya-v-slozhnykh-konstruktsiyakh
- Двоеточие: правила и примеры:
  https://gramota.ru/biblioteka/spravochniki/pravila-russkoj-orfografii-i-punktuacii/dvoetochie
- Знаки препинания в сложноподчинённом предложении:
  https://gramota.ru/biblioteka/spravochniki/pravila-russkoy-orfografii-i-punktuatsii/znaki-prepinaniya-v-slozhnopodchinennom-predlozhenii

### Деепричастие

- «Русская грамматика», раздел о деепричастии и требовании односубъектности:
  https://rusgram.ru/%D0%94%D0%B5%D0%B5%D0%BF%D1%80%D0%B8%D1%87%D0%B0%D1%81%D1%82%D0%B8%D0%B5
- Разъяснение «Грамоты.ру» о нормативных безличных конструкциях с инфинитивом:
  https://gramota.ru/spravka/vopros/328468

Это основание для того, чтобы не использовать упрощённое правило «деепричастие всегда относится только к грамматическому подлежащему» без оговорок.

## 2. Описательная грамматика и корпусная база

### Коммуникативная структура и порядок слов

- Русская корпусная грамматика. «Коммуникативная структура предложения»:
  https://rusgram.ru/new/chapter/clauseintro/information_structure/
- Большая российская энциклопедия. «Русский язык»:
  https://bigenc.ru/c/russkii-iazyk-8b217f

Эти источники используются для принципа: порядок слов в русском относительно свободен, но перестановка меняет тему, рему, акцент или экспрессивность. Поэтому Skill не навязывает универсальный SVO-порядок.

### Письменный русский

- Национальный корпус русского языка, основной корпус:
  https://ruscorpora.ru/corpus/main
- Синтаксический корпус СинТагРус:
  https://ruscorpora.ru/corpus/syntax

Корпуса используются как база для будущей эмпирической калибровки частотных эвристик. Само наличие конструкции в корпусе не делает её автоматически стилистически предпочтительной.

### Устная речь

- Национальный корпус русского языка, устный корпус:
  https://ruscorpora.ru/corpus/spoken
- Мультимедийный русский корпус:
  https://ruscorpora.ru/corpus/murco

Они подтверждают необходимость отделять закономерности подготовленной письменной прозы от бытовой, публичной и другой устной речи.

## 3. Редакторская и стилистическая традиция

Эти работы используются как профессиональная редакторская традиция, а не как свод обязательных современных языковых норм.

- Д. Э. Розенталь. «Справочник по русскому языку. Практическая стилистика». 2-е изд., 2007.
  Каталог РГБ:
  https://search.rsl.ru/ru/record/01003349578
- И. Б. Голуб. «Стилистика русского языка». 1997.
  Каталог РГБ:
  https://search.rsl.ru/ru/record/01001796403
- Г. Я. Солганик. «Стилистика текста». 1997.
  Каталог РГБ:
  https://search.rsl.ru/ru/record/01001770215
- Нора Галь. «Слово живое и мертвое».
  Каталог РГБ:
  https://search.rsl.ru/ru/record/01009907130
- Корней Чуковский. «Живой как жизнь: о русском языке».
  Каталог РГБ:
  https://search.rsl.ru/ru/record/01004322736
- А. Э. Мильчин, Л. К. Чельцова. «Справочник издателя и автора». 2-е изд., 2003.
  Каталог РГБ:
  https://search.rsl.ru/ru/record/01002366119

Из этой группы берутся направления анализа: канцелярская тяжеловесность, выбор точного слова, удобство чтения, текстовая связность, соответствие формы жанру. Из неё не выводятся автоматические «запрещённые слова».

## 4. Продуктовые истории и ИИ-продукты

Эта группа обосновывает расширение `references/product-story.md`. Она не регулирует русский язык; она помогает не превращать продуктовый кейс в рекламный рассказ.

### Пользовательские потребности и сквозной сценарий

- GOV.UK Service Manual. Understand users and their needs:
  https://www.gov.uk/service-manual/service-standard/point-1-understand-user-needs
- GOV.UK Service Manual. Learning about users and their needs:
  https://www.gov.uk/service-manual/user-research/start-by-learning-user-needs
- GOV.UK Service Manual. Measuring the success of your service:
  https://www.gov.uk/service-manual/measuring-success/measuring-the-success-of-your-service

Используется для разделения пользовательской задачи, проверяемых потребностей, сквозного сценария и измерения результата.

### ИИ-функции

- Google PAIR. People + AI Guidebook:
  https://pair.withgoogle.com/guidebook-v2/
- NIST AI Risk Management Framework:
  https://www.nist.gov/itl/ai-risk-management-framework
- NIST AI RMF: Generative AI Profile:
  https://www.nist.gov/publications/artificial-intelligence-risk-management-framework-generative-artificial-intelligence
- NIST AI RMF Core:
  https://airc.nist.gov/airmf-resources/airmf/5-sec-core/

Эти источники поддерживают проверки происхождения данных, оценки качества, человеческого контроля, ошибок и деградации, границ применения и рисков ИИ-систем.

## 5. Что является эвристикой Skill, а не нормой

Следующие механизмы не имеют статуса языковой нормы и должны рассматриваться только как редакторские сигналы:

- плотность тире и двоеточий;
- коэффициент вариации длины предложений;
- порог «длинного» предложения;
- частота однофразовых абзацев;
- частота вводных переходов;
- словари промо- и корпоративных формул;
- частота разговорных частиц.

Их пороги должны калиброваться на корпусах разных жанров. До такой калибровки скрипт обязан выдавать предупреждение, а не оценку качества или авторства.

## 6. Главные расхождения с upstream

1. Полный запрет тире заменён анализом функции и, во вторую очередь, плотности.
2. Полный запрет двоеточия заменён анализом функции и шаблонного употребления.
3. Требование «субъект и действие сначала» заменено прозрачностью синтаксической основы и коммуникативной структурой.
4. «Не X, а Y» не запрещается: проверяется только повторяющийся риторический жест без фактической необходимости.
5. Добавлены русские зоны риска: номинализация, пассивно-безличные оболочки, цепочки родительного падежа, местоименная неоднозначность, перегруженные определения и деепричастные конструкции.
6. Устная речь выделена в отдельный режим.
7. Product Story расширен по issue #2 и дополнен трассировкой доказательств, метриками, степенью готовности и контрактом ИИ-системы.
8. Проверяющий скрипт принципиально не является детектором ИИ.


## 10. Репрезентативные корпуса и вариативность

- Russian National Corpus: About / structure / current corpora:
  https://ruscorpora.ru/en/page/corpora-about/
  https://ruscorpora.ru/en/page/corpora-structure/
  https://ruscorpora.ru/en/

НКРЯ охватывает литературную, разговорную, субстандартную и диалектную речь и разводит коллекции по задачам. В 2026 в НКРЯ добавлен GICR (VK) с социолингвистической аннотацией возраста, пола и места проживания. Эти признаки применяются для проверки устойчивости, а не генерации стереотипного голоса.

## 11. Неродной русский и GEC

- Russian Learner Corpus: Towards Error-Cause Annotation for L2 Russian (LREC-COLING 2024):
  https://aclanthology.org/2024.lrec-main.1241/
- Grammar Error Correction in Morphologically Rich Languages: The Case of Russian (TACL 2019):
  https://aclanthology.org/Q19-1001/
- Semi-automatically Annotated Learner Corpus for Russian (LREC 2022):
  https://aclanthology.org/2022.lrec-1.88/
- Multi-Reference Benchmarks for Russian Grammatical Error Correction (EACL 2024):
  https://aclanthology.org/2024.eacl-long.76/
- RuCoLA: Russian Corpus of Linguistic Acceptability (EMNLP 2022):
  https://aclanthology.org/2022.emnlp-main.348/

Multi-reference GEC особенно важен для eval-дизайна: несколько редакторов могут дать разные корректные лексические решения, поэтому редактуру нельзя оценивать строковым совпадением с одним эталоном.

## 12. Переводной русский

- Fiction in Russian Translation: A Translationese Study (RANLP 2021):
  https://aclanthology.org/2021.ranlp-1.84/

Исследование на параллельных данных НКРЯ показывает статистическую отличимость литературных переводов от оригинальной русской прозы. Это основание выделять переводной русский как отдельное условие, но не объявлять отдельные частотные признаки ошибками.

## 13. Упрощение и читаемость

- Creating an Aligned Russian Text Simplification Dataset from Language Learner Data (RuAdapt, 2021):
  https://aclanthology.org/2021.bsnlp-1.8/
- Assessment of reading difficulty levels in Russian academic texts:
  https://doi.org/10.3233/JIFS-169489
- W3C WAI: Use Clear and Understandable Content:
  https://www.w3.org/WAI/WCAG2/supplemental/objectives/o3-clear-content/
- W3C WAI: Understanding Guideline 3.1 Readable:
  https://www.w3.org/WAI/WCAG21/Understanding/readable.html

Эти источники поддерживают многомерную модель понятности. Длина предложения не используется как самостоятельная «оценка доступности».

## 14. Связность, референция и контекст

- RuCoCo: a new Russian corpus with coreference annotation:
  https://arxiv.org/abs/2206.04925
- RusConText Benchmark (ACL SRW 2025):
  https://aclanthology.org/2025.acl-srw.91/

Они используются для проектирования evals на местоименные референты, эллипсис и локальную дискурсивную связность, а не для простого счёта местоимений.


## 15. Диагностика грамматической коррекции по правилам

- What Aggregate Scores Hide: Per-Rule Evaluation of Russian Grammatical Error Correction (BEA 2026):
  https://aclanthology.org/2026.bea-1.32/
- LLMs in alliance with Edit-based models / LORuGEC (BEA 2025):
  https://aclanthology.org/2025.bea-1.38/
- Multi-Reference Benchmarks for Russian Grammatical Error Correction (EACL 2024):
  https://aclanthology.org/2024.eacl-long.76/

Эти работы используются для принципа: общий GEC-score недостаточен для контроля регрессий. Нужен отчёт по типам правил и несколько допустимых редакций там, где возможна вариативность.

## 16. Связность и контекст

- RuCoCo — русский корпус кореференции:
  https://arxiv.org/abs/2206.04925
- RusConText — coreference, discourse understanding, idioms, ellipsis:
  https://aclanthology.org/2025.acl-srw.91/

Эти ресурсы нужны для document-level evals референции и связности. Они не задают стилистическую норму.


## 17. Корпуса pilot benchmark 1.3

- RuCoLA: https://github.com/RussianNLP/RuCoLA — grammatical acceptability; Apache-2.0. Используется только как диагностический control, не как «корпус хорошего стиля».
- RIA News Dataset: https://github.com/RossiyaSegodnya/ria_news_dataset — опубликованные русские новости; CC BY-ND-NC. Сырые материалы не включаются в релиз.
- RuAdapt: https://github.com/Digital-Pushkin-Lab/RuAdapt — источник для будущих accessibility/simplification evals.
- RULEC-GEC: https://github.com/arozovskaya/RULEC-GEC — learner Russian / GEC; нужен для отдельного benchmark корректуры.
- Russian Legislative Corpus: https://huggingface.co/datasets/rcds/russian-legislative-corpus — будущая длинная official/legal выборка.
- Taiga: https://tatianashavrina.github.io/taiga_site/ — жанровые сегменты для fiction/social/subtitles/news; условия конкретного сегмента проверяются до использования.
- StRuCom: https://aclanthology.org/2025.acl-long.1465/ — русские структурированные комментарии к коду; будущая техническая выборка.

Упоминание корпуса в `SOURCES.md` не означает права на его перераспространение. `benchmark/corpora.json` хранит отдельную лицензионную заметку; сторонние сырые тексты в ZIP не входят.


## 18. Ablation порогов 1.4

Пороговые эксперименты `road-sign-density`, `sentence-uniformity`, `long-sentence`, `one-sentence-paragraphs`, `context-jargon-density` не вводят новую нормативную базу. Они являются статистическим тестом поведения детерминированного редакторского линтера.

Методика зафиксирована внутри пакета в `benchmark/ablation/spec.json`: natural held-out используется для alert burden, synthetic controls — только для чувствительности, а corpus candidate не активируется до заранее заданного freeze gate и последующего редакторского A/B.


## 19. External held-out sources 1.5

### LiveJournal / blog

- LJSearch: https://ljsear.ch/
- LJSearch FAQ: https://ljsear.ch/faq
- Zenodo LiveJournal Dataset: https://zenodo.org/records/7139731
- DOI: https://doi.org/10.5281/zenodo.7139731

LJSearch используется как архивный индекс и источник saved copies, а не как языковая норма. Конкретные `savedcopy?post=...` URL и discovery mirrors перечислены в `benchmark/external-heldout/LINKS.md`. Zenodo record указывает CC BY 4.0 для `livejournal.zip`, но не описывает внутреннюю схему данных; поэтому набор считается format-unverified и не допускается в freeze до инспекции содержимого.

### Media

- factRuEval-2016: https://github.com/dialogue-evaluation/factRuEval-2016
- RIA News Dataset: https://github.com/RossiyaSegodnya/ria_news_dataset

Для factRuEval используется document-level `book_*.txt`, а не отдельные токены/предложения. Условия RIA учитываются отдельно; raw article bodies не входят в release.

### Social

- Taiga downloads: https://tatianashavrina.github.io/taiga_site/downloads.html
- UD Russian Taiga: https://github.com/UniversalDependencies/UD_Russian-Taiga

### Oral

- Russian Everyday Dialogues: https://huggingface.co/datasets/kukunechka/russian-everyday-dialogues
- Common Voice Spontaneous Speech 4.0 — Russian: https://mozilladatacollective.com/datasets/cmqi2c2eu0062o5075atr17rs
- Russian National Corpus spoken search: https://ruscorpora.ru/new/search-spoken.html

Spoken datasets используются только при сохранении естественных document/session boundaries; utterance-level строки не склеиваются ради freeze gate.

### Product / business

- RBC Companies cases: https://companies.rbc.ru/cases/
- Ruward Awards/cases: https://ruward.ru/award/
- Sostav business blogs: https://www.sostav.ru/blogs/tags/13043

Полные copyrighted web texts — только transient/local research material. В release остаются URLs, hashes/features и aggregates.

### Official / legal

- RusLawOD: https://github.com/irlcode/RusLawOD/
- RusLawOD dataset: https://huggingface.co/datasets/irlspbru/RusLawOD
- Official legal open data: https://publication.pravo.gov.ru/OpenData

Источник RusLawOD используется для длинных full-document official/legal samples. Размер и лицензии источников не превращаются в языковые правила; это только база для held-out benchmark.

## Технические задания / requirements engineering

Проверено 2026-08-11:

- Росстандарт, карточка ГОСТ 34.602-2020 (статус «Действует», область применения ТЗ на АС): https://protect.gost.ru/gost/details/5876f733-ee91-431a-8cb6-9e02ea2436ac
- ГОСТ 19.201-78, состав и содержание ТЗ на программу/программное изделие: https://docs.cntd.ru/document/1200007648
- IEEE/ISO/IEC 29148-2018, Requirements Engineering: https://standards.ieee.org/standard/29148-2018.html

ГОСТ-профили checker-а проверяют только структурные признаки и не означают сертификацию соответствия.

## Humanizer / признаки шаблонного ИИ-письма

- `blader/humanizer`, версия 2.11.0, `SKILL.md`: https://github.com/blader/humanizer/blob/main/SKILL.md
- README и история правил: https://github.com/blader/humanizer/blob/main/README.md
- Лицензия upstream: MIT, Copyright (c) 2025 Siqi Chen: https://github.com/blader/humanizer/blob/main/LICENSE
- Upstream указывает в качестве содержательной основы Wikipedia WikiProject AI Cleanup, “Signs of AI writing”. В `human-writing-ru` перенесены и локализованы только редакторски полезные принципы; правила, завязанные на английскую пунктуацию/типографику, не применяются буквально.
