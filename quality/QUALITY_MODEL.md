# Quality / reliability model

Здесь `reliability score` означает **инженерную и методическую готовность пакета**, а не вероятность того, что любой стилевой порог «правилен» для русского языка.

Максимум — 100 баллов. Цель pre-release: **>90**.

| Блок | Вес | Что подтверждает |
|---|---:|---|
| Agent Skills spec / package hygiene | 14 | стабильный root/name/frontmatter, ссылки, JSON/YAML, отсутствие мусора и stale operational refs |
| Regression suite | 24 | детерминированные скрипты и известные edge/adversarial cases |
| Eval design / coverage | 16 | ≥24 generative cases, declared coverage, disjoint triggers, reproducible A/B workspace/aggregation |
| Ablation protocol v3 | 22 | signal/diversity gates, connected-component calibration/validation split, provenance coverage, adjudication before decision |
| Edit integrity safety | 10 | числа+единицы, даты, URL, модальность, отрицание, условия, attribution, quotes, conservative entity-like review |
| Frozen reproducibility | 6 | active 1.4 linter/profile/historical runner не изменены |
| Documentation / progressive disclosure | 4 | package/policy version separation и узкие references |
| External `skills-ref validate` | 4 | независимая reference-validator проверка, если инструмент реально доступен |

Если `skills-ref` не установлен в runtime, эти 4 балла **не начисляются**. Локальный максимум тогда равен 96; отсутствие инструмента нельзя выдавать за успешную внешнюю валидацию.

## Отдельная эмпирическая уверенность

Corpus validity пяти стилевых сигналов **не входит** в engineering score. Пока не выполнен внешний held-out protocol v3 с достаточными diversity/signal/split gates и требуемой natural-alert adjudication, её статус — `not_established_until_external_heldout_v3`.

Аналогично generative superiority не считается установленной, пока не выполнены реальные `current_skill / previous_skill / without_skill` runs и blind/human grading. Большое число unit tests не компенсирует отсутствие этих данных.
