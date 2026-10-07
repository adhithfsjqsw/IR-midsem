"""Automatic (model) labelling of pooled query-passage pairs with the SAME classifier the app uses (irlaw.stance).

  python -X utf8 -m evalkit.annotation.autolabel <split> [--queries F1,F2] [--limit N] [--offset N] [--max-calls N] [--dry-run]

 * Needs ANTHROPIC_API_KEY (+ optional STANCE_MODEL); without it the command exits without writing anything.
 * Input: evalkit/pool_<split>.json (pooled passages) + propositions.json (exact proposition). Neighbouring passages of the same
   judgment are supplied as context.
 * Output: append-only evalkit/annotation/labels_v2/auto-<model>__<pass>__<split>.jsonl in schema v2. label_source=AI,
   review_status=UNREVIEWED, `automatic=true`. No human review is implied or required. Existing legacy / v2 files are never touched.
 * Idempotent and resumable: (query_id, passage_id) pairs already present in that output file are skipped.
 * Every record is validated with schema.validate before it is written; rejected items are logged to
   labels_v2/rejected/auto_rejected.jsonl and not written.
 * --limit/--offset bound the batch (per query); --max-calls bounds the number of model requests in this run.
"""
import argparse
import json
import pickle
import re
import sys
import time
from pathlib import Path

from evalkit.annotation.schema import STORE, append, needs_review, validate
from irlaw import stance as S

E = Path(__file__).resolve().parent.parent
ROOT = E.parent
PROPS = json.load(open(Path(__file__).parent / "propositions.json", encoding="utf-8"))
PASS = "auto1"
GUIDELINE = "auto-1.0"  # automatic prompt aligned with guideline v1.1 (see irlaw/stance.py SYSTEM, PROMPT_VERSION)


def safe(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", s)


def to_record(qid, pid, split, lab, model, passage, provider="anthropic"):
    r = dict(query_id=qid, exact_proposition=PROPS[qid]["proposition"], passage_id=int(pid), relevance=lab["relevance"],
             court_stance=lab["stance"], speaker_role=lab["role"],
             party_argument_stance="UNCERTAIN" if lab["role"] == "PARTY_ARGUMENT" else "NOT_APPLICABLE",
             evidence_span=lab["evidence_span"], rationale=lab["rationale"], confidence=lab["confidence"],
             review_status="UNREVIEWED", label_source="AI", guideline_version=GUIDELINE, annotator_id=f"auto:{model}",
             annotation_pass=PASS, context_seen=True, legacy_code="", split=split, automatic=True, provider=provider,
             model=model, prompt_version=S.PROMPT_VERSION, labelled_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
             provisional=True)
    r["needs_human_review"] = needs_review(r)
    return r


def main(argv=None, client=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("split")
    ap.add_argument("--queries", default="")
    ap.add_argument("--limit", type=int, default=10**9)
    ap.add_argument("--offset", type=int, default=0)
    ap.add_argument("--max-calls", type=int, default=10**9)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--provider", choices=["anthropic", "ollama"], default="anthropic",
                    help="anthropic (needs ANTHROPIC_API_KEY) or ollama (free local model, OLLAMA_MODEL)")
    a = ap.parse_args(argv)
    ollama = a.provider == "ollama" and client is None
    if ollama:
        from irlaw.respond import ollama_available, ollama_model
        model = f"ollama:{ollama_model()}"
        if not a.dry_run and not ollama_available():
            sys.exit(f"Ollama is not reachable or model {ollama_model()!r} is not pulled: nothing labelled, nothing written.")
        client = S.OllamaClient() if not a.dry_run else None
    else:
        model = S.model_name()
        if client is None and not a.dry_run and not S.api_available():
            sys.exit("ANTHROPIC_API_KEY is not set: nothing labelled, nothing written. (Use --dry-run to count pending items, or --provider ollama.)")
    pool = json.load(open(E / f"pool_{a.split}.json", encoding="utf-8"))
    P = pickle.load(open(ROOT / "data" / "index.pkl", "rb"))["passages"]
    out = STORE / f"auto-{safe(model)}__{PASS}__{a.split}.jsonl"
    done = set()
    if out.exists():
        for line in open(out, encoding="utf-8"):
            if line.strip():
                j = json.loads(line)
                done.add((j["query_id"], j["passage_id"]))
    wanted = [q for q in a.queries.split(",") if q] or list(pool)
    written = rejected = skipped = 0
    calls_left = a.max_calls
    rej_path = STORE / "rejected" / "auto_rejected.jsonl"
    for qid in wanted:
        rows = pool[qid][a.offset:a.offset + a.limit]
        todo = [r for r in rows if (qid, r["pid"]) not in done]
        skipped += len(rows) - len(todo)
        if a.dry_run or not todo:
            print(f"{qid}: pending {len(todo)}, already labelled {len(rows) - len(todo)}")
            continue
        batch = S._int_env("STANCE_BATCH", 4 if ollama else 6, 1, 20)
        todo = todo[: calls_left * batch]
        if not todo:
            print("max-calls reached"); break
        items = []
        for r in todo:
            pid = r["pid"]
            ctx = {"zone": P[pid].get("zone", "unknown"), "passage": P[pid]["text"],
                   "previous_context": P[pid - 1]["text"][-500:] if pid > 0 and P[pid - 1]["doc_id"] == P[pid]["doc_id"] else "",
                   "next_context": P[pid + 1]["text"][:500] if pid + 1 < len(P) and P[pid + 1]["doc_id"] == P[pid]["doc_id"] else ""}
            items.append({"id": str(pid), "case": r.get("case", ""), **ctx})
        labels, info = S.classify_items(PROPS[qid]["proposition"], items, client, model=model if ollama else None, batch_default=4 if ollama else 6)
        calls_left -= max(info["n_called"], 1)
        if not info["available"]:
            print(f"{qid}: classifier unavailable ({info['error']}); nothing written for this query"); continue
        good = []
        for it in items:
            lab = labels.get(it["id"])
            if lab is None or not lab.get("output_validated"):
                # failed calls / malformed output: not written, so a later run retries them
                rejected += 1
                append(rej_path, [dict(query_id=qid, passage_id=int(it["id"]), reason=(lab or {}).get("rationale", "no label"), model=model)])
                continue
            rec = to_record(qid, it["id"], a.split, lab, model, it["passage"], "ollama" if ollama else "anthropic")
            errs = validate(rec, it["passage"])
            if errs:
                rejected += 1
                append(rej_path, [dict(query_id=qid, passage_id=int(it["id"]), reason="; ".join(errs), model=model)])
            else:
                good.append(rec)
        append(out, good)
        written += len(good)
        print(f"{qid}: wrote {len(good)}, rejected/failed {len(items) - len(good)}, cached {info['n_cached']}, calls {info['n_called']}")
        if calls_left <= 0:
            print("max-calls reached"); break
    print(f"done: wrote {written}, skipped existing {skipped}, rejected {rejected} -> {out.name}")


if __name__ == "__main__":
    main()
