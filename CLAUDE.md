# CLAUDE.md

**lonerna.se** — Swedish "vad tjänar ett yrke / lön efter skatt" site. One page
per SSYK occupation (SCB data) plus a take-home pay calculator. Funded by
AdSense. Static HTML, stdlib Python build, GitHub Pages. Swedish copy; English
code and commits. Sibling of ledigadagarna/hjarngympa — same plumbing.

## Why it looks the way it does
"[yrke] lön" queries have difficulty 0–15 and €1.3–3 CPC; generic "lön efter
skatt" has 150k/mo volume but €0.07 CPC. Occupation pages earn; the calculator
pulls traffic. Each page's copy is generated from its own numbers (rank,
gender gap, trend, age, region) so no two pages read alike — AdSense rejected
hjarngympa for thin content, don't regress into template prose.

## Commands
```bash
python3 -m unittest -q tools.test   # tax engine vs every row of Skatteverket's 2026 tables (Python + JS)
python3 tools/build.py              # -> dist/
python3 tools/fetch.py              # refresh SCB data (yearly), commit site/data/*.json
```

## Layout
- `tools/tax.py` — SKV 433 (teknisk beskrivning) for column 1, under 66. **`site/assets/tax.js` is a line-for-line port; change both.** The test runs both against `tools/fixtures/skattetabell-2026-kol1.json`.
- `tools/build.py` — all generated pages: `/`, `/yrken/`, `/kommunalskatt/`, `/yrke/<slug>/`. Hand-written pages in `site/pages/**` (`<!--meta -->` block).
- `site/assets/lon.js` — payslip recalculation, kommun picker (reads `/assets/data.json`, emitted by build), "where do you land" marker, table filter.
- `site/assets/app.js` — theme, ad mounting, consent reopen. Copied from ledigadagarna; same rules.

## Yearly update (each January + June)
1. January: new tax year. Update constants in `tax.py` + `tax.js` (PBB, IBB, SKIKT, any formula change in the new SKV 433), refetch the fixture (Skatteverket rowstore dataset `88320397-5c32-4c16-ae79-d36d95b17b95`, filter `år`, `tabellnr`, `antal dgr=30B`), bump `TAX_YEAR`, run `fetch.py` for the new kommunalskatt.
2. June: SCB publishes new lönestrukturstatistik → `fetch.py`, bump `YEAR` (the `*AN` tables cover 2023+).

## Rules
- Numbers are computed, never typed. Tax is exact or it's a bug — add a fixture row, not a fudge.
- Green = money you keep, rose = tax. Everywhere.
- Ads never between the H1 and the answer sentence, never inside the payslip or a table.
- Occupations without the full P10–P90 set are skipped, not half-rendered.
