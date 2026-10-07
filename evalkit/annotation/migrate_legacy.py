"""Import the legacy single-letter labels (evalkit/labels_*.json) into the v2 record format WITHOUT modifying the originals.
Mapping is lossy by design and flagged:  N->NOT_RELEVANT ; T->RELEVANT/NEUTRAL_OR_CONTEXT ; S->RELEVANT/SUPPORTS ;
O->RELEVANT/OPPOSES ; M->RELEVANT/MIXED.  speaker_role=UNCLEAR, no evidence span, confidence=NOT_RECORDED, label_source=AI,
review_status=UNREVIEWED, guideline_version=legacy-0.  Legacy stance labels therefore do NOT satisfy the v2 rules (no role, no span)
and are only used for comparison, never as v2 ground truth.
Run: python -X utf8 -m evalkit.annotation.migrate_legacy"""
import json
from pathlib import Path

from evalkit.annotation.schema import STORE, needs_review

E = Path(__file__).resolve().parent.parent
PROPS = json.load(open(Path(__file__).parent / "propositions.json", encoding="utf-8"))
MAP = {"N": ("NOT_RELEVANT", "NEUTRAL_OR_CONTEXT"), "T": ("RELEVANT", "NEUTRAL_OR_CONTEXT"), "S": ("RELEVANT", "SUPPORTS"),
       "O": ("RELEVANT", "OPPOSES"), "M": ("RELEVANT", "MIXED")}


def main():
    out = []
    for split in ("dev", "test", "fresh"):
        labels = json.load(open(E / f"labels_{split}.json"))
        pool = json.load(open(E / f"pool_{split}.json", encoding="utf-8"))
        for q, items in labels.items():
            for pid, code in items.items():
                rel, st = MAP[code]
                r = dict(query_id=q, exact_proposition=PROPS[q]["proposition"], passage_id=int(pid), relevance=rel, court_stance=st,
                         speaker_role="UNCLEAR", party_argument_stance="UNCERTAIN", evidence_span="",
                         rationale="Imported from legacy single-letter label; no evidence or role was recorded.",
                         confidence="NOT_RECORDED", review_status="UNREVIEWED", label_source="AI", guideline_version="legacy-0",
                         annotator_id="claude-legacy", annotation_pass="legacy", context_seen=False, legacy_code=code, split=split)
                r["needs_human_review"] = True
                out.append(r)
    STORE.mkdir(parents=True, exist_ok=True)
    path = STORE / "legacy_import.jsonl"
    if path.exists():
        print("legacy_import.jsonl already exists; not overwriting"); return
    with open(path, "w", encoding="utf-8") as f:
        for r in out:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print("imported", len(out), "legacy labels ->", path)


if __name__ == "__main__":
    main()
