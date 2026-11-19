# ABOUTME: Assembles everything the explainer page needs (parish map paths, 2023-24 figures,
# ABOUTME: per-student trends, published-budget survey) into one JSON file in site/.
import datetime
import json
import math
import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
COMBINED = ROOT / "data" / "combined"
OUT = ROOT / "site" / "data.json"
PAGE = ROOT / "site" / "index.html"


def stamp_updated(day: datetime.date) -> None:
    """Set the page's "Updated" date (the <time id="updated"> element)."""
    html = PAGE.read_text()
    label = f"{day.day} {day:%B %Y}"
    new, n = re.subn(r'<time id="updated" datetime="[^"]*">[^<]*</time>',
                     f'<time id="updated" datetime="{day.isoformat()}">{label}</time>', html)
    if n != 1:
        raise SystemExit("index.html has no single <time id=\"updated\"> element")
    PAGE.write_text(new)
CITY_SYSTEMS = {"Baker": "East Baton Rouge", "Central": "East Baton Rouge",
                "Zachary": "East Baton Rouge", "Monroe": "Ouachita", "Bogalusa": "Washington"}
CATS = [("instruction", "Classroom instruction"), ("support", "Student and teacher support"),
        ("school_admin", "School offices"), ("central_admin", "Central office"),
        ("buildings", "Buildings and upkeep"), ("transport", "Buses"), ("food", "Food"),
        ("community", "Other")]


def parish_paths() -> dict:
    topo = json.loads((ROOT / "data" / "raw" / "geo" / "counties-10m.json").read_text())
    sx, sy = topo["transform"]["scale"]
    tx, ty = topo["transform"]["translate"]
    arcs = []
    for arc in topo["arcs"]:
        x = y = 0
        pts = []
        for dx, dy in arc:
            x += dx
            y += dy
            pts.append((x * sx + tx, y * sy + ty))
        arcs.append(pts)

    def ring(idx):
        pts = []
        for i in idx:
            seg = arcs[i] if i >= 0 else arcs[~i][::-1]
            pts.extend(seg if not pts else seg[1:])
        return pts

    geoms = [g for g in topo["objects"]["counties"]["geometries"] if g["id"].startswith("22")]
    k = math.cos(math.radians(31))
    shapes = {}
    for g in geoms:
        polys = g["arcs"] if g["type"] == "MultiPolygon" else [g["arcs"]]
        shapes[g["id"]] = [[[(lon * k, -lat) for lon, lat in ring(r)] for r in poly] for poly in polys]
    xs = [p[0] for s in shapes.values() for poly in s for r in poly for p in r]
    ys = [p[1] for s in shapes.values() for poly in s for r in poly for p in r]
    w = 600
    scale = w / (max(xs) - min(xs))
    h = (max(ys) - min(ys)) * scale
    out = {}
    for fips, s in shapes.items():
        d = []
        for poly in s:
            for r in poly:
                d.append("M" + "L".join(f"{(x-min(xs))*scale:.1f},{(y-min(ys))*scale:.1f}" for x, y in r) + "Z")
        out[fips] = "".join(d)
    return {"width": w, "height": round(h, 1), "paths": out}


def clean(v):
    if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
        return None
    return v


def budgets_by_parish(lea: pd.DataFrame) -> list:
    b = pd.read_csv(ROOT / "research" / "district-budgets.csv", dtype=str).fillna("")
    parishes = sorted(set(lea.parish), key=len, reverse=True)
    rows = []
    for r in b.itertuples():
        name = r.system
        place = next((p for c, p in CITY_SYSTEMS.items() if name.startswith(c) or f"City of {c}" in name
                      or f"{c} City" in name), None)
        city = place is not None
        if not city:
            norm = name.replace("DeSoto", "De Soto").replace("St ", "St. ")
            place = next((p for p in parishes if norm.startswith(p)), None)
        if place is None:
            raise SystemExit(f"Cannot place budget survey row: {name}")
        found = not r.earliest_year.lower().startswith("not")
        rows.append({"system": name, "parish": place, "city": city, "found": found,
                     "earliest": r.earliest_year if found else "", "latest": r.latest_year if found else "",
                     "detail": r.detail_level, "page": r.budget_page_url if r.budget_page_url.startswith("http") else "",
                     "latest_url": r.latest_budget_url if r.latest_budget_url.startswith("http") else ""})
    return rows


def main() -> None:
    lea = pd.read_csv(COMBINED / "lea_2023_24.csv", dtype={"lea_code": str})
    par = pd.read_csv(COMBINED / "parish_2023_24.csv", dtype={"fips": str})
    trend = pd.read_csv(COMBINED / "trend_f33.csv", dtype={"lea_code": str})
    state_tr = pd.read_csv(COMBINED / "trend_f33_state.csv")

    keys = [k for k, _ in CATS] + ["teacher_pay", "admin_pay", "benefits", "federal"]
    systems = []
    for r in lea.itertuples():
        systems.append({"code": r.lea_code, "name": r.lea_name, "type": r.lea_type, "parish": r.parish,
                        "students": int(r.enrollment), "spend": round(r.current_spending),
                        **{k: round(getattr(r, k)) for k in keys}})
    parishes = []
    for r in par.itertuples():
        parishes.append({"fips": r.fips, "name": r.parish, "population": int(r.population),
                         "students": int(r.enrollment), "charter_students": int(r.charter_students),
                         "spend": round(r.current_spending), **{k: round(getattr(r, k)) for k in keys}})
    trends = {}
    for code, g in trend.groupby("lea_code"):
        trends[code] = [[int(y), round(v)] for y, v in zip(g.fiscal_year, g.per_student_real)]
    total = {"students": int(lea.enrollment.sum()), "spend": round(lea.current_spending.sum()),
             **{k: round(lea[k].sum()) for k in keys}}
    data = {
        "school_year": "2023-24", "pop_year": 2023, "categories": CATS, "state": total,
        "state_trend": [[int(y), round(v)] for y, v in zip(state_tr.fiscal_year, state_tr.per_student_real)],
        "parishes": parishes, "systems": systems, "trends": trends,
        "budgets": budgets_by_parish(lea), "map": parish_paths(),
    }
    OUT.parent.mkdir(exist_ok=True)
    text = json.dumps(data, separators=(",", ":"), default=clean)
    if not OUT.exists() or OUT.read_text() != text:
        OUT.write_text(text)
        stamp_updated(datetime.date.today())
    print(f"{OUT} {OUT.stat().st_size/1024:.0f} KB; {len(parishes)} parishes, {len(systems)} systems, "
          f"{len(data['budgets'])} budget rows, {len(data['map']['paths'])} map shapes")


if __name__ == "__main__":
    main()
