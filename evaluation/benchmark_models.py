"""Compare LLM models on the parsing task (the real latency bottleneck).

For each model it runs the profile + goals parsing on the evaluation scenarios,
calling Ollama directly (no backend needed, only Ollama running), and reports:

  - parameter size (why one model is faster than another)
  - average / median latency per request (2 parse calls)
  - profile field accuracy vs the gold labels
  - goal extraction F1

Usage (from project root, Ollama running):

  python -m evaluation.benchmark_models
  python -m evaluation.benchmark_models --models llama3 llama3.2:3b llama3.2:1b
  python -m evaluation.benchmark_models --scenarios 9

Only the LLM (parsing) is compared, because the rule-based scoring engine is
identical for every model and takes microseconds.
"""
import argparse
import statistics
import time

import requests

from app.config import settings
from app.services import goal_parser_service, profile_parser_service
from app.services.llm_client import llm_client
from evaluation.dataset import SCENARIOS
from evaluation.evaluate import _profile_field_accuracy

DEFAULT_MODELS = ["llama3", "llama3.2:3b", "llama3.2:1b", "qwen2.5:3b"]


def _available_models():
    """Return {name: parameter_size} for models Ollama currently has."""
    try:
        resp = requests.get(f"{settings.llm_base_url}/api/tags", timeout=5)
        resp.raise_for_status()
    except requests.RequestException as exc:
        raise SystemExit(f"Cannot reach Ollama at {settings.llm_base_url}: {exc}")

    info = {}
    for model in resp.json().get("models", []):
        name = model["name"]
        params = model.get("details", {}).get("parameter_size", "?")
        info[name] = params
        # Also index without the ":latest" suffix for convenience.
        if name.endswith(":latest"):
            info[name[: -len(":latest")]] = params
    return info


def _goal_f1(parsed_goals, gold_goals):
    parsed, gold = set(parsed_goals), set(gold_goals)
    if not parsed and not gold:
        return 1.0
    tp = len(parsed & gold)
    precision = tp / len(parsed) if parsed else 0.0
    recall = tp / len(gold) if gold else 0.0
    return 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0


def benchmark(model, scenarios):
    original = llm_client.model
    llm_client.model = model
    latencies, field_accs, goal_f1s = [], [], []

    try:
        # Warm-up call (loads the model into memory) so it isn't counted.
        profile_parser_service.parse_profile("warm up")

        for sc in scenarios:
            start = time.perf_counter()
            profile = profile_parser_service.parse_profile(sc["profile_text"])
            goals = goal_parser_service.parse_goals(sc["goals_text"])
            latencies.append(time.perf_counter() - start)

            acc = _profile_field_accuracy(
                sc["gold_profile"], profile.model_dump(mode="json")
            )
            if acc is not None:
                field_accs.append(acc)
            goal_f1s.append(_goal_f1([g.value for g in goals.goals], sc["gold_goals"]))
    finally:
        llm_client.model = original

    return {
        "avg_latency": statistics.mean(latencies),
        "median_latency": statistics.median(latencies),
        "field_acc": statistics.mean(field_accs) if field_accs else None,
        "goal_f1": statistics.mean(goal_f1s) if goal_f1s else None,
    }


def main():
    parser = argparse.ArgumentParser(description="Benchmark LLM models on parsing.")
    parser.add_argument("--models", nargs="+", default=DEFAULT_MODELS)
    parser.add_argument("--scenarios", type=int, default=5, help="how many scenarios")
    args = parser.parse_args()

    scenarios = SCENARIOS[: args.scenarios]
    available = _available_models()

    print("=" * 78)
    print(f"MODEL BENCHMARK  (parsing task, {len(scenarios)} scenarios, 2 LLM calls each)")
    print("=" * 78)

    rows = []
    for model in args.models:
        if model not in available:
            print(f"\n[skip] {model} is not pulled (run: ollama pull {model})")
            continue
        print(f"\nBenchmarking {model} ({available[model]}) ...", flush=True)
        result = benchmark(model, scenarios)
        rows.append((model, available[model], result))
        print(
            f"   avg {result['avg_latency']:.1f}s/req  "
            f"median {result['median_latency']:.1f}s  "
            f"field_acc {_pct(result['field_acc'])}  "
            f"goal_F1 {_pct(result['goal_f1'])}"
        )

    # ---- Comparison table ----
    print("\n" + "=" * 78)
    print(f"{'MODEL':<16}{'PARAMS':<9}{'AVG/req':<10}{'MEDIAN':<10}{'FIELD ACC':<12}{'GOAL F1':<9}")
    print("-" * 78)
    for model, params, r in rows:
        print(
            f"{model:<16}{params:<9}{r['avg_latency']:<10.1f}"
            f"{r['median_latency']:<10.1f}{_pct(r['field_acc']):<12}{_pct(r['goal_f1']):<9}"
        )
    print("=" * 78)
    if rows:
        fastest = min(rows, key=lambda x: x[2]["avg_latency"])
        print(
            f"Fastest: {fastest[0]} ({fastest[1]} params, "
            f"{fastest[2]['avg_latency']:.1f}s/req). Fewer parameters = less compute "
            f"per token = faster inference on CPU."
        )


def _pct(value):
    return "-" if value is None else f"{value:.0%}"


if __name__ == "__main__":
    main()
