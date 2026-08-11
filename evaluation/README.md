# Evaluation

Scripts for evaluating the MySupplements system. Run everything from the project
root (the folder containing `app/` and `evaluation/`).

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
