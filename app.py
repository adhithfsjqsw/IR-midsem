"""Streamlit demo.  Run:  streamlit run app.py
Retrieval is executed ONCE per query (cached on the query string only); the Regular/Professional switch only changes
which text generator receives the identical EvidencePack."""
import html
import importlib
import os
import re
import sys

import streamlit as st

# Streamlit keeps imported modules alive between runs, so after editing irlaw/*.py a running server would keep using the OLD code.
# Reload the project modules (in dependency order) whenever any of their files changed on disk.
_ROOT = os.path.dirname(os.path.abspath(__file__))
_MODS = ["lexicon", "textproc", "engine", "local_stance", "stance", "balance", "respond"]
_SIG = tuple(os.path.getmtime(os.path.join(_ROOT, "irlaw", m + ".py")) for m in _MODS)
if getattr(sys, "_irlaw_sig", None) not in (None, _SIG):
    for _m in _MODS:
        if "irlaw." + _m in sys.modules:
            importlib.reload(sys.modules["irlaw." + _m])
sys._irlaw_sig = _SIG

from irlaw.balance import evidence_balanced
from irlaw.engine import BASELINE, Config, Index, search
from irlaw.respond import build_pack, respond, verify_response

st.set_page_config(page_title="Indian Legal IR", layout="wide")

# ---- presentation only: one restrained accent colour (#1f4e79), light surfaces, consistent spacing ----
st.markdown("""
<style>
.block-container {max-width: 1180px; padding-top: 2.2rem; padding-bottom: 3rem;}
.stAppDeployButton, [data-testid="stToolbar"] {visibility: hidden;}
h1 {font-family: Georgia, 'Times New Roman', serif; font-weight: 600; font-size: 2.05rem !important; color: #16324f; letter-spacing: -0.01em;
    padding-bottom: .25rem; border-bottom: 3px solid #1f4e79; display: inline-block;}
h2, h3 {font-family: Georgia, 'Times New Roman', serif; color: #16324f; font-weight: 600;}
h3 {font-size: 1.15rem !important; margin-top: 1.4rem; padding-bottom: .2rem; border-bottom: 1px solid #dfe4ea;}
.tagline {color: #44546a; font-size: 1.02rem; margin: .6rem 0 .2rem 0; max-width: 62rem;}
[data-testid="stCaptionContainer"] {color: #5c6b7a;}
/* search row */
[data-testid="stTextInput"] input {font-size: 1.05rem; padding: .7rem .85rem; border: 1.5px solid #b8c4d0; border-radius: 8px; background: #ffffff;}
[data-testid="stTextInput"] input:focus {border-color: #1f4e79; box-shadow: 0 0 0 2px rgba(31,78,121,.15);}
.stButton > button {background: #1f4e79; color: #ffffff; border: 1px solid #1f4e79; border-radius: 8px; padding: .55rem 1.4rem; font-weight: 600;}
.stButton > button:hover {background: #173b5c; border-color: #173b5c; color: #ffffff;}
/* count summary */
[data-testid="stMetric"] {background: #ffffff; border: 1px solid #dfe4ea; border-radius: 10px; padding: .6rem .9rem;}
[data-testid="stMetricLabel"] p {font-size: .82rem; color: #5c6b7a;}
[data-testid="stMetricValue"] {font-size: 1.6rem; color: #16324f;}
/* notices: readable, but calm */
[data-testid="stAlert"] {border-radius: 8px;}
/* case cards */
[data-testid="stVerticalBlockBorderWrapper"] {border-radius: 10px; border-color: #dfe4ea; background: #ffffff;}
.case-head {font-family: Georgia, 'Times New Roman', serif; font-size: 1.02rem; font-weight: 600; color: #16324f; line-height: 1.35;}
.case-tag {display: inline-block; min-width: 2rem; text-align: center; margin-right: .6rem; padding: 1px 7px; border-radius: 6px;
           background: #1f4e79; color: #fff; font-family: sans-serif; font-size: .78rem; font-weight: 700; vertical-align: 1px;}
.case-meta {color: #5c6b7a; font-size: .82rem; margin: .3rem 0 .45rem 0;}
.chip {display: inline-block; padding: 1px 10px; margin: 0 6px 4px 0; border: 1px solid #cfd6de; border-radius: 999px; background: #f6f8fa;
       color: #44546a; font-size: .78rem;}
.chip.stance {border-color: #1f4e79; background: #eaf0f6; color: #1f4e79; font-weight: 600;}
.chip-note {color: #7a8794; font-size: .76rem; font-style: italic; margin-bottom: .4rem;}
.section-note {color: #5c6b7a; font-size: .9rem; margin: -.2rem 0 .6rem 0;}
details summary {font-size: .92rem;}
</style>
""", unsafe_allow_html=True)


