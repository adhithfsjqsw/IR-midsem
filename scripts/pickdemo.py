import sys
sys.path.insert(0, ".")
from irlaw.balance import evidence_balanced
from irlaw.engine import Index
from evalkit.queries import ALL

ix = Index()
for qid in sys.argv[1:]:
    r = evidence_balanced(ix, ALL[qid])
    print(f"\n{qid} {ALL[qid]}\n  counts={r['counts']}")
    for side in ("support", "oppose"):
        for i, h in enumerate(r[side][:3], 1):
            d = ix.docs[h.doc_id]
            ops = [c['phrase'] for pol in h.trace['cues'].values() for c in pol][:4]
            print(f"  [{side[0].upper()}{i}] {h.score:5.1f} {d['case_id']:14s} {d['title'][:48]:48s} {ops}")
