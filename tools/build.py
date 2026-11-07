#!/usr/bin/env python3
"""Render the site into dist/.

    python3 tools/build.py

Data: site/data/yrken.json + kommuner.json (tools/fetch.py, from SCB). Tax:
tools/tax.py (SKV 433, verified against Skatteverket's tables). Every number on
a page is computed here; copy is generated from the numbers so each occupation
page says something no other page says.

ponytail: f-strings, no template engine, same plumbing as ledigadagarna.
"""
import os, re, shutil, html as H, json, datetime as dt, sys, unicodedata
from string import Template

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools import tax

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE, DIST = os.path.join(ROOT, "site"), os.path.join(ROOT, "dist")
BASE_URL = os.environ.get("BASE_URL") or "https://lonerna.se"
BASE_PATH = (os.environ.get("BASE_PATH") or "").rstrip("/")
CNAME = os.environ.get("CNAME") or "lonerna.se"
SITE_NAME = "Lönerna"
META_RE = re.compile(r"^<!--meta\s*(.*?)-->\s*", re.S)
ADS_CLIENT = "ca-pub-2838730195714407"   # same AdSense account as hjärngympa / ledigadagarna
ADS_SLOT = "4551546102"                 # TODO: create a slot for this site once approved
AD_RE = re.compile(r'<div class="ad ([^"]*)">[^<]*</div>')

YEAR = "2025"          # latest SCB measurement (published June 2026)
TAX_YEAR = 2026
TODAY = dt.date.today()
esc = H.escape

OCC_RAW = json.load(open(os.path.join(SITE, "data/yrken.json"), encoding="utf-8"))
KOM_RAW = json.load(open(os.path.join(SITE, "data/kommuner.json"), encoding="utf-8"))
RIKET = KOM_RAW["00"]                 # average kommunalskatt + burial fee
DEF_RATE, DEF_BURIAL = RIKET["rate"], RIKET["burial"]
KOMMUNER = sorted(({"code": c, "name": v["name"], "rate": v["rate"], "burial": KOM_RAW[c[:2]]["burial"],
                    "church": KOM_RAW[c[:2]]["church"] - KOM_RAW[c[:2]]["burial"]}
                   for c, v in KOM_RAW.items() if len(c) == 4), key=lambda k: k["name"])

SECTORS = {"public": "Offentlig sektor", "private": "Privat sektor", "state": "Staten", "municipal": "Kommuner", "region": "Regioner"}
PCT = [("p10", "10 %"), ("p25", "25 %"), ("p50", "Median"), ("p75", "75 %"), ("p90", "90 %")]


# ------------------------------------------------------------------ helpers
def kr(n): return f"{round(n):,}".replace(",", " ") + " kr"
def num(n): return f"{round(n):,}".replace(",", " ")
def pct(x, d=0): return f"{x:.{d}f}".replace(".", ",") + " %"
def net(gross): return tax.monthly_net(gross, DEF_RATE, DEF_BURIAL)[0]


def slugify(s):
    s = s.lower().replace("å", "a").replace("ä", "a").replace("ö", "o")
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")


def lower_first(s):
    """'Poliser' -> 'poliser', but leave 'IT-arkitekter' alone."""
    return s[0].lower() + s[1:] if len(s) > 1 and not s[1].isupper() else s


def jsonld(obj):
    return f'<script type="application/ld+json">{json.dumps(obj, ensure_ascii=False)}</script>'


def faq_ld(pairs):
    return jsonld({"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
        {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in pairs]})


def faq_html(pairs):
    return '<section class="faq"><h2>Vanliga frågor</h2>' + "".join(f"<h3>{esc(q)}</h3><p>{esc(a)}</p>" for q, a in pairs) + "</section>"


def crumb(*parts):
    items = [("/", "Lönerna")] + list(parts)
    ld = jsonld({"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": i + 1, "name": n, "item": BASE_URL + BASE_PATH + u} for i, (u, n) in enumerate(items)]})
    links = " / ".join(f'<a href="{u}">{esc(n)}</a>' for u, n in items[:-1])
    return f'<p class="crumb">{links} / <span>{esc(items[-1][1])}</span></p>', ld


def mount_ads(page):
    """Fixed-size <ins>, never data-ad-format=auto (it grows the slot and shifts the page)."""
    def rep(m):
        w, h = re.search(r"ad-(\d+)x(\d+)", m.group(1)).groups()
        return (f'<div class="ad {m.group(1)}"><ins class="adsbygoogle" style="display:inline-block;width:{w}px;height:{h}px"'
                f' data-ad-client="{ADS_CLIENT}" data-ad-slot="{ADS_SLOT}"></ins></div>')
    return AD_RE.sub(rep, page)


