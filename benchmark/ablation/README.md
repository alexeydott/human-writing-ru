# Ablation пяти замороженных сигналов

Исследуются `road-sign-density`, `sentence-uniformity`, `long-sentence`, `one-sentence-paragraphs` и `context-jargon-density`.

## Протоколы

- `spec.json` + `scripts/ablate_signals.py` — **исторический protocol 1.4**. Эти файлы сохранены byte-identical только для воспроизведения прежнего прохода.
- `spec-v3.json` + `scripts/ablate_signals_v3.py` — **текущий decision protocol**. Новые решения о порогах не должны использовать historical runner.

## Protocol v3

1. Вход — только deduplicated `manifest.validated.csv` с уникальным `document_id`.
2. Каждый profile проходит preregistered size + provenance diversity gate.
3. Каждый применимый signal отдельно проходит ≥50 eligible документов / ≥10 000 eligible слов и собственный diversity gate.
4. Split строится по **connected components** всех известных зависимостей: общий `author_or_group`, `split_group`, `source_document_id` или `independence_group` связывает строки. Source-local document/independence IDs scope-ятся `source_id`.
5. Один компонент целиком попадает либо в calibration, либо в validation. Минимум: calibration ≥30 документов / 6000 слов, untouched validation ≥20 / 4000.
6. Candidate threshold выводится **только на calibration**. Validation не участвует в квантиле.
7. Source diversity измеряется и document share, и word share. `unknown` не считается отдельным источником и не разбавляет концентрацию; для профилей с обязательным author gate недостаточное metadata coverage блокирует evidence.
8. Synthetic positive controls проверяют чувствительность, но не входят в corpus quantiles.
9. На validation сравниваются old/candidate/off; alert reduction сам по себе не доказывает улучшение.
10. Для candidate/off требуется natural-alert adjudication `actionable / non_actionable / uncertain`. Конфликтующие labels для одного `(document_id, signal)` запрещены.
11. Ни один результат не редактирует `profiles/editorial-baseline.json` автоматически.

Создать decision result и шаблон natural-alert разметки:

```bash
python3 scripts/ablate_signals_v3.py \
  --manifest heldout-work/manifest.validated.csv \
  --output heldout-work/ABLATION_DECISION_V3.json \
  --annotation-template heldout-work/alert-adjudication.csv
```

После разметки:

```bash
python3 scripts/ablate_signals_v3.py \
  --manifest heldout-work/manifest.validated.csv \
  --output heldout-work/ABLATION_DECISION_V3.json \
  --annotations heldout-work/alert-adjudication.csv \
  --annotation-template heldout-work/alert-adjudication.next.csv
```

## Почему `off` не выигрывает автоматически

`off` всегда имеет нулевую alert burden и теряет targeted positive control. Поэтому отключение допускается к review только при достаточном количестве **естественных** alerts и низкой actionable precision. Если естественных alerts мало, правильный статус — `off_not_evaluable_insufficient_natural_alert_sample`, а не автоматическое отключение.

Все size/diversity/adjudication числа в `spec-v3.json` — preregistered требования к достаточности evidence, а не нормы русского языка.
