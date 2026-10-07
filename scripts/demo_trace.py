"""Print the IR intermediates for one query (for the demo video / report):
parsed concept groups, postings sizes, Boolean intersection order, candidate counts, tf-idf term table, proximity window,
stance operators with positions, score decomposition, and the evidence-pack hash.
Usage: python scripts/demo_trace.py "Can an employer terminate a probationary employee without prior notice?" """
import sys
sys.path.insert(0, ".")
from dataclasses import replace

from irlaw.balance import evidence_balanced
from irlaw.engine import BASELINE, Config, Index, parse_query, search
from irlaw.respond import build_pack

q = sys.argv[1] if len(sys.argv) > 1 else "Can an employer terminate a probationary employee without prior notice?"
ix = Index()
print(f"QUERY: {q}\nINDEX: {len(ix.docs)} judgments, {ix.N} passages, {len(ix.vocab)} terms, {len(ix.pos)} positions\n")

print("== 1. QUERY PARSER: concept groups (stem variants), profile")
parsed = parse_query(ix, q, Config())
for g in parsed.groups:
    print(f"  concept '{g.label}': " + ", ".join(f"{' '.join(v[0])}[{v[2]},w={v[1]}]" for v in g.variants))
print("  stance profile:", parsed.profile)

print("\n== 2. BASELINE (plain tf-idf cosine, no Boolean/proximity/zones)")
hits, dbg, _ = search(ix, q, BASELINE, 5)
for i, h in enumerate(hits, 1):
    d = ix.docs[h.doc_id]
    print(f"  {i}. {h.score:6.2f}  {d['case_id']:15s} {d['title'][:70]}")

print("\n== 3. SUPPORT SPEC on the same engine")
hits, dbg, parsed = search(ix, q, replace(Config(), stance="support"), 3)
print("  postings (passage df) per concept group:", [(g['concept'], g['passage_df']) for g in dbg['groups']])
print("  Boolean mode:", dbg['mode'], "| intersection order (rarest first):", dbg.get('intersection_order'), "| candidates:", dbg.get('candidates'), "| pruned synonyms:", dbg.get('pruned_synonyms'))
for h in hits[:1]:
    t, d, p = h.trace, ix.docs[h.doc_id], ix.passages[h.pid]
    print(f"\n  TOP SUPPORT-SPEC HIT: {d['title']} | {d['citation']} | {d['case_id']} | bench {d['bench']} | {d['date']}")
    print(f"  passage ({p['zone']} zone, pid {h.pid}): {p['text'][:420]}...")
    print("  query/document term weights (ltc query weight wq, lnc doc weight wd, contribution = 100*wq*wd):")
    for r in t['terms'][:6]:
        print(f"    {r['term']:12s} concept={r['concept']:12s} {r['kind']:8s} tf={r['tf']} df={r['df']} idf={r['idf']} wq={r['wq']} wd={r['wd']} -> {r['contrib']}")
    print(f"  proximity: groups matched={t['groups_matched']}, window={t['prox_window']}, span={t['prox_span']}, value={t['prox']:.3f}")
    print("  stance operators:", [(c['phrase'], c['polarity'], f"pos={c['pos']}", f"dist={c['dist']}") for pol in t['cues'].values() for c in pol])
    w = t['weights']
    print("  SCORE DECOMPOSITION:")
    rows = [("tf-idf cosine x100 (lnc.ltc)", t['tfidf']), ("headnote-zone boost", t['zone_boost']), (f"proximity x{w['w_prox']}", w['w_prox'] * t['prox']),
            (f"stance margin x{w['w_cue']}", w['w_cue'] * t['cue']), (f"title-zone hits x{w['w_title']}", w['w_title'] * len(t['title_groups'])),
            (f"statute match x{w['w_statute']}", w['w_statute'] * (1 if t['statutes_matched'] else 0)), (f"authority log2(bench={t['bench']}) x{w['w_auth']}", w['w_auth'] * t['g'])]
    for n, v in rows:
        print(f"    {n:38s} {v:8.3f}")
    print(f"    {'FINAL':38s} {t['final']:8.3f}   (champion list: {t['champion']})")

print("\n== 4. EVIDENCE BALANCE (support spec + oppose spec, same index)")
res = evidence_balanced(ix, q)
print("  counts:", res['counts'], "|", res['verdict'])
for side in ("support", "oppose"):
    for i, h in enumerate(res[side], 1):
        d = ix.docs[h.doc_id]
        print(f"  [{side[0].upper()}{i}] {h.score:6.2f} stance-margin={h.trace['cue']:.2f}  {d['case_id']:15s} {d['title'][:60]}")
pack = build_pack(ix, q, res)
print("\n== 5. EVIDENCE PACK handed to the response layer: sha256 =", pack['sha256'])


