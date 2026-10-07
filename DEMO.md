# Recording script: Legal vertical search demo

**Target length:** about 6½ minutes (within the assignment's 5–8 minute video requirement).
**Format:** live application demonstration with narration; no slide deck.

## Before recording

1. Start the app from this project directory and confirm the search page loads.
2. Restart the Streamlit process after code changes so it imports the current project code.
3. Confirm the corpus/index is available and the query returns results.
4. Decide whether an Anthropic stance model is configured. Never show an API key.
   - Without a configured model, expect a topical-only/unclassified result state: the app must not present topical matches as confirmed support or opposition.
   - With a configured model, check the displayed method and inspect its relevance decision, stance, confidence, and quoted evidence for a result. Do not claim accuracy that has not been evaluated.
5. Close unrelated windows and notifications; set browser zoom so the query, results, and score trace are legible. Test microphone and screen capture.

If the interface says `Classification method: unknown` while still assigning support/opposition, stop and restart the app from this project directory before recording. That combination is inconsistent with the intended no-classifier fallback.

## Timed narration and actions

### 0:00–0:35 — Introduce the problem

**Say:** “This project is a vertical search engine for Indian Supreme Court judgments. A general search engine can find documents containing similar words, but a legal researcher also needs to see where a passage occurs, which court decided it, when it was decided, and what legal position the passage takes. This demo shows how the system combines those signals.”

**Show:** The project search page and its legal-search focus.

### 0:35–1:10 — Explain the collection

**Say:** “The indexed collection contains Supreme Court judgments from the years and sources described in the project report. The system extracts judgment metadata and splits the text into passages, so it can retrieve a useful passage and retain a link to the original judgment. The collection is bounded, so results should be understood as search results within this dataset, not a complete answer to Indian law.”

**Show:** Corpus/index information if available in the interface or report. State the exact corpus figures only if they match the current index and report.

### 1:10–2:25 — Run a legal question and explain retrieval

**Action:** Search for `Can a dying declaration alone form the basis of conviction?`

**Say:** “I’ll use a legal question about whether a dying declaration can by itself support a conviction. The search engine processes the words and legal concepts, finds candidate passages in its index, and ranks them using lexical relevance and proximity. Its positional index records where terms occur, which helps it detect terms appearing near one another. It also uses document zones and judgment metadata where available. These are retrieval signals: a high score means a passage matched the query well, not that it proves a legal conclusion.”

**Show:** Search intermediates if present—query processing, concept groups, Boolean/posting counts, and candidate counts. Expand only the relevant section and keep the result visible.

### 2:25–3:40 — Inspect evidence and stance carefully

**Action:** Open one of the top results and its score explanation; point to the passage and judgment link.

**Say:** “Here the system shows the matching passage, judgment metadata, and a score trace. The trace makes the ranking more explainable: it shows the contributions from text relevance, proximity, zones, and authority features. Authority here is a static proxy based on available bench information; it is not a citation-network analysis. I can open the source judgment to check the passage in context.”

**If a stance model is configured, say:** “The stance classifier separately estimates whether this passage is relevant to the question and, if it is, whether it supports, opposes, mixes, or is uncertain about the proposition. That is a model prediction attached to a passage, not a verified legal label.”

**If no stance model is configured, say:** “This run has no stance classifier configured, so these are topical candidates only. The system should leave them unclassified rather than treating keyword overlap as proof of support or opposition.”

### 3:40–4:25 — Show response modes and reproducibility

**Action:** If the UI provides Regular and Professional modes, switch between them for the same search. Point out the evidence-pack identifier/hash if shown.

**Say:** “The response mode changes how the explanation is worded; it should not change the retrieved evidence. The evidence-pack identifier lets us check that both modes are describing the same underlying results. The search ranking and the stance assessment are separate steps.”

### 4:25–5:35 — Present evaluation honestly

**Action:** Show the evaluation summary only if it is current and corresponds to the code/version being demonstrated.

**Say:** “We evaluate retrieval separately from stance classification. Precision at ten measures how many of the first ten results are relevant for the evaluated queries. The report includes a lexical baseline for comparison. Historical scores in the report belong to the earlier cue-based stance approach and its labeled examples; they do not establish the accuracy of a newly configured language-model classifier. The current model-based classifier needs its own evaluation on a held-out set before we can claim its support/opposition decisions are accurate.”

**Important:** Read exact numbers only after confirming the report states their dataset, version, and method. Do not present historical metrics as results for the current classifier.

### 5:35–6:30 — Limitations and close

**Say:** “The main contribution is combining legal document structure with ranked passage retrieval and a visible score explanation. The current limits are the coverage of the indexed corpus, the quality of extracted text and metadata, and the need to evaluate stance predictions independently. The system is a research and discovery aid: users should inspect the cited judgment and surrounding context. This concludes the demonstration.”

## Recording checklist

- Keep the video between 5 and 8 minutes and narrate what is happening on screen.
- Demonstrate a real query, intermediate retrieval evidence, a result passage, and its source link.
- Avoid slides; the assignment asks for a demo video.
- Do not expose API keys, local secrets, or unrelated personal information.
- If a screen or result differs from this script, describe what the running application actually does; do not narrate intended behavior as if it were working.
- Save the recording and play it back once to verify the audio, readable text, and full duration.
