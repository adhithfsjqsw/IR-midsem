"""Compute pilot-evaluation metrics from runs_<split>.json + labels_<split>.json.
Label codes per pooled passage: N = not relevant, T = relevant but neutral/no stance on the proposition,
S = supports the proposition, O = opposes / limits it, M = relevant, mixed.
Run:  python -X utf8 -m evalkit.metrics dev|test"""
import json
import sys
from pathlib import Path

D = Path(__file__).parent


def interleave(eb):
    s, o, out = list(eb["support"]), list(eb["oppose"]), []
    while s or o:
        if s:
            out.append(s.pop(0))
        if o:
            out.append(o.pop(0))
    return out + list(eb["contested"])


def evaluate(runs, labels):
    rows = {}
    for qid, systems in runs.items():
        lab = {int(k): v for k, v in labels[qid].items()}
        pool_S = sum(1 for v in lab.values() if v == "S")
        pool_O = sum(1 for v in lab.values() if v == "O")
        for name, out in systems.items():
            lst = out if isinstance(out, list) else interleave(out)
            top10 = lst[:10]
            rel = lambda p: lab.get(p, "N") != "N"
            r = dict(P5=sum(map(rel, lst[:5])) / 5, P10=sum(map(rel, top10)) / 10, returned=len(lst))
            S10 = sum(1 for p in top10 if lab.get(p) == "S"); O10 = sum(1 for p in top10 if lab.get(p) == "O")
            r["S_in_top10"], r["O_in_top10"] = S10, O10
            r["coverage"] = float(S10 > 0 and O10 > 0)
            r["S_recall"] = S10 / pool_S if pool_S else float("nan")
            r["O_recall"] = O10 / pool_O if pool_O else float("nan")
            if not isinstance(out, list):
                sup, opp = out["support"], out["oppose"]
                r["supP"] = sum(lab.get(p) == "S" for p in sup) / len(sup) if sup else float("nan")
                r["oppP"] = sum(lab.get(p) == "O" for p in opp) / len(opp) if opp else float("nan")
                r["supInv"] = sum(lab.get(p) == "O" for p in sup) / len(sup) if sup else float("nan")
                r["oppInv"] = sum(lab.get(p) == "S" for p in opp) / len(opp) if opp else float("nan")
                r["stance_coverage"] = float(any(lab.get(p) == "S" for p in sup) and any(lab.get(p) == "O" for p in opp))
                r["both_sides_returned"] = float(bool(sup) and bool(opp))
            rows.setdefault(name, {})[qid] = r
    return rows


def macro(rows):
    agg = {}
    for name, per_q in rows.items():
        keys = {k for r in per_q.values() for k in r}
        agg[name] = {}
        for k in keys:
            v = [r[k] for r in per_q.values() if k in r and r[k] == r[k]]
            agg[name][k] = sum(v) / len(v) if v else float("nan")
        agg[name]["n_queries"] = len(per_q)
    return agg


def table(agg, cols):
    head = "| system | " + " | ".join(cols) + " |\n|---|" + "---|" * len(cols) + "\n"
    body = ""
    for name, a in agg.items():
        body += f"| {name} | " + " | ".join(f"{a[c]:.2f}" if c in a and a[c] == a[c] else "-" for c in cols) + " |\n"
    return head + body


if __name__ == "__main__":
    split = sys.argv[1]
    runs = json.load(open(D / f"runs_{split}.json"))
    labels = json.load(open(D / f"labels_{split}.json"))
    rows = evaluate(runs, labels)
    agg = macro(rows)
    lists = {k: v for k, v in agg.items() if k.startswith("list")}
    ebs = {k: v for k, v in agg.items() if k.startswith("EB")}
    out = f"## {split} (n={len(runs)} queries)\n\n### Single ranked list (top-10 judgments)\n" + \
          table(lists, ["P5", "P10", "S_in_top10", "O_in_top10", "coverage", "S_recall", "O_recall"]) + \
          "\n### Evidence-balanced output (support list + oppose list, <=5 each; P@k over interleaved list)\n" + \
          table(ebs, ["P5", "P10", "returned", "supP", "oppP", "supInv", "oppInv", "stance_coverage", "both_sides_returned", "S_recall", "O_recall"])
    print(out)
    (D / f"results_{split}.md").write_text(out, encoding="utf-8")
    json.dump(rows, open(D / f"results_{split}_perquery.json", "w"), indent=1)