AD_TOP = '<div class="ad ad-728x90 desktop-ad">Annons</div><div class="ad ad-320x100 mobile-ad">Annons</div>'
AD_MID = '<div class="ad ad-336x280 desktop-ad">Annons</div><div class="ad ad-300x250 mobile-ad">Annons</div>'


# ------------------------------------------------------------------ data
def build_occupations():
    occ = []
    for code, o in OCC_RAW.items():
        y = o["years"].get(YEAR, {})
        d = y.get("all", {}).get("all", {})
        # ponytail: 28 occupations (mostly chef levels) lack suppressed percentiles; skip rather than half-render
        if code == "0000" or not all(d.get(k) for k in ("p10", "p25", "p50", "p75", "p90", "mean")): continue
        occ.append({"code": code, "name": o["name"], "slug": slugify(o["name"]), "d": d, "raw": o, "y": y})
    occ.sort(key=lambda o: -o["d"]["p50"])
    for i, o in enumerate(occ): o["rank"] = i + 1
    slugs = [o["slug"] for o in occ]
    assert len(slugs) == len(set(slugs)), "slug collision"
    return occ


OCC = build_occupations()
ALL = OCC_RAW["0000"]["years"][YEAR]["all"]["all"]   # every employee in Sweden
BY_CODE = {o["code"]: o for o in OCC}


# ------------------------------------------------------------------ components
def slip(gross, title, editable_label="Månadslön före skatt"):
    """The payslip: server-rendered with the national average rate, recomputed client-side
    when the reader picks a kommun or types a salary (site/assets/lon.js)."""
    a = tax.annual(gross * 12, DEF_RATE / 100, DEF_BURIAL / 100)
    t = a["skatt"] // 12
    m = lambda k: kr(a[k] / 12)
    red = (a["red_pension"] + a["jobbskatteavdrag"] + a["red_forvarvsinkomst"]) / 12
    return f"""<section class="slip" data-slip data-rate="{DEF_RATE}" data-burial="{DEF_BURIAL}" data-church="{RIKET['church'] - DEF_BURIAL:.2f}" aria-label="{esc(title)}">
<div class="slip-head"><h2 class="slip-title">{esc(title)}</h2>
<label class="field"><span>{editable_label}</span><input data-gross inputmode="numeric" autocomplete="off" value="{gross}" aria-describedby="slip-note"></label>
<label class="field"><span>Kommun</span><select data-kommun><option value="">Genomsnitt, {pct(DEF_RATE, 2)}</option></select></label>
<label class="check"><input type="checkbox" data-church> Medlem i Svenska kyrkan</label></div>
<table class="slip-rows"><tbody>
<tr><th scope="row">Bruttolön</th><td data-k="brutto">{kr(gross)}</td></tr>
<tr><th scope="row">Kommunalskatt</th><td class="minus" data-k="kommunal">−{m("kommunal")}</td></tr>
<tr data-row="statlig"{"" if a["statlig"] else " hidden"}><th scope="row">Statlig skatt</th><td class="minus" data-k="statlig">−{m("statlig")}</td></tr>
<tr><th scope="row">Allmän pensionsavgift, 7&nbsp;%</th><td class="minus" data-k="pensionsavgift">−{m("pensionsavgift")}</td></tr>
<tr><th scope="row">Jobbskatteavdrag och andra skattereduktioner</th><td class="plus" data-k="red">+{kr(red)}</td></tr>
<tr><th scope="row">Begravningsavgift och public service</th><td class="minus" data-k="avg">−{kr((a["avgifter"] + a["public_service"]) / 12)}</td></tr>
<tr class="sum"><th scope="row">Skatt per månad</th><td data-k="skatt">−{kr(t)}</td></tr>
</tbody></table>
<p class="net"><span>Kvar efter skatt</span><b data-k="net">{kr(gross - t)}</b></p>
<p class="small" id="slip-note">Skatteverkets beräkningsregler för {TAX_YEAR}, under 66 år, utan andra inkomster eller avdrag. Skatten blir <span data-k="eff">{pct(t / gross * 100, 1)}</span> av lönen.</p>
</section>"""


