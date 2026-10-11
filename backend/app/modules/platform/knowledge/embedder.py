"""Deterministic embedding engine for offline RAG and testing."""

import hashlib
import math
import re
from typing import Protocol

from app.config import settings


def cosine_similarity(v1: list[float], v2: list[float]) -> float:
    """Computes cosine similarity between two unit or arbitrary float vectors."""
    dot = sum(a * b for a, b in zip(v1, v2, strict=False))
    norm_a = math.sqrt(sum(a * a for a in v1))
    norm_b = math.sqrt(sum(b * b for b in v2))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


class Embedder(Protocol):
    """Protocol for vector embedding models."""

    def embed_text(self, text: str) -> list[float]: ...

    def embed_batch(self, texts: list[str]) -> list[list[float]]: ...


class DeterministicFakeEmbedder:
    """
    Deterministic fake embedder producing unit-normalized 768-dim vectors.
    Token-aware bag-of-words hashing gives high cosine similarity to semantically overlapping texts.
    """

    def __init__(self, dim: int | None = None) -> None:
        self.dim = dim or settings.embedding_dim

    def embed_text(self, text: str) -> list[float]:
        vector = [0.0] * self.dim
        tokens = re.findall(r"\w+", text.lower())

        if not tokens:
            tokens = ["empty"]

        # Project each token deterministically into vector space
        for token in tokens:
            token_hash = int(hashlib.sha256(token.encode("utf-8")).hexdigest(), 16)
            idx = token_hash % self.dim
            sign = 1.0 if (token_hash >> 10) % 2 == 0 else -1.0
            vector[idx] += sign * 1.0

            # Second hash projection for dense dispersion
            idx2 = (token_hash >> 16) % self.dim
            vector[idx2] += sign * 0.5

        # Normalize to unit length
        norm = math.sqrt(sum(x * x for x in vector))
        if norm > 0:
            vector = [x / norm for x in vector]

        return vector

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [self.embed_text(t) for t in texts]


fake_embedder = DeterministicFakeEmbedder()
