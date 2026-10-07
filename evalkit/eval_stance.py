"""Compare the automatic stance classifier with the phrase-cue baseline on the SAME pooled candidate passages.

  python -X utf8 -m evalkit.eval_stance <split>[,<split>...] [--ref "<glob>"] [--auto "<glob>"] [--out evalkit/RESULTS_stance_auto.md]

Reference = the existing AI-assisted v2 labels (guideline v1.1 pass). They are NOT verified truth, so every number is agreement
with an unverified reference. The automatic labels must first be produced with
  python -X utf8 -m evalkit.annotation.autolabel <split>          (needs ANTHROPIC_API_KEY)
If no automatic label file exists, only the phrase baseline is scored and the report says the classifier was NOT evaluated.
Globs are relative to evalkit/annotation/labels_v2/. Nothing here tunes any parameter; results are written to a new file."""
import argparse
import collections
import json
from pathlib import Path

from evalkit.annotation.schema import load_store

E = Path(__file__).resolve().parent
BASE_SYSTEM = "EB|E +authority g(d)"  # phrase-cue evidence-balanced baseline (full pipeline)


def load(pattern):
    return {(r["query_id"], r["passage_id"]): r for r in load_store(pattern)}


def ref_stance(r, strict=True):
    if r is None:
        return None
    ok = r["confidence"] in (("HIGH", "MEDIUM") if strict else ("HIGH", "MEDIUM", "LOW"))
    return r["court_stance"] if (r["court_stance"] in ("SUPPORTS", "OPPOSES") and ok) else "OTHER"


def prec(preds, ref, want, strict):
    sel = [k for k, v in preds.items() if v == want]
    if not sel:
        return None, 0
    return sum(ref_stance(ref.get(k), strict) == want for k in sel) / len(sel), len(sel)


def fmt(x):
    return "n/a" if x is None else f"{x:.2f}"


def evaluate(splits, ref_glob, auto_glob):
    lines = []
    for split in splits:
        pool = json.load(open(E / f"pool_{split}.json", encoding="utf-8"))
        runs = json.load(open(E / f"runs_{split}.json", encoding="utf-8"))
        ref = load(ref_glob.format(split=split))
        auto = load(auto_glob.format(split=split))
        base = {}
        for q, systems in runs.items():
            out = systems.get(BASE_SYSTEM)
            if out:
                for p in out["support"]:
                    base[(q, p)] = "SUPPORTS"
                for p in out["oppose"]:
                    base[(q, p)] = "OPPOSES"
        pooled = {(q, r["pid"]) for q, rows in pool.items() for r in rows}
        labelled_ref = pooled & set(ref)
        lines.append(f"### Split `{split}`: {len(pool)} queries, {len(pooled)} pooled passages, {len(labelled_ref)} with a reference label")
        # phrase baseline on the whole pool
        for strict in (True, False):
            sp, ns = prec({k: v for k, v in base.items() if k in ref}, ref, "SUPPORTS", strict)
            op, no = prec({k: v for k, v in base.items() if k in ref}, ref, "OPPOSES", strict)
            lines.append(f"- phrase baseline (whole pool, {'strict' if strict else 'lenient'}): support precision {fmt(sp)} (n={ns}), "
                         f"oppose precision {fmt(op)} (n={no}); abstains on {len(labelled_ref) - ns - no} of {len(labelled_ref)} pooled passages")
        both = {k for k in auto if k in ref and k in pooled}
        if not auto or not both:
            lines.append("- **Automatic classifier: NOT EVALUATED** - no automatic label file for this split (requires a configured API key). "
                         f"Reproduce with: `python -X utf8 -m evalkit.annotation.autolabel {split}` then "
                         f"`python -X utf8 -m evalkit.eval_stance {split}`.\n")
            continue
        qn = len({k[0] for k in both})
        cnt = collections.Counter(auto[k]["court_stance"] for k in both)
        lines.append(f"- compared on the SAME {len(both)} passages ({qn} queries) labelled by both the automatic classifier and the reference")
        lines.append("- automatic predictions on them: " + ", ".join(f"{s}={cnt.get(s, 0)}" for s in ("SUPPORTS", "OPPOSES", "MIXED", "NEUTRAL_OR_CONTEXT", "UNCERTAIN")))
        for strict in (True, False):
            ap = {k: auto[k]["court_stance"] for k in both}
            bp = {k: base.get(k, "ABSTAIN") for k in both}
            for name, preds in (("automatic classifier", ap), ("phrase baseline", bp)):
                sp, ns = prec(preds, ref, "SUPPORTS", strict)
                op, no = prec(preds, ref, "OPPOSES", strict)
                cov = (ns + no) / len(both)
                lines.append(f"  - {name} ({'strict' if strict else 'lenient'}): support precision {fmt(sp)} (n={ns}), oppose precision {fmt(op)} (n={no}), "
                             f"decided coverage {cov:.2f}, abstained/mixed/contextual {len(both) - ns - no}")
        # role agreement and S/O reversals
        role = sum(auto[k]["speaker_role"] == ref[k]["speaker_role"] for k in both) / len(both)
        rev = sum({auto[k]["court_stance"], ref[k]["court_stance"]} == {"SUPPORTS", "OPPOSES"} for k in both)
        lines.append(f"  - role agreement with reference {role:.2f}; direct SUPPORTS<->OPPOSES reversals {rev}")
        lines.append("")
    return lines


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("splits")
    ap.add_argument("--ref", default="*passA11__{split}*")
    ap.add_argument("--auto", default="auto-*__auto1__{split}*")
    ap.add_argument("--out", default=str(E / "RESULTS_stance_auto.md"))
    a = ap.parse_args()
    lines = ["# Automatic stance classifier vs phrase baseline (new-version output; older RESULTS*.md are untouched)\n",
             "Reference = AI-assisted, unreviewed v2 labels (not verified truth). Numbers are agreement with that reference. "
             "The classifier is never tuned on these sets. Phrase-baseline figures describe the OLD system only.\n"]
    lines += evaluate(a.splits.split(","), a.ref, a.auto)
    Path(a.out).write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
