# Evidence-Balanced and Explainable Indian Legal Search
**CSD358 IR Hackathon · Track T6 (Vertical search for law) · Indian Supreme Court judgments, 2018–2024**
Team: *[fill in names]* · Repo: *[fill in link]* · Video: *[fill in link]*

---

## 1. Problem and track relevance

**User need.** A lawyer, law student or citizen researching a legal proposition ("Can an employer terminate a probationary employee without prior notice?") needs the authorities that *support* it **and** the ones that *limit* it. Keyword search returns whatever matches best, usually one side, with no account of why a result is ranked where it is. Commercial legal engines are closed, so the ranking cannot be inspected.

**Research question.** *Can retrieving supporting and opposing Indian Supreme Court passages with two query specifications executed on one positional index increase the coverage of both sides in legal search, without lowering topical precision, while exposing a score decomposition that is faithful to the computation?*

**Track fit (T6).** The track theme is search that uses domain structure — zones, metadata, authority — rather than flat text. We index judgments as structured documents (headnote vs body zones, title zone, statute/section field, parametric fields for bench/year/court/disposal), use Westlaw-style Boolean concept queries, proximity and positional phrase queries for statute names, and a static quality score.

**Scope decision: syllabus techniques only.** The system uses only techniques from the assignment's lecture list (Boolean retrieval, positional index and phrase queries, tf-idf/vector-space with lnc.ltc and cosine, heap top-K, champion lists, index elimination, zone/parametric indexes, proximity, static quality g(d) and net score, query parser). We deliberately removed BM25 and our earlier negation-flipping, thresholding and abstention logic (§5.4 reports what those had bought).

**Related work (read at abstract/summary level only; we did not reproduce any of it).** ILDC (Malik et al., ACL 2021) is a 35k-case Supreme Court corpus built for judgment prediction and explanation. U-CREAT (Joshi et al., ACL 2023; arXiv 2307.05260) introduces IL-PCR, an Indian prior-case-retrieval benchmark. IL-PCSR (arXiv 2511.00268, 2025) adds joint prior-case and statute retrieval. AQgR (arXiv 2508.04710) studies LLM/RAG-based retrieval of Indian case law with structured summaries. These target *relevant-case* retrieval; the work we found does not return a stance-separated, score-decomposed result list over an open positional index.

## 2. How we used IR

```
 judgment PDFs (AWS Open Data, eCourts) ──► clean ► zones(headnote|body) ► passages (~150 words)
                                                │
                       tokenise · case-fold · stop words · Porter · keep positions
                                                ▼
  ┌──────────────────────── POSITIONAL INVERTED INDEX (numpy CSR) ────────────────────────┐
  │ dictionary → postings (passage, tf, offset) → positions ;  title zone ; statute field ;   │
  │ parametric: year, bench, court, disposal ; lnc passage vector lengths                      │
  └────────────────────────────────────────────────────────────────────────────────────────┘
 QUERY ─► parser: concept groups (stem + legal synonyms), "section N"/statute phrases, polarity profile
       ─► Boolean AND(OR) over groups, rarest-first, relax to n−1 … ─► lnc.ltc cosine over candidates
       ─► heap top-K (1,500) ─► proximity window ─► champion list (best 100) ─► stance phrase queries
       ─► passage→judgment ─► + title zone, statute field, g(d)  ─►  Hit + score trace
 support spec ─┐
               ├─ SAME index, SAME scorer ─► evidence balance (each judgment on the side with the higher stance score)
 oppose spec ──┘                                     │
                                          EvidencePack (sha256) ─► Regular wording | Professional wording (response layer only)
```

