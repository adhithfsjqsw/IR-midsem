"""List items where two annotation passes differ.  python -X utf8 -m evalkit.annotation.disagreements <globA> <globB> <split>"""
import sys

from evalkit.annotation.analysis import recs

A, B = recs(sys.argv[1]), recs(sys.argv[2])
split = sys.argv[3]
n = 0
for k in sorted(A):
    if k in B and A[k].get("split") == split:
        a, b = A[k], B[k]
        if (a["relevance"], a["court_stance"]) != (b["relevance"], b["court_stance"]):
            n += 1
            print(f"{k[0]} {k[1]:>7}  A: {a['relevance'][:4]}/{a['court_stance'][:5]:5s}/{a['speaker_role'][:6]:6s}/{a['confidence'][0]}   B: {b['relevance'][:4]}/{b['court_stance'][:5]:5s}   | {a['rationale'][:150]}")
print("differing items:", n)
