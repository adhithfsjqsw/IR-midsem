"""DEV judgments (AI-assisted: Claude read each pooled passage; team must spot-check - see report).
Codes: N not relevant | T relevant, neutral | S supports proposition | O opposes/limits | M relevant, mixed."""
import json
from pathlib import Path

L = {
 "D1": "125581 T 37774 S 110884 M 128446 N 138931 T 131900 N 191282 T 194654 N 66051 T 173302 T 68057 M 129081 S 103962 O "
       "1118 O 115725 N 46294 S 37776 T 65042 N 184867 T 103941 O 55376 N 19260 T 115886 S 97427 T 49221 N 176379 N 1120 O",
 "D2": "112456 T 50624 O 59302 T 164886 M 127994 O 90407 T 67058 O 111677 T 189444 T 82164 O 59316 S 189443 N 3210 S 90386 T "
       "151524 O 67085 T 170580 T 59187 T 44273 T 127849 N 59310 S 189378 N",
 "D3": "6395 T 108538 S 180394 T 54151 T 95702 O 165010 O 172047 O 59416 S 29820 T 172566 O 47581 O 54147 O 6389 T 7690 N 188607 T "
       "172492 O 83594 O 180392 S 172026 N 39395 S 123118 M 24490 O 137380 T 136664 T 83642 T 166182 T 180375 M 159344 N",
}
out = {}
for q, s in L.items():
    t = s.split()
    out[q] = {int(t[i]): t[i + 1] for i in range(0, len(t), 2)}
pool = json.load(open(Path(__file__).parent / "pool_dev.json", encoding="utf-8"))
for q in pool:
    missing = [r["pid"] for r in pool[q] if r["pid"] not in out[q]]
    print(q, "labelled", len(out[q]), "pool", len(pool[q]), "missing", missing)
json.dump(out, open(Path(__file__).parent / "labels_dev.json", "w"), indent=1)
