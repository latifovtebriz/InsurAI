import React, { useEffect, useState } from 'react';
import { api } from '../api/client';
import { RenewalAssessmentResponse, RenewalCaseItem } from '../types';

export const RenewalScreen: React.FC = () => {
  const [cases, setCases] = useState<RenewalCaseItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [selectedCase, setSelectedCase] = useState<RenewalCaseItem | null>(null);
  const [assessment, setAssessment] = useState<RenewalAssessmentResponse | null>(null);
  const [assessing, setAssessing] = useState<boolean>(false);
  const [actionMsg, setActionMsg] = useState<string | null>(null);

  const loadCases = async () => {
    setLoading(true);
    try {
      const data = await api.getRenewalCases();
      setCases(data);
      if (data.length > 0 && !selectedCase) {
        setSelectedCase(data[0]);
      }
    } catch (err: unknown) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadCases();
  }, []);

  const handleRunScan = async () => {
    try {
      const res = await api.runRenewalScan(60);
      setActionMsg(`T-60 scan complete: ${res.scanned_cases_count} cases evaluated. ${res.breaches_flagged_count} statutory breaches flagged.`);
      await loadCases();
    } catch (err: unknown) {
      const error = err as Error;
      setActionMsg(`Scan failed: ${error.message}`);
    }
  };

  const handleRunAdvisor = async (policyNumber: string) => {
    setAssessing(true);
    try {
      const res = await api.assessPolicyRenewal(policyNumber, 'Review expiring terms');
      setAssessment(res);
    } catch (err: unknown) {
      const error = err as Error;
      setActionMsg(`A7 Advisor failed: ${error.message}`);
    } finally {
      setAssessing(false);
    }
  };

  const handleIssueOffer = async (caseId: string) => {
    try {
      const res = await api.generateRenewalOffer(caseId);
      setActionMsg(res.message);
      await loadCases();
    } catch (err: unknown) {
      const error = err as Error;
      setActionMsg(`Offer error: ${error.message}`);
    }
  };

  const handleIssueNonRenewal = async (caseId: string) => {
    try {
      const res = await api.issueNonRenewalNotice(caseId, 'Risk profile and loss frequency exceed acceptable underwriting tolerance.');
      setActionMsg(res.message);
      await loadCases();
    } catch (err: unknown) {
      const error = err as Error;
      setActionMsg(`Non-renewal notice error: ${error.message}`);
    }
  };

  const handleAcceptRenewal = async (caseId: string) => {
    try {
      const res = await api.acceptRenewalOffer(caseId);
      setActionMsg(`Renewal accepted! New contract issued: ${res.renewed_policy_number} (${res.premium} AZN).`);
      await loadCases();
    } catch (err: unknown) {
      const error = err as Error;
      setActionMsg(`Acceptance error: ${error.message}`);
    }
  };

  const breachesCount = cases.filter((c) => c.statutory_deadline_breached).length;

  return (
    <div className="space-y-6">
      {/* Header & Scanning */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Policy Renewal Review & Agent A7</h1>
          <p className="text-slate-500 text-sm mt-1">
            T-60 automated review, claim loss re-rating, statutory 30-day notice deadline enforcement, and A7 Renewal Advisor.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={handleRunScan}
            className="px-4 py-2 text-sm font-semibold bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg transition shadow-sm"
          >
            Run T-60 Scanner Job
          </button>
        </div>
      </div>

      {/* Critical Statutory Notice Warning Banner */}
      {breachesCount > 0 && (
        <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-900 flex items-start gap-3 shadow-sm">
          <span className="text-xl">⚠️</span>
          <div>
            <h3 className="font-bold text-sm">Critical Statutory Notice Alert: {breachesCount} Case(s) Breached</h3>
            <p className="text-xs text-rose-700 mt-0.5">
              Statutory 30-day non-renewal notice deadline has passed for adverse policies expiring soon without timely notice. Immediate underwriter intervention required.
            </p>
          </div>
        </div>
      )}

      {actionMsg && (
        <div className="p-4 rounded-lg bg-sky-50 text-sky-800 border border-sky-200 text-sm flex justify-between items-center">
          <span>{actionMsg}</span>
          <button onClick={() => setActionMsg(null)} className="text-sky-600 font-bold ml-4">✕</button>
        </div>
      )}

      {/* Main Grid: Cases List & A7 Advisor Panel */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Cases List */}
        <div className="lg:col-span-2 space-y-4">
          <div className="bg-white rounded-xl border border-slate-200 overflow-hidden shadow-sm">
            <div className="p-4 bg-slate-50 border-b border-slate-200 flex justify-between items-center">
              <span className="font-semibold text-sm text-slate-800">Expiring Policies Queue ({cases.length})</span>
              <span className="text-xs text-slate-500">Sorted by expiry urgency</span>
            </div>
            <div className="divide-y divide-slate-100 max-h-[600px] overflow-y-auto">
              {loading ? (
                <div className="p-8 text-center text-slate-400">Scanning expiring policies...</div>
              ) : cases.length === 0 ? (
                <div className="p-8 text-center text-slate-400">No expiring policies found within T-60 days.</div>
              ) : (
                cases.map((c) => (
                  <div
                    key={c.id}
                    onClick={() => {
                      setSelectedCase(c);
                      setAssessment(null);
                    }}
                    className={`p-4 cursor-pointer transition hover:bg-slate-50 flex items-center justify-between ${
                      selectedCase?.id === c.id ? 'bg-indigo-50/60 border-l-4 border-indigo-600' : ''
                    }`}
                  >
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-sm font-bold text-slate-900">{c.policy_number}</span>
                        <span className={`px-2 py-0.5 rounded text-xs font-semibold ${
                          c.recommendation === 'STANDARD_RENEWAL'
                            ? 'bg-emerald-100 text-emerald-800'
                            : c.recommendation === 'SURCHARGED_RENEWAL'
                            ? 'bg-amber-100 text-amber-800'
                            : 'bg-rose-100 text-rose-800'
                        }`}>
                          {c.recommendation.replace('_', ' ')}
                        </span>
                        {c.statutory_deadline_breached && (
                          <span className="px-1.5 py-0.5 rounded text-xs font-bold bg-rose-600 text-white animate-pulse">
                            T-30 BREACH
                          </span>
                        )}
                      </div>
                      <p className="text-xs text-slate-500 mt-1">
                        Expires in <strong className="text-slate-800">{c.days_to_expiry} days</strong> ({c.current_end_date}) • {c.claims_count} claim(s) incurred
                      </p>
                    </div>
                    <div className="text-right">
                      <div className="text-xs text-slate-400 line-through">{c.current_premium} AZN</div>
                      <div className="text-sm font-bold text-slate-900">{c.proposed_premium} AZN</div>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>

        {/* Selected Case & A7 Advisor Inspection */}
        <div className="space-y-4">
          {selectedCase ? (
            <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm space-y-4">
              <div className="flex justify-between items-start">
                <div>
                  <span className="text-xs font-bold text-slate-400 uppercase">Renewal Case Dossier</span>
                  <h2 className="text-lg font-bold text-slate-900 font-mono mt-0.5">{selectedCase.policy_number}</h2>
                </div>
                <span className="text-xs px-2 py-1 bg-slate-100 font-semibold text-slate-700 rounded">
                  {selectedCase.status.toUpperCase()}
                </span>
              </div>

              <div className="bg-slate-50 p-3 rounded-lg text-xs space-y-2 text-slate-700">
                <div className="flex justify-between">
                  <span>Days to Expiration:</span>
                  <strong className="text-slate-900">{selectedCase.days_to_expiry} days</strong>
                </div>
                <div className="flex justify-between">
                  <span>Statutory Notice Deadline:</span>
                  <strong className="text-slate-900">{selectedCase.notice_deadline}</strong>
                </div>
                <div className="flex justify-between">
                  <span>Claims during term:</span>
                  <strong className="text-slate-900">{selectedCase.claims_count} ({selectedCase.total_claims_incurred} AZN)</strong>
                </div>
                <div className="flex justify-between">
                  <span>Proposed Re-rated Premium:</span>
                  <strong className="text-indigo-600 font-bold">{selectedCase.proposed_premium} AZN</strong>
                </div>
              </div>

              <button
                onClick={() => handleRunAdvisor(selectedCase.policy_number)}
                disabled={assessing}
                className="w-full py-2.5 px-4 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white font-medium text-sm transition shadow-sm disabled:opacity-50"
              >
                {assessing ? 'Running A7 Advisor...' : 'Run Agent A7 Advisor Assessment'}
              </button>

              {assessment && (
                <div className="mt-4 p-4 rounded-lg bg-indigo-50/50 border border-indigo-100 space-y-3 text-xs">
                  <div className="flex justify-between items-center">
                    <span className="font-bold text-indigo-900 uppercase">A7 Advisor Assessment</span>
                    <span className="px-2 py-0.5 bg-indigo-200 text-indigo-800 rounded font-bold">
                      Autonomy: {assessment.autonomy_level}
                    </span>
                  </div>
                  <p className="text-slate-600 leading-relaxed whitespace-pre-line bg-white p-3 rounded border border-slate-200 font-mono text-[11px]">
                    {assessment.draft_notice_text}
                  </p>
                  {assessment.underwriter_signoff_required && (
                    <div className="p-2 bg-amber-50 border border-amber-200 rounded text-amber-800 text-[11px]">
                      ⚠️ <strong>L2 Governance:</strong> Underwriter written rationale and sign-off required before sending notice.
                    </div>
                  )}
                </div>
              )}

              {/* Action Buttons */}
              <div className="pt-2 border-t border-slate-100 space-y-2">
                {selectedCase.recommendation === 'STANDARD_RENEWAL' && (
                  <button
                    onClick={() => handleIssueOffer(selectedCase.id)}
                    className="w-full py-2 px-3 text-xs font-semibold bg-emerald-600 hover:bg-emerald-700 text-white rounded transition"
                  >
                    Issue Renewal Offer Letter
                  </button>
                )}
                {selectedCase.recommendation === 'NON_RENEWAL' && (
                  <button
                    onClick={() => handleIssueNonRenewal(selectedCase.id)}
                    className="w-full py-2 px-3 text-xs font-semibold bg-rose-600 hover:bg-rose-700 text-white rounded transition"
                  >
                    Issue Statutory Non-Renewal Notice (L2 Sign-off)
                  </button>
                )}
                <button
                  onClick={() => handleAcceptRenewal(selectedCase.id)}
                  className="w-full py-2 px-3 text-xs font-semibold bg-slate-800 hover:bg-slate-900 text-white rounded transition"
                >
                  Accept & Issue Next Annual Contract
                </button>
              </div>
            </div>
          ) : (
            <div className="bg-white rounded-xl border border-slate-200 p-8 text-center text-slate-400 text-sm">
              Select an expiring policy to review terms and run Agent A7.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
