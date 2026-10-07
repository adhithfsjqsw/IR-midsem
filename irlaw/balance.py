"""Automatic stance classification over a shared topical candidate set.

With ANTHROPIC_API_KEY, candidate passages receive a role-aware, evidence-checked
automatic classification. Without a key, topical candidates are shown as uncertain;
the old phrase-cue method remains available only as a baseline for evaluation.
"""
from __future__ import annotations

from dataclasses import replace

from .engine import STRICT, Config, Index, parse_query, search
from .stance import classify_hits, uncertain_label

POOL = 40  # judgments pulled from each spec before assignment


def lexical_evidence_balanced(ix: Index, query: str, cfg: Config | None = None, k: int = 5, method: str = "lexical-fallback"):
    """Phrase-cue baseline (the pre-classifier system). Never calls a model. Every item is labelled UNCERTAIN:
    a deontic cue phrase near the query terms is wording, not an understood stance of the court."""
    cfg = cfg or Config()
    out, dbg = {}, {}
    for side in ("support", "oppose"):
        parsed = parse_query(ix, query, cfg)  # same parse for both specs
        hits, d, parsed = search(ix, query, replace(cfg, stance=side), POOL, parsed)
        out[side] = {h.doc_id: h for h in hits}
        dbg[side] = d
    assigned = {"support": [], "oppose": []}
    for did in set(out["support"]) | set(out["oppose"]):
        hs, ho = out["support"].get(did), out["oppose"].get(did)
        cs = hs.trace["cue"] if hs else 0.0
        co = ho.trace["cue"] if ho else 0.0
        if max(cs, co) <= 0:
            continue
        (assigned["support"] if cs >= co else assigned["oppose"]).append(hs if cs >= co else ho)
    for lst in assigned.values():
        lst.sort(key=lambda h: -h.score)
    for side, lst in assigned.items():
        for h in lst:
            cues = h.trace.get("cues", {}).get(side, [])
            h.trace["automatic_stance"] = dict(
                relevance="UNCERTAIN", stance="UNCERTAIN", role="UNCLEAR", confidence="LOW",
                evidence_span=(cues[0]["phrase"] if cues else ""),
                rationale="Legacy phrase-cue match only; role and proposition-level stance were not independently determined.",
                classifier="lexical-heuristic", verified=False)
            h.trace["classification_method"] = "lexical-fallback"
    ns, no = len(assigned["support"]), len(assigned["oppose"])
    if ns and no:
        verdict = "The retrieved corpus contains passages pointing in different directions on this proposition (potentially divergent judicial positions)."
    elif ns:
        verdict = "Supporting wording was found; no passage with opposing wording was found in this corpus."
    elif no:
        verdict = "Opposing wording was found; no passage with supporting wording was found in this corpus."
    else:
        verdict = "No passage with supporting or opposing wording was found for this query."
    return dict(support=assigned["support"][:k], oppose=assigned["oppose"][:k], contested=[], uncertain=[],
                counts=dict(support=ns, oppose=no, contested=0, uncertain=0, not_relevant=0), verdict=verdict, debug=dbg, parsed=parsed,
                classification_method=method, heuristic=True,
                classification_notice=("HEURISTIC FALLBACK: no model classifier was used. 'Supporting'/'opposing' below only means the passage "
                                       "contains supporting-/opposing-sounding wording near the query terms; the court's actual stance was "
                                       "NOT automatically understood and every item is marked UNCERTAIN / low confidence."))


def _unclassified_candidates(ix: Index, query: str, cfg: Config, k: int, method: str):
    """Safe app fallback: surface topical candidates as uncertain, never as stance results.

    The phrase-only implementation remains available as an evaluation baseline via
    lexical_evidence_balanced(), but it cannot make proposition-level stance decisions.
    """
    topical_cfg = replace(cfg, authority=False, stance=None)
    hits, dbg, parsed = search(ix, query, topical_cfg, max(40, k * 8), parse_query(ix, query, topical_cfg))
    for h in hits:
        h.trace["automatic_stance"] = uncertain_label(
            "No stance model was available. This is only a topical candidate; relevance and stance were not determined.",
            model="unavailable")
        h.trace["automatic_stance"]["classifier"] = "unavailable"
        h.trace["classification_method"] = method
    visible = hits[:k]
    return dict(support=[], oppose=[], contested=[], uncertain=visible,
                counts=dict(support=0, oppose=0, contested=0, uncertain=len(hits), not_relevant=0),
                verdict="No confident support/opposition classification is available. Topical candidates are shown as uncertain; inspect them or configure the stance model.",
                debug={"topical": dbg}, parsed=parsed, classification_method=method, heuristic=True,
                classification_notice="No stance model was used. These are topical candidates only; they are not classified as relevant, supporting, or opposing.")


