import sys, time
sys.path.insert(0, ".")
from irlaw.engine import Index, search, Config, BASELINE

q = sys.argv[1] if len(sys.argv) > 1 else "Can an employer terminate a probationary employee without prior notice?"
t = time.time(); ix = Index(); print(f"loaded in {time.time()-t:.1f}s: {len(ix.docs)} docs {ix.N} passages")
for name, cfg in [("BASELINE", BASELINE), ("SUPPORT", Config(stance="support")), ("OPPOSE", Config(stance="oppose"))]:
    t = time.time()
    hits, dbg, parsed = search(ix, q, cfg, 5)
    print(f"\n=== {name} ({time.time()-t:.2f}s) {dbg['mode']} cands={dbg.get('candidates')} dropped={dbg['dropped_generic_concepts']}")
    for h in hits:
        d = ix.docs[h.doc_id]; tr = h.trace
        print(f"{h.score:6.2f} {d['case_id']:14s} {d['title'][:60]:60s} tfidf={tr['tfidf']:.1f} prox={tr['prox']:.2f} cue={tr['cue']:.2f}/{tr['cue_other']:.2f} {[c['phrase'] for pol in tr['cues'].values() for c in pol][:4]}")