| IR principle (lecture) | What we did | Why | Code |
|---|---|---|---|
| Document = ? | Judgment → headnote/body zone → ~150-word passages; display unit = judgment | Judgments are 5k words; stance lives in single paragraphs | `irlaw/build_index.py` |
| Normalisation | Case folding, light stop list, Porter stemmer; **stop words dropped but token positions kept** | Phrase/proximity distances must be measured in the real token stream; "not", "no", "can", "may" must stay in the index for phrase queries | `irlaw/textproc.py` |
| Inverted + **positional** index | Dictionary, postings (passage, tf, offset), 29.7M stored positions; phrase, proximity and stance matching are done on these arrays | Assignment hint: positional indexes for statute names | `Index.rows/keys/phrase_keys` |
| Boolean retrieval / query optimisation | Each query word is a *concept group* (OR of stem + curated legal synonyms); groups are AND-ed; intersection processed **rarest group first**; relaxed to n−1, n−2 groups only if < 40 candidates | Westlaw-style recall control | `search()` |
| Index elimination | Synonym variants with passage-df > 3 % dropped; concept groups matching > 20 % of passages are not used as Boolean filters | Common terms discriminate nothing and cost postings work | `search()` |
| Phrase queries | "section 125", "Code of Criminal Procedure"/CrPC, "show cause", and the stance phrases ("not permissible", "no requirement"); adjacent terms may be 1–2 positions apart (dropped stop words); **longest match wins** | Statute names, legal terms of art, negation without any special logic | `parse_query`, `phrase_keys`, `OPERATORS` |
| Vector space model / tf-idf | **lnc.ltc**: document weight (1+log10 tf) cosine-normalised, query weight (1+log10 tf)·log10(N/df) cosine-normalised, score = cosine × 100; synonym variants weighted 0.6 | The lecture's standard weighting; length normalisation by passage vector length | `query_vector`, `search()` |
| Heap-based top-K | `heapq.nlargest` for the 1,500 best passages and the final K judgments | Positional work is only done where it can matter | `search()` |
| Proximity | Smallest window covering one occurrence of every matched concept; value = (k/span)·(k/n) | Concepts close together = same legal point | `smallest_window` |
| Zone / parametric | Headnote ×1.25 on the cosine (the Court's "Held" statements); title-zone concept hits; statute-field match; bench size parsed from the judgment header | Headnotes are condensed holdings | `search()` |
| Champion list | Only the 100 best passages by topical score may carry a stance bonus | Stance may re-order good passages, never promote weak ones | `search()` |
| Static quality g(d), net score | g = log₂(bench size) from the judgment's own header; net score = topical + proximity + stance + title + statute + 0.6·g | The only authority signal this data supports | `search()` |

**Evidence-balanced mechanism (our design).** The parser produces one set of concept groups *C*. The *supporting* and *opposing* specifications both run `search()` on *C*; they differ only in which side's **stance phrase queries** add to the score. The phrase lists are hand-written deontic/validity phrases — support: *can, permissible, entitled, liable, sufficient, not required, no requirement…*; oppose: *cannot, impermissible, illegal, mandatory, required, natural justice, set aside, not permissible, not entitled…*. Negation is just more phrases ("not permissible" is an opposing phrase; "not required" is supporting), and the **longest match wins** so "not required" is not also counted as "required". Two profiles exist because obligation words change meaning with the proposition: for "Can/Is X permissible/entitled/liable?" *required* is opposing; for "Is X required?" it is supporting (profile chosen from the query text). A phrase counts only if it starts within 8 token positions of a concept term and not on a concept word itself, and only for passages in the champion list; phrases inside the headnote count ×1.5. Each judgment is put on the side with the larger stance margin (stance(side) − ½·stance(other side)); a judgment with no matched stance phrase is not placed on either side.

**Explainability.** Every hit carries a trace: per-term tf, df, idf, ltc query weight, lnc document weight and contribution; the proximity window; each stance phrase with its position, distance and weight; zone, title/statute/authority inputs; and final = the exact sum of the displayed parts. `irlaw/faithfulness.py` **recomputes all of this from the raw passage text** — including the passage vector length, the query vector, the proximity window, and the *complete* set of stance phrases (with longest-match) — and compares: 1,610 returned hits, 13 check types, **0 failures** (§5.3). It verifies that the explanation is the computation; it does **not** verify that a stance label is *right*; that is evaluated separately and is the weak part.

**Same retrieval for both modes.** The retrieval functions take no mode argument. `build_pack()` freezes the results into an EvidencePack and displays its SHA-256; both response generators receive only that pack. Test over 23 queries: identical pack hash on two independent retrievals (23/23); both generated responses cited only evidence ids/case ids present in the pack and differed in wording (23/23).

**Stance stage (added after the evaluation below was run).** Retrieval is unchanged. `irlaw/stance.py` then classifies the retrieved
passages as separate fields: relevance, speaker role, stance (SUPPORTS / OPPOSES / MIXED / NEUTRAL_OR_CONTEXT / UNCERTAIN), exact
evidence span, rationale, confidence. It is conservative: every material part of the proposition must match, and only a relevant court holding/reasoning with an exact evidence span can be
SUPPORTS/OPPOSES; MIXED needs court reasoning pointing both ways; party arguments, unadopted quoted precedents, statutes and
background cannot be the court's stance; malformed/invalid output or a failed call becomes UNCERTAIN; LOW-confidence stances are
withheld; headnote evidence is capped at MEDIUM. Judgment text is passed as data in a JSON payload. Results are cached on
(model, prompt version, proposition, passage, context). Without `ANTHROPIC_API_KEY` the app shows topical candidates only as UNCERTAIN
and makes no support/opposition decision; phrase cues remain only as an evaluation baseline. All labels are *automatic predictions*; no human verification is required or implied.

## 3. Beyond IR

* **Libraries:** PyMuPDF (PDF→text), NLTK (Porter stemmer), numpy/pandas/pyarrow (index arrays, metadata). The index and every scoring step are our own code.
* **LLM response layer (optional, post-retrieval).** If `ANTHROPIC_API_KEY` is set, Claude rewrites the frozen EvidencePack (rules: cite only pack ids, add no cases/sections/holdings, no "the law is …"). Without a key a deterministic template renders the same pack in two styles. The LLM never sees the corpus, never retrieves, reorders or rescored. **The evaluation covers retrieval only; LLM text was not evaluated;** all numbers here were produced with the template generator.
* **LLM stance classifier (optional, post-retrieval, outside the lecture list).** See §2 "Stance stage". It never retrieves, re-ranks or changes a retrieval score; the stance field is shown beside the unchanged score trace. **It was not evaluated for accuracy** (§5.5).
* Streamlit UI (not graded). Evaluation tooling (pooling, judging helpers, faithfulness checker) is not part of the retrieval system.

## 4. Novelty and creativity

We claim only what we built and measured: (a) a **pair of stance-conditioned query specifications executed on one positional index**, implemented purely with phrase queries, proximity and a champion list; (b) **score traces whose faithfulness is mechanically verified** against raw text, including completeness of the stance phrases shown; (c) a **frozen evidence pack** that makes "same retrieval, different wording" testable. Compared with the obvious baseline (tf-idf + citation authority, the track's sample idea) this adds structure (zones, statute phrases), explicit two-sided retrieval and verified explanations. We do **not** claim that stance detection works well — §5 shows it does not — nor that no one has built stance-aware legal search.

## 5. Evaluation

**Corpus.** 5,776 Supreme Court judgments (2018–2024), 195,640 passages, 139,115 terms. Source: AWS Open Data "Indian Supreme Court Judgments" (CC-BY-4.0; from the court/eCourts site). 1 of 5,777 PDFs was dropped (extraction error or < 200 words); the 2023 archive's file count (854) matches the dataset's own index.

**Protocol (pilot, hackathon time limit).** 23 propositions in 3 sets: **DEV** (3, used to choose weights/phrase lists), **TEST** (12) and **FRESH** (8, written after the first system freeze). Pooling: the union of the top results of every system variant (plain lists A–E and evidence-balanced B–E) is judged, so all systems are scored on the same judged items. Codes: N not relevant · T relevant, no stance · S supports the proposition · O opposes/limits it · M mixed. Unjudged items count as not relevant. In total 771 passages were judged (98 S, 108 O, 69 M, 333 T, 163 N). **Labels are AI-assisted: Claude read each passage and applied the rubric; the team has not yet independently re-judged them.** *[Team: re-judge a ≥ 25 % random sample and report agreement before submission.]* Metrics are macro-averaged; with 20 held-out queries, differences of a few points are not significant and we ran no tests. Weights were set on the earlier BM25 version and **not re-tuned** for the tf-idf version.

**History, stated plainly.** v1 (generic polarity words, window 25) scored at chance on DEV. v2 introduced deontic phrases, a polarity profile, a topical gate and statute phrase concepts and fixed a stop-word bug (modals had been dropped from the index). We found and fixed a self-match bug (a stance word that was itself a query word counted as stance). TEST was seen at v1, so TEST+FRESH is a *development-contaminated* estimate; FRESH alone is the cleanest. v3 (this report) then removed everything outside the syllabus and was fully re-pooled and re-judged. `evalkit/RESULTS_v3_with_extras.md` keeps the previous numbers.

### 5.1 Retrieval quality vs baseline (20 held-out queries)

| System | P@5 | P@10 | Pooled recall of **supporting** passages | Pooled recall of **opposing** passages | Queries with ≥1 S **and** ≥1 O in top-10 |
|---|---|---|---|---|---|
| A. tf-idf cosine (lnc.ltc) baseline | 0.84 | 0.78 | 0.38 | 0.35 | 0.50 |
| B. + Boolean concepts + synonyms | 0.92 | 0.89 | 0.42 | 0.33 | 0.40 |
| C. + proximity | 0.91 | 0.89 | 0.37 | 0.36 | 0.50 |
| D. + zones / statute field | 0.91 | 0.88 | 0.42 | 0.48 | 0.60 |
| E. + authority g(d) | 0.91 | 0.89 | 0.42 | 0.48 | 0.60 |

On FRESH alone (A → E): P@10 0.79 → 0.90, S-recall 0.33 → 0.65, O-recall 0.42 → 0.51, both-sides coverage 0.50 → 0.62. **Reading:** Boolean concept queries with synonyms give the largest precision gain (P@10 0.78 → 0.89); headnote/statute zone weighting is what raises recall of opposing passages (0.36 → 0.48) and both-sides coverage (0.50 → 0.60); proximity changes little; **authority g(d) changes nothing measurable** (bench size varies too little) — kept only because it is cheap and explainable. Figure: `evalkit/fig_results.png`.

### 5.2 Stance-labelled evidence lists (20 held-out queries) - OLD phrase-cue system only

| System (evidence-balanced output) | judgments returned | support-list precision | oppose-list precision | support list holds an O | oppose list holds an S | both lists contain a correct item |
|---|---|---|---|---|---|---|
| B. Boolean + synonyms | 10.0 | 0.20 | 0.21 | 0.10 | 0.13 | 0.35 |
| C. + proximity | 10.0 | 0.19 | 0.21 | 0.11 | 0.15 | 0.35 |
| D. + zones/statute | 9.95 | 0.20 | 0.22 | 0.11 | 0.13 | 0.40 |
| E. + authority | 9.95 | 0.20 | 0.22 | 0.11 | 0.13 | 0.40 |

**This is the negative result.** Strict precision of the support / oppose lists is only 0.20 / 0.22 (for scale: S and O are 13 % and 14 % of the judged passages, so this is above the pool base rate but far from reliable), and a query gets a correct item on *both* sides 40 % of the time. P@10 of the combined list is 0.85, so the lists are topically sound; the problem is the stance label. Most errors are passages that merely *discuss* a rule, quote a party's argument, or state a general principle with conditions ("conviction can be based on circumstantial evidence if the chain is complete" is mixed, not supporting); and many true opposing passages contain no stance phrase near a concept word. Compared with the unlabelled list A (both sides in the top-10 for 50 % of queries), **our labelled lists do not demonstrate improved correct stance coverage**. The honest answer to the research question is: *retrieving with structure improves relevance and the recall of opposing passages; separating them by stance with a phrase lexicon does not reach a useful level.*

### 5.3 Explanation faithfulness and mode identity

Over 1,610 returned hits (23 queries × 7 system variants): term frequencies, lnc passage vector length, ltc/lnc weights and contributions, cosine sum, proximity span/value, **complete set of stance phrases with positions, distances, polarity and weights**, stance margin, headnote weight, title-zone claim, statute claim, authority, champion-list consistency and *final = sum of displayed parts* were recomputed from the raw passage text: **100 % pass** (`evalkit/FAITHFULNESS.md`). Mode identity: 23/23.

### 5.4 What the non-syllabus extras had bought (previous version, same 20 queries)

| | Syllabus-only (this report) | With BM25 + negation flipping + topical gate + abstention |
|---|---|---|
| Plain baseline P@10 | 0.78 (tf-idf) | 0.86 (BM25) |
| Full pipeline P@10 | 0.89 | 0.86 |
| Support / oppose list precision | 0.20 / 0.22 | 0.32 / 0.25 |
| Judgments returned per query | 10.0 | 4.8 (abstained rather than pad) |
| Both lists contain a correct item | 0.40 | 0.20 |

Removing the extras costs list precision (0.32 → 0.20 for support) because the lists are now always filled to 10; it gains both-sides coverage (0.20 → 0.40) for the same reason, and the full pipeline's relevance is as good or better. BM25 was a stronger baseline than tf-idf (0.86 vs 0.78 P@10).

### 5.5 Automatic stance classifier - evaluation status

**Not evaluated.** No API key was available in this environment, so no model call was made and no accuracy, precision or coverage figure exists for the classifier. What was run: (i) `evalkit/test_stance_offline.py`, 15 offline checks with a fake client (invalid/malformed/fabricated output, party argument, quoted precedent, low confidence, headnote cap, invalid model id, no key) - these test the *validation rules*, not whether model predictions are correct; (ii) a fake-model end-to-end run on the real index confirming that buckets, citation verification and pack hashing work and that retrieval scores are unchanged; (iii) the existing faithfulness/mode-identity run in no-key mode (0 failures, 23/23; this covers the retrieval trace, not model labels). `evalkit/RESULTS_stance_auto.md` (new file; older results untouched) reports, for each split, the phrase baseline against the AI-assisted v2 reference labels (FRESH: support precision 0.28 / oppose precision 0.10 strict, 0.15 lenient, 8 queries, 166 passages; TEST 0.25 / 0.19; these are *phrase-baseline* numbers, equal to the earlier v2 re-scoring) and marks the classifier "NOT EVALUATED". To evaluate it: `autolabel` then `eval_stance` (commands in README); the reference is itself AI-assisted and unverified, so agreement would measure consistency with an unverified reference, not accuracy. Self-consistency of the classifier would not establish accuracy either.

### 5.6 Abstention on poorly covered queries

`Config.abstain` (on in the app via `STRICT`, off in every ablation): the rarest concept is mandatory when it matches ≤ 0.5 % of passages, and a returned judgment's best passage must match ≥ 50 % of the query's concept groups (min. 2). Parameters were fixed before measuring and were not tuned. Effect (`evalkit/RESULTS_abstain.md`, reference = AI-assisted unreviewed labels): on the 23 evaluation queries all still return 10 judgments and the labelled-relevant share is unchanged on TEST (0.87) and FRESH (0.74), and 0.70 → 0.82 on the three DEV queries (DEV informed the guideline, so treat that as weak evidence). An off-topic query ("mural on a public wall") returns 1 judgment instead of 40; a nonsense query returns none. This shows that abstention does not hurt the evaluated queries and removes padding for uncovered ones; it does **not** show that off-topic queries are answered correctly - there is no labelled set of uncovered queries yet.

### 5.7 Local rule-based stance classifier (default without a key)

`irlaw/local_stance.py`: sentence splitting, quote detection, per-sentence speaker role (regex patterns for counsel/party submissions, quoted precedents and citations, statute text, procedural background, court holding/reasoning), concept coverage of the proposition, polarity from the lexicon's phrase cues (longest match), conditional wording downgrades to MIXED, abstention otherwise. It was adjusted once using DEV only (confidence rule: MEDIUM if cue weight ≥ 1 and the sentence is a holding or covers ≥ 50 % of the concepts) and then run **once** on TEST+FRESH (`evalkit/RESULTS_local_stance.md`; 20 queries, 440 passages; reference = AI-assisted unreviewed labels, strict):

| | local rules | phrase-cue baseline (same passages) |
|---|---|---|
| support precision | 8/27 = 0.30 | 26/100 = 0.26 |
| oppose precision | 10/29 = 0.34 | 15/98 = 0.15 |
| recall of reference supports / opposes | 0.10 / 0.26 | not computed |
| decided coverage | 56/440 = 0.13 | 198/440 = 0.45 |

Direct SUPPORTS↔OPPOSES reversals: 3. It still labelled 13 of 154 passages the reference calls party/quoted/statute/background as decided. Role agreement with the reference is 0.41. **Reading:** precision is slightly above the phrase baseline but based on few predictions (27 and 29), the intervals are wide, and it leaves most relevant passages uncertain; it is a conservative filter, not a dependable stance detector. DEV figures (3 queries) are not reported as results because the rules were adjusted on them.

### 5.9 Local-model stance classifier (Ollama, qwen2.5:7b)

Same prompt and validator as the Claude path, run through a local Ollama server (`irlaw/stance.py`, `OllamaClient`). Labelled all DEV/TEST/FRESH pool passages (`autolabel --provider ollama`; DEV used only to check that parsing works, no prompt tuning on TEST/FRESH) and compared with the AI-assisted, unreviewed v2 reference on the same passages (`evalkit/RESULTS_stance_ollama.md`). TEST (12 queries, 241 passages): support precision 20/42 = 0.48, oppose 3/11 = 0.27. FRESH (8 queries, 156 passages): support 10/33 = 0.30, oppose 0/3. Combined support 30/75 = 0.40, oppose 3/14 = 0.21, decided coverage about 22-23 %; MIXED never predicted; role agreement 0.41-0.45; SUPPORTS<->OPPOSES reversals 1 (TEST) + 3 (FRESH). 46 of 441 passages (10 %) were rejected (40 for an evidence span that is not a verbatim substring). The phrase baseline reached 0.22 / 0.22 (TEST) and 0.30 / 0.11 (FRESH) on the same passages with about twice the coverage. **Reading:** better than the phrase cues and the local rules on support, nearly unable to detect opposition, very conservative; the reference is itself unverified and the oppose figures rest on 14 predictions.

### 5.8 Local LLM summaries (Ollama) - quote-checked, lightly tested

`respond.py` can send a bounded copy of the evidence pack to a local Ollama model (default `qwen2.5:7b`) with separate Regular and Professional instructions; output is accepted only after the citation/ID checks in `verify_response` and replaced by the template otherwise. Eight offline checks cover the acceptance/fallback logic with a fake model (`evalkit/test_respond_offline.py`). The model returns, per item, a one-sentence summary and an exact quote; `validate_summaries` keeps an item only if the quote is verbatim in the full passage (11 offline checks). A real `qwen2.5:7b` run on one query (daughter / coparcenary) produced 4-5 of 6 verified summaries in 13-21 s; the unverified ones are shown as "(no verified summary)". **Faithfulness and readability were not measured**: the quote proves the quoted words exist, not that the one-sentence paraphrase is right, and the overall short answer over-generalised in that run (a state-specific 1989 rule stated as general).

**Limitations of the evaluation.** AI-assisted labels, no inter-annotator agreement yet; pooled (not exhaustive) recall; 23 queries; propositions that the corpus mostly supports or mostly opposes make one side nearly empty (they are in the macro-average); relevance judged on the best passage only; weights not re-tuned for tf-idf; LLM text unevaluated.

## 6. Limitations and next steps

* **Stance is the weak link.** A hand-written phrase lexicon cannot tell whether a passage endorses *this* proposition (measured, §5.2). The optional model classifier (§2) is the attempt to fix this; **its accuracy is unmeasured** (§5.5). Next: run `autolabel` + `eval_stance` with a key, then have humans review a sample to turn the AI-assisted reference into a verified one.
* **Scope:** Supreme Court only, 2018–2024, English; no High Courts, no statutes (India Code). No citation network or treatment signals ("overruled", "distinguished") because the metadata does not give them reliably; the authority score is therefore only bench size.
* **Propositions:** phrase profiles cover permission/entitlement/liability and requirement questions only; keyword queries ("driving license") are not propositions and give meaningless stance lists.
* **Corpus bias:** the Supreme Court hears contested matters; a proposition may be settled in one direction (e.g. T1). Without abstention the system then still fills the weaker side with whatever phrase matches exist.
* **Data quirks:** e.g. NCB v. Kashif is `2025 INSC 1045` in the metadata but `2024 INSC 1045` in the judgment.
* **Roadmap if continued as the course project:** re-judge with the whole team and report agreement; re-tune weights for tf-idf; High Court + India Code zones; citation extraction for a PageRank-style g(d); a stance reranker evaluated against this baseline.

## 7. Work division *(fill in names; roles as planned)*

| Member | Component |
|---|---|
| *[M1]* | Data/source research, extraction, passages/zones, positional index (`build_index.py`, `textproc.py`) |
| *[M2]* | Retrieval and ranking: Boolean concepts, lnc.ltc cosine, proximity, stance phrase queries, evidence balance (`engine.py`, `balance.py`) |
| *[M3]* | Explainability, faithfulness checks, judging protocol, metrics, ablation (`faithfulness.py`, `evalkit/`) |
| *[M4]* | Response layer, Streamlit UI, integration, README/video (`respond.py`, `app.py`) |

## 8. AI-use declaration

* **Claude (Claude Code, Anthropic)** wrote most of the code, the design document, the first draft of this report and — importantly — the pilot relevance/stance judgments (it read each pooled passage and applied the rubric in §5). It also ran the evaluation loop (pooling → judging → metrics) and made the engineering changes described in §5 "History", including the later refactor to syllabus-only techniques. The team directed the task and must verify the judgments and claims.
* **Claude API (optional)** in the response layer only. **NLTK** (Porter stemmer) and **PyMuPDF** as libraries. No pretrained retrieval or embedding model is used. No LLM is used for retrieval or ranking. An LLM is used, optionally and after retrieval, for stance classification (automatic predictions, unverified) and response wording; the stance labels and the evaluation numbers in §5.1-§5.4 were produced without it.
* Related-work notes were taken from search snippets/abstracts, not full reading.

## 9. Data and source ethics

Corpus: AWS Open Data "Indian Supreme Court Judgments", curated by Dattam Labs from the Supreme Court/eCourts website, **CC-BY-4.0**, accessed 2026-10-07 (cite: https://registry.opendata.aws/indian-supreme-court-judgments). Downloaded from the public bucket as provided; we crawled nothing, so robots.txt/rate limits do not arise. Judgments are public court records; we add no personal data and show party names as published. Indian Kanoon was not used (its terms restrict bulk crawling); ILDC is cited but not used. Every result links to the original PDF in the same bucket. The system states that it is an information-retrieval tool, not legal advice, and its vocabulary avoids "correct"/"the law is".
