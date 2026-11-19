# ABOUTME: Builds the 1992-2024 per-student spending trend for each parish/city school
# ABOUTME: system from the Census F-33 extract, adjusted to 2024-25 dollars with CPI-U.
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
BASE_FY = 2025
# After Hurricane Katrina most New Orleans schools became charters, which Census leaves out
# of scope, so Orleans figures stop being comparable after FY2005. The RSD is all charters.
CUTOFF = {"2201170": 2005}
DROP = {"2200054"}


def fiscal_year_cpi() -> pd.Series:
    cpi = pd.read_csv(ROOT / "data" / "raw" / "bls" / "CPIAUCSL.csv", parse_dates=["observation_date"])
    d = cpi.observation_date
    # Louisiana school fiscal years run July to June: FY2024 = Jul 2023 - Jun 2024.
    cpi["fy"] = d.dt.year + (d.dt.month >= 7).astype(int)
    return cpi.groupby("fy").CPIAUCSL.mean()


def main() -> None:
    f = pd.read_csv(ROOT / "data" / "extracted" / "f33_louisiana.csv", dtype={"nces_leaid": str})
    f = f[~f.nces_leaid.isin(DROP)].copy()
    for leaid, last in CUTOFF.items():
        f = f[~((f.nces_leaid == leaid) & (f.fiscal_year > last))]
    cpi = fiscal_year_cpi()
    f["to_base"] = cpi[BASE_FY] / f.fiscal_year.map(cpi)
    uni = pd.read_csv(ROOT / "research" / "lea-universe.csv", dtype=str)[["nces_leaid", "lea_code"]]
    f = f.merge(uni, on="nces_leaid", how="left")
    f["per_student_real"] = f.exp_current / f.enrollment * f.to_base
    f["instruction_share"] = f.exp_instruction / f.exp_current
    out = f[["lea_code", "nces_leaid", "census_name", "fiscal_year", "enrollment",
             "exp_current", "per_student_real", "instruction_share"]]
    if out.lea_code.isna().any():
        raise SystemExit(f"No LDOE code for: {out[out.lea_code.isna()].census_name.unique()}")
    state = f.groupby("fiscal_year").agg(exp=("exp_current", "sum"), enr=("enrollment", "sum"),
                                         to_base=("to_base", "first"))
    state["per_student_real"] = state.exp / state.enr * state.to_base
    out.to_csv(ROOT / "data" / "combined" / "trend_f33.csv", index=False)
    state.reset_index().to_csv(ROOT / "data" / "combined" / "trend_f33_state.csv", index=False)
    print(state.per_student_real.round(0).to_string())


if __name__ == "__main__":
    main()
