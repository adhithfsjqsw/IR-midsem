"""Independent re-computation of every explanation claim from RAW passage text (no postings, no key arrays).
If the explanation shown to the user were not the real computation, these checks would fail."""
from __future__ import annotations

import math

from .engine import Config, Index, smallest_window
from .lexicon import OPERATORS
from .textproc import NEGATORS, STOP, analyze, stem, tokenize


def occurrences(stream, stems, gap=2):
    """naive phrase search on the (pos, stem) stream; returns start positions"""
    out = []
    for i, (p, s) in enumerate(stream):
        if s != stems[0]:
            continue
        last, ok = p, True
        for nxt in stems[1:]:
            found = None
            for (p2, s2) in stream[i + 1:i + 1 + 40]:
                if p2 - last > gap:
                    break
                if p2 > last and s2 == nxt:
                    found = p2
                    break
            if found is None:
                ok = False
                break
            last = found
        if ok:
            out.append(p)
    return out


def check_hit(ix: Index, h, parsed, cfg: Config, tol=1e-3):
    t = h.trace
    text = ix.passages[h.pid]["text"]
    stream = analyze(text)
    results = {}
    # ---- lnc document vector length, recomputed from the raw passage
    counts = {}
    for _, s in stream:
        counts[s] = counts.get(s, 0) + 1
    norm = math.sqrt(sum((1 + math.log10(c)) ** 2 for c in counts.values())) or 1.0
    # ---- ltc query vector, recomputed from the parsed query
    raw = {}
    for g in parsed.groups:
        for stems, w, kind in g.variants:
            for st in stems:
                if st not in raw:
                    idf, df = ix.idf(st)
                    raw[st] = w * idf
    qn = math.sqrt(sum(v * v for v in raw.values())) or 1.0
    ok_tf = ok_w = True
    for r in t["terms"]:
        tf = counts.get(r["term"], 0)
        ok_tf &= tf == r["tf"]
        wq = raw[r["term"]] / qn
        wd = (1 + math.log10(tf)) / norm if tf else 0.0
        ok_w &= abs(wq - r["wq"]) < 1e-4 and abs(wd - r["wd"]) < 1e-4 and abs(100 * wq * wd - r["contrib"]) < tol
    results["tf_counts"] = ok_tf
    results["cosine_weights"] = ok_w
    # all matched terms are listed, so their contributions sum to the cosine score
    full = sum(100 * raw[s] / qn * (1 + math.log10(c)) / norm for s, c in counts.items() if s in raw)
    results["cosine_sum"] = abs(full - t["tfidf"]) < 0.02 and abs(sum(r["contrib"] for r in t["terms"]) - t["tfidf"]) < 0.02
    # ---- proximity
    if cfg.prox and len(parsed.groups) >= 2:
        pl = []
        for g in parsed.groups:
            ps = []
            for stems, w, kind in g.variants:
                ps += occurrences(stream, stems) if len(stems) > 1 else [p for p, s in stream if s == stems[0]]
            if ps:
                pl.append(sorted(set(ps)))
        if len(pl) >= 2:
            best = smallest_window(pl)
            exp = (len(pl) / best[0]) * (len(pl) / len(parsed.groups))
            results["proximity"] = abs(exp - t["prox"]) < tol and best[0] == t["prox_span"]
        else:
            results["proximity"] = t["prox"] == 0
    # ---- stance phrase queries: the COMPLETE set of matches (with longest-match) must equal the trace
    if cfg.stance:
        concept = sorted({p for g in parsed.groups for stems, w, k in g.variants
                          for p in ([q for q, s in stream if s == stems[0]] if len(stems) == 1 else occurrences(stream, stems))})
        lex = []
        for pol, lst in OPERATORS[parsed.profile].items():
            for phrase, w in lst:
                stems = [stem(x) for x in tokenize(phrase) if x not in STOP or x in NEGATORS]
                if stems:
                    lex.append((phrase, pol, w, stems))
        matches = []
        if t["champion"] and concept:
            for phrase, pol, w, stems in lex:
                for s in occurrences(stream, stems):
                    d = min(abs(s - q) for q in concept)
                    if 0 < d <= cfg.cue_window:
                        matches.append((phrase, pol, w, len(stems), s, d))
        accepted = []
        for m in sorted(matches, key=lambda x: (-x[3], x[4])):
            if any(a[3] > m[3] and a[4] <= m[4] <= a[4] + 2 * (a[3] - 1) for a in accepted):
                continue
            accepted.append(m)
        exp = sorted((m[0], m[4], m[1], round(m[2] / (1 + m[5] / cfg.cue_window), 4), m[5]) for m in accepted)
        got = sorted((c["phrase"], c["pos"], c["polarity"], c["weight"], c["dist"]) for pol in t["cues"].values() for c in pol)
        results["stance_phrases_complete"] = exp == got
        sums = {p: sum(sorted((c["weight"] for c in l), reverse=True)[:3]) for p, l in t["cues"].items()}
        side = sums.get(cfg.stance, 0.0)
        oth = sums["oppose" if cfg.stance == "support" else "support"]
        mult = cfg.cue_head_mult if (cfg.zones and ix.passages[h.pid]["zone"] == "headnote") else 1.0
        results["stance_margin"] = abs(max(side - cfg.lam_other * oth, 0.0) * mult - t["cue"]) < tol
    # ---- zone / title / statute / authority claims
    d = ix.docs[h.doc_id]
    if cfg.zones:
        results["headnote_weight"] = abs((t["tfidf"] * (cfg.headnote_mult - 1) if ix.passages[h.pid]["zone"] == "headnote" else 0) - t["zone_boost"]) < tol
        title_stems = {s for _, s in analyze(d["title"])}
        results["title_zone"] = all(any(v[0][0] in title_stems for v in g.variants if v[2] == "query" and len(v[0]) == 1)
                                    for g in parsed.groups if g.label in t["title_groups"])
        results["statute_field"] = all(s in d["statutes"] for s in t["statutes_matched"])
    if cfg.authority:
        results["authority"] = abs(math.log2(max(d["bench"], 1)) - t["g"]) < tol
    # ---- champion list gate and final score
    results["topical_score"] = abs(t["topical"] - (t["tfidf"] + t["zone_boost"] + cfg.w_prox * t["prox"])) < tol
    results["no_stance_outside_champions"] = t["champion"] or (not any(t["cues"].values()) and t["cue"] == 0)
    parts = (t["tfidf"] + t["zone_boost"] + cfg.w_prox * t["prox"] + cfg.w_cue * t["cue"] + cfg.w_title * len(t["title_groups"])
             + cfg.w_statute * (1 if t["statutes_matched"] else 0) + cfg.w_auth * t["g"])
    results["final_equals_sum_of_parts"] = abs(parts - t["final"]) < tol and abs(t["final"] - h.score) < tol
    return results
