# Pass 12 — network materialization gate

**Release candidate:** `1.6.1-beta.1`  
**Date:** 2026-08-10  
**Scope:** acquisition/validation infrastructure only. No linter rule, active threshold, profile value or ablation decision rule changed.

## Goal

Materialize a genuinely external held-out corpus and repeat `old → candidate → off` only after the existing freeze gate is true for every profile:

- `prose`: ≥50 independent documents and ≥10,000 words;
- `oral`: ≥50 / ≥10,000;
- `product`: ≥50 / ≥10,000;
- `technical`: ≥50 / ≥10,000;
- `official`: ≥50 / ≥10,000.

The validator must first create a representative-only, exact/near-copy-deduplicated `manifest.validated.csv`. The unchanged ablation runner may consume only that manifest.

## What this pass changed

### 1. Network gate orchestrator

Added `scripts/run_external_heldout_gate.py`. It:

1. verifies frozen SHA-256 inputs;
2. runs each external source separately into the same resumable acquisition manifest;
3. runs `validate_external_heldout.py`;
4. records profile freeze and per-signal eligibility;
5. writes `ABLATION_NOT_RUN.json` and exits 3 when any profile gate fails;
6. invokes the existing `ablate_signals.py` only when `ready_for_unchanged_ablation=true`;
7. verifies frozen hashes again after acquisition/ablation.

A hard per-source process timeout prevents a dead endpoint from blocking all other profiles. It changes only orchestration, not source selection within an adapter or any editorial threshold.

### 2. Acquisition correctness fixes

- `factRuEval`: fixed undefined `profile` state; profile/channel are read from registry.
- GitHub tree: raw URL components now use percent encoding (`%20`) rather than form encoding (`+`).
- ZIP: one source can contain multiple upstream ZIP parts; archive part is provenance, not a new source.
- TSV/CSV: one source row remains one natural document; rows are never concatenated to satisfy freeze.
- Markdown/XML: acquisition normalization removes non-rendered wrappers/code but preserves one source file = one held-out document.
- Empty validated manifests preserve the full input schema.

### 3. Automated source routes

- `technical`: Yandex Cloud `ru/**/*.md` through GitHub tree acquisition.
- `oral`: RUB Corpus TSV plus direct `levshina/Putin_Corpus` XML GitHub route; the Putin source has a deliberately smaller target because it must not dominate oral evidence.
- `product`: RBC/Ruward remain genuine case sources; RuREBus is automated only as a separate `business_document` supplement.
- `official`: RusLawOD streaming remains the main bulk legal source.
- `prose`: factRuEval/LJSearch/LiveJournal remain the main routes.

## Build-environment network result

The build container still cannot transfer public web/GitHub corpus bytes into its local filesystem through ordinary outbound networking. A real five-profile probe was therefore run with a two-second process cap per selected source:

- `factrueval_2016`: process timeout, 0 accepted;
- `rub_corpus_russia`: process timeout, 0 accepted;
- `ruward_cases`: process timeout, 0 accepted;
- `yandex_cloud_docs_ru`: process timeout, 0 accepted;
- `ruslawod_v3`: clean materializer failure because optional Python package `datasets` is absent, 0 accepted.

Result: `manifest.validated.csv` has 0 data rows; every profile remains `0 / 50`, `0 / 10,000`; ablation output is absent and `ABLATION_NOT_RUN.json` is present.

This is an environment/transport result, not corpus evidence. URLs, connector previews, source metadata and timeouts do not count as materialized documents.

## Frozen integrity

The following hashes remain unchanged:

- `scripts/check_prose_ru.py`: `00648ff1df947042eedb4372ad4e4175f88af795f3ae883d98623d73b16b8a57`
- `scripts/ablate_signals.py`: `f6b6eb357636fdfafcca3b78661cedac6c9b01b70709c267754026ca2a36454a`
- `profiles/editorial-baseline.json`: `437199c10715bef7a2a74e9d172f5f40bef95a337e488a889a2819b2c6b96839`

## Reproduction on a normal networked machine

```bash
python3 -m pip install datasets
python3 scripts/run_external_heldout_gate.py \
  --output-dir ../heldout-work
```

Do not copy third-party raw texts into a release automatically. The release should contain provenance, manifests, hashes, validator reports and aggregates unless redistribution rights are separately verified.

## Decision

No threshold may move in this pass. The next valid decision point is the first run where the validator reports the full five-profile freeze gate as true. Only then may the unchanged corpus-wide `old → candidate → off` result be interpreted separately for the five preregistered signals.
