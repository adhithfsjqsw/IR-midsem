# Automatic stance classifier vs phrase baseline (new-version output; older RESULTS*.md are untouched)

Reference = AI-assisted, unreviewed v2 labels (not verified truth). Numbers are agreement with that reference. The classifier is never tuned on these sets. Phrase-baseline figures describe the OLD system only.

### Split `dev`: 3 queries, 80 pooled passages, 80 with a reference label
- phrase baseline (whole pool, strict): support precision 0.00 (n=15), oppose precision 0.27 (n=15); abstains on 50 of 80 pooled passages
- phrase baseline (whole pool, lenient): support precision 0.00 (n=15), oppose precision 0.27 (n=15); abstains on 50 of 80 pooled passages
- **Automatic classifier: NOT EVALUATED** - no automatic label file for this split (requires a configured API key). Reproduce with: `python -X utf8 -m evalkit.annotation.autolabel dev` then `python -X utf8 -m evalkit.eval_stance dev`.

### Split `test`: 12 queries, 275 pooled passages, 274 with a reference label
- phrase baseline (whole pool, strict): support precision 0.25 (n=60), oppose precision 0.19 (n=58); abstains on 156 of 274 pooled passages
- phrase baseline (whole pool, lenient): support precision 0.25 (n=60), oppose precision 0.19 (n=58); abstains on 156 of 274 pooled passages
- **Automatic classifier: NOT EVALUATED** - no automatic label file for this split (requires a configured API key). Reproduce with: `python -X utf8 -m evalkit.annotation.autolabel test` then `python -X utf8 -m evalkit.eval_stance test`.

### Split `fresh`: 8 queries, 166 pooled passages, 166 with a reference label
- phrase baseline (whole pool, strict): support precision 0.28 (n=40), oppose precision 0.10 (n=40); abstains on 86 of 166 pooled passages
- phrase baseline (whole pool, lenient): support precision 0.28 (n=40), oppose precision 0.15 (n=40); abstains on 86 of 166 pooled passages
- **Automatic classifier: NOT EVALUATED** - no automatic label file for this split (requires a configured API key). Reproduce with: `python -X utf8 -m evalkit.annotation.autolabel fresh` then `python -X utf8 -m evalkit.eval_stance fresh`.