@st.cache_resource
def get_index():
    return Index()


def _code_version():
    """cache key: changes whenever the retrieval code changes, so stale cached results are never reused"""
    import os
    root = os.path.dirname(os.path.abspath(__file__))
    from irlaw.stance import api_available, model_name
    files = tuple(os.path.getmtime(os.path.join(root, "irlaw", f)) for f in ("engine.py", "balance.py", "lexicon.py", "respond.py", "stance.py", "local_stance.py"))
    from irlaw.respond import ollama_available
    return files + (api_available(), model_name(), ollama_available(), os.environ.get("STANCE_PROVIDER", "auto"))  # configuration changes invalidate cached results


@st.cache_data(show_spinner=False)
def _run_cached(query: str, version):
    return _run(query)


@st.cache_data(show_spinner=False)
def _respond_cached(mode: str, sha: str, provider_state, _pack):
    """a local LLM can take tens of seconds: generate once per (mode, evidence pack, provider) and reuse on reruns"""
    return respond(mode, _pack)


def respond_cached(mode: str, pack: dict):
    from irlaw.respond import llm_provider, ollama_model
    return _respond_cached(mode, pack["sha256"], (llm_provider(), ollama_model()), pack)


def run(query: str):
    return _run_cached(query, _code_version())


def _run(query: str):
    ix = get_index()
    base, bdbg, bparsed = search(ix, query, BASELINE, 10)
    res = evidence_balanced(ix, query)
    pack = build_pack(ix, query, res)
    return base, bdbg, res, pack


def trace_table(ix, h, side=None):
    t = h.trace
    cue_label = f"Stance cue ({side}, margin; x{t['weights']['w_cue']})" if side else "Stance cue (not used)"
    rows = [("Text relevance (lnc.ltc cosine x100, matched passage)", t["tfidf"]), ("Headnote-zone boost", t["zone_boost"]),
            (f"Query proximity (x{t['weights']['w_prox']})", t["weights"]["w_prox"] * t["prox"]),
            (cue_label, t["weights"]["w_cue"] * t["cue"] if side else 0.0),
            (f"Title-zone concept hits x{t['weights']['w_title']}", t["weights"]["w_title"] * len(t["title_groups"])),
            (f"Statute match x{t['weights']['w_statute']}", t["weights"]["w_statute"] * (1 if t["statutes_matched"] else 0)),
            (f"Authority g=log2(bench={t['bench']}) x{t['weights']['w_auth']}", t["weights"]["w_auth"] * t["g"])]
    st.table({"signal": [r[0] for r in rows], "contribution": [round(r[1], 3) for r in rows]})
    st.caption(f"final = {t['final']:.3f}   |  proximity span={t['prox_span']} window={t['prox_window']}  "
               f"groups matched={t['groups_matched']}")
    if t["terms"]:
        st.caption("Matched terms: " + ", ".join(f"{r['term']} (tf={r['tf']}, idf={r['idf']}, {r['kind']})" for r in t["terms"][:8]))
    cues = [c for pol in t.get("cues", {}).values() for c in pol]
    if cues:
        st.caption("Phrase cues in passage (heuristic wording only): " + "; ".join(f"'{c['phrase']}' -> {c['polarity']}, dist={c['dist']}" for c in cues[:8]))


def show_classification(h):
    cls = h.trace.get("automatic_stance")
    if not cls:
        return
    heur = cls.get("classifier") == "lexical-heuristic"
    unavailable = cls.get("classifier") == "unavailable"
    kind = ("heuristic wording match only - stance NOT understood" if heur else
            "topical candidate only - stance NOT classified" if unavailable else
            "automatic model prediction, unverified")
    st.markdown(f"**Predicted stance:** {cls['stance']} · **speaker role:** {cls['role']} · **confidence:** {cls['confidence']} · "
                f"**relevance:** {cls['relevance']}  \n*({kind})*")
    st.caption(f"Classifier: {cls.get('classifier', 'unknown')}" + (" · from cache" if cls.get("cached") else ""))
    if cls.get("evidence_span"):
        st.markdown(f"**Evidence span:** “{cls['evidence_span']}”")
    if cls.get("rationale"):
        st.caption(f"Rationale: {cls['rationale']}")


res_is_heuristic = False


