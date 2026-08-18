# Research pass 11 — external held-out freeze gate

**Release:** `1.6.0-beta.1`  
**Date:** 2026-08-10  
**Decision:** `BLOCK_ABLATION` — freeze gate is not met; 1.4 thresholds remain frozen.

## 1. Scope

This pass is deliberately research-only for the five remaining signals. It does not alter `scripts/check_prose_ru.py`, `scripts/ablate_signals.py`, or any active threshold in `profiles/editorial-baseline.json`.

The required order remains:

1. Materialize real external documents with natural document boundaries.
2. Validate UTF-8, hashes, exact/near duplicates and independence.
3. Produce `manifest.validated.csv`.
4. Require **≥50 independent documents and ≥10,000 words in each of the five profiles**.
5. Check per-signal eligibility.
6. Only then run the unchanged `old → candidate → off` runner.

## 2. Critical gate bug found and fixed

The 1.5 validator computed `ready_for_unchanged_ablation` over `prose`, `oral`, `product`, and `official` only. `technical` was missing even though the active profile file has five profiles and `spec.json` defines the freeze target per profile. This could have produced a false-positive readiness state.

The validator now derives required profiles from the active profile file. A regression test explicitly proves that a corpus where prose/oral/product/official pass but technical is missing still returns `ready_for_unchanged_ablation=false`. This is a benchmark-validation fix only; linter and ablation runner are unchanged.

## 3. Source research and links

### Prose / blog / media / social

- LJSearch: https://ljsear.ch/ — archive/search over Russian-language LiveJournal 2000–2017.
- FAQ: https://ljsear.ch/faq — states that the archive was received from Yandex and includes posts no longer available in LiveJournal.
- Saved-copy seeds: see `LJSEARCH_SAVED_COPY_SEEDS.csv`; they remain discovery/provenance entries until body retrieval succeeds.
- Zenodo LiveJournal Dataset: https://zenodo.org/records/7139731 — `livejournal.zip`, 202.9 MB; archive schema still unverified for benchmark document boundaries.
- factRuEval-2016: https://github.com/dialogue-evaluation/factRuEval-2016 — source documents preserve paragraph boundaries.
- RIA News Dataset: https://github.com/RossiyaSegodnya/ria_news_dataset — 1,003,869 Russian news documents; useful media supplement under upstream license conditions.
- UD Russian Taiga: https://github.com/UniversalDependencies/UD_Russian-Taiga — social/blog supplement, but paragraph fidelity must be checked before using it for paragraph-rhythm calibration.

### Oral

- Russian National Corpus, Spoken: https://ruscorpora.ru/en/corpus/spoken — reference corpus with natural spoken-text boundaries; offline use has separate license procedure.
- Common Voice Spontaneous Russian: https://mozilladatacollective.com/datasets/cmqi2c2eu0062o5075atr17rs — spontaneous Russian responses; do not concatenate unrelated clips.
- Speech corpus 2012–2022: https://zenodo.org/records/7057103 — naturally bounded speeches/addresses and some Q&A; use only as a supplement because author concentration is high.
- Duma Speeches 1994–2021: https://doi.org/10.48320/FB52DAC2-66E3-47A3-86C5-B2A3DADF41BF — >385,000 transcripts of speeches/oral contributions; promising long-form oral source with many speakers.

### Product / business

- RBC Companies cases: https://companies.rbc.ru/cases/
- Ruward cases: https://ruward.ru/award/
- Sostav business blogs: https://www.sostav.ru/blogs/tags/13043
- RuREBus: https://github.com/dialogue-evaluation/RuREBus — business-domain regional reports and strategic plans; kept in a separate `business_document` channel and **not** treated as a substitute for customer/product cases.

### Technical

- Yandex Cloud docs: https://github.com/yandex-cloud/docs
- Russian tree: https://github.com/yandex-cloud/docs/tree/master/ru
- License: https://github.com/yandex-cloud/docs/blob/master/LICENSE — CC BY 4.0.

This closes a real source-plan gap from 1.5: the technical profile now has a dedicated Russian technical-document source. One source Markdown document must remain one benchmark document after rendering/boilerplate removal.

### Official / legal

- RusLawOD v3: https://github.com/irlcode/RusLawOD/
- Dataset entry: https://huggingface.co/datasets/irlspbru/RusLawOD
- Official legal open data: https://publication.pravo.gov.ru/OpenData

## 4. Actual materialization result in this build

