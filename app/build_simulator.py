"""Build app/index.html from app/simulateur.csv and app/template.html.

Browsers block a file:// page from reading a local CSV, so the data is
validated here and embedded in the page as JSON.

Usage: python app/build_simulator.py
"""

import csv
import json
import math
import sys
from pathlib import Path

APP = Path(__file__).resolve().parent
CSV_PATH = APP / "simulateur.csv"
TEMPLATE_PATH = APP / "template.html"
OUT_PATH = APP / "index.html"

COLUMNS = ["percentile", "n", "defauts", "montant", "montant_defaut", "pd_seuil"]
INT_COLUMNS = {"percentile", "n", "defauts"}
N_ROWS = 100
PLACEHOLDER = "/*__DATA__*/null"


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
    print(f"  automation rate:          {(green['n'] + red['n']) / N:.2%}")
    print(f"  defaults caught by red:   {red['defauts'] / D:.2%}")
    print(f"  good clients refused:     {(red['n'] - red['defauts']) / (N - D):.2%}")
    print(f"  loss in green:            {green['montant_defaut'] * lgd:,.0f} USD")
    print(f"  losses avoided by red:    {red['montant_defaut'] * lgd:,.0f} USD")
    print(f"  refused to good clients:  {red['montant'] - red['montant_defaut']:,.0f} USD")


def main():
    rows = load_rows()

    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    if template.count(PLACEHOLDER) != 1:
        fail(f"template must contain '{PLACEHOLDER}' exactly once")

    data_json = json.dumps(rows, separators=(",", ":"))
    OUT_PATH.write_text(template.replace(PLACEHOLDER, data_json), encoding="utf-8")

    print(f"Wrote {OUT_PATH}")
    print_check(rows)


if __name__ == "__main__":
    main()
