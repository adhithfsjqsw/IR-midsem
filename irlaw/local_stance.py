"""Local, rule-based, role-aware stance classifier. No model, no network, no API key.

It is a HEURISTIC with the same output fields as the model classifier (irlaw/stance.py): relevance, role, stance, evidence span,
rationale, confidence. Differences that matter:
  * it can never give HIGH confidence;
  * it never labels a passage NOT_RELEVANT (relevance is UNCERTAIN when concept coverage is low) so it can never hide a passage;
  * it abstains (UNCERTAIN) whenever the court's own voice, the proposition's concepts and a polarity cue do not line up.
Steps: split the passage into sentences; mark quoted text; assign each sentence a speaker role (party argument, quoted precedent,
statute text, procedural background, court holding/reasoning) from surface patterns; keep only court-voice sentences that cover the
proposition's concepts; count polarity cues (lexicon.OPERATORS, longest match) in them; conditions ("if", "unless", "provided")
downgrade to MIXED/UNCERTAIN. All labels are automatic predictions (verified=False). Accuracy is measured separately
(evalkit/RESULTS_local_stance.md); it is not claimed to understand law.
"""
from __future__ import annotations

import re

from .lexicon import OPERATORS, REQUIREMENT_QUERY_WORDS
from .textproc import MODALS, NEGATORS, STOP, stem, tokenize

CLASSIFIER = "local-rules"
ABBREV = {"no", "nos", "ltd", "co", "cr", "p", "c", "dr", "mr", "mrs", "smt", "shri", "anr", "ors", "para", "viz", "etc", "u", "s", "r",
          "w", "v", "vs", "sec", "art", "ch", "cl", "ibid", "supra", "hon", "j", "jj", "cj", "pvt", "i", "e", "g"}
GENERIC = {"court", "case", "act", "section", "law", "whether", "accus", "person", "permiss", "requir", "valid", "entitl"}

PARTY = re.compile(r"\b(learned|ld\.?)\s+(senior\s+)?(counsel|advocate|solicitor|attorney)|\b(submit(s|ted)?|contend(s|ed)?|argu(es|ed|ing)|"
                   r"urge[sd]?|plead(s|ed)?|allege[sd]?|canvass(ed)?)\b|\bper contra\b|\bon behalf of the (appellant|respondent|petitioner|state)|"
                   r"\baccording to the (appellant|respondent|petitioner|complainant|prosecution|defendant)|\bit is (the )?(case|contention)\b", re.I)
QUOTEDP = re.compile(r"\b(this|the supreme|the high|a constitution bench of this) court (has )?(held|observed|laid down|opined|ruled|noted|said)\b|"
                     r"\b(held|observed|ruled|laid down|opined) (in|by)\b|\bin the case of\b|\bin\s+[A-Z][\w.&' ]{2,40}\s+v(s|ersus)?\.?\s+[A-Z]|"
                     r"\(\d{4}\)\s*\d+\s*SCC|\bAIR\s*\d{4}|\[\d{4}\]\s*\d+\s*SCR|\bSCC\s+\d+|\brelied (up)?on\b|\bas (held|observed) (in|by)\b|"
                     r"\bthe court (further )?(observed|held|said) that\b|\bwas of the view\b|\bthe bench (held|observed)\b", re.I)
STATUTE = re.compile(r"^\s*(\d+[A-Z]?\.\s*)?(section|rule|article|order|regulation|clause)\s+\d+|\bExplanation\b\s*[.—:-]|"
                     r"\bprovided that\b.*\bshall\b|\bshall be (punishable|liable|deemed|entitled|competent)\b|^\s*\(\w{1,3}\)\s", re.I)
PROCED = re.compile(r"\b(appeal|petition|writ|suit|revision)\s+(arises|is directed|has been filed|was filed|is preferred|is filed)|"
                    r"\b(filed|preferred|instituted|lodged|registered)\s+(a|an|the)\b|\bimpugned (judgment|order)\b|\bhigh court (has )?(allowed|dismissed|"
                    r"set aside|granted|rejected)|\bthe facts\b|\bbrief facts\b|\bon \d{1,2}[./-]\d{1,2}[./-]\d{2,4}|\bleave granted\b|\bheard (the )?learned\b|"
                    r"\bthe (prosecution|complainant) (case|story|alleges)|\btrial court\b.*\b(convicted|acquitted|decreed|dismissed)", re.I)