def show_hit(ix, h, label, side):
    d, p = ix.docs[h.doc_id], ix.passages[h.pid]
    cls = h.trace.get("automatic_stance", {})
    with st.container(border=True):
        st.markdown(f'<div class="case-head"><span class="case-tag">{html.escape(label)}</span>{html.escape(d["title"])}</div>'
                    f'<div class="case-meta">{html.escape(str(d["citation"]))} &middot; {html.escape(str(d["court"]))} &middot; decided {html.escape(str(d["date"]))}'
                    f' &middot; bench of {html.escape(str(d["bench"]))} &middot; {html.escape(str(d["case_id"]))} &middot; disposal: {html.escape(str(d["disposal"]))}</div>',
                    unsafe_allow_html=True)
        chips = ""
        if cls:
            heur = cls.get("classifier") == "lexical-heuristic"
            unavailable = cls.get("classifier") == "unavailable"
            note = ("heuristic wording match only - stance NOT understood" if heur else
                    "topical candidate only - stance NOT classified" if unavailable else
                    "automatic prediction, unverified")
            chips = (f'<span class="chip stance">{html.escape(str(cls["stance"]))}</span>'
                     f'<span class="chip">role: {html.escape(str(cls["role"]).lower().replace("_", " "))}</span>'
                     f'<span class="chip">confidence: {html.escape(str(cls["confidence"]).lower())}</span>')
        st.markdown(f'<div>{chips}<span class="chip">topical score {h.score:.2f}</span></div>'
                    + (f'<div class="chip-note">{html.escape(note)}</div>' if cls else ""), unsafe_allow_html=True)
        if d["statutes"]:
            st.caption("Provisions mentioned: " + "; ".join(d["statutes"][:5]))
        preview = p["text"][:320] + ("..." if len(p["text"]) > 320 else "")
        st.markdown(f"**Matching passage ({p['zone']} zone):** {preview}")
        st.markdown(f"[View original judgment (PDF)]({d['pdf_url']})")
        with st.expander("Full passage, prediction details and score trace"):
            st.markdown(f"**Matching passage ({p['zone']} zone):** {p['text'][:900]}")
            show_classification(h)
            st.markdown("**Topical retrieval score trace** (unchanged by the stance classifier):")
            trace_table(ix, h, side if cls.get("classifier") == "lexical-heuristic" else None)


ix = get_index()
st.title("Evidence-Balanced and Explainable Indian Legal Search")
st.markdown('<div class="tagline">Find Supreme Court passages that support, oppose or qualify a legal proposition. '
            'Stance labels are automatic predictions shown with their evidence, not verified legal conclusions.</div>', unsafe_allow_html=True)
st.caption(f"Corpus: {len(ix.docs)} Supreme Court of India judgments ({min(d['year'] for d in ix.docs)}-{max(d['year'] for d in ix.docs)}), "
           f"{ix.N} passages. Source: AWS Open Data 'Indian Supreme Court Judgments' (CC-BY-4.0, from eCourts). Information retrieval, not legal advice.")
_cq, _cm, _cb = st.columns([6, 3, 1.2], vertical_alignment="bottom")
with _cq:
    q = st.text_input("Legal proposition / question", "Can an employer terminate a probationary employee without prior notice?")
with _cm:
    mode = st.radio("Response mode (changes wording only)", ["Regular", "Professional"], horizontal=True)
with _cb:
    _clicked = st.button("Search")
