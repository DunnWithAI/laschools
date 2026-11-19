# Louisiana School Dollars

How every Louisiana public school system spends its money, by parish: per student, per
resident, classrooms vs offices, teachers vs administrators, and who posts a budget online.
A sibling of nolabudget.dunn.us. First version built 2026-11-19.

Live: https://laschools.dunn.us (deploys from `main`; see [docs/deploying.md](docs/deploying.md)).
Preview: `python3 -m http.server 4322 --directory site` (or the `schoolbudgets` entry in
`.claude/launch.json`).

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
| LDOE Annual Financial Report (AFR), `data/raw/ldoe/afr-data` | 2006-07 to 2024-25 (charters from 2008-09; 2011-12 to 2013-14 Access only; 2024-25 lost its Object column) | Every LEA, by function, object, fund | Every figure on the page, 2008-09 to 2024-25 |
| LDOE enrollment multi-stats | Oct 2006-Feb 2026 | Every site | Per-student figures (each October) |
| Census F-33, `data/raw/census-f33` | FY1992-FY2024 (FY1999 missing) | 69 parish/city systems + RSD; charters out of scope | 1992-2024 "longer view", cross-check |
| Census population estimates | 2008-2024 | Parishes | Per resident |
| NCES school directory (via Urban Institute), `data/raw/ccd-directory` | 2008-2024 | Every school, with parish | Placing charters in a parish |
| District websites, `research/district-budgets.csv` | varies | 69 boards: 44 post a budget, 25 not found | Who publishes |
| Legislative Auditor audits, `research/lla-howto.md` | ~2005 on | Boards and ~140 charters | Not yet used |

More LDOE sets (per-pupil School Finder, MFP letters, staff FTE, 70% instructional
requirement, teacher salaries) are listed in `research/ldoe-data.md`.

## Pipeline

    scripts/extract_f33.py      Census files -> data/extracted/f33_louisiana.csv
    scripts/extract_afr.py      AFR zips (unzipped to data/interim/afr, Access years exported
                                to data/interim/afr-access) -> data/interim/afr-normalized/
    scripts/build_history.py    normalized AFR + enrollment + directory + population
                                -> data/combined/{lea,parish}_years.csv, coverage_gaps.csv
    scripts/build_trends.py     F-33 + CPI -> data/combined/trend_f33*.csv (2024-25 dollars)
    scripts/build_page_data.py  everything above + map shapes -> site/data.json
                                (also stamps the page's "Updated" date when the data changes)

`data/raw/` and `data/interim/` are not in git (several GB); each raw folder's README or
`manifest.csv` has the URLs. The Access years were exported with the `access-parser`
package (see `extract_afr.py` for the table names).

## Definitions and checks

- Day-to-day spending = AFR functions 1000-3999, minus tuition paid to other LEAs
  (objects 561-569). Leaves out construction, debt and transfers (incl. OPSB pass-through
  to charters), so nothing is counted twice. State-total rows (codes 999...) are dropped.
- Teacher pay = object 112; administrator pay = object 111. Salaries only. 2024-25 has no
  Object column; it is filled in by line item (KeyPchCd) from earlier years. No line item
  changed its object code between 2017-18 and 2023-24 (2,335 compared).
- Each school's students go to the system that reports its spending: by site code, then,
  where a year codes a school differently in the two files (2015-16), by school name.
- Charters are placed in a parish by the NCES directory; `data/crosswalk/site_parish_overrides.csv`
  fixes the two schools the directory gets wrong.
- Check: for every parish/city system in every year 2008-09 to 2023-24, AFR day-to-day
  spending is within 11% of Census F-33 current spending (median about +1%), except
  FY2012, when Census runs 15-28% high for about ten systems and falls back the next year.
  That Census bump is also why its statewide trend dips from FY2012 to FY2013.

## Known gaps

- Students at a few state-run special schools (under 1,600 a year) have no spending in the
  AFR and are left out (`data/combined/coverage_gaps.csv`).
- Budget survey: 7 district sites block automated visits; "not found" is not proof of none.
- Charter type definitions and some history in `research/lea-universe.md` were written
  from memory by a research agent; check before publishing.