def band(o):
    """P10-P90 spread with the reader's own salary as a marker (moved by lon.js)."""
    d = o["d"]; lo, hi = d["p10"] * 0.85, d["p90"] * 1.08
    pos = lambda v: f"{(v - lo) / (hi - lo) * 100:.2f}%"
    pts = json.dumps({k: d[k] for k, _ in PCT})
    ticks = "".join(f'<span class="tick {k}" style="left:{pos(d[k])}"><b>{num(d[k])}</b><i>{lbl}</i></span>' for k, lbl in PCT)
    nl = esc(lower_first(o["name"]))
    return f"""<section class="check-pay" aria-labelledby="check-h"><h2 id="check-h">Är din lön rimlig?</h2>
<label class="field you-field"><span>Din månadslön före skatt</span><input data-you inputmode="numeric" autocomplete="off" placeholder="Till exempel {num(d['p50'])}"></label>
<figure class="band" data-band='{pts}' data-lo="{lo:.0f}" data-hi="{hi:.0f}" data-name="{nl}">
<div class="track" aria-hidden="true"><span class="outer" style="left:{pos(d['p10'])};right:calc(100% - {pos(d['p90'])})"></span>
<span class="inner" style="left:{pos(d['p25'])};right:calc(100% - {pos(d['p75'])})"></span><span class="you" hidden></span></div>
<div class="ticks">{ticks}</div>
<figcaption data-you-text aria-live="polite">Hälften av alla {nl} tjänar mellan {kr(d['p25'])} och {kr(d['p75'])}. Var tionde tjänar under {kr(d['p10'])} och var tionde över {kr(d['p90'])}.</figcaption>
</figure></section>"""


def trend_svg(points):
    """points: [(year, value)]. Plain inline SVG polyline, no library."""
    if len(points) < 3: return ""
    ys = [v for _, v in points]; lo, hi = min(ys) * 0.95, max(ys) * 1.02
    W, Hh, P = 480, 170, 30
    x = lambda i: P + i * (W - 2 * P) / (len(points) - 1)
    y = lambda v: Hh - 22 - (v - lo) / (hi - lo) * (Hh - 44)
    line = " ".join(f"{x(i):.1f},{y(v):.1f}" for i, (_, v) in enumerate(points))
    labels = "".join(f'<text x="{x(i):.1f}" y="{Hh - 4}" text-anchor="middle">{yr[2:] if i not in (0, len(points) - 1) else yr}</text>'
                     for i, (yr, _) in enumerate(points))
    first, last = points[0][1], points[-1][1]
    return (f'<svg class="trend" viewBox="0 0 {W} {Hh}" role="img" aria-label="Medianlön {points[0][0]}–{points[-1][0]}, från {num(first)} till {num(last)} kronor">'
            f'<polyline points="{line}" />'
            f'<circle cx="{x(0):.1f}" cy="{y(first):.1f}" r="4"/><circle cx="{x(len(points) - 1):.1f}" cy="{y(last):.1f}" r="4"/>'
            f'<text class="v" x="{x(0):.1f}" y="{y(first) - 10:.1f}" text-anchor="start">{num(first)}</text>'
            f'<text class="v" x="{x(len(points) - 1):.1f}" y="{y(last) - 10:.1f}" text-anchor="end">{num(last)}</text>{labels}</svg>')


def bars(rows, unit_max=None):
    """[(label, value)] -> table with inline bars. Real <table>, bars are decoration."""
    mx = unit_max or max(v for _, v in rows)
    return ("<table class='bars'><tbody>" + "".join(
        f'<tr><th scope="row">{esc(l)}</th><td><span class="bar" style="width:{v / mx * 100:.1f}%"></span></td><td class="n">{kr(v)}</td></tr>'
        for l, v in rows) + "</tbody></table>")


def occ_link(o): return f'<a href="/yrke/{o["slug"]}/">{esc(o["name"])}</a>'


def occ_table(rows, caption):
    return (f'<div class="tablewrap"><table><caption class="vh">{esc(caption)}</caption><thead><tr><th scope="col">Yrke</th>'
            f'<th scope="col" class="n">Median</th><th scope="col" class="n">Efter skatt</th></tr></thead><tbody>'
            + "".join(f'<tr><td>{occ_link(o)}</td><td class="n">{kr(o["d"]["p50"])}</td><td class="n">{kr(net(o["d"]["p50"]))}</td></tr>' for o in rows)
            + "</tbody></table></div>")


