# Pilot evaluation (hackathon time constraint; judgments AI-assisted, see report)

Metric key: P5/P10 = fraction of top-k judgments (best passage) judged relevant; S/O_in_top10 = passages judged supporting / opposing in the top-10; coverage = fraction of queries whose top-10 contains >=1 S and >=1 O (unlabelled single list); S/O_recall = pooled recall of S/O passages; supP/oppP = precision of the support/oppose list (strict: label must equal S/O); supInv/oppInv = stance inversion rate; stance_coverage = fraction of queries where the support list has >=1 true S AND the oppose list has >=1 true O.

## DEV (3 queries; used to set parameters) (n=3 queries)

**Single ranked list, top-10 judgments**

| system | P5 | P10 | S_in_top10 | O_in_top10 | coverage | S_recall | O_recall |
|---|---|---|---|---|---|---|---|
| list|A tf-idf cosine (baseline) | 0.87 | 0.83 | 0.67 | 1.00 | 0.33 | 0.09 | 0.11 |
| list|B +Boolean concepts+synonyms | 0.93 | 0.87 | 2.33 | 3.00 | 1.00 | 0.36 | 0.40 |
| list|C +proximity | 1.00 | 0.90 | 2.33 | 3.00 | 0.67 | 0.30 | 0.40 |
| list|D +zones/statute | 0.93 | 0.87 | 1.00 | 3.67 | 0.67 | 0.12 | 0.47 |
| list|E +authority g(d) | 0.93 | 0.87 | 1.00 | 3.67 | 0.67 | 0.12 | 0.47 |

**Evidence-balanced output (support list + oppose list)**

| system | P5 | P10 | returned | supP | oppP | supInv | oppInv | stance_coverage | both_sides_returned |
|---|---|---|---|---|---|---|---|---|---|
| EB|B +Boolean concepts+synonyms | 0.93 | 0.83 | 10.00 | 0.33 | 0.40 | 0.13 | 0.13 | 1.00 | 1.00 |
| EB|C +proximity | 0.93 | 0.83 | 10.00 | 0.33 | 0.40 | 0.13 | 0.20 | 1.00 | 1.00 |
| EB|D +zones/statute | 0.73 | 0.73 | 10.00 | 0.13 | 0.40 | 0.13 | 0.20 | 0.67 | 1.00 |
| EB|E +authority g(d) | 0.73 | 0.73 | 10.00 | 0.13 | 0.40 | 0.13 | 0.20 | 0.67 | 1.00 |


## TEST (12 queries; final system, but inspected once under v1 - see report) (n=12 queries)

**Single ranked list, top-10 judgments**

| system | P5 | P10 | S_in_top10 | O_in_top10 | coverage | S_recall | O_recall |
|---|---|---|---|---|---|---|---|
| list|A tf-idf cosine (baseline) | 0.87 | 0.77 | 1.33 | 1.42 | 0.50 | 0.42 | 0.30 |
| list|B +Boolean concepts+synonyms | 0.93 | 0.87 | 1.33 | 1.67 | 0.42 | 0.36 | 0.35 |
| list|C +proximity | 0.92 | 0.87 | 1.25 | 1.83 | 0.58 | 0.33 | 0.40 |
| list|D +zones/statute | 0.92 | 0.87 | 1.00 | 2.08 | 0.58 | 0.26 | 0.45 |
| list|E +authority g(d) | 0.92 | 0.88 | 1.00 | 2.08 | 0.58 | 0.26 | 0.45 |

**Evidence-balanced output (support list + oppose list)**

| system | P5 | P10 | returned | supP | oppP | supInv | oppInv | stance_coverage | both_sides_returned |
|---|---|---|---|---|---|---|---|---|---|
| EB|B +Boolean concepts+synonyms | 0.92 | 0.84 | 10.00 | 0.17 | 0.20 | 0.08 | 0.12 | 0.33 | 1.00 |
| EB|C +proximity | 0.90 | 0.84 | 10.00 | 0.17 | 0.20 | 0.10 | 0.12 | 0.33 | 1.00 |
| EB|D +zones/statute | 0.90 | 0.83 | 9.92 | 0.15 | 0.22 | 0.13 | 0.12 | 0.33 | 1.00 |
| EB|E +authority g(d) | 0.92 | 0.83 | 9.92 | 0.15 | 0.22 | 0.13 | 0.12 | 0.33 | 1.00 |


