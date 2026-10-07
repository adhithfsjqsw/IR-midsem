"""Final result tables + figure.  Run: python -X utf8 -m evalkit.summary
Reads runs_<split>.json / labels_<split>.json for dev, test, fresh (final system) and writes
evalkit/RESULTS.md and evalkit/fig_results.png."""
import json
from pathlib import Path

from evalkit.metrics import evaluate, macro, table

D = Path(__file__).parent


def load(split):
    return json.load(open(D / f"runs_{split}.json")), json.load(open(D / f"labels_{split}.json"))


def combined(splits):
    runs, labels = {}, {}
    for s in splits:
        r, l = load(s)
        runs.update(r)
        labels.update(l)
    return runs, labels


def section(title, splits):
    runs, labels = combined(splits)
    agg = macro(evaluate(runs, labels))
    lists = {k: v for k, v in agg.items() if k.startswith("list")}
    ebs = {k: v for k, v in agg.items() if k.startswith("EB")}
    txt = f"## {title} (n={len(runs)} queries)\n\n**Single ranked list, top-10 judgments**\n\n" + \
          table(lists, ["P5", "P10", "S_in_top10", "O_in_top10", "coverage", "S_recall", "O_recall"]) + \
          "\n**Evidence-balanced output (support list + oppose list)**\n\n" + \
          table(ebs, ["P5", "P10", "returned", "supP", "oppP", "supInv", "oppInv", "stance_coverage", "both_sides_returned"]) + "\n"
    return txt, agg


def main():
    out = "# Pilot evaluation (hackathon time constraint; judgments AI-assisted, see report)\n\n"
    out += "Metric key: P5/P10 = fraction of top-k judgments (best passage) judged relevant; S/O_in_top10 = passages judged supporting / opposing in the top-10; " \
           "coverage = fraction of queries whose top-10 contains >=1 S and >=1 O (unlabelled single list); S/O_recall = pooled recall of S/O passages; " \
           "supP/oppP = precision of the support/oppose list (strict: label must equal S/O); supInv/oppInv = stance inversion rate; " \
           "stance_coverage = fraction of queries where the support list has >=1 true S AND the oppose list has >=1 true O.\n\n"
    aggs = {}
    for title, splits in [("DEV (3 queries; used to set parameters)", ["dev"]),
                          ("TEST (12 queries; final system, but inspected once under v1 - see report)", ["test"]),
                          ("FRESH (8 queries; written after freeze, never inspected before pooling)", ["fresh"]),
                          ("ALL HELD-OUT (TEST+FRESH, 20 queries)", ["test", "fresh"])]:
        txt, agg = section(title, splits)
        out += txt + "\n"
        aggs[title] = agg
    (D / "RESULTS.md").write_text(out, encoding="utf-8")
    json.dump(aggs, open(D / "results_all.json", "w"), indent=1)
    print(out)
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        agg = aggs["ALL HELD-OUT (TEST+FRESH, 20 queries)"]
        names = [k for k in agg if k.startswith("list")]
        lab = ["A tf-idf", "B +Bool/syn", "C +prox", "D +zones", "E +auth"]
        fig, ax = plt.subplots(1, 3, figsize=(12, 3.2))
        for a, (key, ttl) in zip(ax, [("P10", "P@10 (relevance)"), ("S_recall", "Pooled recall of supporting passages"),
                                       ("O_recall", "Pooled recall of opposing passages")]):
            a.bar(lab, [agg[n][key] for n in names], color=["#8a8a8a"] + ["#2b6cb0"] * 4)
            a.set_title(ttl, fontsize=9); a.set_ylim(0, 1); a.tick_params(axis="x", labelsize=7, rotation=20)
        plt.tight_layout(); plt.savefig(D / "fig_results.png", dpi=160)
        print("figure written")
    except Exception as e:
        print("no figure:", e)


if __name__ == "__main__":
    main()

