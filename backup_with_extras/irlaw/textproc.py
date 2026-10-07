"""Tokenisation / normalisation shared by indexing and querying (same pipeline on both sides)."""
import re
from functools import lru_cache

from nltk.stem import PorterStemmer

_stemmer = PorterStemmer()
TOKEN_RE = re.compile(r"[a-z0-9]+(?:'[a-z]+)?")

# Light stop list. Negators (not, no, without, never, nor) are deliberately NOT here:
# the stance module needs them in the positional index.  They are excluded from the
# *concept* terms at query time instead (see query.py).
STOP = frozenset("""a an and are as at be been being by for from has have had he her his i in is it its of on or
that the their them there these they this those to was were which who whom with
do does did if then than so such we you your our also any all each other into upon under over
said thereof therein herein hereby aforesaid whether""".split())

# Modal verbs are kept in the index (the stance operators need them) but never used as query concept terms.
MODALS = frozenset("can may could shall should will would might must".split())
NEGATORS = frozenset(["not", "no", "never", "neither", "nor", "cannot", "without"])


@lru_cache(maxsize=200_000)
def stem(w: str) -> str:
    return _stemmer.stem(w)


def tokenize(text: str):
    """Case-fold + split.  Returns raw lowercase tokens (not stemmed, stopwords kept) so that
    positions are the true token offsets in the passage."""
    return TOKEN_RE.findall(text.lower())


def analyze(text: str):
    """tokens -> list of (position, stem) with stopwords dropped but positions preserved
    (so proximity distances are measured in the original token stream)."""
    out = []
    for i, t in enumerate(tokenize(text)):
        if t in STOP and t not in NEGATORS:
            continue
        out.append((i, stem(t)))
    return out

