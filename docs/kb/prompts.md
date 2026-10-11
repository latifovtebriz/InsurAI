# Prompt Catalog

| Agent / Service | `PROMPT_VERSION` | Purpose | Notes & Revisions |
|---|---|---|---|
| Extraction (FNOL) | `claims-fnol-extract-v1` | Extracts structured fields from free-text incident descriptions | Delimited untrusted text blocks, null for unknown values |
| Agent A4 | `claims-triage-a4-v1` | Evaluates claim eligibility, checks coverage, and recommends triage outcome | Mandatory tools required; cites clause IDs; no raw calculations |
| Agent A1 | `sales-quote-a1-v1` | Helps prospects clarify quote options | Strictly references engine calculation numbers |
| Agent A2 | `uw-copilot-a2-v1` | Summarizes risk referral reasons for underwriter | Objective risk summary |
| Agent A5 | `fraud-analysis-a5-v1` | Outlines anomaly indicators for SIU | Neutral, non-accusatory language |
| Agent A6 | `service-chat-a6-v1` | Answers policyholder inquiries | Requires verified identity before revealing policy facts |
| Agent A7 | `renewal-advisor-a7-v1`| Prepares renewal summaries | Checks 30-day notice requirement |
| Agent A8 | `compliance-a8-v1` | Explains watchlist fuzzy matches | Strictly barred from auto-clearing matches |
