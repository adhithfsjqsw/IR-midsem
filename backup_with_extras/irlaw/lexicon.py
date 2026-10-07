"""Hand-written, auditable legal vocabulary resources.

1. SYNONYMS  - concept expansion (legal-terminology normalisation).  Each entry maps a *query word*
               to variants that are OR-ed into the same Boolean concept group.
2. CUES_SUPPORT / CUES_OPPOSE - polarity-tagged stance cue phrases, written relative to a proposition
               that is ASSERTED by the user ("employer can terminate ...").  Weights are fixed a priori.
These lists are the main stance-lexicon limitation of the system and are reported as such.
"""

SYNONYMS = {
    "terminate": ["termination", "terminated", "discharge", "dismissal", "removal", "simpliciter"],
    "termination": ["terminate", "terminated", "discharge", "dismissal", "simpliciter"],
    "dismiss": ["dismissal", "dismissed", "removal"],
    "probationary": ["probation", "probationer", "probationers"],
    "probationer": ["probation", "probationary"],
    "employee": ["employees", "servant", "workman"],
    "employer": ["employers", "management"],
    "notice": ["show cause", "opportunity of hearing"],
    "anticipatory": ["section 438"],
    "arrest": ["arrested", "detention"],
    "cheque": ["cheques", "dishonour", "dishonoured", "section 138"],
    "dishonour": ["dishonoured", "bounced"],
    "delay": ["condonation", "belated", "laches", "sufficient cause"],
    "limitation": ["time barred", "condonation"],
    "compensation": ["damages", "solatium"],
    "acquisition": ["acquired", "land acquisition"],
    "arbitration": ["arbitral", "arbitrator", "section 34"],
    "tenant": ["tenancy", "lessee"],
    "eviction": ["evict", "ejectment"],
    "pension": ["pensionary", "retiral", "gratuity"],
    "promotion": ["promoted", "seniority"],
    "maintenance": ["alimony", "section 125"],
    "dowry": ["498a", "cruelty"],
    "reservation": ["quota", "article 16"],
    "possession": ["adverse possession"],
    "mortgage": ["mortgagee", "mortgagor", "redemption"],
    "negligence": ["negligent", "medical negligence"],
    "confession": ["confessional", "section 25"],
    "sanction": ["prosecution sanction", "section 197"],
    "bail": ["enlarged on bail"],
    "wife": ["spouse"],
    "divorce": ["dissolution of marriage"],
}
# ---------------------------------------------------------------------------------------------------------------
# Stance OPERATORS (deontic / validity vocabulary), matched on the positional index within a few tokens of a query
# concept term.  Weights are fixed a priori.  A negator 1-3 tokens before an operator flips its polarity
# ("not required" -> opposite of "required").  Two profiles because obligation words flip meaning with the proposition:
#   permission  : "Can X be done?  Is X permissible / entitled / liable / sufficient?"  (default)
#   requirement : "Is X required / necessary / mandatory?"  (selected when the query contains such a word)
# Scope limit: propositions that are neither permission-type nor requirement-type are outside this lexicon.
# ---------------------------------------------------------------------------------------------------------------
REQUIREMENT_QUERY_WORDS = frozenset("required requirement necessary mandatory must compulsory essential need needed".split())

OPERATORS = {
    "permission": {
        "support": [
            ("can", 0.6), ("may", 0.4), ("could", 0.4), ("permissible", 1.0), ("permitted", 0.9), ("allowed", 0.8),
            ("entitled", 1.0), ("empowered", 0.9), ("competent", 0.7), ("justified", 1.0), ("valid", 0.7),
            ("lawful", 0.7), ("legal", 0.5), ("maintainable", 1.0), ("upheld", 0.8), ("sustainable", 0.9),
            ("liable", 0.9), ("sufficient", 0.9), ("need not", 1.2), ("within jurisdiction", 0.9), ("condoned", 0.9),
        ],
        "oppose": [
            ("cannot", 1.0), ("may not", 1.0), ("shall not", 1.0), ("must not", 1.0), ("impermissible", 1.3),
            ("prohibited", 1.0), ("barred", 1.0), ("illegal", 1.0), ("unlawful", 1.0), ("arbitrary", 1.0),
            ("violative", 1.2), ("violation", 0.8), ("unsustainable", 1.2), ("untenable", 1.1), ("bad in law", 1.3),
            ("erroneous", 0.7), ("refused", 0.8), ("declined", 0.8), ("mandatory", 0.9), ("required", 0.8),
            ("requirement", 0.8), ("necessary", 0.6), ("must", 0.7), ("bound to", 0.9), ("obligation", 0.8),
            ("natural justice", 1.2), ("opportunity of hearing", 1.0), ("show cause", 0.8), ("stigmatic", 1.2),
            ("set aside", 0.7), ("quashed", 0.7), ("per incuriam", 1.0), ("overruled", 1.0), ("distinguished", 0.8),
            ("contrary to", 0.8), ("insufficient", 1.0), ("unjustified", 1.1),
        ],
    },
    "requirement": {
        "support": [
            ("required", 1.0), ("requirement", 0.9), ("mandatory", 1.1), ("necessary", 0.9), ("must", 0.8),
            ("bound to", 0.9), ("obligation", 0.8), ("essential", 0.8), ("condition precedent", 1.0),
            ("sine qua non", 1.0), ("compulsory", 1.0), ("imperative", 0.9), ("indispensable", 1.0), ("shall", 0.4),
        ],
        "oppose": [
            ("directory", 1.2), ("dispensed with", 1.0), ("waived", 0.8), ("unnecessary", 1.0), ("need not", 1.2),
            ("dispense", 0.8), ("exempt", 0.7), ("exempted", 0.8),
        ],
    },
}



# Well-known Indian statutes: matched in the query as ONE phrase concept (positional phrase query), with abbreviations.
# (name words, [abbreviation / alternative phrases])
STATUTES = [
    (["code", "criminal", "procedure"], [["crpc"], ["cr", "p", "c"]]),
    (["code", "civil", "procedure"], [["cpc"]]),
    (["indian", "penal", "code"], [["ipc"], ["penal", "code"]]),
    (["negotiable", "instruments", "act"], [["ni", "act"], ["negotiable", "instruments"]]),
    (["prevention", "corruption", "act"], [["pc", "act"]]),
    (["evidence", "act"], [["indian", "evidence", "act"]]),
    (["limitation", "act"], []),
    (["arbitration", "conciliation", "act"], [["arbitration", "act"]]),
    (["land", "acquisition", "act"], []),
    (["motor", "vehicles", "act"], [["mv", "act"]]),
    (["hindu", "marriage", "act"], [["hma"]]),
    (["industrial", "disputes", "act"], [["id", "act"]]),
    (["constitution", "india"], [["constitution"]]),
]
