# Louisiana LEA universe

Built from LDOE Multiple Statistics (Feb 1, 2026) joined to the NCES CCD LEA directory (2024-25). Files and URLs: `data/raw/lea/README.md`. Table: `research/lea-universe.csv` (196 rows; one row per LEA).
Facts below come from those two files unless marked "background" (from memory, not verified here).

## Counts (rows in the CSV)

| lea_type | rows | enrollment (Feb 2026) | notes |
|---|---|---|---|
| parish_system | 64 | 557,526 | codes 001-064. Includes each parish's own Type 1/3/4 charters (see traps). |
| city_system | 5 | 20,379 | 065 Monroe, 066 Bogalusa, 067 Zachary, 068 Baker, 069 Central |
| charter_type2 | 44 open (+3 likely closed) | 36,673 | BESE-authorized, each its own LEA, 44 sites |
| charter_local | 62 open (+5 closed) | ~40,900 | New Orleans charter LEAs authorized by Orleans Parish School Board (OPSB): Types 1, 3, 3B. Nothing outside Orleans is a separate LEA. |
| charter_rsd | 3 | 902 | Type 5, Baton Rouge (Lanier, Dalton, Prescott) |
| rsd | 1 | 742 | LDOE code WYC / NCES LA-396 "Recovery School District-LDE" = Linwood Public Charter (Caddo), Type 5 |
| lab_school | 2 | 2,060 | LSU Lab (318), Southern Lab (319) |
| state_special | 5 | 1,145 | Special School District 101, LSMSA 302, NOCCA 334, Thrive Academy 3C1, Office of Juvenile Justice A02 |
| other | 2 | 54 | Ecole Pointe-au-Chien 3C9; Howard School 307 (NCES-only, unverified) |

Currently operating: 187 open + 1 unverified. NCES-only and flagged: 5 closed in NCES 2024-25 (all charters), 3 "likely_closed" (Noble Minds W18, Southwest Louisiana Charter Academy WAK, Voices for International Business 344: open in NCES 2024-25, absent from LDOE Oct 2025 and Feb 2026 lists - not confirmed by a news source; my web search failed on credits). Howard School (307): an NCES LEA with no LDOE counterpart; a "Howard School" site exists under Lincoln Parish in LDOE.
Rows in CSV: 196 = 187 open + 5 closed + 3 likely_closed + 1 unverified.
Check: LDOE statewide enrollment 660,349 (Feb 1, 2026).

## How LDOE codes them (this is the main trap)

