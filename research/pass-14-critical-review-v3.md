# Pass 14 — multi-pass critical review и decision protocol v3

## Scope

Этот проход исправляет инженерные и методологические недочёты пакета **без изменения замороженной policy 1.4.0**. Его цель — уменьшить вероятность ложного вывода из benchmark/A-B инфраструктуры, а не добавить новые русскоязычные эвристики.

Нельзя интерпретировать этот проход как доказательство, что пять style thresholds оптимальны, или что generative Skill лучше 1.6.1: внешний held-out v3 и реальные model runs в текущем runtime не выполнены.

## Проход A — packaging/spec и version split

Исправлено/проверено:

- install directory — `human-writing-ru/`, совпадает с `name` в `SKILL.md`;
- package version `1.7.0-beta.2` отделена от frozen policy `1.4.0`;
- frontmatter использует `license`, `compatibility`, `metadata.version`, `metadata.policy_version`;
- self-validator проверяет YAML, ссылки, literal `\\n`, version drift и generated artifacts;
- current release integrity больше не смешивается с историческим snapshot 1.6.1.

Основание: Agent Skills specification требует совпадения `name` с parent directory и поддерживает progressive disclosure / metadata. Reference: `https://agentskills.io/specification`.

## Проход B — утечка calibration → validation

Старый ablation вычислял candidate и оценивал его на одном corpus. В v3 candidate строится **только на calibration**; validation не участвует в квантиле.

Split не использует «первый подходящий group key». Он строит connected components по всем известным ограничениям:

- `author_or_group`;
- `split_group`;
- `source_document_id`;
- `independence_group`.

Source-local IDs scope-ятся `source_id`, чтобы два независимых корпуса с ID `1` не склеивались. Human-readable author/source/channel нормализуются casefold+whitespace; opaque IDs остаются case-sensitive.

## Проход C — gates недостаточной выборки

Profile `50 documents / 10k words` оставлен как preregistered minimum, но больше не считается достаточным для решения. Добавлены:

- profile source/channel/author diversity;
- signal-specific eligible docs/words;
- signal-specific diversity;
- calibration minimum;
- untouched validation minimum.

`unknown`, `n/a`, `none`, `?` и подобные значения не считаются отдельными источниками/авторами и не «разбавляют» концентрацию.

## Проход D — достижимость preregistered gate

Критическая проверка показала, что строгий gate может быть логически недостижим даже при идеальной сети, если registry не содержит требуемых strata.

Исправления:

- technical получил второй source family — русские страницы `kubernetes/website/content/ru/docs`; upstream LICENSE — CC BY 4.0;
- reusable/navigation pages исключаются routing regex/minimum-size checks;
- prose/oral author-concentration gate теперь имеет machine-readable feasibility `author_provenance_capable`;
- Duma/Taiga local imports могут подавать verified author/speaker metadata через sidecar manifest.

Self-validator теперь проверяет feasibility registry до сетевого запуска. Это только проверка **возможности** пройти gate, а не утверждение о materialized evidence.

## Проход E — acquisition и document boundaries

Найдены и исправлены реальные runtime/provenance bugs:

- LJSearch adapter после успешного fetch обращался к неопределённым `profile/channel`; добавлен mocked-success regression;
- profile/channel для factRuEval и ZIP берутся из registry;
- GitHub raw paths используют percent encoding;
- multi-ZIP сохраняет provenance archive part без выдумывания source diversity;
- XML Putin Corpus берёт `<speech>`, не editorial `<meta>`, и не приписывает multi-speaker event одному фиктивному автору;
- local sidecar `manifest.csv` передаёт natural boundaries и verified author/split IDs; без sidecar действует conservative `one .txt = one document` и автор не угадывается.

Публичный RUB Corpus TSV описан upstream как `date / href / text`; отдельного speaker column там нет. Поэтому speaker не выводится из URL эвристически.

## Проход F — dedup/routing conflicts

Acquisition раньше мог global-SHA dedupe-ить одинаковый текст между profiles и тем самым **скрыть** routing conflict до validator. Теперь acquisition exact dedupe scoped по `(profile, sha256)`.

Validator:

- объединяет exact/near copies внутри profile;
- identical text в разных profiles считает blocking `cross_profile_exact_duplicate`, а не выбирает произвольного representative;
- требует уникальные document IDs;
- source-scopes explicit independence IDs;
- пишет только representative `manifest.validated.csv`.

## Проход G — validator → decision integrity

Закрыты два пути обхода:

1. network orchestrator больше не продолжает decision-chain, если validator subprocess вернул non-zero или `validation_clean=false`;
2. v3 runner не доверяет manifest слепо — повторно проверяет file SHA и exact duplicate bytes перед threshold computation.

