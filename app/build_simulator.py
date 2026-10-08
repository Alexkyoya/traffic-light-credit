"""Build app/index.html from its CSV, model, scoring code and HTML template.

Browsers block a file:// page from reading local files, so all required
data and scoring code are embedded in the generated page.

Usage: python app/build_simulator.py
"""

import csv
import json
import math
import sys
from pathlib import Path

APP = Path(__file__).resolve().parent
CSV_PATH = APP / "simulateur.csv"
MODEL_PATH = APP / "modele.json"
SCORING_PATH = APP / "scoring.js"
TEMPLATE_PATH = APP / "template.html"
OUT_PATH = APP / "index.html"

COLUMNS = ["percentile", "n", "defauts", "montant", "montant_defaut", "pd_seuil"]
INT_COLUMNS = {"percentile", "n", "defauts"}
N_ROWS = 100
PLACEHOLDER = "/*__DATA__*/null"
MODEL_PLACEHOLDER = "/*__MODEL__*/null"
SCORING_PLACEHOLDER = "/*__SCORING__*/"


def fail(message):
    sys.exit(f"ERROR: {message}")


def parse_number(text, column, line):
    try:
        value = float(text)
    except (TypeError, ValueError):
        fail(f"line {line}, column '{column}': '{text}' is not a number")
    if not math.isfinite(value):
        fail(f"line {line}, column '{column}': value is not finite")
    if column in INT_COLUMNS:
        if value != int(value):
            fail(f"line {line}, column '{column}': {text} should be a whole number")
        return int(value)
    return value


def load_rows():
    if not CSV_PATH.exists():
        fail(f"{CSV_PATH} not found")
    with CSV_PATH.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        missing = [c for c in COLUMNS if c not in (reader.fieldnames or [])]
        if missing:
            fail(f"missing columns: {', '.join(missing)}")
        rows = []
        for line, raw in enumerate(reader, start=2):
            rows.append({c: parse_number(raw[c], c, line) for c in COLUMNS})

    if len(rows) != N_ROWS:
        fail(f"expected {N_ROWS} rows, found {len(rows)}")

    previous_pd = -1.0
    for i, row in enumerate(rows):
        line = i + 2
        if row["percentile"] != i:
            fail(f"line {line}: expected percentile {i}, found {row['percentile']}")
        if row["n"] <= 0:
            fail(f"line {line}: n must be positive")
        if not 0 <= row["defauts"] <= row["n"]:
            fail(f"line {line}: defauts must be between 0 and n")
        if not 0 <= row["montant_defaut"] <= row["montant"] + 1e-6:
            fail(f"line {line}: montant_defaut must be between 0 and montant")
        if not 0 <= row["pd_seuil"] <= 1:
            fail(f"line {line}: pd_seuil must be between 0 and 1")
        if row["pd_seuil"] < previous_pd:
            fail(f"line {line}: pd_seuil must not decrease")
        previous_pd = row["pd_seuil"]
    return rows


def load_model():
    if not MODEL_PATH.exists():
        fail(f"{MODEL_PATH} not found")
    try:
        model = json.loads(MODEL_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        fail(f"could not read {MODEL_PATH}: {exc}")

    required = {"features", "mean", "scale", "coef", "intercept",
                "numeric_inputs", "categories", "ranges", "pd_cuts", "check"}
    missing = sorted(required - model.keys())
    if missing:
        fail(f"model is missing fields: {', '.join(missing)}")
    size = len(model["features"])
    if not size or any(len(model[key]) != size for key in ("mean", "scale", "coef")):
        fail("features, mean, scale and coef must have the same non-zero length")
    if len(model["pd_cuts"]) != 101:
        fail(f"expected 101 PD cuts, found {len(model['pd_cuts'])}")
    if len(model["check"]) != 3:
        fail(f"expected 3 check clients, found {len(model['check'])}")
    for name in model["numeric_inputs"]:
        if name == "loan_to_income":
            continue
        if name not in model["ranges"]:
            fail(f"model has no range for numeric input '{name}'")
    for i, scale in enumerate(model["scale"]):
        if not math.isfinite(scale) or scale == 0:
            fail(f"feature {i}: scale must be finite and non-zero")
    return model


def zone(rows, start, end):
    part = rows[start:end]
    return {k: sum(r[k] for r in part) for k in ("n", "defauts", "montant", "montant_defaut")}


def print_check(rows, g=40, r=90, lgd=0.60):
    total = zone(rows, 0, N_ROWS)
    green, yellow, red = zone(rows, 0, g), zone(rows, g, r), zone(rows, r, N_ROWS)
    N, D = total["n"], total["defauts"]

    print(f"Total loans:    {N:,}")
    print(f"Total defaults: {D:,}  ({D / N:.2%})")
    print()
    print(f"Check with g = {g}, r = {r}, LGD = {lgd:.0%}:")
    for name, z in (("green", green), ("yellow", yellow), ("red", red)):
        print(f"  {name:<6} {z['n']:>6,} loans ({z['n'] / N:6.2%})  "
              f"{z['defauts']:>5,} defaults  default rate {z['defauts'] / z['n']:.2%}")
    print(f"  automatic approvals:      {green['n'] / N:.2%}")
    print(f"  analyst workload:         {(yellow['n'] + red['n']) / N:.2%}")
    print(f"  defaults sent to review:  {red['defauts'] / D:.2%}")
    print(f"  good clients reviewed:    {(red['n'] - red['defauts']) / (N - D):.2%}")
    print(f"  loss in green:            {green['montant_defaut'] * lgd:,.0f} USD")
    print(f"  potential loss in red:    {red['montant_defaut'] * lgd:,.0f} USD")
    print(f"  good-client loans in red: {red['montant'] - red['montant_defaut']:,.0f} USD")


def main():
    rows = load_rows()
    model = load_model()

    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    for placeholder in (PLACEHOLDER, MODEL_PLACEHOLDER, SCORING_PLACEHOLDER):
        if template.count(placeholder) != 1:
            fail(f"template must contain '{placeholder}' exactly once")
    if not SCORING_PATH.exists():
        fail(f"{SCORING_PATH} not found")

    data_json = json.dumps(rows, separators=(",", ":"))
    model_json = json.dumps(model, separators=(",", ":"))
    scoring_js = SCORING_PATH.read_text(encoding="utf-8")
    built = template.replace(PLACEHOLDER, data_json)
    built = built.replace(MODEL_PLACEHOLDER, model_json)
    built = built.replace(SCORING_PLACEHOLDER, scoring_js)
    OUT_PATH.write_text(built, encoding="utf-8")

    print(f"Wrote {OUT_PATH}")
    print_check(rows)


if __name__ == "__main__":
    main()