def evidence_balanced(ix: Index, query: str, cfg: Config | None = None, k: int = 5, client=None):
    """Retrieve topical candidates once, classify stance automatically, and abstain on uncertain items.

    The topical score/order and its trace are retained untouched; the classification is a separate field
    (`h.trace["automatic_stance"]`) and never alters the IR score. Without a configured model the phrase-cue
    heuristic is used and is labelled as such (see lexical_evidence_balanced). `client` is injectable for offline tests.
    """
    cfg = cfg or STRICT  # application default: full pipeline + abstention (rarest concept mandatory, minimum concept coverage)
    # Authority can break ties among relevant authorities, but it should not help an
    # otherwise weak candidate enter the classifier's pool. Keep candidate generation topical.
    topical_cfg = replace(cfg, authority=False, stance=None)
    candidates, dbg, parsed = search(ix, query, topical_cfg, max(40, k * 8), parse_query(ix, query, topical_cfg))
    if not candidates:  # abstain: nothing in the corpus matches enough of the query; no model call is made
        return dict(support=[], oppose=[], contested=[], uncertain=[],
                    counts=dict(support=0, oppose=0, contested=0, uncertain=0, not_relevant=0),
                    verdict=("No passage in this corpus matches enough of the query's concepts, so nothing is shown rather than loosely related text. "
                             "The corpus (Supreme Court judgments 2018-2024) may not cover this topic."),
                    debug={"topical": dbg}, parsed=parsed, classification_method="not-run (no candidates)", heuristic=False,
                    classification_notice="No candidates were retrieved, so no stance classification was attempted.")
    labels, method = classify_hits(ix, query, candidates, client)
    if not labels:
        safe_method = method.replace("lexical-fallback", "topical-only (classifier unavailable)")
        return _unclassified_candidates(ix, query, topical_cfg, k, method=safe_method)

    buckets = {"support": [], "oppose": [], "contested": [], "uncertain": []}
    not_relevant = 0
    for h in candidates:
        label = labels.get(h.pid)
        if label is None:
            label = uncertain_label("No classification returned for this passage.")
        h.trace["automatic_stance"] = label
        h.trace["classification_method"] = method
        if label["relevance"] == "NOT_RELEVANT":
            not_relevant += 1  # counted, not listed: the passage does not address the proposition
            continue
        key = {"SUPPORTS": "support", "OPPOSES": "oppose", "MIXED": "contested"}.get(label["stance"], "uncertain")
        buckets[key].append(h)
    for vals in buckets.values():
        # clearly relevant passages first, then by topical score (the score itself is never modified)
        vals.sort(key=lambda h: (h.trace["automatic_stance"]["relevance"] != "RELEVANT", -h.score))
    ns, no, nm, nu = (len(buckets[x]) for x in ("support", "oppose", "contested", "uncertain"))
    if ns and no:
        verdict = "Automatically predicted stances point in different directions; read the quoted text and context before relying on either."
    elif ns:
        verdict = "Passages automatically predicted to support the proposition were found; none was predicted to oppose it in this candidate set."
    elif no:
        verdict = "Passages automatically predicted to oppose the proposition were found; none was predicted to support it in this candidate set."
    elif nm:
        verdict = "Only mixed or qualified passages were found; no passage was confidently predicted to support or oppose the proposition."
    elif nu:
        verdict = "No passage received a confident supporting or opposing prediction; relevant but ambiguous passages are listed as uncertain/contextual."
    else:
        verdict = "The model judged every retrieved candidate not relevant to the proposition, so nothing is listed; the corpus may not cover this topic."
    return dict(support=buckets["support"][:k], oppose=buckets["oppose"][:k], contested=buckets["contested"][:k],
                uncertain=buckets["uncertain"][:k],
                counts=dict(support=ns, oppose=no, contested=nm, uncertain=nu, not_relevant=not_relevant),
                verdict=verdict, debug={"topical": dbg}, parsed=parsed, classification_method=method, heuristic=False,
                local=method.startswith("local-rules"),
                classification_notice=(
                    ("LOCAL RULE-BASED CLASSIFIER (no model, no API key): a heuristic that detects the speaker (party argument, quoted precedent, statute, "
                     "court) and polarity wording. On held-out reference labels it was right for about 30 % of the supports and 34 % of the opposes it "
                     "reported and found only about 10 % / 26 % of the reference ones, so most passages are left uncertain. These are automatic predictions, "
                     "not verified, not legal conclusions.")
                    if method.startswith("local-rules") else
                    ("LOCAL LANGUAGE MODEL (Ollama, free, runs on this computer) read each passage against the proposition. Measured on held-out reference labels "
                     "(AI-assisted, unreviewed): about 40 % of its 'supports' (30/75) and 21 % of its 'opposes' (3/14) matched; it almost never predicts 'opposes' "
                     "or 'mixed' and leaves most passages as context, so absence of an opposing prediction means little. Automatic predictions, not verified, "
                     "not legal conclusions.")
                    if method.startswith("ollama") else
                    ("Stances are AUTOMATIC PREDICTIONS from a language model reading the retrieved passage and its neighbouring text. "
                     "They are not verified by a human and are not legal conclusions; low-confidence cases are withheld as uncertain.")))
