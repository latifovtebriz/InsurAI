import React, { useEffect, useState } from 'react';
import { api } from '../api/client';
import { SIUAssessmentResponse, SIUCaseItem } from '../types';

export const SIUScreen: React.FC = () => {
  const [cases, setCases] = useState<SIUCaseItem[]>([]);
  const [selectedCase, setSelectedCase] = useState<SIUCaseItem | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [assessClaimNumber, setAssessClaimNumber] = useState<string>('CLM-20261012-001');
  const [investigatorNotes, setInvestigatorNotes] = useState<string>('Unwitnessed single-vehicle incident occurring at night.');
  const [assessment, setAssessment] = useState<SIUAssessmentResponse | null>(null);
  const [assessing, setAssessing] = useState<boolean>(false);
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [updateStatus, setUpdateStatus] = useState<string>('under_investigation');
  const [findingsNotes, setFindingsNotes] = useState<string>('');
  const [actionMsg, setActionMsg] = useState<string | null>(null);

  const loadCases = async () => {
    setLoading(true);
    try {
      const data = await api.getSIUCases(statusFilter || undefined);
      setCases(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadCases();
  }, [statusFilter]);

  const handleAssessClaim = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!assessClaimNumber.trim()) return;
    setAssessing(true);
    setActionMsg(null);
    try {
      const res = await api.assessClaimSIU(assessClaimNumber.trim(), investigatorNotes);
      setAssessment(res);
      setActionMsg(`Agent A5 assessed claim ${res.claim_number} with Risk Score: ${res.risk_score}`);
      await loadCases();
    } catch (err: any) {
      setActionMsg(`Assessment failed: ${err.message || 'Unknown error'}`);
    } finally {
      setAssessing(false);
    }
  };

  const handleUpdateCase = async (caseId: string) => {
    if (!findingsNotes.trim()) return;
    try {
      await api.updateSIUCase(caseId, updateStatus, findingsNotes);
      setActionMsg(`SIU Case updated to ${updateStatus}.`);
      setFindingsNotes('');
      await loadCases();
    } catch (err: any) {
      setActionMsg(`Failed to update case: ${err.message || 'Unknown error'}`);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between pb-4 border-b border-gray-200">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <span>🛡️ Special Investigation Unit (SIU)</span>
            <span className="text-xs bg-purple-100 text-purple-800 px-2 py-0.5 rounded-full font-semibold">
              Agent A5 Active
            </span>
          </h1>
          <p className="text-sm text-gray-500 mt-1">
            Autonomous fraud risk triage, transparent signal evaluation, and Guardrail G8 neutral dossier synthesis.
          </p>
        </div>
        <div className="mt-4 md:mt-0 flex gap-2">
          <button
            onClick={loadCases}
            className="px-3 py-1.5 text-sm bg-white border border-gray-300 rounded hover:bg-gray-50 text-gray-700"
          >
            Refresh Queue
          </button>
        </div>
      </div>

      {actionMsg && (
        <div className="p-3 bg-blue-50 border border-blue-200 rounded text-sm text-blue-800 flex justify-between items-center">
          <span>{actionMsg}</span>
          <button onClick={() => setActionMsg(null)} className="text-blue-500 hover:text-blue-700 font-bold">&times;</button>
        </div>
      )}

      {/* Grid: Triage Assessor + Case Queue */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Agent A5 Assessor */}
        <div className="bg-white p-5 rounded-lg border border-gray-200 shadow-sm space-y-4">
          <h2 className="text-lg font-bold text-gray-900 border-b pb-2 flex items-center justify-between">
            <span>Agent A5 Claim Assessor</span>
            <span className="text-xs font-normal text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded">G8 & G9 Verified</span>
          </h2>
          <form onSubmit={handleAssessClaim} className="space-y-3">
            <div>
              <label className="block text-xs font-semibold text-gray-600 mb-1">Claim Number</label>
              <input
                type="text"
                value={assessClaimNumber}
                onChange={(e) => setAssessClaimNumber(e.target.value)}
                placeholder="e.g. CLM-20261012-001"
                className="w-full text-sm border rounded px-3 py-2 focus:ring-1 focus:ring-blue-500"
                required
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-gray-600 mb-1">Adjuster Preliminary Notes</label>
              <textarea
                value={investigatorNotes}
                onChange={(e) => setInvestigatorNotes(e.target.value)}
                rows={3}
                placeholder="Enter scene or interview observations..."
                className="w-full text-sm border rounded px-3 py-2 focus:ring-1 focus:ring-blue-500"
              />
            </div>
            <button
              type="submit"
              disabled={assessing}
              className="w-full py-2 bg-indigo-600 hover:bg-indigo-700 text-white font-medium text-sm rounded transition disabled:opacity-50"
            >
              {assessing ? 'Evaluating Fraud Signals...' : 'Assess Claim with Agent A5'}
            </button>
          </form>

          {/* Assessment Output Preview */}
          {assessment && (
            <div className="mt-4 pt-4 border-t space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-gray-500">Fraud Score</span>
                <span
                  className={`text-sm font-bold px-2.5 py-0.5 rounded-full ${
                    assessment.risk_score >= 70
                      ? 'bg-red-100 text-red-800'
                      : assessment.risk_score >= 40
                      ? 'bg-amber-100 text-amber-800'
                      : 'bg-emerald-100 text-emerald-800'
                  }`}
                >
                  {assessment.risk_score} / 100
                </span>
              </div>

              <div>
                <span className="text-xs font-semibold text-gray-500 block mb-1">Triggered Fraud Signals</span>
                {assessment.signals_detected.length === 0 ? (
                  <p className="text-xs text-gray-500">No anomalous signals detected.</p>
                ) : (
                  <div className="space-y-1.5">
                    {assessment.signals_detected.map((sig, idx) => (
                      <div key={idx} className="bg-gray-50 p-2 rounded text-xs border border-gray-100">
                        <div className="flex justify-between font-semibold text-gray-800">
                          <span>{sig.signal_code}: {sig.name}</span>
                          <span className="text-red-600">+{sig.weight} pts</span>
                        </div>
                        <p className="text-gray-500 mt-0.5">{sig.description}</p>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              <div className="bg-blue-50/50 p-2.5 rounded border border-blue-100 text-xs">
                <div className="flex items-center justify-between mb-1">
                  <span className="font-semibold text-blue-900">G8 Neutral Findings Dossier</span>
                  <span className="text-[10px] bg-emerald-100 text-emerald-800 px-1.5 py-0.2 rounded font-bold">100% NEUTRAL</span>
                </div>
                <p className="text-gray-700 leading-relaxed">{assessment.neutral_findings_summary}</p>
              </div>

              <div className="text-xs font-medium text-gray-700">
                <span className="text-gray-500">Recommended Action: </span>
                <span className="font-bold text-indigo-700">{assessment.recommended_siu_action}</span>
              </div>
            </div>
          )}
        </div>

        {/* Right 2 Columns: SIU Investigation Cases Queue */}
        <div className="lg:col-span-2 space-y-4">
          <div className="bg-white p-5 rounded-lg border border-gray-200 shadow-sm">
            <div className="flex items-center justify-between pb-3 border-b mb-4">
              <h2 className="text-lg font-bold text-gray-900">SIU Priority Referral Cases</h2>
              <div className="flex items-center gap-2">
                <label className="text-xs text-gray-500 font-semibold">Filter:</label>
                <select
                  value={statusFilter}
                  onChange={(e) => setStatusFilter(e.target.value)}
                  className="text-xs border rounded px-2 py-1 bg-white"
                >
                  <option value="">All Statuses</option>
                  <option value="open">Open</option>
                  <option value="under_investigation">Under Investigation</option>
                  <option value="cleared">Cleared</option>
                  <option value="referred_legal">Referred to Legal</option>
                </select>
              </div>
            </div>

            {loading ? (
              <div className="text-center py-8 text-gray-400 text-sm">Loading SIU queue...</div>
            ) : cases.length === 0 ? (
              <div className="text-center py-8 text-gray-400 text-sm">
                No active SIU investigation cases found matching filter.
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs border-collapse">
                  <thead>
                    <tr className="bg-gray-50 text-gray-500 border-b">
                      <th className="py-2.5 px-3">Case Number</th>
                      <th className="py-2.5 px-3">Claim #</th>
                      <th className="py-2.5 px-3">Policy #</th>
                      <th className="py-2.5 px-3 text-center">Score</th>
                      <th className="py-2.5 px-3">Status</th>
                      <th className="py-2.5 px-3">Date</th>
                      <th className="py-2.5 px-3 text-right">Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {cases.map((c) => (
                      <tr
                        key={c.id}
                        className={`hover:bg-gray-50 transition cursor-pointer ${selectedCase?.id === c.id ? 'bg-indigo-50/50' : ''}`}
                        onClick={() => setSelectedCase(c)}
                      >
                        <td className="py-2.5 px-3 font-semibold text-gray-900">{c.case_number}</td>
                        <td className="py-2.5 px-3 text-indigo-600 font-medium">{c.claim_number}</td>
                        <td className="py-2.5 px-3 text-gray-600">{c.policy_number}</td>
                        <td className="py-2.5 px-3 text-center font-bold">
                          <span
                            className={`px-2 py-0.5 rounded-full ${
                              c.risk_score >= 70
                                ? 'bg-red-100 text-red-700'
                                : 'bg-amber-100 text-amber-700'
                            }`}
                          >
                            {c.risk_score}
                          </span>
                        </td>
                        <td className="py-2.5 px-3">
                          <span className="capitalize px-2 py-0.5 bg-gray-100 text-gray-800 rounded font-medium">
                            {c.status.replace('_', ' ')}
                          </span>
                        </td>
                        <td className="py-2.5 px-3 text-gray-400">{c.created_at.slice(0, 10)}</td>
                        <td className="py-2.5 px-3 text-right">
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              setSelectedCase(c);
                            }}
                            className="text-xs text-indigo-600 hover:text-indigo-900 font-semibold"
                          >
                            Review &rarr;
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* Detailed Selected Case Panel */}
          {selectedCase && (
            <div className="bg-white p-5 rounded-lg border border-indigo-200 shadow-sm space-y-4">
              <div className="flex items-center justify-between border-b pb-2">
                <div>
                  <h3 className="font-bold text-gray-900">
                    Investigator Adjudication: {selectedCase.case_number}
                  </h3>
                  <p className="text-xs text-gray-500">Related Claim: {selectedCase.claim_number} | Policy: {selectedCase.policy_number}</p>
                </div>
                <span className="text-xs font-bold px-2 py-1 bg-red-100 text-red-800 rounded">
                  Score: {selectedCase.risk_score} / 100
                </span>
              </div>

              {selectedCase.findings_summary && (
                <div className="p-3 bg-gray-50 rounded text-xs text-gray-700">
                  <span className="font-semibold block text-gray-900 mb-1">Previous Findings Dossier:</span>
                  {selectedCase.findings_summary}
                </div>
              )}

              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-2">
                <div>
                  <label className="block text-xs font-semibold text-gray-600 mb-1">Update Status</label>
                  <select
                    value={updateStatus}
                    onChange={(e) => setUpdateStatus(e.target.value)}
                    className="w-full text-xs border rounded px-3 py-2 bg-white"
                  >
                    <option value="under_investigation">Under Investigation</option>
                    <option value="cleared">Cleared (No Fraud Indicators)</option>
                    <option value="referred_legal">Referred to Legal / Ombudsman</option>
                    <option value="closed">Closed</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-semibold text-gray-600 mb-1">Investigator Justification</label>
                  <input
                    type="text"
                    value={findingsNotes}
                    onChange={(e) => setFindingsNotes(e.target.value)}
                    placeholder="Enter objective factual conclusion..."
                    className="w-full text-xs border rounded px-3 py-2"
                  />
                </div>
              </div>

              <div className="flex justify-end pt-2">
                <button
                  onClick={() => handleUpdateCase(selectedCase.id)}
                  className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white font-medium text-xs rounded transition"
                >
                  Save Investigator Adjudication
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