# ------------------------------------------------------------------ occupation page
def page_occ(o):
    d, raw, name = o["d"], o["raw"], o["name"]
    nl = lower_first(name); med = d["p50"]; med_net = net(med); n_occ = len(OCC)
    vs_all = (med / ALL["p50"] - 1) * 100
    cmp_all = (f"{pct(abs(vs_all))} {'högre' if vs_all > 0 else 'lägre'} än medianlönen för alla yrken ({kr(ALL['p50'])})"
               if abs(vs_all) >= 1 else f"i nivå med medianlönen för alla yrken ({kr(ALL['p50'])})")
    count = raw.get("count", {})
    answer = (f"Medianlönen för {nl} är {kr(med)} i månaden före skatt, enligt SCB:s lönestatistik för {YEAR}. "
              f"Efter skatt blir det {kr(med_net)} med genomsnittlig kommunalskatt. "
              f"Det är {cmp_all}, plats {o['rank']} av {n_occ} yrken.")

    # men / women
    men, women = o["y"].get("all", {}).get("men", {}), o["y"].get("all", {}).get("women", {})
    sex_html, sex_faq = "", None
    if all(x.get(k) for x in (men, women) for k in ("p50", "mean")):
        gap = (women["p50"] / men["p50"] - 1) * 100
        verdict = ("Kvinnor och män har i stort sett samma medianlön" if abs(gap) < 1.5 else
                   f"Kvinnor har {pct(abs(gap), 1)} {'lägre' if gap < 0 else 'högre'} medianlön än män")
        share = f" Av ungefär {num(count['all'])} anställda är {pct(count['women'] / count['all'] * 100)} kvinnor." if count.get("all") and count.get("women") else ""
        sex_html = (f"<h2>Lön för män och kvinnor</h2><p>{verdict}.{share}</p>"
                    f'<div class="tablewrap"><table><caption class="vh">Lön för män och kvinnor, {esc(nl)}</caption><thead><tr><th scope="col"></th>'
                    f'<th scope="col" class="n">Median</th><th scope="col" class="n">Medel</th><th scope="col" class="n">Efter skatt</th></tr></thead><tbody>'
                    + "".join(f'<tr><th scope="row">{l}</th><td class="n">{kr(x["p50"])}</td><td class="n">{kr(x["mean"])}</td><td class="n">{kr(net(x["p50"]))}</td></tr>'
                              for l, x in (("Kvinnor", women), ("Män", men)))
                    + "</tbody></table></div>")
        sex_faq = (f"Tjänar män mer än kvinnor som {nl}?", f"{verdict}: {kr(women['p50'])} för kvinnor och {kr(men['p50'])} för män ({YEAR}).")

    # sector, only when it actually splits
    sect = [(SECTORS[k], o["y"][k]["all"]) for k in SECTORS if o["y"].get(k, {}).get("all", {}).get("p50")]
    sect_html = ""
    if len({x["p50"] for _, x in sect}) >= 2:   # only when the sector actually changes the answer
        sect_html = ("<h2>Lön per sektor</h2><p>Så skiljer sig medianlönen beroende på arbetsgivare.</p>"
                     + bars([(l, x["p50"]) for l, x in sorted(sect, key=lambda s: -s[1]["p50"])]))

    # age
    age = raw.get("age", {})
    age_html = ""
    if len(age) >= 3:
        rows = [(f"{k.replace('-', '–')} år", v) for k, v in sorted(age.items())]
        lo_k, hi_k = min(age, key=age.get), max(age, key=age.get)
        age_html = (f"<h2>Lön efter ålder</h2><p>Medellönen är lägst för {lo_k.replace('-', '–')}-åringar ({kr(age[lo_k])}) "
                    f"och högst för {hi_k.replace('-', '–')}-åringar ({kr(age[hi_k])}).</p>" + bars(rows))

    # region
    reg = raw.get("region", {})
    reg_html = ""
    if len(reg) >= 4:
        top = max(reg, key=reg.get); bot = min(reg, key=reg.get)
        reg_html = (f"<h2>Lön i olika delar av Sverige</h2><p>Högst medellön i {top} ({kr(reg[top])}), lägst i {bot} ({kr(reg[bot])}).</p>"
                    + bars(sorted(reg.items(), key=lambda kv: -kv[1])))

    # trend
    pts = [(y, raw["years"][y]["all"]["all"]["p50"]) for y in sorted(raw["years"]) if raw["years"][y].get("all", {}).get("all", {}).get("p50")]
    trend_html, trend_faq = "", None
    if len(pts) >= 4:
        (y0, v0), (y1, v1) = pts[0], pts[-1]
        growth = (v1 / v0 - 1) * 100
        rows = "".join(f'<tr><th scope="row">{y}</th><td class="n">{kr(v)}</td><td class="n">{"" if i == 0 else ("+" if v >= pts[i-1][1] else "−") + pct(abs(v / pts[i-1][1] - 1) * 100, 1)}</td></tr>'
                       for i, (y, v) in enumerate(pts))
        trend_html = (f"<h2>Löneutveckling {y0}–{y1}</h2><p>Medianlönen har gått från {kr(v0)} till {kr(v1)}, en ökning med {pct(growth)} på {int(y1) - int(y0)} år.</p>"
                      f"{trend_svg(pts)}<details><summary>Visa år för år</summary><div class='tablewrap'><table><caption class='vh'>Medianlön per år</caption>"
                      f"<thead><tr><th scope='col'>År</th><th scope='col' class='n'>Median</th><th scope='col' class='n'>Förändring</th></tr></thead><tbody>{rows}</tbody></table></div></details>")
        trend_faq = (f"Hur har lönen för {nl} utvecklats?", f"Medianlönen har ökat från {kr(v0)} {y0} till {kr(v1)} {y1}, totalt {pct(growth)}.")

    # percentiles, gross + net
    pct_rows = "".join(f'<tr><th scope="row">{lbl if k != "p50" else "Median (50 %)"}</th><td class="n">{kr(d[k])}</td><td class="n">{kr(net(d[k]))}</td></tr>' for k, lbl in PCT)
    pct_rows += f'<tr><th scope="row">Medellön</th><td class="n">{kr(d["mean"])}</td><td class="n">{kr(net(d["mean"]))}</td></tr>'
    pct_html = (f'<div class="tablewrap"><table><caption class="vh">Lön för {esc(nl)} före och efter skatt</caption><thead><tr><th scope="col">Percentil</th>'
                f'<th scope="col" class="n">Före skatt</th><th scope="col" class="n">Efter skatt</th></tr></thead><tbody>{pct_rows}</tbody></table></div>'
                f'<p class="small">Percentil 25 betyder att en fjärdedel tjänar mindre än beloppet. Efter skatt med genomsnittlig kommunalskatt {pct(DEF_RATE, 2)}.</p>')

    # related: same 3-digit group, else 2-digit, nearest salary
    rel = [x for x in OCC if x["code"][:3] == o["code"][:3] and x is not o] or [x for x in OCC if x["code"][:2] == o["code"][:2] and x is not o]
    rel = sorted(rel, key=lambda x: abs(x["d"]["p50"] - med))[:6]
    near = sorted((x for x in OCC if x is not o and x not in rel), key=lambda x: abs(x["d"]["p50"] - med))[:6]
    related = ""
    if rel: related += f"<h2>Liknande yrken</h2>{occ_table(sorted(rel, key=lambda x: -x['d']['p50']), 'Liknande yrken')}"
    related += f"<h2>Yrken med ungefär samma lön</h2>{occ_table(sorted(near, key=lambda x: -x['d']['p50']), 'Yrken med liknande lön')}"

    faqs = [(f"Hur mycket tjänar {nl}?", f"Medianlönen för {nl} är {kr(med)} i månaden ({YEAR}). Medellönen är {kr(d['mean'])}."),
            (f"Vad tjänar {nl} efter skatt?", f"Med medianlön och genomsnittlig kommunalskatt blir det {kr(med_net)} i månaden efter skatt ({TAX_YEAR} års regler)."),
            (f"Vad är ingångslönen för {nl}?", f"SCB redovisar inte ingångslöner, men var tionde {nl} tjänar under {kr(d['p10'])}, vilket ger en fingervisning om lönen i början av karriären.")]
    if age.get("18-24") or age.get("25-34"):
        k = "18-24" if age.get("18-24") else "25-34"
        faqs[2] = (faqs[2][0], f"SCB redovisar inte ingångslöner. {k.replace('-', '–')}-åringar har en medellön på {kr(age[k])}, och var tionde {nl} tjänar under {kr(d['p10'])}.")
    faqs += [f for f in (sex_faq, trend_faq) if f]

    cr, cr_ld = crumb(("/yrken/", "Alla yrken"), (f"/yrke/{o['slug']}/", name))
    body = f"""<div class="wrap">{cr}
<h1>Lön för {esc(nl)}</h1>
<p class="lead">{esc(answer)}</p>
{band(o)}
{AD_TOP}
{slip(med, f"Lön efter skatt för {nl}")}
<h2>Lön före och efter skatt</h2>
{pct_html}
{AD_MID}
{sex_html}
{trend_html}
{age_html}
{sect_html}
{reg_html}
{AD_MID if (age_html or reg_html) else ""}
{faq_html(faqs)}
{related}
<p class="small source">Källa: SCB, Lönestrukturstatistik {YEAR} (yrkeskod SSYK {o['code']}), heltidslön inklusive fasta tillägg. Skatt enligt Skatteverkets tekniska beskrivning för {TAX_YEAR}.</p>
</div>"""
    return {"route": f"/yrke/{o['slug']}/", "title": f"{name} lön: {kr(med)} – efter skatt {kr(med_net)} ({TAX_YEAR})",
            "desc": answer, "priority": "0.8", "body": body, "head": faq_ld(faqs) + cr_ld}


