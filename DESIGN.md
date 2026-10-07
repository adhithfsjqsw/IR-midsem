# Evidence-Balanced and Explainable Indian Legal Search — Design (pre-implementation)

Track T6 (Vertical search for law). Assignment facts that shape the design: frontend is **not graded**; IR principles = 30 marks, working system 20, evaluation 15, novelty 10, report 10, video 10, track relevance 5. Report ≤ 8 pages, video 5–8 min, no slides, show intermediate outputs (postings, weights, scores). Dataset "must be big enough that ranking matters". Direct copying of published work is penalised, so the stance mechanism below is our own.

## 1. Title
Evidence-Balanced and Explainable Indian Legal Search over Supreme Court of India Judgments

## 2. Description
A classical IR engine (hand-built positional inverted index, BM25, Boolean concept queries, proximity, zone and parametric fields, static authority) over ~5,000 Supreme Court of India judgments. For a proposition-style query it builds two query specifications, a *supporting* and an *opposing* one, from the same parsed concept groups plus polarity-tagged legal cue phrases. Both are executed by the same index and scorer. Every result carries a score decomposition computed by the scorer itself, and a "view original judgment" link to the source PDF. An LLM layer, which receives only the already-ranked evidence pack, renders it in Regular or Professional language.

## 3. Research question
Does evidence-balanced retrieval (separate support/oppose query specifications executed on one positional index) increase *stance coverage* of the top-10 for Indian legal propositions relative to a single BM25 ranking, without lowering topical precision, while exposing a score decomposition that is faithful to the computation?

## 4. Novelty claim (defensible)
We implement an evidence-balanced retrieval framework for Indian Supreme Court judgments that (a) derives support and oppose query specifications from one concept parse with negation-aware polarity cues matched by positional proximity, (b) runs both through the same index and scorer, (c) reports an abstention rule when one side lacks evidence, and (d) exposes a per-signal score decomposition that we verify against the raw index. We do not claim nobody has built stance-aware legal search; we found Indian legal IR work on prior-case/statute retrieval (IL-PCR, IL-PCSR, AILA), explanation generation, and rhetorical-role segmentation, but no open system combining these three properties, and we only claim what our pilot evaluation shows.

## 5. Difference from the assignment's sample ("BM25/tf-idf + citation authority precedent finder")
The sample ranks one list. We rank two stance-conditioned lists, use proximity/negation over positional postings, report an evidence balance with abstention, and verify explanation faithfulness.

## 6. Sources investigated
| Source | Type | Authority/Trust | Use | Practicality (15h) |
|---|---|---|---|---|
| Supreme Court of India / eCourts judgment PDFs | Primary | Official court record | Ultimate provenance of every text | Direct crawl is slow, so we use the mirror below |
| **AWS Open Data "Indian Supreme Court Judgments" (Dattam Labs)** | Primary texts, secondary packaging | Mirror of eCourts PDFs, CC-BY-4.0, public bucket, parquet metadata with citation/case_id/judges/disposal | **Selected corpus** | Excellent: tar per year (~390MB), no crawler |
| ILDC (IIT Kanpur, ACL 2021) | Academic dataset | Peer-reviewed, 35k SC cases | Cited as related work. Not used: release is task-oriented (outcome labels), access friction | Medium |
| Indian Kanoon | Secondary aggregator of primary text | Reliable text, but ToS restricts bulk crawling and API is paid | Not used (compliance risk) | Poor |
| India Code (indiacode.nic.in) | Primary statutes | Official | Not used; statutes not in corpus | Needs scraping, out of scope |
| High Court sites | Primary | Official | Not used | Many heterogeneous portals |
| Blogs / SEO law sites | Secondary | Untrusted | Excluded | n/a |

## 7–9. Dataset
Supreme Court of India **English judgments 2019–2023**, from s3://indian-supreme-court-judgments (CC-BY-4.0; attribution "Indian Supreme Court Judgments, Dattam Labs, accessed 2026-10-07, registry.opendata.aws/indian-supreme-court-judgments"). Trust: texts are the court's own eCourts PDFs; every record has an official citation (e.g. `[2019] 9 S.C.R. 593`) and neutral citation (`2019 INSC 770`); we link back to the PDF path. Scope statement: **judgments of the Supreme Court only, 2019–2023, no High Courts, no statutes, no overruling/treatment data.** Size: ≈5,000 judgments, split into passages (the retrieval unit). Metadata available and used: title (petitioner/respondent), judges (bench size), decision date, citation, case_id, disposal_nature. Zones derived from text by regex: statute/section mentions.

## 10. Indexing
Case-fold, tokenise, light legal-aware stop list, Porter stemming (nltk). Passage = ~150-word window on paragraph boundaries. Hand-written positional inverted index (term → passage → positions) with document-frequency dictionary; zones: `body`, `title`, `statute`; parametric fields: year, bench size, disposal, court. Stored as pickle, loaded at start.

