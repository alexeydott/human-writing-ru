# Benchmark

Эта папка отделяет **измерение** от правил Skill.

- `corpora.json` — реестр источников; сырые сторонние корпуса в пакет не входят.
- `METHODOLOGY.md` — правила сравнения версий.
- `PILOT_RESULTS.json` — результаты малого реального pilot benchmark 1.1/1.2/1.3 candidate.

Для воспроизведения на собственных законно полученных данных:

```bash
python3 scripts/prepare_benchmark.py --input-dir ./corpora --output-dir ./prepared
python3 scripts/benchmark_checkers.py --manifest ./prepared/manifest.csv \
  --version current=. --output ./prepared/results.json
```

Для сравнения нескольких распакованных версий:

```bash
python3 scripts/benchmark_checkers.py --manifest ./prepared/manifest.csv \
  --version v11=/path/human-writing-ru-1.1 \
  --version v12=/path/human-writing-ru-1.2 \
  --version v13=. \
  --output ./prepared/results.json
```


## Ablation 1.4

`ablation/` содержит следующий слой benchmark: пять оставшихся density/rhythm сигналов сравниваются по одному как `old → candidate → off`. Small local probe не достиг corpus freeze gate, поэтому активные пороги сохранены.
