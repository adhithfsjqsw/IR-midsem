"""Single retrieval engine used by the baseline, every ablation, the supporting spec and the opposing spec.

Stages (all on the SAME positional inverted index):
  parse query -> concept groups (stem + legal synonym variants)
  -> Boolean candidate generation: AND over concept groups (postings intersection, rarest group first;
     relaxed to >= n-1, n-2 ... groups only if too few candidates)
  -> BM25 over candidate passages (zone multiplier for headnote)
  -> top-N rerank: query-term proximity (positional index), stance-cue proximity with negation (positional index)
  -> aggregate passages to judgments (+ title zone, statute parametric, bench-size authority)
Every number that enters the final score is stored in a trace (see Hit.trace) so the explanation is the computation.
"""
from __future__ import annotations

import math
import pickle
import re
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from .lexicon import OPERATORS, REQUIREMENT_QUERY_WORDS, STATUTES, SYNONYMS
from .textproc import MODALS, NEGATORS, STOP, stem, tokenize

ROOT = Path(__file__).resolve().parent.parent
FILLER = frozenset("prior whether regarding between what when how where why under per upon without".split())
SHIFT = 16
NEG_WINDOW = 5  # a negator up to 5 token positions before an operator flips it


# ------------------------------------------------------------------ configuration
@dataclass(frozen=True)
class Config:
    boolean: bool = True        # Boolean AND over concept groups
    expand: bool = True         # legal synonym variants
    prox: bool = True           # query-term proximity
    zones: bool = True          # headnote boost + title zone + statute parametric
    authority: bool = True      # static quality g(d) = log2(bench size)
    stance: str | None = None   # None | 'support' | 'oppose'
    k1: float = 1.2
    b: float = 0.75
    headnote_mult: float = 1.25
    w_prox: float = 6.0
    w_cue: float = 2.5
    w_title: float = 1.5
    w_statute: float = 2.0
    w_auth: float = 0.6
    cue_window: int = 8
    rerank_n: int = 1500
    min_cands: int = 40
    generic_df: float = 0.20
    syn_max_df: float = 0.03   # index elimination: drop synonym variants too common to discriminate
    topical_gate: float = 0.75  # stance cues only count for passages with topical score >= gate * best topical score
    cue_head_mult: float = 1.5  # stance cues inside the headnote (the Court's own HELD statements) count more
    lam_other: float = 0.5     # stance margin = cue(side) - lam * cue(other side)


BASELINE = Config(boolean=False, expand=False, prox=False, zones=False, authority=False, stance=None)
ABLATIONS = {
    "A BM25 (baseline)": BASELINE,
    "B +Boolean concepts+synonyms": Config(prox=False, zones=False, authority=False),
    "C +proximity": Config(zones=False, authority=False),
    "D +zones/statute": Config(authority=False),
    "E +authority g(d)": Config(),
}


@dataclass
class Group:
    label: str
    variants: list  # [(stems tuple, weight, 'query'|'synonym')]


@dataclass
class Parsed:
    text: str
    groups: list
    statute_nums: list
    profile: str = "permission"
    dropped_generic: list = field(default_factory=list)


def in_sorted(x, arr):
    """membership of x in the SORTED array arr (searchsorted; avoids np.isin re-sorting huge arrays)"""
    if len(arr) == 0:
        return np.zeros(len(x), bool)
    i = np.searchsorted(arr, x)
    i[i >= len(arr)] = len(arr) - 1
    return arr[i] == x


