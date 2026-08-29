# Roadmap после 1.9.0-beta.2 critical review

> **Статус (2026-08-29):** пакет выпущен в **stable 1.9.0** — все stable-критерии §5
> закрыты одновременно (quality score 100/100, held-out v3, generative A/B ×2,
> `skills-ref` в CI, отсутствие неразмеченных candidate-решений); политика **1.5.0**,
> frozen-входы не тронуты.
> Этап 1 завершён (2026-08-27) — полный внешний held-out v3,
> решения человека применены политикой **1.5.0** (пакет 1.9.0-beta.5).
> Этап 3 (generative A/B) выполнен 2026-08-28 (итерация 1) и 2026-08-29 (итерация 2):
> `research/ab-eval-iteration-1.md`, `research/ab-eval-iteration-2.md` — по 420
> прогонных запусков и 420 blind pairwise. Итог: регрессий нет (high-stakes
> 3.9–4.0, фабрикаций нет), current и previous статистически неразличимы
> (p=1.000), Skill значимо впереди базового без Skill (p=0.0019 по preference,
> over_editing 0.60 против 1.14). Все stable-критерии §5 закрыты (score 100/100
> и `skills-ref` validation в CI — 2026-08-28).

## 1. Следующий обязательный этап — данные, не новые эвристики

Завершён (2026-08-27): policy 1.5.0 применена по итогам полного held-out v3
(детали — `POLICY_RERUN_PLAN.md`, CHANGELOG 1.9.0-beta.5); frozen-входы
перефиксированы на `baseline_release: 1.5.0`. До следующего изменения порогов
качественно новый результат снова должен прийти из внешнего held-out.

1. Материализовать естественно ограниченные документы для `prose`, `oral`, `product`, `technical`, `official`. ✅ (911 документов)
2. Пройти exact/near-copy dedup и получить `manifest.validated.csv`. ✅
3. Для каждого profile выполнить size + diversity gate. ✅ (все 5 профилей)
4. Для каждого применимого сигнала отдельно выполнить signal eligibility + signal diversity gate. ✅
5. Разделить группы на calibration/untouched validation без пересечения любого известного author/split/source-document/independence component. ✅
6. Получить candidate только на calibration. ✅
7. На validation сформировать `--annotation-template`, разметить natural alerts как `actionable / non_actionable / uncertain` слепо к arm, где возможно. ✅ (217/217, 0 uncertain)
8. Только после этого принимать решение `keep old / candidate / off`; active profile не меняется автоматически. ✅ (решения в `data/heldout-work-policy-1.6/ABLATION_DECISION_V3.json`)

## 2. Приоритеты корпуса

- `prose`: длинные blog/media/social документы; для paragraph-rhythm нужен естественный ≥8-paragraph subset.
- `oral`: отдельно prepared speech, Q&A/interview и spontaneous dialogue/monologue; не склеивать несвязанные ASR utterances.
- `product`: customer/product cases должны преобладать над общими business documents.
- `technical`: минимум два независимых source families; reusable includes/templates не считать отдельными документами.
- `official`: полные нормативные/административные документы с контролем amendment/template near-copies.

## 3. Generative A/B

Запустить `evals/AB_EVAL_PROTOCOL.md` для текущей версии, предыдущей версии и baseline без Skill:

- 5 независимых запусков на case; ✅ (420 runs, итерация 1)
- чистый context; ✅
- assertions + blind pairwise; ✅ (420 pairwise, 28 кейсов × 5 runs × 3 пары)
- factual/meaning/modality/voice/over-edit отдельно; ✅
- high-stakes cases не усреднять с обычными так, чтобы регрессия скрылась. ✅ (выделены в отчёте)

Выполнено 2026-08-28: `research/ab-eval-iteration-1.md`.
Выполнено 2026-08-29 (итерация 2, исправленный harness: входные файлы в 24 из 28 кейсов, анонимные пути судьи, исходник в pairing-промпте): `research/ab-eval-iteration-2.md` — без факт/high-stakes регрессий, current и previous неразличимы (p=1.000), Skill значимо лучше без Skill (p=0.0019); обнаружен паттерн «честный каркас» в генеративных кейсах (product-story 5:0 против обоих skill-армов).

## 4. Что можно добавлять только после evidence

- новый user-facing style signal — только с отдельным positive/negative set и held-out precision;
- тяжёлый morphosyntax/coreference модуль — отдельной опциональной веткой, а не скрытой зависимостью core Skill;
- новые linter profiles — только если текущие channel strata показывают устойчиво разные distributions и редакторскую пользу.

## 5. Stable criteria

Stable-релиз требует одновременно:

- engineering/methodology quality score >90; ✅ (2026-08-28: 100/100, `quality/QUALITY_SCORE.json`)
- успешный внешний Agent Skills reference validation (`skills-ref`) в CI; ✅ (2026-08-28: `.github/workflows/skills-ref.yml` — PyPI `skills-ref`, CLI `agentskills validate` на push/PR: корень пакета + содержимое собранного релизного ZIP)
- хотя бы один полный external held-out v3 evidence run; ✅ (2026-08-27, `heldout-work-policy-1.6`)
- generative A/B без factual/high-stakes regression; ✅ (2026-08-28, `research/ab-eval-iteration-1.md`: high-stakes 4.0/4.0, фабрикаций нет; подтверждено второй итерацией 2026-08-29)
- отсутствие неразмеченных candidate/off решений, которые объявляются доказанными. ✅

Все критерии закрыты одновременно — stable-релиз **1.9.0** выполнен 2026-08-29.

## TZ normalization follow-up

- собрать реальный обезличенный корпус ТЗ с экспертной разметкой rule-level TP/FP;
- не калибровать новые пороги по synthetic cases;
- добавить optional cross-reference/ID graph и contradiction candidates только после corpus evidence;
- сохранять generic/GOST structural profiles раздельно.
