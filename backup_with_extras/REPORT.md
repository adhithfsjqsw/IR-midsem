# Evidence-Balanced and Explainable Indian Legal Search
**CSD358 IR Hackathon · Track T6 (Vertical search for law) · Indian Supreme Court judgments, 2018–2024**
Team: *[fill in names]* · Repo: *[fill in link]* · Video: *[fill in link]*

---

## 1. Problem and track relevance

**User need.** A lawyer, law student or citizen researching a legal proposition ("Can an employer terminate a probationary employee without prior notice?") needs the authorities that *support* it **and** the ones that *limit* it. Keyword search returns whatever matches best, usually one side, with no account of why a result is ranked where it is. Commercial legal engines are closed, so the ranking cannot be inspected.

**Research question.** *Can retrieving supporting and opposing Indian Supreme Court passages with two query specifications executed on one positional index increase the coverage of both sides in legal search, without lowering topical precision, while exposing a score decomposition that is faithful to the computation?*

**Track fit (T6).** The track theme is search that uses domain structure — zones, metadata, citations, authority — rather than flat text. We index judgments as structured documents (headnote vs body zones, title zone, statute/section field, parametric fields for bench/year/court/disposal), use Westlaw-style Boolean concept queries, proximity and positional phrase queries for statute names, and a static quality score.

**Related work (read at abstract/summary level only; we did not reproduce any of it).** ILDC (Malik et al., ACL 2021) is a 35k-case Supreme Court corpus built for judgment prediction and explanation. U-CREAT (Joshi et al., ACL 2023; arXiv 2307.05260) introduces IL-PCR, an Indian prior-case-retrieval benchmark,. IL-PCSR (arXiv 2511.00268, 2025) adds joint prior-case and statute retrieval. AQgR (arXiv 2508.04710) studies LLM/RAG-based retrieval of Indian case law with structured summaries. These target *relevant-case* retrieval; the work we found does not return a stance-separated, score-decomposed result list over an open positional index.

## 2. How we used IR

```
 judgment PDFs (AWS Open Data, eCourts) ──► clean ► zones(headnote|body) ► passages (~150 words)
                                                │
                       tokenise · case-fold · stop words · Porter · keep positions
                                                ▼
  ┌──────────────────────── POSITIONAL INVERTED INDEX (numpy CSR) ────────────────────────┐
  │ dictionary → postings (passage, tf, offset) → positions ;  title zone ; statute field ;   │
  │ parametric: year, bench, court, disposal                                                  │
  └────────────────────────────────────────────────────────────────────────────────────────┘
 QUERY ─► parser: concept groups (stem + legal synonyms), "section N"/statute phrases, polarity profile
       ─► Boolean AND(OR) over groups, rarest-first, relax to n−1 …  ─► BM25 ─► top-N positional rerank:
          proximity window · stance operators (negation-aware) · topical gate ─► passage→judgment ─► + title,
          statute, g(d)  ─►  Hit + score trace
 support spec ─┐
               ├─ SAME index, SAME scorer ─► evidence balance (assign to one side, τ, abstain) ─► EvidencePack (sha256)
 oppose spec ──┘                                                     │
                                             Regular wording ◄───────┴───────► Professional wording   (response layer only)
```

