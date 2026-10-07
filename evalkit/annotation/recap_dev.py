"""Create the guideline-1.1 DEV records from the 1.0 DEV records by applying ONLY the mechanical headnote confidence cap
(no stance or relevance is changed).  Originals are kept; new records go to a new file with guideline_version 1.1."""
import json
import pickle
from pathlib import Path

from evalkit.annotation.schema import STORE, needs_review, validate

ROOT = Path(__file__).resolve().parents[2]
P = pickle.load(open(ROOT / "data" / "index.pkl", "rb"))["passages"]
src = STORE / "claude-annotator-A__passA__dev.jsonl"
dst = STORE / "claude-annotator-A__passA11__dev.jsonl"
assert not dst.exists(), "already created"
out, capped = [], 0
for line in open(src, encoding="utf-8"):
    r = json.loads(line)
    r["guideline_version"] = "1.1"
    r["annotation_pass"] = "passA11"
    if P[r["passage_id"]]["zone"] == "headnote" and r["confidence"] == "HIGH" and r["court_stance"] in ("SUPPORTS", "OPPOSES", "MIXED"):
        r["confidence"] = "MEDIUM"
        r["rationale"] += " [confidence capped at MEDIUM: evidence is a reporter's headnote]"
        capped += 1
    r["needs_human_review"] = needs_review(r)
    assert not validate(r, P[r["passage_id"]]["text"])
    out.append(r)
with open(dst, "w", encoding="utf-8") as f:
    for r in out:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")
print("wrote", len(out), "records; confidence capped on", capped)
