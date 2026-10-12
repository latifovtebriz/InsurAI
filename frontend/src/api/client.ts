import {
  AgentRunDetail,
  AuditEvent,
  ChatQuoteResponse,
  ClaimDetail,
  ClaimSummary,
  EvalSummary,
  OperationalMetrics,
  PolicyDetail,
  PolicyListItem,
  QuoteDetail,
  QuoteSummary,
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
}

export const api = new ApiClient();

