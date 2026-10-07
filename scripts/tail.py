import json, sys
split, qid, start = sys.argv[1], sys.argv[2], int(sys.argv[3])
end = int(sys.argv[4]); pids = {int(x) for x in sys.argv[5:]}
P = json.load(open(f"evalkit/pool_{split}.json", encoding="utf-8"))
for r in P[qid]:
    if r["pid"] in pids:
        print(f"[{r['pid']}] {r['case'][:50]}\n...{r['text'][start:end]}\n")