# ------------------------------------------------------------------ hub pages
def page_home():
    common = sorted(OCC, key=lambda o: -o["raw"].get("count", {}).get("all", 0))[:12]
    rows = "".join(
        f'<tr><th scope="row">{kr(g)}</th><td class="n">−{kr(g - net(g))}</td><td class="n">{kr(net(g))}</td><td class="n">{pct((g - net(g)) / g * 100, 1)}</td></tr>'
        for g in list(range(20_000, 60_001, 2_500)) + list(range(65_000, 100_001, 5_000)))
    brk = next(g for g in range(40_000, 80_000, 100) if tax.annual(g * 12, DEF_RATE / 100, DEF_BURIAL / 100)["statlig"] > 0)
    faqs = [("Hur räknar man ut lön efter skatt?", f"Dra av grundavdraget från årslönen, räkna kommunalskatt på resten (i snitt {pct(DEF_RATE, 2)}), lägg till statlig skatt över skiktgränsen och dra av jobbskatteavdraget. Kalkylatorn ovan gör det åt dig med Skatteverkets regler för {TAX_YEAR}."),
            (f"Vad blir 30 000 kr efter skatt {TAX_YEAR}?", f"Med genomsnittlig kommunalskatt blir 30 000 kr i månadslön {kr(net(30_000))} efter skatt."),
            (f"Vad blir 40 000 kr efter skatt {TAX_YEAR}?", f"Med genomsnittlig kommunalskatt blir 40 000 kr i månadslön {kr(net(40_000))} efter skatt."),
            (f"När betalar man statlig skatt {TAX_YEAR}?", f"När månadslönen är över ungefär {kr(brk - 100)}, alltså när årsinkomsten passerar brytpunkten 660 400 kr."),
            ("Vad är medianlönen i Sverige?", f"Medianlönen för alla anställda var {kr(ALL['p50'])} i månaden {YEAR} enligt SCB. Efter skatt blir det {kr(net(ALL['p50']))}.")]
    body = f"""<div class="wrap">
<h1>Lön efter skatt {TAX_YEAR}</h1>
<p class="lead">Skriv in din månadslön och välj kommun, så räknar vi ut vad du får ut efter skatt med Skatteverkets regler för {TAX_YEAR}. Eller sök på ditt yrke och se vad andra tjänar.</p>
{slip(35_000, "Räkna ut din lön efter skatt")}
<form class="search" action="/yrken/" role="search"><label for="q">Vad tjänar ett yrke?</label><div><input id="q" name="q" list="yrken-list" placeholder="Till exempel undersköterska" autocomplete="off"><button type="submit">Visa lön</button></div>
<datalist id="yrken-list">{"".join(f'<option value="{esc(o["name"])}">' for o in sorted(OCC, key=lambda o: o["name"]))}</datalist></form>
{AD_TOP}
<h2>Vanliga yrken</h2>
{occ_table(common, "De vanligaste yrkena")}
<p><a href="/yrken/">Alla {len(OCC)} yrken</a></p>
<h2>Lön efter skatt, tabell</h2>
<p>Månadslön före och efter skatt med genomsnittlig kommunalskatt ({pct(DEF_RATE, 2)}), {TAX_YEAR}.</p>
<div class="tablewrap"><table><caption class="vh">Lön efter skatt {TAX_YEAR}</caption><thead><tr><th scope="col">Före skatt</th><th scope="col" class="n">Skatt</th><th scope="col" class="n">Efter skatt</th><th scope="col" class="n">Skattesats</th></tr></thead><tbody>{rows}</tbody></table></div>
{AD_MID}
<h2>Så räknas skatten ut</h2>
<p>Från årslönen dras först ett <b>grundavdrag</b> som beror på inkomsten. På det som blir kvar betalar du <b>kommunalskatt</b>, i genomsnitt {pct(DEF_RATE, 2)} men mellan {pct(min(k['rate'] for k in KOMMUNER), 2)} och {pct(max(k['rate'] for k in KOMMUNER), 2)} beroende på kommun. Tjänar du över brytpunkten, {kr(660_400)} om året, betalar du också 20&nbsp;% <b>statlig skatt</b> på det som överstiger.</p>
<p>Alla anställda betalar 7&nbsp;% <b>allmän pensionsavgift</b>, men den kvittas helt mot skatten. Det stora avdraget är <b>jobbskatteavdraget</b>, som sänker skatten på arbetsinkomster med upp till ungefär {kr(tax.jobbskatteavdrag(600_000, tax.grundavdrag(600_000), DEF_RATE / 100) / 12)} i månaden. Till sist tillkommer begravningsavgift, public service-avgift och, om du är medlem, kyrkoavgift.</p>
<p>Kalkylatorn använder exakt samma regler som Skatteverkets skattetabeller. Vi har kontrollerat den mot varje rad i tabellerna för {TAX_YEAR}. Din slutliga skatt kan ändå skilja sig om du har andra inkomster, avdrag eller ränteutgifter.</p>
<p><a href="/kommunalskatt/">Kommunalskatt {TAX_YEAR} för alla kommuner</a></p>
{faq_html(faqs)}
</div>"""
    return {"route": "/", "title": f"Lön efter skatt {TAX_YEAR} – räkna ut din nettolön",
            "desc": f"Räkna ut din lön efter skatt {TAX_YEAR} för din kommun, med Skatteverkets regler. Se också vad {len(OCC)} yrken tjänar enligt SCB.",
            "priority": "1.0", "body": body, "head": faq_ld(faqs)}


