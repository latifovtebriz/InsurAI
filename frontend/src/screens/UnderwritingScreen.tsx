import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import { UnderwritingCaseSummary, UnderwritingCaseDetail } from '../types';
import { Badge } from '../components/Badge';

export const UnderwritingScreen: React.FC = () => {
  const [cases, setCases] = useState<UnderwritingCaseSummary[]>([]);
  const [selectedCase, setSelectedCase] = useState<UnderwritingCaseDetail | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [loading, setLoading] = useState(false);
  const [, setDetailLoading] = useState(false);
  const [copilotLoading, setCopilotLoading] = useState(false);

  // Decision Form State
  const [decision, setDecision] = useState<'approved_standard' | 'approved_with_conditions' | 'declined'>('approved_with_conditions');
  const [conditionsText, setConditionsText] = useState('Mandatory GPS tracker installation within 7 days.');
  const [overrideReason, setOverrideReason] = useState('');
  const [underwriterNotes, setUnderwriterNotes] = useState('');
  const [submittingDecision, setSubmittingDecision] = useState(false);

  useEffect(() => {
    loadCases();
  }, [statusFilter]);

  const loadCases = async () => {
    try {
      setLoading(true);
      const filter = statusFilter === 'all' ? undefined : statusFilter;
      const res = await api.listUnderwritingCases(filter);
      setCases(res);
      if (res.length > 0 && !selectedCase) {
        loadCaseDetail(res[0].id);
      }
    } catch (err) {
      console.error('Failed to load underwriting cases:', err);
    } finally {
      setLoading(false);
    }
  };

  const loadCaseDetail = async (caseId: string) => {
    try {
      setDetailLoading(true);
      const res = await api.getUnderwritingCase(caseId);
      setSelectedCase(res);
    } catch (err) {
      console.error('Failed to load case detail:', err);
    } finally {
      setDetailLoading(false);
    }
  };

  const handleRunCopilot = async () => {
    if (!selectedCase) return;
    try {
      setCopilotLoading(true);
      const updated = await api.assessUnderwritingCase(selectedCase.id);
      setSelectedCase(updated);
      loadCases();
    } catch (err: any) {
      alert(`Copilot assessment failed: ${err.message}`);
    } finally {
      setCopilotLoading(false);
    }
  };

  const handleSubmitDecision = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedCase) return;

    if (decision === 'declined' && !overrideReason.trim() && !underwriterNotes.trim()) {
      alert('Mandatory Guardrail G3: Declining a risk requires a written rationale.');
      return;
    }

    try {
      setSubmittingDecision(true);
      const conditionsList =
        decision === 'approved_with_conditions'
          ? conditionsText.split('\n').filter((c) => c.trim().length > 0)
          : [];

      const updated = await api.recordUnderwriterDecision(selectedCase.id, {
        decision,
        conditions: conditionsList,
        override_reason: overrideReason || undefined,
        notes: underwriterNotes || undefined,
      });

      setSelectedCase(updated);
      alert(`Decision recorded successfully! Status: ${updated.status}`);
      loadCases();
    } catch (err: any) {
      alert(`Decision failed: ${err.message}`);
    } finally {
      setSubmittingDecision(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 bg-white p-6 rounded-xl border border-gray-200 shadow-sm">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Underwriting Referral Queue (P03)</h1>
          <p className="text-sm text-gray-500 mt-1">
            Deterministic rule hits, authority limit enforcement, and A2 Underwriting Copilot guideline analysis.
          </p>
        </div>

        {/* Filter Pills */}
        <div className="flex space-x-2 bg-gray-100 p-1 rounded-lg text-xs">
          {['all', 'pending_review', 'approved_with_conditions', 'declined'].map((st) => (
            <button
              key={st}
              onClick={() => setStatusFilter(st)}
              className={`px-3 py-1.5 font-medium rounded-md capitalize transition ${
                statusFilter === st
                  ? 'bg-white text-indigo-700 shadow-sm'
                  : 'text-gray-600 hover:text-gray-900'
              }`}
            >
              {st.replace('_', ' ')}
            </button>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Cases List */}
        <div className="lg:col-span-4 bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden flex flex-col h-[700px]">
          <div className="p-4 border-b border-gray-100 bg-gray-50 flex justify-between items-center">
            <h2 className="font-bold text-gray-800 text-sm">Referral Cases ({cases.length})</h2>
            <button onClick={loadCases} className="text-xs text-indigo-600 hover:text-indigo-800 font-medium">
              Refresh
            </button>
          </div>

          <div className="flex-1 overflow-y-auto divide-y divide-gray-100">
            {cases.map((c) => (
              <div
                key={c.id}
                onClick={() => loadCaseDetail(c.id)}
                className={`p-4 cursor-pointer transition ${
                  selectedCase?.id === c.id ? 'bg-indigo-50/70 border-l-4 border-indigo-600' : 'hover:bg-gray-50'
                }`}
              >
                <div className="flex justify-between items-start mb-1">
                  <span className="font-mono text-xs font-bold text-gray-900">{c.case_number}</span>
                  <Badge type="status" value={c.status} />
                </div>
                <div className="text-xs text-gray-600 flex justify-between mt-2">
                  <span>Product: {c.product_code}</span>
                  <span className="font-medium text-gray-900">{c.sum_insured.toLocaleString()} AZN</span>
                </div>
                <div className="flex justify-between items-center text-xs text-gray-400 mt-2">
                  <span className="bg-amber-100 text-amber-800 px-2 py-0.5 rounded font-mono text-[10px]">
                    Auth: {c.authority_tier_required}
                  </span>
                  <span>{c.rule_hits_count} Rule Hits</span>
                </div>
              </div>
            ))}
            {cases.length === 0 && !loading && (
              <div className="p-8 text-center text-gray-400 text-xs">
                No underwriting cases matching this filter.
              </div>
            )}
          </div>
        </div>

        {/* Case Dossier & Copilot */}
        <div className="lg:col-span-8 space-y-6">
          {selectedCase ? (
            <>
              {/* Case Summary Card */}
              <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm space-y-4">
                <div className="flex justify-between items-start">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-xs bg-gray-100 text-gray-700 px-2.5 py-1 rounded">
                        {selectedCase.case_number}
                      </span>
                      {selectedCase.quote_id && (
                        <span className="text-xs text-gray-500">Ref: {selectedCase.quote_id}</span>
                      )}
                    </div>
                    <h2 className="text-xl font-bold text-gray-900 mt-2">
                      Referral Assessment: {selectedCase.product_code} ({selectedCase.sum_insured.toLocaleString()} AZN)
                    </h2>
                  </div>
                  <Badge type="status" value={selectedCase.status} />
                </div>

                <div className="grid grid-cols-3 gap-4 pt-3 border-t text-xs">
                  <div>
                    <span className="text-gray-500">Proposed Premium:</span>
                    <div className="text-sm font-bold text-gray-900 mt-0.5">
                      {selectedCase.proposed_premium.toLocaleString('en-US', { minimumFractionDigits: 2 })} AZN
                    </div>
                  </div>
                  <div>
                    <span className="text-gray-500">Required Authority:</span>
                    <div className="text-sm font-bold text-amber-600 mt-0.5 capitalize">
                      {selectedCase.authority_tier_required} Underwriter
                    </div>
                  </div>
                  <div>
                    <span className="text-gray-500">Risk Score:</span>
                    <div className="text-sm font-bold text-rose-600 mt-0.5">
                      {(selectedCase.risk_score * 100).toFixed(0)} / 100
                    </div>
                  </div>
                </div>

                {/* Deterministic Rule Hits */}
                <div className="mt-4">
                  <h3 className="text-xs font-bold uppercase tracking-wider text-gray-600 mb-2">
                    Deterministic Rule Hits ({selectedCase.rule_hits.length})
                  </h3>
                  <div className="space-y-2">
                    {selectedCase.rule_hits.map((h, idx) => (
                      <div key={idx} className="p-3 bg-amber-50/70 border border-amber-200 rounded-lg text-xs">
                        <div className="flex justify-between font-bold text-amber-900 mb-1">
                          <span>{h.rule_code}: {h.rule_name}</span>
                          <span className="uppercase text-[10px] bg-amber-200/80 px-2 py-0.5 rounded">{h.severity}</span>
                        </div>
                        <p className="text-amber-800">{h.description}</p>
                        <div className="mt-1.5 font-medium text-amber-950">Action: {h.recommended_action}</div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              {/* A2 Underwriting Copilot Assessment */}
              <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm space-y-4">
                <div className="flex justify-between items-center">
                  <div className="flex items-center gap-2">
                    <span className="text-base font-bold text-gray-900">A2 Underwriting Copilot</span>
                    <span className="text-xs bg-indigo-100 text-indigo-700 px-2 py-0.5 rounded font-medium">L2 Human-in-the-Loop</span>
                  </div>
                  <button
                    onClick={handleRunCopilot}
                    disabled={copilotLoading}
                    className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-medium rounded-lg shadow-sm transition disabled:opacity-50"
                  >
                    {copilotLoading ? 'Analyzing Guidelines...' : 'Run Copilot Assessment'}
                  </button>
                </div>

                {selectedCase.copilot_assessment ? (
                  <div className="space-y-4 pt-3 border-t">
                    <div className="p-4 bg-indigo-50/50 border border-indigo-100 rounded-lg">
                      <div className="flex justify-between items-center mb-2">
                        <span className="text-xs font-bold text-indigo-900">
                          Recommended Action: <span className="uppercase">{selectedCase.copilot_assessment.recommended_action}</span>
                        </span>
                        <span className="text-xs font-medium text-indigo-700">
                          Confidence: {(selectedCase.copilot_assessment.confidence * 100).toFixed(0)}%
                        </span>
                      </div>
                      <p className="text-xs text-indigo-950">{selectedCase.copilot_assessment.risk_summary}</p>
                    </div>

                    {/* Cited Guidelines */}
                    <div>
                      <h4 className="text-xs font-bold uppercase tracking-wider text-gray-600 mb-2">
                        Grounding Citations (Guardrail G1)
                      </h4>
                      <ul className="space-y-1 text-xs text-gray-700">
                        {selectedCase.copilot_assessment.cited_guidelines.map((g, idx) => (
                          <li key={idx} className="flex items-start gap-1.5 bg-gray-50 p-2 rounded border border-gray-200">
                            <span className="text-indigo-600">📖</span>
                            <span>{g}</span>
                          </li>
                        ))}
                      </ul>
                    </div>

                    {/* Proposed Conditions */}
                    {selectedCase.copilot_assessment.proposed_conditions.length > 0 && (
                      <div>
                        <h4 className="text-xs font-bold uppercase tracking-wider text-gray-600 mb-2">
                          Proposed Conditions & Endorsements
                        </h4>
                        <ul className="list-disc pl-5 text-xs text-gray-700 space-y-1">
                          {selectedCase.copilot_assessment.proposed_conditions.map((cond, idx) => (
                            <li key={idx}>{cond}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="p-6 bg-gray-50 rounded-lg text-center text-xs text-gray-500">
                    Click "Run Copilot Assessment" to invoke Agent A2 for guideline RAG and draft conditions.
                  </div>
                )}
              </div>

              {/* Underwriter Adjudication Panel */}
              <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm">
                <h3 className="text-base font-bold text-gray-900 mb-4">Underwriter Action Panel</h3>

                {selectedCase.underwriter_decision ? (
                  <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-lg text-xs space-y-2">
                    <div className="flex justify-between items-center font-bold text-emerald-900">
                      <span>Adjudicated: {selectedCase.underwriter_decision.decision}</span>
                      <span>By: {selectedCase.underwriter_decision.decided_by}</span>
                    </div>
                    {selectedCase.underwriter_decision.conditions?.length > 0 && (
                      <div>
                        <span className="font-semibold text-emerald-950">Enforced Conditions:</span>
                        <ul className="list-disc pl-4 text-emerald-900 mt-1">
                          {selectedCase.underwriter_decision.conditions.map((c: string, idx: number) => (
                            <li key={idx}>{c}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                    {selectedCase.notes && <p className="text-emerald-800">Notes: {selectedCase.notes}</p>}
                  </div>
                ) : (
                  <form onSubmit={handleSubmitDecision} className="space-y-4">
                    <div className="grid grid-cols-3 gap-3">
                      {[
                        { val: 'approved_standard', label: 'Approve Standard', color: 'border-emerald-500 text-emerald-700' },
                        { val: 'approved_with_conditions', label: 'Approve Conditional', color: 'border-indigo-500 text-indigo-700' },
                        { val: 'declined', label: 'Decline Risk', color: 'border-rose-500 text-rose-700' },
                      ].map((item) => (
                        <button
                          key={item.val}
                          type="button"
                          onClick={() => setDecision(item.val as any)}
                          className={`p-3 text-xs font-bold rounded-lg border text-center transition ${
                            decision === item.val
                              ? `bg-gray-100 ${item.color} ring-2 ring-indigo-500/20`
                              : 'border-gray-200 text-gray-600 hover:bg-gray-50'
                          }`}
                        >
                          {item.label}
                        </button>
                      ))}
                    </div>

                    {decision === 'approved_with_conditions' && (
                      <div>
                        <label className="block text-xs font-semibold uppercase text-gray-500 mb-1">
                          Special Endorsement Conditions (one per line)
                        </label>
                        <textarea
                          rows={2}
                          value={conditionsText}
                          onChange={(e) => setConditionsText(e.target.value)}
                          className="w-full px-3 py-2 border rounded-lg text-xs"
                          placeholder="E.g., Mandatory GPS tracker warranty..."
                        />
                      </div>
                    )}

                    {decision === 'declined' && (
                      <div>
                        <label className="block text-xs font-semibold uppercase text-rose-600 mb-1">
                          Mandatory Written Rationale for Rejection (Guardrail G3)
                        </label>
                        <textarea
                          rows={2}
                          value={overrideReason}
                          onChange={(e) => setOverrideReason(e.target.value)}
                          className="w-full px-3 py-2 border border-rose-300 rounded-lg text-xs"
                          placeholder="State statutory and appetite reason for declining this risk..."
                          required
                        />
                      </div>
                    )}

                    <div>
                      <label className="block text-xs font-semibold uppercase text-gray-500 mb-1">
                        Underwriter Notes (Internal Audit)
                      </label>
                      <input
                        type="text"
                        value={underwriterNotes}
                        onChange={(e) => setUnderwriterNotes(e.target.value)}
                        className="w-full px-3 py-2 border rounded-lg text-xs"
                        placeholder="Optional internal justification notes..."
                      />
                    </div>

                    <button
                      type="submit"
                      disabled={submittingDecision}
                      className="w-full py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white font-medium text-xs rounded-lg shadow-sm transition disabled:opacity-50"
                    >
                      {submittingDecision ? 'Submitting Adjudication...' : 'Confirm Underwriting Decision'}
                    </button>
                  </form>
                )}
              </div>
            </>
          ) : (
            <div className="bg-white p-12 rounded-xl border border-dashed border-gray-300 text-center text-gray-500">
              <p className="font-medium">No Case Selected</p>
              <p className="text-xs text-gray-400 mt-1">Select an underwriting referral case from the list on the left.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
