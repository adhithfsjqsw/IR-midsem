"""Incremental judging helper.
  python -X utf8 -m evalkit.labels_tool todo <split> [chars]     print pooled passages that have no label yet
  python -X utf8 -m evalkit.labels_tool add  <split> "<qid> <pid> <code> <pid> <code> ... ; <qid> ..."   merge labels
"""
import json
import sys
from pathlib import Path

D = Path(__file__).parent


def load(split):
    lp = D / f"labels_{split}.json"
    return json.load(open(lp)) if lp.exists() else {}


def main():
    cmd, split = sys.argv[1], sys.argv[2]
    labels = load(split)
    if cmd == "todo":
        n = int(sys.argv[3]) if len(sys.argv) > 3 else 600
        pool = json.load(open(D / f"pool_{split}.json", encoding="utf-8"))
        total = 0
        for q, items in pool.items():
            have = labels.get(q, {})
            todo = [r for r in items if str(r["pid"]) not in have]
            total += len(todo)
            if todo:
                print(f"\n##### QUERY {q}  ({len(todo)} unlabelled)")
            for r in todo:
                print(f"[{r['pid']}] {r['case'][:60]} ({r['zone']})\n{r['text'][:n]}\n")
        print("TOTAL UNLABELLED", total)
    elif cmd == "add":
        for chunk in sys.argv[3].split(";"):
            t = chunk.split()
            if not t:
                continue
            q, rest = t[0], t[1:]
            d = labels.setdefault(q, {})
            for i in range(0, len(rest), 2):
                assert rest[i + 1] in {"N", "T", "S", "O", "M"}, rest[i:i + 2]
                d[str(int(rest[i]))] = rest[i + 1]
        json.dump(labels, open(D / f"labels_{split}.json", "w"), indent=1)
        print({q: len(v) for q, v in labels.items()})


if __name__ == "__main__":
    main()
