# Automatic stance classifier vs phrase baseline (new-version output; older RESULTS*.md are untouched)

Reference = AI-assisted, unreviewed v2 labels (not verified truth). Numbers are agreement with that reference. The classifier is never tuned on these sets. Phrase-baseline figures describe the OLD system only.

### Split `test`: 12 queries, 275 pooled passages, 274 with a reference label
- phrase baseline (whole pool, strict): support precision 0.25 (n=60), oppose precision 0.19 (n=58); abstains on 156 of 274 pooled passages
- phrase baseline (whole pool, lenient): support precision 0.25 (n=60), oppose precision 0.19 (n=58); abstains on 156 of 274 pooled passages
- compared on the SAME 241 passages (12 queries) labelled by both the automatic classifier and the reference
- automatic predictions on them: SUPPORTS=42, OPPOSES=11, MIXED=0, NEUTRAL_OR_CONTEXT=187, UNCERTAIN=1
  - automatic classifier (strict): support precision 0.48 (n=42), oppose precision 0.27 (n=11), decided coverage 0.22, abstained/mixed/contextual 188
  - phrase baseline (strict): support precision 0.22 (n=51), oppose precision 0.22 (n=51), decided coverage 0.42, abstained/mixed/contextual 139
  - automatic classifier (lenient): support precision 0.48 (n=42), oppose precision 0.27 (n=11), decided coverage 0.22, abstained/mixed/contextual 188
  - phrase baseline (lenient): support precision 0.22 (n=51), oppose precision 0.22 (n=51), decided coverage 0.42, abstained/mixed/contextual 139
  - role agreement with reference 0.45; direct SUPPORTS<->OPPOSES reversals 1

### Split `fresh`: 8 queries, 166 pooled passages, 166 with a reference label
- phrase baseline (whole pool, strict): support precision 0.28 (n=40), oppose precision 0.10 (n=40); abstains on 86 of 166 pooled passages
- phrase baseline (whole pool, lenient): support precision 0.28 (n=40), oppose precision 0.15 (n=40); abstains on 86 of 166 pooled passages
- compared on the SAME 156 passages (8 queries) labelled by both the automatic classifier and the reference
- automatic predictions on them: SUPPORTS=33, OPPOSES=3, MIXED=0, NEUTRAL_OR_CONTEXT=117, UNCERTAIN=3
  - automatic classifier (strict): support precision 0.30 (n=33), oppose precision 0.00 (n=3), decided coverage 0.23, abstained/mixed/contextual 120
  - phrase baseline (strict): support precision 0.30 (n=37), oppose precision 0.11 (n=38), decided coverage 0.48, abstained/mixed/contextual 81
  - automatic classifier (lenient): support precision 0.30 (n=33), oppose precision 0.00 (n=3), decided coverage 0.23, abstained/mixed/contextual 120
  - phrase baseline (lenient): support precision 0.30 (n=37), oppose precision 0.16 (n=38), decided coverage 0.48, abstained/mixed/contextual 81
  - role agreement with reference 0.41; direct SUPPORTS<->OPPOSES reversals 3
