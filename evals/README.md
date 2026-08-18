# Evals

## Trigger evals

`eval_queries.json` содержит realistic positive и near-miss negative запросы. `train_queries.json` и `validation_queries.json` — фиксированный disjoint split для настройки `description` без подглядывания в validation.

Stochastic activation нельзя оценивать одним наблюдением: запускать cases несколько раз в чистом контексте.

## Output evals

`evals.json` содержит generative cases с concrete assertions и dimensions из `coverage_matrix.json`. Покрытие каждого объявленного значения не означает полный декартов продукт измерений.

Проверка структуры:

```bash
python3 scripts/validate_eval_design.py
python3 scripts/audit_eval_coverage.py --json
```

## Reproducible A/B workspace

`prepare_ab_eval.py` **не вызывает модель**. Он только создаёт одинаковую файловую структуру для независимых runs:

```bash
python3 scripts/prepare_ab_eval.py \
  --workspace ../ab-eval \
  --iteration 1
```

По умолчанию arms:

- `current_skill`;
- `previous_skill`;
- `without_skill`.

`run-manifest.json` фиксирует immutable IDs current/previous skill, SHA исходного `evals.json`, а referenced input artifacts копируются в `iteration-N/_inputs/` с SHA-256. Каждый `run.json` хранит case, arm, prompt, **переносимые относительные пути** input/output/grading/timing и run index. Конкретный агентный/LLM runtime должен стартовать каждый run с чистым context и сохранить output/grading/timing в соответствующую директорию.

После фактических прогонов:

```bash
python3 scripts/aggregate_ab_eval.py \
  --iteration-dir ../ab-eval/iteration-1 \
  --output ../ab-eval/iteration-1/aggregate.json
```

Aggregator использует только реально присутствующие `grading.json` и `timing.json`; по умолчанию отказывается агрегировать неполную матрицу. `--allow-incomplete` — только diagnostic mode: headline delta не выводится, а сравнение строится исключительно по парным `(case, run_index)` observations. Arms/run keys уникальны, числовые метрики обязаны быть finite. Aggregator не выводит blind/human quality из автоматических assertions.

Полный процесс и judge axes описаны в `AB_EVAL_PROTOCOL.md`; минимальная форма human/blind verdict — в `judge_schema.json`.

## Edit integrity

После редактуры фактического текста `scripts/check_edit_integrity.py source.txt edited.txt` даёт дополнительный deterministic review signal по числам, единицам, датам, URL, модальности, отрицанию, условиям, attribution, quotes и консервативным entity-like изменениям. Это **не** доказательство семантической эквивалентности и не замена human/semantic grading.

## Не считать успехом

- просто меньше предупреждений линтера;
- более короткий текст без проверки смысла;
- совпадение с единственным эталоном;
- «похожесть на человека» по внешнему AI-detector;
- высокий общий score, если high-stakes или конкретная rule-category регрессировала;
- агрегат, построенный на неполных runs без явной маркировки incompleteness.
