# ABOUTME: Builds day-to-day spending for every Louisiana school system and parish for each
# ABOUTME: school year 2008-09 to 2024-25, from normalized AFR files, October enrollment and Census population.
import difflib
import json
import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
NORM = ROOT / "data" / "interim" / "afr-normalized"
OUT = ROOT / "data" / "combined"

# LDOE AFR function codes (LAUGH chart of accounts) -> plain categories. Day-to-day spending
# is functions 1000-3999; construction (4xxx), debt and transfers (5xxx, incl. pass-through
# money to charters) are left out, as is tuition paid to other systems (objects 561-569).
CATEGORIES = [
    ("instruction", lambda f: 1000 <= f < 2000),
    ("support", lambda f: f // 100 in (21, 22)),
    ("school_admin", lambda f: f // 100 == 24),
    ("central_admin", lambda f: f // 100 in (23, 25, 28, 29)),
    ("buildings", lambda f: f // 100 == 26),
    ("transport", lambda f: f // 100 == 27),
    ("food", lambda f: f // 100 == 31),
    ("community", lambda f: f // 100 in (32, 33)),
]
MONEY = [k for k, _ in CATEGORIES] + ["teacher_pay", "admin_pay", "benefits", "federal", "current_spending"]
ONLINE = re.compile(r"virtual|connections academy|university view|e-?academy|online", re.I)
# Enrollment roll-up codes whose sites belong to a system with a different code.
ROLLUP_OWNER = {"R36": "036"}
PLACE_TO_PARISH = {"DeSoto": "De Soto", "New Orleans": "Orleans", "Lake Charles": "Calcasieu",
                   "Mansura": "Avoyelles"}


def norm_name(name) -> str:
    """School name reduced for matching across files ("RSD-Arthur Ashe Charter School" -> "arthurashe")."""
    n = re.sub(r"^rsd\s*-\s*", "", str(name).lower())
    n = re.sub(r"\b(the|school|charter|inc|of|a|an)\b", " ", n)
    return re.sub(r"[^a-z0-9]", "", n)


def match_by_name(names: pd.Series, candidates: pd.Series) -> pd.Series:
    """Map each name to a candidate key (exact normalized match first, then a close one)."""
    cand = {norm_name(v): k for k, v in candidates.items() if norm_name(v)}
    out = {}
    for idx, name in names.items():
        n = norm_name(name)
        hit = cand.get(n) or next((cand[m] for m in difflib.get_close_matches(n, cand, n=1, cutoff=0.88)), None)
        if hit is not None:
            out[idx] = hit
    return pd.Series(out, dtype=object)


def summarise(afr: pd.DataFrame) -> pd.DataFrame:
    f = afr.function.fillna(0).astype(int)
    obj = afr.object.fillna(0).astype(int)
    cur = afr[(f >= 1000) & (f < 4000) & ~obj.between(561, 569)].copy()
    cf, co = cur.function.astype(int), cur.object.fillna(0).astype(int)
    for key, test in CATEGORIES:
        cur[key] = cur.total.where(cf.map(test), 0)
    cur["teacher_pay"] = cur.total.where(co == 112, 0)
    cur["admin_pay"] = cur.total.where(co == 111, 0)
    cur["benefits"] = cur.total.where(co.between(200, 299), 0)
    cur["current_spending"] = cur.total
    out = cur.groupby("lea_code")[MONEY].sum()
    # System-level rows carry the system's name; charters reporting only by school fall
    # back to the name on their school rows.
    names = afr[afr.site_code.isna()].groupby("lea_code").name.first()
    out["name"] = names.reindex(out.index).fillna(afr.groupby("lea_code").name.first())
    return out


def load_enrollment(fall_year: int) -> pd.DataFrame:
    folder = RAW / "ldoe" / "enrollment-multi-stats"
    hits = sorted(folder.glob(f"oct-{fall_year}-multi-stats-(total-by-site*"))
    if len(hits) != 1:
        raise SystemExit(f"Expected one October {fall_year} site file, found {hits}")
    xl = pd.ExcelFile(hits[0])
    sheet = next((s for s in xl.sheet_names if "site" in s.lower()), xl.sheet_names[0])
    raw = pd.read_excel(xl, sheet_name=sheet, header=None, dtype=str)
    hdr_row = next(i for i, r in raw.iterrows() if r.astype(str).str.contains("Site Code", case=False).any())
    hdr = raw.iloc[hdr_row].astype(str)
    site_col = next(i for i, v in enumerate(hdr) if re.search("site code", v, re.I))
    enr_col = next(i for i, v in enumerate(hdr) if re.search("enrollment|total reported|total students", v, re.I))
    name_col = next(i for i, v in enumerate(hdr) if i > site_col and re.search("name", v, re.I))
    d = raw.iloc[hdr_row + 1:, [0, 1, site_col, name_col, enr_col]]
    d.columns = ["sys", "sys_name", "site", "site_name", "enrollment"]
    d = d[d.site.astype(str).str.fullmatch(r"\w{6}")].copy()
    d["sys"] = d.sys.str.strip()
    d["enrollment"] = pd.to_numeric(d.enrollment, errors="coerce").fillna(0)
    return d


def ccd_sites() -> pd.DataFrame:
    rows = []
    for p in sorted((RAW / "ccd-directory").glob("la_*.json")):
        for r in json.loads(p.read_text())["results"]:
            rows.append({"site": r["seasch"], "year": r["year"], "fips": r["county_code"],
                         "charter": r["charter"] == 1, "virtual": r.get("virtual") in (1, "1")})
    d = pd.DataFrame(rows).dropna(subset=["site"]).sort_values("year")
    return d.groupby("site").last()


def ccd_names() -> pd.Series:
    """Normalized school name -> parish FIPS, for schools whose LDOE code is not in the directory."""
    rows = {}
    for p in sorted((RAW / "ccd-directory").glob("la_*.json")):
        for r in json.loads(p.read_text())["results"]:
            if r["county_code"] and str(r["county_code"]).startswith("22") and r["school_name"]:
                rows[norm_name(r["school_name"])] = r["county_code"]
    return pd.Series(rows)


def populations() -> pd.DataFrame:
    a = pd.read_csv(RAW / "census-pop" / "co-est00int-tot.csv", encoding="latin-1", dtype={"STATE": str, "COUNTY": str})
    b = pd.read_csv(RAW / "census-pop" / "co-est2020-alldata.csv", encoding="latin-1", dtype={"STATE": str, "COUNTY": str})
    c = pd.read_csv(RAW / "census-pop" / "co-est2024-alldata.csv", encoding="latin-1", dtype={"STATE": str, "COUNTY": str})
    out = {}
    for df, years in ((a, range(2008, 2010)), (b, range(2010, 2020)), (c, range(2020, 2025))):
        # The 2000-2010 file writes codes without leading zeros ("1" for "001").
        df = df.assign(STATE=df.STATE.str.zfill(2), COUNTY=df.COUNTY.str.zfill(3))
        df = df[(df.STATE == "22") & (df.COUNTY != "000")]
        for y in years:
            for fips, pop in zip("22" + df.COUNTY, df[f"POPESTIMATE{y}"]):
                out[(fips, y)] = pop
    names = c[(c.STATE == "22") & (c.COUNTY != "000")]
    fips_name = dict(zip("22" + names.COUNTY, names.CTYNAME.str.replace(" Parish", "", regex=False)))
    s = pd.Series(out, name="population")
    s.index.names = ["fips", "year"]
    return s.reset_index().assign(parish=lambda d: d.fips.map(fips_name))


def place_systems(lea: pd.DataFrame, sites: pd.DataFrame, ccd: pd.DataFrame, uni: pd.DataFrame,
                  fips_name: dict, by_name: pd.Series) -> pd.DataFrame:
    """Give each system a parish and a type."""
    lea = lea.copy()
    lea["lea_type"] = uni.lea_type.reindex(lea.index)
    lea["parish"] = uni.parish.reindex(lea.index).replace(PLACE_TO_PARISH)
    s = sites.join(ccd[["fips", "virtual"]], on="site")
    s["parish_ccd"] = s.fips.map(fips_name)  # non-Louisiana county codes map to nothing
    s["parish_ccd"] = s.parish_ccd.fillna(s.site_name.map(norm_name).map(by_name).map(fips_name))
    # A few NCES directory entries have a wrong or missing county; fix them by school name.
    fixes = pd.read_csv(ROOT / "data" / "crosswalk" / "site_parish_overrides.csv")
    for pat, parish in zip(fixes.site_name_pattern, fixes.parish):
        s.loc[s.site_name.astype(str).str.contains(pat, case=False), "parish_ccd"] = parish
    by_owner = s.groupby("owner")
    online = by_owner.apply(lambda g: bool(g.virtual.any() or g.site_name.astype(str).str.contains(ONLINE).any()),
                            include_groups=False)
    ccd_parish = by_owner.apply(lambda g: g.groupby("parish_ccd").enrollment.sum().idxmax()
                                if g.parish_ccd.notna().any() else None, include_groups=False)
    fixed = lea.lea_type.isin(["parish_system", "city_system", "state_special", "lab_school"])
    for code in lea.index[~fixed]:
        if online.get(code, False) or ONLINE.search(str(lea.at[code, "name"])):
            lea.at[code, "parish"] = "statewide (online)"
        elif ccd_parish.get(code):
            lea.at[code, "parish"] = ccd_parish[code]
        if pd.isna(lea.at[code, "lea_type"]):
            lea.at[code, "lea_type"] = "rsd" if code == "396" else "charter"
    return lea


def main() -> None:
    uni = pd.read_csv(ROOT / "research" / "lea-universe.csv", dtype=str).drop_duplicates("lea_code").set_index("lea_code")
    ccd = ccd_sites()
    by_name = ccd_names()
    pop = populations()
    fips_name = dict(zip(pop.fips, pop.parish))
    lea_rows, parish_rows, gaps = [], [], []
    for path in sorted(NORM.glob("afr_exp_*.csv.gz")):
        afr = pd.read_csv(path, dtype={"lea_code": str, "site_code": str, "keypch": str}, low_memory=False)
        sy, fy = afr.school_year.iloc[0], int(afr.fy.iloc[0])
        fall = fy - 1
        lea = summarise(afr)
        enr = load_enrollment(fall)
        owners = afr.dropna(subset=["site_code"]).drop_duplicates("site_code").set_index("site_code").lea_code
        enr["owner"] = enr.site.map(owners).fillna(enr.sys.replace(ROLLUP_OWNER))
        # Some years code a school differently in the two files (2015-16: operator codes in
        # the AFR, per-school W codes in enrollment). Match those leftovers by school name.
        loose = ~enr.owner.isin(lea.index)
        afr_sites = afr.dropna(subset=["site_code"]).drop_duplicates("site_code")
        unclaimed = afr_sites[~afr_sites.site_code.isin(enr.site)].set_index("site_code")
        hit = match_by_name(enr.loc[loose, "site_name"], unclaimed.site_name)
        enr.loc[hit.index, "owner"] = hit.map(unclaimed.lea_code)
        # Students at schools whose spending is not in the AFR (e.g. early Type 1/3/4 charters
        # that filed separate reports) would inflate the count; find them and leave them out.
        enr = enr.join(ccd[["charter"]], on="site")
        in_afr = enr.owner.isin(lea.index)
        missing_spend = enr[~in_afr]
        gaps.append({"school_year": sy, "students_without_spending": int(missing_spend.enrollment.sum()),
                     "owners": ",".join(sorted(missing_spend.owner.unique()))})
        enr = enr[in_afr]
        lea["enrollment"] = enr.groupby("owner").enrollment.sum()
        lea = place_systems(lea, enr, ccd, uni, fips_name, by_name)
        # The AFR cuts some names short ("Zachary Community School Di"); parish and city
        # boards keep the same code every year, so use their full name from the LEA list.
        boards = lea.lea_type.isin(["parish_system", "city_system"])
        lea.loc[boards, "name"] = uni.name.reindex(lea.index[boards]).fillna(lea.loc[boards, "name"])
        no_students = lea[lea.enrollment.isna() | (lea.enrollment == 0)]
        if len(no_students):
            gaps[-1]["spending_without_students"] = round(no_students.current_spending.sum())
            gaps[-1]["no_student_leas"] = ",".join(no_students.index)
        lea = lea[lea.enrollment > 0]
        unplaced = lea[lea.parish.isna()]
        if len(unplaced):
            raise SystemExit(f"{sy}: no parish for {unplaced.name.to_dict()}")
        lea["school_year"], lea["fy"] = sy, fy
        lea_rows.append(lea.reset_index().rename(columns={"index": "lea_code"}))

        p = pop[pop.year == fall].set_index("parish")
        in_parish = lea[lea.parish.isin(p.index) & (lea.lea_type != "state_special")]
        par = in_parish.groupby("parish")[MONEY + ["enrollment"]].sum()
        par["systems"] = in_parish.groupby("parish").size()
        par["charter_students"] = in_parish[in_parish.lea_type.str.startswith("charter")].groupby("parish").enrollment.sum()
        par = p[["fips", "population"]].join(par, how="left").fillna({"charter_students": 0})
        par["school_year"], par["fy"] = sy, fy
        parish_rows.append(par.reset_index().rename(columns={"index": "parish"}))
        print(f"{sy}: {len(lea):>3} systems, {int(lea.enrollment.sum()):>7,} students, "
              f"${lea.current_spending.sum()/1e9:.2f}B, ${lea.current_spending.sum()/lea.enrollment.sum():,.0f}/student; "
              f"students w/o spending {gaps[-1]['students_without_spending']:,} ({gaps[-1]['owners'][:60]})"
              + (f"; spending w/o students ${gaps[-1]['spending_without_students']/1e6:.1f}M ({gaps[-1]['no_student_leas']})"
                 if "spending_without_students" in gaps[-1] else ""))
    lea_all = pd.concat(lea_rows, ignore_index=True)
    lea_all = lea_all.rename(columns={lea_all.columns[0]: "lea_code"})
    cols = ["school_year", "fy", "lea_code", "name", "lea_type", "parish", "enrollment"] + MONEY
    lea_all[cols].to_csv(OUT / "lea_years.csv", index=False)
    pd.concat(parish_rows, ignore_index=True).to_csv(OUT / "parish_years.csv", index=False)
    pd.DataFrame(gaps).to_csv(OUT / "coverage_gaps.csv", index=False)


if __name__ == "__main__":
    main()
