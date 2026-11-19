# Raw LEA source files (untrusted downloads; never execute)

Downloaded 2026-11-19 with curl. Read them only with `python -I` from a different working directory.

| File | URL | What it is |
|---|---|---|
| `ldoe_multistats_feb2026.xlsx` | https://doe.louisiana.gov/docs/default-source/fiscal-data/feb-2026-multi-stats-(total-by-site-and-school-system)-web.xlsx?sfvrsn=a43aa9ee_5 | LDOE Feb 1, 2026 Multiple Statistics. Sheet "Total by School System" (80 reporting entities + state total) and "Total by Site" (~1,330 sites; includes Charter Type, Roll Up Type, Physical Parish, nonprofit operator, SIS and federal site codes). |
| `ldoe_multistats_oct2025.xlsx` | https://doe.louisiana.gov/docs/default-source/fiscal-data/oct-2025-multi-stats-(total-by-site-and-school-system)-web.xlsx?sfvrsn=3b25b78c_5 | Same report for Oct 1, 2025; used to check which sites disappeared. |
| `ldoe_enrollment_data_page.html` | https://doe.louisiana.gov/data-and-reports/enrollment-data | LDOE page listing every multi-stats file back to 2013 (link source). Older files not downloaded. |
| `nces_2425/ccd_lea_029_2425_w_1a_073025.csv` (inside `ccd_lea_029_2425.zip`) | https://nces.ed.gov/ccd/Data/zip/ccd_lea_029_2425_w_1a_073025.zip | NCES Common Core of Data, LEA Universe (directory) 2024-25, national; Louisiana = ST=="LA", 194 rows. Has NCES LEAID, ST_LEAID, type, status, website. No enrollment column. |

Not obtained: the NCES CCD LEA membership file (https://nces.ed.gov/ccd/Data/zip/ccd_lea_052_2425_l_1a_073025.zip, ~37 MB) - the download was cut off by a timeout and the partial file was deleted. LDOE Feb 2026 counts were used for enrollment instead.
The ccd file URLs were guessed from NCES naming conventions (https://nces.ed.gov/ccd/files.asp builds its links with JavaScript); the zip downloaded and parsed fine.
