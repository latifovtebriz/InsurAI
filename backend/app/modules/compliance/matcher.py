"""Fuzzy name matching engine and simulated sanctions/PEP watchlist catalog."""

import re
from typing import Any

from app.modules.compliance.models import WatchlistEntity
from sqlalchemy import select
from sqlalchemy.orm import Session

DEFAULT_WATCHLIST_DATA = [
    {
        "entity_name": "Viktor Anatolyevich Bout",
        "entity_type": "INDIVIDUAL",
        "list_name": "OFAC_SDN",
        "tax_id": "RU-882910492",
        "country": "RU",
        "notes": "Specially Designated National (SDN) arms trafficking sanctions.",
    },
    {
        "entity_name": "Global Maritime Logistics Trading Corp",
        "entity_type": "COMPANY",
        "list_name": "OFAC_SDN",
        "tax_id": "CY-99182301",
        "country": "CY",
        "notes": "Cover company identified in sanctioned maritime oil transshipment.",
    },
    {
        "entity_name": "Dawood Ibrahim Kaskar",
        "entity_type": "INDIVIDUAL",
        "list_name": "UN_SANCTIONS",
        "tax_id": "IN-77192001",
        "country": "IN",
        "notes": "UN Security Council Consolidated List transnational illicit network.",
    },
    {
        "entity_name": "Farhad Aliyev",
        "entity_type": "INDIVIDUAL",
        "list_name": "PEP",
        "tax_id": "AZ-10029384",
        "country": "AZ",
        "notes": "Politically Exposed Person (former senior government executive).",
    },
    {
        "entity_name": "Caspian Petroleum Transit CJSC",
        "entity_type": "COMPANY",
        "list_name": "LOCAL_WATCHLIST",
        "tax_id": "AZ-99881122",
        "country": "AZ",
        "notes": "High-risk entity flagged by national financial intelligence unit.",
    },
]


def normalize_text(text: str) -> str:
    """Normalizes string for fuzzy token comparison."""
    cleaned = re.sub(r"[^\w\s]", "", text.lower())
    return " ".join(cleaned.split())


def compute_string_similarity(str1: str, str2: str) -> float:
    """
    Computes token-based Jaccard and character bigram similarity between two entity names.
    Returns float in range [0.0, 1.0].
    """
    norm1 = normalize_text(str1)
    norm2 = normalize_text(str2)

    if norm1 == norm2:
        return 1.0

    tokens1 = set(norm1.split())
    tokens2 = set(norm2.split())

    if not tokens1 or not tokens2:
        return 0.0

    # Token overlap (Jaccard and containment)
    intersection = tokens1.intersection(tokens2)
    union = tokens1.union(tokens2)
    jaccard = len(intersection) / len(union)
    min_tokens = min(len(tokens1), len(tokens2))
    containment = (len(intersection) / min_tokens) if min_tokens > 0 else 0.0

    # Character bigrams
    bigrams1 = {norm1[i : i + 2] for i in range(len(norm1) - 1)}
    bigrams2 = {norm2[i : i + 2] for i in range(len(norm2) - 1)}

    if not bigrams1 or not bigrams2:
        return max(jaccard, containment * 0.8)

    bi_overlap = len(bigrams1.intersection(bigrams2))
    bi_union = len(bigrams1.union(bigrams2))
    bi_score = bi_overlap / bi_union if bi_union > 0 else 0.0

    token_score = max(jaccard, containment * 0.85)
    return round((token_score * 0.6) + (bi_score * 0.4), 4)


def ensure_watchlist_seed(session: Session) -> list[WatchlistEntity]:
    """Populates standard simulated sanctions watchlist if empty."""
    entities: list[WatchlistEntity] = []
    for item in DEFAULT_WATCHLIST_DATA:
        existing = session.scalars(
            select(WatchlistEntity).where(WatchlistEntity.entity_name == item["entity_name"])
        ).first()
        if not existing:
            entity = WatchlistEntity(
                entity_name=item["entity_name"],
                entity_type=item["entity_type"],
                list_name=item["list_name"],
                tax_id=item["tax_id"],
                country=item["country"],
                notes=item["notes"],
            )
            session.add(entity)
            entities.append(entity)
        else:
            entities.append(existing)
    session.flush()
    return entities


def screen_entity(
    name: str,
    tax_id: str | None,
    watchlist: list[WatchlistEntity],
    threshold: float = 0.65,
) -> list[dict[str, Any]]:
    """
    Screens party name and tax ID against watchlist entities.
    Returns matches with score >= threshold or exact tax ID hit.
    """
    matches: list[dict[str, Any]] = []

    for entity in watchlist:
        tax_hit = False
        if tax_id and entity.tax_id and tax_id.strip() == entity.tax_id.strip():
            tax_hit = True

        name_score = compute_string_similarity(name, entity.entity_name)

        if tax_hit or name_score >= threshold:
            final_score = 1.0 if tax_hit else name_score
            reasons = []
            if tax_hit:
                reasons.append("Exact Tax ID match confirmed")
            if name_score >= threshold:
                reasons.append(f"Name fuzzy similarity score: {name_score:.2f}")

            matches.append(
                {
                    "watchlist_id": entity.id,
                    "matched_name": entity.entity_name,
                    "list_name": entity.list_name,
                    "match_score": final_score,
                    "reasons": "; ".join(reasons),
                    "entity_type": entity.entity_type,
                }
            )

    matches.sort(key=lambda m: m["match_score"], reverse=True)
    return matches
