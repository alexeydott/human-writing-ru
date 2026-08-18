# Журнал изменений

## 1.9.0-beta.3 — локальные данные и пакет релиза

- Каталоги локальных корпусов и результаты воспроизводимого рабочего конвейера сведены в `data/`; устаревшие ссылки на `examples/` и `.examples` удалены из документации и сценариев.
- Обновлены локальный запуск held-out-проверки и `.github/workflows/heldout-gate.yml`: корень корпусов и каталог результатов по умолчанию находятся в `data/`.
- Добавлено руководство [data/README.md](data/README.md) с источниками корпусов, требованиями к локальным средствам и командами воспроизведения.
- Сценарий `scripts/build_release.py` теперь без параметров создаёт готовый детерминированный ZIP и файл SHA-256 в `dist/`; `--output-dir` позволяет выбрать другой каталог. Предыдущие архивы и контрольные суммы не включаются в новый пакет.
- Пакет не содержит скачанные корпуса и результаты локального запуска; в него входят только краткое руководство и шаблон манифеста для подготовки данных.
- Публикация GitHub-релиза сборщиком не выполняется: каталог `dist/` содержит только исходные файлы для последующей публикации.

## 1.9.0-beta.2

- Полная пересборка после интеграции нормализации ТЗ и русскоязычной адаптации `blader/humanizer` 2.11.0; функциональные правила из 1.8.0-beta.1 и 1.9.0-beta.1 сохранены.
- Исправлена гигиена релиза: `.pytest_cache`, `__pycache__`, `.pyc`, `.mypy_cache`, `.ruff_cache`, `.coverage`, `.DS_Store` и локальный `.git` исключаются из детерминированного ZIP.
- `quality/RELEASE_INTEGRITY.json` теперь явно отслеживает ключевые файлы ТЗ-нормализации и Humanizer-адаптации, включая references, eval-наборы и third-party notices.
- Regression-тест сборщика проверяет отсутствие локальных cache/build artifacts и наличие ключевых integration-файлов в integrity snapshot.
- Frozen linguistic/linter policy остаётся **1.4.0**; пороги `check_prose_ru.py` не изменены.

## 1.9.0-beta.1

- Интегрированы полезные редакторские принципы `blader/humanizer` 2.11.0 как русскоязычный reference `references/ai-writing-patterns.md`.
- Добавлены проверки раздувания значимости, псевдоанализа, неопределённых источников, формульных секций, принудительных троек, синонимической карусели, ложных диапазонов, chatbot-artifacts, накопления оговорок, пустых финалов, фиктивных возражений и альтернатив.
- Авторский образец формально поставлен выше общих humanization-эвристик; одиночный признак не трактуется как доказательство ИИ-происхождения.
- Явно отклонён буквальный перенос англоязычных правил о запрете тире, ASCII-кавычках и дефисных compound modifiers.
- Добавлен `THIRD_PARTY_NOTICES.md` с MIT-attribution upstream.
- Лингвистическая/линтерная policy остаётся 1.4.0: новые знания пока интегрированы в генеративно-редакторский слой без изменения frozen порогов детерминированного линтера.

## 1.8.0-beta.1

- Добавлена нормализация/редактура ТЗ и спецификаций требований.
- Новый `check_tz_ru.py`, локализованный registry правил и профили generic/gost34/gost19.
- Safe normalization не меняет смысл; semantic autofix намеренно запрещён.
- Добавлены false-positive controls и passes 15–18.
- Frozen prose policy остаётся 1.4.0.

## 1.7.0-beta.2 — multi-pass critical review

- Preserved policy 1.4.0 byte-for-byte: frozen `check_prose_ru.py`, historical `ablate_signals.py`, and `profiles/editorial-baseline.json` hashes are unchanged.
- Replaced the current decision path with protocol v3: connected-component calibration/validation split across all known author/split/source-document/independence constraints; candidate thresholds are learned only on calibration.
- Closed orchestrator bypasses: current network decisions require a clean validator result and call only `ablate_signals_v3.py`; historical 1.4 runner remains reproduction-only.
- Hardened provenance evidence: unknown sentinels do not count as diversity; labels are case/whitespace normalized where safe; source concentration uses documents and word mass; author metadata coverage is blocking where preregistered.
- Added registry feasibility checks for source/channel and author-provenance capability. Added Russian Kubernetes documentation as a second technical source family; local Duma/Taiga imports can carry verified provenance through sidecar manifests.
- Fixed acquisition correctness defects: LJSearch successful fetch no longer reaches undefined `profile/channel`; exact acquisition dedupe is profile-scoped so contradictory cross-profile routing remains visible to the validator; unverified-format sources are blocked from decision runs.
- Validator now blocks duplicate IDs and cross-profile exact text conflicts, rebases paths for custom validated-manifest locations, normalizes provenance diagnostics, and emits only representative decision rows.
- Decision runner rechecks document SHA and exact-dedup after validation as defense-in-depth; annotation references/labels must be unique and valid; `uncertain` does not count as decisive natural-alert evidence.
- Network workspace is fresh by default. `--resume` is explicit and rejects old manifest source IDs outside the current selection, preventing silent cross-run contamination.
- Added deterministic edit-integrity signals for number+unit/entity-like changes and corrected URL comparison so case-sensitive path changes are not hidden. Findings remain review signals, never proof of semantic equivalence.
- Generative A/B workspace now records immutable current/previous skill IDs, eval SHA and copied input-artifact SHA; incomplete diagnostics use only paired `(case, run_index)` observations and never expose unpaired headline deltas.
- Strengthened self-validation: parent directory/name/version/frontmatter, stale operational refs, source registry↔CSV projection, registry feasibility, frozen hashes, current release-integrity hashes, eval contracts and mutation tests.
- Deterministic builder now emits current `quality/RELEASE_INTEGRITY.json`; historical 1.6.1 integrity data is explicitly marked as a historical snapshot. A release-builder regression caught and led to fixing a missing `json` import in the new generator.
- Current engineering/methodology quality score is 96/100 in this runtime; 4 external `skills-ref validate` points are deliberately not awarded because the executable is unavailable. External held-out v3 evidence and real generative A/B superiority remain **not established**.

