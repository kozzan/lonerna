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


if __name__ == "__main__":
    unittest.main()
