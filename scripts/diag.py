import json, sys
sys.path.insert(0, ".")
split = sys.argv[1]; sysname = sys.argv[2] if len(sys.argv) > 2 else "EB|E +authority g(d)"
runs = json.load(open(f"evalkit/runs_{split}.json")); labels = json.load(open(f"evalkit/labels_{split}.json"))
pool = {q: {r["pid"]: r for r in v} for q, v in json.load(open(f"evalkit/pool_{split}.json", encoding="utf-8")).items()}
for q, systems in runs.items():
    eb = systems[sysname]
    for side in ("support", "oppose"):
        row = [(p, labels[q].get(str(p), "?")) for p in eb[side]]
        print(q, side, " ".join(f"{p}:{c}" for p, c in row))