# ------------------------------------------------------------------ index
class Index:
    def __init__(self, path=ROOT / "data" / "index.pkl"):
        d = pickle.load(open(path, "rb"))
        self.docs, self.passages = d["docs"], d["passages"]
        self.vocab, self.df, self.term_ptr = d["vocab"], d["df"], d["term_ptr"]
        self.post_pid, self.post_tf, self.post_off, self.pos = d["post_pid"], d["post_tf"], d["post_off"], d["pos"]
        self.plen, self.title_index = d["plen"], d["title_index"]
        self.N = len(self.passages)
        self.avgdl = float(self.plen.mean())
        self.pid_doc = np.fromiter((p["doc_id"] for p in self.passages), np.int32, self.N)
        self.pid_head = np.fromiter((p["zone"] == "headnote" for p in self.passages), bool, self.N)
        self._keys, self._cue = {}, {}
        self.syn_by_stem = {stem(k): v for k, v in SYNONYMS.items()}

    # --- dictionary / postings
    def rows(self, st):
        tid = self.vocab.get(st)
        if tid is None:
            e = np.zeros(0, np.int32)
            return e, e, e
        a, b = self.term_ptr[tid], self.term_ptr[tid + 1]
        return self.post_pid[a:b], self.post_tf[a:b], self.post_off[a:b]

    def idf(self, st):
        tid = self.vocab.get(st)
        df = int(self.df[tid]) if tid is not None else 0
        return math.log(1 + (self.N - df + 0.5) / (df + 0.5)), df

    def keys(self, st):
        """All occurrences of a stem as sorted int64 keys  pid<<16 | position  (the positional index)."""
        k = self._keys.get(st)
        if k is None:
            pids, tf, off = self.rows(st)
            if len(pids) == 0:
                k = np.zeros(0, np.int64)
            else:
                lo, hi = int(off[0]), int(off[-1] + tf[-1])
                k = (np.repeat(pids.astype(np.int64), tf) << SHIFT) | self.pos[lo:hi].astype(np.int64)
            self._keys[st] = k
        return k

    def phrase_keys(self, stems, gap=2):
        """Start keys of a phrase.  Stop words were dropped at index time but positions kept, so consecutive
        phrase terms may be 1..gap positions apart."""
        cur = self.keys(stems[0])
        last = cur.copy()
        for s in stems[1:]:
            nxt = self.keys(s)
            new_last = np.full(len(cur), -1, np.int64)
            for g in range(1, gap + 1):
                m = (new_last < 0) & in_sorted(last + g, nxt)
                new_last[m] = last[m] + g
            ok = new_last >= 0
            cur, last = cur[ok], new_last[ok]
            if len(cur) == 0:
                break
        return cur

    def variant_pids(self, stems):
        if len(stems) == 1:
            return self.rows(stems[0])[0]
        return np.unique(self.phrase_keys(stems) >> SHIFT)

    # --- cue lexicon matched on the positional index
    def cues(self, profile="permission"):
        if profile not in self._cue:
            neg = [self.keys(n) for n in {stem(n) for n in NEGATORS}]
            neg = np.unique(np.concatenate(neg)) if neg else np.zeros(0, np.int64)
            out = []
            for pol, lst in OPERATORS[profile].items():
                for phrase, w in lst:
                    stems = tuple(stem(t) for t in tokenize(phrase) if t not in STOP or t in NEGATORS)
                    if not stems:
                        continue
                    ks = self.phrase_keys(stems)
                    if len(ks) == 0:
                        continue
                    inherent_neg = any(s in {stem(n) for n in NEGATORS} for s in stems)
                    negated = np.zeros(len(ks), bool)
                    if not inherent_neg:
                        for g in range(1, NEG_WINDOW + 1):
                            negated |= in_sorted(ks - g, neg)
                    out.append(dict(phrase=phrase, pol=pol, w=w, keys=ks, negated=negated))
            self._cue[profile] = out
        return self._cue[profile]


# ------------------------------------------------------------------ query parsing
def parse_query(ix: Index, text: str, cfg: Config) -> Parsed:
    low = text.lower()
    statute_nums = [m.group(2) for m in re.finditer(r"\b(section|sec\.?|article|art\.?)\s*(\d+[a-z]?)", low)]
    groups, seen = [], {}
    toks = tokenize(text)
    consumed = set()
    # --- phrase concepts: "section 125" / "article 16" and known statute names (positional phrase queries)
    for i, tok in enumerate(toks[:-1]):
        if tok in ("section", "sec", "article", "art") and re.fullmatch(r"\d+[a-z]?", toks[i + 1]):
            consumed |= {i, i + 1}
            groups.append(Group(f"{tok} {toks[i + 1]}", [((stem(tok), toks[i + 1]), 1.0, "query")]))
    ct = [(i, t) for i, t in enumerate(toks) if t not in STOP or t in ("of",)]
    ct = [(i, t) for i, t in ct if t != "of"]
    for name, abbrs in STATUTES:
        n = len(name)
        for j in range(len(ct) - n + 1):
            if [t for _, t in ct[j:j + n]] == name:
                idxs = {i for i, _ in ct[j:j + n]}
                consumed |= idxs
                variants = [(tuple(stem(w) for w in name), 1.0, "query")]
                variants += [(tuple(stem(w) for w in a), 0.9, "synonym") for a in abbrs]
                groups.append(Group(" ".join(name), variants))
                break
    for ti, tok in enumerate(toks):
        if ti in consumed:
            continue
        if tok in STOP or tok in NEGATORS or tok in FILLER or tok in MODALS:
            continue
        st = stem(tok)
        if st in seen:
            continue
        variants = [((st,), 1.0, "query")]
        if cfg.expand:
            for syn in ix.syn_by_stem.get(st, []):
                sst = tuple(stem(t) for t in tokenize(syn) if t not in STOP)
                if sst and all((sst, 0.6, "synonym")[0] != v[0] for v in variants):
                    variants.append((sst, 0.6, "synonym"))
        seen[st] = len(groups)
        groups.append(Group(tok, variants))
    # drop duplicate concepts: a later group whose query stem is already a variant of an earlier group
    merged = []
    for g in groups:
        host = next((m for m in merged if (stem(g.label),) in [v[0] for v in m.variants]), None)
        if host is None:
            merged.append(g)
    profile = "requirement" if any(t in REQUIREMENT_QUERY_WORDS for t in tokenize(text)) else "permission"
    return Parsed(text, merged, statute_nums, profile)