## FRESH (8 queries; written after freeze, never inspected before pooling) (n=8 queries)

**Single ranked list, top-10 judgments**

| system | P5 | P10 | S_in_top10 | O_in_top10 | coverage | S_recall | O_recall |
|---|---|---|---|---|---|---|---|
| list|A tf-idf cosine (baseline) | 0.80 | 0.79 | 1.62 | 1.00 | 0.50 | 0.33 | 0.42 |
| list|B +Boolean concepts+synonyms | 0.90 | 0.91 | 2.25 | 1.00 | 0.38 | 0.51 | 0.31 |
| list|C +proximity | 0.90 | 0.91 | 2.00 | 1.00 | 0.38 | 0.42 | 0.31 |
| list|D +zones/statute | 0.90 | 0.90 | 2.50 | 1.50 | 0.62 | 0.65 | 0.51 |
| list|E +authority g(d) | 0.90 | 0.90 | 2.50 | 1.50 | 0.62 | 0.65 | 0.51 |

**Evidence-balanced output (support list + oppose list)**

| system | P5 | P10 | returned | supP | oppP | supInv | oppInv | stance_coverage | both_sides_returned |
|---|---|---|---|---|---|---|---|---|---|
| EB|B +Boolean concepts+synonyms | 0.95 | 0.86 | 10.00 | 0.25 | 0.23 | 0.12 | 0.15 | 0.38 | 1.00 |
| EB|C +proximity | 0.95 | 0.89 | 10.00 | 0.23 | 0.23 | 0.12 | 0.20 | 0.38 | 1.00 |
| EB|D +zones/statute | 0.95 | 0.90 | 10.00 | 0.28 | 0.23 | 0.08 | 0.15 | 0.50 | 1.00 |
| EB|E +authority g(d) | 0.95 | 0.89 | 10.00 | 0.28 | 0.23 | 0.08 | 0.15 | 0.50 | 1.00 |


## ALL HELD-OUT (TEST+FRESH, 20 queries) (n=20 queries)

**Single ranked list, top-10 judgments**

| system | P5 | P10 | S_in_top10 | O_in_top10 | coverage | S_recall | O_recall |
|---|---|---|---|---|---|---|---|
| list|A tf-idf cosine (baseline) | 0.84 | 0.78 | 1.45 | 1.25 | 0.50 | 0.38 | 0.35 |
| list|B +Boolean concepts+synonyms | 0.92 | 0.89 | 1.70 | 1.40 | 0.40 | 0.42 | 0.33 |
| list|C +proximity | 0.91 | 0.89 | 1.55 | 1.50 | 0.50 | 0.37 | 0.36 |
| list|D +zones/statute | 0.91 | 0.88 | 1.60 | 1.85 | 0.60 | 0.42 | 0.48 |
| list|E +authority g(d) | 0.91 | 0.89 | 1.60 | 1.85 | 0.60 | 0.42 | 0.48 |

**Evidence-balanced output (support list + oppose list)**

| system | P5 | P10 | returned | supP | oppP | supInv | oppInv | stance_coverage | both_sides_returned |
|---|---|---|---|---|---|---|---|---|---|
| EB|B +Boolean concepts+synonyms | 0.93 | 0.85 | 10.00 | 0.20 | 0.21 | 0.10 | 0.13 | 0.35 | 1.00 |
| EB|C +proximity | 0.92 | 0.86 | 10.00 | 0.19 | 0.21 | 0.11 | 0.15 | 0.35 | 1.00 |
| EB|D +zones/statute | 0.92 | 0.86 | 9.95 | 0.20 | 0.22 | 0.11 | 0.13 | 0.40 | 1.00 |
| EB|E +authority g(d) | 0.93 | 0.85 | 9.95 | 0.20 | 0.22 | 0.11 | 0.13 | 0.40 | 1.00 |


