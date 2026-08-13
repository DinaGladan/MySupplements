# MySupplements

An intelligent backend system for **personalized dietary-supplement recommendations**,
based on a user's free-text profile and goals.

## What the system does

The user sends two free-text inputs (a profile description and a goals description).
The system then:

1. **Parses** the profile text into a structured JSON profile (LLM).
2. **Parses** the goals text into a structured list of goals (LLM).
3. **Scores** every supplement in the database against the profile + goals using a
   deterministic, **rule-based** engine.
4. **Filters** out supplements below a minimum score and **ranks** the rest.
5. **Generates** a natural-language explanation of the recommendations (LLM).
6. Returns the parsed profile, parsed goals, ranked recommendations and the explanation.

### Important design rule

The **LLM never decides which supplements to recommend.** It is used only for:

- parsing the user profile from free text into structured JSON,
- parsing the user goals from free text into structured JSON,
- generating the final natural-language explanation from the structured results.

The actual recommendation logic is **rule-based and scoring-based**, implemented in
`app/services/scoring_service.py` and `app/services/recommendation_engine.py`.

## Technologies used

- **Python 3.13**
- **FastAPI** + **Uvicorn** – web framework / ASGI server
- **PostgreSQL** – supplement storage
- **SQLAlchemy** – ORM / database models
- **Pydantic** / **pydantic-settings** – schemas, validation, config
- **Ollama** (local LLM, e.g. `llama3`) – text parsing and explanation generation
- **requests** – HTTP client used to call Ollama

## Scoring model

Each supplement stores its own scoring data as JSON:

- `goal_tags` – goals it supports
- `state_scores` – points for profile states (e.g. `"sleep_quality:poor": 3`)
- `lifestyle_scores` – points for lifestyle (e.g. `"activity_level:high": 2`)
- `diet_scores` – points for diet (e.g. `"diet_type:vegan": 4`)
- `deficiency_scores` – deficiency-risk points (e.g. `"sun_exposure:low": 3`)
- `penalties` – `{ "field:value": { "penalty": N, "hard": true, "warning": "..." } }`

The engine builds a set of `"field:value"` tokens from the parsed profile and looks
them up in these dictionaries.

### Stage 1 — safety

A penalty rule marked `"hard": true` is a **contraindication**, not a score
reduction. When `SAFETY_MODE=veto` (the default) the supplement is removed from
the candidate set before ranking and can never be shown, no matter how many
positive matches it collected. Rules without the flag stay soft penalties.

Hard rules currently cover animal-derived products against vegan and vegetarian
diets, four allergens (`fish`, `shellfish`, `milk`, `mushroom`), and supplements
without sufficient safety data in pregnancy or breastfeeding.

Setting `SAFETY_MODE=soft` restores the earlier behaviour, where a contraindication
was only subtracted from the total. It is kept so the two policies can be compared.

### Stage 2 — scoring

```
total_score = goal_match
            + state_match
            + lifestyle_match
            + diet_match
            + deficiency_risk_proxy
            - penalty_risk
```

`goal_match` = 2 points per matched goal. Supplements scoring below
`MIN_DISPLAY_SCORE` (default 4) are not shown. Strength labels: `weak` (<5),
`good` (5–6), `very_relevant` (7+). Ties are broken by supplement name so that
the same profile always produces the same ordering.

Weights, category scales and the safety mode are grouped in
`app/services/scoring_config.py`. Passing no config reproduces production
behaviour; the evaluation scripts vary it to run ablation and sensitivity analyses.

## Tests

```bash
pytest            # 81 hermetic tests, no Ollama needed
pytest -m llm     # 12 parser-robustness tests, needs Ollama running
```

## Evaluation

```bash
python evaluation/export_supplements.py     # database -> evaluation/data/supplements.json
cd evaluation && python run_all.py          # ranking, ablation, sensitivity, safety, NLU, performance
```

`run_all.py` writes CSV reports to `evaluation/results/`. The scripts evaluate the
real engine from `app/` through `evaluation/real_engine.py`; setting
`EVAL_ENGINE=reference` switches to the bundled reference implementation, which is
useful only for checking that the two agree. On Windows set `PYTHONIOENCODING=utf-8`
first, otherwise the console cannot print the Croatian output.

Re-run `export_supplements.py` after every change to `app/db/seed.py` — the scripts
read the exported JSON, not the database.
