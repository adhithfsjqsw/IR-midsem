"""Offline checks of the stance classifier (no network, no API key needed).  Run: python -X utf8 -m evalkit.test_stance_offline
A fake client replaces the Anthropic client; STANCE_CACHE is disabled so nothing is written to disk."""
import json
import os
import types

os.environ["STANCE_CACHE"] = "off"
os.environ.pop("ANTHROPIC_API_KEY", None)

from irlaw import stance as S  # noqa: E402

PASSAGE = "The Court held that an employer may terminate a probationer without notice if the contract so provides."
ITEM = {"id": "1", "passage": PASSAGE, "zone": "body", "previous_context": "", "next_context": "", "case": "X v. Y"}


def fake(rows):
    class C:
        class messages:
            @staticmethod
            def create(**kw):
                assert "ignore previous" not in kw["system"].lower()
                return types.SimpleNamespace(content=[types.SimpleNamespace(text=rows if isinstance(rows, str) else json.dumps({"results": rows}))])
    return C


def lab(**kw):
    base = dict(id="1", relevance="RELEVANT", role="COURT_HOLDING", stance="SUPPORTS", confidence="HIGH",
                evidence_span="an employer may terminate a probationer without notice", rationale="r")
    base.update(kw)
    return base


def run(rows, item=ITEM):
    out, info = S.classify_items("Employer may terminate probationer without notice", [item], fake(rows))
    return out.get(item["id"]), info


def check(name, cond):
    print(("PASS " if cond else "FAIL ") + name)
    return cond


ok = True
l, i = run([lab()]);                                   ok &= check("valid court holding SUPPORTS kept", l["stance"] == "SUPPORTS" and l["verified"] is False)
l, _ = run([lab(role="PARTY_ARGUMENT")]);              ok &= check("party argument never SUPPORTS", l["stance"] == "NEUTRAL_OR_CONTEXT")
l, _ = run([lab(role="QUOTED_PRECEDENT", stance="OPPOSES")]); ok &= check("unadopted quoted precedent never OPPOSES", l["stance"] == "NEUTRAL_OR_CONTEXT")
l, _ = run([lab(evidence_span="text that is not in the passage")]); ok &= check("fabricated span -> UNCERTAIN", l["stance"] == "UNCERTAIN" and l["confidence"] == "LOW")
l, _ = run([lab(evidence_span="")]);                   ok &= check("SUPPORTS without span -> UNCERTAIN", l["stance"] == "UNCERTAIN")
l, _ = run([lab(stance="MAYBE")]);                     ok &= check("invalid enum -> UNCERTAIN", l["stance"] == "UNCERTAIN")
l, _ = run([lab(relevance="NOT_RELEVANT")]);           ok &= check("decided stance on not-relevant -> UNCERTAIN", l["stance"] == "UNCERTAIN")
l, _ = run([lab(confidence="LOW")]);                   ok &= check("LOW-confidence stance abstains", l["stance"] == "UNCERTAIN")
l, _ = run("this is not json");                        ok &= check("malformed output -> no confident stance", l["stance"] == "UNCERTAIN" and not l["output_validated"])
l, _ = run([]);                                        ok &= check("missing item -> UNCERTAIN", l["stance"] == "UNCERTAIN")
l, _ = run([lab(id="999")]);                           ok &= check("mismatched id -> UNCERTAIN", l["stance"] == "UNCERTAIN")
l, _ = run([lab()], dict(ITEM, zone="headnote"));      ok &= check("headnote confidence capped at MEDIUM", l["confidence"] == "MEDIUM")
l, _ = run([lab(stance="MIXED", role="COURT_REASONING", confidence="MEDIUM")]); ok &= check("MIXED from court reasoning kept", l["stance"] == "MIXED")
out, info = S.classify_items("p", [ITEM])
ok &= check("no API key -> unavailable, no labels, no network", out == {} and info["available"] is False)
from irlaw.stance import classify_items_local  # noqa: E402
PROP = "Can a dying declaration alone form the basis of conviction?"
def loc(text, zone="body"):
    return classify_items_local(PROP, [{"id": "1", "passage": text, "zone": zone}])["1"]
ok &= check("local: counsel's submission is never the court's stance",
            loc("The learned counsel for the appellant submitted that a dying declaration alone cannot form the basis of conviction.")["stance"] not in ("SUPPORTS", "OPPOSES"))
ok &= check("local: long quoted precedent is never the court's stance",
            loc("The Court observed: \u201cA dying declaration alone can form the basis of conviction if it is voluntary and reliable and inspires confidence.\u201d")["stance"] not in ("SUPPORTS", "OPPOSES"))
l = loc("We hold that a dying declaration alone can form the basis of conviction, which is permissible when it is voluntary.")
ok &= check("local: court holding with an exact span can SUPPORT, never HIGH confidence", l["stance"] in ("SUPPORTS", "MIXED") and l["confidence"] != "HIGH" and l["evidence_span"] != "")
ok &= check("local: unrelated passage is never NOT_RELEVANT (cannot hide) and never decided",
            loc("The appellant purchased the plot in 1990 by a registered sale deed.")["relevance"] != "NOT_RELEVANT")
os.environ["STANCE_MODEL"] = "not a model; DROP TABLE"
out, info = S.classify_items("p", [ITEM], fake([lab()]))
ok &= check("invalid STANCE_MODEL rejected", out == {} and not info["available"])
os.environ.pop("STANCE_MODEL")
print("ALL PASS" if ok else "SOME CHECKS FAILED")
raise SystemExit(0 if ok else 1)
