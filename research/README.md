# Исследовательские проходы 1.2

Версия 1.2 строилась пятью независимыми проходами. Каждый проход добавлял не новый «чёрный список», а отдельный класс условий и проверок.

1. `pass-01-corpus-coverage.md` — жанры, каналы, устная/социальная вариативность, раздельная корпусная калибровка.
2. `pass-02-origin.md` — learner Russian и переводной русский как разные задачи.
3. `pass-03-audience.md` — читаемость, упрощение и доступность относительно аудитории.
4. `pass-04-evals-calibration.md` — multi-reference редактура, document-level связность и eval-driven развитие.
5. `pass-05-diagnostic-granularity.md` — rule-level диагностика, negative controls и борьба с over-editing.

Основные последствия отражены в `SKILL.md`, `DATA_PLAN.md`, `evals/`, `profiles/` и `scripts/`.

- pass 15 — разрыв между technical prose и requirements quality;
- pass 16 — дизайн локализованных TZ rules;
- pass 17 — pruning ложных срабатываний;
- pass 18 — интеграция и safety review.

## Generative A/B

- `ab-eval-iteration-1.md` — A/B 1.9.0-beta.5 (policy 1.5.0) против 1.9.0-beta.4 (1.4.0) и без Skill: 420 прогонных запусков, 420 blind pairwise; без регрессий, current и previous неразличимы, Skill погранично впереди базового.
- `ab-eval-iteration-2.md` — итерация 2 с исправленным harness (24 из 28 кейсов с входными файлами, анонимные пути судьи, исходник в pairing-промпте): без регрессий, current и previous неразличимы (p=1.000), Skill значимо впереди базового (p=0.0019); паттерн «честный каркас» в генеративных кейсах.
