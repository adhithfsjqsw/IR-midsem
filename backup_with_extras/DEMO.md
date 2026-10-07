# Demo-video script (5–8 min, no slides — assignment rule: show the system running and intermediate output)

Prepare once: `streamlit run app.py` in one terminal (first load ≈ 20 s), `python scripts/demo_trace.py "<query>"` in another.
Query used live: **F5 — "Can a dying declaration alone form the basis of conviction?"** (clean case; its 3 support hits were judged S in our pool).
Limitation queries: **D1** (probationary termination — weak support item) and **T4** (confession to police — only one side found).

| Time | Say / show | Who |
|---|---|---|
| 0:00–0:50 | **Problem & track.** Lawyer asks a proposition; keyword search returns one side with an opaque score. Track T6 = domain structure (zones, metadata, authority). Corpus: 5,776 Supreme Court judgments 2018–24, official eCourts texts via AWS Open Data, CC-BY. Scope is judgments only, not "Indian law". | M1 |
| 0:50–2:00 | **Index, shown as data.** Run `demo_trace.py` on D1 and scroll: parsed concept groups (stem + synonyms), postings sizes (`passage df` per concept), rarest-first intersection order, relaxed Boolean mode, candidate count, pruned synonyms. Explain headnote vs body zone, positional postings, stop words dropped but positions kept. | M1 / M2 |
| 2:00–3:30 | **Live search (app).** Type F5. (1) Open *IR intermediates*. (2) Show the **baseline** BM25 list. (3) Show Supporting vs Opposing columns and the evidence-balance counters. (4) Open S1 and O1: matching passage, *View original judgment (PDF)* link, **score table** (BM25, headnote boost, proximity, stance margin, title, statute, authority) and the matched stance operators with negation flags. State: "evidence found", never "the law is". | M2 / M3 |
| 3:30–4:30 | **Same evidence, two voices.** Switch Regular ↔ Professional: point at the unchanged SHA-256, the same S1/O1 ids, scores, order; only the wording changes. Click *Prove: both modes use identical evidence*. If an API key is set, mention that Claude only rewrites the frozen pack; otherwise the template generator is used. | M4 |
| 4:30–6:00 | **Evaluation.** Show `evalkit/RESULTS.md` / `fig_results.png`: A→E table (P@10 0.86 → 0.86–0.88, supporting-recall 0.49 → 0.55, opposing-recall 0.42 → 0.55, both sides in top-10 0.25 → 0.40); ablation (zones lift stance precision; authority adds nothing). Show `FAITHFULNESS.md`: 1,610 hits re-computed from raw text, 0 failures. Judgments are AI-assisted, 23 queries, pilot. | M3 |
| 6:00–7:00 | **Limitation, live.** Run D1: the single support item is weak (operators "permitted/allowed" near the topic). State the measured numbers: labelled lists reach only 0.32 / 0.25 precision and 20 % both-sides coverage; a lexicon cannot decide endorsement of a *specific* proposition. Then T4: abstention — "no sufficiently strong supporting evidence found in this corpus". Next step: supervised/NLI stance reranker. | M2 |
| 7:00–7:40 | **Each member, one sentence**: M1 corpus/index, M2 retrieval/stance, M3 explainability/evaluation, M4 response layer/UI. | all |

Checklist before recording: `ANTHROPIC_API_KEY` set or not (say which); close other apps (index = 620 MB RAM + key caches); run each query once beforehand so caches are warm; do **not** edit any weights after the evaluation numbers are fixed.
