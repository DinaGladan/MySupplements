"""Evaluation script for MySupplements.

Three modes:

  python -m evaluation.evaluate --mode engine
      Deterministic evaluation of the RULE-BASED recommendation engine using the
      gold profiles/goals from the dataset. No PostgreSQL, no Ollama required.
      Reports recommendation recall@5, hit-rate and threshold behaviour.

  python -m evaluation.evaluate --mode e2e --url http://127.0.0.1:8000
      End-to-end evaluation through the running API. Sends raw text to /recommend,
      measures how well the LLM parsed the profile/goals (field accuracy + goal
      F1) and per-request latency. Requires the backend, PostgreSQL and Ollama.

  python -m evaluation.evaluate --mode load --requests 30 --concurrency 5
      Simple load test: fires N /recommend requests with a given concurrency and
      reports latency percentiles and throughput. Requires the backend running.

Run from the project root (the folder that contains app/ and evaluation/).
"""
import argparse
import statistics
import time
from concurrent.futures import ThreadPoolExecutor

# ---- Build the in-memory knowledge base from the seed (no DB needed) --------
from app.db.seed import SUPPLEMENTS_DATA
from app.models.supplement import Supplement
from app.schemas.goals_schema import ParsedGoals
from app.schemas.profile_schema import ParsedProfile
from app.services import recommendation_engine
from evaluation.dataset import SCENARIOS

_SUPPLEMENTS = [Supplement(**data) for data in SUPPLEMENTS_DATA]


def _engine_recommendations(profile: ParsedProfile, goals: ParsedGoals):
    """Run the REAL engine against the in-memory supplements (patch the repo)."""
    recommendation_engine.get_all_supplements = lambda db=None: _SUPPLEMENTS
    result = recommendation_engine.generate_recommendations(None, profile, goals)
    return [rec.supplement_name for rec in result.recommendations]


# ============================================================ engine mode ====
def run_engine_mode():
    print("=" * 70)
    print("ENGINE EVALUATION  (rule-based recommendation quality, no LLM)")
    print("=" * 70)

    recalls = []
    hits = 0
    forbidden_violations = 0
    scored = 0

    for sc in SCENARIOS:
        profile = ParsedProfile(**sc["gold_profile"])
        goals = ParsedGoals(goals=sc["gold_goals"])
        got = _engine_recommendations(profile, goals)
        got_set = set(got)

        expected = sc["expected_supplements"]
        forbidden = sc.get("forbidden_supplements", set())

        print(f"\n[{sc['id']}] {sc['description']}")
        print(f"    goals    : {sc['gold_goals']}")
        print(f"    expected : {sorted(expected) or '(none)'}")
        print(f"    got top5 : {got or '(none)'}")

        if sc.get("expect_empty"):
            ok = len(got) == 0
            print(f"    -> expect no results: {'PASS' if ok else 'FAIL'}")
            if ok:
                hits += 1
            continue

        matched = expected & got_set
        recall = len(matched) / len(expected) if expected else 1.0
        recalls.append(recall)
        scored += 1
        if matched:
            hits += 1

        bad = forbidden & got_set
        if bad:
            forbidden_violations += 1
            print(f"    !! FORBIDDEN present: {sorted(bad)}")

        print(f"    -> recall@5 = {recall:.2f}  (matched {sorted(matched) or '(none)'})")

    print("\n" + "-" * 70)
    print("SUMMARY")
    print(f"  scenarios                : {len(SCENARIOS)}")
    if recalls:
        print(f"  mean recall@5            : {statistics.mean(recalls):.2%}")
    print(f"  hit-rate (>=1 expected)  : {hits}/{len(SCENARIOS)} = {hits / len(SCENARIOS):.2%}")
    print(f"  forbidden-rule violations: {forbidden_violations}")
    print("-" * 70)


# =============================================================== e2e mode =====
def _api_recommend(url, profile_text, goals_text, timeout):
    import requests

    start = time.perf_counter()
    response = requests.post(
        f"{url}/recommend",
        json={"profile_text": profile_text, "goals_text": goals_text},
        timeout=timeout,
    )
    elapsed = time.perf_counter() - start
    response.raise_for_status()
    return response.json(), elapsed


def _profile_field_accuracy(gold: dict, parsed: dict):
    """Fraction of gold fields the parser got right (only fields we labelled)."""
    if not gold:
        return None
    correct = 0
    for key, expected in gold.items():
        actual = parsed.get(key)
        # Normalise booleans / strings for comparison.
        if isinstance(expected, bool):
            correct += int(actual is expected)
        else:
            correct += int(str(actual) == str(expected))
    return correct / len(gold)


