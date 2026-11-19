# ABOUTME: Builds one school year's spending snapshot for every Louisiana school system
# ABOUTME: (LDOE AFR + Oct enrollment) and a parish roll-up with Census population.
import argparse
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "combined"

# LDOE AFR function codes (LAUGH chart of accounts) -> plain categories.
# Current spending = functions 1000-3999. Facilities acquisition (4xxx), debt service and
# transfers (5xxx, incl. pass-through money to charters) are left out, as in Census "current".
CATEGORIES = [
    ("instruction", "Classroom instruction", lambda f: 1000 <= f < 2000),
    ("support", "Student and teacher support", lambda f: f // 100 in (21, 22)),
    ("school_admin", "School office (principals)", lambda f: f // 100 == 24),
    ("central_admin", "Central office", lambda f: f // 100 in (23, 25, 28, 29)),
    ("buildings", "Buildings and upkeep", lambda f: f // 100 == 26),
    ("transport", "Buses", lambda f: f // 100 == 27),
    ("food", "Food", lambda f: f // 100 == 31),
    ("community", "Community and other", lambda f: f // 100 in (32, 33)),
]
VIRTUAL_LEAS = {"345"}  # statewide online schools: shown, but not placed in a parish
TOTALS_LEA = "999"      # LDOE statewide/subtotal rows


def load_afr(path: Path) -> pd.DataFrame:
    engine = "pyxlsb" if path.suffix == ".xlsb" else None
    df = pd.read_excel(path, engine=engine)
    df = df[df.LEA_Code.astype(str) != TOTALS_LEA].copy()
    df["LEA_Code"] = df.LEA_Code.astype(str)
    return df


def load_enrollment(path: Path) -> pd.DataFrame:
    s = pd.read_excel(path, sheet_name="Total by Site", header=None, skiprows=6, dtype=str)
    s = s.iloc[:, [0, 1, 2, 4, 5]]
    s.columns = ["sys", "sys_name", "site", "site_name", "enrollment"]
    s = s[s.sys != "000"].dropna(subset=["site"])
    s["enrollment"] = pd.to_numeric(s.enrollment)
    return s


def summarise(afr: pd.DataFrame) -> pd.DataFrame:
    f = afr.Function.fillna(0).astype(int)
    obj = afr.Object.fillna(0).astype(int)
    # Tuition paid to other school systems (objects 561-569) is counted by the receiver.
    current = afr[(f >= 1000) & (f < 4000) & ~obj.between(561, 569)].copy()
    cf = current.Function.astype(int)
    cols = {}
    for key, _, test in CATEGORIES:
        cols[key] = current.Total_Funds.where(cf.map(test), 0)
    for key, col in cols.items():
        current[key] = col
    co = current.Object.fillna(0).astype(int)
    current["teacher_pay"] = current.Total_Funds.where(co == 112, 0)
    current["admin_pay"] = current.Total_Funds.where(co == 111, 0)
    current["benefits"] = current.Total_Funds.where(co.between(200, 299), 0)
    current["federal"] = current[["Spec_Fed_Funds", "ESEA_Funds"]].sum(axis=1)
    g = current.groupby("LEA_Code")
    out = g[[k for k, _, _ in CATEGORIES] + ["teacher_pay", "admin_pay", "benefits",
                                            "federal", "Total_Funds"]].sum()
    out = out.rename(columns={"Total_Funds": "current_spending"})
    out["lea_name"] = g.LEA_Name.first()
    # Pass-through to charters (function 5xxx transfers) for context only.
    fx = afr[afr.Function.fillna(0).astype(int).between(5300, 5399)]
    out["transfers_out"] = fx.groupby("LEA_Code").Total_Funds.sum()
    return out.fillna({"transfers_out": 0})


def site_owners(afr: pd.DataFrame, enr: pd.DataFrame) -> pd.DataFrame:
    # Charter LEAs report spending by site; their sites appear under CHA/R36/RBR/RLA in
    # the enrollment file. Everything else belongs to the system it is listed under.
    owners = afr[afr.SiteCd.notna()][["LEA_Code", "SiteCd"]].drop_duplicates()
    owners["SiteCd"] = owners.SiteCd.astype(str)
    m = enr.merge(owners, left_on="site", right_on="SiteCd", how="left")
    m["owner"] = m.LEA_Code.fillna(m.sys).replace({"R36": "036"})
    return m


def parish_population(year: int) -> pd.DataFrame:
    p = pd.read_csv(RAW / "census-pop" / "co-est2024-alldata.csv", encoding="latin-1",
                    dtype={"STATE": str, "COUNTY": str})
    p = p[(p.STATE == "22") & (p.COUNTY != "000")]
    return pd.DataFrame({
        "fips": "22" + p.COUNTY,
        "parish": p.CTYNAME.str.replace(" Parish", "", regex=False),
        "population": p[f"POPESTIMATE{year}"],
    })


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--afr", required=True)
    ap.add_argument("--enrollment", required=True)
    ap.add_argument("--school-year", required=True, help="e.g. 2023-24")
    ap.add_argument("--pop-year", type=int, required=True)
    a = ap.parse_args()

    afr = load_afr(Path(a.afr))
    enr = load_enrollment(Path(a.enrollment))
    lea = summarise(afr)
    sites = site_owners(afr, enr)
    lea["enrollment"] = sites.groupby("owner").enrollment.sum()

    uni = pd.read_csv(ROOT / "research" / "lea-universe.csv", dtype=str).set_index("lea_code")
    lea["lea_type"] = uni.lea_type.reindex(lea.index)
    # lea-universe.csv names a few places by city; Census spells De Soto with a space.
    place_to_parish = {"DeSoto": "De Soto", "New Orleans": "Orleans",
                       "Lake Charles": "Calcasieu", "Mansura": "Avoyelles"}
    lea["parish"] = uni.parish.reindex(lea.index).replace(place_to_parish)
    # Some charter operators are keyed by school in lea-universe.csv but by operator in the
    # AFR. If every site an LEA runs is listed under one enrollment roll-up, use its place.
    rollup_place = {"R36": ("Orleans", "charter_local"),
                    "RBR": ("East Baton Rouge", "charter_rsd")}
    sys_by_owner = sites.groupby("owner").sys.agg(lambda s: frozenset(s))
    for code in lea.index[lea.parish.isna()]:
        rolls = sys_by_owner.get(code, frozenset())
        if len(rolls) == 1 and next(iter(rolls)) in rollup_place:
            lea.loc[code, ["parish", "lea_type"]] = list(rollup_place[next(iter(rolls))])
    lea.loc[lea.index.isin(VIRTUAL_LEAS), "parish"] = "statewide (online)"
    missing = lea[lea.parish.isna()]
    if len(missing):
        raise SystemExit(f"LEAs with no parish in lea-universe.csv: {missing.lea_name.to_dict()}")
    if lea.enrollment.isna().any():
        raise SystemExit(f"LEAs with no enrollment: {lea[lea.enrollment.isna()].lea_name.to_dict()}")
    lea["per_student"] = lea.current_spending / lea.enrollment
    lea["school_year"] = a.school_year

    pop = parish_population(a.pop_year)
    # State-run schools (LSMSA, NOCCA, etc.) enroll students from across the state, so
    # they are listed but not counted in the parish where their building sits.
    in_parish = lea[lea.parish.isin(pop.parish) & (lea.lea_type != "state_special")]
    keys = [k for k, _, _ in CATEGORIES] + ["teacher_pay", "admin_pay", "benefits", "federal",
                                            "current_spending", "enrollment"]
    par = in_parish.groupby("parish")[keys].sum()
    par["systems"] = in_parish.groupby("parish").size()
    par["charter_students"] = in_parish[in_parish.lea_type.str.startswith("charter")] \
        .groupby("parish").enrollment.sum()
    par = pop.set_index("parish").join(par, how="left").fillna({"charter_students": 0})
    par["per_student"] = par.current_spending / par.enrollment
    par["per_resident"] = par.current_spending / par.population
    par["school_year"] = a.school_year

    OUT.mkdir(parents=True, exist_ok=True)
    tag = a.school_year.replace("-", "_")
    lea.reset_index().rename(columns={"LEA_Code": "lea_code"}).to_csv(OUT / f"lea_{tag}.csv", index=False)
    par.reset_index().to_csv(OUT / f"parish_{tag}.csv", index=False)
    print(f"{len(lea)} systems, {int(lea.enrollment.sum()):,} students, "
          f"${lea.current_spending.sum()/1e9:.2f}B current spending")
    print(f"{par.systems.notna().sum()} parishes with a system; online-only: "
          f"{int(lea[lea.parish=='statewide (online)'].enrollment.sum()):,} students; "
          f"statewide entities: {int(lea[~lea.parish.isin(pop.parish) & (lea.parish!='statewide (online)')].enrollment.sum()):,}")
    print(json.dumps({"categories": [[k, label] for k, label, _ in CATEGORIES]}))


if __name__ == "__main__":
    main()
