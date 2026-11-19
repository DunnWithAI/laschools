# ABOUTME: Reads LDOE Annual Financial Report expenditure files (Report 2) for 2008-09 to
# ABOUTME: 2024-25, whatever their layout, into one normalized CSV per school year.
"""
Layouts handled (school-year start in the file's Year column; FY = Year + 1):
  grouping   2008-09..2014-15, 2016-17: Grouping, LEA/SiteCode (3 chars = system,
             6 chars = school site, 999xxx = state totals). 2014-15 has no header row.
             2011-12..2013-14 exist only as Access databases (exported first, see ACCESS).
  lea_site   2015-16: LEA, District, SiteCode ("001xxx" = system-level rows).
  modern     2017-18..2023-24: LEA Code / LEA_Code, Site Code / SiteCd.
  no_object  2024-25: as modern but no Object column, and the function code sits in a
             column labelled "Source". Object is filled in from KeyPchCd in earlier years.
Output columns: school_year, fy, lea_code, site_code, name, site_name, keypch, object, function,
federal, total. State-total rows (999...) are dropped.
"""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
AFR = ROOT / "data" / "interim" / "afr"
ACCESS = ROOT / "data" / "interim" / "afr-access"
OUT = ROOT / "data" / "interim" / "afr-normalized"

FUNDS = ["GenFunds", "SpecFedFunds", "ESEAFunds", "OtherSpecFunds", "DebtSvcFunds", "CapProjFunds"]
GROUPING_COLS = ["Year", "Grouping", "LEA/SiteCode", "District/Site Name", "FinProjectCd", "KeyPchCd",
                 "Description", "Object", "Function", "Group", "CapitalOutlay", "Restricted",
                 "Unrestricted", *FUNDS, "TotalFunds"]


def find(pattern: str) -> Path:
    hits = sorted(AFR.glob(pattern))
    if len(hits) != 1:
        raise SystemExit(f"Expected one file for {pattern}, found {len(hits)}")
    return hits[0]


SOURCES = {
    2008: ("grouping", "2008-2009-*/*2-Expenditures*.txt"),
    2009: ("grouping", "2009-2010-*/*2-Expenditures*.txt"),
    2010: ("grouping", "2010-2011-*/*2-Expenditures*.txt"),
    2011: ("access", "2011-2012-exp.csv"),
    2012: ("access", "2012-2013-exp.csv"),
    2013: ("access", "2013-2014-exp.csv"),
    2014: ("grouping_noheader", "2014-afr-web/*2-Expenditures*.txt"),
    2015: ("lea_site", "2015-2016-afr-web/*2-Expenditures*.txt"),
    2016: ("grouping", "2016-2017-afr-web/*2-Expenditures*.xlsx"),
    2017: ("modern", "2017-2018-*/*/*AFR_2 Expenditures.xlsx"),
    2018: ("modern", "2018-2019-*/*AFR-2 Expenditures.xlsx"),
    2019: ("modern", "2019-2020-*/*AFR-2 Expenditures.xlsx"),
    2020: ("modern", "2020-2021-*/*/*AFR-2 Expenditures.xlsb"),
    2021: ("modern", "2021-2022-*/*/*AFR-2 Expenditures.xlsb"),
    2022: ("modern", "2022-2023-*/*AFR-2 Expenditures.xlsb"),
    2023: ("modern", "2023-2024-*/*/AFR - 2 Expenditure.xlsb"),
    2024: ("no_object", "2024-afr-web-reports/*/AFR_Report2_Expenditure.xlsx"),
}


def read_any(path: Path, **kw) -> pd.DataFrame:
    if path.suffix in (".xlsx", ".xlsb"):
        return pd.read_excel(path, engine="calamine", dtype=str, **kw)
    return pd.read_csv(path, dtype=str, encoding="latin-1", **kw)


