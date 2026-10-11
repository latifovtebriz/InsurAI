"""Knowledge ingestion and effective-dated semantic retrieval service."""

import logging
from dataclasses import dataclass

from app.modules.platform.knowledge.embedder import (
    DeterministicFakeEmbedder,
    cosine_similarity,
    fake_embedder,
)
from app.modules.platform.knowledge.models import KBChunk
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from data.synthetic.products_catalog import PRODUCTS_DATA, ProductDef

logger = logging.getLogger(__name__)


@dataclass
class Citation:
    clause_id: str
    section: str
    title: str
    text: str
    score: float
    product_version: int


class KnowledgeService:
    """Manages clause-level semantic chunking, ingestion, and effective-dated retrieval."""

    def __init__(self, embedder: DeterministicFakeEmbedder | None = None) -> None:
        self.embedder = embedder or fake_embedder

    def ingest_product_wording(self, session: Session, product: ProductDef) -> int:
        """
        Ingests all versions and numbered clauses of a product into platform.kb_chunks.
        Idempotent: Re-ingestion updates existing records without creating duplicates.
        """
        ingested_count = 0

        for ver in product.versions:
            for clause in ver.clauses:
                embed_text = f"{clause.title}\n{clause.text}"
                vector = self.embedder.embed_text(embed_text)

                # Query existing chunk
                stmt = select(KBChunk).where(
                    KBChunk.collection == "wording",
                    KBChunk.product_code == product.product_code,
                    KBChunk.version == ver.version,
                    KBChunk.clause_id == clause.clause_id,
                )
                existing = session.scalars(stmt).first()

                if existing:
                    # Update in place
                    existing.title = clause.title
                    existing.content = clause.text
                    existing.embedding = vector
                    existing.effective_from = ver.effective_from
                    existing.effective_to = ver.effective_to
                else:
                    new_chunk = KBChunk(
                        collection="wording",
                        product_code=product.product_code,
                        version=ver.version,
                        clause_id=clause.clause_id,
                        section=clause.section,
                        title=clause.title,
                        content=clause.text,
                        effective_from=ver.effective_from,
                        effective_to=ver.effective_to,
                        embedding=vector,
                        metadata_json={
                            "product_name": product.name,
                            "version_code": ver.version_code,
                        },
                    )
                    session.add(new_chunk)
                    ingested_count += 1

        session.commit()
        return ingested_count

    def ingest_all_catalogs(self, session: Session) -> int:
        """Ingests all products from the products catalog into the knowledge store."""
        total = 0
        for p in PRODUCTS_DATA:
            total += self.ingest_product_wording(session, p)
        return total

    def search_policy_wording(
        self,
        session: Session,
        query: str,
        product_code: str,
        incident_date: str,
        top_k: int = 5,
    ) -> list[Citation]:
        """
        Retrieves top-k policy wording clauses.
        MANDATORY INVARIANT: Filters by 'Date in Force' at incident_date FIRST before vector ranking!
        """
        # 1. Metadata filter: only clauses in force on the incident date
        stmt = select(KBChunk).where(
            KBChunk.collection == "wording",
            KBChunk.product_code == product_code,
            KBChunk.effective_from <= incident_date,
            or_(
                KBChunk.effective_to.is_(None),
                KBChunk.effective_to >= incident_date,
            ),
        )
        candidates = session.scalars(stmt).all()

        if not candidates:
            logger.warning(
                f"No wording clauses in force for product '{product_code}' on incident date '{incident_date}'"
            )
            return []

        # 2. Vector search: rank candidates by cosine similarity against query embedding
        query_vec = self.embedder.embed_text(query)

        scored: list[tuple[float, KBChunk]] = []
        for chunk in candidates:
            score = cosine_similarity(query_vec, chunk.embedding)
            scored.append((score, chunk))

        # Sort descending by score
        scored.sort(key=lambda x: x[0], reverse=True)

        citations: list[Citation] = []
        for score, chunk in scored[:top_k]:
            citations.append(
                Citation(
                    clause_id=chunk.clause_id,
                    section=chunk.section,
                    title=chunk.title,
                    text=chunk.content,
                    score=round(score, 4),
                    product_version=chunk.version or 1,
                )
            )

        return citations


knowledge_service = KnowledgeService()
