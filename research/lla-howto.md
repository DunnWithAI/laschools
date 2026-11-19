# Pulling Louisiana Legislative Auditor (LLA) audits systematically

Researched 2026-11-19. Everything below was run live that day unless marked UNVERIFIED.

## Short version

The LLA public site (https://www.lla.la.gov/, a Nuxt single-page app) is backed by two unauthenticated
JSON endpoints on the old Lotus Domino host `app.lla.la.gov`. No API key, no login, no captcha, CORS is `*`.
The "list" is scrapeable as JSON; the reports themselves are PDFs.

The old `app.lla.state.la.us/PublicReports.nsf` URLs still appear in redirects and PDF links (and in many search-engine results), so legacy hosts still resolve.

## 1. Entity list (all ~5,900 auditees)

```
GET https://app.lla.la.gov/agentcentral.nsf/getAgencyListJSON?Open
```
Returns a JSON array of `{"custname": "..."}` (5,936 entries on 2026-11-19, ~334 KB; some are empty `{}`, filter them). Saved copy: `data/raw/lla-index/agencies.json`.

A second endpoint, `https://app.lla.la.gov/getAgencyNames?Open`, returns `{custname, agencyid}` pairs (the numeric agency ID, e.g. 4137). It is used by the by-agency page to match slugs; it returns a few rows per ID (name variants). Note the shape differs by `returnNested` handling in the site JS: the raw response is `{"data":[...]}`.

Naming convention (useful for filtering):
- 69 parish and city school boards: `"<Parish> Parish School Board"`, `"City of Monroe School Board"`, `City of Baker/Bogalusa/Central/Zachary School Board`.
- `Recovery School District - LA Department of Education` (7 audits 2009-2018) and `Special School District` (0 audits listed under Audit worktype).
- Charters: `"<Parish> Parish Charter School - <Operator legal name>"` (142 entries with that prefix), e.g. `Orleans Parish Charter School - KIPP New Orleans Inc.`. The parish is the parish of the authorizer or location, not the operator's HQ. Type 2 / BESE schools are named for the parish they sit in (e.g. `East Baton Rouge Parish Charter School - IDEA Public School Louisiana Inc.`). A few charters lack the prefix (e.g. `Vermilion Charter Foundation, Inc. DBA Vermilion Charter Academy`), so also search by `Academy|Charter|Foundation`.
- Names get truncated at ~100 chars in the list (e.g. `...Foundation for Louisiana Students dba University View Acad`).

## 2. Report list for one entity

```
GET https://app.lla.la.gov/publicreports.nsf/vwPRByAgencyJSON?OpenView&Count=10000&RestrictToCategory=<URL-encoded custname>
```
Exact-match on `custname` (case/spacing sensitive; use the string from the list). Returns `{"data":[{...}]}` (empty objects are padding). Fields:

| field | meaning |
|---|---|
| `acn` | audit control number, e.g. `72251830` |
| `agency` | entity name |
| `worktype` | `Audit`, `A` (legacy), `Agreed-upon Procedures`, `Fraud`, `Other Services (w/report)`... |
| `serviceweb` | `Contracted` (CPA-done audit filed with LLA), `Financial`, `Investigative`, `Performance`, `Advisory`, ... |
| `issuedate` / `issuedatesort` | MM/DD/YYYY and YYYYMMDD (date LLA released it, not period end) |
| `period` | fiscal period, e.g. `7/1/2024 - 6/30/2025` |
| `reportlink` | stable-ish link: `https://lla.la.gov/go.nsf/get?OpenAgent&arlkey=<key>` |
| `summarylink`, `supplementlink`, `podcastlink`, `dashboardlink` | usually empty |

A school board's `Contracted` + `Audit` rows are the annual audited financial statements. Filter `worktype in {Audit, A}`; `Agreed-upon Procedures` rows are the separate state-required AUP reports (Caddo has one per year 2007-2014; later years the AUP is bundled). Investigative/fraud rows also appear.

Order is not guaranteed; sort on `issuedatesort`.

A working inventory script (loops all school board and charter names, prints count / first / last audit) is at `data/raw/lla-index/inventory-script.py`; output at `data/raw/lla-index/inv.txt`. 218 entities, ~0.3 s sleep each, took about 2 minutes. Be polite; no rate limit was hit but none is documented.

### Verified report lists

| entity | rows | audits | first audit issued | latest | notes |
|---|---|---|---|---|---|
| Orleans Parish School Board | 40 | 22 (+ investigative/advisory) | 05/2005 for audits; reports back to FY1995 (issued 2001-2004) | 05/13/2026 (FY ended 6/30/2025) | `arlkey=72251830APPP-DTZRQX` |
| KIPP New Orleans Inc. (`Orleans Parish Charter School - KIPP New Orleans Inc.`) | 20 | 20 | 02/2007 (FY2006) | 02/04/2026 (FY2025) | `arlkey=72251421APPP-DQXVB5` |
| Caddo Parish School Board | 40 | 23 + AUPs | 02/2001 (FY2000); audits listed from 01/2004 under `Audit` | 05/13/2026 (FY2025) | `arlkey=72251860APPP-DTZRQP` |

Full per-year `arlkey` lists for these three are reproducible with the curl above. The lag from fiscal year end to LLA release is roughly 7-11 months for school boards (FY ending 6/30/2025 released 02/2026 to 05/2026).

## 3. Getting the PDF

`reportlink` -> `https://lla.la.gov/go.nsf/get?OpenAgent&arlkey=...` -> HTTP 302 to `https://app.lla.la.gov/go.nsf/get?...` -> returns a tiny HTML page with a JavaScript redirect:

```
window.location.href = 'https://app.lla.state.la.us/publicreports.nsf/0/<32-hex-docid>/$file/<8hex>.pdf?openelement&.<n>'
```
So do not rely on `curl -L` alone; parse that line:

```bash
url=$(curl -sL -A "Mozilla/5.0" "https://lla.la.gov/go.nsf/get?OpenAgent&arlkey=$KEY" \
  | grep -o "window.location.href = '[^']*'" | sed "s/.*= '//;s/'$//")
curl -sL -A "Mozilla/5.0" -o out.pdf "$url"
```
All three samples returned `200 application/pdf`. Always send a browser-ish User-Agent. Files are text PDFs (pdftotext works; no OCR needed on the 2025 ones). Older (pre-2005) scans are UNVERIFIED for OCR need.

Some older reports are also reachable at `https://lla.la.gov/publicreports.nsf/0/<docid>/$file/<hex>.pdf` and `app1.lla.la.gov/PublicReports.nsf/...` (seen in search results). Treat the `arlkey` route as canonical.

## 4. How far back

Per-entity listings go back to FY1995-FY1996 for large boards (OPSB, Caddo: reports "issued" 2001 and a batch "07/01/2004" for FY1995-FY1999 backfills). Most parish boards have audits listed from 2004-2005. Charters appear from the year their first audit was filed (see the table in `charters-and-audits.md`).

## 5. Other LLA-hosted data worth knowing

- **Annual "Charter School Report"** (one PDF per year, crosswalk of every charter entity, parish, LLA agency ID, charter type 1/2/3/4/5, authorizer, schools operated, and date of the latest report): `https://app.lla.la.gov/reports-data/local-government-financials/documents/CharterSchoolReport2019.pdf` and `...Report2020.pdf` returned 200 (saved: `data/raw/lla-samples/CharterSchoolReport2020.pdf`). 2021-2025 with that file name pattern returned 404; a search result says editions through 2023 exist, so the filename or path differs (UNVERIFIED). Index page `https://lla.la.gov/reports/local-government-financial-reports` is JS-rendered; I did not extract its link list.
- **Governmental audit guide** `lla.la.gov/resources/local-government-reporting/louisiana-governmental-audit-guide/` pages 200-1130 (school boards and charters) and 300-1040 (charter reporting rules).
- Per-entity pages exist as `https://www.lla.la.gov/reports/audit-reports/by-agency/<slug>` where slug = lowercase, strip non `[\w ]`, spaces to hyphens (from the site JS). These are rendered client-side from the JSON above, so scrape the JSON, not the HTML.
- Federal single audits for charters that spend >= $750k federal are also on the Federal Audit Clearinghouse (e.g. FirstLine: $60.8M expended, latest accepted 2025-12-05, per a search snippet; not independently verified).

## 6. What is in the audits (sampled FY2025)

Text-extracted with `pdftotext -layout` (files in `data/raw/lla-samples/`, never executed):

| file | pages | schedule of compensation to agency head | expenditures by function |
|---|---|---|---|
| `opsb_FY2025.pdf` (Orleans Parish School Board) | 151 | Yes: "Schedule of Compensation, Benefits, and Other Payments to the Superintendent" p.94 (Avis Williams: salary $476,384, stipend, health, retirement, payroll taxes, travel; total $534,606). Separate schedule of board member pay. | Yes: governmental-fund and government-wide statements by function (Instruction: other instructional, instructional staff support, etc.), budget-to-actual schedules for major funds. Charter-school (pass-through) revenue is included at the OPSB level but individual charter spending is NOT here. |
| `caddo-parish-school-board_FY2025.pdf` | 224 | Yes: "Schedule of Compensation, Benefits, and Other Payments to Agency Head" (Superintendent Keith Burton) listed in contents, p.134 | Yes: statement of activities by function; fund statements; combining statements; budgetary comparison schedule. MD&A has per-function dollar tables (Regular programs, Student services...). |
| `kipp-new-orleans_FY2025.pdf` (charter, nonprofit model) | 50 | Yes: Schedule 5, p.28: CEO Rhonda Kalifey-Aluise, salary $281,000 + stipend/insurance/retirement/travel = $313,355 total | Nonprofit "Statement of Functional Expenses" (Exhibit C): Program services vs. Support services by natural line item. Also combining statement of activities by school (Schedule 4). No budget-vs-actual (nonprofit model). |

The agency-head schedule is required by R.S. 24:513(A)(3) and appears in all three. Charters on the nonprofit model give functional expenses (program/support) rather than governmental functions (instruction, student services, etc.); the LLA guide explicitly says LLA accepts either nonprofit or governmental-model reports for charters (audit guide 300-1040). Expect inconsistent formats across charters: plan for per-entity extraction.

## 7. Recommended pipeline

1. Pull `getAgencyListJSON`; filter school boards and `Charter School -` names (plus a manual list of odd names).
2. For each, call `vwPRByAgencyJSON`; keep `worktype in {Audit, A}` and `serviceweb == Contracted`; store full JSON.
3. For each `reportlink`, resolve the JS redirect and download the PDF; name by `acn`; hash and record URL. Re-run annually, since reports drop through the year (many in Jan-Feb and May).
4. Extract text with `pdftotext -layout`; locate "SCHEDULE OF COMPENSATION, BENEFITS, AND OTHER PAYMENTS" and the function-level statements. Table extraction will need per-format work (governmental vs. nonprofit).
5. Cross-check against the Charter School Report (agency ID, type, authorizer) and ProPublica 990 data.

Caveats: charters that stop filing (closed or merged) just end; renamed operators split across two LLA entity names (e.g. Choice Foundation 2008-2021 vs Better Choice Foundation 2015-2021; InspireNOLA shows only 2023+ so earlier filings may sit under a predecessor name, UNVERIFIED). One entity name (`...Advocates for Innovative Schools Inc. - ReNEW Moton`) returned non-JSON from the listing endpoint during the loop; retry it separately.
