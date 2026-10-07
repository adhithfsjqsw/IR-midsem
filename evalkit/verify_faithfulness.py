"""Explanation-faithfulness test: for every hit the system returns on every evaluation query (support and oppose specs
and the plain list systems), recompute each claimed signal from RAW passage text and compare with the trace.
Also runs the Regular/Professional identity test.   python -X utf8 -m evalkit.verify_faithfulness"""
import json
from collections import Counter, defaultdict
from dataclasses import replace
from pathlib import Path

from evalkit.queries import ALL
from irlaw.balance import evidence_balanced
from irlaw.engine import ABLATIONS, Config, Index, parse_query, search
from irlaw.faithfulness import check_hit
from irlaw.respond import build_pack, respond, verify_response

D = Path(__file__).parent


def main():
    ix = Index()
    ok, tot = defaultdict(int), defaultdict(int)
    failures = []
    n_hits = 0
    for qid, q in ALL.items():
        for name, cfg in list(ABLATIONS.items()) + [("stance:support", replace(Config(), stance="support")),
                                                    ("stance:oppose", replace(Config(), stance="oppose"))]:
            parsed = parse_query(ix, q, cfg)
            hits, _, parsed = search(ix, q, cfg, 10, parsed)
            for h in hits:
                n_hits += 1
                for k, v in check_hit(ix, h, parsed, cfg).items():
                    tot[k] += 1
                    ok[k] += int(bool(v))
                    if not v:
                        failures.append((qid, name, h.pid, k))
    lines = [f"Faithfulness check over {n_hits} returned hits ({len(ALL)} queries x 7 system variants)\n",
             "| signal re-computed from raw text | checks | pass |", "|---|---|---|"]
    for k in sorted(tot):
        lines.append(f"| {k} | {tot[k]} | {ok[k]} ({100*ok[k]/tot[k]:.1f}%) |")
    lines.append(f"\nFailures: {len(failures)}  e.g. {failures[:8]}")

    # ---- mode identity: retrieval has no mode argument; verify packs and responses
    same, cites_ok = 0, 0
    for qid, q in ALL.items():
        r1 = evidence_balanced(ix, q); r2 = evidence_balanced(ix, q)
        p1, p2 = build_pack(ix, q, r1), build_pack(ix, q, r2)
        same += int(p1["sha256"] == p2["sha256"])
        a, _ = respond("regular", p1); b, _ = respond("professional", p1)
        cites_ok += int(verify_response(a, p1)["ok"] and verify_response(b, p1)["ok"] and a != b)
    lines.append(f"\nMode-identity test over {len(ALL)} queries: evidence-pack hash identical across two independent retrievals: {same}/{len(ALL)}; "
                 f"both generated responses cite only evidence ids/case ids present in the pack (and differ in wording): {cites_ok}/{len(ALL)}")
    txt = "\n".join(lines)
    (D / "FAITHFULNESS.md").write_text(txt, encoding="utf-8")
    print(txt)


if __name__ == "__main__":
    main()
