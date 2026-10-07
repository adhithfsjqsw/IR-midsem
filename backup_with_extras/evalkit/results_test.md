## test (n=12 queries)

### Single ranked list (top-10 judgments)
| system | P5 | P10 | S_in_top10 | O_in_top10 | coverage | S_recall | O_recall |
|---|---|---|---|---|---|---|---|
| list|A BM25 (baseline) | 0.92 | 0.92 | 1.08 | 1.67 | 0.33 | 0.47 | 0.51 |
| list|B +Boolean concepts+synonyms | 0.92 | 0.92 | 1.17 | 2.00 | 0.33 | 0.54 | 0.59 |
| list|C +proximity | 0.92 | 0.92 | 1.25 | 2.00 | 0.25 | 0.56 | 0.55 |
| list|D +zones/statute | 0.93 | 0.91 | 1.08 | 2.08 | 0.33 | 0.38 | 0.60 |
| list|E +authority g(d) | 0.95 | 0.91 | 1.08 | 2.08 | 0.33 | 0.38 | 0.60 |

### Evidence-balanced output (support list + oppose list, <=5 each; P@k over interleaved list)
| system | P5 | P10 | returned | supP | oppP | supInv | oppInv | stance_coverage | both_sides_returned | S_recall | O_recall |
|---|---|---|---|---|---|---|---|---|---|---|---|
| EB|B +Boolean concepts+synonyms | 0.83 | 0.62 | 10.58 | 0.09 | 0.18 | 0.13 | 0.07 | 0.17 | 0.83 | 0.39 | 0.30 |
| EB|C +proximity | 0.85 | 0.66 | 10.50 | 0.11 | 0.16 | 0.13 | 0.07 | 0.17 | 0.83 | 0.43 | 0.30 |
| EB|D +zones/statute | 0.87 | 0.67 | 10.08 | 0.11 | 0.18 | 0.20 | 0.07 | 0.08 | 0.83 | 0.39 | 0.40 |
| EB|E +authority g(d) | 0.87 | 0.67 | 10.08 | 0.11 | 0.16 | 0.20 | 0.07 | 0.08 | 0.83 | 0.39 | 0.38 |
