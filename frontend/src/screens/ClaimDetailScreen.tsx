import React, { useEffect, useState } from 'react';
import {
  ArrowLeft,
  FileText,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Sparkles,
  ChevronDown,
  ChevronRight,
  Activity,
  CreditCard,
  UserCheck,
  ShieldAlert,
} from 'lucide-react';
import { api } from '../api/client';
import { AgentRunDetail, ClaimDetail, UserProfile } from '../types';
import { Badge } from '../components/Badge';

interface ClaimDetailScreenProps {
  claimNumber: string;
  currentUser: UserProfile | null;
  onBack: () => void;
  onRefreshQueue: () => void;
}

export const ClaimDetailScreen: React.FC<ClaimDetailScreenProps> = ({
  claimNumber,
  currentUser: _currentUser,
  onBack,
  onRefreshQueue,
}) => {
  const [claim, setClaim] = useState<ClaimDetail | null>(null);
  const [trace, setTrace] = useState<AgentRunDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [triaging, setTriaging] = useState(false);
  const [deciding, setDeciding] = useState(false);
  const [settling, setSettling] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Decision Form State
  const [decisionNotes, setDecisionNotes] = useState('');
  const [payoutAmount, setPayoutAmount] = useState<number>(0);
  const [overrideReason, setOverrideReason] = useState('');
  const [showTraceModal, setShowTraceModal] = useState(false);
  const [expandedClauses, setExpandedClauses] = useState<Record<string, boolean>>({});

  const fetchClaimData = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getClaim(claimNumber);
      setClaim(data);

      const payable = data.triage_recommendation?.payout?.payable ?? data.approved_payout ?? data.claimed_amount;
      setPayoutAmount(Number(payable));

      // Attempt to load trace if triage happened
      try {
        const traceData = await api.getTrace(`triage-${claimNumber}`);
        setTrace(traceData);
      } catch {
        // Trace may not exist yet if untriaged
        setTrace(null);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to fetch claim details');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchClaimData();
  }, [claimNumber]);

  const handleTriggerTriage = async () => {
    setTriaging(true);
    setError(null);
    try {
      const updated = await api.triageClaim(claimNumber);
      setClaim(updated);
      try {
        const traceData = await api.getTrace(`triage-${claimNumber}`);
        setTrace(traceData);
      } catch {}
      onRefreshQueue();
    } catch (err: any) {
      setError(err.message || 'Triage execution failed');
    } finally {
      setTriaging(false);
    }
  };

  const handleDecision = async (decision: 'approve' | 'reject') => {
    if (!decisionNotes.trim()) {
      alert('Mandatory Requirement: Please provide adjuster justification notes before recording decision.');
      return;
    }

    setDeciding(true);
    setError(null);
    try {
      const updated = await api.recordDecision(claimNumber, {
        decision,
        approved_payout: decision === 'approve' ? payoutAmount : 0,
        notes: decisionNotes,
        override_reason: overrideReason || undefined,
      });
      setClaim(updated);
      onRefreshQueue();
    } catch (err: any) {
      setError(err.message || 'Failed to record decision');
    } finally {
      setDeciding(false);
    }
  };

  const handleSettle = async () => {
    setSettling(true);
    setError(null);
    try {
      const updated = await api.settleClaim(claimNumber);
      setClaim(updated);
      onRefreshQueue();
    } catch (err: any) {
      setError(err.message || 'Settlement disbursement failed');
    } finally {
      setSettling(false);
    }
  };

  const toggleClause = (id: string) => {
    setExpandedClauses((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  if (loading) {
    return (
      <div className="py-20 text-center text-slate-400">
        <Activity className="h-8 w-8 animate-spin mx-auto text-sky-500 mb-2" />
        <p>Loading dossier for {claimNumber}...</p>
      </div>
    );
  }

  if (!claim) {
    return (
      <div className="p-8 text-center bg-slate-900 border border-slate-800 rounded-xl text-slate-400">
        <p>Claim not found.</p>
        <button onClick={onBack} className="mt-4 px-4 py-2 bg-sky-600 text-white rounded-lg text-xs">
          Return to Queue
        </button>
      </div>
    );
  }

  const rec = claim.triage_recommendation;
  const isHighValue = payoutAmount > 10000;
  const canDecide = claim.status === 'awaiting_review' || claim.status === 'registered';
  const canSettle = claim.status === 'approved';

  return (
    <div className="space-y-6">
      {/* Top Bar Navigation */}
      <div className="flex items-center justify-between">
        <button
          onClick={onBack}
          className="flex items-center space-x-2 text-slate-400 hover:text-white text-xs font-semibold transition"
        >
          <ArrowLeft className="h-4 w-4" />
          <span>Back to Claims Queue</span>
        </button>

        <div className="flex items-center space-x-3">
          {trace && (
            <button
              onClick={() => setShowTraceModal(true)}
              className="flex items-center space-x-1.5 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-sky-400 border border-slate-700 rounded-lg text-xs font-medium transition"
            >
              <Activity className="h-3.5 w-3.5" />
              <span>Inspect Agent Trace ({trace.steps.length} Steps)</span>
            </button>
          )}

          {!rec && (
            <button
              onClick={handleTriggerTriage}
              disabled={triaging}
              className="flex items-center space-x-1.5 px-3.5 py-1.5 bg-sky-600 hover:bg-sky-500 text-white rounded-lg text-xs font-medium shadow transition disabled:opacity-50"
            >
              <Sparkles className={`h-3.5 w-3.5 ${triaging ? 'animate-spin' : ''}`} />
              <span>{triaging ? 'Triaging with A4 Agent...' : 'Run A4 Triage Agent'}</span>
            </button>
          )}
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs">
          {error}
        </div>
      )}

      {/* Hero Dossier Header */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow">
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 border-b border-slate-800 pb-5">
          <div>
            <div className="flex items-center space-x-3">
              <h1 className="text-2xl font-extrabold text-white font-mono tracking-tight">
                {claim.claim_number}
              </h1>
              <Badge type="status" value={claim.status} />
              <Badge type="autonomy" value={claim.autonomy_level} />
            </div>
            <p className="text-xs text-slate-400 mt-1">
              Policy: <strong className="text-sky-400 font-mono">{claim.policy_number}</strong> • Product:{' '}
              <span className="text-slate-300 font-semibold">{claim.product_code}</span> • Incident Date:{' '}
              <span className="text-slate-300">{claim.incident_date}</span> (Reported:{' '}
              {claim.notification_date})
            </p>
          </div>

          <div className="flex items-center gap-6 bg-slate-950/60 p-3 rounded-lg border border-slate-800/80">
            <div>
              <div className="text-[11px] text-slate-400 uppercase font-semibold">Claimed Amount</div>
              <div className="text-lg font-bold text-white font-mono">
                {claim.claimed_amount.toLocaleString('en-US', { minimumFractionDigits: 2 })} AZN
              </div>
            </div>
            <div className="h-8 w-px bg-slate-800" />
            <div>
              <div className="text-[11px] text-slate-400 uppercase font-semibold">Approved / Payable</div>
              <div className="text-lg font-bold text-emerald-400 font-mono">
                {(claim.approved_payout ?? rec?.payout?.payable ?? 0).toLocaleString('en-US', {
                  minimumFractionDigits: 2,
                })}{' '}
                AZN
              </div>
            </div>
          </div>
        </div>

        {/* Incident Summary */}
        <div className="mt-4 text-xs text-slate-300 bg-slate-950/40 p-3.5 rounded-lg border border-slate-800">
          <span className="font-semibold text-slate-400 uppercase tracking-wider block mb-1">
            First Notice of Loss Narrative:
          </span>
          <p className="leading-relaxed">{claim.incident_description}</p>
        </div>
      </div>

      {/* Main Grid: AI Recommendation Card vs Documents & Timeline */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left 2 Cols: AI Triage Recommendation & Citations */}
        <div className="lg:col-span-2 space-y-6">
          {rec ? (
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow space-y-6">
              {/* Header with Uncertainty Disclosure */}
              <div className="border-b border-slate-800 pb-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    <Sparkles className="h-5 w-5 text-sky-400" />
                    <h2 className="text-base font-bold text-white">A4 Agent Adjudication Dossier</h2>
                  </div>
                  <Badge type="recommendation" value={rec.recommendation} />
                </div>
                {/* Mandatory Honest AI Label */}
                <div className="mt-2 flex items-center space-x-2 text-[11px] text-amber-300/90 bg-amber-500/10 border border-amber-500/30 px-3 py-1.5 rounded-lg">
                  <AlertTriangle className="h-4 w-4 text-amber-400 flex-shrink-0" />
                  <span>
                    <strong>AI Decision Support (L2 Human-in-the-Loop):</strong> Machine recommendation is
                    advisory. Payout calculation is purely deterministic. Human adjuster must approve or reject.
                  </span>
                </div>
              </div>

              {/* Confidence & Reasoning */}
              <div>
                <div className="flex items-center justify-between text-xs mb-1">
                  <span className="font-semibold text-slate-400">Agent Confidence Score</span>
                  <span className="font-mono font-bold text-sky-400">{(rec.confidence * 100).toFixed(1)}%</span>
                </div>
                <div className="h-2 w-full bg-slate-800 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-sky-500 transition-all duration-500"
                    style={{ width: `${rec.confidence * 100}%` }}
                  />
                </div>
                <p className="text-xs text-slate-300 mt-2.5 bg-slate-800/40 p-3 rounded-lg border border-slate-800 italic">
                  "{rec.reasoning}"
                </p>
              </div>

              {/* Deterministic Payout Breakdown */}
              {rec.payout && (
                <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-3">
                  <div className="flex items-center justify-between">
                    <h3 className="text-xs font-bold text-white uppercase tracking-wider flex items-center space-x-1.5">
                      <CreditCard className="h-4 w-4 text-sky-400" />
                      <span>Deterministic Payout Engine Breakdown</span>
                    </h3>
                    {rec.payout.is_total_loss && (
                      <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-purple-500/20 text-purple-300 border border-purple-500/40 uppercase">
                        Clause D.2: 70% Constructive Total Loss
                      </span>
                    )}
                  </div>
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
                    <div className="bg-slate-900 p-2.5 rounded-lg border border-slate-800">
                      <div className="text-slate-500 text-[11px]">Claimed Sum</div>
                      <div className="font-mono font-bold text-white mt-0.5">
                        {rec.payout.claimed_amount.toFixed(2)} AZN
                      </div>
                    </div>
                    <div className="bg-slate-900 p-2.5 rounded-lg border border-slate-800">
                      <div className="text-slate-500 text-[11px]">Deductible Applied</div>
                      <div className="font-mono font-bold text-amber-400 mt-0.5">
                        -{rec.payout.deductible.toFixed(2)} AZN
                      </div>
                    </div>
                    <div className="bg-slate-900 p-2.5 rounded-lg border border-slate-800">
                      <div className="text-slate-500 text-[11px]">Salvage Deduction</div>
                      <div className="font-mono font-bold text-amber-400 mt-0.5">
                        -{rec.payout.salvage_deduction.toFixed(2)} AZN
                      </div>
                    </div>
                    <div className="bg-sky-950/40 p-2.5 rounded-lg border border-sky-800/60">
                      <div className="text-sky-300 text-[11px] font-semibold">Net Payable</div>
                      <div className="font-mono font-extrabold text-emerald-400 mt-0.5 text-sm">
                        {rec.payout.payable.toFixed(2)} AZN
                      </div>
                    </div>
                  </div>
                  <p className="text-[11px] text-slate-500">Rule: {rec.payout.calculation_rule}</p>
                </div>
              )}

              {/* Fraud Flags & Warnings */}
              {rec.risk_flags.length > 0 && (
                <div className="space-y-2">
                  <span className="text-xs font-semibold text-rose-400 uppercase tracking-wider flex items-center space-x-1">
                    <ShieldAlert className="h-4 w-4" />
                    <span>Fraud & Risk Triggers Detected</span>
                  </span>
                  <div className="flex flex-wrap gap-2">
                    {rec.risk_flags.map((flag, idx) => (
                      <Badge key={idx} type="risk" value={flag} />
                    ))}
                  </div>
                </div>
              )}

              {/* Policy Wording Citations */}
              <div className="space-y-3">
                <h3 className="text-xs font-bold text-white uppercase tracking-wider flex items-center space-x-1.5">
                  <FileText className="h-4 w-4 text-sky-400" />
                  <span>Governing Policy Wording Citations</span>
                </h3>
                {rec.clause_citations.length === 0 ? (
                  <p className="text-xs text-slate-500 italic">No specific statutory clauses cited.</p>
                ) : (
                  <div className="space-y-2">
                    {rec.clause_citations.map((cite) => {
                      const isExpanded = expandedClauses[cite.clause_id];
                      return (
                        <div
                          key={cite.clause_id}
                          className="bg-slate-950 border border-slate-800 rounded-lg overflow-hidden text-xs"
                        >
                          <button
                            onClick={() => toggleClause(cite.clause_id)}
                            className="w-full flex items-center justify-between p-3 text-left hover:bg-slate-850 transition"
                          >
                            <div className="flex items-center space-x-2">
                              {isExpanded ? (
                                <ChevronDown className="h-4 w-4 text-sky-400" />
                              ) : (
                                <ChevronRight className="h-4 w-4 text-slate-500" />
                              )}
                              <span className="font-mono font-semibold text-sky-300">{cite.clause_id}</span>
                              <span className="text-slate-300 font-medium">{cite.title}</span>
                            </div>
                            <span className="text-[11px] text-slate-400">
                              Relevance: {(cite.relevance * 100).toFixed(0)}%
                            </span>
                          </button>
                          {isExpanded && (
                            <div className="p-3 bg-slate-900 border-t border-slate-800 text-slate-300 leading-relaxed font-mono text-[11px]">
                              Section {cite.section} of statutory product policy wording. Enforces deductible,
                              total loss ratios, notification limits, and policyholder covenants.
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            </div>
          ) : (
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-12 text-center text-slate-400 space-y-4">
              <Sparkles className="h-10 w-10 text-sky-500 mx-auto" />
              <div>
                <h3 className="text-base font-bold text-white">Claim Awaiting AI Triage</h3>
                <p className="text-xs text-slate-400 mt-1 max-w-md mx-auto">
                  Run the A4 Claims Triage Agent to extract documents, verify policy active dates, evaluate
                  statutory exclusions, and compute penny-exact payouts.
                </p>
              </div>
              <button
                onClick={handleTriggerTriage}
                disabled={triaging}
                className="px-4 py-2 bg-sky-600 hover:bg-sky-500 text-white rounded-lg text-xs font-semibold shadow transition disabled:opacity-50"
              >
                {triaging ? 'Executing Agent Loop...' : 'Trigger A4 Agent Now'}
              </button>
            </div>
          )}

          {/* Evidence Documents Section */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow space-y-4">
            <h3 className="text-xs font-bold text-white uppercase tracking-wider flex items-center space-x-1.5">
              <FileText className="h-4 w-4 text-sky-400" />
              <span>Evidence Documents & Intake Transcripts ({claim.documents.length})</span>
            </h3>

            {claim.documents.length === 0 ? (
              <p className="text-xs text-slate-500 italic">No external document files attached to this FNOL.</p>
            ) : (
              <div className="space-y-2">
                {claim.documents.map((doc) => (
                  <div
                    key={doc.id}
                    className="bg-slate-950 p-3.5 rounded-lg border border-slate-800 text-xs space-y-1.5"
                  >
                    <div className="flex items-center justify-between">
                      <div className="font-semibold text-white flex items-center space-x-2">
                        <span className="text-sky-400 font-mono">[{doc.document_type.toUpperCase()}]</span>
                        <span>{doc.file_name}</span>
                      </div>
                      <span className="text-slate-500 text-[11px]">{doc.created_at}</span>
                    </div>
                    <div className="text-slate-300 bg-slate-900/60 p-2.5 rounded border border-slate-800 font-mono text-[11px] leading-relaxed">
                      {doc.content_text}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Right Col: Adjuster Action Panel & Settlement */}
        <div className="space-y-6">
          {/* Adjuster Decision Panel */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow space-y-5">
            <div className="border-b border-slate-800 pb-3">
              <h3 className="text-sm font-bold text-white flex items-center space-x-1.5">
                <UserCheck className="h-4 w-4 text-sky-400" />
                <span>Adjuster Review & Governance</span>
              </h3>
              <p className="text-[11px] text-slate-400 mt-0.5">
                Human-in-the-loop sign-off with audit trail enforcement.
              </p>
            </div>

            {claim.adjuster_decision ? (
              <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-3 text-xs">
                <div className="flex items-center justify-between">
                  <span className="text-slate-400">Adjudication Decision:</span>
                  <span className="font-bold uppercase text-emerald-400">
                    {claim.adjuster_decision.decision}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-slate-400">Decided By:</span>
                  <span className="font-mono text-white">{claim.adjuster_decision.adjuster_id}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-slate-400">Approved Payout:</span>
                  <span className="font-mono font-bold text-emerald-400">
                    {claim.adjuster_decision.approved_payout.toFixed(2)} AZN
                  </span>
                </div>
                <div className="pt-2 border-t border-slate-800 text-slate-300 italic">
                  "{claim.adjuster_decision.notes}"
                </div>

                {canSettle && (
                  <div className="pt-3">
                    <button
                      onClick={handleSettle}
                      disabled={settling}
                      className="w-full py-2.5 px-4 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg font-bold text-xs shadow transition flex items-center justify-center space-x-1.5 disabled:opacity-50"
                    >
                      <CreditCard className="h-4 w-4" />
                      <span>{settling ? 'Disbursing...' : 'Disburse & Settle Payout'}</span>
                    </button>
                  </div>
                )}
              </div>
            ) : canDecide ? (
              <div className="space-y-4 text-xs">
                {isHighValue && (
                  <div className="p-3 bg-amber-500/10 border border-amber-500/30 rounded-lg text-amber-300 text-[11px] flex items-start space-x-2">
                    <AlertTriangle className="h-4 w-4 flex-shrink-0 text-amber-400" />
                    <span>
                      <strong>Four-Eyes Threshold:</strong> Claims exceeding 10,000 AZN require Senior Claims
                      Lead confirmation.
                    </span>
                  </div>
                )}

                {/* Approved Payout Field */}
                <div>
                  <label className="block text-slate-400 font-semibold mb-1">Approved Payout Amount (AZN)</label>
                  <input
                    type="number"
                    step="0.01"
                    value={payoutAmount}
                    onChange={(e) => setPayoutAmount(parseFloat(e.target.value) || 0)}
                    className="w-full px-3 py-2 bg-slate-950 border border-slate-700 rounded-lg font-mono text-white text-sm focus:outline-none focus:border-sky-500"
                  />
                </div>

                {/* Mandatory Notes */}
                <div>
                  <label className="block text-slate-400 font-semibold mb-1">
                    Adjuster Notes <span className="text-rose-400">*</span>
                  </label>
                  <textarea
                    rows={3}
                    value={decisionNotes}
                    onChange={(e) => setDecisionNotes(e.target.value)}
                    placeholder="Enter formal justification for approval or repudiation..."
                    className="w-full px-3 py-2 bg-slate-950 border border-slate-700 rounded-lg text-white text-xs placeholder-slate-500 focus:outline-none focus:border-sky-500"
                  />
                </div>

                {/* Override Reason if Diverging */}
                <div>
                  <label className="block text-slate-400 font-semibold mb-1">
                    Override Reason (if disagreeing with AI)
                  </label>
                  <input
                    type="text"
                    value={overrideReason}
                    onChange={(e) => setOverrideReason(e.target.value)}
                    placeholder="e.g. Police citation clarified by insured"
                    className="w-full px-3 py-1.5 bg-slate-950 border border-slate-700 rounded-lg text-white text-xs placeholder-slate-500 focus:outline-none focus:border-sky-500"
                  />
                </div>

                {/* Action Buttons */}
                <div className="grid grid-cols-2 gap-2 pt-2">
                  <button
                    onClick={() => handleDecision('approve')}
                    disabled={deciding}
                    className="py-2.5 px-3 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg font-bold text-xs shadow transition flex items-center justify-center space-x-1 disabled:opacity-50"
                  >
                    <CheckCircle2 className="h-3.5 w-3.5" />
                    <span>Approve Payout</span>
                  </button>
                  <button
                    onClick={() => handleDecision('reject')}
                    disabled={deciding}
                    className="py-2.5 px-3 bg-rose-600 hover:bg-rose-500 text-white rounded-lg font-bold text-xs shadow transition flex items-center justify-center space-x-1 disabled:opacity-50"
                  >
                    <XCircle className="h-3.5 w-3.5" />
                    <span>Repudiate Claim</span>
                  </button>
                </div>
              </div>
            ) : (
              <p className="text-xs text-slate-500 italic">
                Claim is currently in state <strong>{claim.status}</strong>. Adjudication complete.
              </p>
            )}
          </div>

          {/* Reserve Ledger Card */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow space-y-3">
            <h3 className="text-xs font-bold text-white uppercase tracking-wider flex items-center space-x-1.5">
              <CreditCard className="h-4 w-4 text-sky-400" />
              <span>Claim Reserve Ledger</span>
            </h3>
            <div className="space-y-2 text-xs">
              {claim.reserves.map((res) => (
                <div
                  key={res.id}
                  className="bg-slate-950 p-2.5 rounded-lg border border-slate-800 flex items-center justify-between"
                >
                  <div>
                    <span className="font-semibold text-white capitalize">{res.reserve_type} Reserve</span>
                    <span className="text-slate-500 block text-[11px]">{res.reason}</span>
                  </div>
                  <span className="font-mono font-bold text-white">{res.amount.toFixed(2)} AZN</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Trace Timeline Modal */}
      {showTraceModal && trace && (
        <div className="fixed inset-0 bg-black/80 flex items-center justify-center p-4 z-50">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-3xl w-full max-h-[85vh] flex flex-col shadow-2xl overflow-hidden">
            <div className="p-4 border-b border-slate-800 flex items-center justify-between bg-slate-950">
              <div className="flex items-center space-x-2">
                <Activity className="h-5 w-5 text-sky-400" />
                <h3 className="text-sm font-bold text-white">
                  ReAct Agent Execution Trace: <span className="font-mono">{trace.correlation_id}</span>
                </h3>
              </div>
              <button
                onClick={() => setShowTraceModal(false)}
                className="text-slate-400 hover:text-white p-1 rounded-lg text-xs"
              >
                ✕ Close
              </button>
            </div>

            <div className="p-6 overflow-y-auto space-y-4 text-xs font-mono">
              <div className="grid grid-cols-4 gap-2 bg-slate-950 p-3 rounded-lg border border-slate-800 text-center">
                <div>
                  <div className="text-slate-500 text-[10px]">Steps</div>
                  <div className="text-white font-bold">{trace.step_count}</div>
                </div>
                <div>
                  <div className="text-slate-500 text-[10px]">Tokens</div>
                  <div className="text-white font-bold">{trace.total_tokens}</div>
                </div>
                <div>
                  <div className="text-slate-500 text-[10px]">Cost</div>
                  <div className="text-white font-bold">${trace.total_cost_usd.toFixed(4)}</div>
                </div>
                <div>
                  <div className="text-slate-500 text-[10px]">Duration</div>
                  <div className="text-white font-bold">{trace.duration_seconds.toFixed(2)}s</div>
                </div>
              </div>

              <div className="space-y-3">
                {trace.steps.map((st) => (
                  <div key={st.id} className="bg-slate-950 p-3.5 rounded-lg border border-slate-800 space-y-2">
                    <div className="flex items-center justify-between text-[11px]">
                      <span className="px-2 py-0.5 rounded bg-sky-500/20 text-sky-300 font-bold uppercase">
                        Step {st.step_index}: {st.step_kind}
                      </span>
                      <span className="text-slate-500">{st.latency_ms} ms</span>
                    </div>

                    {st.tool_name && (
                      <div className="text-white font-bold flex items-center space-x-1">
                        <span>Tool:</span>
                        <span className="text-amber-400">{st.tool_name}</span>
                      </div>
                    )}

                    {st.tool_input && (
                      <div>
                        <div className="text-slate-500 text-[10px] uppercase">Input:</div>
                        <pre className="bg-slate-900 p-2 rounded text-[11px] text-slate-300 overflow-x-auto mt-0.5">
                          {JSON.stringify(st.tool_input, null, 2)}
                        </pre>
                      </div>
                    )}

                    {st.tool_output && (
                      <div>
                        <div className="text-slate-500 text-[10px] uppercase">Output:</div>
                        <pre className="bg-slate-900 p-2 rounded text-[11px] text-emerald-300 overflow-x-auto mt-0.5">
                          {JSON.stringify(st.tool_output, null, 2)}
                        </pre>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