## 11. Retrieval
Query parser → concept groups (stem + curated legal synonym expansion, e.g. terminate/termination/discharge/dismissal) → Boolean CNF (AND over groups of OR over variants), postings intersection in increasing-df order, relaxing to ≥k−1 groups if empty → BM25 on candidates → top-K by heap → aggregate passage→judgment (max passage + capped bonus for additional matching passages).

## 12. Support/oppose mechanism
Same concept parse `C`. Two query specs: `Q+ = C ∪ Cue+`, `Q− = C ∪ Cue−`. Cue lexicons are polarity-tagged phrases relative to the proposition being asserted ("permissible", "justified", "no requirement of notice", "upheld" vs "illegal", "arbitrary", "violative", "set aside", "natural justice", "stigmatic"). A cue counts only if it lies within window w of a concept term (positional proximity) and negation flips its polarity ("not permissible" is opposing, "not illegal" supporting; negator within 3 tokens). The same `score()` function evaluates both specs. **Abstention:** a judgment is labelled only if its stance score ≥ τ; a side with < 1 qualifying judgment is reported as "no sufficiently strong supporting/opposing evidence in this corpus"; "divergent positions" requires both sides ≥ 1 above τ. Lexicon is hand-written and limited; stance is *lexical evidence*, never truth.

