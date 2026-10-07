"""Validate and append compact annotations to the append-only v2 store.
Input: a JSON file = list of {"q","pid","rel","st","role","party","span","why","conf"} with
 rel: R|N|U   st: S|O|M|C|U   role: CH|CR|PA|QP|SR|FB|OT|UN   party: S|O|NA|U   conf: H|M|L
Usage: python -X utf8 -m evalkit.annotation.ingest <file.json> <split> <guideline_version> <annotator_id> <pass_name>
Invalid records (bad enum, span not an exact substring of the passage, role/stance conflict) are NOT written; they are listed."""
import json
import pickle
import sys
from pathlib import Path

from evalkit.annotation.schema import STORE, append, needs_review, validate

ROOT = Path(__file__).resolve().parents[2]
PROPS = json.load(open(Path(__file__).parent / "propositions.json", encoding="utf-8"))
REL = {"R": "RELEVANT", "N": "NOT_RELEVANT", "U": "UNCERTAIN"}
ST = {"S": "SUPPORTS", "O": "OPPOSES", "M": "MIXED", "C": "NEUTRAL_OR_CONTEXT", "U": "UNCERTAIN"}
ROLE = {"CH": "COURT_HOLDING", "CR": "COURT_REASONING", "PA": "PARTY_ARGUMENT", "QP": "QUOTED_PRECEDENT", "SR": "STATUTE_OR_RULE",
        "FB": "FACTUAL_OR_PROCEDURAL_BACKGROUND", "OT": "OTHER", "UN": "UNCLEAR"}
PARTY = {"S": "SUPPORTS", "O": "OPPOSES", "NA": "NOT_APPLICABLE", "U": "UNCERTAIN"}
CONF = {"H": "HIGH", "M": "MEDIUM", "L": "LOW"}


def main():
    f, split, gv, annot, pas = sys.argv[1:6]
    items = json.load(open(f, encoding="utf-8"))
    P = pickle.load(open(ROOT / "data" / "index.pkl", "rb"))["passages"]
    ok, bad = [], []
    for it in items:
        try:
            r = dict(query_id=it["q"], exact_proposition=PROPS[it["q"]]["proposition"], passage_id=int(it["pid"]),
                     relevance=REL[it["rel"]], court_stance=ST[it["st"]], speaker_role=ROLE[it["role"]],
                     party_argument_stance=PARTY[it["party"]], evidence_span=it.get("span", ""), rationale=it["why"],
                     confidence=CONF[it["conf"]], review_status="UNREVIEWED", label_source="AI", guideline_version=gv,
                     annotator_id=annot, annotation_pass=pas, context_seen=True, legacy_code="", split=split)
        except KeyError as e:
            bad.append((it.get("q"), it.get("pid"), f"bad/missing key {e}")); continue
        errs = validate(r, P[r["passage_id"]]["text"])
        # guideline >= 1.1: headnote-only evidence is the reporter's summary -> confidence capped at MEDIUM
        if gv >= "1.1" and P[r["passage_id"]]["zone"] == "headnote" and r["confidence"] == "HIGH" \
                and r["court_stance"] in ("SUPPORTS", "OPPOSES", "MIXED"):
            r["confidence"] = "MEDIUM"
            r["rationale"] += " [confidence capped at MEDIUM: evidence is a reporter's headnote]"
        r["needs_human_review"] = needs_review(r)
        (bad if errs else ok).append(r if not errs else (r["query_id"], r["passage_id"], "; ".join(errs)))
    out = STORE / f"{annot}__{pas}__{split}.jsonl"
    done = set()
    if out.exists():
        done = {(json.loads(l)["query_id"], json.loads(l)["passage_id"]) for l in open(out, encoding="utf-8") if l.strip()}
    new = [r for r in ok if (r["query_id"], r["passage_id"]) not in done]
    append(out, new)
    print(f"valid+written {len(new)} (skipped duplicates {len(ok)-len(new)}), rejected {len(bad)} -> {out.name}")
    for b in bad:
        print("  REJECT", b)


if __name__ == "__main__":
    main()
