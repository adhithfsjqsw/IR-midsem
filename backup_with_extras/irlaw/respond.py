"""Post-retrieval response layer.  IR decides WHAT (the EvidencePack); this module only decides HOW to word it.

 * build_pack(result)  -> frozen, JSON-serialisable evidence pack + sha256 (identical for both modes by construction:
                          the retrieval functions take no mode argument).
 * respond(mode, pack) -> text.  Uses the Claude API if ANTHROPIC_API_KEY is set, else a deterministic template.
 * verify_response()   -> checks the text cites only evidence ids that exist in the pack.
"""
from __future__ import annotations

import hashlib
import json
import os
import re

DISCLAIMER = ("This is an information-retrieval result over a limited corpus (Supreme Court of India judgments, 2019-2023). "
              "It surfaces passages that use supporting or opposing language; it does not decide what the law is and is not legal advice.")


def _snippet(text: str, n=520):
    text = re.sub(r"\s+", " ", text).strip()
    return text if len(text) <= n else text[:n].rsplit(" ", 1)[0] + " ..."


def build_pack(ix, query: str, result: dict) -> dict:
    items = []
    for side, tag in (("support", "S"), ("oppose", "O"), ("contested", "C")):
        for i, h in enumerate(result[side], 1):
            d, p, tr = ix.docs[h.doc_id], ix.passages[h.pid], h.trace
            cues = [c for pol in tr["cues"].values() for c in pol]
            items.append(dict(
                id=f"{tag}{i}", side=side, rank=i, score=round(h.score, 4), case=d["title"], case_id=d["case_id"],
                citation=d["citation"], date=d["date"], court=d["court"], bench=d["bench"], disposal=d["disposal"],
                statutes=d["statutes"][:5], zone=p["zone"], passage=_snippet(p["text"]), url=d["pdf_url"],
                signals=dict(bm25=round(tr["bm25"], 3), headnote_boost=round(tr["zone_boost"], 3), proximity=round(tr["prox"], 4),
                             stance_cue=round(tr["cue"], 3), authority_g=round(tr["g"], 3),
                             matched_cues=[dict(phrase=a, polarity=b, negated=n)
                                           for a, b, n in sorted({(c["phrase"], c["polarity"], c["negated"]) for c in cues})[:6]])))
    pack = dict(query=query, counts=result["counts"], verdict=result["verdict"], items=items, disclaimer=DISCLAIMER)
    blob = json.dumps(pack, sort_keys=True, ensure_ascii=False)
    pack["sha256"] = hashlib.sha256(blob.encode("utf-8")).hexdigest()
    return pack


# ----------------------------------------------------------------------------- template fallback (no LLM)
def _cue_words(it):
    ph = [c["phrase"] for c in it["signals"]["matched_cues"]][:3]
    return ", ".join(f'"{p}"' for p in ph) if ph else "no strong cue phrase"


def template_regular(pack):
    L = [f"**What your question is about**\n{pack['query']}\n"]
    c = pack["counts"]
    L.append(f"**What the search found**\nThe search looked through the judgments in the database and found {c['support']} judgment(s) "
             f"whose wording leans towards agreeing with your question and {c['oppose']} whose wording leans against it."
             + (f" {c['contested']} judgment(s) used both kinds of wording." if c["contested"] else "") + f"\n{pack['verdict']}\n")
    for side, title, verb in (("support", "What the supporting cases indicate", "points in favour"),
                              ("oppose", "What the opposing cases indicate", "points the other way")):
        its = [i for i in pack["items"] if i["side"] == side]
        L.append(f"**{title}**")
        if not its:
            L.append("No judgment in this database was strong enough to include here.\n")
            continue
        for i in its:
            L.append(f"- [{i['id']}] *{i['case']}* ({i['date']}). The passage {verb}; it uses words like {_cue_words(i)}. "
                     f"In the court's words: \"{i['passage'][:260]}...\"")
        L.append("")
    L.append(f"**Important limitation**\n{pack['disclaimer']} Please talk to a lawyer before acting on any of this.")
    return "\n".join(L)


