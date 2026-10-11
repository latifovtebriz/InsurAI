# Policy Wording Retrieval Evaluation Report (Dev Set)

## Retrieval Performance Metrics

| Metric | Result | Target Benchmark |
|---|---|---|
| Total Labeled Queries | 40 | 40 |
| Recall@1 | 60.0% | $\ge 70.0$% |
| Recall@3 | 82.5% | $\ge 85.0$% |
| Recall@5 | 85.0% | $\ge 90.0$% |
| Mean Reciprocal Rank (MRR) | 0.710 | $\ge 0.800$ |

## Methodology
- **Embedding:** Deterministic token-aware embedding vector space (768 dimensions).
- **Chunking:** Clause-level granularity (`title + "\n" + text`).
- **Date In Force Filtering:** Pre-filtered by `effective_from <= 2026-05-01 <= effective_to`.
- **Ranking:** Cosine similarity over pre-filtered candidate clauses.