# ------------------------------------------------------------------ scoring
def bm25_term(ix, cfg, st):
    """-> (pids, contribution array, idf, df) for one stem."""
    pids, tf, _ = ix.rows(st)
    idf, df = ix.idf(st)
    if len(pids) == 0:
        return pids, np.zeros(0), idf, df
    dl = ix.plen[pids]
    c = idf * tf * (cfg.k1 + 1) / (tf + cfg.k1 * (1 - cfg.b + cfg.b * dl / ix.avgdl))
    return pids, c, idf, df


def smallest_window(plists):
    """plists: list of position lists (one per matched group). Smallest span covering one of each."""
    ev = sorted((p, g) for g, lst in enumerate(plists) for p in lst)
    need, have, cnt, best, l = len(plists), {}, 0, None, 0
    for r, (p, g) in enumerate(ev):
        have[g] = have.get(g, 0) + 1
        if have[g] == 1:
            cnt += 1
        while cnt == need:
            span = p - ev[l][0] + 1
            if best is None or span < best[0]:
                best = (span, ev[l][0], p)
            gl = ev[l][1]
            have[gl] -= 1
            if have[gl] == 0:
                cnt -= 1
            l += 1
    return best


@dataclass
class Hit:
    doc_id: int
    pid: int
    score: float
    trace: dict


