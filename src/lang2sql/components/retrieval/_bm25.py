"""
Internal BM25 index — stdlib only (math, collections).

BM25 parameters:
  k1 = 1.5  (term frequency saturation)
  b  = 0.75 (document length normalization)

Tokenization: text.lower().split()  (whitespace, no external deps)
"""

from __future__ import annotations

import math
from collections import Counter
from typing import Any

_K1 = 1.5
_B = 0.75


def _tokenize(text: str) -> list[str]:
    return text.lower().split()


def _extract_text(value: Any) -> list[str]:
    """Recursively extract text tokens from any value (str, list, dict, other)."""
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        result: list[str] = []
        for item in value:
            result.extend(_extract_text(item))
        return result
    if isinstance(value, dict):
        result = []
        for k, v in value.items():
            result.append(str(k))
            result.extend(_extract_text(v))
        return result
    return [str(value)]


def _entry_to_text(entry: dict[str, Any], index_fields: list[str]) -> str:
    """
    Convert a catalog dict entry into a single text string for indexing.

    Handles:
    - str fields  → joined as-is
    - dict fields → "key value key value ..." (for columns: {col_name: col_desc})
    - list fields → each element extracted recursively
    - other types → str(value)
    """
    parts: list[str] = []
    for field in index_fields:
        value = entry.get(field)
        if value is None:
            continue
        parts.extend(_extract_text(value))
    return " ".join(parts)


class _BM25Index:
    """
    In-memory BM25 index over a list[dict] catalog.

    Usage:
        index = _BM25Index(catalog, index_fields=["name", "description", "columns"])
        scores = index.score("주문 테이블")  # list[float], one per catalog entry
    """

    def __init__(
        self,
        catalog: list[dict[str, Any]],
        index_fields: list[str],
    ) -> None:
        self._catalog = catalog
        self._n = len(catalog)

        # Tokenize each document
        self._docs: list[list[str]] = [
            _tokenize(_entry_to_text(entry, index_fields)) for entry in catalog
        ]

        # Term frequencies per document
        self._tfs: list[Counter[str]] = [Counter(doc) for doc in self._docs]

        # Document lengths
        doc_lengths = [len(doc) for doc in self._docs]
        self._avgdl: float = sum(doc_lengths) / self._n if self._n > 0 else 0.0

        # Inverted index: term → set of doc indices that contain it
        self._df: Counter[str] = Counter()
        for tf in self._tfs:
            for term in tf:
                self._df[term] += 1

    def score(self, query: str) -> list[float]:
        """
        Return a BM25 score for each catalog entry.

        Args:
            query: Natural language query string.

        Returns:
            List of float scores, one per catalog entry, in original order.
        """
        if self._n == 0:
            return []

        query_terms = _tokenize(query)
        scores = [0.0] * self._n

        for term in query_terms:
            df_t = self._df.get(term, 0)
            if df_t == 0:
                continue

            # IDF — smoothed to avoid log(0)
            idf = math.log((self._n - df_t + 0.5) / (df_t + 0.5) + 1)

            for i, tf in enumerate(self._tfs):
                tf_t = tf.get(term, 0)
                if tf_t == 0:
                    continue

                dl = len(self._docs[i])
                denom = tf_t + _K1 * (1 - _B + _B * dl / self._avgdl)
                scores[i] += idf * (tf_t * (_K1 + 1)) / denom

        return scores
