import React, { useEffect, useState } from 'react';
import { api } from '../api/client';
import { ComplaintItem, CustomerChatResponse, EndorsementDraftResult } from '../types';

export const CustomerServiceScreen: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'chat' | 'endorsement' | 'complaints'>('chat');

  // Chat State (Agent A6)
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false);
  const [verifiedPartyId, setVerifiedPartyId] = useState<string>('PARTY-VERIFIED-01');
  const [chatMessage, setChatMessage] = useState<string>('');
  const [chatLog, setChatLog] = useState<Array<{ sender: 'user' | 'agent'; text: string; action?: string | null; dataAccessed?: boolean }>>([
    {
      sender: 'agent',
      text: 'Hello! I am your InsurAI Assistant. How can I assist you with insurance coverage, claims, or general questions today?',
    },
  ]);
  const [chatLoading, setChatLoading] = useState<boolean>(false);

  // Endorsement State (Agent A3)
  const [policyNumber, setPolicyNumber] = useState<string>('POL-20261012-001');
  const [endorsementType, setEndorsementType] = useState<string>('INCREASE_SUM_INSURED');
  const [effectiveDate, setEffectiveDate] = useState<string>(new Date().toISOString().slice(0, 10));
  const [newValuation, setNewValuation] = useState<number>(45000);
  const [endorsementResult, setEndorsementResult] = useState<EndorsementDraftResult | null>(null);
  const [proposingEndorsement, setProposingEndorsement] = useState<boolean>(false);

  // Complaints State
  const [complaints, setComplaints] = useState<ComplaintItem[]>([]);
  const [complaintPartyId, setComplaintPartyId] = useState<string>('PARTY-CUST-01');
  const [complaintSubject, setComplaintSubject] = useState<string>('Delayed Claim Inspection');
  const [complaintDescription, setComplaintDescription] = useState<string>('Adjuster did not show up on the agreed inspection date.');
  const [submittingComplaint, setSubmittingComplaint] = useState<boolean>(false);

  const [actionMsg, setActionMsg] = useState<string | null>(null);

  const loadComplaints = async () => {
    try {
      const data = await api.getComplaints();
      setComplaints(data);
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    if (activeTab === 'complaints') {
      loadComplaints();
    }
  }, [activeTab]);

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!chatMessage.trim()) return;

    const userText = chatMessage.trim();
    setChatLog((prev) => [...prev, { sender: 'user', text: userText }]);
    setChatMessage('');
    setChatLoading(true);

    try {
      const res: CustomerChatResponse = await api.sendCustomerChat(
        userText,
        isAuthenticated,
        isAuthenticated ? verifiedPartyId : undefined
      );

      setChatLog((prev) => [
        ...prev,
        {
          sender: 'agent',
          text: res.reply_text,
          action: res.action_taken,
          dataAccessed: res.data_accessed,
        },
      ]);
    } catch (err: any) {
      setChatLog((prev) => [
        ...prev,
        {
          sender: 'agent',
          text: `Service error: ${err.message || 'Unable to process request.'}`,
        },
      ]);
    } finally {
      setChatLoading(false);
    }
  };

  const handleProposeEndorsement = async (e: React.FormEvent) => {
    e.preventDefault();
    setProposingEndorsement(true);
    setActionMsg(null);
    try {
      const res = await api.proposeEndorsement(policyNumber.trim(), endorsementType, effectiveDate, {
        new_sum_insured: newValuation,
      });
      setEndorsementResult(res);
      setActionMsg(`Agent A3 drafted endorsement proposal: ${res.prorata_adjustment_azn} AZN pro-rata adjustment.`);
    } catch (err: any) {
      setActionMsg(`Failed to propose endorsement: ${err.message || 'Unknown error'}`);
    } finally {
      setProposingEndorsement(false);
    }
  };

  const handleSubmitComplaint = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!complaintSubject.trim() || !complaintDescription.trim()) return;
    setSubmittingComplaint(true);
    setActionMsg(null);
    try {
      const res = await api.submitComplaint(complaintPartyId.trim(), complaintSubject.trim(), complaintDescription.trim());
      setActionMsg(`Formal complaint registered: ${res.complaint_number}. Statutory SLAs active.`);
      setComplaintSubject('');
      setComplaintDescription('');
      await loadComplaints();
    } catch (err: any) {
      setActionMsg(`Failed to submit complaint: ${err.message || 'Unknown error'}`);
    } finally {
      setSubmittingComplaint(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between pb-4 border-b border-gray-200">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <span>🎧 Customer Service & Policy Servicing</span>
            <span className="text-xs bg-cyan-100 text-cyan-800 px-2.5 py-0.5 rounded-full font-semibold">
              Agents A6 & A3 Active
            </span>
          </h1>
          <p className="text-sm text-gray-500 mt-1">
            Identity verification gated customer dialogue (A6), mid-term endorsement pro-rata drafting (A3), and statutory complaint SLAs.
          </p>
        </div>
        {/* Navigation Tabs */}
        <div className="mt-4 md:mt-0 flex gap-2">
          <button
            onClick={() => setActiveTab('chat')}
            className={`px-3 py-1.5 text-sm rounded font-medium transition ${
              activeTab === 'chat' ? 'bg-indigo-600 text-white' : 'bg-white border text-gray-700 hover:bg-gray-50'
            }`}
          >
            Agent A6 Customer Chat
          </button>
          <button
            onClick={() => setActiveTab('endorsement')}
            className={`px-3 py-1.5 text-sm rounded font-medium transition ${
              activeTab === 'endorsement' ? 'bg-indigo-600 text-white' : 'bg-white border text-gray-700 hover:bg-gray-50'
            }`}
          >
            Agent A3 Endorsements (P06)
          </button>
          <button
            onClick={() => setActiveTab('complaints')}
            className={`px-3 py-1.5 text-sm rounded font-medium transition ${
              activeTab === 'complaints' ? 'bg-indigo-600 text-white' : 'bg-white border text-gray-700 hover:bg-gray-50'
            }`}
          >
            Complaints SLA Tracker
          </button>
        </div>
      </div>

      {actionMsg && (
        <div className="p-3 bg-blue-50 border border-blue-200 rounded text-sm text-blue-800 flex justify-between items-center">
          <span>{actionMsg}</span>
          <button onClick={() => setActionMsg(null)} className="text-blue-500 hover:text-blue-700 font-bold">&times;</button>
        </div>
      )}

      {/* Tab 1: Agent A6 Customer Chat with Verification Gate */}
      {activeTab === 'chat' && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left: Verification Gate Controls */}
          <div className="bg-white p-5 rounded-lg border border-gray-200 shadow-sm space-y-4">
            <h2 className="text-lg font-bold text-gray-900 border-b pb-2 flex items-center justify-between">
              <span>Verification Gate Simulator</span>
              <span className={`text-xs px-2 py-0.5 rounded font-bold ${isAuthenticated ? 'bg-emerald-100 text-emerald-800' : 'bg-amber-100 text-amber-800'}`}>
                {isAuthenticated ? 'VERIFIED' : 'GUEST / UNVERIFIED'}
              </span>
            </h2>
            <p className="text-xs text-gray-500">
              Toggle authentication to observe how Agent A6 strictly defends policyholder PII and contracts:
            </p>

            <div className="p-3 bg-gray-50 rounded border space-y-3">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={isAuthenticated}
                  onChange={(e) => setIsAuthenticated(e.target.checked)}
                  className="rounded text-indigo-600 focus:ring-indigo-500"
                />
                <span className="text-xs font-semibold text-gray-800">
                  Simulate Verified Session (FIN / Mobile OTP)
                </span>
              </label>

              {isAuthenticated && (
                <div>
                  <label className="block text-[11px] font-semibold text-gray-600 mb-1">Verified Party ID</label>
                  <input
                    type="text"
                    value={verifiedPartyId}
                    onChange={(e) => setVerifiedPartyId(e.target.value)}
                    className="w-full text-xs border rounded px-2 py-1 bg-white"
                  />
                </div>
              )}
            </div>

            <div className="space-y-2 text-xs text-gray-600">
              <span className="font-bold text-gray-800 block">Suggested Test Prompts:</span>
              <div className="space-y-1">
                <button
                  onClick={() => setChatMessage('What is the standard deductible?')}
                  className="w-full text-left p-1.5 bg-gray-50 hover:bg-gray-100 rounded text-gray-700"
                >
                  💬 "What is the standard deductible?" (FAQ)
                </button>
                <button
                  onClick={() => setChatMessage('Can you show my policy details and status?')}
                  className="w-full text-left p-1.5 bg-gray-50 hover:bg-gray-100 rounded text-gray-700"
                >
                  🔒 "Show my policy details" (Gated PII)
                </button>
                <button
                  onClick={() => setChatMessage('How can I pay my insurance premium?')}
                  className="w-full text-left p-1.5 bg-gray-50 hover:bg-gray-100 rounded text-gray-700"
                >
                  💳 "How can I pay my premium?" (FAQ)
                </button>
              </div>
            </div>
          </div>

          {/* Right: Interactive Chat Console */}
          <div className="lg:col-span-2 bg-white rounded-lg border border-gray-200 shadow-sm flex flex-col h-[520px]">
            <div className="p-3 border-b bg-gray-50 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 bg-emerald-500 rounded-full"></span>
                <span className="font-semibold text-xs text-gray-800">InsurAI Customer Service Bot</span>
              </div>
              <span className="text-xs text-gray-400">Strict Non-Leakage Architecture</span>
            </div>

            {/* Chat Messages */}
            <div className="flex-1 p-4 overflow-y-auto space-y-3">
              {chatLog.map((msg, idx) => (
                <div key={idx} className={`flex ${msg.sender === 'user' ? 'justify-end' : 'justify-start'}`}>
                  <div
                    className={`max-w-[80%] rounded-lg p-3 text-xs leading-relaxed ${
                      msg.sender === 'user'
                        ? 'bg-indigo-600 text-white'
                        : 'bg-gray-100 text-gray-900 border border-gray-200'
                    }`}
                  >
                    <p className="whitespace-pre-wrap">{msg.text}</p>
                    {msg.sender === 'agent' && msg.action && (
                      <div className="mt-1.5 pt-1.5 border-t border-gray-200/50 flex items-center gap-2 text-[10px] text-gray-500">
                        <span className="font-semibold">Action: {msg.action}</span>
                        {msg.dataAccessed ? (
                          <span className="text-emerald-600 font-bold">Policy Data Accessed</span>
                        ) : (
                          <span className="text-blue-600 font-semibold">Zero Data Exposure</span>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              ))}
              {chatLoading && (
                <div className="flex justify-start">
                  <div className="bg-gray-100 text-gray-500 p-2.5 rounded-lg text-xs italic">
                    Agent A6 is verifying request permissions...
                  </div>
                </div>
              )}
            </div>

            {/* Chat Input */}
            <form onSubmit={handleSendMessage} className="p-3 border-t flex gap-2">
              <input
                type="text"
                value={chatMessage}
                onChange={(e) => setChatMessage(e.target.value)}
                placeholder="Ask about policies, claims, or coverage rules..."
                className="flex-1 text-xs border rounded px-3 py-2 focus:ring-1 focus:ring-indigo-500"
              />
              <button
                type="submit"
                disabled={chatLoading}
                className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white font-medium text-xs rounded transition disabled:opacity-50"
              >
                Send
              </button>
            </form>
          </div>
        </div>
      )}

      {/* Tab 2: Agent A3 Mid-term Endorsement Servicing (P06) */}
      {activeTab === 'endorsement' && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="bg-white p-5 rounded-lg border border-gray-200 shadow-sm space-y-4">
            <h2 className="text-lg font-bold text-gray-900 border-b pb-2 flex items-center justify-between">
              <span>Agent A3 Endorsement Simulator</span>
              <span className="text-xs font-normal text-purple-700 bg-purple-50 px-2 py-0.5 rounded">Process P06</span>
            </h2>
            <form onSubmit={handleProposeEndorsement} className="space-y-3">
              <div>
                <label className="block text-xs font-semibold text-gray-600 mb-1">Policy Number</label>
                <input
                  type="text"
                  value={policyNumber}
                  onChange={(e) => setPolicyNumber(e.target.value)}
                  placeholder="e.g. POL-20261012-001"
                  className="w-full text-sm border rounded px-3 py-2"
                  required
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-gray-600 mb-1">Endorsement Type</label>
                <select
                  value={endorsementType}
                  onChange={(e) => setEndorsementType(e.target.value)}
                  className="w-full text-xs border rounded px-3 py-2 bg-white"
                >
                  <option value="INCREASE_SUM_INSURED">Increase Sum Insured / Valuation</option>
                  <option value="ADD_DRIVER">Add Designated Named Driver</option>
                  <option value="ADDRESS_CHANGE">Policyholder Address Relocation</option>
                </select>
              </div>
              <div>
                <label className="block text-xs font-semibold text-gray-600 mb-1">Effective Date</label>
                <input
                  type="date"
                  value={effectiveDate}
                  onChange={(e) => setEffectiveDate(e.target.value)}
                  className="w-full text-xs border rounded px-3 py-2"
                  required
                />
              </div>
              {endorsementType === 'INCREASE_SUM_INSURED' && (
                <div>
                  <label className="block text-xs font-semibold text-gray-600 mb-1">Updated Valuation (AZN)</label>
                  <input
                    type="number"
                    value={newValuation}
                    onChange={(e) => setNewValuation(parseFloat(e.target.value) || 0)}
                    className="w-full text-sm border rounded px-3 py-2"
                    required
                  />
                </div>
              )}
              <button
                type="submit"
                disabled={proposingEndorsement}
                className="w-full py-2 bg-purple-600 hover:bg-purple-700 text-white font-medium text-xs rounded transition disabled:opacity-50"
              >
                {proposingEndorsement ? 'Drafting Endorsement...' : 'Calculate Pro-Rata & Draft Endorsement'}
              </button>
            </form>
          </div>

          {/* Endorsement Result Card */}
          <div className="lg:col-span-2 bg-white p-5 rounded-lg border border-gray-200 shadow-sm space-y-4">
            <h2 className="text-lg font-bold text-gray-900 border-b pb-2">
              Endorsement Draft Analysis & Underwriter Sign-off
            </h2>

            {endorsementResult ? (
              <div className="space-y-4">
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                  <div className="p-3 bg-gray-50 rounded border text-xs">
                    <span className="text-gray-500 block">Policy</span>
                    <span className="font-bold text-gray-900">{endorsementResult.policy_number}</span>
                  </div>
                  <div className="p-3 bg-purple-50 rounded border border-purple-100 text-xs">
                    <span className="text-purple-600 block">Pro-Rata Adjustment</span>
                    <span className="font-bold text-purple-900 text-sm">+{endorsementResult.prorata_adjustment_azn.toFixed(2)} AZN</span>
                  </div>
                  <div className="p-3 bg-gray-50 rounded border text-xs">
                    <span className="text-gray-500 block">Autonomy Level</span>
                    <span className="font-bold text-amber-700">{endorsementResult.autonomy_level}</span>
                  </div>
                  <div className="p-3 bg-amber-50 rounded border border-amber-100 text-xs">
                    <span className="text-amber-700 block">UW Sign-off</span>
                    <span className="font-bold text-amber-900">
                      {endorsementResult.requires_underwriter_approval ? 'Required (L2)' : 'Pre-approved'}
                    </span>
                  </div>
                </div>

                <div className="p-3 bg-gray-50 rounded text-xs text-gray-700">
                  <span className="font-bold text-gray-900 block mb-1">Agent A3 Rationale Dossier:</span>
                  <p>{endorsementResult.summary_explanation}</p>
                </div>
              </div>
            ) : (
              <div className="text-center py-12 text-gray-400 text-sm">
                Submit an endorsement change request on the left to review pro-rata adjustments.
              </div>
            )}
          </div>
        </div>
      )}

      {/* Tab 3: Complaints & Statutory SLA Tracker */}
      {activeTab === 'complaints' && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="bg-white p-5 rounded-lg border border-gray-200 shadow-sm space-y-4">
            <h2 className="text-lg font-bold text-gray-900 border-b pb-2">File Formal Complaint</h2>
            <form onSubmit={handleSubmitComplaint} className="space-y-3">
              <div>
                <label className="block text-xs font-semibold text-gray-600 mb-1">Customer Party ID</label>
                <input
                  type="text"
                  value={complaintPartyId}
                  onChange={(e) => setComplaintPartyId(e.target.value)}
                  className="w-full text-xs border rounded px-3 py-2"
                  required
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-gray-600 mb-1">Subject</label>
                <input
                  type="text"
                  value={complaintSubject}
                  onChange={(e) => setComplaintSubject(e.target.value)}
                  placeholder="e.g. Delayed Payout on Claim"
                  className="w-full text-xs border rounded px-3 py-2"
                  required
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-gray-600 mb-1">Detailed Description</label>
                <textarea
                  value={complaintDescription}
                  onChange={(e) => setComplaintDescription(e.target.value)}
                  rows={3}
                  className="w-full text-xs border rounded px-3 py-2"
                  required
                />
              </div>
              <button
                type="submit"
                disabled={submittingComplaint}
                className="w-full py-2 bg-rose-600 hover:bg-rose-700 text-white font-medium text-xs rounded transition disabled:opacity-50"
              >
                {submittingComplaint ? 'Registering...' : 'Register Complaint (Activate Statutory SLA)'}
              </button>
            </form>
          </div>

          <div className="lg:col-span-2 bg-white p-5 rounded-lg border border-gray-200 shadow-sm">
            <h2 className="text-lg font-bold text-gray-900 border-b pb-3 mb-4">Active Customer Complaints Queue</h2>
            {complaints.length === 0 ? (
              <div className="text-center py-8 text-gray-400 text-sm">No registered complaints in system.</div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs border-collapse">
                  <thead>
                    <tr className="bg-gray-50 text-gray-500 border-b">
                      <th className="py-2.5 px-3">Complaint #</th>
                      <th className="py-2.5 px-3">Party</th>
                      <th className="py-2.5 px-3">Subject</th>
                      <th className="py-2.5 px-3">Initial SLA (5d)</th>
                      <th className="py-2.5 px-3">Final SLA (15d)</th>
                      <th className="py-2.5 px-3">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {complaints.map((c) => (
                      <tr key={c.id} className="hover:bg-gray-50 transition">
                        <td className="py-2.5 px-3 font-semibold text-gray-900">{c.complaint_number}</td>
                        <td className="py-2.5 px-3 text-gray-600">{c.party_id}</td>
                        <td className="py-2.5 px-3 font-medium text-gray-800">{c.subject}</td>
                        <td className="py-2.5 px-3 text-gray-500">{c.initial_response_deadline}</td>
                        <td className="py-2.5 px-3 text-gray-500">{c.final_resolution_deadline}</td>
                        <td className="py-2.5 px-3">
                          {c.sla_breached ? (
                            <span className="px-2 py-0.5 bg-red-100 text-red-800 rounded font-bold">
                              BREACHED (Escalated)
                            </span>
                          ) : (
                            <span className="capitalize px-2 py-0.5 bg-blue-50 text-blue-800 rounded font-medium">
                              {c.status}
                            </span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
