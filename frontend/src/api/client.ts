import {
  AgentRunDetail,
  AuditEvent,
  ChatQuoteResponse,
  ClaimDetail,
  ClaimSummary,
  ComplaintItem,
  ComplianceAlertItem,
  ComplianceExplanationResponse,
  CustomerChatResponse,
  EndorsementDraftResult,
  EvalSummary,
  ExecutiveKPIs,
  FinancialKpiResponse,
  GeneralLedgerTransactionItem,
  InvoiceItem,
  LedgerCheckResponse,
  OperationalMetrics,
  PolicyDetail,
  PolicyListItem,
  QuoteDetail,
  QuoteSummary,
  ReinsuranceTreatyItem,
  RenewalAssessmentResponse,
  RenewalCaseItem,
  SIUAssessmentResponse,
  SIUCaseItem,
  UnderwritingCaseDetail,
  UnderwritingCaseSummary,
  UserProfile,
} from '../types';

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000';

class ApiClient {
  private token: string | null = null;

  constructor() {
    this.token = localStorage.getItem('insurai_token');
  }

  setToken(token: string | null): void {
    this.token = token;
    if (token) {
      localStorage.setItem('insurai_token', token);
    } else {
      localStorage.removeItem('insurai_token');
    }
  }

  getToken(): string | null {
    return this.token;
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...(options.headers as Record<string, string>),
    };

    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`;
    }

    const response = await fetch(`${API_BASE}${endpoint}`, {
      ...options,
      headers,
    });

    if (!response.ok) {
      let errorDetail = response.statusText;
      try {
        const errJson = await response.json();
        errorDetail = errJson.detail || errJson.title || JSON.stringify(errJson);
      } catch {
        // Fallback to text
      }
      throw new Error(errorDetail);
    }

    return response.json();
  }

  // System
  async checkHealth(): Promise<{ status: string; app: string }> {
    return this.request<{ status: string; app: string }>('/health');
  }

  // Auth
  async login(username: string, password: string): Promise<{ access_token: string; user_id: string; username: string; role: string; full_name: string }> {
    const res = await this.request<{ access_token: string; user_id: string; username: string; role: string; full_name: string }>('/api/v1/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    });
    this.setToken(res.access_token);
    return res;
  }

  async getMe(): Promise<UserProfile> {
    return this.request<UserProfile>('/api/v1/auth/me');
  }

  logout(): void {
    this.setToken(null);
  }

  // Policies
  async listPolicies(search?: string, status?: string): Promise<PolicyListItem[]> {
    const params = new URLSearchParams();
    if (search) params.append('search', search);
    if (status) params.append('status', status);
    const query = params.toString() ? `?${params.toString()}` : '';
    return this.request<PolicyListItem[]>(`/api/v1/policies${query}`);
  }

  async getPolicy(policyNumber: string): Promise<PolicyDetail> {
    return this.request<PolicyDetail>(`/api/v1/policies/${policyNumber}`);
  }

  // Claims
  async listClaims(search?: string, status?: string): Promise<ClaimSummary[]> {
    const params = new URLSearchParams();
    if (search) params.append('search', search);
    if (status) params.append('status', status);
    const query = params.toString() ? `?${params.toString()}` : '';
    return this.request<ClaimSummary[]>(`/api/v1/claims${query}`);
  }

  async getClaim(claimNumber: string): Promise<ClaimDetail> {
    return this.request<ClaimDetail>(`/api/v1/claims/${claimNumber}`);
  }

  async submitFNOL(data: {
    policy_number: string;
    incident_date: string;
    notification_date?: string;
    claimed_amount: number;
    incident_description: string;
    product_code?: string;
    documents?: Array<{ type: string; file_name: string; content: string }>;
  }): Promise<ClaimSummary> {
    return this.request<ClaimSummary>('/api/v1/claims/fnol', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async triageClaim(claimNumber: string): Promise<ClaimDetail> {
    return this.request<ClaimDetail>(`/api/v1/claims/${claimNumber}/triage`, {
      method: 'POST',
    });
  }

  async recordDecision(claimNumber: string, decision: {
    decision: 'approve' | 'reject';
    approved_payout?: number;
    notes: string;
    override_reason?: string;
  }): Promise<ClaimDetail> {
    return this.request<ClaimDetail>(`/api/v1/claims/${claimNumber}/decision`, {
      method: 'POST',
      body: JSON.stringify(decision),
    });
  }

  async settleClaim(claimNumber: string): Promise<ClaimDetail> {
    return this.request<ClaimDetail>(`/api/v1/claims/${claimNumber}/settle`, {
      method: 'POST',
    });
  }

  // Traces
  async getTrace(runOrCorrelationId: string): Promise<AgentRunDetail> {
    return this.request<AgentRunDetail>(`/api/v1/traces/${runOrCorrelationId}`);
  }

  // Audit
  async listAuditEvents(): Promise<AuditEvent[]> {
    return this.request<AuditEvent[]>('/api/v1/audit?limit=50');
  }

  // Metrics
  async getMetrics(): Promise<OperationalMetrics> {
    return this.request<OperationalMetrics>('/api/v1/metrics');
  }

  async getExecutiveKPIs(): Promise<ExecutiveKPIs> {
    return this.request<ExecutiveKPIs>('/api/v1/metrics/executive-kpis');
  }

  async getEvalReports(): Promise<EvalSummary> {
    return this.request<EvalSummary>('/api/v1/metrics/evals/latest');
  }

  // Sales & Quotation
  async createQuote(data: {
    product_code: string;
    vehicle_value: number;
    vehicle_age: number;
    driver_age: number;
    prior_claims_count?: number;
    deductible?: number;
  }): Promise<QuoteDetail> {
    return this.request<QuoteDetail>('/api/v1/sales/quotes', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async listQuotes(status?: string): Promise<QuoteSummary[]> {
    const url = status ? `/api/v1/sales/quotes?status=${status}` : '/api/v1/sales/quotes';
    return this.request<QuoteSummary[]>(url);
  }

  async getQuote(quoteNumber: string): Promise<QuoteDetail> {
    return this.request<QuoteDetail>(`/api/v1/sales/quotes/${quoteNumber}`);
  }

  async acceptQuote(quoteNumber: string): Promise<QuoteDetail> {
    return this.request<QuoteDetail>(`/api/v1/sales/quotes/${quoteNumber}/accept`, {
      method: 'POST',
    });
  }

  async chatWithQuoteAssistant(message: string): Promise<ChatQuoteResponse> {
    return this.request<ChatQuoteResponse>('/api/v1/sales/chat', {
      method: 'POST',
      body: JSON.stringify({ message }),
    });
  }

  // Underwriting & Referral
  async listUnderwritingCases(status?: string): Promise<UnderwritingCaseSummary[]> {
    const url = status ? `/api/v1/underwriting/cases?status=${status}` : '/api/v1/underwriting/cases';
    return this.request<UnderwritingCaseSummary[]>(url);
  }

  async getUnderwritingCase(caseId: string): Promise<UnderwritingCaseDetail> {
    return this.request<UnderwritingCaseDetail>(`/api/v1/underwriting/cases/${caseId}`);
  }

  async assessUnderwritingCase(caseId: string): Promise<UnderwritingCaseDetail> {
    return this.request<UnderwritingCaseDetail>(`/api/v1/underwriting/cases/${caseId}/assess`, {
      method: 'POST',
    });
  }

  async recordUnderwriterDecision(caseId: string, decision: {
    decision: string;
    conditions?: string[];
    override_reason?: string;
    notes?: string;
  }): Promise<UnderwritingCaseDetail> {
    return this.request<UnderwritingCaseDetail>(`/api/v1/underwriting/cases/${caseId}/decision`, {
      method: 'POST',
      body: JSON.stringify(decision),
    });
  }

  // Finance & Ledger
  async getInvoices(policyNumber?: string, status?: string): Promise<InvoiceItem[]> {
    let url = '/api/v1/finance/invoices';
    const params = new URLSearchParams();
    if (policyNumber) params.append('policy_number', policyNumber);
    if (status) params.append('status', status);
    if (params.toString()) url += `?${params.toString()}`;
    return this.request<InvoiceItem[]>(url);
  }

  async payInvoice(invoiceId: string, amount: number, paymentMethod = 'bank_transfer'): Promise<{
    status: string;
    message: string;
    payment_reference: string;
    amount: number;
  }> {
    return this.request(`/api/v1/finance/invoices/${invoiceId}/pay`, {
      method: 'POST',
      body: JSON.stringify({ amount, payment_method: paymentMethod }),
    });
  }

  async getLedgerTransactions(limit = 50): Promise<GeneralLedgerTransactionItem[]> {
    return this.request<GeneralLedgerTransactionItem[]>(`/api/v1/finance/ledger?limit=${limit}`);
  }

  async getLedgerCheck(): Promise<LedgerCheckResponse> {
    return this.request<LedgerCheckResponse>('/api/v1/finance/ledger/check');
  }

  async getFinancialKpis(): Promise<FinancialKpiResponse> {
    return this.request<FinancialKpiResponse>('/api/v1/finance/kpis');
  }

  async runDunningJob(asOfDate?: string): Promise<{
    status: string;
    notices_generated_count: number;
    notices: Array<Record<string, unknown>>;
  }> {
    return this.request('/api/v1/finance/dunning/run', {
      method: 'POST',
      body: JSON.stringify({ as_of_date: asOfDate }),
    });
  }

  // Renewal Review & A7 Advisor
  async getRenewalCases(status?: string, breachedOnly = false): Promise<RenewalCaseItem[]> {
    let url = '/api/v1/renewals/cases';
    const params = new URLSearchParams();
    if (status) params.append('status_filter', status);
    if (breachedOnly) params.append('breached_only', 'true');
    if (params.toString()) url += `?${params.toString()}`;
    return this.request<RenewalCaseItem[]>(url);
  }

  async runRenewalScan(daysAhead = 60, asOfDate?: string): Promise<{
    status: string;
    scanned_cases_count: number;
    breaches_flagged_count: number;
  }> {
    return this.request('/api/v1/renewals/scan', {
      method: 'POST',
      body: JSON.stringify({ days_ahead: daysAhead, as_of_date: asOfDate }),
    });
  }

  async assessPolicyRenewal(policyNumber: string, message = '', asOfDate?: string): Promise<RenewalAssessmentResponse> {
    return this.request<RenewalAssessmentResponse>(`/api/v1/renewals/assess/${policyNumber}`, {
      method: 'POST',
      body: JSON.stringify({ message, as_of_date: asOfDate }),
    });
  }

  async generateRenewalOffer(caseId: string): Promise<{ status: string; message: string }> {
    return this.request(`/api/v1/renewals/cases/${caseId}/offer`, {
      method: 'POST',
    });
  }

  async issueNonRenewalNotice(caseId: string, rationale: string, underwriterName = 'Senior Underwriter'): Promise<{ status: string; message: string }> {
    return this.request(`/api/v1/renewals/cases/${caseId}/non-renewal`, {
      method: 'POST',
      body: JSON.stringify({ rationale, underwriter_name: underwriterName }),
    });
  }

  async acceptRenewalOffer(caseId: string): Promise<{
    status: string;
    renewed_policy_number: string;
    premium: number;
  }> {
    return this.request(`/api/v1/renewals/cases/${caseId}/accept`, {
      method: 'POST',
    });
  }

  // Reinsurance
  async getReinsuranceTreaties(): Promise<ReinsuranceTreatyItem[]> {
    return this.request<ReinsuranceTreatyItem[]>('/api/v1/reinsurance/treaties');
  }

  // Phase 11: Fraud & SIU (Agent A5)
  async getSIUCases(statusFilter?: string): Promise<SIUCaseItem[]> {
    const url = statusFilter ? `/api/v1/siu/cases?status_filter=${statusFilter}` : '/api/v1/siu/cases';
    return this.request<SIUCaseItem[]>(url);
  }

  async getSIUCase(caseId: string): Promise<SIUCaseItem & { signals: any[] }> {
    return this.request(`/api/v1/siu/cases/${caseId}`);
  }

  async assessClaimSIU(claimNumber: string, investigatorNotes = ''): Promise<SIUAssessmentResponse> {
    return this.request<SIUAssessmentResponse>(`/api/v1/siu/assess/${claimNumber}`, {
      method: 'POST',
      body: JSON.stringify({ investigator_notes: investigatorNotes }),
    });
  }

  async updateSIUCase(caseId: string, status: string, findingsSummary: string, investigatorId = 'investigator'): Promise<{ status: string }> {
    return this.request(`/api/v1/siu/cases/${caseId}/update`, {
      method: 'POST',
      body: JSON.stringify({ status, findings_summary: findingsSummary, investigator_id: investigatorId }),
    });
  }

  // Phase 11: Compliance & Watchlist (Agent A8)
  async getComplianceAlerts(statusFilter?: string): Promise<ComplianceAlertItem[]> {
    const url = statusFilter ? `/api/v1/compliance/alerts?status_filter=${statusFilter}` : '/api/v1/compliance/alerts';
    return this.request<ComplianceAlertItem[]>(url);
  }

  async screenPartyCompliance(partyId: string, partyName: string, taxId?: string): Promise<{
    status: string;
    matches_count: number;
    alerts: Array<{ id: string; alert_number: string; matched_name: string; score: number }>;
  }> {
    return this.request('/api/v1/compliance/screen', {
      method: 'POST',
      body: JSON.stringify({ party_id: partyId, party_name: partyName, tax_id: taxId }),
    });
  }

  async assessComplianceAlert(alertId: string): Promise<ComplianceExplanationResponse> {
    return this.request<ComplianceExplanationResponse>(`/api/v1/compliance/assess/${alertId}`, {
      method: 'POST',
    });
  }

  async adjudicateComplianceAlert(alertId: string, decision: string, decisionNotes: string): Promise<{
    status: string;
    alert_status: string;
    alert_number: string;
    decided_by: string;
  }> {
    return this.request(`/api/v1/compliance/alerts/${alertId}/adjudicate`, {
      method: 'POST',
      body: JSON.stringify({ decision, decision_notes: decisionNotes }),
    });
  }

  // Phase 11: Customer Service & Servicing (Agents A6 & A3)
  async sendCustomerChat(message: string, isAuthenticated = false, verifiedPartyId?: string, customerIdentifier = 'guest_user'): Promise<CustomerChatResponse> {
    return this.request<CustomerChatResponse>('/api/v1/service/chat', {
      method: 'POST',
      body: JSON.stringify({
        message,
        is_authenticated: isAuthenticated,
        verified_party_id: verifiedPartyId,
        customer_identifier: customerIdentifier,
      }),
    });
  }

  async getComplaints(statusFilter?: string): Promise<ComplaintItem[]> {
    const url = statusFilter ? `/api/v1/service/complaints?status_filter=${statusFilter}` : '/api/v1/service/complaints';
    return this.request<ComplaintItem[]>(url);
  }

  async submitComplaint(partyId: string, subject: string, description: string, policyId?: string, claimId?: string): Promise<{
    status: string;
    complaint_number: string;
    initial_response_deadline: string;
    final_resolution_deadline: string;
    sla_breached: boolean;
  }> {
    return this.request('/api/v1/service/complaints', {
      method: 'POST',
      body: JSON.stringify({ party_id: partyId, subject, description, policy_id: policyId, claim_id: claimId }),
    });
  }

  async proposeEndorsement(policyNumber: string, endorsementType: string, effectiveDate: string, changes: Record<string, any>): Promise<EndorsementDraftResult> {
    return this.request<EndorsementDraftResult>('/api/v1/service/endorsements/propose', {
      method: 'POST',
      body: JSON.stringify({
        policy_number: policyNumber,
        endorsement_type: endorsementType,
        effective_date: effectiveDate,
        changes,
      }),
    });
  }
}

export const api = new ApiClient();