| IR principle (lecture) | What we did | Why | Code |
|---|---|---|---|
| Document = ? | Judgment → headnote/body zone → ~150-word passages; display unit = judgment | Judgments are 5k words; stance lives in single paragraphs | `irlaw/build_index.py` |
| Normalisation | Case folding, light stop list, Porter stemmer; **stop words dropped but token positions kept** | Phrase/proximity distances must be measured in the real token stream; negators and modals ("not", "cannot", "may") must *stay* in the index | `irlaw/textproc.py` |
| Inverted + **positional** index | Dictionary, postings (passage, tf, offset), 29.7M stored positions; all phrase/proximity/negation work is done on these arrays | The assignment's hint: positional indexes for statute names | `Index.rows/keys/phrase_keys` |
| Boolean retrieval | Each query word is a *concept group* (OR of stem + curated legal synonyms); groups are AND-ed; intersection processed **rarest group first**; relaxed to n−1, n−2 groups only if < 40 candidates; synonym variants with passage-df > 3 % are eliminated, groups > 20 % are not used as filters | Westlaw-style recall control; index elimination of high-df terms | `search()` |
| Phrase queries | "section 125", "Code of Criminal Procedure"/CrPC, "show cause"; adjacent terms may be 1–2 positions apart (dropped stop words) | Statute names and legal terms of art | `parse_query`, `STATUTES` |
| tf-idf family / ranking | BM25 (k1 = 1.2, b = 0.75) with passage-length normalisation; synonyms weighted 0.6 | Standard strong lexical baseline; legal text shares distinctive vocabulary | `bm25_term` |
| Proximity | Smallest window covering one occurrence of every matched concept; value = (k/span)·(k/n) | Concepts close together = same legal point | `smallest_window` |
| Zone / parametric | Headnote ×1.25 on BM25 (the Court's own "Held" statements); title-zone concept hits; statute-field match; bench size parsed from the judgment header | Headnotes are condensed holdings | `search()` |
| Static quality g(d) | g = log₂(bench size) from the judgment's own header; weight 0.6 | The only authority signal this data supports (no reliable citation graph) | `search()` |
| Top-K, two-stage scoring | BM25 over candidates → positional rerank of top 1,500 → judgments | Positional work is only done where it can matter | `search()` |

**Evidence-balanced mechanism (our design).** The parser produces one set of concept groups *C*. The *supporting* and *opposing* specifications are both `C` plus **stance operators** — a hand-written list of deontic/validity phrases (can, may, permissible, entitled, liable, sufficient / cannot, impermissible, illegal, arbitrary, mandatory, required, natural justice, set aside, …). Two profiles exist because obligation words flip meaning with the proposition: for "Can/Is X permissible/entitled/liable?" *required* is opposing, for "Is X required?" it is supporting (profile chosen from the query text). An operator counts only if (i) it lies within 8 token positions of a concept term, (ii) it is not itself the query's concept word (a bare "entitled" in an "entitled?" query says nothing), and (iii) the passage is **topically strong** (topical score ≥ 0.75 × best topical score of the query — the *topical gate*; stance may re-order good passages but never promote weak ones). A negator up to 5 positions before an operator **flips** it ("not required" ⇒ opposite of "required"). Operators inside the headnote count ×1.5. Both specifications go through the *same* `search()` function; they differ only in which side's operators add to the score. `balance.py` then puts each judgment on at most one side by comparing stance margins, requires a margin ≥ τ = 1.0 to label anything, puts near-equal cases in a "mixed" bucket, and **abstains** ("no sufficiently strong opposing evidence found in this corpus") rather than padding a weak side.

**Explainability.** Every hit carries a trace: per-term tf/df/idf/contribution, the proximity window and positions, each stance operator with position, distance, negation flag and weight, the zone, title/statute/authority inputs, and final = exact sum of displayed parts. `irlaw/faithfulness.py` **recomputes every one of these from the raw passage text** (not from the postings) and compares: 1,610 returned hits, 12 check types, 0 failures (§5.3). It verifies that the explanation is the computation; it does **not** verify that the stance label is *right* — that is evaluated separately and is the weak part.

**Same retrieval for both modes.** The retrieval functions take no mode argument. `build_pack()` freezes the results into an EvidencePack and displays its SHA-256; both response generators receive only that pack. Test: over 23 queries the pack hash was identical on two independent retrievals (23/23), and both generated responses cited only evidence ids/case ids present in the pack and differed in wording (23/23).

## 3. Beyond IR

* **PyMuPDF** for PDF→text; **NLTK** Porter stemmer; **numpy/pandas/pyarrow** for the index and metadata.
* **LLM response layer (optional, post-retrieval).** If `ANTHROPIC_API_KEY` is set, Claude rewrites the frozen EvidencePack (system prompts for Regular / Professional; rules: cite only pack ids, add no cases/sections/holdings, no "the law is …"). Without a key a deterministic template renders the same pack in two styles. The LLM never sees the corpus, never retrieves, never reorders or rescoring. **The evaluation in this report covers retrieval only; the LLM text was not evaluated.** The demo and all numbers here were produced with the template generator unless stated otherwise.
* Streamlit UI (not graded) for the demo.

## 4. Novelty and creativity

We claim only what we built and measured: (a) a **stance-conditioned pair of query specifications executed on one positional index** with negation-aware operator matching by position, topical gating and an abstention rule; (b) **score traces whose faithfulness is mechanically verified** against raw text; (c) a **frozen evidence pack** that makes "same retrieval, different wording" testable. Compared with the obvious baseline (BM25 + citation authority, the track's sample idea) this adds structure (zones, statute phrases), explicit two-sided retrieval and verified explanations. We do **not** claim that stance detection works well — §5 shows it does not — nor that no one has built stance-aware legal search.

## 5. Evaluation

**Corpus.** 5,776 Supreme Court judgments (2018–2024), 195,640 passages, 139,115 terms. Source: AWS Open Data "Indian Supreme Court Judgments" (CC-BY-4.0; from the court/eCourts site). 1 of 5,777 PDFs was dropped (extraction error or < 200 words); the 2023 archive's file count (854) matches the dataset's own index.

**Protocol (pilot, hackathon time limit).** 23 propositions in 3 sets: **DEV** (3, used to set weights/lexicon), **TEST** (12) and **FRESH** (8, written after the system was frozen). Pooling: the union of the top results of every system variant (plain list A–E and evidence-balanced B–E) is judged, so all systems are scored on the same judged items. Each pooled passage got a code: N not relevant · T relevant, no stance · S supports the proposition · O opposes/limits it · M mixed. Unjudged items count as not relevant. In total 577 passages were judged (72 S, 86 O, 53 M, 254 T, 112 N). **Labels are AI-assisted: Claude read each passage and applied the rubric; the team has not yet independently re-judged them.** *[Team: re-judge a ≥ 25 % random sample and report agreement before submission.]* Metrics are macro-averaged; with 20 held-out queries differences of a few points are not significant and we ran no tests.

**History, stated plainly.** v1 (generic polarity cues, 25-token window) gave stance precision ≈ 0.0–0.2 on DEV — no better than chance. We rebuilt the cue lexicon as deontic operators with negation and a polarity profile and fixed a stop-word bug (modals had been dropped from the index). TEST (12 queries) was then judged (support precision 0.11, oppose 0.16, many topically irrelevant stance results). Diagnosis led to the topical gate, τ = 1.0 and statute phrase concepts. FRESH was written afterwards and judged for the first time with that system. A last bug (an operator that was itself a concept word, e.g. "show cause", counted as a stance cue) was found while inspecting a demo trace; we fixed it and re-measured everything. TEST was therefore seen before the later changes, so TEST+FRESH is a *development-contaminated* estimate; FRESH alone is the cleanest (its numbers are in `evalkit/RESULTS.md`).

### 5.1 Retrieval quality vs baseline (20 held-out queries)

| System | P@5 | P@10 | Pooled recall of **supporting** passages | Pooled recall of **opposing** passages | Queries with ≥1 S **and** ≥1 O in top-10 |
|---|---|---|---|---|---|
| A. BM25 baseline | 0.90 | 0.86 | 0.49 | 0.42 | 0.25 |
| B. + Boolean concepts + synonyms | 0.94 | 0.88 | 0.53 | 0.53 | 0.35 |
| C. + proximity | 0.93 | 0.88 | 0.57 | 0.51 | 0.30 |
| D. + zones / statute field | 0.93 | 0.86 | 0.55 | 0.56 | 0.40 |
| E. + authority g(d) | 0.94 | 0.86 | 0.55 | 0.55 | 0.40 |

On FRESH alone: P@10 0.82 → 0.88, S-recall 0.58 → 0.79, O-recall 0.48 → 0.71, both-sides coverage 0.25 → 0.50 (A → E). **Reading:** the structured pipeline does not hurt precision and recovers more stance-bearing passages; proximity helps support-recall slightly; zones/statute help most on FRESH; **authority g(d) changes nothing measurable** (bench size varies too little) — we keep it only because it is explainable and cheap. Figure: `evalkit/fig_results.png`.

### 5.2 Stance-labelled evidence lists (20 held-out queries)

| System (evidence-balanced output) | returned judgments (avg) | support-list precision | oppose-list precision | support list holds an O | oppose list holds an S | both lists contain a correct item |
|---|---|---|---|---|---|---|
| B. Boolean + synonyms | 6.55 | 0.19 | 0.14 | 0.09 | 0.14 | 0.10 |
| C. + proximity | 6.30 | 0.18 | 0.15 | 0.10 | 0.14 | 0.10 |
| D. + zones/statute | 4.80 | **0.32** | **0.25** | 0.16 | 0.15 | **0.20** |
| E. + authority | 4.80 | 0.32 | 0.25 | 0.16 | 0.15 | 0.20 |

**This is the negative result.** Strict precision of the support / oppose lists is 0.32 / 0.25 (for scale: S and O make up only 12 % and 15 % of the judged passages, so this is above the pool base rate but far from reliable) and a query gets a correct item on *both* sides only 20 % of the time (a list for each side is returned for 65 % of queries). The headnote-zone weighting is what helps (0.18 → 0.32 and 0.15 → 0.25), consistent with the idea that the Court's own "Held" statements are the reliable stance carriers; most of the remaining errors are passages that merely *discuss* a rule, quote a party's argument, or state a general principle in conditional language ("conviction can be based on circumstantial evidence if the chain is complete" is mixed, not supporting). Many true opposing passages contain no operator within 8 tokens of a concept word. Compared with the unlabelled list A, **our labelled lists do not demonstrate improved correct stance coverage**; the honest answer to the research question is: *retrieval of stance-bearing passages improved modestly; correct stance separation did not reach a useful level with a lexical operator lexicon.*

### 5.3 Explanation faithfulness and mode identity

Over 1,610 returned hits (23 queries × 7 system variants): tf and passage length, per-term BM25 contributions, BM25 sum, proximity span/value, stance operator position/negation/distance/weight, stance margin, headnote boost, title-zone claim, statute claim, authority value, topical-gate eligibility, and *final = sum of displayed parts* were recomputed from the raw passage text: **100 % pass** (`evalkit/FAITHFULNESS.md`). Mode identity: 23/23 (above).

**Limitations of the evaluation.** AI-assisted labels with no inter-annotator agreement yet; a pooled (not exhaustive) recall; 23 queries; propositions that the corpus mostly supports or mostly opposes make one side undefined (those queries are in the macro-average); relevance was judged on the best passage only; the LLM text is unevaluated.

## 6. Limitations and next steps

* **Stance is the weak link.** A hand-written operator lexicon cannot tell whether a passage endorses *this* proposition. Next: use the ~620 judged passages (+ more) to train a small supervised stance model **as a re-ranker of already retrieved passages**, keep the lexicon version as the explainable baseline, and measure both; or a cross-encoder NLI model (declared ML beyond IR).
* **Scope:** Supreme Court only, 2018–2024, English; no High Courts, no statutes (India Code), so the corpus cannot say what a *statute* provides. No citation network or treatment signals ("overruled", "distinguished") because the metadata does not give them reliably; the authority score is therefore only bench size.
* **Propositions:** operator profiles cover permission/entitlement/liability and requirement questions only.
* **Corpus bias:** the Supreme Court hears contested matters; a proposition may be settled in one direction (e.g. T1), and the system then correctly returns little on the other side — but a biased corpus gives a biased balance.
* **Data quirks:** e.g. NCB v. Kashif is `2025 INSC 1045` in the metadata but `2024 INSC 1045` in the judgment.
* **Roadmap if continued as the course project:** re-judge with the whole team and report agreement; High Court + India Code zones; citation extraction for a PageRank-style g(d); query-by-fact-pattern; a cross-encoder stance reranker evaluated against this lexicon baseline.

## 7. Work division *(fill in names; roles as planned)*

| Member | Component |
|---|---|
| *[M1]* | Data/source research, extraction, passages/zones, positional index (`build_index.py`, `textproc.py`) |
| *[M2]* | Retrieval and ranking: Boolean concepts, BM25, proximity, stance specs, evidence balance (`engine.py`, `balance.py`) |
| *[M3]* | Explainability, faithfulness checks, judging protocol, metrics, ablation (`faithfulness.py`, `evalkit/`) |
| *[M4]* | Response layer, Streamlit UI, integration, README/video (`respond.py`, `app.py`) |

## 8. AI-use declaration

* **Claude (Claude Code, Anthropic)** wrote most of the code, the design document, this report's draft, and — importantly — the pilot relevance/stance judgments (it read each pooled passage and applied the rubric in §5). It also ran the evaluation loop (pooling → judging → metrics) and made the engineering fixes described in §5 "History". The team directed the task and must verify the judgments and claims.
* **Claude API (optional)** in the response layer only. **NLTK** (Porter stemmer) and **PyMuPDF** as libraries. No pretrained retrieval or embedding model is used. No LLM is used for retrieval, ranking or stance labelling.
* Related-work notes were taken from search snippets/abstracts, not full reading.

## 9. Data and source ethics

Corpus: AWS Open Data "Indian Supreme Court Judgments", curated by Dattam Labs from the Supreme Court/eCourts website, **CC-BY-4.0**, accessed 2026-10-07 (cite: https://registry.opendata.aws/indian-supreme-court-judgments). Downloaded from the public bucket as provided; we crawled nothing, so robots.txt/rate limits do not arise. Judgments are public court records; we add no personal data and show party names as published. Indian Kanoon was not used (its terms restrict bulk crawling); ILDC is cited but not used. Every result links to the original PDF in the same bucket. The system states that it is an information-retrieval tool, not legal advice, and its vocabulary avoids "correct"/"the law is".

