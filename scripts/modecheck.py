import sys
sys.path.insert(0, ".")
from evalkit.queries import ALL
from irlaw.balance import evidence_balanced
from irlaw.engine import Index
from irlaw.respond import build_pack, respond, verify_response

ix = Index()
for qid, q in ALL.items():
    r = evidence_balanced(ix, q); p = build_pack(ix, q, r)
    a, _ = respond("regular", p); b, _ = respond("professional", p)
    va, vb = verify_response(a, p), verify_response(b, p)
    if not (va["ok"] and vb["ok"] and a != b):
        print(qid, q, r["counts"], va, vb, a == b)
        print(a[:600])