if _clicked or q:
    base, bdbg, res, pack = run(q)
    # default to heuristic when the flag is missing (stale modules) or the method string says fallback: never call phrase hits "predicted"
    res_is_heuristic = bool(res.get("heuristic", True)) or str(res.get("classification_method", "lexical")).startswith("lexical")
    c = res["counts"]
    from irlaw.respond import llm_provider, ollama_model, ollama_status
    from irlaw.stance import stance_provider
    _ok, _why = ollama_status()
    if res_is_heuristic:
        st.warning("NO STANCE CLASSIFIER IN USE. " + res.get("classification_notice", "") +
                   " Set ANTHROPIC_API_KEY (and optionally STANCE_MODEL) to enable the automatic stance classifier.")
    elif res.get("local"):
        pass  # the rule-based classifier's description is shown inside "Technical details" below (and the page tagline states labels are predictions)
    else:
        st.info("Stance labels below are AUTOMATIC PREDICTIONS from a language model; they are not verified by a human and are not legal conclusions. "
                "Uncertain items are shown, not forced into support/opposition.")
    st.caption(f"Classification method: **{res.get('classification_method', 'unknown')}**")
    cols = st.columns(5)
    cols[0].metric("Predicted support" if not res_is_heuristic else "Not classified: support", c["support"])
    cols[1].metric("Predicted oppose" if not res_is_heuristic else "Not classified: oppose", c["oppose"])
    cols[2].metric("Mixed", c["contested"]); cols[3].metric("Uncertain / contextual", c.get("uncertain", 0))
    cols[4].metric("Judged not relevant", c.get("not_relevant", 0))
    st.info(res["verdict"])

    with st.expander("Technical details: classifier configuration and evidence-pack hash", expanded=False):
        if res.get("local") and not res_is_heuristic:
            st.caption(res.get("classification_notice", "") + " Uncertain items are shown, not forced into support/opposition. "
                       "Set ANTHROPIC_API_KEY for the model classifier.")
        st.caption(f"Stance provider: **{stance_provider()}** | summary provider: **{llm_provider()}** | Ollama: "
                   + (f"running, model {ollama_model()}" if _ok else f"NOT available - {_why}"))
        st.caption(f"Evidence-pack SHA-256 (identical in both modes): `{pack['sha256']}`")

    with st.expander("IR intermediates: query processing, Boolean concepts, postings, candidate counts", expanded=False):
        search_debug = res["debug"].get("topical", res["debug"].get("support", {}))
        st.json({"concept_groups": search_debug.get("groups", []), "pruned_synonyms": search_debug.get("pruned_synonyms"),
                 "boolean": {k: search_debug.get(k) for k in ("mode", "intersection_order", "candidates", "scored_passages")},
                 "baseline": {k: bdbg.get(k) for k in ("mode", "scored_passages")}})
        for g in search_debug.get("groups", [])[:3]:
            st.caption(f"postings sample for '{g['concept']}': passage df={g['passage_df']}")

    left, right = st.columns(2, gap="large")
    with left:
        st.subheader("Predicted to support" if not res_is_heuristic else "Support (classifier unavailable)")
        for i, h in enumerate(res["support"], 1):
            show_hit(ix, h, f"S{i}", "support")
        if not res["support"]:
            st.warning("No passage was classified as supporting.")
    with right:
        st.subheader("Predicted to oppose" if not res_is_heuristic else "Opposition (classifier unavailable)")
        for i, h in enumerate(res["oppose"], 1):
            show_hit(ix, h, f"O{i}", "oppose")
        if not res["oppose"]:
            st.warning("No passage was classified as opposing.")

    st.subheader(f"Mixed or qualified passages ({len(res.get('contested', []))})")
    for i, h in enumerate(res.get("contested", []), 1):
        show_hit(ix, h, f"C{i}", "contested")
    if not res.get("contested"):
        st.caption("None.")
    st.subheader(f"Uncertain or contextual passages ({len(res.get('uncertain', []))})")
    for i, h in enumerate(res.get("uncertain", []), 1):
        show_hit(ix, h, f"U{i}", "uncertain")
    if not res.get("uncertain"):
        st.caption("None." if not res_is_heuristic else "Topical candidates are shown above as uncertain; no stance prediction was made.")

    st.divider()
    key = "regular" if mode == "Regular" else "professional"
    with st.spinner("Writing the summary (a local model can take up to a minute the first time)..."):
        text, engine = respond_cached(key, pack)
    st.subheader(f"{mode} response")
    st.caption(f"generator: {engine}")
    with st.container(border=True):
        st.markdown(text)
    with st.expander("Citation verification details", expanded=False):
        st.caption(f"citation verification: {verify_response(text, pack)}")
    if st.button("Prove: both modes use identical evidence"):
        a, _ = respond_cached("regular", pack)
        b, _ = respond_cached("professional", pack)
        cited_a = sorted(set(re.findall(r"\[([SOCU]\d+)\]", a)))
        cited_b = sorted(set(re.findall(r"\[([SOCU]\d+)\]", b)))
        st.success(f"Both responses were generated from the same pack, sha256={pack['sha256'][:16]}... "
                   f"Cited ids: regular={cited_a}, professional={cited_b}. Retrieval and classification were not re-run.")

    with st.expander("Baseline: plain tf-idf cosine, lnc.ltc (no Boolean concepts, proximity, zones, authority or stance)"):
        for i, h in enumerate(base, 1):
            d = ix.docs[h.doc_id]
            st.markdown(f"{i}. **{d['title']}** ({d['citation']}) score {h.score:.2f}")
    st.caption("IR prototype over a limited corpus; not legal advice and not a determination of the law.")
