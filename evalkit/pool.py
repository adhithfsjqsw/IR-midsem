"""Build the judging pool: union of the top results of every system variant, so that every system is judged on
the same (pid) items (pooling, as in TREC).  Output: evalkit/pool.json
Run from project root:  python -X utf8 -m evalkit.pool"""
import json
from dataclasses import replace
from pathlib import Path

from irlaw.balance import lexical_evidence_balanced
from irlaw.engine import ABLATIONS, Config, Index, search
import sys

from evalkit.queries import ALL, DEV, FRESH, TEST

OUT = Path(__file__).parent


def systems(ix, q):
    """-> {system_name: [pid, ...]} (the passage shown for each returned judgment, in rank order)"""
    out = {}
    for name, cfg in ABLATIONS.items():
        hits, _, _ = search(ix, q, cfg, 10)
        out[f"list|{name}"] = [h.pid for h in hits]
    for name, cfg in ABLATIONS.items():
        if name.startswith("A"):
            continue
        r = lexical_evidence_balanced(ix, q, cfg, 5)  # phrase baseline; never calls a model
        out[f"EB|{name}"] = {"support": [h.pid for h in r["support"]], "oppose": [h.pid for h in r["oppose"]],
                             "contested": [h.pid for h in r["contested"]]}
    return out


def main(split):
    ix = Index()
    pool, runs = {}, {}
    for qid, q in {"dev": DEV, "test": TEST, "fresh": FRESH, "all": ALL}[split].items():
        s = systems(ix, q)
        runs[qid] = s
        pids = []
        for v in s.values():
            lst = v if isinstance(v, list) else v["support"] + v["oppose"] + v["contested"]
            for p in lst[:10]:
                if p not in pids:
                    pids.append(p)
        pool[qid] = [dict(pid=p, case=ix.docs[ix.passages[p]["doc_id"]]["title"], case_id=ix.docs[ix.passages[p]["doc_id"]]["case_id"],
                          zone=ix.passages[p]["zone"], text=ix.passages[p]["text"]) for p in pids]
        print(qid, len(pids), "pooled passages")
    json.dump(pool, open(OUT / f"pool_{split}.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    json.dump(runs, open(OUT / f"runs_{split}.json", "w"), indent=1)
    print("total", sum(len(v) for v in pool.values()))


if __name__ == "__main__":
    split = sys.argv[1]
    existing = [f for f in (OUT / f"pool_{split}.json", OUT / f"runs_{split}.json") if f.exists()]
    if existing and "--force" not in sys.argv:
        sys.exit(f"Refusing to overwrite {[f.name for f in existing]} (previous pool/run results are preserved). Pass --force to regenerate.")
    main(split)


