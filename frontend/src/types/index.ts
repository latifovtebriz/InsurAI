/**
 * InsurAI Core TypeScript Type Definitions
 */

export interface UserProfile {
  user_id: string;
  username: string;
  full_name?: string;
  role: 'admin' | 'adjuster' | 'underwriter' | 'customer' | string;
  permissions: string[];
}

export interface PolicyListItem {
  id: string;
  policy_number: string;
  product_code: string;
  status: string;
  holder_name?: string | null;
  start_date: string;
  end_date: string;
  sum_insured: number;
  total_premium: number;
  paid_premium: number;
}

export interface PolicyDetail {
  id: string;
  policy_number: string;
  party_id: string;
  asset_id: string;
  product_code: string;
  product_version_id: string;
  status: string;
  start_date: string;
  end_date: string;
  sum_insured: number;
  deductible: number;
  total_premium: number;
  paid_premium: number;
  payment_schedule: Array<{
    due_date: string;
    amount: number;
    status: string;
  }>;
  certificate_hash?: string | null;
  holder_info?: {
    party_id: string;
    full_name: string;
    party_type: string;
    tax_id: string;
    email: string;
    phone: string;
  } | null;
}

export interface ClaimSummary {
  id: string;
  claim_number: string;
  policy_number: string;
  product_code: string;
  incident_date: string;
  status: string;
  claimed_amount: number;
  approved_payout?: number | null;
  autonomy_level: string;
  recommendation?: 'approve' | 'reject' | 'needs_human_review' | null;
  confidence_score?: number | null;
  risk_flags: string[];
  created_at: string;
}

export interface ClauseCitation {
  clause_id: string;
  section: string;
  title: string;
  relevance: number;
}

export interface PayoutBreakdown {
  claimed_amount: number;
  covered_loss: number;
  deductible: number;
  payable: number;
  is_total_loss: boolean;
  salvage_deduction: number;
  calculation_rule: string;
}

export interface TriageRecommendation {
  recommendation: 'approve' | 'reject' | 'needs_human_review';
  confidence: number;
  payout?: PayoutBreakdown;
  risk_flags: string[];
  missing_information: string[];
  clause_citations: ClauseCitation[];
  reasoning: string;
}

export interface ClaimDocument {
  id: string;
  document_type: string;
  file_name: string;
  content_preview: string;
  content_text: string;
  created_at: string;
}

export interface ClaimReserve {
  id: string;
  amount: number;
  reserve_type: string;
  reason: string;
  created_at: string;
}

export interface ClaimDetail {
  id: string;
  claim_number: string;
  policy_number: string;
  product_code: string;
  incident_date: string;
  notification_date: string;
  status: string;
  claimed_amount: number;
  estimated_reserve: number;
  approved_payout?: number | null;
  deductible_applied?: number | null;
  autonomy_level: string;
  incident_description: string;
  triage_recommendation?: TriageRecommendation | null;
  adjuster_decision?: {
    decision: string;
    adjuster_id: string;
    decided_at: string;
    notes: string;
    override_reason?: string | null;
    approved_payout: number;
  } | null;
  documents: ClaimDocument[];
  reserves: ClaimReserve[];
  created_at: string;
}

export interface AgentStep {
  id: string;
  step_index: number;
  step_kind: 'llm_call' | 'tool_call' | 'guardrail';
  tool_name?: string | null;
  tool_input?: Record<string, any> | null;
  tool_output?: Record<string, any> | null;
  tokens_used: number;
  latency_ms: number;
  error_message?: string | null;
  created_at: string;
}

export interface AgentRunDetail {
  id: string;
  agent_id: string;
  correlation_id: string;
  status: string;
  input_payload: Record<string, any>;
  final_output?: Record<string, any> | null;
  step_count: number;
  total_tokens: number;
  total_cost_usd: number;
  duration_seconds: number;
  created_at: string;
  completed_at?: string | null;
  steps: AgentStep[];
}