No source catalogue entry is promoted to `fetched` merely because research tools can inspect its web page. The local benchmark filesystem is the authority for materialization.

| Adapter/source | Actual probe result | Accepted docs |
|---|---|---:|
| `ljsearch_saved_copies` | fetch failed: https://ljsear.ch/savedcopy?post=402698938: <urlopen error [Errno -3] Temporary failure in name resolution> | 0 |
| `factrueval_2016` | fetch failed: https://api.github.com/repos/dialogue-evaluation/factRuEval-2016/git/trees/master?recursive=1: <urlopen error [Errno -3] Temporary failure in name resolution> | 0 |
| `rbc_company_cases` | fetch failed: https://companies.rbc.ru/cases/: <urlopen error [Errno -3] Temporary failure in name resolution> | 0 |
| `ruslawod_v3` | optional dependency 'datasets' is not installed | 0 |
| `ruward_cases` | outer timeout before adapter produced a report; no documents accepted or written | 0 |

Therefore this release contains **0 external materialized documents and 0 external words**. This is a runtime result, not a claim that the sources themselves are inaccessible in a normal networked environment.

## 5. `manifest.validated.csv` and freeze matrix

The real validator was run on the actual local acquisition manifest. Because no external body was written locally, the validated manifest contains its header and zero data rows. It is intentionally retained as evidence of the failed precondition, not represented as a corpus.

| Profile | Independent docs | Words | Gate |
|---|---:|---:|---|
| `official` | 0 / 50 | 0 / 10,000 | FAIL |
| `oral` | 0 / 50 | 0 / 10,000 | FAIL |
| `product` | 0 / 50 | 0 / 10,000 | FAIL |
| `prose` | 0 / 50 | 0 / 10,000 | FAIL |
| `technical` | 0 / 50 | 0 / 10,000 | FAIL |

**Overall:** `ready_for_unchanged_ablation = false`.

## 6. Per-signal structural eligibility

With no materialized documents, actual eligible counts are zero. Separately, profile configuration itself makes two rhythm signals ineligible for `technical` and `official` because those profiles have `rhythm_checks=false`. This must not be confused with a data shortage.

| Signal | prose | oral | product | technical | official |
|---|---|---|---|---|---|
| road-sign-density | potentially eligible | potentially eligible | potentially eligible | potentially eligible | potentially eligible |
| sentence-uniformity | potentially eligible | potentially eligible | potentially eligible | disabled by profile | disabled by profile |
| long-sentence | potentially eligible | potentially eligible | potentially eligible | potentially eligible | potentially eligible |
| one-sentence-paragraphs | potentially eligible | potentially eligible | potentially eligible | disabled by profile | disabled by profile |
| context-jargon-density | potentially eligible | potentially eligible | potentially eligible | potentially eligible | potentially eligible |

For `sentence-uniformity`, an otherwise eligible document must also meet the profile minimum sentence count. For `one-sentence-paragraphs`, it must meet the minimum paragraph count. Lexical-density signals still require their configured hit minima before firing.

## 7. Ablation decision

The unchanged `old → candidate → off` runner was **not run**. Running it now would violate the preregistered gate and would turn a known absence of held-out evidence into pseudo-calibration. `ABLATION_NOT_RUN.json` records this machine-readably.

No threshold was changed; active 1.4 values remain frozen. A byte-level comparison against the 1.5 package confirms that `profiles/editorial-baseline.json`, `scripts/check_prose_ru.py`, and `scripts/ablate_signals.py` are all identical. The profile SHA-256 is `437199c10715bef7a2a74e9d172f5f40bef95a337e488a889a2819b2c6b96839`; linter and runner hashes are recorded in `RELEASE_INTEGRITY.json`.

## 8. What remains before the next legitimate ablation

1. Execute acquisition in a runtime that can write full external source bodies into the working corpus directory.
2. Prioritize paragraph-rich `prose/blog/media` first, especially LJSearch saved copies or another source retaining real paragraph boundaries.
3. Build oral from naturally bounded speeches/dialogues/monologues, not glued ASR clips.
4. Keep real product/customer cases separate from generic business reports and inspect channel-specific distributions.
5. Render Russian technical docs one source document → one text document.
6. Stream/sample full legal acts for official.
7. Run validator until **all five** profile gates pass and inspect author/source concentration plus exact/near-copy clusters.
8. Confirm non-zero eligible samples for each signal in every profile where the signal is structurally active.
9. Only then run the byte-identical `ablate_signals.py`.