def page_all():
    groups = {}
    for o in sorted(OCC, key=lambda o: o["name"]):
        groups.setdefault(o["name"][0].upper(), []).append(o)
    letters = " ".join(f'<a href="#{slugify(L) or L}">{L}</a>' for L in groups)
    lists = "".join(
        f'<h2 id="{slugify(L) or L}">{L}</h2><div class="tablewrap"><table><caption class="vh">Yrken på {L}</caption><thead><tr><th scope="col">Yrke</th>'
        f'<th scope="col" class="n">Median</th><th scope="col" class="n">Efter skatt</th></tr></thead><tbody>'
        + "".join(f'<tr><td>{occ_link(o)}</td><td class="n">{kr(o["d"]["p50"])}</td><td class="n">{kr(net(o["d"]["p50"]))}</td></tr>' for o in os_)
        + "</tbody></table></div>" for L, os_ in groups.items())
    cr, cr_ld = crumb(("/yrken/", "Alla yrken"))
    body = f"""<div class="wrap">{cr}
<h1>Lön för alla yrken</h1>
<p class="lead">Medianlön före och efter skatt för {len(OCC)} yrken, enligt SCB:s lönestatistik {YEAR}. Högst lön har {lower_first(OCC[0]['name'])} ({kr(OCC[0]['d']['p50'])}), lägst {lower_first(OCC[-1]['name'])} ({kr(OCC[-1]['d']['p50'])}).</p>
<input class="filter" data-filter placeholder="Filtrera yrken" aria-label="Filtrera yrken" autocomplete="off">
<nav class="letters" aria-label="Bokstav">{letters}</nav>
{AD_TOP}
<h2>Högst lön</h2>{occ_table(OCC[:15], "Yrken med högst lön")}
{lists}
</div>"""
    return {"route": "/yrken/", "title": f"Lön för alla yrken {TAX_YEAR} – median före och efter skatt",
            "desc": f"Medianlön för {len(OCC)} yrken enligt SCB, före och efter skatt. Sök ditt yrke och jämför.", "priority": "0.9", "body": body, "head": cr_ld}


