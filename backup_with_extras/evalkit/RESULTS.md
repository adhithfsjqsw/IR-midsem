# Pilot evaluation (hackathon time constraint; judgments AI-assisted, see report)

Metric key: P5/P10 = fraction of top-k judgments (best passage) judged relevant; S/O_in_top10 = passages judged supporting / opposing in the top-10; coverage = fraction of queries whose top-10 contains >=1 S and >=1 O (unlabelled single list); S/O_recall = pooled recall of S/O passages; supP/oppP = precision of the support/oppose list (strict: label must equal S/O); supInv/oppInv = stance inversion rate; stance_coverage = fraction of queries where the support list has >=1 true S AND the oppose list has >=1 true O.

## DEV (3 queries; used to set parameters) (n=3 queries)

**Single ranked list, top-10 judgments**

| system | P5 | P10 | S_in_top10 | O_in_top10 | coverage | S_recall | O_recall |
|---|---|---|---|---|---|---|---|
| list|A BM25 (baseline) | 0.93 | 0.90 | 1.00 | 2.67 | 0.33 | 0.19 | 0.39 |
| list|B +Boolean concepts+synonyms | 0.93 | 0.90 | 1.67 | 3.33 | 1.00 | 0.44 | 0.48 |
| list|C +proximity | 0.93 | 0.90 | 2.00 | 3.33 | 1.00 | 0.50 | 0.52 |
| list|D +zones/statute | 0.93 | 0.87 | 1.33 | 3.33 | 1.00 | 0.31 | 0.52 |
| list|E +authority g(d) | 0.93 | 0.87 | 1.33 | 3.33 | 1.00 | 0.31 | 0.52 |

**Evidence-balanced output (support list + oppose list)**

| system | P5 | P10 | returned | supP | oppP | supInv | oppInv | stance_coverage | both_sides_returned |
|---|---|---|---|---|---|---|---|---|---|
| EB|B +Boolean concepts+synonyms | 0.73 | 0.43 | 4.33 | 0.25 | 0.53 | 0.00 | 0.23 | 0.33 | 0.33 |
| EB|C +proximity | 0.73 | 0.37 | 3.67 | 0.50 | 0.42 | 0.00 | 0.33 | 0.33 | 0.33 |
| EB|D +zones/statute | 0.87 | 0.50 | 5.00 | 0.50 | 0.33 | 0.00 | 0.13 | 0.33 | 0.67 |
| EB|E +authority g(d) | 0.87 | 0.50 | 5.00 | 0.50 | 0.33 | 0.00 | 0.13 | 0.33 | 0.67 |


## TEST (12 queries; final system, but inspected once under v1 - see report) (n=12 queries)

**Single ranked list, top-10 judgments**

| system | P5 | P10 | S_in_top10 | O_in_top10 | coverage | S_recall | O_recall |
|---|---|---|---|---|---|---|---|
| list|A BM25 (baseline) | 0.90 | 0.89 | 1.08 | 1.50 | 0.25 | 0.41 | 0.38 |
| list|B +Boolean concepts+synonyms | 0.93 | 0.88 | 1.00 | 1.83 | 0.33 | 0.43 | 0.46 |
| list|C +proximity | 0.92 | 0.88 | 1.17 | 1.83 | 0.25 | 0.50 | 0.42 |
| list|D +zones/statute | 0.93 | 0.86 | 1.00 | 1.83 | 0.33 | 0.36 | 0.46 |
| list|E +authority g(d) | 0.95 | 0.86 | 1.00 | 1.75 | 0.33 | 0.36 | 0.45 |

**Evidence-balanced output (support list + oppose list)**

| system | P5 | P10 | returned | supP | oppP | supInv | oppInv | stance_coverage | both_sides_returned |
|---|---|---|---|---|---|---|---|---|---|
| EB|B +Boolean concepts+synonyms | 0.78 | 0.58 | 6.67 | 0.17 | 0.16 | 0.06 | 0.10 | 0.08 | 0.67 |
| EB|C +proximity | 0.77 | 0.54 | 6.33 | 0.17 | 0.15 | 0.07 | 0.10 | 0.08 | 0.67 |
| EB|D +zones/statute | 0.70 | 0.42 | 4.58 | 0.30 | 0.36 | 0.17 | 0.10 | 0.17 | 0.67 |
| EB|E +authority g(d) | 0.70 | 0.42 | 4.58 | 0.30 | 0.36 | 0.17 | 0.10 | 0.17 | 0.67 |


