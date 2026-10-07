import sys, time
sys.path.insert(0, ".")
from streamlit.testing.v1 import AppTest

t = time.time()
at = AppTest.from_file("../app.py", default_timeout=180).run()
print("first run", round(time.time() - t, 1), "s; exceptions:", [e.value for e in at.exception])
print("metrics:", [(m.label, m.value) for m in at.metric])
print("title:", [x.value for x in at.title])
at.radio[0].set_value("Professional").run()
print("professional run exceptions:", [e.value for e in at.exception])
md = " ".join(m.value for m in at.markdown)
print("has LEGAL ISSUE:", "LEGAL ISSUE" in md, "| has Regular heading:", "What your question is about" in md)

