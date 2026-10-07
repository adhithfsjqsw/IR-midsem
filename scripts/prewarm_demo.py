"""Pre-generate and SAVE the Regular and Professional summaries for the demo queries, so they open instantly in the app.

  python -X utf8 scripts/prewarm_demo.py              (needs Ollama running with the model pulled, or an ANTHROPIC_API_KEY)

It runs the same retrieval + stance + evidence-pack steps as app.py and calls respond() for both modes; finished, quote-verified
summaries are appended to data/summary_cache.jsonl, which respond() reads first. The saved entries are keyed by the evidence-pack hash, the mode,
the model and SUMMARY_MAX_ITEMS, so they are used only for the identical evidence. After ANY change to irlaw/*.py that alters the pack
(or to the model / SUMMARY_MAX_ITEMS), run this again before presenting. Nothing is written for failed or template outputs."""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from irlaw.balance import evidence_balanced  # noqa: E402
from irlaw.engine import Index  # noqa: E402
from irlaw.respond import build_pack, llm_provider, respond, summary_max_items  # noqa: E402

DEMO_QUERIES = [
    "Is a daughter entitled to a share in coparcenary property under the Hindu Succession Act?",
    "Is reservation in promotion permissible for scheduled castes and scheduled tribes?",
    "Can the court enhance compensation for land acquired under the Land Acquisition Act?",
    "Can a landlord evict a tenant on the ground of bona fide personal requirement?",
    "Is a confession made to a police officer admissible in evidence?",
    "Can bail be granted to an accused in an offence under the Narcotic Drugs and Psychotropic Substances Act?",
    "Can a court set aside an arbitral award under Section 34 on the ground of erroneous interpretation of the contract?",
]


def main():
    provider = llm_provider()
    print(f"summary provider: {provider} | passages summarised per query: {summary_max_items()}")
    if provider == "template":
        sys.exit("No language model is available (start Ollama or set ANTHROPIC_API_KEY): nothing to pre-run.")
    ix = Index()
    ok = 0
    for q in DEMO_QUERIES:
        t0 = time.time()
        pack = build_pack(ix, q, evidence_balanced(ix, q))
        for mode in ("regular", "professional"):
            t1 = time.time()
            text, engine = respond(mode, pack)
            good = not engine.startswith("template")
            ok += good
            print(f"  {mode:12} {time.time() - t1:5.0f}s  {engine[:95]}")
        print(f"{time.time() - t0:5.0f}s total | {q[:80]}", flush=True)
    print(f"done: {ok} of {2 * len(DEMO_QUERIES)} summaries are saved model-written results (the rest fell back to the template and were not saved).")


if __name__ == "__main__":
    main()