def page_kommunalskatt():
    ks = sorted(KOMMUNER, key=lambda k: k["rate"])
    g = 35_000
    rows = "".join(f'<tr id="k{k["code"]}"><td>{esc(k["name"])}</td><td class="n">{pct(k["rate"], 2)}</td><td class="n">{kr(tax.monthly_net(g, k["rate"], k["burial"])[0])}</td></tr>' for k in ks)
    lo, hi = ks[0], ks[-1]
    diff = tax.monthly_net(g, lo["rate"], lo["burial"])[0] - tax.monthly_net(g, hi["rate"], hi["burial"])[0]
    cr, cr_ld = crumb(("/kommunalskatt/", f"Kommunalskatt {TAX_YEAR}"))
    faqs = [(f"Vilken kommun har lägst skatt {TAX_YEAR}?", f"{lo['name']}, {pct(lo['rate'], 2)}."),
            (f"Vilken kommun har högst skatt {TAX_YEAR}?", f"{hi['name']}, {pct(hi['rate'], 2)}."),
            (f"Vad är genomsnittlig kommunalskatt {TAX_YEAR}?", f"{pct(DEF_RATE, 2)}, inklusive regionskatt.")]
    body = f"""<div class="wrap">{cr}
<h1>Kommunalskatt {TAX_YEAR}</h1>
<p class="lead">Genomsnittlig kommunalskatt {TAX_YEAR} är {pct(DEF_RATE, 2)}. Lägst är den i {lo['name']} ({pct(lo['rate'], 2)}) och högst i {hi['name']} ({pct(hi['rate'], 2)}). På en lön på {kr(g)} blir skillnaden {kr(diff)} i månaden.</p>
<input class="filter" data-filter placeholder="Filtrera kommuner" aria-label="Filtrera kommuner" autocomplete="off">
{AD_TOP}
<div class="tablewrap"><table><caption class="vh">Kommunalskatt {TAX_YEAR} per kommun</caption><thead><tr><th scope="col">Kommun</th><th scope="col" class="n">Skattesats</th><th scope="col" class="n">{num(g)} kr efter skatt</th></tr></thead><tbody>{rows}</tbody></table></div>
<p class="small">Skattesatsen är kommunens och regionens skatt tillsammans, exklusive begravningsavgift och kyrkoavgift. Källa: SCB.</p>
{faq_html(faqs)}
</div>"""
    return {"route": "/kommunalskatt/", "title": f"Kommunalskatt {TAX_YEAR} – alla kommuner, lägst till högst",
            "desc": f"Kommunalskatt {TAX_YEAR} för alla 290 kommuner. Lägst i {lo['name']}, högst i {hi['name']}. Se vad det betyder för din lön.",
            "priority": "0.8", "body": body, "head": faq_ld(faqs) + cr_ld}


