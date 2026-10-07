"""Offline checks of the LLM summary layer (no network): a fake model reply replaces the Ollama/Claude call.
Run: python -X utf8 -m evalkit.test_respond_offline"""
import json
import os

os.environ.pop("ANTHROPIC_API_KEY", None)
os.environ["LLM_PROVIDER"] = "ollama"
os.environ["SUMMARY_CACHE"] = "off"

from irlaw import respond as R  # noqa: E402

PACK = {"query": "Can X?", "counts": {"support": 1, "oppose": 1, "contested": 0, "uncertain": 0, "not_relevant": 0}, "verdict": "v",
        "disclaimer": R.DISCLAIMER, "classification_method": "m", "classification_notice": "n", "heuristic": False, "sha256": "x",
        "items": [dict(id="S1", side="support", rank=1, case="A v. B", case_id="2020 INSC 1", citation="[2020] 1 SCR 1", date="01-01-2020", url="http://u/1",
                       passage="The court held that X is permissible when the conditions in the Act are satisfied.",
                       classification={"stance": "SUPPORTS", "role": "COURT_HOLDING", "confidence": "MEDIUM", "evidence_span": "X is permissible"},
                       statutes=[], zone="body", bench=3, disposal="Allowed", court="SC", score=1.0, signals={"matched_cues": []}),
                  dict(id="O1", side="oppose", rank=1, case="C v. D", case_id="2021 INSC 2", citation="[2021] 1 SCR 2", date="01-01-2021", url="http://u/2",
                       passage="The court held that X is not permissible without prior sanction of the government.",
                       classification={"stance": "OPPOSES", "role": "COURT_HOLDING", "confidence": "MEDIUM", "evidence_span": "X is not permissible"},
                       statutes=[], zone="body", bench=3, disposal="Allowed", court="SC", score=1.0, signals={"matched_cues": []})]}

GOOD = {"short_answer": "The retrieved cases point in different directions, so the question looks unsettled.",
        "items": [{"id": "S1", "summary": "The court allowed X where the statutory conditions are met.", "quote": "X is permissible when the conditions in the Act are satisfied"},
                  {"id": "O1", "summary": "The court refused X unless the government first sanctions it.", "quote": "X is not permissible without prior sanction of the government"}]}


def reply(obj):
    R._chat = lambda provider, system, body, num_predict=2200: (obj if isinstance(obj, str) else json.dumps(obj), "ollama:fake (local LLM)")
    return R.respond("regular", PACK)


def check(name, cond):
    print(("PASS " if cond else "FAIL ") + name)
    return cond


ok = True
t, e = reply(GOOD)
ok &= check("verified summaries are assembled with quotes, sources and disclaimer", e.startswith("ollama") and "In the court's words" in t and "**Sources**" in t and R.DISCLAIMER in t)
ok &= check("both items passed the quote check", "all summaries passed" in e)
bad = json.loads(json.dumps(GOOD)); bad["items"][0]["quote"] = "the court expressly held that daughters inherit equally"
t, e = reply(bad)
ok &= check("a quote that is not in the passage is dropped (item shows 'no verified summary')", "(no verified summary)" in t and "1/2" in e and "daughters inherit" not in t)
bad = json.loads(json.dumps(GOOD)); bad["items"][1]["summary"] = "Decided in 2019 INSC 999 that X is banned."
t, e = reply(bad)
ok &= check("invented case id in a summary is dropped", "2019 INSC 999" not in t)
bad = json.loads(json.dumps(GOOD)); bad["items"][0]["id"] = "S9"
t, e = reply(bad)
ok &= check("unknown id ignored", "S9" not in t)
bad = json.loads(json.dumps(GOOD)); bad["short_answer"] = "See 2019 INSC 999 for the law."
t, e = reply(bad)
ok &= check("short answer with an invented case id is replaced by a neutral sentence", "2019 INSC 999" not in t)
t, e = reply("not json at all")
ok &= check("malformed output -> template with reason", e.startswith("template"))
t, e = reply({"short_answer": "x" * 30, "items": []})
ok &= check("nothing verifiable -> template", e.startswith("template"))
def boom(*a, **k):
    raise TimeoutError("x")
R._chat = boom
t, e = R.respond("professional", PACK)
ok &= check("model failure/timeout -> template with reason", e.startswith("template") and "failed" in e)
t, e = reply(GOOD) if False else (None, None)
os.environ["LLM_PROVIDER"] = "template"
t, e = R.respond("regular", PACK)
ok &= check("LLM_PROVIDER=template never calls a model", e.startswith("template"))
os.environ["LLM_PROVIDER"] = "ollama"
R._chat = lambda provider, system, body, num_predict=2200: (json.dumps(GOOD), "ollama:fake (local LLM)")
t, e = R.respond("professional", PACK)
ok &= check("professional mode includes the neutral citation and predicted stance", "2020 INSC 1" in t and "Predicted: SUPPORTS" in t)
# --- item limit and saved-result cache
os.environ["SUMMARY_MAX_ITEMS"] = "1"
seen = {}
def spy(provider, system, body, num_predict=2200):
    seen["ids"] = [i["id"] for i in body["items"]]
    return json.dumps(GOOD), "ollama:fake (local LLM)"
R._chat = spy
t, e = R.respond("regular", PACK)
ok &= check("SUMMARY_MAX_ITEMS=1 sends only the best item to the model and labels the rest 'not summarised'", seen["ids"] == ["S1"] and "not summarised" in t)
os.environ.pop("SUMMARY_MAX_ITEMS")
import tempfile
os.environ["SUMMARY_CACHE"] = os.path.join(tempfile.mkdtemp(), "c.jsonl")
calls = []
def counting(provider, system, body, num_predict=2200):
    calls.append(1)
    return json.dumps(GOOD), "ollama:fake (local LLM)"
R._chat = counting
t1, e1 = R.respond("regular", PACK)
t2, e2 = R.respond("regular", PACK)
ok &= check("a finished summary is saved once and reused without calling the model again", len(calls) == 1 and t1 == t2 and "saved result" in e2)
t3, e3 = R.respond("professional", PACK)
ok &= check("the other mode is a separate saved entry", len(calls) == 2)
print("ALL PASS" if ok else "SOME CHECKS FAILED")
raise SystemExit(0 if ok else 1)
