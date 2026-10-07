"""Effect of the abstention rule (rarest concept mandatory + minimum concept coverage) on the 23 evaluation queries.
  python -X utf8 -m evalkit.eval_abstain   ->  evalkit/RESULTS_abstain.md  (new file; older results untouched)

Compares Config() (full pipeline, no abstention; the system scored in RESULTS.md) with STRICT (same + abstention) on the same queries.
Reference = AI-assisted, unreviewed v2 labels (guideline v1.1). Passages without a reference label are reported separately and are NOT
counted as relevant. Nothing is tuned on these sets: rare_df=0.005 and min_group_frac=0.5 were fixed before this run."""
from pathlib import Path

from evalkit.annotation.schema import load_store
from evalkit.queries import DEV, FRESH, TEST
from irlaw.engine import STRICT, Config, Index, search

E = Path(__file__).parent


def main():
    ix = Index()
    ref = {(r["query_id"], r["passage_id"]): r["relevance"] for r in load_store("*passA11__*.jsonl")}
    lines = ["# Abstention rule vs no abstention (new-version output)\n",
             "Reference: AI-assisted, unreviewed v2 labels. Top-10 judgments per query; unlabelled passages are not counted as relevant.\n",
             "| split | queries | system | mean results returned | queries returning 0 | P@returned (labelled only) | unlabelled returned |", "|---|---|---|---|---|---|---|"]
    for split, qs in (("dev", DEV), ("test", TEST), ("fresh", FRESH)):
        for name, cfg in (("no abstention", Config()), ("abstention (STRICT)", STRICT)):
            ret = zero = rel = lab = unl = 0
            for qid, q in qs.items():
                hits, _, _ = search(ix, q, cfg, 10)
                ret += len(hits); zero += not hits
                for h in hits:
                    r = ref.get((qid, h.pid))
                    if r is None:
                        unl += 1
                    else:
                        lab += 1; rel += r == "RELEVANT"
            lines.append(f"| {split} | {len(qs)} | {name} | {ret / len(qs):.1f} | {zero} | {rel / lab:.2f} (n={lab}) | {unl} |" if lab else
                         f"| {split} | {len(qs)} | {name} | {ret / len(qs):.1f} | {zero} | n/a | {unl} |")
    off = ["mural on a public wall", "Does painting a mural on a public wall require prior permission", "xyzzy quux blorf"]
    lines.append("\nOff-topic queries (no reference labels): results returned with abstention vs without")
    for q in off[1:]:
        lines.append(f"- {q!r}: no abstention {len(search(ix, q, Config(), 40)[0])}, abstention {len(search(ix, q, STRICT, 40)[0])}")
    (E / "RESULTS_abstain.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
