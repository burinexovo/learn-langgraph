"""Shared offline embedding for 14_rag_retrieval.ipynb.

`langchain_core.embeddings.DeterministicFakeEmbedding` looks like the obvious
choice for an offline demo, but it embeds text as pure hash-seeded random
noise -- there is zero relationship between text similarity and vector
similarity, so a retrieval demo built on it would look broken (a query about
LangGraph could just as easily retrieve a document about coffee machines).

This module instead uses the "hashing trick": each text is represented as a
hashed bag-of-character-bigrams vector. It is still not a real embedding
model (no learned semantics), but it does reflect actual lexical overlap
between texts, so similarity search behaves sensibly for a small demo corpus.
"""

from __future__ import annotations

import hashlib
import math

from langchain_core.embeddings import Embeddings


class HashingBagOfCharsEmbeddings(Embeddings):
    """Deterministic, offline stand-in for a real embedding model."""

    def __init__(self, size: int = 256) -> None:
        self.size = size

    def _vector(self, text: str) -> list[float]:
        vec = [0.0] * self.size
        chars = list(text)
        bigrams = [chars[i] + chars[i + 1] for i in range(len(chars) - 1)] or chars
        for bg in bigrams:
            h = int(hashlib.sha256(bg.encode("utf-8")).hexdigest(), 16)
            vec[h % self.size] += 1.0
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._vector(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._vector(text)
