"""Print an annotation task for one query: the exact proposition + each pooled passage IN FULL with the end of the previous and the
start of the next passage of the same judgment.  Legacy labels are NOT shown (to avoid anchoring).
Usage: python -X utf8 -m evalkit.annotation.task <split> <qid> [first_n_passages] [offset]"""
import json
import pickle
import sys
from pathlib import Path

E = Path(__file__).resolve().parent.parent
ROOT = E.parent
PROPS = json.load(open(Path(__file__).parent / "propositions.json", encoding="utf-8"))
_I = None


def passages():
    global _I
    if _I is None:
        _I = pickle.load(open(ROOT / "data" / "index.pkl", "rb"))
    return _I["passages"]


def context(pid, n=420):
    P = passages()
    cur = P[pid]
    prev = P[pid - 1]["text"][-n:] if pid > 0 and P[pid - 1]["doc_id"] == cur["doc_id"] else ""
    nxt = P[pid + 1]["text"][:n] if pid + 1 < len(P) and P[pid + 1]["doc_id"] == cur["doc_id"] else ""
    return prev, cur["text"], nxt


def main():
    split, qid = sys.argv[1], sys.argv[2]
    limit = int(sys.argv[3]) if len(sys.argv) > 3 else 10**9
    off = int(sys.argv[4]) if len(sys.argv) > 4 else 0
    pool = json.load(open(E / f"pool_{split}.json", encoding="utf-8"))[qid]
    p = PROPS[qid]
    print(f"##### {qid}  PROPOSITION: {p['proposition']}\n SUPPORTS if: {p['supports']}\n OPPOSES  if: {p['opposes']}\n NOTE: {p['note']}\n")
    for r in pool[off:off + limit]:
        prev, text, nxt = context(r["pid"])
        print(f"[{r['pid']}] {r['case'][:70]} ({r['zone']} zone)")
        print(f"  <prev>…{prev}</prev>")
        print(f"  <PASSAGE>{text}</PASSAGE>")
        print(f"  <next>{nxt}…</next>\n")


if __name__ == "__main__":
    main()
