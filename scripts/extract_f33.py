# ABOUTME: Pulls Louisiana school systems out of the Census Annual Survey of School System
# ABOUTME: Finances (F-33) files, 1992-2024, into one tidy CSV in dollars (source is $1,000s).
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw" / "census-f33"
OUT = ROOT / "data" / "extracted" / "f33_louisiana.csv"

# Census variable -> our column name. Money fields are $1,000s in the source.
MONEY = {
    "TOTALREV": "rev_total", "TFEDREV": "rev_federal", "TSTREV": "rev_state",
    "TLOCREV": "rev_local", "T06": "rev_local_property_tax", "C01": "rev_state_formula",
    "TOTALEXP": "exp_total", "TCURELSC": "exp_current", "TCURINST": "exp_instruction",
    "TCURSSVC": "exp_support_services", "TCUROTH": "exp_other_current",
    "E17": "exp_student_support", "E07": "exp_instructional_staff_support",
    "E08": "exp_general_admin", "E09": "exp_school_admin",
    "V40": "exp_operations_maintenance", "V45": "exp_transportation",
    "V90": "exp_business_central", "V85": "exp_support_nonspecified", "E11": "exp_food",
    "TCAPOUT": "exp_capital_outlay", "I86": "exp_debt_interest",
    "Q11": "exp_payments_other_systems", "V92": "exp_payments_to_charters",
    "Z32": "sal_total", "Z33": "sal_instruction", "V15": "sal_general_admin",
    "V17": "sal_school_admin", "Z34": "benefits_total",
    "_19H": "debt_outstanding_start", "_41F": "debt_outstanding_end",
}
COUNTS = {"V33": "enrollment"}


def read(path: Path) -> pd.DataFrame:
    if path.suffix == ".xlsx":
        return pd.read_excel(path, dtype=str)
    # index_col=False: some years have a trailing comma on the header row.
    return pd.read_csv(path, dtype=str, low_memory=False, index_col=False)


def fiscal_year(name: str) -> int:
    yy = int(name[5:7])
    return 1900 + yy if yy >= 90 else 2000 + yy


def main() -> None:
    files = {}
    for p in sorted(RAW.glob("elsec??.*")):
        fy = fiscal_year(p.stem)
        # The 2022 .txt on the Census site is truncated (1,729 rows); prefer the .xlsx.
        if fy in files and p.suffix != ".xlsx":
            continue
        files[fy] = p
    frames = []
    for fy, path in sorted(files.items()):
        df = read(path)
        df.columns = [c.strip() for c in df.columns]
        la = df[df["NCESID"].astype(str).str.strip().str.startswith("22")].copy()
        if la.empty:
            sys.exit(f"No Louisiana rows in {path.name}")
        out = pd.DataFrame({
            "fiscal_year": fy,
            "nces_leaid": la["NCESID"].str.strip(),
            "census_name": la["NAME"].str.strip(),
            "source_file": path.name,
        })
        for src, dst in COUNTS.items():
            out[dst] = pd.to_numeric(la.get(src), errors="coerce")
        for src, dst in MONEY.items():
            vals = pd.to_numeric(la[src], errors="coerce") if src in la else pd.NA
            out[dst] = vals * 1000 if src in la else pd.NA
        frames.append(out)
    allyears = pd.concat(frames, ignore_index=True)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    allyears.to_csv(OUT, index=False)
    print(f"Wrote {len(allyears)} rows, {allyears.fiscal_year.nunique()} years -> {OUT}")
    print(allyears.groupby("fiscal_year").agg(n=("nces_leaid", "size"),
                                              enr=("enrollment", "sum"),
                                              cur=("exp_current", "sum")).to_string())


if __name__ == "__main__":
    main()
