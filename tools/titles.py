"""SITE-65: the everyday title people search for, per SSYK code.

Search Console showed the occupation pages getting impressions at position 50-70 for queries such as
"pr specialist lön" and "it chef lön", while the pages were titled after SCB's group names. Each entry
leads the page's title, H1 and description with the title people actually type, and keeps the figure,
the year and the SCB group.

Rules (tested in tools/test.py):
- No invented titles. Every title names its source: a title in SCB's SSYK 2012 index for that same
  code (site/data/ssyk-titlar.json) or GROUP, the SCB group name itself (e.g. "PR-specialister").
- "lead" is the most-searched of those titles in GSC (25 Oct-27 Nov 2026, page+query rows); the
  queries are noted per entry. Searched titles that SCB files under another code are left out.
- "h1" is the H1 after "Lön för ".
- One page per code: no new pages per title, URLs unchanged.
"""

GROUP = "GROUP"

# code: {lead: (title, source), alts: [(title, source)], h1: str}
TITLES = {
    # "it supporttekniker lön", "lön it tekniker", "supporttekniker lön"; not SCB here: "it support", "onsite tekniker"
    "3512": {"lead": ("IT-supporttekniker", "Supporttekniker, IT"),
             "alts": [("IT-tekniker", "IT-tekniker, support"), ("helpdesktekniker", "Helpdesktekniker")],
             "h1": "IT-supporttekniker och helpdesktekniker"},
    # "hur mycket tjänar en mäklare", "mäklare lön"
    "3334": {"lead": ("Mäklare", "Fastighetsmäklare"), "alts": [("fastighetsmäklare", "Fastighetsmäklare")],
             "h1": "mäklare (fastighetsmäklare)"},
    # "kommunikationschef lön"; not SCB here: "pr manager", "pr konsult" (PR-konsult is 2432)
    "1241": {"lead": ("Kommunikationschef", "Kommunikationschef, funktions- eller mellanchef"),
             "alts": [("PR-chef", "PR-chef, funktions- eller mellanchef"), ("informationschef", "Informationschef, funktions- eller mellanchef")],
             "h1": "kommunikationschefer och PR-chefer"},
    # "personlig assistent lön", "timlön personlig assistent"
    "5343": {"lead": ("Personlig assistent", "Personlig assistent"), "alts": [("ledsagare", "Ledsagare")],
             "h1": "personliga assistenter"},
    # "arbetsledare lön bygg", "arbetsledare anläggning lön"
    "3121": {"lead": ("Arbetsledare bygg", "Arbetsledare, bygg och anläggning"),
             "alts": [("arbetsledare anläggning", "Arbetsledare, anläggning")],
             "h1": "arbetsledare inom bygg och anläggning"},
    # "it-specialist lön", "löner inom it"; not SCB here: "molnspecialist", "it infrastruktur"
    "2519": {"lead": ("IT-specialist", GROUP),
             "alts": [("UX-designer", "UX-designer"), ("scrum master", "Scrum master, IT"), ("IT-strateg", "IT-strateg")],
             "h1": "IT-specialister"},
    # "it chef lön", "lön cio"; not SCB here: "it manager", "it-ansvarig"
    "1311": {"lead": ("IT-chef", "IT-chef, funktions- eller mellanchef"),
             "alts": [("CIO", "CIO, information, funktions- eller mellanchef"), ("driftchef IT", "Driftchef, IT, funktions- eller mellanchef")],
             "h1": "IT-chefer"},
    # "pr specialist lön", "snittlön kommunikatör"; not SCB here: "kommunikationsspecialist", "internkommunikatör"
    "2432": {"lead": ("PR-specialist", GROUP),
             "alts": [("kommunikatör", "Kommunikatör, informatör"), ("informatör", "Informatör"), ("PR-konsult", "PR-konsult")],
             "h1": "PR-specialister och kommunikatörer"},
    # "betongarbetare lön", "hur mycket tjänar en betongarbetare"
    "7113": {"lead": ("Betongarbetare", "Betongarbetare, bygg och anläggning"), "alts": [("armerare", "Betongarmerare")],
             "h1": "betongarbetare"},
    # "receptionist lön"; "kontorsassistent", "kontorsansvarig", "kontorist" also land here but are not in this group
    "4225": {"lead": ("Receptionist", "Receptionist, kontor"), "alts": [("växelreceptionist", "Växelreceptionist")],
             "h1": "receptionister"},
    # "grafisk formgivare lön", "grafisk designer lön"
    "2172": {"lead": ("Grafisk formgivare", "Grafisk formgivare"),
             "alts": [("grafisk designer", "Grafisk designer"), ("art director", "Art director")],
             "h1": "grafiska formgivare och designers"},
    # "fastighetsförvaltare lön"; the page keeps its question framing (QUESTION_SLUGS)
    "3335": {"lead": ("Fastighetsförvaltare", "Fastighetsförvaltare"), "alts": [("förvaltare", "Förvaltare, fastigheter"), ("vicevärd", "Vicevärd")],
             "h1": "fastighetsförvaltare"},
    # "företagssäljare lön", "vad tjänar en innesäljare"
    "3322": {"lead": ("Företagssäljare", "Företagssäljare"),
             "alts": [("innesäljare", "Innesäljare, företagssäljare"), ("key account manager", "Key account manager"), ("account manager", "Account manager")],
             "h1": "företagssäljare och innesäljare"},
    # "mjukvaruutvecklare lön"
    "2512": {"lead": ("Mjukvaruutvecklare", "Mjukvaruutvecklare"),
             "alts": [("systemutvecklare", "Systemutvecklare"), ("programmerare", "Dataprogrammerare")],
             "h1": "mjukvaru- och systemutvecklare"},
    # "vd sekreterare lön", "vd assistent lön"; not SCB here: "chefsassistent"
    "3343": {"lead": ("VD-sekreterare", "VD-sekreterare"),
             "alts": [("VD-assistent", "VD-assistent"), ("chefssekreterare", "Chefssekreterare")],
             "h1": "VD-sekreterare och VD-assistenter"},
    # "vad tjänar en ekonom", "ekonom lön"; "civilekonom" is SCB 2411, left out
    "2419": {"lead": ("Ekonom", GROUP), "alts": [("ekonomikonsult", "Ekonomikonsult")],
             "h1": "ekonomer (övriga ekonomer)"},
    # "redovisningsekonom lön", "redovisningsekonom ingångslön"
    "3313": {"lead": ("Redovisningsekonom", "Redovisningsekonom"),
             "alts": [("redovisningskonsult", "Auktoriserad redovisningskonsult"), ("bokhållare", "Bokhållare")],
             "h1": "redovisningsekonomer"},
    # "anläggningsarbetare lön", "anläggare lön"; "markarbetare" is not an SCB title ("Markanläggningsarbetare")
    "7114": {"lead": ("Anläggningsarbetare", "Anläggningsarbetare, markarbeten, VA m.m."),
             "alts": [("anläggare", "Anläggare, markarbeten, VA m.m."), ("vägarbetare", "Vägarbetare")],
             "h1": "anläggningsarbetare"},
    # "vad tjänar en inköpare", "upphandlare lön"
    "3323": {"lead": ("Inköpare", "Inköpare"), "alts": [("upphandlare", "Upphandlare")],
             "h1": "inköpare och upphandlare"},
    # "inköpschef lön", "logistikchef lön"
    "1321": {"lead": ("Inköpschef", "Inköpschef, funktions- eller mellanchef"),
             "alts": [("logistikchef", "Logistikchef, funktions- eller mellanchef")],
             "h1": "inköpschefer och logistikchefer"},
}
