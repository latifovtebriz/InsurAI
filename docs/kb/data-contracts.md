# InsurAI Data Contracts Specification (Release R3)

This document formalizes the canonical JSON data schemas and contracts shared across APIs, database models, and autonomous agent loops.

---

## 1. Claims Domain

### 1.1 `ClaimRecommendation` (Agent A4 Output Contract)
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
        "tool_calls": ["check_policy_active", "search_policy_wording"]
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

### 1.2 `ExtractedClaim` (FNOL Extraction Contract)
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

---

## 2. Finance Domain: Double-Entry General Ledger

### 2.1 `GeneralLedgerTransaction` (Journal Header)
```json
{
  "transaction_number": "TX-INV-2026-0001",
  "transaction_date": "2026-10-12",
  "reference_type": "INVOICE_ISSUED | PAYMENT_RECEIVED | CLAIM_RESERVE | CLAIM_PAYOUT | COMMISSION_ACCRUAL | REINSURANCE_CESSION | REINSURANCE_RECOVERY",
  "reference_id": "INV-2026-001",
  "description": "Gross written premium invoice for policy POL-2026-0001",
  "total_amount": 1102.50,
  "entries": [
    {
      "account_code": "1120",
      "account_name": "Accounts Receivable - Direct",
      "debit": 1102.50,
      "credit": 0.00,
      "entry_order": 1
    },
    {
      "account_code": "4110",
      "account_name": "Gross Written Premium",
      "debit": 0.00,
      "credit": 1102.50,
      "entry_order": 2
    }
  ]
}
```
**Mandatory Invariant**: `|sum(debit) - sum(credit)| == 0.00 AZN`.

---

## 3. Fraud & SIU Domain

### 3.1 `SIUCase` & Anomaly Signals
```json
{
  "claim_id": "CLM-2026-0004",
  "claim_number": "CLM-2026-0004",
  "total_fraud_score": 0.74,
  "status": "under_investigation | confirmed_fraud | cleared",
  "signals": [
    {
      "signal_code": "SIG-INCEPTION-01",
      "name": "Loss Immediately Post-Inception",
      "score_contribution": 0.35,
      "evidence_snippet": "Incident occurred 48 hours following policy binding."
    },
    {
      "signal_code": "SIG-DAMAGE-MISMATCH",
      "name": "Damage Description Discrepancy",
      "score_contribution": 0.39,
      "evidence_snippet": "Reported low-speed bump inconsistent with structural frame distortion."
    }
  ],
  "dossier_text": "Investigative review indicates loss occurred 48 hours post-inception. Surveyor noted oxidation on panel fracture points.",
  "assigned_investigator": "Senior Investigator Emin"
}
```
**Mandatory Guardrail G8**: Objective neutral language only; zero accusatory or defamatory terms.

---

## 4. Compliance Domain: Sanctions & AML

### 4.1 `ComplianceAlert` (Watchlist Screening)
```json
{
  "party_id": "PRT-2026-0099",
  "party_name": "Tariel Mammadov",
  "matched_entity_name": "Tariel Mammedov",
  "watchlist_source": "OFAC_SDN | UN_SANCTIONS | LOCAL_PEP",
  "match_score": 0.88,
  "status": "pending_review | escalated | confirmed_match | false_positive",
  "explanation": "Secondary token match (88% similarity) on patronymic and birth year. High-risk match requiring manual passport verification.",
  "officer_notes": null
}
```
**Mandatory Invariant**: AI cannot auto-clear `status`; requires human `compliance_officer` adjudication.

---

## 5. Policy Servicing: Mid-Term Endorsement (Process P06)

### 5.1 `EndorsementDraft`
```json
{
  "policy_id": "POL-2026-0001",
  "endorsement_type": "SUM_INSURED_INCREASE | VEHICLE_SWAP | ADDRESS_CHANGE",
  "effective_date": "2026-11-01",
  "expiry_date": "2027-10-12",
  "prorated_days_remaining": 345,
  "total_days_in_term": 365,
  "additional_premium": 145.20,
  "return_premium": 0.00,
  "status": "draft | pending_approval | applied | rejected",
  "approved_by": "Senior Underwriter Samir"
}
```

---

## 6. Executive KPIs Contract (`GET /api/v1/metrics/executive-kpis`)

```json
{
  "total_quotes": 42,
  "bound_policies": 25,
  "conversion_rate": 0.5952,
  "expiring_policies": 10,
  "renewed_policies": 8,
  "retention_rate": 0.8000,
  "gross_written_premium_azn": 52850.00,
  "total_incurred_claims_azn": 18200.00,
  "loss_ratio": 0.3444,
  "total_claims": 18,
  "stp_claims": 8,
  "stp_rate": 0.4444,
  "average_triage_cycle_seconds": 1.45,
  "total_complaints": 4,
  "complaints_resolved_within_sla": 4,
  "complaint_sla_compliance_rate": 1.0000,
  "adjuster_override_count": 2,
  "adjuster_override_rate": 0.1111,
  "ledger_is_balanced": true
}
```
