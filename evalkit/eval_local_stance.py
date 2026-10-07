"""Score the local rule-based stance classifier on the pooled passages against the AI-assisted v2 reference labels.

  python -X utf8 -m evalkit.eval_local_stance dev            # development split (rules were adjusted using DEV only)
  python -X utf8 -m evalkit.eval_local_stance test,fresh     # held-out: run once; do not adjust rules after seeing these

Reference = unreviewed AI-assisted labels (guideline v1.1 pass), NOT verified truth, so every figure is agreement with that reference.
The phrase-cue baseline on the same passages is shown for comparison. Output: evalkit/RESULTS_local_stance.md (appended per run)."""
import collections
import json
import sys
import time
from pathlib import Path

from evalkit.annotation.schema import load_store
from irlaw.local_stance import classify_local
from irlaw.stance import classify_items_local

E = Path(__file__).parent
PROPS = json.load(open(E / "annotation" / "propositions.json", encoding="utf-8"))
BASE = "EB|E +authority g(d)"


def run(splits, out_name="RESULTS_local_stance.md"):
    lines = [f"\n## Run {time.strftime('%Y-%m-%d %H:%M')} - splits: {','.join(splits)}\n"]
    ref = {(r["query_id"], r["passage_id"]): r for r in load_store("*passA11__*.jsonl")}
    pred, rows_all = {}, []
    for split in splits:
        pool = json.load(open(E / f"pool_{split}.json", encoding="utf-8"))
        runs = json.load(open(E / f"runs_{split}.json", encoding="utf-8"))
        for q, rows in pool.items():
            items = [{"id": str(r["pid"]), "passage": r["text"], "zone": r["zone"]} for r in rows]
            labs = classify_items_local(PROPS[q]["proposition"], items)
            for r in rows:
                pred[(q, r["pid"])] = labs[str(r["pid"])]
            b = runs[q].get(BASE, {})
            for p in b.get("support", []):
                pred.setdefault(("base", q, p), "SUPPORTS")
            for p in b.get("oppose", []):
                pred.setdefault(("base", q, p), "OPPOSES")
    keys = [k for k in pred if len(k) == 2 and k in ref]
    base = {k[1:]: v for k, v in pred.items() if len(k) == 3}
    lines.append(f"- queries: {len({k[0] for k in keys})}, passages compared: {len(keys)} (all have a reference label)")
    cnt = collections.Counter(pred[k]["stance"] for k in keys)
    lines.append("- local predictions: " + ", ".join(f"{s}={cnt.get(s, 0)}" for s in ("SUPPORTS", "OPPOSES", "MIXED", "NEUTRAL_OR_CONTEXT", "UNCERTAIN")))

    def rstance(k, strict=True):
        r = ref[k]
        ok = r["confidence"] in (("HIGH", "MEDIUM") if strict else ("HIGH", "MEDIUM", "LOW"))
        return r["court_stance"] if r["court_stance"] in ("SUPPORTS", "OPPOSES") and ok else "OTHER"

    for strict in (True, False):
        tag = "strict" if strict else "lenient"
        for want in ("SUPPORTS", "OPPOSES"):
            sel = [k for k in keys if pred[k]["stance"] == want]
            hit = sum(rstance(k, strict) == want for k in sel)
            refs = [k for k in keys if rstance(k, strict) == want]
            rec = sum(pred[k]["stance"] == want for k in refs)
            bsel = [k for k in keys if base.get(k) == want]
            bhit = sum(rstance(k, strict) == want for k in bsel)
            lines.append(f"- {want.lower()} ({tag}): local precision {hit}/{len(sel)} = {hit / max(len(sel), 1):.2f}, recall of reference {rec}/{len(refs)} = "
                         f"{rec / max(len(refs), 1):.2f}; phrase baseline precision {bhit}/{len(bsel)} = {bhit / max(len(bsel), 1):.2f}")
    rev = sum({pred[k]["stance"], ref[k]["court_stance"]} == {"SUPPORTS", "OPPOSES"} for k in keys)
    role = sum(pred[k]["role"] == ref[k]["speaker_role"] for k in keys) / max(len(keys), 1)
    noncourt = [k for k in keys if ref[k]["speaker_role"] in ("PARTY_ARGUMENT", "QUOTED_PRECEDENT", "STATUTE_OR_RULE", "FACTUAL_OR_PROCEDURAL_BACKGROUND")]
    leak = sum(pred[k]["stance"] in ("SUPPORTS", "OPPOSES") for k in noncourt)
    decided = sum(pred[k]["stance"] in ("SUPPORTS", "OPPOSES") for k in keys)
    lines.append(f"- decided coverage {decided}/{len(keys)} = {decided / max(len(keys), 1):.2f}; direct SUPPORTS<->OPPOSES reversals vs reference: {rev}; "
                 f"role agreement {role:.2f}; decided stance on passages the reference calls party/quoted/statute/background: {leak}/{len(noncourt)}")
    # confusion
    cm = collections.Counter((pred[k]["stance"][:4], ref[k]["court_stance"][:4]) for k in keys)
    lines.append("- confusion (local/reference): " + ", ".join(f"{a}/{b}={n}" for (a, b), n in sorted(cm.items(), key=lambda x: -x[1])[:14]))
    path = E / out_name
    old = path.read_text(encoding="utf-8") if path.exists() else "# Local rule-based stance classifier vs AI-assisted reference (append-only log of runs)\n"
    path.write_text(old + "\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    return keys, pred, ref


if __name__ == "__main__":
    run(sys.argv[1].split(","))