export interface AuditEvent {
  id: string;
  user_id?: string | null;
  action: string;
  entity_type: string;
  entity_id: string;
  before_state?: Record<string, any> | null;
  after_state?: Record<string, any> | null;
  correlation_id?: string | null;
  timestamp: string;
}

export interface OperationalMetrics {
  total_policies: number;
  active_policies: number;
  total_claims: number;
  claims_by_status: Record<string, number>;
  auto_approval_count: number;
  auto_approval_rate_percent: number;
  total_reserve_azn: number;
  total_paid_out_azn: number;
}

export interface EvalSummary {
  extraction_eval?: Record<string, any> | null;
  retrieval_eval?: Record<string, any> | null;
  claims_triage_dev_eval?: Record<string, any> | null;
  claims_triage_test_eval?: Record<string, any> | null;
}

// Sales & Quotation
export interface QuoteSummary {
  id: string;
  quote_number: string;
  product_code: string;
  status: string;
  sum_insured: number;
  total_premium: number;
  valid_until: string;
  underwriting_case_id?: string | null;
  created_at: string;
}

export interface QuoteDetail {
  id: string;
  quote_number: string;
  product_code: string;
  status: string;
  sum_insured: number;
  deductible: number;
  total_premium: number;
  rating_inputs: Record<string, any>;
  breakdown: Record<string, any>;
  installment_options: Array<{
    plan: string;
    installments_count: number;
    schedule: Array<{ seq: number; due_date: string; amount: number }>;
  }>;
  valid_until: string;
  underwriting_case_id?: string | null;
  created_at: string;
}

export interface ChatQuoteResponse {
  status: string;
  message: string;
  missing_fields: string[];
  extracted?: Record<string, any> | null;
  quote_result?: Record<string, any> | null;
  risk_flag?: string | null;
}

// Underwriting & Referral
export interface UnderwritingCaseSummary {
  id: string;
  case_number: string;
  quote_id?: string | null;
  product_code: string;
  sum_insured: number;
  proposed_premium: number;
  status: string;
  authority_tier_required: string;
  rule_hits_count: number;
  risk_score: number;
  created_at: string;
}

export interface UnderwritingCaseDetail {
  id: string;
  case_number: string;
  quote_id?: string | null;
  policy_id?: string | null;
  product_code: string;
  sum_insured: number;
  proposed_premium: number;
  status: string;
  authority_tier_required: string;
  rule_hits: Array<{
    rule_code: string;
    rule_name: string;
    severity: string;
    description: string;
    recommended_action: string;
  }>;
  risk_score: number;
  copilot_assessment?: {
    recommended_action: string;
    confidence: number;
    cited_guidelines: string[];
    proposed_conditions: string[];
    risk_summary: string;
  } | null;
  underwriter_decision?: {
    decision: string;
    conditions: string[];
    override_reason?: string | null;
    decided_by: string;
    decided_at: string;
  } | null;
  notes?: string | null;
  created_at: string;
}

export interface InvoiceItem {
  id: string;
  invoice_number: string;
  policy_id: string;
  policy_number: string;
  party_id: string;
  installment_number: number;
  amount: number;
  due_date: string;
  status: string;
  dunning_level: number;
  paid_at?: string | null;
  created_at: string;
}

export interface GeneralLedgerTransactionItem {
  id: string;
  transaction_number: string;
  transaction_date: string;
  reference_type: string;
  reference_id: string;
  description: string;
  total_amount: number;
  entries: Array<{
    account_code: string;
    debit: number;
    credit: number;
  }>;
  created_at: string;
}

export interface LedgerCheckResponse {
  is_balanced: boolean;
  difference: number;
  total_debits: number;
  total_credits: number;
  status: string;
}

