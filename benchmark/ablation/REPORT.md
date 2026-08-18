# human-writing-ru 1.4.0-beta.1 — five-signal ablation report

## Цель

Проверить по одному пять оставшихся редакторских сигналов в режиме **старый порог → консервативный candidate → off**, не меняя остальные правила одновременно. Этап относится к детерминированному `check_prose_ru.py`; это не generative A/B всего Skill.

## Данные и уровень доказательности

- natural in-scope local probe: **5 независимых связных документов / 2161 анализируемое слово** (`technical`, `product`);
- 4 каталога русской локализации: только secondary lexical controls, **не** корпус связной прозы;
- 1 художественный фрагмент: только domain-routing guard, исключён из threshold calibration;
- предыдущий 1.3 pilot: 15 документов / 1838 слов используется только как агрегированное подтверждение alert burden; per-document feature vectors для расчёта новых квантилей не реконструируются.

Целевой freeze gate — 50 независимых документов и 10 000 слов на основной профиль — **не достигнут**. Это размер исследовательской выборки, а не норма русского языка. Большие внешние корпуса не копировались в релиз; в текущем окружении не было надёжного способа материализовать достаточные raw corpora для полноценного freeze.

## Итог

**Ни один из пяти активных порогов не изменён.** На доступных in-scope clean documents старые пороги не дали целевых предупреждений; консервативные candidates не показали измеримого выигрыша и в доступных профилях фактически совпали со старыми значениями. Вариант `off` убирает targeted positive control, но на clean probe нет измеренного шума, который оправдывал бы такое отключение.

## По сигналам

### `road-sign-density`

Решение: **keep_old_no_evidence_for_threshold_change**.

| Профиль | Eligible docs | Слова | Old | Candidate | Clean old | Clean candidate | Control old/cand/off | Решение |
|---|---:|---:|---:|---:|---:|---:|---|---|
| official | 0 | 0 | 18.0 | 18.0 | 0 | 0 | T/T/F | no_data_keep_old |
| oral | 0 | 0 | 10.0 | 10.0 | 0 | 0 | T/T/F | no_data_keep_old |
| product | 3 | 672 | 10.0 | 10.0 | 0 | 0 | T/T/F | keep_old_freeze_gate_not_met |
| prose | 0 | 0 | 10.0 | 10.0 | 0 | 0 | T/T/F | no_data_keep_old |
| technical | 2 | 1489 | 15.0 | 15.0 | 0 | 0 | T/T/F | keep_old_freeze_gate_not_met |

### `sentence-uniformity`

Решение: **keep_old_no_evidence_for_threshold_change**.

| Профиль | Eligible docs | Слова | Old | Candidate | Clean old | Clean candidate | Control old/cand/off | Решение |
|---|---:|---:|---:|---:|---:|---:|---|---|
| official | 0 | 0 | 0.22 | 0.22 | 0 | 0 | F/F/F | no_data_keep_old |
| oral | 0 | 0 | 0.28 | 0.28 | 0 | 0 | T/T/F | no_data_keep_old |
| product | 2 | 512 | 0.3 | 0.3 | 0 | 0 | T/T/F | keep_old_freeze_gate_not_met |
| prose | 0 | 0 | 0.32 | 0.32 | 0 | 0 | T/T/F | no_data_keep_old |
| technical | 0 | 0 | 0.25 | 0.25 | 0 | 0 | F/F/F | no_data_keep_old |

### `long-sentence`

Решение: **keep_old_no_evidence_for_threshold_change**.

| Профиль | Eligible docs | Слова | Old | Candidate | Clean old | Clean candidate | Control old/cand/off | Решение |
|---|---:|---:|---:|---:|---:|---:|---|---|
| official | 0 | 0 | 60.0 | 60.0 | 0 | 0 | T/T/F | no_data_keep_old |
| oral | 0 | 0 | 32.0 | 32.0 | 0 | 0 | T/T/F | no_data_keep_old |
| product | 3 | 672 | 46.0 | 46.0 | 0 | 0 | T/T/F | keep_old_freeze_gate_not_met |
| prose | 0 | 0 | 42.0 | 42.0 | 0 | 0 | T/T/F | no_data_keep_old |
| technical | 2 | 1489 | 55.0 | 55.0 | 0 | 0 | T/T/F | keep_old_freeze_gate_not_met |

