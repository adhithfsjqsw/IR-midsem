## fresh (n=8 queries)

### Single ranked list (top-10 judgments)
| system | P5 | P10 | S_in_top10 | O_in_top10 | coverage | S_recall | O_recall |
|---|---|---|---|---|---|---|---|
| list|A BM25 (baseline) | 0.90 | 0.82 | 2.12 | 0.62 | 0.25 | 0.63 | 0.48 |
| list|B +Boolean concepts+synonyms | 0.95 | 0.88 | 2.25 | 1.12 | 0.38 | 0.70 | 0.63 |
| list|C +proximity | 0.95 | 0.88 | 2.25 | 1.12 | 0.38 | 0.70 | 0.63 |
| list|D +zones/statute | 0.93 | 0.88 | 2.50 | 1.00 | 0.50 | 0.84 | 0.71 |
| list|E +authority g(d) | 0.93 | 0.88 | 2.50 | 1.00 | 0.50 | 0.84 | 0.71 |

### Evidence-balanced output (support list + oppose list, <=5 each; P@k over interleaved list)
| system | P5 | P10 | returned | supP | oppP | supInv | oppInv | stance_coverage | both_sides_returned | S_recall | O_recall |
|---|---|---|---|---|---|---|---|---|---|---|---|
| EB|B +Boolean concepts+synonyms | 0.85 | 0.60 | 6.50 | 0.37 | 0.12 | 0.14 | 0.18 | 0.12 | 0.88 | 0.44 | 0.61 |
| EB|C +proximity | 0.85 | 0.59 | 6.38 | 0.34 | 0.15 | 0.17 | 0.20 | 0.12 | 0.88 | 0.44 | 0.77 |
| EB|D +zones/statute | 0.78 | 0.49 | 5.12 | 0.39 | 0.07 | 0.17 | 0.23 | 0.25 | 0.62 | 0.46 | 0.64 |
| EB|E +authority g(d) | 0.78 | 0.49 | 5.12 | 0.39 | 0.07 | 0.17 | 0.23 | 0.25 | 0.62 | 0.46 | 0.64 |