## 1.7.0-beta.1 — quality hardening

- Agent Skills spec/package conformance: stable root name, YAML metadata, version/policy separation, stronger validator.
- Ablation protocol v2: grouped calibration/validation split, signal eligibility gates, source/channel diversity gates, alert adjudication before candidate/off decisions.
- Added deterministic edit-integrity safety diff and regression tests.
- Split product/customer case, portfolio and AI-feature references for progressive disclosure.
- Expanded generative evals from 16 to 28 and added A/B/blind-eval protocol.
- Added 100-point engineering/methodology quality gate; empirical threshold confidence remains explicitly pending external held-out v2.
- Frozen `check_prose_ru.py`, `ablate_signals.py` and `profiles/editorial-baseline.json` remain unchanged.


## 1.6.1-beta.1 — network gate executor hardening

- Added `scripts/run_external_heldout_gate.py`: one-shot network acquisition → validator → unchanged ablation orchestration. `ablate_signals.py` is unreachable unless the validator reports the all-five-profile freeze gate as satisfied.
- Added `FROZEN_INPUT_SHA256.json` and pre/post integrity checks for `check_prose_ru.py`, `ablate_signals.py`, and `profiles/editorial-baseline.json`; all three remain byte-identical to the frozen 1.4 inputs.
- Fixed a latent `factRuEval` acquisition error (`profile/channel` now come from the source registry).
- Fixed GitHub raw-path URL encoding for spaces/non-ASCII paths and added direct `github_tree_text` acquisition for Russian Yandex Cloud Markdown and the XML Putin Corpus mirror.
- Extended ZIP acquisition to multiple upstream archives without inventing source diversity; RuREBus train/test parts keep one `source_id` and archive-specific provenance.
- Added CSV/TSV natural-row record handling for record-oriented corpora such as RUB Corpus; rows are not concatenated into pseudo-documents.
- Added source-process wall-clock timeout to the network orchestrator so one unavailable endpoint cannot stall the complete five-profile acquisition pass.
- Empty `manifest.validated.csv` now preserves the full input manifest schema instead of degrading to three columns.
- Added regressions for factRuEval routing, TSV boundaries, multi-ZIP provenance, GitHub path encoding, and hard ablation blocking.
- A real build-environment probe still materialized 0 documents: four selected network sources hit the per-source timeout and RusLawOD reported the missing optional `datasets` dependency. `old → candidate → off` therefore remains intentionally NOT RUN.

## 1.6.0-beta.1 — external held-out freeze-gate research

- Research-only pass: active 1.4 thresholds remain frozen; `scripts/check_prose_ru.py` and `scripts/ablate_signals.py` remain byte-for-byte unchanged.
- Fixed a benchmark-validator correctness defect: readiness now requires **all profiles from the active profile file**, including `technical`; previous 1.5 readiness logic omitted `technical`. Added a regression test where prose/oral/product/official pass but missing technical must still block ablation.
- Added a real technical source plan based on Russian Yandex Cloud Markdown documentation (CC BY 4.0) and expanded oral acquisition with naturally bounded speech corpora instead of arbitrary ASR utterance concatenation.
- Added RuREBus as a separate business-document supplement; it is not treated as a substitute for real product/customer cases.
- Fixed the generic ZIP acquisition adapter so it routes documents according to the registry `profiles/channels` instead of hardcoding `prose/blog`; regression-tested with an oral ZIP fixture.
- Ran source-specific acquisition probes in the build container. LJSearch, factRuEval and RBC failed at DNS resolution; RusLawOD streaming is blocked by missing optional `datasets`; Ruward did not finish before the probe timeout. Zero external documents were accepted.
- Materialized an explicit empty acquisition manifest and generated `materialized/manifest.validated.csv` with the real validator. All five profile gates are 0 documents / 0 words and therefore fail.
- Added `FREEZE_GATE_STATUS.json`, `ABLATION_NOT_RUN.json` and `probes/PROBE_REPORT.json`. The unchanged `old → candidate → off` runner was intentionally **not executed** because its precondition is false.

