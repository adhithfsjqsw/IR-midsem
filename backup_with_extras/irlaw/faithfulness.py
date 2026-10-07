"""Independent re-computation of every explanation claim from RAW passage text (no postings, no key arrays).
If the explanation shown to the user were not the real computation, these checks would fail."""
from __future__ import annotations

import math

from .engine import NEG_WINDOW, Config, Index, smallest_window
from .lexicon import OPERATORS
from .textproc import NEGATORS, STOP, analyze, stem, tokenize

NEG = {stem(n) for n in NEGATORS}


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
    # 1. term frequencies + BM25 contributions
    ok_tf = ok_bm = True
    dl = len(stream)
    ok_len = abs(dl - int(ix.plen[h.pid])) == 0
    for r in t["terms"]:
        tf = sum(1 for _, s in stream if s == r["term"])
        ok_tf &= tf == r["tf"]
        idf, df = ix.idf(r["term"])
        c = idf * tf * (cfg.k1 + 1) / (tf + cfg.k1 * (1 - cfg.b + cfg.b * dl / ix.avgdl))
        ok_bm &= abs(r["weight"] * c - r["contrib"]) < tol
    results["tf_and_length"] = ok_tf and ok_len
    results["bm25_terms"] = ok_bm
    # 2. bm25 total = sum of listed terms (all matched terms of the passage are listed)
    results["bm25_sum"] = abs(sum(r["contrib"] for r in t["terms"]) - t["bm25"]) < 0.02
    # 3. proximity
    if cfg.prox and len(parsed.groups) >= 2:
        pl = []
        for g in parsed.groups:
            ps = []
            for stems, w, kind in g.variants:
                ps += [p for p in occurrences(stream, stems)] if len(stems) > 1 else [p for p, s in stream if s == stems[0]]
            if ps:
                pl.append(sorted(set(ps)))
        if len(pl) >= 2:
            best = smallest_window(pl)
            exp = (len(pl) / best[0]) * (len(pl) / len(parsed.groups))
            results["proximity"] = abs(exp - t["prox"]) < tol and best[0] == t["prox_span"]
        else:
            results["proximity"] = t["prox"] == 0
    # 4. stance cues (presence, position, negation, distance)
    if cfg.stance:
        concept = sorted({p for g in parsed.groups for stems, w, k in g.variants
                          for p in ([q for q, s in stream if s == stems[0]] if len(stems) == 1 else occurrences(stream, stems))})
        lex = {c: (pol, w) for pol, lst in OPERATORS[parsed.profile].items() for c, w in lst}
        negpos = {p for p, s in stream if s in NEG}
        ok = True
        for pol, lst in t["cues"].items():
            for c in lst:
                raw_pol, w = lex[c["phrase"]]
                stems = [stem(x) for x in tokenize(c["phrase"]) if x not in STOP or x in NEGATORS]
                starts = occurrences(stream, stems)
                ok &= c["pos"] in starts
                inherent = any(s in NEG for s in stems)
                neg = (not inherent) and any((c["pos"] - g) in negpos for g in range(1, NEG_WINDOW + 1))
                ok &= neg == c["negated"]
                exp_pol = ("oppose" if raw_pol == "support" else "support") if neg else raw_pol
                ok &= exp_pol == c["polarity"] == pol
                d = min(abs(c["pos"] - q) for q in concept) if concept else 999
                ok &= d == c["dist"] and d <= cfg.cue_window
                ok &= not (d == 0 and not neg)  # bare self-match with a concept term must have been skipped
                ok &= abs(w * (0.8 if neg else 1.0) / (1 + d / cfg.cue_window) - c["weight"]) < tol
        results["stance_cues"] = ok
        sums = {p: sum(sorted((c["weight"] for c in l), reverse=True)[:3]) for p, l in t["cues"].items()}
        side = sums.get(cfg.stance, 0.0)
        oth = sums["oppose" if cfg.stance == "support" else "support"]
        mult = cfg.cue_head_mult if (cfg.zones and ix.passages[h.pid]["zone"] == "headnote") else 1.0
        results["stance_margin"] = abs(max(side - cfg.lam_other * oth, 0.0) * mult - t["cue"]) < tol
    # 5. zone / title / statute / authority claims
    d = ix.docs[h.doc_id]
    if cfg.zones:
        results["headnote_boost"] = abs((t["bm25"] * (cfg.headnote_mult - 1) if ix.passages[h.pid]["zone"] == "headnote" else 0) - t["zone_boost"]) < tol
        title_stems = {s for _, s in analyze(d["title"])}
        results["title_zone"] = all(any(v[0][0] in title_stems for v in g.variants if v[2] == "query" and len(v[0]) == 1)
                                    for g in parsed.groups if g.label in t["title_groups"])
        results["statute"] = all(s in d["statutes"] for s in t["statutes_matched"])
    if cfg.authority:
        results["authority"] = abs(math.log2(max(d["bench"], 1)) - t["g"]) < tol
    # 5b. topical gate: cues only counted for topically strong passages
    results["topical_gate"] = (abs(t["topical"] - (t["bm25"] + t["zone_boost"] + cfg.w_prox * t["prox"])) < tol
                               and t["gate_eligible"] == (t["topical"] >= cfg.topical_gate * t["best_topical"] - 1e-9)
                               and (t["gate_eligible"] or (not any(t["cues"].values()) and t["cue"] == 0)))
    # 6. final score is exactly the sum of displayed parts
    parts = (t["bm25"] + t["zone_boost"] + cfg.w_prox * t["prox"] + cfg.w_cue * t["cue"] + cfg.w_title * len(t["title_groups"])
             + cfg.w_statute * (1 if t["statutes_matched"] else 0) + cfg.w_auth * t["g"])
    results["final_equals_sum_of_parts"] = abs(parts - t["final"]) < tol and abs(t["final"] - h.score) < tol
    return results





