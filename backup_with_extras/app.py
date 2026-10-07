"""Streamlit demo.  Run:  streamlit run app.py
Retrieval is executed ONCE per query (cached on the query string only); the Regular/Professional switch only changes
which text generator receives the identical EvidencePack."""
import re

import streamlit as st

from irlaw.balance import evidence_balanced
from irlaw.engine import BASELINE, Config, Index, search
from irlaw.respond import build_pack, respond, verify_response

st.set_page_config(page_title="Indian Legal IR", layout="wide")


@st.cache_resource
def get_index():
    return Index()


@st.cache_data(show_spinner=False)
def run(query: str):
    ix = get_index()
    base, bdbg, bparsed = search(ix, query, BASELINE, 10)
    res = evidence_balanced(ix, query)
    pack = build_pack(ix, query, res)
    return base, bdbg, res, pack


def trace_table(ix, h, side=None):
    t = h.trace
    rows = [("Text relevance (BM25, matched passage)", t["bm25"]), ("Headnote-zone boost", t["zone_boost"]),
            (f"Query proximity (x{t['weights']['w_prox']})", t["weights"]["w_prox"] * t["prox"]),
            (f"Stance cue ({side}, margin; x{t['weights']['w_cue']})", t["weights"]["w_cue"] * t["cue"] if side else 0.0),
            (f"Title-zone concept hits x{t['weights']['w_title']}", t["weights"]["w_title"] * len(t["title_groups"])),
            (f"Statute match x{t['weights']['w_statute']}", t["weights"]["w_statute"] * (1 if t["statutes_matched"] else 0)),
            (f"Authority g=log2(bench={t['bench']}) x{t['weights']['w_auth']}", t["weights"]["w_auth"] * t["g"])]
    st.table({"signal": [r[0] for r in rows], "contribution": [round(r[1], 3) for r in rows]})
    st.caption(f"final = {t['final']:.3f}   |  proximity span={t['prox_span']} window={t['prox_window']}  "
               f"groups matched={t['groups_matched']}")
    if t["terms"]:
        st.caption("Matched terms: " + ", ".join(f"{r['term']} (tf={r['tf']}, idf={r['idf']}, {r['kind']})" for r in t["terms"][:8]))
    cues = [c for pol in t["cues"].values() for c in pol]
    if cues:
        st.caption("Stance cues in passage: " + "; ".join(f"'{c['phrase']}' -> {c['polarity']}{' (negated)' if c['negated'] else ''}, dist={c['dist']}" for c in cues[:8]))


def show_hit(ix, h, label, side):
    d, p = ix.docs[h.doc_id], ix.passages[h.pid]
    with st.expander(f"{label}  {d['title']}  |  {d['citation']}  |  score {h.score:.2f}"):
        st.markdown(f"**Court:** {d['court']}  **Date:** {d['date']}  **Bench:** {d['bench']}  **Case ID:** {d['case_id']}  **Disposal:** {d['disposal']}")
        if d["statutes"]:
            st.markdown("**Provisions mentioned:** " + "; ".join(d["statutes"][:5]))
        st.markdown(f"**Matching passage ({p['zone']} zone):** {p['text'][:900]}")
        st.markdown(f"[View original judgment (PDF)]({d['pdf_url']})")
        trace_table(ix, h, side)


ix = get_index()
st.title("Evidence-Balanced and Explainable Indian Legal Search")
st.caption(f"Corpus: {len(ix.docs)} Supreme Court of India judgments ({min(d['year'] for d in ix.docs)}-{max(d['year'] for d in ix.docs)}), "
           f"{ix.N} passages. Source: AWS Open Data 'Indian Supreme Court Judgments' (CC-BY-4.0, from eCourts). Information retrieval, not legal advice.")
q = st.text_input("Legal proposition / question", "Can an employer terminate a probationary employee without prior notice?")
mode = st.radio("Response mode (changes wording only)", ["Regular", "Professional"], horizontal=True)
if st.button("Search") or q:
    base, bdbg, res, pack = run(q)
    c1, c2, c3 = st.columns(3)
    c1.metric("Supporting evidence", res["counts"]["support"]); c2.metric("Opposing evidence", res["counts"]["oppose"]); c3.metric("Mixed-language", res["counts"]["contested"])
    st.info(res["verdict"])
    st.caption(f"Evidence-pack SHA-256 (identical in both modes): `{pack['sha256']}`")

    with st.expander("IR intermediates: query processing, Boolean concepts, postings, candidate counts", expanded=False):
        st.json({"concept_groups": res["debug"]["support"]["groups"], "pruned_synonyms": res["debug"]["support"].get("pruned_synonyms"),
                 "boolean": {k: res["debug"]["support"].get(k) for k in ("mode", "intersection_order", "candidates", "scored_passages")},
                 "baseline": {k: bdbg.get(k) for k in ("mode", "scored_passages")}})
        for g in res["debug"]["support"]["groups"][:3]:
            st.caption(f"postings sample for '{g['concept']}': passage df={g['passage_df']}")

    left, right = st.columns(2)
    with left:
        st.subheader("Supporting evidence")
        for i, h in enumerate(res["support"], 1):
            show_hit(ix, h, f"S{i}", "support")
        if not res["support"]:
            st.warning("No sufficiently strong supporting evidence found.")
    with right:
        st.subheader("Opposing evidence")
        for i, h in enumerate(res["oppose"], 1):
            show_hit(ix, h, f"O{i}", "oppose")
        if not res["oppose"]:
            st.warning("No sufficiently strong opposing evidence found.")
    if res["contested"]:
        st.subheader("Mixed-language authorities (both kinds of cue, not counted on either side)")
        for i, h in enumerate(res["contested"], 1):
            show_hit(ix, h, f"C{i}", "support")

    st.divider()
    key = "regular" if mode == "Regular" else "professional"
    text, engine = respond(key, pack)
    st.subheader(f"{mode} response")
    st.caption(f"generator: {engine}  |  verification: {verify_response(text, pack)}")
    st.markdown(text)
    if st.button("Prove: both modes use identical evidence"):
        a, _ = respond("regular", pack)
        b, _ = respond("professional", pack)
        cited_a = sorted(set(re.findall(r"\[([SOC]\d+)\]", a)))
        cited_b = sorted(set(re.findall(r"\[([SOC]\d+)\]", b)))
        st.success(f"Both responses were generated from the same pack, sha256={pack['sha256'][:16]}... "
                   f"Cited ids: regular={cited_a}, professional={cited_b}. Retrieval was not re-run.")

    with st.expander("Baseline: plain BM25 (no Boolean concepts, proximity, zones, authority or stance)"):
        for i, h in enumerate(base, 1):
            d = ix.docs[h.doc_id]
            st.markdown(f"{i}. **{d['title']}** ({d['citation']}) score {h.score:.2f}")
