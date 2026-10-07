import json, sys
split, qid = sys.argv[1], sys.argv[2]
n = int(sys.argv[3]) if len(sys.argv) > 3 else 900
P = json.load(open(f"evalkit/pool_{split}.json", encoding="utf-8"))
print("QUERY", qid)
for r in P[qid]:
    print(f"[{r['pid']}] {r['case'][:60]} ({r['zone']})\n{r['text'][:n]}\n")
