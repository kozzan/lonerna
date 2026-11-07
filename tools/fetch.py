#!/usr/bin/env python3
"""Pull SCB salary + municipal tax data into site/data/*.json.

    python3 tools/fetch.py

Run once a year when SCB publishes (lönestrukturstatistik ~June, kommunalskatt
~December). Output is committed; the build never touches the network.
"""
import json, os, urllib.request

API = "https://api.scb.se/OV0104/v1/doris/sv/ssd/"
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "site", "data")


def scb(table, query):
    sel = lambda v: {"filter": "all", "values": ["*"]} if v == "*" else {"filter": "item", "values": v}
    body = json.dumps({"query": [{"code": k, "selection": sel(v)} for k, v in query.items()],
                       "response": {"format": "json"}}).encode()
    req = urllib.request.Request(API + table, body, {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        d = json.load(r)
    keys = [c["code"] for c in d["columns"] if c["type"] != "c"]
    cols = [c["code"] for c in d["columns"] if c["type"] == "c"]
    for row in d["data"]:
        for code, v in zip(cols, row["values"]):
            if v not in ("..", ".", "-", ""):
                yield dict(zip(keys, row["key"])), code, float(v)


def meta(table):
    with urllib.request.urlopen(API + table, timeout=60) as r:
        return {v["code"]: dict(zip(v["values"], v["valueTexts"])) for v in json.load(r)["variables"]}


def put(name, obj):
    with open(os.path.join(OUT, name), "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    print(name, os.path.getsize(os.path.join(OUT, name)) // 1024, "kB")


def main():
    T = "AM/AM0110/AM0110A/"
    yrken = meta(T + "LoneSpridSektYrk4AN")["Yrke2012"]
    SPREAD = {"000007CD": "mean", "000007CE": "p50", "000007CF": "p10", "000007CG": "p25", "000007CH": "p75", "000007CI": "p90"}
    SEX = {"1+2": "all", "1": "men", "2": "women"}
    SECT = {"0": "all", "1-3": "public", "4-5": "private", "1": "state", "2": "municipal", "3": "region"}
    occ = {code: {"name": name, "years": {}} for code, name in yrken.items() if code not in ("0000", "0001", "0002")}
    occ["0000"] = {"name": "Samtliga yrken", "years": {}}

    def slot(k, sector, sex):
        o = occ.get(k["Yrke2012"])
        if o is None: return None
        return o["years"].setdefault(k["Tid"], {}).setdefault(sector, {}).setdefault(sex, {})

    # 2023-2025: full spread by sector and sex
    for k, c, v in scb(T + "LoneSpridSektYrk4AN", {"Yrke2012": "*", "Sektor": list(SECT), "Kon": list(SEX), "ContentsCode": list(SPREAD), "Tid": ["2023", "2024", "2025"]}):
        s = slot(k, SECT[k["Sektor"]], SEX[k["Kon"]])
        if s is not None: s[SPREAD[c]] = round(v)
    # 2014-2022: mean + median, all sectors, all sexes (trend line)
    OLD = {"000000C5": "mean", "000000C6": "p50"}
    for k, c, v in scb(T + "LoneSpridSektorYrk4A", {"Yrke2012": "*", "Sektor": ["0"], "Kon": ["1+2"], "ContentsCode": list(OLD), "Tid": [str(y) for y in range(2014, 2023)]}):
        s = slot(k, "all", "all")
        if s is not None: s[OLD[c]] = round(v)
    # headcount + age profile (latest year)
    for k, c, v in scb(T + "LonYrkeAlder4AN", {"Yrke2012": "*", "Sektor": ["0"], "Kon": ["1+2", "1", "2"], "Alder": ["18-24", "25-34", "35-44", "45-54", "55-64", "tot"],
                                                "ContentsCode": ["000007BN", "000007BK"], "Tid": ["2025"]}):
        o = occ.get(k["Yrke2012"])
        if o is None: continue
        if k["Alder"] == "tot":
            if c == "000007BK": o.setdefault("count", {})[SEX[k["Kon"]]] = round(v)
        elif k["Kon"] == "1+2" and c == "000007BN":
            o.setdefault("age", {})[k["Alder"]] = round(v)
    # region (riksområden), latest year
    regions = meta(T + "LonYrkeRegion4AN")["Region"]
    for k, c, v in scb(T + "LonYrkeRegion4AN", {"Yrke2012": "*", "Region": [r for r in regions if r != "SE"], "Sektor": ["0"], "Kon": ["1+2"], "ContentsCode": ["000007AS"], "Tid": ["2025"]}):
        o = occ.get(k["Yrke2012"])
        if o is not None: o.setdefault("region", {})[regions[k["Region"]]] = round(v)
    put("yrken.json", occ)

    # municipal tax 2026 + burial fee / church fee per län
    kt = meta("OE/OE0101/Kommunalskatter2000")["Region"]
    kom = {}
    for k, c, v in scb("OE/OE0101/Kommunalskatter2000", {"Region": list(kt), "ContentsCode": ["OE0101D1"], "Tid": ["2026"]}):
        kom[k["Region"]] = {"name": kt[k["Region"]], "rate": v}
    for k, c, v in scb("OE/OE0101/BegrochKyrkoavg2000", {"Region": list(meta("OE/OE0101/BegrochKyrkoavg2000")["Region"]),
                                                         "ContentsCode": ["OE0101G1", "OE0101G2"], "Tid": ["2026"]}):
        r = kom.setdefault(k["Region"], {})
        r["burial" if c == "OE0101G1" else "church"] = v
    put("kommuner.json", kom)


if __name__ == "__main__":
    main()
