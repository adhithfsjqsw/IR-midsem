# Evidence-Balanced and Explainable Indian Legal Search (CSD358 IR Hackathon, Track T6)

A classical IR engine built **only from techniques in the CSD358 lecture list** — hand-written positional inverted index,
Boolean concept queries, lnc.ltc tf-idf cosine, heap top-K, champion list, proximity, zone/parametric fields, static quality g(d) —
over **5,776 Supreme Court of India judgments (2018–2024)**. For a proposition-style query ("Can an employer terminate a
probationary employee without prior notice?") it runs the **same index and scorer twice** — once with a *supporting* and once
with an *opposing* set of stance phrase queries — returns the two evidence lists, and shows a score decomposition for every
result that is re-verified against the raw text. An optional LLM layer rewrites the **already-ranked, frozen evidence pack**
for a *Regular* (plain-language) or *Professional* (legal-research) reader. **IR decides what and in which order; the
response layer only decides how it is worded.**

**Two stages, kept separate.** (1) *Topical retrieval* (the syllabus-only engine above) finds candidate passages and keeps its own
score trace. (2) An **optional stance classifier** (`irlaw/stance.py`; a language model, *outside* the lecture list, off unless
`ANTHROPIC_API_KEY` is set) reads each retrieved passage plus its neighbouring text against the exact proposition and predicts
relevance, speaker role, stance (SUPPORTS / OPPOSES / MIXED / NEUTRAL_OR_CONTEXT / UNCERTAIN), an exact evidence span, a rationale and
a confidence, abstaining when unsure. **Every stance shown is an automatic prediction, not a verified or legal conclusion.** Without a
key the app shows topical candidates only as uncertain; it does not put phrase matches into support/opposition. The phrase-cue method
remains available as an evaluation baseline.

> This is an information-retrieval prototype, not a judge and not legal advice or a determination of the law. It never says what
> "the law is".

## Honest status (read this first)

| Part | Status |
|---|---|
| Corpus, PDF→text, passage segmentation, zones, positional index | works (5,776 judgments, 195,640 passages, 29.7M positions) |
| Boolean concept queries (AND-of-OR, rarest-first), phrase queries, lnc.ltc cosine, proximity, zones, static quality, heap top-K | works, ablated |
| Phrase-cue stance (old evaluation baseline) | works, **but stance separation is weak** (see below); not used as a stance decision in the app |
| Local rule-based stance classifier (`irlaw/local_stance.py`, default when no key) | implemented and measured on held-out data: precision ≈ 0.30 (support) / 0.34 (oppose), coverage 13 %, recall ≈ 0.10 / 0.26 vs an AI-assisted reference |
| Automatic stance classifier (`irlaw/stance.py`, optional model path, role-aware, evidence-span checked, cached) | implemented; offline unit checks pass (15/15, fake client). **Not evaluated against the references: no API key was available**, so no accuracy figure exists for it |
| `evalkit/annotation/autolabel.py` (labels pooled pairs with the same classifier, append-only, resumable) | implemented; dry-run verified; no labels produced yet |
| Explainable ranking (per-signal trace) | works; **1,610/1,610 hits re-verified from raw text, 0 failures** |
| Regular vs Professional modes with identical retrieval | works; evidence-pack SHA-256 identical (23/23 queries) |
| Source traceability (link to original PDF, citation, bench, date) | works |
| Evaluation | pilot: 23 hand-judged queries (3 dev + 12 test + 8 fresh), 771 judged passages; labels are **AI-assisted** (see report) |
| Citation graph / treatment ("overruled") authority | **not built** (not reliably derivable from this data) |
| High Courts, statutes (India Code) | **not in corpus** — Supreme Court judgments only |

**Everything from here to the end of this section describes the OLD phrase-cue system scored on the original single-label judgments
(and the v2 re-labelling note). None of it is a result for the new classifier.**

**Headline result on 20 held-out queries** (details: `evalkit/RESULTS.md`):

| System | P@5 | P@10 | pooled recall of supporting passages | pooled recall of opposing passages | queries with ≥1 S and ≥1 O in top-10 |
|---|---|---|---|---|---|
| A. tf-idf cosine baseline (lnc.ltc) | 0.84 | 0.78 | 0.38 | 0.35 | 0.50 |
| E. full pipeline (Boolean concepts + synonyms + proximity + zones/statutes + g(d)) | 0.91 | 0.89 | 0.42 | 0.48 | 0.60 |

and the part that did **not** work well: the *labelled* support/oppose lists have only **0.20 / 0.22 precision**
(strict label match) and both lists contain a correct item for **40 %** of queries. The report analyses why (a hand-written
phrase lexicon cannot reliably tell whether a passage endorses or restricts a *specific* proposition) and what the next step
is. Ablation findings: Boolean concepts + synonyms give the main precision gain; headnote/statute zone weighting raises
recall of opposing passages; authority g(d) adds nothing measurable. Pilot numbers, 20 queries, no significance testing.
**Label schema v2 (provisional).** The numbers above use the legacy single-label judgments. A stricter, role-aware
re-labelling (court stance vs party argument vs quoted precedent, evidence spans, confidence, review routing) was added in
`evalkit/annotation/`; all 520 v2 labels are AI-assisted, **unreviewed by any human**, and not double-annotated. On the
FRESH set (8 queries, 166 passages) the stance lists reach supP 0.28 / oppP 0.10–0.15 under the strict policy. See
`evalkit/annotation/LABELS_V2_REPORT.md` for counts, agreement, policy, limits and the human annotation plan.
`backup_with_extras/` and `evalkit/RESULTS_v3_with_extras.md` keep an earlier version that also used BM25, negation flipping,
a relative topical gate and abstention (support/oppose precision 0.32/0.25 but only 4.8 results per query).

**Abstention (application default, `STRICT` in `irlaw/engine.py`).** A concept matching ≤ 0.5 % of passages (e.g. "mural") is
mandatory; Boolean relaxation may drop common concepts but never that one, and a returned passage must match at least half of the
query's concept groups (≥ 2). Off-topic queries therefore return few or no results instead of padding with generic matches
("mural on a public wall": 40 results → 1). On the 23 evaluation queries the number of results and the share of labelled results
judged relevant are unchanged (`evalkit/RESULTS_abstain.md`, AI-assisted reference; dev 0.70 → 0.82 on 3 calibration queries, test
0.87 → 0.87, fresh 0.74 → 0.74). All ablation configurations keep `abstain=False`, so the stored `RESULTS.md` numbers still describe
the system without abstention. When a model is configured, passages it judges NOT_RELEVANT are counted but not listed.

## Quick start (Windows/Linux/Mac, Python ≥ 3.10)

```bash
pip install -r requirements.txt
python scripts/fetch_data.py 2018 2019 2020 2021 2022 2023 2024   # ~2.2 GB from the public AWS bucket, resumable
for y in 2018 2019 2020 2021 2022 2023 2024; do python scripts/extract.py $y; done   # PDF -> text (PyMuPDF), ~1 min/year
python -m irlaw.build_index                                         # builds data/index.pkl (~70 s, 620 MB)
python -m streamlit run app.py                                      # demo UI (if `streamlit` is not on PATH)
```
On Windows use `python -X utf8 ...` and do not use the `-I` flag.

Without a key the app runs the **local rule-based classifier** (`irlaw/local_stance.py`; no model, no network; disable with
`STANCE_LOCAL=off`, which gives topical-only uncertain results). It detects who is speaking (party argument, quoted precedent, statute,
background, court), keeps only court-voice sentences that cover the proposition's concepts, and counts polarity wording; it never
gives HIGH confidence, never labels a passage NOT_RELEVANT, and leaves most passages UNCERTAIN. **Measured** (`evalkit/RESULTS_local_stance.md`,
held-out TEST+FRESH, 20 queries, 440 passages, AI-assisted unreviewed reference): support precision 8/27 = 0.30, oppose precision 10/29 = 0.34,
but it reports a stance for only 13 % of passages and recovers about 10 % (support) / 26 % (oppose) of the reference ones; the phrase-cue
baseline on the same passages reached 0.26 / 0.15 precision with many more predictions. So it is a cautious filter, not a reliable
stance detector.

**Optional: local stance classifier via Ollama (off by default).** The default stance classifier is the fast rule-based one (Ollama is used only for
summaries). To use the local model for stance, set `STANCE_PROVIDER=ollama`; it then classifies the 24 best-ranked
candidates with the local model (`qwen2.5:7b`, about 1-2 minutes for a new query; results are cached in `data/stance_cache.jsonl`) and the rest
with the local rules; `STANCE_PROVIDER=anthropic|ollama|local` forces one. **Measured once** on the held-out TEST+FRESH pools against the
AI-assisted, unreviewed reference (`evalkit/RESULTS_stance_ollama.md`, 20 queries, 397 passages that parsed validly of 441): support precision
30/75 = 0.40, oppose precision 3/14 = 0.21, decided coverage about 23 %; it predicted MIXED 0 times and OPPOSES only 14 times, with 4
direct support/oppose reversals; 46 passages (10 %) could not be labelled (invalid evidence span or output). Compare local rules: 0.30 / 0.34.
It is better at support and almost blind to opposition, so neither mode is a reliable stance detector. Reproduce:
`python -X utf8 -m evalkit.annotation.autolabel fresh --provider ollama` then `python -X utf8 -m evalkit.eval_stance fresh --auto "auto-ollama*__auto1__{split}*"`.

**Free local summaries (Ollama).** The Regular / Professional text can be written by a free local language model:
install Ollama (https://ollama.com), run `ollama pull qwen2.5:7b`, keep it running, and restart the app. `LLM_PROVIDER=auto` (default)
uses the Claude API if `ANTHROPIC_API_KEY` is set, else Ollama if reachable, else the deterministic template; force one with
`LLM_PROVIDER=anthropic|ollama|template`. `OLLAMA_MODEL` (default `qwen2.5:7b`), `OLLAMA_HOST` (default `http://localhost:11434`) and
`OLLAMA_TIMEOUT` (default 300 s) configure it. The model only rewords a bounded copy of the frozen evidence pack; its text is accepted only
if it cites known ids under the right buckets, invents no INSC case id and is not empty - otherwise the template is shown and the reason is
displayed. Sources and the disclaimer are appended by code, not by the model. Small local models can still misstate what a passage says;
summary quality was **not evaluated** beyond offline checks (`python -X utf8 -m evalkit.test_respond_offline`) and manual reading of one run.
**Speed.** `SUMMARY_MAX_ITEMS` (default 6) limits how many of the best passages the model summarises (the rest are listed as "not summarised").
Finished, quote-verified summaries are saved in `data/summary_cache.jsonl` (disable with `SUMMARY_CACHE=off`), keyed by the evidence-pack hash,
mode, model and `SUMMARY_MAX_ITEMS`. Run `python -X utf8 scripts/prewarm_demo.py` before a presentation to generate and save both modes for the
seven demo queries; they then open without waiting. Re-run it after any change to `irlaw/*.py`, the model or `SUMMARY_MAX_ITEMS`.
Summaries are quote-checked: the model returns, per item, one sentence plus an exact quote; code drops any item whose quote is not verbatim in
the passage, builds the section structure itself, and appends sources and the disclaimer. The sentence itself is still a model paraphrase and
the overall "short answer" can over-generalise (e.g. a state-specific rule stated as general).

Optional model features (no key => local rule-based labels and deterministic template wording; nothing needs a human):

| Variable | Meaning | Default |
|---|---|---|
| `ANTHROPIC_API_KEY` | enables the stance classifier and LLM rewording (never printed or stored) | unset |
| `STANCE_MODEL` | model id for stance classification (must look like `claude-...`) | `RESPONSE_MODEL`, else `claude-sonnet-5-5` |
| `RESPONSE_MODEL` | model used to reword the evidence pack | `claude-sonnet-5-5` |
| `STANCE_BATCH`, `STANCE_TIMEOUT`, `STANCE_RETRIES` | passages per request / seconds / retries on rate-limit or timeout | 6 / 90 / 2 |
| `STANCE_CACHE` | classification cache file (`off` disables) | `data/stance_cache.jsonl` |

Model output is validated: unknown labels, a span that is not an exact substring of the passage, a decided stance without a court
role/relevance/span, or a malformed or failed call all become UNCERTAIN (never a confident stance); party arguments, unadopted quoted
precedent, statutes and background are never SUPPORTS/OPPOSES; LOW-confidence stances are withheld; headnotes cap at MEDIUM.
Retrieval scores are never changed by the classifier.

CLI inspection of intermediates: `python scripts/demo_trace.py "Can a dying declaration alone form the basis of conviction?"`

Automatic labelling and comparison (needs a key; writes only new files, skips existing records, resumable):
```bash
python -X utf8 -m evalkit.test_stance_offline                    # offline classifier checks, no key, no network
python -X utf8 -m evalkit.annotation.autolabel fresh --dry-run   # count pending pairs (no key needed)
python -X utf8 -m evalkit.annotation.autolabel fresh --max-calls 20   # label (needs ANTHROPIC_API_KEY); also dev/test
python -X utf8 -m evalkit.eval_stance fresh                      # -> evalkit/RESULTS_stance_auto.md (classifier vs phrase baseline)
```
`eval_stance` compares both systems on the same pooled passages against the AI-assisted v2 reference labels (not verified truth);
without automatic labels it scores only the phrase baseline and says the classifier was not evaluated.

Reproduce the original evaluation (judgments are committed in `evalkit/labels_*.json`; `pool` refuses to overwrite existing
pools/runs unless `--force`):
```bash
python -m evalkit.pool dev ; python -m evalkit.pool test ; python -m evalkit.pool fresh   # regenerate pools/runs
python -m evalkit.summary                 # -> evalkit/RESULTS.md, fig_results.png
python -m evalkit.verify_faithfulness     # -> evalkit/FAITHFULNESS.md (explanation + mode-identity tests)
```
Re-pooling after any code change can surface passages without a judgment (counted as not relevant) — add labels with
`python -m evalkit.labels_tool todo <split>` / `add`.

## Data and ethics

* **Source:** AWS Open Data *Indian Supreme Court Judgments*, curated by Dattam Labs from the Supreme Court / eCourts
  website; CC-BY-4.0. Cite as: "Indian Supreme Court Judgments, accessed 2026-10-07, https://registry.opendata.aws/indian-supreme-court-judgments".
  Nothing was crawled by us, so no robots.txt / rate-limit concern arises. Judgments are public court records; we index party
  names as published and add no personal data.
* **Why this corpus:** primary-source texts with official citation, neutral citation (INSC id), bench, decision date and disposal in
  machine-readable metadata, bulk-downloadable in minutes. Indian Kanoon was not used (terms restrict bulk crawling). ILDC
  (IIT Kanpur) is cited as related work; we did not use it because it is organised around outcome prediction.
* **Known data quirk:** the metadata `case_id` of *NCB v. Kashif* says `2025 INSC 1045` while the judgment header says `2024 INSC 1045`.
* **Scope:** Supreme Court only, 2018–2024, English. Not "Indian law" in general.

## Where each IR idea lives

| Lecture concept | Code |
|---|---|
| What is a document: judgments → zones (headnote / body) → passages; cleaning | `irlaw/build_index.py` |
| Tokenisation, case folding, stop words, Porter stemming, positions kept across dropped stop words | `irlaw/textproc.py` |
| Dictionary + postings + **positional index** (term→(passage, tf, offset), positions) | `irlaw/build_index.py`, `Index.rows/keys` in `irlaw/engine.py` |
| Boolean retrieval: AND over concept groups, OR over synonym variants, postings intersection **rarest-first**, relaxation | `search()` in `irlaw/engine.py` |
| Index elimination of too-common synonym variants / generic groups | `search()` |
| Phrase queries ("section 125", "Code of Criminal Procedure", "not permissible") with stop-word gap; longest match | `Index.phrase_keys`, `search()` |
| tf-idf vector space model, **lnc.ltc**, cosine, length normalisation | `query_vector`, `Index.norm`, `search()` |
| Heap-based top-K; champion list | `search()` (`heapq.nlargest`) |
| Query-term proximity (smallest window over positional lists) | `smallest_window` |
| Zone and parametric indexes: headnote zone, title zone, statute field, bench size / year / court | `build_index.py`, `search()` |
| Static quality g(d) and net score (g = log2 bench size, from the judgment's own header) | `search()` |
| Query parser with legal terminology expansion | `parse_query`, `irlaw/lexicon.py` |
| Supporting / opposing specs on the same engine (stance phrase queries) - retained as evaluation baseline only | `lexical_evidence_balanced` in `irlaw/balance.py`, `irlaw/lexicon.py` |
| *(beyond the lecture list, optional)* automatic stance classification of retrieved passages | `irlaw/stance.py`, `evidence_balanced` in `irlaw/balance.py` |
| Explainability + independent faithfulness checks | `Hit.trace`, `irlaw/faithfulness.py` |

## Layout
```
irlaw/      engine, index builder, lexicon, evidence balance, stance classifier (stance.py), response layer, faithfulness checks
evalkit/    queries, pooling, judgments (labels_*.json), metrics, summary, verification, RESULTS.md
scripts/    fetch_data.py, extract.py, demo_trace.py (CLI), diag/printpool helpers
app.py      Streamlit demo
DESIGN.md   pre-implementation design and professor-attack analysis (see addendum for what changed)
REPORT.md   report (export to PDF for submission)
DEMO.md     timed script for the demo video
backup_with_extras/   previous version that also used non-syllabus techniques (kept for the comparison in the report)
```

## AI-use declaration (summary; full text in REPORT.md)
Claude (Claude Code, Anthropic) wrote most of the code and the pilot relevance/stance judgments under the team's direction;
the team must spot-check the judgments before the final submission. Optional Claude calls are used **after retrieval only**: the
stance classifier (automatic predictions, unverified) and the response-wording layer. Neither is used for retrieval or ranking.
All existing labels are AI-assisted and unreviewed; the project runs and evaluates without any human review.
