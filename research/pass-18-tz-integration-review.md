# Pass 18 — integration and safety review

ТЗ-функциональность встроена без нового параллельного Skill: один router в `SKILL.md`, общий `technical` prose-linter и дополнительный requirements checker. После глубокой редактуры используется `check_edit_integrity.py` как страховка от изменения чисел, модальности, отрицания, условий, ссылок и сущностей.

Compliance-claim намеренно ограничен: `gost34`/`gost19` проверяют структуру эвристически и не являются сертификацией соответствия.