Также исправлен path rebasing: если `manifest.validated.csv` записан в другой каталог, относительные пути переписываются относительно **его** location.

## Проход H — workspace contamination

Повторный network run раньше мог унаследовать старые строки `manifest.csv` из того же `output-dir`.

Теперь:

- fresh workspace — default;
- generated manifests/reports/decisions предыдущего experiment удаляются;
- `--resume` нужно указать явно;
- resume блокируется, если old manifest содержит source IDs вне текущего selection.

## Проход I — natural-alert adjudication

`off` больше не может «побеждать» только потому, что имеет нулевую alert burden.

Natural alerts размечаются `actionable / non_actionable / uncertain`. Важная корректировка этого прохода: `uncertain` **не входит в decisive denominator**. Иначе большое число сомнительных случаев искусственно снижало бы actionable precision и создавало ложную поддержку `off`.

Конфликтующие duplicate labels, неизвестные document/signal references и unsupported labels блокируются.

## Проход J — edit integrity

Добавлен отдельный deterministic source→edited review checker для высокоточных изменений:

- numbers/dates/currency;
- URL;
- number+unit;
- modality/negation/conditions/attribution/causality;
- exact quotes;
- conservative entity-like names/acronyms.

Исправлена отдельная ошибка: URL нельзя полностью lower-case-ить, потому что path/query могут быть case-sensitive. Нормализуются только scheme/host.

Отсутствие findings **никогда не объявляется доказательством semantic equivalence**.

## Проход K — generative A/B reproducibility

Agent Skills evaluation guidance рекомендует current/previous/baseline, clean contexts, repeated runs, saved grading/timing. Reference: `https://agentskills.io/skill-creation/evaluating-skills`.

Инфраструктура теперь:

- фиксирует immutable `current_skill` и конкретный `previous_skill_id`;
- фиксирует SHA eval suite;
- копирует input artifacts внутрь iteration workspace и фиксирует их SHA;
- использует переносимые relative paths;
- требует unique arms/run keys;
- отвергает NaN/Inf metrics;
- full aggregation по умолчанию требует complete matrix;
- `--allow-incomplete` diagnostic mode считает только paired `(case, run_index)` и не публикует unpaired headline delta.

Ни один Python script здесь не притворяется LLM runtime: outputs/grading должны быть реально получены внешним агентом/моделью.

## Проход L — self-validation и stale artifacts

Найдены/закрыты дополнительные consistency defects:

- `SOURCE_MANIFEST.csv` не содержал новый Kubernetes source — regenerated from current registry;
- self-validator теперь сверяет registry↔CSV routing projection;
- stale current-facing v2 operational paths запрещены;
- `validate_eval_design.py` требует конкретный `previous_skill_id`, если policy сравнивает с previous Skill;
- диагностический validator normalizes unknown/case provenance так же консервативно, как decision protocol;
- duplicate line в `RESEARCH_REPORT.md` удалена;
- current deterministic builder генерирует `quality/RELEASE_INTEGRITY.json`.

### Ошибка, найденная в собственном исправлении

При первом добавлении `write_release_integrity()` я забыл `import json`. `validate_skill.py` это не мог заметить, потому что build path не исполняется. `test_release_builder.py` немедленно упал с `NameError`; импорт добавлен и regression повторно прошёл. Это отдельное подтверждение, почему self-validation и execution tests нужны одновременно.

Ранее в этом же цикле была сделана неверная предпосылка, что `evals/judge_schema.json` является JSON Schema с обязательным `type: object`. Файл на самом деле является собственным template contract. Навязанное требование удалено; validator проверяет фактические поля template, а не выдуманную схему.

## Что доказано этим проходом

Доказано только инженерное/методологическое:

- frozen policy bytes не изменились;
- current decision path не использует historical runner;
- preregistered evidence gates нельзя обойти известными путями, покрытыми regression/adversarial tests;
- release build детерминирован и проверяет current tracked hashes;
- eval/A-B workspace не создаёт fictitious model results.

## Что НЕ доказано

- thresholds policy 1.4 не получили новую empirical validity;
- `ready_for_decision_evaluation=true` не получен на полном внешнем corpus в этом runtime;
- candidate/off не активированы;
- generative A/B current vs previous vs without-skill не выполнен;
- blind/human preference не измерен;
- внешний `skills-ref validate` не выполнен, если executable отсутствует.

Следующий качественно новый evidence-stage остаётся прежним: реальная network materialization → clean deduplicated `manifest.validated.csv` → full v3 gates → natural-alert adjudication; отдельно — реальный generative A/B.
