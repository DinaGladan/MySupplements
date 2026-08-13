#!/usr/bin/env python3
"""
evaluate_nlu.py — IP4 (dio A): točnost i robusnost obrade prirodnog jezika.

Razlikuje dvije razine:
  - točnost sheme  — je li izlaz valjan JSON s dopuštenim vrijednostima
  - semantička točnost — poklapa li se izvučena vrijednost sa značenjem teksta
    (pogreška unutar dopuštenog rječnika, npr. 'spavam dobro' -> sleep_quality:poor,
     PROLAZI shemu, ali je semantički netočna i mijenja preporuku)

Izvještava točnost po polju profila (null-svjesno), makro-prosjek, zasebno za
podskup 'negation', te preciznost/odziv/F1 za izvlačenje ciljeva.

Parseri (pluggable):
  - ReplayParser (zadano): čita predicted_profile/predicted_goals iz scenarija
    (za offline evaluaciju logiranih izlaza stvarnog parsera). Radi bez mreže.
  - HttpParser (--api-url URL): šalje profile_text/goals_text na /parse/full
    pokrenutog API-ja i mjeri i determinizam (--repeats).

Pokretanje (offline):  python evaluate_nlu.py
Pokretanje (uživo):    python evaluate_nlu.py --api-url http://localhost:8000 --repeats 3
"""
from __future__ import annotations
import argparse, csv, json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import metrics as M
import engine_adapter as E

RESULTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")


# --------------------------------------------------------------------------- #
# Parseri
# --------------------------------------------------------------------------- #

class ReplayParser:
    """Offline: vraća logirani izlaz parsera pohranjen u scenariju."""
    def parse(self, scn):
        return scn.get("predicted_profile") or {}, list(scn.get("predicted_goals") or [])


class HttpParser:
    """Uživo: poziva /parse/full na pokrenutom API-ju (zahtijeva `requests`)."""
    def __init__(self, base_url):
        import requests  # noqa: F401  (uvezeno lijeno da offline put ne zahtijeva requests)
        self.base = base_url.rstrip("/")

    def parse(self, scn):
        import requests
        r = requests.post(f"{self.base}/parse/full", json={
            "profile_text": scn.get("profile_text", ""),
            "goals_text": scn.get("goals_text", ""),
        }, timeout=120)
        r.raise_for_status()
        data = r.json()

        # Prilagođeno stvarnom obliku odgovora: /parse/full vraća
        # {"profile": {...}, "goals": {"goals": [...]}}, dakle ciljevi su umotani
        # u objekt, a ovdje se očekuje ravna lista naziva.
        profile = data.get("profile") or data.get("parsed_profile") or {}

        goals = data.get("goals")
        if isinstance(goals, dict):
            goals = goals.get("goals")
        if goals is None:
            goals = data.get("parsed_goals")

        return profile, goals or []


# --------------------------------------------------------------------------- #
# Provjere
# --------------------------------------------------------------------------- #

def load_schema():
    with open(os.path.join(DATA_DIR, "nlu_schema.json"), "r", encoding="utf-8") as f:
        return json.load(f)


def schema_valid(profile, goals, schema):
    fields = schema["profile_fields"]
    for key, val in (profile or {}).items():
        if key not in fields:
            return False
        if val is None:
            continue
        spec = fields[key]
        allowed = spec.get("allowed")
        if allowed is None:
            continue
        # Polja tipa liste (npr. allergies) provjeravaju se po članu; bez toga bi
        # se cijela lista uspoređivala s pojedinačnim dopuštenim vrijednostima i
        # svaki ispravno izvučen popis bio bi proglašen neispravnim.
        if spec.get("type") == "list" or isinstance(val, list):
            if not isinstance(val, list) or any(item not in allowed for item in val):
                return False
        elif val not in allowed:
            return False
    allowed_goals = set(schema["goal_tags"])
    return all(g in allowed_goals for g in (goals or []))


def field_correct(expected, predicted, field):
    return expected.get(field, None) == predicted.get(field, None)


