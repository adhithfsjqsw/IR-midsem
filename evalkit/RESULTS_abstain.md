# Abstention rule vs no abstention (new-version output)

Reference: AI-assisted, unreviewed v2 labels. Top-10 judgments per query; unlabelled passages are not counted as relevant.

| split | queries | system | mean results returned | queries returning 0 | P@returned (labelled only) | unlabelled returned |
|---|---|---|---|---|---|---|
| dev | 3 | no abstention | 10.0 | 0 | 0.70 (n=30) | 0 |
| dev | 3 | abstention (STRICT) | 10.0 | 0 | 0.82 (n=28) | 2 |
| test | 12 | no abstention | 10.0 | 0 | 0.87 (n=120) | 0 |
| test | 12 | abstention (STRICT) | 10.0 | 0 | 0.87 (n=119) | 1 |
| fresh | 8 | no abstention | 10.0 | 0 | 0.74 (n=80) | 0 |
| fresh | 8 | abstention (STRICT) | 10.0 | 0 | 0.74 (n=80) | 0 |

Off-topic queries (no reference labels): results returned with abstention vs without
- 'Does painting a mural on a public wall require prior permission': no abstention 40, abstention 1
- 'xyzzy quux blorf': no abstention 0, abstention 0
