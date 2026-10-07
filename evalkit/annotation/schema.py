"""Label schema v2 + validation.  One JSON record per (query, passage, annotator pass).  Append-only storage in
evalkit/annotation/labels_v2/*.jsonl  — existing records are never edited or deleted; a new pass adds new records."""
from __future__ import annotations

import json
import re
from pathlib import Path

HERE = Path(__file__).parent
STORE = HERE / "labels_v2"

RELEVANCE = {"RELEVANT", "NOT_RELEVANT", "UNCERTAIN"}
STANCE = {"SUPPORTS", "OPPOSES", "MIXED", "NEUTRAL_OR_CONTEXT", "UNCERTAIN"}
ROLE = {"COURT_HOLDING", "COURT_REASONING", "PARTY_ARGUMENT", "QUOTED_PRECEDENT", "STATUTE_OR_RULE",
        "FACTUAL_OR_PROCEDURAL_BACKGROUND", "OTHER", "UNCLEAR"}
PARTY = {"SUPPORTS", "OPPOSES", "NOT_APPLICABLE", "UNCERTAIN"}
CONF = {"HIGH", "MEDIUM", "LOW", "NOT_RECORDED"}          # NOT_RECORDED only for imported legacy labels
REVIEW = {"UNREVIEWED", "HUMAN_REVIEWED", "DISAGREEMENT", "ADJUDICATED"}
SOURCE = {"AI", "HUMAN", "HUMAN_ADJUDICATED"}
FIELDS = ["query_id", "exact_proposition", "passage_id", "relevance", "court_stance", "speaker_role", "party_argument_stance",
          "evidence_span", "rationale", "confidence", "review_status", "label_source", "guideline_version",
          "annotator_id", "annotation_pass", "needs_human_review", "context_seen", "legacy_code"]

COURT_ROLES = {"COURT_HOLDING", "COURT_REASONING"}


def norm_ws(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def needs_review(r: dict) -> bool:
    return (r["confidence"] in ("LOW", "NOT_RECORDED") or r["court_stance"] in ("MIXED", "UNCERTAIN")
            or r["speaker_role"] == "UNCLEAR" or r["relevance"] == "UNCERTAIN")


def validate(r: dict, passage_text: str | None = None) -> list[str]:
    """-> list of problems (empty = valid)."""
    errs = []
    for f, allowed in (("relevance", RELEVANCE), ("court_stance", STANCE), ("speaker_role", ROLE),
                       ("party_argument_stance", PARTY), ("confidence", CONF), ("review_status", REVIEW), ("label_source", SOURCE)):
        if r.get(f) not in allowed:
            errs.append(f"{f}={r.get(f)!r} not in {sorted(allowed)}")
    if errs:
        return errs
    if r["court_stance"] in ("SUPPORTS", "OPPOSES", "MIXED") and r["relevance"] != "RELEVANT":
        errs.append("a decided court stance requires relevance=RELEVANT")
    if r["court_stance"] in ("SUPPORTS", "OPPOSES") and r["speaker_role"] not in COURT_ROLES:
        errs.append("SUPPORTS/OPPOSES requires speaker_role COURT_HOLDING or COURT_REASONING")
    if r["speaker_role"] != "PARTY_ARGUMENT" and r["party_argument_stance"] not in ("NOT_APPLICABLE", "UNCERTAIN"):
        errs.append("party_argument_stance only for PARTY_ARGUMENT")
    if r["label_source"] == "AI" and r["review_status"] in ("HUMAN_REVIEWED", "ADJUDICATED"):
        errs.append("an AI label cannot be marked human-reviewed/adjudicated without a human record")
    span = r.get("evidence_span", "")
    if r["court_stance"] in ("SUPPORTS", "OPPOSES", "MIXED") and not span:
        errs.append("decided stance needs an evidence_span")
    if span and passage_text is not None:
        if norm_ws(span) not in norm_ws(passage_text):
            errs.append("evidence_span is not an exact substring of the passage (whitespace-normalised)")
    return errs


def load_store(pattern="*.jsonl"):
    out = []
    for f in sorted(STORE.glob(pattern)):
        for line in open(f, encoding="utf-8"):
            if line.strip():
                out.append(json.loads(line))
    return out


def append(path: Path, records: list[dict]):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
