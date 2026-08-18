# Pass 16 — rule design

Правила разделены на completeness, verifiability, modality, atomicity, ambiguity, time, security, consistency, duplication, traceability, acceptance и structure. Все сообщения и рекомендации локализованы на русский в `profiles/tz-rules.ru.json`.

Autofix запрещён для смысловых правил. `safe_normalize()` ограничен пробелами/пустыми строками и не меняет числа, слова или модальность.