## FRESH (8 queries; written after freeze, never inspected before pooling) (n=8 queries)

**Single ranked list, top-10 judgments**

| system | P5 | P10 | S_in_top10 | O_in_top10 | coverage | S_recall | O_recall |
|---|---|---|---|---|---|---|---|
| list|A BM25 (baseline) | 0.90 | 0.82 | 2.12 | 0.62 | 0.25 | 0.58 | 0.48 |
| list|B +Boolean concepts+synonyms | 0.95 | 0.88 | 2.25 | 1.12 | 0.38 | 0.65 | 0.63 |
| list|C +proximity | 0.95 | 0.88 | 2.25 | 1.12 | 0.38 | 0.65 | 0.63 |
| list|D +zones/statute | 0.93 | 0.88 | 2.50 | 1.00 | 0.50 | 0.79 | 0.71 |
| list|E +authority g(d) | 0.93 | 0.88 | 2.50 | 1.00 | 0.50 | 0.79 | 0.71 |

**Evidence-balanced output (support list + oppose list)**

| system | P5 | P10 | returned | supP | oppP | supInv | oppInv | stance_coverage | both_sides_returned |
|---|---|---|---|---|---|---|---|---|---|
| EB|B +Boolean concepts+synonyms | 0.85 | 0.57 | 6.38 | 0.23 | 0.12 | 0.14 | 0.18 | 0.12 | 0.88 |
| EB|C +proximity | 0.80 | 0.54 | 6.25 | 0.20 | 0.15 | 0.14 | 0.20 | 0.12 | 0.88 |
| EB|D +zones/statute | 0.75 | 0.47 | 5.12 | 0.35 | 0.07 | 0.14 | 0.23 | 0.25 | 0.62 |
| EB|E +authority g(d) | 0.75 | 0.47 | 5.12 | 0.35 | 0.07 | 0.14 | 0.23 | 0.25 | 0.62 |


## ALL HELD-OUT (TEST+FRESH, 20 queries) (n=20 queries)

**Single ranked list, top-10 judgments**

| system | P5 | P10 | S_in_top10 | O_in_top10 | coverage | S_recall | O_recall |
|---|---|---|---|---|---|---|---|
| list|A BM25 (baseline) | 0.90 | 0.86 | 1.50 | 1.15 | 0.25 | 0.49 | 0.42 |
| list|B +Boolean concepts+synonyms | 0.94 | 0.88 | 1.50 | 1.55 | 0.35 | 0.53 | 0.53 |
| list|C +proximity | 0.93 | 0.88 | 1.60 | 1.55 | 0.30 | 0.57 | 0.51 |
| list|D +zones/statute | 0.93 | 0.86 | 1.60 | 1.50 | 0.40 | 0.55 | 0.56 |
| list|E +authority g(d) | 0.94 | 0.86 | 1.60 | 1.45 | 0.40 | 0.55 | 0.55 |

**Evidence-balanced output (support list + oppose list)**

| system | P5 | P10 | returned | supP | oppP | supInv | oppInv | stance_coverage | both_sides_returned |
|---|---|---|---|---|---|---|---|---|---|
| EB|B +Boolean concepts+synonyms | 0.81 | 0.57 | 6.55 | 0.19 | 0.14 | 0.09 | 0.14 | 0.10 | 0.75 |
| EB|C +proximity | 0.78 | 0.54 | 6.30 | 0.18 | 0.15 | 0.10 | 0.14 | 0.10 | 0.75 |
| EB|D +zones/statute | 0.72 | 0.44 | 4.80 | 0.32 | 0.25 | 0.16 | 0.15 | 0.20 | 0.65 |
| EB|E +authority g(d) | 0.72 | 0.44 | 4.80 | 0.32 | 0.25 | 0.16 | 0.15 | 0.20 | 0.65 |