HOLD = re.compile(r"\b(we|this court)\s+(hold|held|are of (the|a) (view|opinion)|find|are satisfied|conclude|answer|agree|therefore hold)\b|"
                  r"\bit is (therefore |accordingly )?(held|clear|settled|well[- ]settled)\b|\bin our (view|opinion)\b|"
                  r"\b(law|position) is (now )?(well[- ])?settled\b|\bheld\s*:|\baccordingly\b|\bthe appeal (is|stands|must be) (allowed|dismissed)\b|"
                  r"\bwe are unable to\b|\bwe do not (find|think|agree)\b|\bwe (think|find|see)\b", re.I)
COND = re.compile(r"\b(if|unless|provided|except|subject to|only (if|when|where)|in case|where the|so long as|on condition)\b", re.I)
QUOTE_RE = re.compile(r"[“\"]([^”\"]{25,})[”\"]")
SENT_SPLIT = re.compile(r"(?<=[.;?!])\s+(?=[A-Z“\"(\[\d])")


def _tok_stems(text: str) -> list[str]:
    return [stem(t) for t in tokenize(text) if t not in STOP and t not in MODALS and t not in NEGATORS]


def concept_stems(proposition: str) -> list[str]:
    out = []
    for s in _tok_stems(proposition):
        if s not in out:
            out.append(s)
    return out


def _sentences(text: str) -> list[tuple[int, int]]:
    """character spans of sentences; avoids splitting after common legal abbreviations"""
    spans, start = [], 0
    for m in SENT_SPLIT.finditer(text):
        prev = text[start:m.start()].rstrip().split()
        last = re.sub(r"\W", "", prev[-1]).lower() if prev else ""
        if last in ABBREV or len(last) <= 1:
            continue
        spans.append((start, m.start()))
        start = m.end()
    spans.append((start, len(text)))
    return [s for s in spans if text[s[0]:s[1]].strip()]


def _quoted_ranges(text: str):
    return [(m.start(), m.end()) for m in QUOTE_RE.finditer(text)]


def _in_quote_fraction(span, quotes):
    a, b = span
    inside = sum(max(0, min(b, qb) - max(a, qa)) for qa, qb in quotes)
    return inside / max(b - a, 1)


def _cue_regexes(profile):
    out = []
    for pol, lst in OPERATORS[profile].items():
        for phrase, w in lst:
            out.append((len(phrase.split()), pol, phrase, w, re.compile(r"\b" + r"\s+".join(map(re.escape, phrase.split())) + r"\b", re.I)))
    out.sort(key=lambda x: -x[0])
    return out


_CUES: dict[str, list] = {}


def _find_cues(sentence: str, profile: str):
    if profile not in _CUES:
        _CUES[profile] = _cue_regexes(profile)
    taken, found = [], []
    for n, pol, phrase, w, rx in _CUES[profile]:  # longest phrase first, overlapping shorter phrases are dropped
        for m in rx.finditer(sentence):
            if any(m.start() < b and a < m.end() for a, b in taken):
                continue
            taken.append((m.start(), m.end()))
            found.append(dict(pol=pol, phrase=phrase, w=w, start=m.start(), end=m.end()))
    return sorted(found, key=lambda c: c["start"])


def _trim(sentence: str, n: int = 45) -> str:
    """first n words of a sentence as an exact contiguous substring (the evidence span for a relevance/context label)"""
    ms = list(re.finditer(r"\S+", sentence))
    return sentence[ms[0].start():ms[min(n, len(ms)) - 1].end()] if ms else ""


def _label(relevance, role, stance, conf, span, why):
    return {"relevance": relevance, "stance": stance, "role": role, "confidence": conf, "evidence_span": span, "rationale": why[:480]}


def _sentence_role(sent: str, quoted_frac: float, zone: str) -> str:
    if quoted_frac > 0.6:
        return "QUOTED_PRECEDENT"
    if PARTY.search(sent):
        return "PARTY_ARGUMENT"
    if STATUTE.search(sent):
        return "STATUTE_OR_RULE"
    if QUOTEDP.search(sent):
        return "QUOTED_PRECEDENT"
    if HOLD.search(sent):
        return "COURT_HOLDING" if zone == "headnote" or re.search(r"\b(we|this court) (hold|held)\b|\bheld\s*:", sent, re.I) else "COURT_REASONING"
    if PROCED.search(sent):
        return "FACTUAL_OR_PROCEDURAL_BACKGROUND"
    return "COURT_REASONING" if zone == "headnote" else "UNCLEAR"


