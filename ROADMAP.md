# Roadmap после 1.9.0-beta.2 critical review

## 1. Следующий обязательный этап — данные, не новые эвристики

Лингвистическая policy 1.4 и три frozen inputs остаются неизменными. Следующий качественно новый результат должен прийти из внешнего held-out corpus.

1. Материализовать естественно ограниченные документы для `prose`, `oral`, `product`, `technical`, `official`.
2. Пройти exact/near-copy dedup и получить `manifest.validated.csv`.
3. Для каждого profile выполнить size + diversity gate.
4. Для каждого применимого сигнала отдельно выполнить signal eligibility + signal diversity gate.
5. Разделить группы на calibration/untouched validation без пересечения любого известного author/split/source-document/independence component.
6. Получить candidate только на calibration.
7. На validation сформировать `--annotation-template`, разметить natural alerts как `actionable / non_actionable / uncertain` слепо к arm, где возможно.
8. Только после этого принимать решение `keep old / candidate / off`; active profile не меняется автоматически.

## 2. Приоритеты корпуса

- `prose`: длинные blog/media/social документы; для paragraph-rhythm нужен естественный ≥8-paragraph subset.
- `oral`: отдельно prepared speech, Q&A/interview и spontaneous dialogue/monologue; не склеивать несвязанные ASR utterances.
- `product`: customer/product cases должны преобладать над общими business documents.
- `technical`: минимум два независимых source families; reusable includes/templates не считать отдельными документами.
- `official`: полные нормативные/административные документы с контролем amendment/template near-copies.

## 3. Generative A/B

Запустить `evals/AB_EVAL_PROTOCOL.md` для текущей версии, предыдущей версии и baseline без Skill:

- 5 независимых запусков на case;
- чистый context;
- assertions + blind pairwise;
- factual/meaning/modality/voice/over-edit отдельно;
- high-stakes cases не усреднять с обычными так, чтобы регрессия скрылась.

## 4. Что можно добавлять только после evidence

- новый user-facing style signal — только с отдельным positive/negative set и held-out precision;
- тяжёлый morphosyntax/coreference модуль — отдельной опциональной веткой, а не скрытой зависимостью core Skill;
- новые linter profiles — только если текущие channel strata показывают устойчиво разные distributions и редакторскую пользу.

## 5. Stable criteria

Stable-релиз требует одновременно:

- engineering/methodology quality score >90;
- успешный внешний Agent Skills reference validation (`skills-ref`) в CI;
- хотя бы один полный external held-out v3 evidence run;
- generative A/B без factual/high-stakes regression;
- отсутствие неразмеченных candidate/off решений, которые объявляются доказанными.

## TZ normalization follow-up

- собрать реальный обезличенный корпус ТЗ с экспертной разметкой rule-level TP/FP;
- не калибровать новые пороги по synthetic cases;
- добавить optional cross-reference/ID graph и contradiction candidates только после corpus evidence;
- сохранять generic/GOST structural profiles раздельно.
