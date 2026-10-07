## dev (n=3 queries)

### Single ranked list (top-10 judgments)
| system | P5 | P10 | S_in_top10 | O_in_top10 | coverage | S_recall | O_recall |
|---|---|---|---|---|---|---|---|
| list|A BM25 (baseline) | 0.93 | 0.90 | 1.00 | 2.67 | 0.33 | 0.22 | 0.39 |
| list|B +Boolean concepts+synonyms | 0.93 | 0.90 | 1.67 | 3.33 | 1.00 | 0.46 | 0.48 |
| list|C +proximity | 0.93 | 0.90 | 2.00 | 3.33 | 1.00 | 0.52 | 0.52 |
| list|D +zones/statute | 0.93 | 0.87 | 1.33 | 3.33 | 1.00 | 0.33 | 0.52 |
| list|E +authority g(d) | 0.93 | 0.87 | 1.33 | 3.33 | 1.00 | 0.33 | 0.52 |

### Evidence-balanced output (support list + oppose list, <=5 each; P@k over interleaved list)
| system | P5 | P10 | returned | supP | oppP | supInv | oppInv | stance_coverage | both_sides_returned | S_recall | O_recall |
|---|---|---|---|---|---|---|---|---|---|---|---|
| EB|B +Boolean concepts+synonyms | 0.93 | 0.73 | 10.33 | 0.30 | 0.13 | 0.20 | 0.07 | 0.67 | 1.00 | 0.37 | 0.31 |
| EB|C +proximity | 0.87 | 0.73 | 10.33 | 0.47 | 0.07 | 0.20 | 0.07 | 0.33 | 1.00 | 0.37 | 0.28 |
| EB|D +zones/statute | 0.87 | 0.73 | 10.00 | 0.47 | 0.20 | 0.20 | 0.00 | 0.67 | 1.00 | 0.26 | 0.37 |
| EB|E +authority g(d) | 0.87 | 0.73 | 10.00 | 0.47 | 0.27 | 0.20 | 0.00 | 0.67 | 1.00 | 0.26 | 0.40 |