LDOE's public reports roll sites up into only 79 "school systems", which is not the same as legal LEAs:
- 001-064: parish systems, alphabetical (Orleans is 036 in site codes, but LDOE's report calls it **R36**).
- 065-069: city systems.
- **CHA** = "Type 2 Charters" bucket: all 44 BESE charter sites in one line (36,673 students). The real LEA code is the first three characters of each site code (321, 329, 331, ... W1A, WAG ...).
- **R36** = Orleans Parish incl. every OPSB-authorized charter (43,182 students, 67 sites). Only 3 sites (866 students) are directly run by OPSB; the rest are charters.
- **RBR** = RSD Baton Rouge (3 Type 5 sites), **WYC** = RSD-LDE (Linwood).
- 101, 302, 318, 319, 334, 3C1, 3C9, A02: separate lines.
Charter LEA code = first 3 characters of the "SIS Submit Site Code" (e.g. 369001). For many New Orleans charters NCES instead uses the "Federal Reporting Site Code" prefix (369001 -> W Z 2 = LA-WZ2). The CSV `lea_code` uses the NCES ST_LEAID suffix so the two sources join; `ldoe_sis_prefix` keeps the LDOE one. Operators with several schools (KIPP New Orleans 7+ sites, FirstLine, ReNEW, Collegiate Academies) are one LDOE operator code but several NCES LEAs; the CSV follows NCES (one row per federal LEA id, `operator` column groups them). 89 distinct nonprofit operators run the 144 charter sites.
Statewide: 144 charter sites, 99,190 students = 15.0% of enrollment (Type 1: 51 sites/27,361; Type 2: 44/36,673; Type 3: 15/13,492; Type 3B: 29/19,613; Type 4: 1/407; Type 5: 4/1,644).

## Charter types in plain words (background; legal definitions are in R.S. 17:3973 - verify before publishing)
- **Type 1**: new charter approved by the local school board; operated by a nonprofit.
- **Type 2**: new charter approved by BESE (state board); funded directly through the state formula; its own LEA.
- **Type 3**: an existing school converted to a charter by the local board, usually run by a nonprofit.
- **Type 3B**: Type 3 charter that was a school taken over by the Recovery School District and later returned to the local board. All 29 are in New Orleans, authorized by OPSB.
- **Type 4**: charter run by the local school board itself (only one: LA School for Ag Science, Avoyelles).
- **Type 5**: charter operating a school that was transferred to the RSD. Today only 4 sites remain (3 Baton Rouge, 1 Caddo).
Important: in the data, Type 3B is legally OPSB, so I coded them `charter_local`, not `charter_rsd`. Only Type 5 is `charter_rsd`.

## Who is in the 69, who is not
The 69 "city/parish" systems check out: 64 parish + 5 city (the earlier note about a separate "Baker" and "City of Baker" is one system, 068). Their charters (Types 1, 3, 4) are rolled into the parent system, are not separate LEAs in NCES, and total 20,005 students (including 1,448 in OPSB's own Type 3 schools): East Baton Rouge 6,046; Jefferson 6,296; Caddo 2,211; Morehouse 1,038; Lafourche 984; St. Landry 751; Union 446; Avoyelles 407; East Feliciana 378.

## Enrollment distribution (Feb 1, 2026, total 660,349)
- Non-charter students: 561,285 = 85.0%; of which 557,160 are in the 69 systems' traditional schools.
- Charter students: 99,190 = 15.0%: 36,673 Type 2 (5.6%); 42,316 in New Orleans OPSB charters (6.4%), 18,557 in Types 1/3/4 inside other parish systems (2.8%); 1,644 Type 5.
- 69 systems including their own charters: 577,905 (87.5%); Orleans in that figure is only 2,314 (its 036 own sites).
- All of New Orleans (geographic parish): 43,182 students, 98% in charters.
- Parish systems: median 4,583; smallest Tensas 312; largest Jefferson 45,406; 10 over 20,000; 15 under 2,000.

## Traps
1. **Orleans**: R36 (LDOE report), 036 (site code), LA-036 (NCES). NCES lists Orleans Parish as 6 schools; LDOE R36 is 67 sites. `enrollment` for 036 in the CSV is its own sites only; add the charter LEA rows to get all of New Orleans.
2. **Parish sums**: site-level sums differ from LDOE's system sheet for East Baton Rouge (+42), Jefferson (+25), Tangipahoa (+59): extra tiny early-childhood sites with odd codes (KNW001, KQP001, KA6001 ...). The CSV uses the system sheet.
3. **RSD**: today's RSD is essentially 4 Type 5 schools. LDOE/NCES lump Linwood as "RSD-LDE" (LDOE WYC, NCES LA-396); the others are charter LEAs under "RBR". Background: RSD took over most New Orleans schools after Katrina, and the schools went back to OPSB over time (mostly by 2018); that explains the many "Type 3B".
4. **NCES vs LDOE mismatches**: NCES has Howard School (307), Voices (344), Noble Minds (W18), SW Louisiana Charter Academy (WAK) not in LDOE Feb 2026; LDOE has three new charters absent from NCES 2024-25: Northshore Charter (WZZ), Elan Academy (WZY) and Vermilion (LDOE WZW = NCES 3D1, status "New"). NCES names are often renamed (e.g. "The MAX Charter School" = LDOE "Maxine Giardina").
5. **LDOE changed the file location/format**: current files sit under `fiscal-data` (2025-26), older under `data-management`; 2016 and before were split "by LEA" and "by site" and had different column names.
6. **Name drift**: `lea_code` can change when a school moves operators; LDOE has used 3-character prefixes that are not stable across years. For time series match on NCES LEAID + name, or on site code.
7. **City systems and parish geography**: city systems sit inside a parish (Monroe -> Ouachita, Bogalusa -> Washington, Zachary/Baker/Central -> East Baton Rouge). Background (unverified): Zachary 2003, Central 2007 (city systems that split off EBR), Baker 2004-ish. A parish map polygon therefore has one parish system plus 0-3 city systems overlapping it; Ouachita/Washington/EBR have extras.
8. **Special entities**: SSD 101 serves state-run sites in many parishes (Pinecrest, Dixon prison, etc.), and OJJ (A02) is multi-parish; `parish` is "statewide (multiple)".
9. The 3 likely_closed rows and Howard School are unverified; the 5 NCES closed rows have no enrollment.

## Recommendation for a "find your parish" map
- Show 64 parish polygons; roll every LEA into its **geographic parish** (`parish` column) so that each polygon lists: parish system (+ its inside charters), city system(s) overlapping the parish, and Type 2 charters physically located there.
- Keep LEAs separate in the table/details (e.g. East Baton Rouge: EBR Parish, Zachary, Baker, Central, plus the Type 2 charters located in Baton Rouge, plus RSD Type 5).
- Define "every school district" as: 69 city/parish systems + Type 2 charter LEAs + OPSB charter LEAs + RSD/Type 5 + lab + state special entities. For spending comparisons a user will probably care about the 69; show charters as a separate layer and always show Orleans as a combined "all New Orleans schools" figure (OPSB + 62 charter LEAs).
- Orleans needs a special case: its 036 own-site numbers are tiny; compare it using the geographic parish total.
- Use NCES LEAID as the permanent key; carry LDOE code as an attribute.

## Known gaps
- `website` is empty for every row: the NCES 2024-25 file has no website values for Louisiana, and LDOE's multi-stats files have none. Needs a separate pass (LDOE school-system directory).
- NCES CCD enrollment was not used (membership download failed); all enrollment is LDOE Feb 1, 2026.
- Closed/likely-closed status for 8 NCES-only rows is from file absence, not news confirmation.
