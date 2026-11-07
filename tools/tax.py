"""Swedish income tax on salary, inkomstår 2026, for someone under 66.

Straight from Skatteverket's "Teknisk beskrivning SKV 433, 2026" (the spec the
skattetabeller are generated from). site/assets/tax.js is a line-for-line port;
tools/test.py checks both against Skatteverket's published tables.

ponytail: column 1 only (salary, under 66). Pensioners, sjukersättning and
sjöinkomst are other columns; add them if a page ever needs them.
"""
import math

PBB = 59_200          # prisbasbelopp 2026
IBB = 83_400          # inkomstbasbelopp 2026
SKIKT = 643_000       # skiktgräns statlig skatt 2026
PS_MAX = math.floor(IBB * 1.42 * 0.01)   # public service-avgift cap = 1 184


def ceil100(x): return math.ceil(x / 100 - 1e-9) * 100
def floor100(x): return math.floor(x / 100 + 1e-9) * 100


def grundavdrag(ffi):
    if ffi <= 0.99 * PBB:   ga = 0.423 * PBB
    elif ffi <= 2.72 * PBB: ga = 0.423 * PBB + 0.20 * (ffi - 0.99 * PBB)
    elif ffi <= 3.11 * PBB: ga = 0.77 * PBB
    elif ffi <= 7.88 * PBB: ga = 0.77 * PBB - 0.10 * (ffi - 3.11 * PBB)
    else:                   ga = 0.293 * PBB
    return min(ceil100(ga), ffi)


def jobbskatteavdrag(ai, ga, ki):
    """ki = kommunal skattesats as a fraction, excluding burial/church fees."""
    ai = floor100(ai)
    if ai <= 0.91 * PBB:   base = ai
    elif ai <= 3.24 * PBB: base = 0.91 * PBB + 0.3874 * (ai - 0.91 * PBB)
    elif ai <= 8.08 * PBB: base = 1.813 * PBB + 0.251 * (ai - 3.24 * PBB)
    else:                  base = 3.027 * PBB
    return max(0, math.floor((base - ga) * ki + 1e-9))


def pensionsavgift(ffi):
    if ffi < 0.423 * PBB: return 0
    fee = 0.07 * min(ffi, 8.07 * IBB)
    return int(math.floor(fee / 100 + 0.5 - 1e-9) * 100) if fee % 100 != 50 else int(fee - 50)   # .50 rounds down


def annual(ffi, ki, fees):
    """Annual tax on salary ffi. ki = kommunal+regional rate, fees = burial (+church) rate, both fractions.
    Returns a dict of every component so pages can show the breakdown."""
    ffi = floor100(ffi)
    ga = grundavdrag(ffi)
    bfi = max(0, ffi - ga)
    statlig = math.floor(0.20 * (bfi - SKIKT)) if bfi - SKIKT >= 200 else 0
    kommunal = math.floor(bfi * ki + 1e-9)
    avgifter = math.floor(bfi * fees + 1e-9)
    pension = pensionsavgift(ffi)
    red_pension = min(pension, statlig + kommunal)
    kom_left = max(0, kommunal - red_pension)
    jsa = min(jobbskatteavdrag(ffi, ga, ki), kom_left); kom_left -= jsa
    red_ffi = min(1500 if bfi > 240_000 else max(0, math.floor((bfi - 40_000) * 0.0075)), kom_left)
    ps = min(math.floor(bfi * 0.01), PS_MAX)
    total = statlig + kommunal - red_pension - jsa - red_ffi + avgifter + pension + ps
    return {"brutto": ffi, "grundavdrag": ga, "beskattningsbar": bfi, "statlig": statlig, "kommunal": kommunal,
            "avgifter": avgifter, "pensionsavgift": pension, "red_pension": red_pension, "jobbskatteavdrag": jsa,
            "red_forvarvsinkomst": red_ffi, "public_service": ps, "skatt": total}


def monthly_net(salary, kommun_rate, burial=0.29, church=0.0):
    """Take-home per month for a monthly salary. Rates in percent, as SCB publishes them."""
    a = annual(salary * 12, kommun_rate / 100, (burial + church) / 100)
    tax = a["skatt"] // 12   # Skatteverket truncates the monthly share
    return salary - tax, tax


def table_withholding(salary_top, table):
    """What Skatteverket's skattetabell `table` (e.g. 32) says for the band whose top is salary_top.
    Tables bake 1.16 pp of burial+church fee into the whole-number rate."""
    return annual(salary_top * 12, (table - 1.16) / 100, 0.0116)["skatt"] // 12