def generated():
    return [page_home(), page_all(), page_kommunalskatt()] + [page_occ(o) for o in OCC]


def file_pages():
    base = os.path.join(SITE, "pages")
    for dirpath, _, files in os.walk(base):
        for fn in files:
            if not fn.endswith(".html"): continue
            raw = open(os.path.join(dirpath, fn), encoding="utf-8").read()
            m = META_RE.match(raw); meta = {}
            if m:
                meta = {k.strip(): v.strip() for k, v in (l.split(":", 1) for l in m.group(1).strip().splitlines() if ":" in l)}
            rel = os.path.dirname(os.path.relpath(os.path.join(dirpath, fn), base))
            yield {"route": "/" + (rel + "/" if rel else ""), "body": raw[m.end():] if m else raw, **meta}


def main():
    if not BASE_URL.startswith(("http://", "https://")):
        raise SystemExit(f"BASE_URL must be absolute, got {BASE_URL!r}")
    layout = Template(open(os.path.join(SITE, "_layout.html"), encoding="utf-8").read())
    if os.path.exists(DIST): shutil.rmtree(DIST)
    os.makedirs(DIST); routes = []
    for p in list(file_pages()) + generated():
        out = os.path.join(DIST, p["route"].strip("/"), "index.html")
        os.makedirs(os.path.dirname(out), exist_ok=True)
        page = layout.safe_substitute(
            basepath=BASE_PATH, title=esc(p.get("title", SITE_NAME)), desc=esc(p.get("desc", "")),
            canonical=BASE_URL + BASE_PATH + p["route"], head=p.get("head", ""), body=p["body"],
            year=TAX_YEAR, datayear=YEAR, updated=TODAY.isoformat())
        page = mount_ads(page)
        if BASE_PATH:
            page = page.replace('href="/', f'href="{BASE_PATH}/').replace('src="/', f'src="{BASE_PATH}/').replace('action="/', f'action="{BASE_PATH}/')
        open(out, "w", encoding="utf-8").write(page)
        if p.get("sitemap", True): routes.append((p["route"], p.get("priority", "0.7")))
    shutil.copytree(os.path.join(SITE, "assets"), os.path.join(DIST, "assets"))
    # client data: kommun rates + occupation slugs (search box)
    json.dump({"k": [[k["name"], k["rate"], k["burial"], round(k["church"], 2)] for k in KOMMUNER],
               "o": [[o["name"], o["slug"]] for o in OCC]},
              open(os.path.join(DIST, "assets", "data.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    if BASE_PATH:
        for dirpath, _, files in os.walk(os.path.join(DIST, "assets")):
            for fn in files:
                if fn.endswith(".css"):
                    f = os.path.join(dirpath, fn); css = open(f, encoding="utf-8").read()
                    open(f, "w", encoding="utf-8").write(css.replace("url(/assets/", f"url({BASE_PATH}/assets/"))
    open(os.path.join(DIST, "sitemap.xml"), "w", encoding="utf-8").write(
        '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "\n".join(f"  <url><loc>{BASE_URL}{BASE_PATH}{r}</loc><lastmod>{TODAY.isoformat()}</lastmod><priority>{p}</priority></url>" for r, p in sorted(routes))
        + "\n</urlset>\n")
    open(os.path.join(DIST, "robots.txt"), "w").write(f"User-agent: *\nAllow: /\n\nSitemap: {BASE_URL}{BASE_PATH}/sitemap.xml\n")
    open(os.path.join(DIST, "ads.txt"), "w").write(f"google.com, {ADS_CLIENT.replace('ca-', '')}, DIRECT, f08c47fec0942fa0\n")
    open(os.path.join(DIST, ".nojekyll"), "w").close()
    if CNAME and not BASE_PATH: open(os.path.join(DIST, "CNAME"), "w").write(CNAME + "\n")
    print(f"built {len(routes)} pages -> {DIST}")


if __name__ == "__main__":
    main()
