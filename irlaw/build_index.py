"""Build the corpus + positional inverted index.
Usage: python -I -X utf8 -m irlaw.build_index   (run from project root; reads data/text/*.jsonl, data/meta/*.parquet)

Pipeline (the 'what is a document' decision):
  judgment PDF text -> clean -> zones (headnote | body) -> passages (~100-220 words, on paragraph boundaries)
  -> tokenise/case-fold/stopword/Porter -> positional postings (term, passage, positions)
Retrieval unit = passage; display unit = judgment.  Everything is stored in plain numpy CSR arrays:
  vocab[term] -> tid ; df ; posting lists (pid, tf, offset into POS) ; POS = token positions (uint16).
"""
import json, pickle, re, sys, time
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

from .textproc import analyze

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "index.pkl"
S3 = "https://indian-supreme-court-judgments.s3.ap-south-1.amazonaws.com"

PARA_START = re.compile(r"^\s*(\d{1,3}(?:\.\d{1,2})*)\.\s+\S")
JUDG_START = re.compile(r"^\s*(?:J\s*U\s*D\s*G\s*M\s*E\s*N\s*T|O\s*R\s*D\s*E\s*R|JUDGMENT|ORDER)\s*:?\s*$", re.I)
NOISE_LINE = re.compile(r"^\s*(?:[A-H]|\d{1,4}|.*SUPREME COURT REPORTS.*|.*S\.C\.R\.\s*)\s*$")
BENCH_RE = re.compile(r"\[([^\]]{4,250}?\bJ{1,2}\.)\s*\]", re.S)
STAT_RE = re.compile(
    r"\b(?:Sections?|Sec\.|S\.|Articles?|Art\.|Or\.|Order)\s*(\d+[A-Z]?(?:\(\d+\))?(?:\([a-z]\))?)"
    r"(?:\s*(?:,|and|&|to|r/w|read with)\s*\d+[A-Z]?)*\s*(?:of|under)\s+(?:the\s+)?"
    r"((?:[A-Z][A-Za-z&\.]+\s+){0,6}?(?:Act|Code|Constitution|Rules|Order)(?:,?\s*(?:of\s+)?\d{4})?)")


def clean(text: str) -> str:
    lines = [l for l in text.split("\n") if not NOISE_LINE.match(l)]
    return "\n".join(lines)


def bench_size(text: str, fallback: str) -> int:
    m = BENCH_RE.search(text[:2500])
    if m:
        names = [n for n in re.split(r",|\band\b", re.sub(r"\bJJ?\.", "", m.group(1), flags=re.I), flags=re.I) if n.strip()]
        if 1 <= len(names) <= 13:
            return len(names)
    return max(1, len([n for n in (fallback or "").split(",") if n.strip()]))


def split_zones(text: str):
    """headnote = everything before the 'JUDGMENT/ORDER' marker line (catchwords + HELD statements);
    body = after it.  If no marker is found, headnote = text before the first numbered paragraph."""
    lines = text.split("\n")
    cut = None
    for i, l in enumerate(lines[:1500]):
        if JUDG_START.match(l) and i > 15:
            cut = i
            break
    if cut is None:
        for i, l in enumerate(lines[:400]):
            if PARA_START.match(l) and i > 5:
                cut = i
                break
    if cut is None:
        return "", text
    return "\n".join(lines[:cut]), "\n".join(lines[cut + 1:])


def sentences_as_paras(zone_text: str, hi=170):
    """Headnote is one dense block: chunk it on sentence boundaries."""
    sents = re.split(r"(?<=[.;])\s+", re.sub(r"\s+", " ", zone_text))
    out, cur, n = [], [], 0
    for s in sents:
        cur.append(s); n += len(s.split())
        if n >= hi:
            out.append(" ".join(cur)); cur, n = [], 0
    if cur:
        out.append(" ".join(cur))
    return [o for o in out if len(o.split()) >= 5]


PARA_REF = re.compile(r"\[Paras?\s+\d+")


def paragraphs(zone_text: str):
    paras, cur = [], []
    for l in zone_text.split("\n"):
        if PARA_START.match(l) and cur:
            paras.append(" ".join(cur))
            cur = []
        cur.append(l.strip())
    if cur:
        paras.append(" ".join(cur))
    return [re.sub(r"\s+", " ", p).strip() for p in paras if len(p.split()) >= 5]


def make_passages(paras, lo=90, hi=230):
    out, cur, n = [], [], 0
    for p in paras:
        w = len(p.split())
        if cur and n + w > hi:
            out.append(" ".join(cur))
            cur, n = [], 0
        cur.append(p)
        n += w
        if n >= lo and w > hi:  # a single huge paragraph stands alone
            out.append(" ".join(cur))
            cur, n = [], 0
    if cur:
        if out and n < 40:
            out[-1] += " " + " ".join(cur)
        else:
            out.append(" ".join(cur))
    return out


