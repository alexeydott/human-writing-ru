# Final critical review — 1.8.0-beta.1

## Результат multi-pass review

Пакет прошёл повторные независимые проверки packaging/spec, acquisition/provenance, validator/dedup, decision split/gates, natural-alert adjudication, network workspace isolation, edit-integrity, generative A/B reproducibility, source-registry feasibility и deterministic release build.

В ходе review исправлены не только исходные недостатки, но и ошибки в промежуточных исправлениях. Наиболее показательный пример: новый release-integrity generator сначала падал из-за пропущенного `import json`; это обнаружил execution regression, хотя self-validator был зелёным. Отдельно была отменена неверная попытка трактовать `judge_schema.json` как JSON Schema — validator теперь проверяет фактический template contract.

Подробный audit trail: `research/pass-14-critical-review-v3.md`.

## TZ normalization / requirements layer

Добавлен отдельный `check_tz_ru.py` и русскоязычный registry `profiles/tz-rules.ru.json`. Он не меняет frozen prose policy 1.4.0. Профили `generic`, `gost34`, `gost19` разделены; соответствие ГОСТ не включается по умолчанию и structural check не считается сертификацией.

Смысловой autofix запрещён. `safe_normalize()` сохраняет fenced code и внутренние пробелы, а после смысловой редакторской правки используется `check_edit_integrity.py`.

На одном реальном ТЗ размером 1 337 279 байт последовательное сужение эвристик снизило alert burden `288 → 26 → 19 → 16`. Исходный текст в релиз не включён; `quality/TZ_REALWORLD_REGRESSION.json` хранит SHA-256 и агрегаты. Это не precision/recall claim без экспертной разметки.

## Frozen policy

Policy остаётся **1.4.0**. Перед релизом независимо сверяются SHA-256:

- `scripts/check_prose_ru.py` — `00648ff1df947042eedb4372ad4e4175f88af795f3ae883d98623d73b16b8a57`;
- `scripts/ablate_signals.py` — `f6b6eb357636fdfafcca3b78661cedac6c9b01b70709c267754026ca2a36454a`;
- `profiles/editorial-baseline.json` — `437199c10715bef7a2a74e9d172f5f40bef95a337e488a889a2819b2c6b96839`.

Ни один active threshold этим релизом не меняется.

## Current decision path

Допустимый current path:

`fresh acquisition → clean validator → representative manifest.validated.csv → v3 profile/signal/diversity gates → connected calibration/untouched-validation split → natural-alert adjudication → explicit human policy review`

Historical `ablate_signals.py` остаётся только для воспроизведения 1.4 и не вызывается current network orchestrator.

## Engineering / methodology score

`quality/QUALITY_SCORE.json` в текущем runtime: **96/100**.

Это означает только engineering/methodological readiness. Локальный максимум — 96, потому что executable `skills-ref` отсутствует; 4 балла за независимый external validator намеренно не начислены.

## Claims, которые запрещено делать по результату 1.8.0-beta.1

- нельзя утверждать, что пять style thresholds имеют доказанную corpus-wide precision/utility;
- нельзя утверждать, что candidate или `off` лучше frozen old threshold без полного external held-out v3;
- нельзя утверждать, что generative Skill статистически лучше 1.6.1 без реальных repeated A/B model runs;
- нельзя превращать отсутствие findings `check_edit_integrity.py` в доказательство semantic equivalence;
- нельзя считать registry feasibility фактом materialization;
- нельзя засчитывать unit tests вместо blind/human grading.
- нельзя считать 16 находок на real-world TZ доказательством высокой precision/recall без экспертной разметки.

## Следующий evidence milestone

1. Выполнить network acquisition на обычной HTTPS-машине с нужными local corpora/sidecar provenance.
2. Получить clean непустой `manifest.validated.csv`.
3. Пройти все profile + signal + diversity + split gates v3.
4. Разметить generated natural-alert template decisive labels.
5. Повторить v3 с annotations и отдельно review каждого из пяти сигналов.
6. Запустить `current_skill / previous_skill / without_skill` A/B в clean contexts и выполнить assertions + blind/human grading.
7. В CI дополнительно выполнить внешний `skills-ref validate`, если инструмент доступен.

До этих этапов empirical threshold confidence и generative superiority имеют статус **not established**.
