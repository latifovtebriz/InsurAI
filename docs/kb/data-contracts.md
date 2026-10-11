# Data Contracts

## 1. ClaimRecommendation Schema

```json
{
  "recommendation": "approve | reject | needs_human_review",
  "confidence": 0.95,
  "summary": "Vehicle damaged during parking collision; covered under Clause A.1.",
  "reasons": [
    {
      "type": "coverage",
      "statement": "Accidental damage while parked is covered under Clause A.1.",
      "evidence": {
        "clause_ids": ["MOTOR_OD:A.1"],
        "tool_calls": ["call_search_policy_wording"]
      }
    }
  ],
  "payout": {
    "claimed": 1200.0,
    "deductible": 200.0,
    "payable": 1000.0,
    "currency": "AZN"
  },
  "risk_flags": [],
  "missing_information": [],
  "next_actions_for_human": [
    "Verify surveyor repair invoice before final payment release."
  ]
}
```

## 2. ExtractedClaim Schema

```json
{
  "policy_number": "POL-2026-M-00123",
  "incident_date": "2026-09-15T14:30:00Z",
  "incident_type": "collision",
  "location": "Baku, Heydar Aliyev Ave",
  "description_summary": "Front bumper damaged after minor collision with barrier.",
  "claimed_amount": 1200.0,
  "stated_driver": "Rashad Aliyev",
  "alcohol_involved": false,
  "driver_licensed": true,
  "police_report_filed": true,
  "confidence_score": 0.96
}
```