def goal_prf(expected_goals, predicted_goals):
    e, p = set(expected_goals or []), set(predicted_goals or [])
    tp = len(e & p)
    prec = tp / len(p) if p else (1.0 if not e else 0.0)
    rec = tp / len(e) if e else (1.0 if not p else 0.0)
    f1 = (2 * prec * rec / (prec + rec)) if (prec + rec) else 0.0
    return prec, rec, f1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenarios", default=None)
    ap.add_argument("--api-url", default=None, help="ako je zadano, koristi HttpParser")
    ap.add_argument("--repeats", type=int, default=1, help="ponovljeni pozivi za provjeru determinizma (samo uživo)")
    args = ap.parse_args()

    scenarios = E.load_scenarios(args.scenarios)
    schema = load_schema()
    fields = list(schema["profile_fields"].keys())
    parser = HttpParser(args.api_url) if args.api_url else ReplayParser()

    per_field_correct = {fld: [] for fld in fields}
    neg_field_correct = {fld: [] for fld in fields}
    schema_ok = 0
    goal_p, goal_r, goal_f = [], [], []
    determinism = []

    for scn in scenarios:
        profile, goals = parser.parse(scn)
        if schema_valid(profile, goals, schema):
            schema_ok += 1
        exp = scn.get("expected_profile") or {}
        is_neg = "negation" in (scn.get("tags") or [])
        for fld in fields:
            ok = 1.0 if field_correct(exp, profile, fld) else 0.0
            per_field_correct[fld].append(ok)
            if is_neg:
                neg_field_correct[fld].append(ok)
        p, r, f1 = goal_prf(scn.get("expected_goals"), goals)
        goal_p.append(p); goal_r.append(r); goal_f.append(f1)

        if args.api_url and args.repeats > 1:
            outs = []
            for _ in range(args.repeats):
                pr, gl = parser.parse(scn)
                outs.append(json.dumps({"p": pr, "g": sorted(gl)}, sort_keys=True))
            determinism.append(1.0 if len(set(outs)) == 1 else 0.0)

    macro = M.mean([M.mean(v) for v in per_field_correct.values() if v])
    neg_macro = M.mean([M.mean(v) for v in neg_field_correct.values() if v])

    print("\n=== IP4-A: EVALUACIJA PARSIRANJA (NLU) ===")
    print(f"Parser: {'HTTP ' + args.api_url if args.api_url else 'Replay (offline log)'}")
    print(f"Valjanost sheme: {schema_ok}/{len(scenarios)} scenarija")
    print("\nSemantička točnost po polju profila:")
    print(f"  {'Polje':<20}{'točnost':>10}")
    for fld in fields:
        acc = M.mean(per_field_correct[fld])
        print(f"  {fld:<20}{(acc if acc is not None else 0):>10.3f}")
    print(f"  {'MAKRO-PROSJEK':<20}{(macro if macro is not None else 0):>10.3f}")
    if neg_macro is not None:
        print(f"  {'Podskup negacije':<20}{neg_macro:>10.3f}")

    gp, gr, gf = M.mean(goal_p), M.mean(goal_r), M.mean(goal_f)
    print("\nIzvlačenje ciljeva (skupovno):")
    print(f"  preciznost {gp:.3f}   odziv {gr:.3f}   F1 {gf:.3f}")

    if determinism:
        print(f"\nDeterminizam parsiranja ({args.repeats} poziva): "
              f"{M.mean(determinism)*100:.1f}% scenarija dalo identičan izlaz")
    else:
        print("\nNapomena: u replay načinu determinizam se ne mjeri. Za pravu provjeru "
              "pokrenite --api-url ... --repeats 3 (temperatura 0.1 ≠ 0 može davati varijacije).")

    os.makedirs(RESULTS_DIR, exist_ok=True)
    out = os.path.join(RESULTS_DIR, "nlu.csv")
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["polje", "tocnost"])
        for fld in fields:
            w.writerow([fld, M.mean(per_field_correct[fld])])
        w.writerow(["MAKRO", macro])
        w.writerow(["NEGACIJA_MAKRO", neg_macro])
        w.writerow(["goal_precision", gp]); w.writerow(["goal_recall", gr]); w.writerow(["goal_f1", gf])
        w.writerow(["schema_ok", schema_ok]); w.writerow(["n", len(scenarios)])
    print(f"\nCSV zapisan: {out}")


if __name__ == "__main__":
    main()
