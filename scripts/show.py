import sys, time
sys.path.insert(0, ".")
from irlaw.balance import evidence_balanced
from irlaw.engine import Index
from evalkit.queries import ALL

ix = Index()
t = time.time(); ix.cues(); print(f"cue index built in {time.time()-t:.1f}s")
qs = [ALL[a] if a in ALL else a for a in sys.argv[1:]]
for q in qs:
    t = time.time(); r = evidence_balanced(ix, q); print(f"\n##### {q}\n({time.time()-t:.2f}s) counts={r['counts']} :: {r['verdict']}")
    print("groups:", [(g['concept'], g['variants'], g['passage_df']) for g in r['debug']['support']['groups']], r['debug']['support']['mode'])
    for side in ("support", "oppose"):
        for i, h in enumerate(r[side], 1):
            d = ix.docs[h.doc_id]; p = ix.passages[h.pid]; tr = h.trace
            cues = [(c['phrase'], c['polarity'][0], '') for pol in tr['cues'].values() for c in pol]
            print(f"\n[{side[0].upper()}{i}] {h.score:.1f} {d['case_id']} {d['title'][:70]} ({p['zone']}) cue={tr['cue']:.2f} other={tr['cue_other']:.2f} {cues[:5]}")
            print("   ", p['text'][:420].replace("\n", " "))


