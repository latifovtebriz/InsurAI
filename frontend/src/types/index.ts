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