## 1.5.0-beta.1 — external held-out acquisition

- Linter code and all five active thresholds are unchanged; `check_prose_ru.py` and `ablate_signals.py` are protected by baseline SHA-256 checks.
- Added `benchmark/external-heldout/` with source registry, explicit URLs, LJSearch saved-copy seeds, acquisition status and release policy.
- Added `scripts/materialize_external_heldout.py` adapters for LJSearch saved copies, Zenodo ZIP records, factRuEval GitHub documents, web case indexes, Hugging Face streaming and already-downloaded local trees.
- Materializer now returns a non-zero exit status when acquisition fails or completes only partially, so network/source failures cannot silently look successful.
- Added `scripts/validate_external_heldout.py`: UTF-8/SHA checks, exact/near-copy clustering, independent-document/word freeze counts, channel/source concentration, per-signal sample eligibility and a representative-only `manifest.validated.csv` for the unchanged runner.
- Priority sources: LJSearch saved copies for long blog paragraphs; Zenodo LiveJournal is retained only as a schema-unverified fallback; factRuEval for independent media prose; RBC/Ruward for real product/business cases; RusLawOD for long official/legal; multiple oral sources with explicit prohibition on concatenating arbitrary short utterances into pseudo-documents.
- The build environment could verify web provenance but could not bulk materialize raw external corpora because its container network/DNS is unavailable. Freeze is therefore **not claimed**: `MATERIALIZATION_STATUS.json` records 0 external documents in the release build.
- No copyrighted LiveJournal/media/product full text is redistributed in the release ZIP; manifests, links, hashes and aggregate outputs are the default release artifacts.


## 1.4.0-beta.1 — five-signal ablation

- Added one-at-a-time `old → candidate → off` ablation for `road-sign-density`, `sentence-uniformity`, `long-sentence`, `one-sentence-paragraphs`, and `context-jargon-density`.
- Added preregistered freeze gate: target 50 independent documents and 10,000 words per main profile before activating corpus-derived thresholds; this is a benchmark design target, not a language norm.
- Added `scripts/ablate_signals.py`, `benchmark/ablation/spec.json`, synthetic sensitivity controls, local-probe provenance and regression tests.
- Local natural probe: 5 in-scope coherent documents / 2,161 words; 4 localization catalogs retained only as secondary lexical controls; 1 literary fragment retained only as a domain-routing guard.
- No active threshold changed: current clean probe produced no target alerts in in-scope documents, candidate thresholds did not improve on old thresholds, and the freeze gate was not met.
- Historical 1.3 pilot is used only as supplementary alert-burden evidence, not to reconstruct unavailable per-document quantiles.
- Added explicit negative result: threshold changes are rejected when evidence is insufficient.

## 1.3.0-beta.1 — real-corpus pilot

- Первый одинаковый deterministic checker benchmark для 1.1/1.2: одинаковая нагрузка сигналами; улучшение не приписано 1.2 без данных.
- В pilot-профиле `dash-density` и `colon-density` отключены как пользовательские alerts, признаки сохранены.
- Одиночный `hype` заменён на агрегированный `hype-density` с minimum hits + density.
- `hype` отключён в `technical` и `official` после подтверждённых контекстных ложных срабатываний.
- Добавлены `benchmark/`, registry корпусов, методика и воспроизводимые runner/prepare/fetch scripts.
- Добавлены regression tests для нормативной пунктуации, технического «бесшовный», одиночного «флагманский» и positive-control рекламной риторики.
- Чётко разделены deterministic checker benchmark, GEC benchmark и generative Skill A/B.

## 1.2.0-beta.2

- Completed five research passes covering genre/channel variation, L2 and translated Russian, audience/accessibility, multi-reference/document-level evaluation, and rule-level diagnostics.
- Added condition-aware corpus manifest schema and example.
- Added `false_positive_cases.json`, `grammar_diagnostic_plan.json`, and `METRICS.md`.
- Expanded output evals to 16 scenarios including media, social, child/student accessibility, and high-stakes factual rewriting.
- Added `audit_eval_coverage.py` and expanded coverage dimensions.
- Improved corpus tools: manifest input, arbitrary group-by calibration, short-document filtering, sample-size/word-count reporting.
- Fixed regex escaping in the checker build and validator self-pollution with `__pycache__`.
- Improved Russian sentence segmentation around initials, versions, abbreviations, year abbreviation, ranges and clock/ratio colons.
- Added regression tests for false-positive preservation and corpus tooling.
- Added 2025–2026 rule-level Russian GEC sources and diagnostic policy.

## 1.2.0-beta.1

- Added condition model: operation × origin × factuality × channel × audience.
- Added L2 Russian, translated Russian, accessibility and language-variation references.
- Externalized checker thresholds into profile JSON.
- Added feature-only mode and first corpus feature/calibration scripts.
- Explicitly rejected exact-string evaluation as the primary metric for editing.

## 1.1.0-beta.1

- Added editing-depth workflow, orthotypography and technical writing.
- Fixed rule duplication and quote handling.
- Added trigger and output eval foundations.

## 1.0.x

Initial Russian adaptation and audits.