### `one-sentence-paragraphs`

Решение: **keep_old_no_evidence_for_threshold_change**.

| Профиль | Eligible docs | Слова | Old | Candidate | Clean old | Clean candidate | Control old/cand/off | Решение |
|---|---:|---:|---:|---:|---:|---:|---|---|
| official | 0 | 0 | 0.85 | 0.85 | 0 | 0 | F/F/F | no_data_keep_old |
| oral | 0 | 0 | 0.75 | 0.75 | 0 | 0 | T/T/F | no_data_keep_old |
| product | 0 | 0 | 0.7 | 0.7 | 0 | 0 | T/T/F | no_data_keep_old |
| prose | 0 | 0 | 0.7 | 0.7 | 0 | 0 | T/T/F | no_data_keep_old |
| technical | 0 | 0 | 0.8 | 0.8 | 0 | 0 | F/F/F | no_data_keep_old |

### `context-jargon-density`

Решение: **keep_old_no_evidence_for_threshold_change**.

| Профиль | Eligible docs | Слова | Old | Candidate | Clean old | Clean candidate | Control old/cand/off | Решение |
|---|---:|---:|---:|---:|---:|---:|---|---|
| official | 0 | 0 | 32.0 | 32.0 | 0 | 0 | T/T/F | no_data_keep_old |
| oral | 0 | 0 | 10.0 | 10.0 | 0 | 0 | T/T/F | no_data_keep_old |
| product | 3 | 672 | 18.0 | 18.0 | 0 | 0 | T/T/F | keep_old_freeze_gate_not_met |
| prose | 0 | 0 | 12.0 | 12.0 | 0 | 0 | T/T/F | no_data_keep_old |
| technical | 2 | 1489 | 28.0 | 28.0 | 0 | 0 | T/T/F | keep_old_freeze_gate_not_met |

## Отдельные наблюдения

1. **`one-sentence-paragraphs` — самый data-starved сигнал.** В local natural probe нет ни одного документа, который одновременно относится к активному rhythm-профилю и проходит минимальное требование по 8 абзацам. Любой новый порог сейчас был бы выдуманным.

2. **`sentence-uniformity`** имеет естественные данные только для двух `product` документов, прошедших минимум по предложениям. Для `technical` и `official` rhythm checks в активном профиле выключены.

3. **`long-sentence`** не дал clean alert на in-scope `product/technical`. Художественный domain guard при принудительном `prose`-режиме дал два срабатывания; это подтверждает необходимость жанровой маршрутизации, но не даёт основания поднимать нейтральный порог.

4. **`road-sign-density` и `context-jargon-density`** на доступном clean probe не создают alert burden. Поэтому отключать их только ради меньшего количества сообщений сейчас нет измерительного основания.

## Что добавлено в пакет

- `scripts/ablate_signals.py` — воспроизводимый runner;
- `benchmark/ablation/spec.json` — направления threshold changes и freeze gate;
- `benchmark/ablation/controls/` — собственные targeted sensitivity controls;
- `benchmark/ablation/LOCAL_PROBE_RESULTS.json`;
- `benchmark/ablation/LOCAL_PROBE_PROVENANCE.json`;
- `tests/test_ablation_tools.py`;
- `research/pass-10-five-signal-ablation.md`.

## Следующий corpus pass

При появлении внешних corpora методику менять не нужно. Следует заполнить manifest и повторить тот же runner. Приоритет профилей: `prose/media`, `oral`, `product`, длинные `official`, затем `social`. Для `one-sentence-paragraphs` нужны длинные документы с реальной абзацной структурой; для `context-jargon-density` — реальные product/business/technical материалы, а не UI-каталоги.

Активировать candidate можно только после corpus freeze gate, сохранения positive controls, отсутствия ухудшения clean alert burden и отдельного редакторского/generative A/B.