def main():
    t0 = time.time()
    meta = pd.concat([pd.read_parquet(p) for p in sorted((ROOT / "data" / "meta").glob("*.parquet"))], ignore_index=True)
    meta = meta.drop(columns=["raw_html"]).drop_duplicates("path").set_index("path")
    docs, passages = [], []
    vocab, term_ids, pid_list, pos_list = {}, [], [], []
    lengths = []
    title_index = {}  # stem -> set(doc_id)  (title zone)
    skipped = 0
    for fp in sorted((ROOT / "data" / "text").glob("*.jsonl")):
        for line in open(fp, encoding="utf-8"):
            r = json.loads(line)
            path = r["file"].replace("_EN.pdf", "")
            if path not in meta.index:
                skipped += 1
                continue
            m = meta.loc[path]
            text = clean(r["text"])
            head, body = split_zones(text)
            did = len(docs)
            statutes = Counter()
            for sm in STAT_RE.finditer(text):
                statutes[f"{sm.group(1)} {re.sub(r'\s+', ' ', sm.group(2)).strip(' ,')}"] += 1
            docs.append(dict(
                doc_id=did, path=path, title=m["title"], petitioner=m["petitioner"], respondent=m["respondent"],
                judges=m["judge"], bench=bench_size(r["text"], m["judge"]), date=m["decision_date"],
                year=int(m["year"]), citation=m["citation"], case_id=m["case_id"], disposal=m["disposal_nature"],
                court=m["court"], pdf_url=f"{S3}/data/pdf/year={m['year']}/english/{path}_EN.pdf",
                statutes=[s for s, _ in statutes.most_common(20)], n_words=len(text.split())))
            for _, st in analyze(m["title"]):
                title_index.setdefault(st, set()).add(did)
            for zone, ztext in (("headnote", head), ("body", body)):
                chunks = sentences_as_paras(ztext) if zone == "headnote" else make_passages(paragraphs(ztext))
                for ptxt in chunks:
                    pid = len(passages)
                    zone_p = "headnote" if (zone == "headnote" or PARA_REF.search(ptxt)) else "body"
                    toks = analyze(ptxt)
                    lengths.append(len(toks))
                    passages.append(dict(pid=pid, doc_id=did, zone=zone_p, text=ptxt))
                    for pos, st in toks:
                        tid = vocab.get(st)
                        if tid is None:
                            tid = vocab[st] = len(vocab)
                        term_ids.append(tid)
                        pid_list.append(pid)
                        pos_list.append(min(pos, 65535))
        print(f"  read {fp.name}: docs={len(docs)} passages={len(passages)} ({time.time()-t0:.0f}s)", flush=True)

    # --- build CSR positional postings: sort by (term, pid, pos) ---
    T = np.asarray(term_ids, np.int32); P = np.asarray(pid_list, np.int32); X = np.asarray(pos_list, np.uint16)
    del term_ids, pid_list, pos_list
    order = np.lexsort((X, P, T))
    T, P, X = T[order], P[order], X[order]
    del order
    # unique (term,pid) pairs -> posting entries
    new = np.ones(len(T), bool)
    new[1:] = (T[1:] != T[:-1]) | (P[1:] != P[:-1])
    starts = np.flatnonzero(new)
    post_term, post_pid = T[starts], P[starts]
    post_tf = np.diff(np.append(starts, len(T))).astype(np.int32)
    post_off = starts.astype(np.int64)  # offset into X (positions)
    V = len(vocab)
    term_ptr = np.zeros(V + 1, np.int64)
    np.add.at(term_ptr, post_term + 1, 1)
    term_ptr = np.cumsum(term_ptr)  # postings of term t = [term_ptr[t], term_ptr[t+1])
    df = np.diff(term_ptr).astype(np.int32)

    idx = dict(docs=docs, passages=passages, vocab=vocab, df=df, term_ptr=term_ptr,
               post_pid=post_pid, post_tf=post_tf, post_off=post_off, pos=X,
               plen=np.asarray(lengths, np.int32), title_index=title_index)
    with open(OUT, "wb") as f:
        pickle.dump(idx, f, protocol=pickle.HIGHEST_PROTOCOL)
    print(f"DONE docs={len(docs)} passages={len(passages)} vocab={V} postings={len(post_pid)} positions={len(X)} "
          f"skipped_no_meta={skipped} avg_plen={np.mean(lengths):.1f} time={time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()

