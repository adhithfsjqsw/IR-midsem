"""Label counts, annotator-vs-annotator agreement, and held-out metrics under explicit policies.
  python -X utf8 -m evalkit.annotation.analysis counts
  python -X utf8 -m evalkit.annotation.analysis agree <pass_a_glob> <pass_b_glob> [split]
  python -X utf8 -m evalkit.annotation.analysis metrics <pass_glob> <split1,split2,...>
"""
import collections
import json
import sys
from pathlib import Path

from evalkit.annotation.schema import STORE, load_store

E = Path(__file__).resolve().parent.parent


def recs(pattern):
    return {(r["query_id"], r["passage_id"]): r for r in load_store(pattern)}


def kappa(pairs):
    n = len(pairs)
    if not n:
        return float("nan")
    po = sum(a == b for a, b in pairs) / n
    ca, cb = collections.Counter(a for a, _ in pairs), collections.Counter(b for _, b in pairs)
    pe = sum(ca[k] * cb[k] for k in set(ca) | set(cb)) / (n * n)
    return (po - pe) / (1 - pe) if pe < 1 else 1.0


def counts():
    allr = load_store()
    by = collections.defaultdict(list)
    for r in allr:
        by[(r["annotator_id"], r["annotation_pass"], r["guideline_version"])].append(r)
    for key, rs in sorted(by.items()):
        print(f"\n== {key}  n={len(rs)}")
        for f in ("relevance", "court_stance", "speaker_role", "confidence", "review_status", "label_source"):
            print(f"  {f:13s}", dict(collections.Counter(r[f] for r in rs)))
        print("  needs_human_review", sum(bool(r["needs_human_review"]) for r in rs))


def agree(pa, pb, split=None):
    A, B = recs(pa), recs(pb)
    keys = [k for k in A if k in B and (split is None or A[k].get("split") == split)]
    print(f"shared items: {len(keys)}")
    for f in ("relevance", "court_stance", "speaker_role"):
        pairs = [(A[k][f], B[k][f]) for k in keys]
        po = sum(a == b for a, b in pairs) / max(len(pairs), 1)
        print(f"  {f:13s} raw agreement {po:.2f}  Cohen's kappa {kappa(pairs):.2f}  (n={len(pairs)})")
    # decided-stance agreement: only SUPPORTS/OPPOSES in either
    dec = [(A[k]["court_stance"], B[k]["court_stance"]) for k in keys if A[k]["court_stance"] in ("SUPPORTS", "OPPOSES") or B[k]["court_stance"] in ("SUPPORTS", "OPPOSES")]
    print(f"  items where either annotator says SUPPORTS/OPPOSES: {len(dec)}; identical decision: {sum(a == b for a, b in dec)}; "
          f"direct reversal (S<->O): {sum({a, b} == {'SUPPORTS', 'OPPOSES'} for a, b in dec)}")
    cm = collections.Counter((A[k]["court_stance"], B[k]["court_stance"]) for k in keys)
    print("  stance confusion (A, B): " + ", ".join(f"{a[:4]}/{b[:4]}={n}" for (a, b), n in sorted(cm.items(), key=lambda x: -x[1])))
    return keys


def metrics(pattern, splits, policy="strict"):
    """Evaluate the stored runs (evalkit/runs_<split>.json) against v2 labels.  Policies for stance items:
      strict   : a returned passage counts as a correct support/oppose hit only if the v2 label is SUPPORTS/OPPOSES with confidence HIGH or MEDIUM;
                 MIXED, NEUTRAL, UNCERTAIN, LOW-confidence and unlabelled count as NOT correct (never as 'inverted').
      lenient  : like strict but LOW-confidence SUPPORTS/OPPOSES also count.
    Relevance: RELEVANT counts; UNCERTAIN and NOT_RELEVANT do not (reported separately as the share uncertain)."""
    L = recs(pattern)
    agg = collections.defaultdict(lambda: collections.defaultdict(list))
    unl = unc = tot = 0
    for split in splits:
        runs = json.load(open(E / f"runs_{split}.json"))
        for q, systems in runs.items():
            for name, out in systems.items():
                lst = out if isinstance(out, list) else out["support"] + out["oppose"]
                for p in lst:
                    tot += 1
                    if (q, p) not in L:
                        unl += 1
                    elif L[(q, p)]["relevance"] == "UNCERTAIN":
                        unc += 1

                def rel(p):
                    r = L.get((q, p)); return bool(r and r["relevance"] == "RELEVANT")

                def hit(p, want):
                    r = L.get((q, p))
                    if not r or r["court_stance"] != want:
                        return False
                    return r["confidence"] in (("HIGH", "MEDIUM") if policy == "strict" else ("HIGH", "MEDIUM", "LOW"))
                lst10 = (out if isinstance(out, list) else [x for pair in zip(out["support"], out["oppose"]) for x in pair])[:10]
                row = agg[name]
                row["P5"].append(sum(map(rel, lst10[:5])) / 5); row["P10"].append(sum(map(rel, lst10)) / 10)
                if not isinstance(out, list):
                    if out["support"]:
                        row["supP"].append(sum(hit(p, "SUPPORTS") for p in out["support"]) / len(out["support"]))
                    if out["oppose"]:
                        row["oppP"].append(sum(hit(p, "OPPOSES") for p in out["oppose"]) / len(out["oppose"]))
                    row["both_correct"].append(float(any(hit(p, "SUPPORTS") for p in out["support"]) and any(hit(p, "OPPOSES") for p in out["oppose"])))
                else:
                    S = sum(hit(p, "SUPPORTS") for p in lst10); O = sum(hit(p, "OPPOSES") for p in lst10)
                    row["S_in_top10"].append(S); row["O_in_top10"].append(O); row["both_in_top10"].append(float(S > 0 and O > 0))
    print(f"policy={policy}; runs evaluated: {tot} returned passages, {unl} without a v2 label (counted not relevant / not correct), {unc} relevance UNCERTAIN")
    for name, row in agg.items():
        print(f"  {name:32s} " + "  ".join(f"{k}={sum(v)/len(v):.2f}" for k, v in row.items()) + f"   (queries={len(row['P10'])})")


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "counts":
        counts()
    elif cmd == "agree":
        agree(sys.argv[2], sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else None)
    elif cmd == "metrics":
        metrics(sys.argv[2], sys.argv[3].split(","), sys.argv[4] if len(sys.argv) > 4 else "strict")