def classify_local(proposition: str, passage: str, zone: str = "body") -> dict:
    concepts = concept_stems(proposition)
    core = [c for c in concepts if c not in GENERIC] or concepts
    profile = "requirement" if any(t in REQUIREMENT_QUERY_WORDS for t in tokenize(proposition)) else "permission"
    text = passage
    pstems = set(_tok_stems(text))
    cov_passage = sum(c in pstems for c in core) / max(len(core), 1)
    relevance = "RELEVANT" if cov_passage >= 0.6 else "UNCERTAIN"  # never NOT_RELEVANT: a heuristic must not hide passages
    quotes = _quoted_ranges(text)
    sents = []
    for (a, b) in _sentences(text):
        s = text[a:b]
        st = set(_tok_stems(s))
        cov = sum(c in st for c in core) / max(len(core), 1)
        role = _sentence_role(s, _in_quote_fraction((a, b), quotes), zone)
        sents.append(dict(a=a, b=b, s=s, cov=cov, role=role))
    if not sents:
        return _label("UNCERTAIN", "UNCLEAR", "UNCERTAIN", "LOW", "", "Empty passage.")
    best_any = max(sents, key=lambda x: x["cov"])
    court = [x for x in sents if x["role"] in ("COURT_HOLDING", "COURT_REASONING", "UNCLEAR") and x["cov"] >= 0.34]
    if not court:
        role = best_any["role"] if best_any["role"] != "UNCLEAR" else "OTHER"
        return _label(relevance, role, "NEUTRAL_OR_CONTEXT" if relevance == "RELEVANT" else "UNCERTAIN", "LOW",
                      _trim(best_any["s"]) if relevance == "RELEVANT" else "",
                      f"No court-voice sentence covers the proposition's concepts; the closest sentence reads as {role.lower().replace('_', ' ')}.")
    # polarity cues inside court-voice sentences that cover the concepts (the best two by coverage)
    court.sort(key=lambda x: -x["cov"])
    cues, used = [], []
    for x in court[:2]:
        for c in _find_cues(x["s"], profile):
            cues.append(dict(c, sent=x))
        used.append(x)
    top = used[0]
    sup = sum(c["w"] for c in cues if c["pol"] == "support")
    opp = sum(c["w"] for c in cues if c["pol"] == "oppose")
    role = top["role"] if top["role"] != "UNCLEAR" else "COURT_REASONING"
    if not cues:
        return _label(relevance, role, "NEUTRAL_OR_CONTEXT" if relevance == "RELEVANT" else "UNCERTAIN", "LOW",
                      _trim(top["s"]) if relevance == "RELEVANT" else "",
                      "The court discusses the proposition's concepts but no polarity wording was found.")
    lead = max(cues, key=lambda c: c["w"])
    s_txt = lead["sent"]["s"]
    a0 = max(0, lead["start"] - 140)
    b0 = min(len(s_txt), lead["end"] + 140)
    span = s_txt[a0:b0].strip()
    held = bool(HOLD.search(s_txt)) or zone == "headnote"
    conditional = bool(COND.search(s_txt))
    big, small = max(sup, opp), min(sup, opp)
    if small > 0 and small / big >= 0.5:
        stance, conf, why = "MIXED", "LOW", "Cue wording pointing both ways appears in the court's own sentences."
    else:
        stance = "SUPPORTS" if sup > opp else "OPPOSES"
        conf = "MEDIUM" if (big >= 1.0 and (held or lead["sent"]["cov"] >= 0.5)) else "LOW"
        why = f"Court-voice sentence covers {lead['sent']['cov']:.0%} of the proposition's concepts and contains '{lead['phrase']}'."
        if conditional and conf == "MEDIUM":
            stance, why = "MIXED", why + " The sentence is conditional, so the stance is qualified rather than plain."
    if relevance != "RELEVANT":
        conf = "LOW"
    return _label(relevance, role, stance, conf, span, why)