## 13. Ranking formula (passage p in judgment d, spec S)
`score = BM25_body(C) + w_t·BM25_title(C) + w_x·Prox(C) + w_c·Cue_S(p) + w_s·StatuteMatch + w_g·g(d)`
- `Prox` = 1/(1+(minimal span covering all matched concept groups − #groups)), from positions.
- `Cue_S` = Σ cue weight × proximity decay, polarity-aware.
- `g(d)` = log2(bench size) from the `judge` field (Constitution/larger benches carry more authority); the only authority signal the data supports. No citation-count authority (not reliably derivable).
Weights fixed a priori then tuned on a *separate* dev subset of queries, reported openly.

## 14. Explainability
The scorer returns a `ScoreTrace` object (each term's tf, idf, contribution; proximity span and positions; cue phrases with token offsets and polarity; zone matches; g(d) inputs). The UI renders only the trace. A verification script recomputes each claimed signal from the raw index/text (span actually contains terms; cue actually in passage; title zone term actually in title; final = sum of parts) and reports a faithfulness pass rate.

## 15–18. Modes and the AI role
`EvidencePack` (JSON: ordered docs, passages, scores, stance, metadata, URLs) is produced once; `sha256(pack)` is displayed. Regular and Professional prompts both take exactly that pack; the retrieval function has no mode parameter. A test asserts the pack hash is identical for both modes and that the response cites only IDs in the pack (post-check strips/flags any case name or number not in the pack). LLM (Claude via API if a key is present; deterministic template fallback otherwise) = HOW only. It cannot add, drop, re-order or re-score documents.

## 19–21. Baseline, evaluation, ablation
Baseline: BM25 over the same passages, judgments ranked by best passage, no stance. Pilot evaluation (hackathon time constraint): ~12 proposition queries; pooled top-10 from every system variant judged by relevance (0/1) and stance (support/oppose/neutral), reading the passage. Metrics: P@5, P@10, support-P@k, oppose-P@k, stance coverage (fraction of queries with ≥1 correct support *and* ≥1 correct oppose in top-10), recall against the pool (pooled recall — stated as such). Ablation: A BM25; B +Boolean concepts; C +proximity; D +zones/statute; E +authority; F full evidence-balanced. Labelling is AI-assisted and is declared as such, with a team spot check.

## 22. Traceability
Each judgment keeps `case_id`, citation, date, bench, S3 path → link `https://indian-supreme-court-judgments.s3.ap-south-1.amazonaws.com/data/pdf/year=YYYY/english/<path>_EN.pdf`. No fabricated links.

## 23. Plan (15h, compressed)
0–1 research/design (done) · 1–3 download, PDF→text, passages, index · 3–5 BM25 + Boolean + baseline · 5–7 stance specs + proximity + traces · 7–8 faithfulness checks · 8–9 modes + pack hash · 9–10 Streamlit/CLI · 10–12.5 judging + evaluation + ablation · 12.5–14 README/report · 14–15 video.

## 24. Team
M1 data/preprocess/index · M2 retrieval/ranking/stance · M3 explainability/evaluation/ablation · M4 LLM modes/UI/integration/video.

## 26. Risks (professor attack, fixed)
- *"BM25 + chatbot"* → the LLM is optional and last; evaluation is on retrieval only.
- *Opposing evidence measurable?* → stance P@k and coverage vs judged pool.
- *Lexical cues misfire* (e.g. "not permissible" in a quoted argument) → reported as a limitation; we measure stance precision.
- *Corpus biased / one side missing* → abstention rule; never pad.
- *Judgment outcome ≠ stance on the proposition* → we deliberately do not use `disposal_nature` for stance, only display/filter.
- *Truth claims* → fixed vocabulary, disclaimer in every output.
- *OCR/old scans* → recent born-digital PDFs only; extraction failures counted and reported.
- *No statutes / no treatment data* → stated scope.

## 27. Expected marks (honest)
IR use 24/30, novelty 6/10, working 16/20, evaluation 10/15 (small pilot), track 5/5, report 7/10, video 7/10 ≈ **75/100**; ceiling depends on how clean the stance evaluation is.


---
## Addendum — what changed between this design and the final system (see REPORT.md §5 "History")
* **Corpus:** 2018–2024 (5,776 judgments) instead of 2019–2023; Supreme Court only.
* **Stance mechanism:** the first cue lexicon (generic words such as "illegal", "set aside", window 25) scored at chance level on DEV. Final version: deontic *operators* with negation flipping, two polarity profiles (permission / requirement), window 8, **topical gate** (cues only count for passages within 75 % of the best topical score), τ = 1.0, headnote cues ×1.5, bare self-matches with query concept words skipped, statute names as phrase concepts. A stop-word bug that had removed modal verbs from the index was fixed.
* **Authority:** g(d) = log2(bench size) parsed from the judgment header. No citation-based authority. Ablation shows it contributes nothing measurable.
* **Evaluation:** 3 DEV + 12 TEST + 8 FRESH queries, 577 judged passages (AI-assisted). Final held-out result: the structured pipeline keeps P@10 and recovers more stance-bearing passages; the lexical stance separation is weak (support / oppose list precision 0.32 / 0.25).
* **Expected marks (revised, honest):** IR use ~25/30, novelty ~5/10, working system ~17/20, evaluation ~11/15, track ~5/5, report ~7/10, video ~7/10 ≈ **77/100**, conditional on re-judging a sample of labels and reporting agreement.

## Addendum 2 — syllabus-only refactor
At the team's request every technique outside the assignment's lecture list was removed: **BM25 → lnc.ltc tf-idf cosine**; **heap top-K** instead of argpartition; **champion list** (top 100 passages) instead of the relative topical gate; **negation flipping → explicit negated phrase queries with longest-match**; **abstention threshold τ and the "mixed" bucket removed** (a judgment goes to the side with the larger stance margin if it matched any stance phrase). Evaluation was fully re-pooled and re-judged. Result: full pipeline P@10 0.89 vs 0.78 baseline; stance list precision 0.20 / 0.22. The earlier version is kept in `backup_with_extras/`.


## Addendum 3 - automatic stance classification stage
* **What changed:** `irlaw/stance.py` classifies already-retrieved passages against every material part of the exact proposition with an optional language model; `evidence_balanced` retrieves topical candidates once without the authority boost, attaches classification separately and buckets items into support / oppose / mixed / uncertain-or-contextual (not-relevant items are counted, not listed). Without a model, the app shows only topical candidates as uncertain. The old phrase-cue procedure remains as `lexical_evidence_balanced` for evaluation (`evalkit/pool.py` calls it directly, so pools never depend on a key).
* **Why:** the measured weakness of phrase cues (REPORT §5.2). This stage is outside the lecture list, optional, post-retrieval, and does not touch scores.
* **Safeguards:** role-aware validation, exact-span check, abstention on LOW confidence, UNCERTAIN on any malformed/failed output, model-id check, cache, bounded batches/timeouts/retries, judgment text as data. Response layer: items keep their bucket; `verify_response` checks every cited id (S/O/C/U) and case id, and rejects a response that cites an item under the wrong bucket; an LLM response failing the check is replaced by the template.
* **Abstention (added later):** `STRICT` = full pipeline + rarest-concept-mandatory + minimum concept coverage; when nothing qualifies the app shows an explicit "nothing in the corpus" message and makes no model call. Ablations keep `abstain=False` so earlier results remain reproducible.
* **Not done / open:** no accuracy measurement without an API key; model labels are unverified predictions; cache keys do not include the retrieval version, only the text shown to the model.

## Addendum 4 - local rule-based stance classifier
`irlaw/local_stance.py` is the default when no API key is set (`STANCE_LOCAL=off` disables it). Role-aware surface rules + lexicon polarity cues, never HIGH confidence, never NOT_RELEVANT, abstains by default; validated by the same `validate_label` as model output. Measured once on held-out data (REPORT §5.7): precision ≈ 0.30 / 0.34 at 13 % coverage. Known weakness: no understanding of proposition direction, so it cannot tell "court rejects the proposition" from "court states the rule" unless explicit negated phrases appear.