export interface FinancialKpiResponse {
  gross_written_premium: number;
  incurred_losses: number;
  commissions_expense: number;
  loss_ratio_pct: number;
  expense_ratio_pct: number;
  combined_ratio_pct: number;
  cash_balance: number;
  outstanding_receivables: number;
  claims_payable_reserve: number;
  ledger_balanced: boolean;
  ledger_difference: number;
}

export interface RenewalCaseItem {
  id: string;
  policy_id: string;
  policy_number: string;
  party_id: string;
  product_code: string;
  current_end_date: string;
  days_to_expiry: number;
  claims_count: number;
  total_claims_incurred: number;
  current_premium: number;
  proposed_premium: number;
  recommendation: string;
  status: string;
  notice_deadline: string;
  notice_sent: boolean;
  statutory_deadline_breached: boolean;
  advisor_rationale?: string | null;
  underwriter_approved: boolean;
  approved_by?: string | null;
}

export interface RenewalAssessmentResponse {
  policy_number: string;
  current_end_date: string;
  days_to_expiry: number;
  claims_count: number;
  total_claims_incurred: number;
  current_premium: number;
  proposed_premium: number;
  recommendation: string;
  notice_deadline: string;
  statutory_deadline_breached: boolean;
  autonomy_level: string;
  draft_notice_text: string;
  underwriter_signoff_required: boolean;
}

export interface ReinsuranceTreatyItem {
  id: string;
  treaty_code: string;
  treaty_name: string;
  treaty_type: string;
  product_code: string;
  reinsurer_name: string;
  retention_share_pct: number;
  ceded_share_pct: number;
  retention_amount: number;
  treaty_limit: number;
  start_date: string;
  end_date: string;
  is_active: boolean;
}

// Phase 11: Fraud & SIU (Agent A5)
export interface SIUCaseItem {
  id: string;
  case_number: string;
  claim_id: string;
  claim_number: string;
  policy_number: string;
  risk_score: number;
  status: string;
  investigator_id?: string | null;
  findings_summary?: string | null;
  created_at: string;
}

export interface FraudSignalItem {
  code: string;
  name: string;
  weight: number;
  description: string;
}

export interface SIUAssessmentResponse {
  claim_number: string;
  risk_score: number;
  signals_detected: Array<{ signal_code: string; name: string; weight: number; description: string }>;
  timeline_summary: string;
  cross_claim_notes: string;
  neutral_findings_summary: string;
  g8_neutral_language_verified: boolean;
  recommended_siu_action: string;
}

// Phase 11: Compliance & Watchlist (Agent A8)
export interface ComplianceAlertItem {
  id: string;
  alert_number: string;
  party_id: string;
  party_name: string;
  matched_entity_id: string;
  matched_entity_name: string;
  match_score: number;
  match_reasons: string;
  status: string;
  assigned_officer_id?: string | null;
  officer_decision_notes?: string | null;
  decided_at?: string | null;
  created_at: string;
}

export interface ComplianceExplanationResponse {
  alert_number: string;
  party_name: string;
  matched_entity_name: string;
  list_name: string;
  match_score: number;
  analysis_text: string;
  recommendation: string;
  auto_cleared: boolean;
  human_signoff_required: boolean;
  draft_sar_report?: string | null;
}

// Phase 11: Customer Service & Servicing (Agents A6 & A3)
export interface CustomerChatResponse {
  reply_text: string;
  is_authenticated: boolean;
  verified_party_id?: string | null;
  data_accessed: boolean;
  action_taken?: string | null;
}

export interface ComplaintItem {
  id: string;
  complaint_number: string;
  party_id: string;
  subject: string;
  status: string;
  initial_response_deadline: string;
  final_resolution_deadline: string;
  sla_breached: boolean;
  created_at: string;
}

export interface EndorsementDraftResult {
  policy_number: string;
  endorsement_type: string;
  effective_date: string;
  prorata_adjustment_azn: number;
  proposed_changes: Record<string, any>;
  draft_status: string;
  autonomy_level: string;
  requires_underwriter_approval: boolean;
  summary_explanation: string;
}


