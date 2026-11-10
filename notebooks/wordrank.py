"""WordRank (EASSE's "Lexical complexity score"), reimplemented without EASSE.

EASSE computes WordRank by calling `get_wordrank_score` from tseval
(facebookresearch/text-simplification-evaluation, feature_extraction.py).
EASSE and tseval require Python 3.6/3.7 plus torch, fairseq and more, so this
file reproduces that one function's logic exactly instead:

  1. drop tokens that are punctuation characters (string.punctuation)
  2. drop NLTK English stopwords (case-insensitive check)
  3. keep only words among the 50,000 most frequent in tseval's English
     Wikipedia frequency table (case-sensitive lookup, as in tseval)
  4. score = 75th percentile (third quartile) of log(1 + rank),
     where rank is 0-based ("the" = 0)
  5. if no words remain, score = log(1 + 50000)

Lower score = more common, everyday vocabulary.

Setup:
  * Frequency table: download `enwiki_frequency_table.tsv` from
    https://github.com/facebookresearch/text-simplification-evaluation
    (tseval/resources/various/) and save it as resources/enwiki_frequency_table.tsv
  * Stopwords: run once:  import nltk; nltk.download("stopwords")
"""

from functools import lru_cache
from pathlib import Path
from string import punctuation

import numpy as np

FREQ_TABLE = Path("../resources/enwiki_frequency_table.tsv")
VOCAB_SIZE = 50_000


@lru_cache(maxsize=1)
def get_word2rank(path=FREQ_TABLE, vocab_size=VOCAB_SIZE):
    """Map each of the `vocab_size` most frequent words to its 0-based rank."""
    word2rank = {}
    with open(path, encoding="utf-8") as f:
        for rank, line in enumerate(f):
            if rank >= vocab_size:
                break
            word, _ = line.rstrip("\n").split("\t")
            word2rank[word] = rank
    return word2rank


@lru_cache(maxsize=1)
def get_stopwords():
    from nltk.corpus import stopwords
    return frozenset(stopwords.words("english"))


def wordrank(text: str) -> float:
    word2rank = get_word2rank()
    stops = get_stopwords()
    words = [
        w for w in text.split()
        if w not in punctuation        # 1. punctuation tokens
        and w.lower() not in stops     # 2. stopwords
        and w in word2rank             # 3. top-50k vocabulary only
    ]
    if not words:
        return float(np.log(1 + len(word2rank)))
    log_ranks = [np.log(1 + word2rank[w]) for w in words]
    return float(np.quantile(log_ranks, 0.75))
