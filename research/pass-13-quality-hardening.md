# Pass 13 — quality hardening and decision validity

Цель прохода — не добавить новые стилистические эвристики, а уменьшить вероятность ошибочного вывода о качестве самого Skill и пяти замороженных сигналов.

## Найденные дефекты

1. versioned parent directory нарушал strict Agent Skills `name == parent directory`;
2. frontmatter проверялся regex вместо YAML parser;
3. два reference содержали literal `\\n`;
4. README имел дублированный хвост и смешивал package/policy version;
5. candidate threshold в ablation 1.4 выводился и оценивался на одном наборе;
6. profile freeze не гарантировал signal-specific eligibility;
7. source/channel concentration только сообщалась, но не блокировала решение;
8. `off` можно было формально сравнивать без доказательства редакторской бесполезности alerts;
9. Skill не имел deterministic safety diff для сохранения чисел/модальности/атрибуции;
10. product/customer case, portfolio и AI system contract грузились одним большим reference;
11. generative eval suite не покрывал все заявленные dimensions.

## Исправления

- strict package validator + version/policy split;
- ablation protocol v2 with grouped calibration/validation, signal/diversity gates and adjudication requirements;
- edit-integrity checker;
- progressive disclosure split;
- 28-case generative suite + A/B protocol;
- objective engineering/methodology quality score.

## Ограничение вывода

Даже идеальный локальный regression suite не доказывает валидность стилевых порогов на реальном русском корпусе. Поэтому `quality_score >90` относится только к инженерно-методической готовности; empirical threshold confidence остаётся `not_established` до внешнего held-out v2.
