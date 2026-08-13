#!/usr/bin/env python3
"""
evaluate_performance.py — IP4 (dio B): latencija i propusnost.

Mjeri latenciju po zahtjevu i izvještava percentile (p50/p95/p99), s isključenim
prvim (zagrijavajućim) pozivom. Dva načina:
  - engine (zadano): mjeri SAMO deterministički mehanizam bodovanja u procesu
    (bez LLM-a). Radi offline i vrlo je brz — koristan za odvajanje troška jezgre
    od troška LLM-a.
  - e2e (--api-url URL): mjeri stvarni /recommend na pokrenutom sustavu (uključuje
    parsiranje i, po izboru, objašnjenje). Ovo su brojevi za tablicu latencije.

Okruženje mjerenja (hardver, kvantizacija) čita se iz results/perf_env.json ako
postoji, i ispisuje uz rezultate radi ponovljivosti. Bez tih podataka brojevi
latencije NISU ponovljivi.

Pokretanje (engine):  python evaluate_performance.py --repeats 50
Pokretanje (e2e):     python evaluate_performance.py --api-url http://localhost:8000 --repeats 20
"""
from __future__ import annotations
import argparse, csv, json, os, sys, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import metrics as M
import engine_adapter as E

RESULTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")

ENV_TEMPLATE = {
    "cpu": "npr. AMD Ryzen 7 5800H, 8C/16T — POPUNITI",
    "ram_gb": "POPUNITI",
    "gpu": "npr. nema / NVIDIA RTX 3060 — POPUNITI",
    "os": "POPUNITI",
    "ollama_version": "POPUNITI",
    "model": "npr. qwen2.5:3b — POPUNITI",
    "quantization": "npr. Q4_K_M — POPUNITI"
}


def load_env():
    path = os.path.join(RESULTS_DIR, "perf_env.json")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    os.makedirs(RESULTS_DIR, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(ENV_TEMPLATE, f, ensure_ascii=False, indent=2)
    return ENV_TEMPLATE


def time_engine(supplements, scenarios, cfg, repeats):
    lat = []
    # zagrijavanje
    s0 = scenarios[0]
    E.recommend(supplements, s0.get("expected_profile") or {}, s0.get("expected_goals"), cfg)
    for _ in range(repeats):
        for scn in scenarios:
            t = time.perf_counter()
            E.recommend(supplements, scn.get("expected_profile") or {},
                        scn.get("expected_goals"), cfg)
            lat.append((time.perf_counter() - t) * 1000.0)  # ms
    return lat, "ms"


def time_e2e(base_url, scenarios, repeats):
    import requests
    base = base_url.rstrip("/")
    lat = []
    # zagrijavanje (model se učitava pri prvom pozivu)
    requests.post(f"{base}/recommend", json={
        "profile_text": scenarios[0].get("profile_text", ""),
        "goals_text": scenarios[0].get("goals_text", "")}, timeout=600)
    for _ in range(repeats):
        for scn in scenarios:
            t = time.perf_counter()
            requests.post(f"{base}/recommend", json={
                "profile_text": scn.get("profile_text", ""),
                "goals_text": scn.get("goals_text", "")}, timeout=600)
            lat.append(time.perf_counter() - t)  # s
    return lat, "s"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--supplements", default=None)
    ap.add_argument("--scenarios", default=None)
    ap.add_argument("--api-url", default=None)
    ap.add_argument("--repeats", type=int, default=50)
    args = ap.parse_args()

    supplements = E.load_supplements(args.supplements)
    scenarios = E.load_scenarios(args.scenarios)
    env = load_env()

    if args.api_url:
        lat, unit = time_e2e(args.api_url, scenarios, args.repeats)
        mode = "e2e (/recommend)"
    else:
        lat, unit = time_engine(supplements, scenarios, E.ScoringConfig(), args.repeats)
        mode = "engine (samo bodovanje, bez LLM-a)"

    p50, p95, p99 = M.percentile(lat, 50), M.percentile(lat, 95), M.percentile(lat, 99)

    print("\n=== IP4-B: PERFORMANSE ===")
    print(f"Način: {mode}   |   uzoraka: {len(lat)}   |   jedinica: {unit}")
    print("Okruženje mjerenja (results/perf_env.json):")
    for kk, vv in env.items():
        print(f"  {kk:<16}: {vv}")
    print(f"\n  p50 = {p50:.3f} {unit}   p95 = {p95:.3f} {unit}   p99 = {p99:.3f} {unit}"
          f"   (mean = {M.mean(lat):.3f} {unit})")
    if not args.api_url:
        print("\nNAPOMENA: engine način NE uključuje latenciju LLM-a. Brojevi za rad "
              "(npr. p50 e2e) dobiju se s --api-url na pokrenutom sustavu; tek tada su "
              "usporedivi s vrijednostima ~22 s / ~12 s iz poglavlja 9/10.")

    os.makedirs(RESULTS_DIR, exist_ok=True)
    out = os.path.join(RESULTS_DIR, "performance.csv")
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["nacin", "jedinica", "n", "p50", "p95", "p99", "mean"])
        w.writerow([mode, unit, len(lat), p50, p95, p99, M.mean(lat)])
    print(f"\nCSV zapisan: {out}")


if __name__ == "__main__":
    main()
