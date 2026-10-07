# Evidence-Balanced and Explainable Indian Legal Search (CSD358 IR Hackathon, Track T6)

A classical IR engine (hand-written positional inverted index, Boolean concept queries, BM25, proximity, zone/parametric
fields, static quality) over **5,776 Supreme Court of India judgments (2018–2024)**. For a proposition-style query
("Can an employer terminate a probationary employee without prior notice?") it runs the **same index and scorer twice** —
once with a *supporting* and once with an *opposing* query specification — returns the two evidence lists, and shows a
score decomposition for every result that is re-verified against the raw text. An optional LLM layer rewrites the
**already-ranked, frozen evidence pack** for a *Regular* (plain-language) or *Professional* (legal-research) reader.
**IR decides what and in which order; the response layer only decides how it is worded.**

> This is an information-retrieval prototype, not a judge and not legal advice. It never says what "the law is"; it says
> "supporting passages found / opposing passages found".

## Honest status (read this first)

| Part | Status |
|---|---|
| Corpus, PDF→text, passage segmentation, zones, positional index | works (5,776 judgments, 195,640 passages, 29.7M positions) |
| Boolean concept queries (AND-of-OR, rarest-first), phrase/statute queries, BM25, proximity, zones, static quality, top-K | works, ablated |
| Support / oppose query specs on one engine, abstention, evidence balance | works, **but lexical stance separation is weak** (see below) |
| Explainable ranking (per-signal trace) | works; **1,610/1,610 hits re-verified from raw text, 0 failures** |
| Regular vs Professional modes with identical retrieval | works; evidence-pack SHA-256 identical (23/23 queries) |
| Source traceability (link to original PDF, citation, bench, date) | works |
| Evaluation | pilot: 23 hand-judged queries, 3 dev + 12 test + 8 fresh; labels are **AI-assisted** (see report) |
| Citation graph / treatment ("overruled", "distinguished") authority | **not built** (not reliably derivable from this data) |
| High Courts, statutes (India Code) | **not in corpus** — judgments of the Supreme Court only |

**Headline result on 20 held-out queries** (details: `evalkit/RESULTS.md`):

| System | P@5 | P@10 | pooled recall of supporting passages | pooled recall of opposing passages | queries with ≥1 S and ≥1 O in top-10 |
|---|---|---|---|---|---|
| A. BM25 baseline | 0.90 | 0.86 | 0.49 | 0.42 | 0.25 |
| E. full classical pipeline (Boolean concepts + synonyms + proximity + zones/statutes + authority) | 0.94 | 0.86 | 0.55 | 0.55 | 0.40 |

and the part that did **not** work well: the *labelled* support/oppose lists have only **0.32 / 0.25 precision**
(strict label match) and both correct sides appear for only **20 %** of queries (a side is returned at all for 65 %). The report analyses why (a hand-written
lexicon of deontic operators cannot reliably tell whether a passage endorses or restricts a *specific* proposition) and
what the next step is. Pilot numbers, 20 queries, no significance testing. Two further findings from the ablation: authority g(d) adds nothing measurable, and the headnote-zone weighting is what raises stance precision (support 0.18→0.32, oppose 0.15→0.25 from system C to D).

## Quick start (Windows/Linux/Mac, Python ≥ 3.10)

```bash
pip install -r requirements.txt
python scripts/fetch_data.py 2018 2019 2020 2021 2022 2023 2024   # ~2.2 GB from the public AWS bucket, resumable
for y in 2018 2019 2020 2021 2022 2023 2024; do python scripts/extract.py $y; done   # PDF -> text (PyMuPDF), ~1 min/year
python -m irlaw.build_index                                         # builds data/index.pkl (~70 s, 620 MB)
streamlit run app.py                                                # demo UI
```

Optional: `export ANTHROPIC_API_KEY=...` makes the response layer use Claude (`RESPONSE_MODEL` selects the model);
without a key a deterministic template generator is used (same evidence pack, different wording per mode).

CLI inspection of intermediates: `python scripts/show.py "Is a daughter entitled to a share in coparcenary property?"`

