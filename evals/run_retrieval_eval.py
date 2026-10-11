"""Evaluation runner for Knowledge Service (RAG) retrieval benchmarks."""

import json
import sys
from pathlib import Path

# Add project root and backend to sys.path
repo_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo_root))
sys.path.insert(0, str(repo_root / "backend"))

from app.db import Base  # noqa: E402
from app.modules.platform.knowledge.service import knowledge_service  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402


def run_retrieval_evaluation() -> dict[str, float]:
    queries_file = repo_root / "data" / "synthetic" / "retrieval_queries.json"
    if not queries_file.exists():
        print(f"Queries file not found: {queries_file}")
        sys.exit(1)

    with open(queries_file, encoding="utf-8") as f:
        queries = json.load(f)

    # Setup isolated SQLite in-memory knowledge store with schema translation
    engine = create_engine(
        "sqlite:///:memory:",
        execution_options={"schema_translate_map": {"platform": None}},
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    session = session_factory()

    # Ingest catalog
    ingested = knowledge_service.ingest_all_catalogs(session)
    print(f"Ingested {ingested} wording clauses into knowledge store.")

    total = len(queries)
    hits_at_1 = 0
    hits_at_3 = 0
    hits_at_5 = 0
    reciprocal_ranks: list[float] = []
    misses: list[dict[str, str]] = []

    incident_date = "2026-05-01"

    for q in queries:
        citations = knowledge_service.search_policy_wording(
            session=session,
            query=q["query"],
            product_code="MOTOR_OD",
            incident_date=incident_date,
            top_k=5,
        )

        retrieved_ids = [c.clause_id for c in citations]
        expected_id = q["expected_clause_id"]

        # Calculate rank
        if expected_id in retrieved_ids:
            rank = retrieved_ids.index(expected_id) + 1
            reciprocal_ranks.append(1.0 / rank)

            if rank == 1:
                hits_at_1 += 1
            if rank <= 3:
                hits_at_3 += 1
            if rank <= 5:
                hits_at_5 += 1
        else:
            reciprocal_ranks.append(0.0)
            misses.append(
                {
                    "id": q["id"],
                    "query": q["query"],
                    "expected": expected_id,
                    "retrieved": ", ".join(retrieved_ids[:3]),
                }
            )

    metrics = {
        "total_queries": total,
        "recall_at_1": (hits_at_1 / total) * 100.0,
        "recall_at_3": (hits_at_3 / total) * 100.0,
        "recall_at_5": (hits_at_5 / total) * 100.0,
        "mrr": (sum(reciprocal_ranks) / total),
    }

    # Generate Markdown report
    reports_dir = repo_root / "evals" / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    report_file = reports_dir / "retrieval_dev_report.md"

    report_content = f"""# Policy Wording Retrieval Evaluation Report (Dev Set)

## Retrieval Performance Metrics

| Metric | Result | Target Benchmark |
|---|---|---|
| Total Labeled Queries | {metrics["total_queries"]} | 40 |
| Recall@1 | {metrics["recall_at_1"]:.1f}% | $\\ge 70.0$% |
| Recall@3 | {metrics["recall_at_3"]:.1f}% | $\\ge 85.0$% |
| Recall@5 | {metrics["recall_at_5"]:.1f}% | $\\ge 90.0$% |
| Mean Reciprocal Rank (MRR) | {metrics["mrr"]:.3f} | $\\ge 0.800$ |

## Methodology
- **Embedding:** Deterministic token-aware embedding vector space (768 dimensions).
- **Chunking:** Clause-level granularity (`title + "\\n" + text`).
- **Date In Force Filtering:** Pre-filtered by `effective_from <= {incident_date} <= effective_to`.
- **Ranking:** Cosine similarity over pre-filtered candidate clauses.
"""
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(report_content)

    print(f"\nReport written to: {report_file}")
    for k, v in metrics.items():
        print(f"  {k:20s}: {v:.3f}" if isinstance(v, float) else f"  {k:20s}: {v}")

    session.close()
    return metrics


if __name__ == "__main__":
    run_retrieval_evaluation()
