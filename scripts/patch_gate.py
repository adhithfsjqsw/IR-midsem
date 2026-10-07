"""One-off patch: add the topical gate to engine.search (stance cues only count for passages whose topical score is
within cfg.topical_gate of the best topical score of the query)."""
from pathlib import Path

p = Path("irlaw/engine.py")
t = p.read_text(encoding="utf-8")

a = t.index("    best_per_doc = {}\n    for pid in top.tolist():")
b = t.index("    # ---- document-level signals")
new = '''    best_per_doc = {}
    pre = {}
    for pid in top.tolist():
        base = float(score[pid])
        zone_boost = 0.0
        if cfg.zones and ix.pid_head[pid]:
            zone_boost = base * (cfg.headnote_mult - 1)
        prox_val, span, kmatch, window = 0.0, None, 0, None
        if cfg.prox and n_groups >= 2:
            d = pos_of.get(pid, {})
            kmatch = len(d)
            if kmatch >= 2:
                best = smallest_window([d[i] for i in sorted(d)])
                if best:
                    span, window = best[0], (best[1], best[2])
                    prox_val = (kmatch / span) * (kmatch / n_groups)
        pre[pid] = (base, zone_boost, prox_val, span, kmatch, window, base + zone_boost + cfg.w_prox * prox_val)
    best_topical = max((v[6] for v in pre.values()), default=0.0)
    for pid, (base, zone_boost, prox_val, span, kmatch, window, topical) in pre.items():
        eligible = topical >= cfg.topical_gate * best_topical      # stance may only re-order topically strong passages
        cues = cue_by_pid.get(pid, []) if eligible else []
        by_pol = {"support": [], "oppose": []}
        for c in cues:
            by_pol[c["polarity"]].append(c)
        sums = {p: sum(sorted((c["weight"] for c in l), reverse=True)[:3]) for p, l in by_pol.items()}
        side = sums.get(cfg.stance, 0.0) if cfg.stance else 0.0
        other = sums["oppose" if cfg.stance == "support" else "support"] if cfg.stance else 0.0
        cue_mult = cfg.cue_head_mult if (cfg.zones and ix.pid_head[pid]) else 1.0
        cue_val = max(side - cfg.lam_other * other, 0.0) * cue_mult
        s_total = topical + cfg.w_cue * cue_val
        did = int(ix.pid_doc[pid])
        cur = best_per_doc.get(did)
        if cur is None or s_total > cur[0]:
            best_per_doc[did] = (s_total, pid, dict(
                bm25=base, zone_boost=zone_boost, prox=prox_val, prox_span=span, prox_window=window,
                groups_matched=kmatch, cue=cue_val, cue_mult=cue_mult, cue_side=side, cue_other=other, cues=by_pol,
                topical=topical, best_topical=best_topical, gate_eligible=eligible))
'''
t = t[:a] + new + t[b:]
t = t.replace("    cue_head_mult: float = 1.5", "    topical_gate: float = 0.75  # stance cues only count for passages with topical score >= gate * best topical score\n    cue_head_mult: float = 1.5")
p.write_text(t, encoding="utf-8")
print("patched")