def run_e2e_mode(url, timeout):
    print("=" * 70)
    print(f"END-TO-END EVALUATION  (via {url}/recommend - needs API + Ollama)")
    print("=" * 70)

    field_accuracies = []
    goal_f1s = []
    rec_recalls = []
    latencies = []

    for sc in SCENARIOS:
        try:
            data, elapsed = _api_recommend(
                url, sc["profile_text"], sc["goals_text"], timeout
            )
        except Exception as exc:  # noqa: BLE001 - report and continue
            print(f"\n[{sc['id']}] REQUEST FAILED: {exc}")
            continue

        latencies.append(elapsed)

        # Parsing accuracy
        acc = _profile_field_accuracy(sc["gold_profile"], data.get("profile", {}))
        if acc is not None:
            field_accuracies.append(acc)

        parsed_goals = set(data.get("goals", {}).get("goals", []))
        gold_goals = set(sc["gold_goals"])
        if gold_goals or parsed_goals:
            tp = len(parsed_goals & gold_goals)
            precision = tp / len(parsed_goals) if parsed_goals else 0.0
            recall = tp / len(gold_goals) if gold_goals else 0.0
            f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
            goal_f1s.append(f1)

        got = {r["supplement_name"] for r in data.get("recommendations", [])}
        expected = sc["expected_supplements"]
        if expected:
            rec_recalls.append(len(expected & got) / len(expected))

        print(
            f"\n[{sc['id']}] {elapsed:5.1f}s  "
            f"field_acc={acc if acc is None else f'{acc:.0%}'}  "
            f"goals={sorted(parsed_goals)}"
        )
        print(f"    recommended: {sorted(got) or '(none)'}")

    print("\n" + "-" * 70)
    print("SUMMARY")
    if field_accuracies:
        print(f"  profile field accuracy : {statistics.mean(field_accuracies):.2%}")
    if goal_f1s:
        print(f"  goal extraction F1     : {statistics.mean(goal_f1s):.2%}")
    if rec_recalls:
        print(f"  recommendation recall  : {statistics.mean(rec_recalls):.2%}")
    if latencies:
        _print_latency(latencies)
    print("-" * 70)


# ============================================================== load mode =====
def run_load_mode(url, total_requests, concurrency, timeout):
    print("=" * 70)
    print(f"LOAD TEST  ({total_requests} requests, concurrency {concurrency})")
    print("=" * 70)

    sc = SCENARIOS[0]  # one representative request repeated

    def one_call(_):
        try:
            _, elapsed = _api_recommend(url, sc["profile_text"], sc["goals_text"], timeout)
            return elapsed, None
        except Exception as exc:  # noqa: BLE001
            return None, str(exc)

    wall_start = time.perf_counter()
    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        results = list(pool.map(one_call, range(total_requests)))
    wall = time.perf_counter() - wall_start

    latencies = [r for r, err in results if err is None]
    failures = [err for _, err in results if err is not None]

    print(f"\n  completed   : {len(latencies)}/{total_requests}")
    print(f"  failures    : {len(failures)}")
    if failures:
        print(f"  first error : {failures[0]}")
    print(f"  wall time   : {wall:.1f}s")
    if latencies:
        print(f"  throughput  : {len(latencies) / wall:.2f} req/s")
        _print_latency(latencies)
    print("-" * 70)


def _print_latency(latencies):
    ordered = sorted(latencies)
    def pct(p):
        idx = min(len(ordered) - 1, int(round((p / 100) * (len(ordered) - 1))))
        return ordered[idx]
    print(f"  latency p50 : {pct(50):.1f}s")
    print(f"  latency p95 : {pct(95):.1f}s")
    print(f"  latency max : {ordered[-1]:.1f}s")


# ================================================================== main ======
def main():
    parser = argparse.ArgumentParser(description="Evaluate MySupplements.")
    parser.add_argument("--mode", choices=["engine", "e2e", "load"], default="engine")
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    parser.add_argument("--timeout", type=float, default=300.0)
    parser.add_argument("--requests", type=int, default=20)
    parser.add_argument("--concurrency", type=int, default=5)
    args = parser.parse_args()

    if args.mode == "engine":
        run_engine_mode()
    elif args.mode == "e2e":
        run_e2e_mode(args.url, args.timeout)
    elif args.mode == "load":
        run_load_mode(args.url, args.requests, args.concurrency, args.timeout)


if __name__ == "__main__":
    main()
