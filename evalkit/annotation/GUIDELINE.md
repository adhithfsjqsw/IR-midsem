# Annotation guideline — passage relevance and court stance (version 1.0)

Status: written by an AI annotator (Claude) for this project; **not yet reviewed by a human legal expert**. Labels produced under it are
PROVISIONAL. Changes to this guideline are recorded at the bottom and every label record carries the guideline version it was made under.

## Unit and context
Unit = one passage (≈150 words) of a Supreme Court of India judgment, judged against ONE exact proposition (see `propositions.json`).
The annotator sees the passage plus the end of the previous passage and the start of the next passage of the same judgment, to resolve
quotation marks, attribution ("it was argued…", "the Court held…"), negation and exceptions. Use only what is shown.

## Fields (one record per query × passage)
1. **relevance** — RELEVANT / NOT_RELEVANT / UNCERTAIN.
   RELEVANT only if the passage materially addresses the same legal issue *and the same kind of conditions* as the proposition.
   Shared words ("notice", "bail") are not enough. UNCERTAIN if the connection cannot be decided from what is shown.
2. **court_stance** — SUPPORTS / OPPOSES / MIXED / NEUTRAL_OR_CONTEXT / UNCERTAIN.
   * SUPPORTS: the **court's own** holding or reasoning affirms the proposition under materially matching conditions.
   * OPPOSES: the court's own holding or reasoning rejects it, or imposes a limit/condition that changes the answer for the proposition as worded.
   * MIXED: the court states both directions, or a rule whose qualification changes the answer (e.g. "yes, but only if …" where the proposition has no such condition).
   * NEUTRAL_OR_CONTEXT: relevant background (facts, procedure, statute text, a party's or a lower court's view, precedent merely reported) that does not establish the court's position.
   * UNCERTAIN: stance cannot be decided from passage + shown context.
   A stance other than NEUTRAL_OR_CONTEXT/UNCERTAIN requires relevance = RELEVANT.
3. **speaker_role** — COURT_HOLDING (operative holding / headnote "Held") · COURT_REASONING (the court's own analysis) ·
   PARTY_ARGUMENT · QUOTED_PRECEDENT (earlier case quoted/summarised, not clearly adopted) · STATUTE_OR_RULE ·
   FACTUAL_OR_PROCEDURAL_BACKGROUND · OTHER · UNCLEAR.
4. **party_argument_stance** — only for PARTY_ARGUMENT: SUPPORTS / OPPOSES the proposition; else NOT_APPLICABLE; UNCERTAIN if unclear.
5. **evidence_span** — shortest exact text copied from the passage that justifies the stance (or the relevance decision if stance is NEUTRAL/UNCERTAIN). Empty only if nothing in the passage supports a label.
6. **rationale** — one or two sentences linking the span to the proposition.
7. **confidence** — HIGH / MEDIUM / LOW: clarity of text + context (not plausibility of the legal claim).

## Hard rules
* Court stance SUPPORTS/OPPOSES is allowed only when speaker_role is COURT_HOLDING or COURT_REASONING (or QUOTED_PRECEDENT that the court clearly adopts — then record the role as COURT_REASONING). Otherwise use NEUTRAL_OR_CONTEXT.
* A party's submission is never the court's view, even if it matches the proposition. Record it as PARTY_ARGUMENT + party stance, court stance NEUTRAL_OR_CONTEXT, unless the next text shows the court adopting or rejecting it.
* Never infer stance from who won, the disposal ("allowed/dismissed"), the sign of a word ("illegal", "valid"), or keyword overlap.
* The proposition's conditions matter: a holding about a *different* condition (e.g. a permanent employee vs a probationer) is NOT_RELEVANT or NEUTRAL_OR_CONTEXT, not support/opposition.
* A rule stated with a condition that the proposition does not contain, which can change the answer ("conviction can rest on dying declaration **if** reliable and voluntary") is MIXED only when that condition is *material to the proposition as worded*; if the proposition itself is the unqualified rule and the court affirms it while merely describing safeguards for weighing the evidence, that is SUPPORTS (HIGH/MEDIUM) — decide per proposition notes.
* If the passage is cut so the decisive sentence is missing, use UNCERTAIN, not a guess.
* Route to human review: confidence LOW, stance MIXED or UNCERTAIN, role UNCLEAR, any relevance UNCERTAIN.

## Provenance
`label_source` = AI / HUMAN / HUMAN_ADJUDICATED. `review_status` = UNREVIEWED / HUMAN_REVIEWED / DISAGREEMENT / ADJUDICATED.
AI labels stay UNREVIEWED until a named human checks them. Disagreeing labels from two annotators are both kept and flagged DISAGREEMENT; nothing is overwritten.

## Additional rules introduced in 1.1 (calibrated on the DEV queries only)
* **Headnotes are editorial.** In the Supreme Court Reports a headnote ("Held: …") is the law reporter's summary of the holding, not the judges' own words. It is accepted as COURT_HOLDING evidence, but a stance whose only evidence is headnote text has confidence at most MEDIUM; HIGH requires the same point to be visible in the judgment text shown. (Enforced automatically by `ingest.py` for guideline ≥ 1.1.)
* **Adoption of quoted precedent** requires the court's own words in the shown passage or context ("we agree", "we follow", "this is the law", "the position of law that emerges is …"). Quotation marks, "(emphasis supplied)" or a citation alone are not adoption → QUOTED_PRECEDENT, court_stance NEUTRAL_OR_CONTEXT (or MIXED if the quoted text itself states both directions).
* **Rule text** (statute, rules, standing orders) that happens to state the proposition is still STATUTE_OR_RULE → NEUTRAL_OR_CONTEXT unless the court says it applies the rule to decide the issue.
* **Bare procedural orders** ("Delay condoned.", "Leave granted.") without reasoning → NOT_RELEVANT, role FACTUAL_OR_PROCEDURAL_BACKGROUND.
* **Refusal on the facts**: a court that refuses relief for lack of the condition the law requires (e.g. no sufficient cause) is recorded as OPPOSES only where the proposition asks whether relief may be granted in that situation (see the proposition's "opposes" line); it is otherwise NEUTRAL/MIXED.

## Change log
* 1.0 — initial version.
* 1.1 — headnote confidence cap, adoption rule for quoted precedent, rule-text rule, bare-order rule, refusal-on-facts rule. Source of the changes: inspection of disagreements between the legacy labels and the v1.0 DEV pass (DEV queries D1–D3 only). No TEST or FRESH label was consulted.
