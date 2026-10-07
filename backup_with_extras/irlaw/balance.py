"""Evidence-balanced assembly: runs the SAME engine twice (support spec, oppose spec), then assigns each
judgment to at most one side.  No retrieval logic lives here -- only bookkeeping and the abstention rule."""
from __future__ import annotations

from dataclasses import dataclass, replace

from .engine import Config, Index, parse_query, search

TAU = 1.0          # minimum stance margin for a judgment to be labelled at all
CONTEST_RATIO = 1.3  # both sides within this ratio -> 'contested' (not counted on either side)
POOL = 40          # judgments pulled from each spec before assignment


def evidence_balanced(ix: Index, query: str, cfg: Config | None = None, k: int = 5):
    cfg = cfg or Config()
    out, dbg = {}, {}
    for side in ("support", "oppose"):
        parsed = parse_query(ix, query, cfg)  # same parse for both specs
        hits, d, parsed = search(ix, query, replace(cfg, stance=side), POOL, parsed)
        out[side] = {h.doc_id: h for h in hits}
        dbg[side] = d
    assigned = {"support": [], "oppose": [], "contested": []}
    for did in set(out["support"]) | set(out["oppose"]):
        hs, ho = out["support"].get(did), out["oppose"].get(did)
        cs = hs.trace["cue"] if hs else 0.0
        co = ho.trace["cue"] if ho else 0.0
        if max(cs, co) < TAU:
            continue
        if min(cs, co) > 0 and max(cs, co) / min(cs, co) < CONTEST_RATIO:
            assigned["contested"].append(hs if cs >= co else ho)
        elif cs > co:
            assigned["support"].append(hs)
        else:
            assigned["oppose"].append(ho)
    for lst in assigned.values():
        lst.sort(key=lambda h: -h.score)
    shown = {s: assigned[s][:k] for s in assigned}
    ns, no, nc = len(assigned["support"]), len(assigned["oppose"]), len(assigned["contested"])
    if ns and no:
        verdict = "The retrieved corpus contains passages pointing in different directions on this proposition (potentially divergent judicial positions)."
    elif ns:
        verdict = "Supporting evidence was found; no sufficiently strong opposing evidence was found in this corpus."
    elif no:
        verdict = "Opposing evidence was found; no sufficiently strong supporting evidence was found in this corpus."
    else:
        verdict = "Insufficient evidence: no passage met the minimum stance threshold. Showing no stance-labelled results."
    return dict(support=shown["support"], oppose=shown["oppose"], contested=shown["contested"][:3],
                counts=dict(support=ns, oppose=no, contested=nc), verdict=verdict, debug=dbg,
                parsed=parsed, tau=TAU)

