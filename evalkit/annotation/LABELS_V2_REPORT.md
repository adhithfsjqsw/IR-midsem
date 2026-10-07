# Label schema v2 — report (all labels AI-assisted, provisional, no human review)

**Status: PROVISIONAL.** Every v2 label was produced by one AI annotator (`claude-annotator-A`) reading the full passage plus the neighbouring text. No human reviewed any label. No second annotator labelled any passage independently. Nothing here is "verified". Do not read any figure below as an accuracy claim.

## 1. What was wrong with the previous labels / process
- Legacy labels (`evalkit/labels_*.json`, 771 items) recorded a single relevance bit and a single stance word per passage. Role, evidence span, rationale and confidence were not recorded, so a label could not be audited.
- Nothing separated the court's own view from a party's submission or a quoted precedent. The legacy labeller was free to call a passage SUPPORTS because a quoted case said so.
- The same model wrote the legacy labels and the v2 labels, and the TEST queries had been inspected during v1 tuning (contaminated). Legacy-vs-v2 agreement therefore measures stability, not accuracy.
- No double annotation, no agreement figures, no abstention path (UNCERTAIN) in the old evaluation.

## 2. What changed
- Append-only versioned store `evalkit/annotation/labels_v2/` (legacy labels re-imported untouched as `legacy_import.jsonl`; originals not modified).
- Separate fields: relevance, court stance (SUPPORTS / OPPOSES / MIXED / NEUTRAL_OR_CONTEXT / UNCERTAIN), speaker role, party-argument stance, confidence, evidence span (validated as an exact substring of the passage), rationale, review status, label source.
- Guideline v1.0 → v1.1 (calibrated on DEV only; change log in `GUIDELINE.md`). v1.1 was frozen before TEST and FRESH were labelled and was not edited afterwards. Headnote text is capped at MEDIUM confidence.
- A quoted precedent, party argument, statute text or bare procedural history is never labelled SUPPORTS/OPPOSES (the validator rejects it). Outcome, winner and isolated words are not evidence.
- `needs_review` routes LOW-confidence, MIXED and UNCERTAIN items to human review. 74 of 520 items are flagged.
- `analysis.py` handles UNCERTAIN/MIXED explicitly: a returned passage counts as a correct support/oppose hit only if the v2 label is SUPPORTS/OPPOSES with HIGH or MEDIUM confidence (strict); lenient also accepts LOW. MIXED, NEUTRAL, UNCERTAIN and unlabelled never count as correct and never as "inverted".

## 3. Human-verified vs AI-assisted
| | count |
|---|---|
| Human-verified labels | **0** |
| AI-assisted, unreviewed (v1.0 pass, DEV) | 80 |
| AI-assisted, unreviewed (v1.1 pass: DEV 80, TEST 274, FRESH 166) | 520 |
| Legacy AI labels (re-imported, unreviewed) | 771 |

Counts for the v1.1 pass (n=520): relevance RELEVANT 355 / NOT_RELEVANT 158 / UNCERTAIN 7; court stance NEUTRAL_OR_CONTEXT 312, SUPPORTS 88, OPPOSES 54, MIXED 60, UNCERTAIN 6; role COURT_HOLDING 170, COURT_REASONING 152, QUOTED_PRECEDENT 73, FACTUAL_OR_PROCEDURAL_BACKGROUND 76, STATUTE_OR_RULE 23, PARTY_ARGUMENT 13, OTHER 13; confidence HIGH 146 / MEDIUM 351 / LOW 23; review status UNREVIEWED 520; source AI 520. (`python -X utf8 -m evalkit.annotation.analysis counts` reproduces this, including a per-pass breakdown.)

## 4. Evaluation run and split
Metrics recomputed from the stored runs with v2 labels (`analysis.py metrics`):

| set | queries | passages | role of the set |
|---|---|---|---|
| DEV | 3 | 80 | guideline calibration only; not reported |
| TEST | 12 | 274 | inspected at v1 → contaminated; reported with that caveat |
| FRESH | 8 | 166 | cleanest held-out set; main figures |

FRESH (strict policy, 8 queries, 166 labelled passages; lenient differs only in one cell):
- Ranked list, baseline A tf-idf: P@10 0.65; best pipeline D/E: P@10 0.74.
- Evidence-balanced stance lists: supP 0.28, oppP 0.10–0.15, both lists correct 0.25 (strict) / 0.38 (lenient, D/E).
TEST (strict): baseline P@10 0.68 → 0.87 (D/E); evidence-balanced supP 0.25, oppP 0.18, both-correct 0.33.

Legacy vs v2 agreement (stability check, not independence): TEST relevance 0.88 raw / κ 0.65; stance 0.64 raw / κ 0.42; FRESH relevance 0.73 / κ 0.36; stance 0.76 / κ 0.54. Where either side said SUPPORTS/OPPOSES, they gave the same decision in 38/115 (TEST) and 26/56 (FRESH) items, with 5 and 1 direct S↔O reversals. Role agreement is not computable (legacy has no role). The strict v1.1 guideline moves many legacy SUPPORTS/OPPOSES items to NEUTRAL or MIXED.

Conclusion kept from the earlier report, now on stricter labels: the classical pipeline improves relevance, but the evidence-balanced split is weak (about a quarter of items in each stance list are correct). The sample (8 FRESH queries, 166 passages, one AI annotator) is too small and too unverified to support any accuracy claim, and the 0.25–0.38 "both lists correct" figure rests on 8 queries.

## 5. Remaining ambiguities and limits
- No human reviewer; no independent second annotator. Inter-annotator agreement was **not** measured. The only agreement figures are legacy-vs-v2 from the same underlying model.
- Propositions (`propositions.json`) for TEST/FRESH were written after seeing those passages and the legacy labels, so the rubric is not blind.
- Ambiguous classes: headnotes (capped at MEDIUM; many mix holding and facts); quoted precedents the court adopts later (labelled NEUTRAL/MIXED when adoption is not in the passage, which lowers stance counts); conditional rules (e.g. dying declaration "if reliable") labelled MIXED/SUPPORTS depending on wording; passages cut off mid-headnote (labelled LOW).
- Several evidence spans were rejected by the validator (ligatures, text outside the passage) and were re-annotated with spans taken from the passage text; no label was altered silently (rejected rows were never written).
- Four TEST returned passages had no label in the earlier run; they count as not relevant.

## Annotation plan to turn this into a trustworthy evaluation
1. Have two independent human annotators (law-literate) label a stratified 20 % sample (≈100 passages: all LOW/MIXED/UNCERTAIN items plus a random draw) blind to AI labels, using GUIDELINE v1.1. Report kappa separately for relevance, stance and role.
2. A third reviewer adjudicates disagreements; the store keeps both labels (DISAGREEMENT status) and the adjudication.
3. Expand FRESH to ≥ 30 queries with new propositions written before retrieval, and freeze them.
4. Only then quote precision figures, with confidence intervals, and only for the human-reviewed subset.
