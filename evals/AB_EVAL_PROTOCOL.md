# Generative A/B evaluation protocol

Этот протокол оценивает **поведение Skill**, а не детерминированный `check_prose_ru.py`.

## Сравниваемые arms

Для каждого eval запускай в чистом контексте:

1. `current_skill`;
2. `previous_skill`;
3. `without_skill`.

Рекомендуется 5 независимых запусков на arm. Минимум для blind pairwise — 3 независимых сравнения на case. Не переносить историю предыдущего запуска в следующий.


## Reproducibility contract

До первого model-run workspace должен зафиксировать package IDs обеих Skill arms (`current_skill` и конкретный `previous_skill`), SHA исходного eval-набора и SHA всех input artifacts. Input files копируются внутрь iteration workspace; run records используют относительные пути, чтобы один manifest означал те же байты после переноса каталога.

Неполную матрицу нельзя сравнивать непарными средними. Diagnostic `--allow-incomplete` показывает только совпадающие пары `(case, run_index)` и явно маркирует результат incomplete; он не является основанием для headline claim о превосходстве current Skill.

## Grading

Сначала проверяются конкретные assertions case. PASS требует видимого доказательства в output; заголовок или декларация без содержания не засчитываются.

Затем blind judge сравнивает outputs без указания arm по независимым осям:

- factual/meaning preservation;
- modality/attribution preservation;
- grammatical correctness;
- register fit;
- voice preservation;
- task completion;
- over-editing;
- overall preference.

Для фактической редактуры `scripts/check_edit_integrity.py` используется как дополнительный deterministic safety signal, но не заменяет смысловую оценку.

## Решение о выпуске

Версия не считается улучшением только из-за большего числа правил. Для релизного утверждения об улучшении нужны одновременно:

- не хуже factual/meaning safety;
- не хуже trigger precision/recall на validation split;
- статистически/практически устойчивое преимущество в blind pairwise хотя бы по целевым задачам изменения;
- отсутствие нового класса систематического over-edit;
- отсутствие регрессии high-stakes cases.

Если преимущество нестабильно между runs или держится на одном жанре, формулируй результат как локальный, а не общий.