def from_grouping(df: pd.DataFrame) -> pd.DataFrame:
    code = df["LEA/SiteCode"].str.strip()
    return pd.DataFrame({
        "lea_code": code.str[:3],
        "site_code": code.where(code.str.len() == 6),
        "name": df["District/Site Name"].str.strip(),
        "site_name": df["District/Site Name"].str.strip().where(code.str.len() == 6),
        "keypch": df.KeyPchCd, "object": df.Object, "function": df.Function,
        "fed_a": df.SpecFedFunds, "fed_b": df.ESEAFunds,
        "total": df["TotalFunds"] if "TotalFunds" in df else None,
        "_funds": df[FUNDS].apply(pd.to_numeric, errors="coerce").sum(axis=1),
    })


def normalize(year: int) -> pd.DataFrame:
    kind, pattern = SOURCES[year]
    if kind == "access":
        out = from_grouping(pd.read_csv(ACCESS / pattern, dtype=str))
    elif kind == "grouping":
        out = from_grouping(read_any(find(pattern)))
    elif kind == "grouping_noheader":
        out = from_grouping(read_any(find(pattern), header=None, names=GROUPING_COLS))
    elif kind == "lea_site":
        df = read_any(find(pattern))
        site = df.SiteCode.str.strip()
        out = pd.DataFrame({
            "lea_code": df.LEA.str.strip(), "site_code": site.where(~site.str.endswith("xxx")),
            "name": df.District.str.strip(), "site_name": df.SiteName.str.strip().where(~site.str.endswith("xxx")),
            "keypch": df.KeyPchCd, "object": df.Object,
            "function": df.Function, "fed_a": df.SpecFedFunds, "fed_b": df.ESEAFunds,
            "total": df.TotalFunds})
    else:
        df = read_any(find(pattern))
        df.columns = [c.replace(" ", "_") for c in df.columns]
        lea = (df.get("LEA_Code")).str.strip()
        site = df["Site_Code"] if "Site_Code" in df else df["SiteCd"]
        out = pd.DataFrame({
            "lea_code": lea, "site_code": site.str.strip(),
            "name": df.LEA_Name.str.strip(), "site_name": df[[c for c in df.columns if c in ("Site_Name", "SiteName")][0]].str.strip(),
            "keypch": df.KeyPchCd,
            "object": df.Object if kind == "modern" else None,
            "function": df.Function if kind == "modern" else df.Source,
            "fed_a": df.Spec_Fed_Funds if "Spec_Fed_Funds" in df else df.SpecFedFunds,
            "fed_b": df.ESEA_Funds if "ESEA_Funds" in df else df.ESEAFunds,
            "total": df.Total_Funds if "Total_Funds" in df else df.TotalFunds})
    out = out[~out.lea_code.str.startswith("999")].copy()
    for c in ["object", "function", "fed_a", "fed_b", "total"]:
        out[c] = pd.to_numeric(out[c], errors="coerce")
    if "_funds" in out:
        out["total"] = out.total.fillna(out._funds)
        out = out.drop(columns="_funds")
    out["keypch"] = out.keypch.str.strip().str.zfill(7)
    out["federal"] = out.fed_a.fillna(0) + out.fed_b.fillna(0)
    out["fy"] = year + 1
    out["school_year"] = f"{year}-{str(year + 1)[2:]}"
    return out[["school_year", "fy", "lea_code", "site_code", "name", "site_name", "keypch", "object",
                "function", "federal", "total"]]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    keypch_object = {}
    for year in sorted(SOURCES):
        df = normalize(year)
        if df.object.isna().all():
            df["object"] = df.keypch.map(keypch_object)
            missing = df[df.object.isna() & (df.total != 0)]
            print(f"  {year}: object filled from earlier years; "
                  f"${missing.total.sum()/1e6:,.1f}M on {missing.keypch.nunique()} line items left without one")
        else:
            keypch_object.update(df.dropna(subset=["object"]).drop_duplicates("keypch")
                                 .set_index("keypch").object.to_dict())
        df.to_csv(OUT / f"afr_exp_{year + 1}.csv.gz", index=False)
        cur = df[(df.function >= 1000) & (df.function < 4000)]
        print(f"{df.school_year.iloc[0]}: {len(df):>7,} rows, {df.lea_code.nunique():>3} LEAs, "
              f"current ${cur.total.sum()/1e9:5.2f}B")


if __name__ == "__main__":
    main()
