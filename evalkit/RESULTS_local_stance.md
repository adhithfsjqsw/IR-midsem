# Local rule-based stance classifier vs AI-assisted reference (append-only log of runs)

## Run 2026-10-07 20:57 - splits: dev

- queries: 3, passages compared: 80 (all have a reference label)
- local predictions: SUPPORTS=3, OPPOSES=2, MIXED=3, NEUTRAL_OR_CONTEXT=0, UNCERTAIN=72
- supports (strict): local precision 1/3 = 0.33, recall of reference 1/9 = 0.11; phrase baseline precision 0/15 = 0.00
- opposes (strict): local precision 0/2 = 0.00, recall of reference 0/13 = 0.00; phrase baseline precision 4/15 = 0.27
- supports (lenient): local precision 1/3 = 0.33, recall of reference 1/9 = 0.11; phrase baseline precision 0/15 = 0.00
- opposes (lenient): local precision 0/2 = 0.00, recall of reference 0/13 = 0.00; phrase baseline precision 4/15 = 0.27
- decided coverage 5/80 = 0.06; direct SUPPORTS<->OPPOSES reversals vs reference: 1; role agreement 0.33; decided stance on passages the reference calls party/quoted/statute/background: 0/31
- confusion (local/reference): UNCE/NEUT=42, UNCE/OPPO=12, UNCE/SUPP=7, UNCE/MIXE=6, UNCE/UNCE=5, OPPO/NEUT=2, MIXE/NEUT=2, SUPP/UNCE=1, SUPP/OPPO=1, SUPP/SUPP=1, MIXE/SUPP=1

## Run 2026-10-07 20:58 - splits: dev

- queries: 3, passages compared: 80 (all have a reference label)
- local predictions: SUPPORTS=3, OPPOSES=2, MIXED=3, NEUTRAL_OR_CONTEXT=28, UNCERTAIN=44
- supports (strict): local precision 1/3 = 0.33, recall of reference 1/9 = 0.11; phrase baseline precision 0/15 = 0.00
- opposes (strict): local precision 0/2 = 0.00, recall of reference 0/13 = 0.00; phrase baseline precision 4/15 = 0.27
- supports (lenient): local precision 1/3 = 0.33, recall of reference 1/9 = 0.11; phrase baseline precision 0/15 = 0.00
- opposes (lenient): local precision 0/2 = 0.00, recall of reference 0/13 = 0.00; phrase baseline precision 4/15 = 0.27
- decided coverage 5/80 = 0.06; direct SUPPORTS<->OPPOSES reversals vs reference: 1; role agreement 0.44; decided stance on passages the reference calls party/quoted/statute/background: 0/31
- confusion (local/reference): UNCE/NEUT=25, NEUT/NEUT=17, NEUT/OPPO=8, UNCE/SUPP=6, UNCE/UNCE=5, UNCE/MIXE=4, UNCE/OPPO=4, OPPO/NEUT=2, NEUT/MIXE=2, MIXE/NEUT=2, SUPP/UNCE=1, SUPP/OPPO=1, SUPP/SUPP=1, NEUT/SUPP=1

## Run 2026-10-07 20:59 - splits: dev

- queries: 3, passages compared: 80 (all have a reference label)
- local predictions: SUPPORTS=7, OPPOSES=2, MIXED=4, NEUTRAL_OR_CONTEXT=28, UNCERTAIN=39
- supports (strict): local precision 3/7 = 0.43, recall of reference 3/9 = 0.33; phrase baseline precision 0/15 = 0.00
- opposes (strict): local precision 0/2 = 0.00, recall of reference 0/13 = 0.00; phrase baseline precision 4/15 = 0.27
- supports (lenient): local precision 3/7 = 0.43, recall of reference 3/9 = 0.33; phrase baseline precision 0/15 = 0.00
- opposes (lenient): local precision 0/2 = 0.00, recall of reference 0/13 = 0.00; phrase baseline precision 4/15 = 0.27
- decided coverage 9/80 = 0.11; direct SUPPORTS<->OPPOSES reversals vs reference: 1; role agreement 0.44; decided stance on passages the reference calls party/quoted/statute/background: 2/31
- confusion (local/reference): UNCE/NEUT=23, NEUT/NEUT=17, NEUT/OPPO=8, UNCE/UNCE=5, UNCE/OPPO=4, UNCE/SUPP=4, UNCE/MIXE=3, SUPP/SUPP=3, OPPO/NEUT=2, NEUT/MIXE=2, MIXE/NEUT=2, SUPP/NEUT=2, MIXE/MIXE=1, SUPP/UNCE=1

## Run 2026-10-07 20:59 - splits: test,fresh

- queries: 20, passages compared: 440 (all have a reference label)
- local predictions: SUPPORTS=27, OPPOSES=29, MIXED=29, NEUTRAL_OR_CONTEXT=150, UNCERTAIN=205
- supports (strict): local precision 8/27 = 0.30, recall of reference 8/77 = 0.10; phrase baseline precision 26/100 = 0.26
- opposes (strict): local precision 10/29 = 0.34, recall of reference 10/39 = 0.26; phrase baseline precision 15/98 = 0.15
- supports (lenient): local precision 8/27 = 0.30, recall of reference 8/79 = 0.10; phrase baseline precision 26/100 = 0.26
- opposes (lenient): local precision 10/29 = 0.34, recall of reference 10/41 = 0.24; phrase baseline precision 17/98 = 0.17
- decided coverage 56/440 = 0.13; direct SUPPORTS<->OPPOSES reversals vs reference: 3; role agreement 0.41; decided stance on passages the reference calls party/quoted/statute/background: 13/154
- confusion (local/reference): UNCE/NEUT=129, NEUT/NEUT=93, UNCE/SUPP=38, NEUT/SUPP=27, UNCE/MIXE=26, SUPP/NEUT=16, MIXE/NEUT=16, NEUT/MIXE=15, NEUT/OPPO=15, UNCE/OPPO=12, OPPO/NEUT=12, OPPO/OPPO=10, SUPP/SUPP=8, MIXE/MIXE=6
