"""python3 -m unittest -q tools.test"""
import json, os, shutil, subprocess, unittest
from tools import tax

HERE = os.path.dirname(os.path.abspath(__file__))
FIX = json.load(open(os.path.join(HERE, "fixtures", "skattetabell-2026-kol1.json")))


class Tax(unittest.TestCase):
    def test_matches_skatteverket_tables(self):
        # Every monthly band up to 80 000 kr, tables 29/32/34/37/42, column 1.
        for t, rows in FIX.items():
            for lo, hi, want in rows:
                self.assertEqual(tax.table_withholding(hi, int(t)), want, f"table {t} band {lo}-{hi}")

    def test_skv433_worked_examples(self):
        self.assertEqual(tax.grundavdrag(120_000), 37_400)
        self.assertEqual(tax.grundavdrag(324_000), 31_600)
        self.assertEqual(tax.jobbskatteavdrag(90_000, 31_400, 0.3284), 11_976)
        self.assertEqual(tax.jobbskatteavdrag(240_000, 40_000, 0.3284), 26_083)
        self.assertEqual(tax.pensionsavgift(181_200), 12_700)
        self.assertEqual(tax.pensionsavgift(10_000_000), 47_100)
        self.assertEqual(tax.annual(28_000, 0.3284, 0.0116)["skatt"], 2_062)
        self.assertEqual(tax.annual(55_000, 0.3284, 0.0116)["skatt"], 4_445)

    @unittest.skipUnless(shutil.which("node"), "node not installed")
    def test_js_port_matches(self):
        js = os.path.join(os.path.dirname(HERE), "site", "assets", "tax.js")
        script = f"""const T=require({json.dumps(js)});const F={json.dumps(FIX)};let bad=[];
for(const t in F)for(const [lo,hi,w] of F[t]){{const g=T.tableWithholding(hi,+t);if(g!==w)bad.push([t,hi,w,g]);}}
console.log(JSON.stringify(bad.slice(0,5)))"""
        out = subprocess.run(["node", "-e", script], capture_output=True, text=True, check=True).stdout.strip()
        self.assertEqual(out, "[]")
        # and odd salaries / real kommun rates agree with Python
        for s in (9_000, 31_234, 57_890, 95_000, 250_000):
            got = subprocess.run(["node", "-e", f"console.log(require({json.dumps(js)}).monthlyNet({s},32.42,0.29,1.05).tax)"],
                                 capture_output=True, text=True, check=True).stdout.strip()
            self.assertEqual(int(got), tax.monthly_net(s, 32.42, 0.29, 1.05)[1], s)


class EverydayTitles(unittest.TestCase):
    """SITE-65: occupation pages lead with the title people search for, never an invented one."""

    @classmethod
    def setUpClass(cls):
        from tools import build as B
        cls.B = B
        cls.pages = {p["route"]: p for p in (B.page_occ(o) for o in B.OCC)}

    def test_every_title_comes_from_scb(self):
        from tools.titles import TITLES, GROUP
        B = self.B
        for code, t in TITLES.items():
            self.assertIn(code, B.BY_CODE, f"{code} has no occupation page")
            for title, src in [t["lead"]] + t["alts"]:
                if src == GROUP:
                    self.assertIn(title.lower(), B.BY_CODE[code]["name"].lower(), f"{code} {title}")
                else:
                    self.assertIn(src, B.SSYK_TITLES[code], f"{code} {title}: {src!r} is not in SCB's index for this code")

    def test_mapped_page_leads_with_the_searched_title(self):
        p = self.pages["/yrke/informatorer-kommunikatorer-och-pr-specialister/"]
        self.assertRegex(p["title"], r"^PR-specialist lön 2026: [\d\s]+kr \(kommunikatör, informatör\)$")
        self.assertIn("<h1>Lön för PR-specialister och kommunikatörer</h1>", p["body"])
        self.assertTrue(p["desc"].startswith("PR-specialist lön"))
        self.assertIn("Siffrorna gäller SCB:s yrkesgrupp Informatörer, kommunikatörer och PR-specialister (SSYK 2432).", p["body"])
        self.assertIn('<h2 id="titlar">Vanliga titlar</h2><ul class="titlar"><li>PR-specialist</li><li>kommunikatör</li>', p["body"])

    def test_unmapped_page_keeps_its_wording_but_gets_titles(self):
        from tools.titles import TITLES
        o = next(o for o in self.B.OCC if o["code"] not in TITLES and self.B.SSYK_TITLES.get(o["code"]) and o["slug"] not in self.B.QUESTION_SLUGS)
        p = self.pages[f"/yrke/{o['slug']}/"]
        self.assertTrue(p["title"].startswith(o["name"][:20]), p["title"])
        self.assertIn(f"<h1>Lön för {self.B.esc(self.B.lower_first(o['name']))}</h1>", p["body"])
        self.assertIn('id="titlar"', p["body"])
        self.assertIn(f"(SSYK {o['code']})", p["body"])

    def test_question_page_keeps_its_framing(self):
        p = self.pages["/yrke/fastighetsforvaltare/"]
        self.assertTrue(p["title"].startswith("Hur mycket tjänar en fastighetsförvaltare?"))
        self.assertIn("<li>vicevärd</li>", p["body"])

    def test_urls_unchanged_and_limits_kept(self):
        for o in self.B.OCC:
            self.assertIn(f"/yrke/{self.B.slugify(o['name'])}/", self.pages)
        for r, p in self.pages.items():
            self.assertLessEqual(len(p["title"]), 70, r)
            self.assertLessEqual(len(p["desc"]), 160, r)
        self.assertEqual(len(self.pages), len(self.B.OCC))


if __name__ == "__main__":
    unittest.main()
