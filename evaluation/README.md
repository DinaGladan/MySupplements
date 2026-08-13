# Evaluation

Two suites live here.

## 1. Thesis evaluation suite

Produces the numbers for the revised chapter 8. Each script writes a table to the
console and a CSV to `results/`.

```bash
python evaluation/export_supplements.py     # database -> data/supplements.json
cd evaluation
PYTHONIOENCODING=utf-8 python run_all.py    # everything offline, in order
```

On Windows the encoding variable is required: the scripts print Croatian text and
the default console codepage cannot encode it.

| Script | Section | Produces |
| --- | --- | --- |
| `evaluate_ranking.py` | 8.3, 8.4, 8.10 | precision/recall/nDCG@k, MRR, Wilson CI, Wilcoxon vs baselines |
| `evaluate_ablation.py` | 8.5 | Δ per removed category |
| `evaluate_sensitivity.py` | 8.6 | overlap@k, Kendall τ under weight perturbation |
| `evaluate_safety.py` | 8.7 | contraindication violation rate, soft penalties vs hard veto |
| `evaluate_nlu.py` | 8.8 | schema validity, per-field accuracy, negation subset, goal F1 |
| `evaluate_performance.py` | 8.9 | p50/p95/p99 latency plus the measurement environment |
| `metrics.py` | 8.2, 8.3 | shared metrics and statistics, including Cohen's and Fleiss' κ |

Live modes need Ollama and the API running:

```bash
python evaluate_nlu.py --api-url http://localhost:8000 --repeats 3
python evaluate_performance.py --api-url http://localhost:8000 --repeats 20
```

### Which engine is measured

`engine_adapter.rank_full` calls the **real** engine from `app/` through
`real_engine.py`, so the evaluation reports the system that actually serves
`/recommend`. The bundled reference implementation stays available as
`rank_reference`; `EVAL_ENGINE=reference` switches to it, which is only useful for
checking that the two agree. They currently agree exactly, both reproducing the
7 / 7 / 6 / 6 / 6 totals of table 10.1.

### Data

`data/*.sample.json` are templates with five examples so the scripts run out of the
box. **Results on them are not usable in the thesis.** `load_supplements` and
`load_scenarios` prefer `supplements.json` and `scenarios.json` when those exist,
so exporting the database and writing the real scenarios is enough to switch over.

Re-run `export_supplements.py` after every change to `app/db/seed.py` — the scripts
read the exported JSON, not the database.

## 2. Older in-house suite

Predates the suite above and is largely superseded by it. `benchmark_models.py` is
not, and is still what compares LLM models for chapter 9.

Run everything from the project root (the folder containing `app/` and
`evaluation/`).

## Dataset

`dataset.py` holds labeled scenarios. Each one has raw input text, the *gold*
(expected) parsed profile and goals, and the supplements that should appear in
the results. Some scenarios also declare `forbidden_supplements` (must NOT be
recommended, e.g. collagen for a vegan) or `expect_empty` (threshold behaviour).

## Modes

### 1. Engine mode (no PostgreSQL, no Ollama)
Deterministic evaluation of the rule-based recommendation engine. Uses the gold
profiles/goals directly, so it measures only the scoring logic — not the LLM.

```bash
python -m evaluation.evaluate --mode engine
```

Reports **recall@5** (how many expected supplements appear in the top 5),
**hit-rate**, and **forbidden-rule violations**.

### 2. End-to-end mode (needs API + PostgreSQL + Ollama)
Sends the raw text through the real `/recommend` endpoint and measures how well
the **LLM parsed** each input, plus latency.

```bash
uvicorn app.main:app --reload          # in another terminal first
python -m evaluation.evaluate --mode e2e
```

Reports **profile field accuracy**, **goal extraction F1**, recommendation
recall, and latency percentiles. This is the mode to run when comparing LLM
models (e.g. llama3 vs a smaller model) — change `LLM_MODEL` in `.env`, restart
the API, and re-run.

### 3. Load mode (needs API running)
Fires many `/recommend` requests concurrently to see how the system behaves
under load.

```bash
python -m evaluation.evaluate --mode load --requests 30 --concurrency 5
```

Reports completed/failed counts, throughput (req/s) and latency percentiles.
The bottleneck under load is the LLM (Ollama), not the scoring engine.
