# Louisiana School Dollars

How every Louisiana public school system spends its money, by parish: per student, per
resident, classrooms vs offices, teachers vs administrators, and who posts a budget online.
A sibling of nolabudget.dunn.us. First version built 2026-11-19.

Live: https://laschools.dunn.us (deploys from `main`; see [docs/deploying.md](docs/deploying.md)).
Preview: `python3 -m http.server 4322 --directory site` (or the `schoolbudgets` entry in
`.claude/launch.json`). Published draft: https://claude.ai/artifact/9btowLCojpzWreyjMamdTY

## Who counts as a "school system"

196 local education agencies (LEAs); see `research/lea-universe.csv` and `.md`.
64 parish boards, 5 city systems (Baker, Central, Zachary, Monroe, Bogalusa), about 44
state-approved (Type 2) charters, about 62 Orleans charter LEAs, 3 Baton Rouge takeover
(Type 5) charters, 2 university lab schools, 5 state-run schools. Charters inside a parish
board (Types 1, 3, 4) report through that board. The page counts charters in the parish
where their school sits, and leaves online and state-run schools out of parish totals.

## Data sources and how far back they go

| Source | Years | Covers | Used for |
|---|---|---|---|
| LDOE Annual Financial Report (AFR), `data/raw/ldoe/afr-data` | FY2007-FY2025 (charters from FY2009; FY2012-14 Access only; FY2025 lost its Object column) | Every LEA, by function, object, fund | 2023-24 snapshot |
| LDOE enrollment multi-stats | Oct 2006-Feb 2026 | Every site | Per-student figures |
| Census F-33, `data/raw/census-f33` | FY1992-FY2024 (FY1999 missing) | 69 parish/city systems + RSD; charters out of scope | 1992-2024 trend, cross-check |
| Census population estimates | 2020-2024 | Parishes | Per resident |
| District websites, `research/district-budgets.csv` | varies | 69 boards: 44 post a budget, 25 not found | Who publishes |
| Legislative Auditor audits, `research/lla-howto.md` | ~2005 on | Boards and ~140 charters | Not yet used |

More LDOE sets (per-pupil School Finder, MFP letters, staff FTE, 70% instructional
requirement, teacher salaries) are listed in `research/ldoe-data.md`.

## Pipeline

    scripts/extract_f33.py      Census files -> data/extracted/f33_louisiana.csv
    scripts/build_snapshot.py   AFR + enrollment + population -> data/combined/{lea,parish}_2023_24.csv
    scripts/build_trends.py     F-33 + CPI -> data/combined/trend_f33*.csv (2024 dollars)
    scripts/build_page_data.py  everything above + map shapes -> site/data.json

    .venv/bin/python -I scripts/build_snapshot.py \
      --afr "data/interim/afr2324/2023-2024 AFR Web/AFR - 2 Expenditure.xlsb" \
      --enrollment "data/raw/ldoe/enrollment-multi-stats/oct-2023-multi-stats-(total-by-site-and-school-system)_web.xlsx" \
      --school-year 2023-24 --pop-year 2023

`data/raw/` is not in git (about 1 GB); each folder's README or `manifest.csv` has the URLs.

## Definitions and checks

- Day-to-day spending = AFR functions 1000-3999, minus tuition paid to other LEAs
  (objects 561-569). Leaves out construction, debt and transfers (incl. OPSB pass-through
  to charters), so nothing is counted twice. LEA code 999 is a statewide totals row: dropped.
- Teacher pay = object 112; administrator pay = object 111. Salaries only.
- Check: for all 70 parish/city systems, AFR 2023-24 day-to-day spending is within 5% of
  Census F-33 FY2024 current spending (median +1.2%).

## Known gaps

- Only one AFR year (2023-24) is processed; the AFR history back to FY2009 with charters
  is downloaded but not extracted.
- Census statewide trend drops about $1,300 per student between FY2012 and FY2013; not yet explained.
- Budget survey: 7 district sites block automated visits; "not found" is not proof of none.
- Charter type definitions and some history in `research/lea-universe.md` were written
  from memory by a research agent; check before publishing.