Reproduce the evaluation (labels are committed in `evalkit/labels_*.json`):
```bash
python -m evalkit.pool dev ; python -m evalkit.pool test ; python -m evalkit.pool fresh   # regenerate pools/runs
python -m evalkit.summary                 # -> evalkit/RESULTS.md, fig_results.png
python -m evalkit.verify_faithfulness     # -> evalkit/FAITHFULNESS.md (explanation + mode-identity tests)
```
Re-pooling after any code change can surface passages without a judgment (treated as not relevant) — add labels with
`python -m evalkit.labels_tool todo <split>` / `add`.

## Data and ethics

* **Source:** AWS Open Data *Indian Supreme Court Judgments*, curated by Dattam Labs from the Supreme Court / eCourts
  website; CC-BY-4.0. Cite as: "Indian Supreme Court Judgments, accessed 2026-10-07, https://registry.opendata.aws/indian-supreme-court-judgments".
  Used under its licence; nothing was crawled by us, so no robots.txt / rate-limit concern arises. Judgments are public court records;
  we index party names as published and do not add any personal data.
* **Why this corpus:** primary-source texts with official citation, neutral citation (INSC id), bench, decision date and disposal in
  machine-readable metadata, bulk-downloadable in minutes. Indian Kanoon was not used (terms of use restrict bulk crawling). ILDC
  (IIT Kanpur) is cited as related work; we did not use it because it is organised around outcome prediction.
* **Known data quirk:** the metadata `case_id` of *NCB v. Kashif* says `2025 INSC 1045` while the judgment header says `2024 INSC 1045`.
  We show both as published; the PDF link is the authority.
* **Scope:** Supreme Court only, 2018–2024, English. Not "Indian law" in general.

## Where each IR idea lives

| Lecture concept | Code |
|---|---|
| What is a document: judgments → zones (headnote / body) → passages; cleaning | `irlaw/build_index.py` |
| Tokenisation, case folding, stop words, Porter stemming, positions kept across dropped stop words | `irlaw/textproc.py` |
| Dictionary + postings + **positional index** (CSR numpy arrays: term→(passage, tf, offset), positions) | `irlaw/build_index.py`, `Index.rows/keys` in `irlaw/engine.py` |
| Boolean retrieval: AND over concept groups, OR over synonym variants, postings intersection **rarest-first**, relaxation, index elimination of generic terms | `search()` in `irlaw/engine.py` |
| Phrase queries ("section 125", "Code of Criminal Procedure", "show cause") with stop-word gap | `Index.phrase_keys` |
| tf-idf family: BM25 with passage-length normalisation | `bm25_term` |
| Query-term proximity (smallest window over positional lists) | `smallest_window` |
| Zone and parametric indexes: headnote zone, title zone, statute field, bench size / year / court | `build_index.py`, `search()` |
| Static quality g(d) and net score (g = log2 bench size, from the judgment's own header) | `search()` |
| Top-K, two-stage scoring (retrieve → positional rerank) | `search()` |
| Query parser with legal terminology expansion | `parse_query`, `irlaw/lexicon.py` |
| Supporting / opposing query specs on the same engine, abstention rule | `irlaw/balance.py`, stance operators in `engine.py` |
| Explainability + independent faithfulness checks | `Hit.trace`, `irlaw/faithfulness.py` |

## Layout
```
irlaw/      engine, index builder, lexicon, evidence balance, response layer, faithfulness checks
evalkit/    queries, pooling, judgments (labels_*.json), metrics, summary, verification, RESULTS.md
scripts/    fetch_data.py, extract.py, show.py (CLI), diag/printpool helpers
app.py      Streamlit demo
DESIGN.md   pre-implementation design and professor-attack analysis
REPORT.md   report (export to PDF for submission)
```

## AI-use declaration (summary; full text in REPORT.md)
Claude (Claude Code, Anthropic) wrote most of the code and the pilot relevance/stance judgments under the team's direction;
the team must spot-check the judgments before the final submission. An optional Claude call is used only in the
post-retrieval response layer.

