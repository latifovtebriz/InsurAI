import React, { useEffect, useState } from 'react';
import { api } from '../api/client';
import { ComplianceAlertItem, ComplianceExplanationResponse } from '../types';

export const ComplianceScreen: React.FC = () => {
  const [alerts, setAlerts] = useState<ComplianceAlertItem[]>([]);
  const [selectedAlert, setSelectedAlert] = useState<ComplianceAlertItem | null>(null);
  const [explanation, setExplanation] = useState<ComplianceExplanationResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [explaining, setExplaining] = useState<boolean>(false);
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [screenName, setScreenName] = useState<string>('Viktor Anatolyevich Bout');
  const [screenTaxId, setScreenTaxId] = useState<string>('RU-882910492');
  const [screening, setScreening] = useState<boolean>(false);
  const [decisionNotes, setDecisionNotes] = useState<string>('');
  const [actionMsg, setActionMsg] = useState<string | null>(null);

  const loadAlerts = async () => {
    setLoading(true);
    try {
      const data = await api.getComplianceAlerts(statusFilter || undefined);
      setAlerts(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAlerts();
  }, [statusFilter]);

  const handleScreenParty = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!screenName.trim()) return;
    setScreening(true);
    setActionMsg(null);
    try {
      const res = await api.screenPartyCompliance(`PARTY-SCR-${Date.now().toString().slice(-4)}`, screenName.trim(), screenTaxId.trim() || undefined);
      setActionMsg(`Screening completed: ${res.matches_count} watchlist match alert(s) generated.`);
      await loadAlerts();
    } catch (err: any) {
      setActionMsg(`Screening error: ${err.message || 'Unknown error'}`);
    } finally {
      setScreening(false);
    }
  };

  const handleSelectAlert = async (alert: ComplianceAlertItem) => {
    setSelectedAlert(alert);
    setExplaining(true);
    setExplanation(null);
    try {
      const res = await api.assessComplianceAlert(alert.id);
      setExplanation(res);
    } catch (err) {
      console.error(err);
    } finally {
      setExplaining(false);
    }
  };

  const handleAdjudicate = async (decision: 'confirmed_hit' | 'false_positive_cleared_by_officer') => {
    if (!selectedAlert) return;
    if (!decisionNotes.trim()) {
      alert('Please provide mandatory compliance officer justification notes.');
      return;
    }
    try {
      await api.adjudicateComplianceAlert(selectedAlert.id, decision, decisionNotes);
      setActionMsg(`Alert ${selectedAlert.alert_number} successfully adjudicated as: ${decision}.`);
      setDecisionNotes('');
      setSelectedAlert(null);
      setExplanation(null);
      await loadAlerts();
    } catch (err: any) {
      setActionMsg(`Adjudication failed: ${err.message || 'Unknown error'}`);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between pb-4 border-b border-gray-200">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <span>⚖️ AML & Sanctions Compliance Cockpit</span>
            <span className="text-xs bg-red-100 text-red-800 px-2.5 py-0.5 rounded-full font-semibold">
              Agent A8 Active
            </span>
          </h1>
          <p className="text-sm text-gray-500 mt-1">
            Real-time watchlist fuzzy matching against OFAC SDN, UN Sanctions, and PEP catalogs. AI is strictly barred from auto-clearing hits.
          </p>
        </div>
        <div className="mt-4 md:mt-0 flex gap-2">
          <button
            onClick={loadAlerts}
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

      {/* Grid: Party Screening Simulator + Alerts Queue */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Party Screening Form */}
        <div className="bg-white p-5 rounded-lg border border-gray-200 shadow-sm space-y-4">
          <h2 className="text-lg font-bold text-gray-900 border-b pb-2 flex items-center justify-between">
            <span>Screen Party against Sanctions</span>
            <span className="text-xs font-normal text-blue-700 bg-blue-50 px-2 py-0.5 rounded">Fuzzy Jaccard</span>
          </h2>
          <form onSubmit={handleScreenParty} className="space-y-3">
            <div>
              <label className="block text-xs font-semibold text-gray-600 mb-1">Entity / Person Legal Name</label>
              <input
                type="text"
                value={screenName}
                onChange={(e) => setScreenName(e.target.value)}
                placeholder="e.g. Viktor Bout or Caspian Petroleum"
                className="w-full text-sm border rounded px-3 py-2 focus:ring-1 focus:ring-blue-500"
                required
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-gray-600 mb-1">Tax ID / National FIN (Optional)</label>
              <input
                type="text"
                value={screenTaxId}
                onChange={(e) => setScreenTaxId(e.target.value)}
                placeholder="e.g. RU-882910492"
                className="w-full text-sm border rounded px-3 py-2 focus:ring-1 focus:ring-blue-500"
              />
            </div>
            <button
              type="submit"
              disabled={screening}
              className="w-full py-2 bg-red-600 hover:bg-red-700 text-white font-medium text-sm rounded transition disabled:opacity-50"
            >
              {screening ? 'Screening Catalogs...' : 'Run Sanctions & PEP Screen'}
            </button>
          </form>

          {/* Regulatory Invariant Callout */}
          <div className="p-3 bg-amber-50 border border-amber-200 rounded text-xs text-amber-900 space-y-1">
            <span className="font-bold flex items-center gap-1">
              <span>⚠️</span> Mandatory Non-Clearance Policy
            </span>
            <p className="text-[11px] leading-relaxed text-amber-800">
              Under statutory AML rules, Agent A8 is prohibited by architecture tests from ever clearing a watchlist match. All clearances require human Compliance Officer adjudication.
            </p>
          </div>
        </div>

        {/* Right 2 Columns: Alerts Queue */}
        <div className="lg:col-span-2 space-y-4">
          <div className="bg-white p-5 rounded-lg border border-gray-200 shadow-sm">
            <div className="flex items-center justify-between pb-3 border-b mb-4">
              <h2 className="text-lg font-bold text-gray-900">Compliance Watchlist Alerts Queue</h2>
              <div className="flex items-center gap-2">
                <label className="text-xs text-gray-500 font-semibold">Filter:</label>
                <select
                  value={statusFilter}
                  onChange={(e) => setStatusFilter(e.target.value)}
                  className="text-xs border rounded px-2 py-1 bg-white"
                >
                  <option value="">All Statuses</option>
                  <option value="open">Open</option>
                  <option value="under_review">Under Review</option>
                  <option value="confirmed_hit">Confirmed Hit</option>
                  <option value="false_positive_cleared_by_officer">Cleared False Positive</option>
                </select>
              </div>
            </div>

            {loading ? (
              <div className="text-center py-8 text-gray-400 text-sm">Loading compliance alerts...</div>
            ) : alerts.length === 0 ? (
              <div className="text-center py-8 text-gray-400 text-sm">
                No compliance alerts found matching filter.
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs border-collapse">
                  <thead>
                    <tr className="bg-gray-50 text-gray-500 border-b">
                      <th className="py-2.5 px-3">Alert Number</th>
                      <th className="py-2.5 px-3">Party Name</th>
                      <th className="py-2.5 px-3">Matched Watchlist Entity</th>
                      <th className="py-2.5 px-3 text-center">Score</th>
                      <th className="py-2.5 px-3">Status</th>
                      <th className="py-2.5 px-3 text-right">Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {alerts.map((a) => (
                      <tr
                        key={a.id}
                        className={`hover:bg-gray-50 transition cursor-pointer ${selectedAlert?.id === a.id ? 'bg-red-50/40' : ''}`}
                        onClick={() => handleSelectAlert(a)}
                      >
                        <td className="py-2.5 px-3 font-semibold text-gray-900">{a.alert_number}</td>
                        <td className="py-2.5 px-3 text-gray-800 font-medium">{a.party_name}</td>
                        <td className="py-2.5 px-3 text-red-700 font-medium">{a.matched_entity_name}</td>
                        <td className="py-2.5 px-3 text-center font-bold">
                          <span
                            className={`px-2 py-0.5 rounded-full ${
                              a.match_score >= 0.9
                                ? 'bg-red-100 text-red-800'
                                : 'bg-amber-100 text-amber-800'
                            }`}
                          >
                            {(a.match_score * 100).toFixed(0)}%
                          </span>
                        </td>
                        <td className="py-2.5 px-3">
                          <span className="capitalize px-2 py-0.5 bg-gray-100 text-gray-800 rounded font-medium">
                            {a.status.replace(/_/g, ' ')}
                          </span>
                        </td>
                        <td className="py-2.5 px-3 text-right">
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              handleSelectAlert(a);
                            }}
                            className="text-xs text-red-600 hover:text-red-900 font-semibold"
                          >
                            Investigate &rarr;
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* Agent A8 Explainer & Human Adjudication Panel */}
          {selectedAlert && (
            <div className="bg-white p-5 rounded-lg border border-red-200 shadow-sm space-y-4">
              <div className="flex items-center justify-between border-b pb-2">
                <div>
                  <h3 className="font-bold text-gray-900 flex items-center gap-2">
                    <span>Agent A8 Match Analysis: {selectedAlert.alert_number}</span>
                    <span className="text-[10px] bg-red-100 text-red-800 font-bold px-2 py-0.5 rounded-full">
                      AI Auto-Clear Strictly Prohibited
                    </span>
                  </h3>
                  <p className="text-xs text-gray-500">Screened Entity: {selectedAlert.party_name}</p>
                </div>
                <span className="text-xs font-bold px-2.5 py-1 bg-red-100 text-red-800 rounded">
                  Match: {(selectedAlert.match_score * 100).toFixed(0)}%
                </span>
              </div>

              {explaining ? (
                <div className="text-center py-4 text-xs text-gray-400">Agent A8 is compiling match indicators...</div>
              ) : explanation ? (
                <div className="space-y-3">
                  <div className="bg-gray-50 p-3 rounded text-xs space-y-1.5 border border-gray-100">
                    <span className="font-bold text-gray-900 block">Objective Comparative Analysis:</span>
                    <p className="text-gray-700 leading-relaxed">{explanation.analysis_text}</p>
                  </div>

                  {explanation.draft_sar_report && (
                    <div className="bg-amber-50/60 p-3 rounded text-xs border border-amber-200">
                      <div className="flex justify-between items-center mb-1">
                        <span className="font-bold text-amber-900">Draft Suspicious Activity Report (SAR) Narrative:</span>
                        <span className="text-[10px] bg-amber-200 text-amber-800 px-1.5 py-0.2 rounded font-semibold">CONFIDENTIAL DRAFT</span>
                      </div>
                      <pre className="font-mono text-[11px] text-gray-800 whitespace-pre-wrap">{explanation.draft_sar_report}</pre>
                    </div>
                  )}

                  {/* Officer Adjudication Controls */}
                  <div className="pt-2 border-t space-y-3">
                    <div>
                      <label className="block text-xs font-semibold text-gray-700 mb-1">
                        Compliance Officer Decision Notes (Mandatory Written Justification)
                      </label>
                      <textarea
                        value={decisionNotes}
                        onChange={(e) => setDecisionNotes(e.target.value)}
                        rows={2}
                        placeholder="State legal findings, corporate registry cross-checks, or confirm sanctions listing..."
                        className="w-full text-xs border rounded px-3 py-2 focus:ring-1 focus:ring-red-500"
                        required
                      />
                    </div>
                    <div className="flex justify-end gap-2">
                      <button
                        onClick={() => handleAdjudicate('false_positive_cleared_by_officer')}
                        className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white font-medium text-xs rounded transition"
                      >
                        Clear as False Positive
                      </button>
                      <button
                        onClick={() => handleAdjudicate('confirmed_hit')}
                        className="px-3 py-1.5 bg-red-600 hover:bg-red-700 text-white font-medium text-xs rounded transition"
                      >
                        Confirm Sanctions Hit & Freeze
                      </button>
                    </div>
                  </div>
                </div>
              ) : null}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