def search(ix: Index, query: str, cfg: Config, topk_docs: int = 10, parsed: Parsed | None = None):
    """Returns (hits, debug).  hits are judgments ordered by score; each carries its best passage + trace."""
    parsed = parsed or parse_query(ix, query, cfg)
    dbg = {"groups": [], "mode": "boolean-AND"}
    # ---- group postings (union over variants) and Boolean candidate generation
    gp = []
    for g in parsed.groups:
        kept = []
        for v in g.variants:
            if v[2] == 'synonym' and len(ix.variant_pids(v[0])) / ix.N > cfg.syn_max_df:
                dbg.setdefault('pruned_synonyms', []).append(' '.join(v[0]))
                continue
            kept.append(v)
        g.variants = kept
        pids = [ix.variant_pids(v[0]) for v in g.variants]
        pids = np.unique(np.concatenate(pids)) if pids else np.zeros(0, np.int32)
        gp.append(pids)
        dbg["groups"].append(dict(concept=g.label, variants=[" ".join(v[0]) for v in g.variants], passage_df=int(len(pids))))
    keep = [i for i, p in enumerate(gp) if len(p) / ix.N <= cfg.generic_df and len(p) > 0]
    parsed.dropped_generic = [parsed.groups[i].label for i in range(len(gp)) if i not in keep]
    if cfg.boolean and keep:
        order = sorted(keep, key=lambda i: len(gp[i]))  # rarest first (query optimisation)
        cand = gp[order[0]]
        for i in order[1:]:
            cand = np.intersect1d(cand, gp[i], assume_unique=True)
        dbg["intersection_order"] = [parsed.groups[i].label for i in order]
        m = len(order)
        if len(cand) < cfg.min_cands and m > 1:
            allp = np.concatenate([gp[i] for i in order])
            u, c = np.unique(allp, return_counts=True)
            while m > 1 and len(u[c >= m]) < cfg.min_cands:
                m -= 1
            cand = u[c >= m]
            dbg["mode"] = f"relaxed to >= {m} of {len(order)} concept groups"
        dbg["candidates"] = int(len(cand))
    else:
        cand = None
        dbg["mode"] = "disjunctive (no Boolean)"
    # ---- BM25 over every variant (query terms weight 1, synonyms 0.6)
    score = np.zeros(ix.N, np.float64)
    termtab = {}
    for g in parsed.groups:
        for stems, w, kind in g.variants:
            for st in stems:
                if st in termtab:
                    continue
                pids, c, idf, df = bm25_term(ix, cfg, st)
                termtab[st] = (w, pids, c, idf, df, g.label, kind)
    # a synonym phrase contributes via its component stems at the synonym weight
    for st, (w, pids, c, idf, df, label, kind) in termtab.items():
        if len(pids):
            score[pids] += w * c
    if cand is not None:
        mask = np.zeros(ix.N, bool)
        mask[cand] = True
        score[~mask] = 0.0
    top = np.argpartition(-score, min(cfg.rerank_n, ix.N - 1))[: cfg.rerank_n]
    top = top[score[top] > 0]
    dbg["scored_passages"] = int(len(top))
    # ---- positional features for the rerank set
    pos_of = {}  # pid -> {group index: [positions]}
    allc = {}    # pid -> sorted concept positions
    top_mask = np.zeros(ix.N, bool)
    top_mask[top] = True
    for gi, g in enumerate(parsed.groups):
        for stems, w, kind in g.variants:
            ks = ix.keys(stems[0]) if len(stems) == 1 else ix.phrase_keys(stems)
            if len(ks) == 0:
                continue
            sel = ks[top_mask[ks >> SHIFT]]
            for k in sel.tolist():
                pos_of.setdefault(k >> SHIFT, {}).setdefault(gi, []).append(k & 0xFFFF)
    for pid, d in pos_of.items():
        allc[pid] = np.array(sorted(p for l in d.values() for p in l))
    cue_by_pid = {}
    if cfg.stance:
        for cue in ix.cues(parsed.profile):
            ks, neg = cue["keys"], cue["negated"]
            m = top_mask[ks >> SHIFT]
            for k, ng in zip(ks[m].tolist(), neg[m].tolist()):
                pid, s = k >> SHIFT, k & 0xFFFF
                cp = allc.get(pid)
                if cp is None or len(cp) == 0:
                    continue
                d = int(np.min(np.abs(cp - s)))
                if d > cfg.cue_window:
                    continue
                if d == 0 and not ng:
                    continue  # operator word is itself a query concept term (e.g. "entitled"): only a NEGATED occurrence carries stance
                pol = cue["pol"]
                w = cue["w"] / (1 + d / cfg.cue_window)
                if ng:
                    pol = "oppose" if pol == "support" else "support"
                    w *= 0.8
                cue_by_pid.setdefault(pid, []).append(dict(phrase=cue["phrase"], pos=s, dist=d, polarity=pol,
                                                           negated=bool(ng), weight=round(w, 4)))
    # ---- final passage scores + traces
    n_groups = len(parsed.groups)
    best_per_doc = {}
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
    # ---- document-level signals
    qgroups_title = []
    for gi, g in enumerate(parsed.groups):
        stset = set()
        for stems, w, kind in g.variants:
            if len(stems) == 1 and kind == "query":
                stset |= ix.title_index.get(stems[0], set())
        qgroups_title.append(stset)
    hits = []
    for did, (s_pass, pid, comp) in best_per_doc.items():
        doc = ix.docs[did]
        title_groups = [parsed.groups[i].label for i, st in enumerate(qgroups_title) if did in st] if cfg.zones else []
        stat = [s for s in doc["statutes"] if any(s.split(" ", 1)[0] == n.upper() for n in parsed.statute_nums)] if cfg.zones else []
        g_auth = math.log2(max(doc["bench"], 1)) if cfg.authority else 0.0
        comp.update(title_groups=title_groups, statutes_matched=stat[:3], bench=doc["bench"], g=g_auth)
        final = s_pass + cfg.w_title * len(title_groups) + cfg.w_statute * (1 if stat else 0) + cfg.w_auth * g_auth
        comp["weights"] = dict(w_prox=cfg.w_prox, w_cue=cfg.w_cue, w_title=cfg.w_title, w_statute=cfg.w_statute,
                               w_auth=cfg.w_auth, headnote_mult=cfg.headnote_mult)
        comp["final"] = final
        hits.append(Hit(did, pid, final, comp))
    hits.sort(key=lambda h: -h.score)
    hits = hits[:topk_docs] if topk_docs else hits
    # per-term BM25 detail for each returned hit (explanation)
    for h in hits:
        rows = []
        for st, (w, pids, c, idf, df, label, kind) in termtab.items():
            j = np.searchsorted(pids, h.pid)
            if j < len(pids) and pids[j] == h.pid:
                tf = int(ix.rows(st)[1][j])
                rows.append(dict(term=st, concept=label, kind=kind, tf=tf, df=df, idf=round(idf, 3),
                                 weight=w, contrib=round(float(w * c[j]), 4)))
        h.trace["terms"] = sorted(rows, key=lambda r: -r["contrib"])
    dbg["dropped_generic_concepts"] = parsed.dropped_generic
    return hits, dbg, parsed