def template_professional(pack):
    L = [f"### LEGAL ISSUE\nWhether, on the retrieved Supreme Court authorities (2019-2023), the proposition is sustained or qualified: *{pack['query']}*\n"]
    for side, title in (("support", "SUPPORTING POSITION"), ("oppose", "OPPOSING / LIMITING POSITION"), ("contested", "MIXED-LANGUAGE AUTHORITIES")):
        its = [i for i in pack["items"] if i["side"] == side]
        if side == "contested" and not its:
            continue
        L.append(f"### {title}")
        if not its:
            L.append("No authority met the minimum stance threshold in the indexed corpus.\n")
            continue
        for i in its:
            stat = f"; provisions noted: {', '.join(i['statutes'][:3])}" if i["statutes"] else ""
            L.append(f"- [{i['id']}] **{i['case']}**, {i['citation']} ({i['case_id']}), decided {i['date']}, bench of {i['bench']}; disposal: {i['disposal']}{stat}.\n"
                     f"  Retrieved passage ({i['zone']} zone; cue terms {_cue_words(i)}): \"{i['passage'][:330]}...\"")
        L.append("")
    c = pack["counts"]
    L.append(f"### RETRIEVAL OBSERVATION\nStance-labelled authorities: supporting={c['support']}, opposing={c['oppose']}, mixed={c['contested']}. {pack['verdict']}\n")
    L.append("### SOURCES\n" + "\n".join(f"- [{i['id']}] {i['case']}, {i['citation']} - {i['url']}" for i in pack["items"]))
    L.append(f"\n*{pack['disclaimer']}*")
    return "\n".join(L)


# ----------------------------------------------------------------------------- LLM path
SYSTEM = {
    "regular": ("You rewrite a fixed set of retrieved Indian Supreme Court passages for a member of the public with no legal training. "
                "Use plain, short sentences and no legal jargon (explain any unavoidable term). Sections: What your question is about; "
                "What the supporting cases indicate; What the opposing cases indicate; What the search found; Important limitation."),
    "professional": ("You rewrite a fixed set of retrieved Indian Supreme Court passages for lawyers and legal researchers. "
                     "Formal, precise, terminology-rich, concise. Sections: LEGAL ISSUE; SUPPORTING POSITION; OPPOSING / LIMITING POSITION; "
                     "RETRIEVAL OBSERVATION; SOURCES."),
}
RULES = ("RULES: Use ONLY the evidence items in the JSON. Cite every claim with its id like [S1]/[O2]. Do not add cases, citations, "
         "sections, dates, judges or holdings that are not in the JSON. Do not reorder, drop, or re-score items. Never say what 'the law is' "
         "or that a case is 'correct'; say 'supporting evidence found', 'opposing evidence found', 'passages retrieved'. "
         "If a side is empty, say no sufficiently strong evidence was found. End with the disclaimer.")


def respond(mode: str, pack: dict):
    """-> (text, engine_name)."""
    key = os.environ.get("ANTHROPIC_API_KEY")
    if key:
        try:
            import anthropic
            cl = anthropic.Anthropic(api_key=key)
            body = {k: v for k, v in pack.items() if k != "sha256"}
            msg = cl.messages.create(model=os.environ.get("RESPONSE_MODEL", "claude-sonnet-5-5"), max_tokens=1800, temperature=0,
                                     system=SYSTEM[mode] + "\n" + RULES,
                                     messages=[{"role": "user", "content": json.dumps(body, ensure_ascii=False)}])
            return msg.content[0].text, "claude-llm"
        except Exception as e:  # fall back, but say so
            txt = (template_regular if mode == "regular" else template_professional)(pack)
            return txt, f"template (LLM failed: {type(e).__name__})"
    return (template_regular if mode == "regular" else template_professional)(pack), "template (no API key)"


def verify_response(text: str, pack: dict):
    ids = {i["id"] for i in pack["items"]}
    cited = set(re.findall(r"\[([SOC]\d+)\]", text))
    case_ids = set(re.findall(r"\b20\d\d INSC \d+\b", text))
    ok_ids = {i["case_id"] for i in pack["items"]}
    for i in pack["items"]:  # ids quoted inside a retrieved passage are source text, hence grounded
        ok_ids |= set(re.findall(r"\b20\d\d INSC \d+\b", i["passage"]))
    return dict(unknown_evidence_ids=sorted(cited - ids), unknown_case_ids=sorted(case_ids - ok_ids), ok=not (cited - ids) and not (case_ids - ok_ids))
