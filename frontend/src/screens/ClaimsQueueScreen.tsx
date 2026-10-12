import React, { useEffect, useState } from 'react';
import { Search, RefreshCw, AlertCircle, ArrowUpRight } from 'lucide-react';
import { api } from '../api/client';
import { ClaimSummary } from '../types';
import { Badge } from '../components/Badge';

interface ClaimsQueueScreenProps {
  onSelectClaim: (claimNumber: string) => void;
  onNavigateFNOL: () => void;
}

export const ClaimsQueueScreen: React.FC<ClaimsQueueScreenProps> = ({
  onSelectClaim,
  onNavigateFNOL,
}) => {
  const [claims, setClaims] = useState<ClaimSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');

  const fetchClaims = async () => {
    setLoading(true);
    setError(null);
    try {
      const filter = statusFilter === 'all' ? undefined : statusFilter;
      const data = await api.listClaims(search || undefined, filter);
      setClaims(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load claims queue');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchClaims();
  }, [statusFilter]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    fetchClaims();
  };

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Claims Adjudication Queue</h1>
          <p className="text-sm text-slate-400">
            Real-time triaged claims stream with A4 ReAct Agent recommendations and guardrails.
          </p>
        </div>
        <div className="flex items-center space-x-2">
          <button
            onClick={fetchClaims}
            className="flex items-center space-x-1.5 px-3 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-xs font-medium border border-slate-700 transition"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>
          <button
            onClick={onNavigateFNOL}
            className="flex items-center space-x-1.5 px-3.5 py-2 bg-sky-600 hover:bg-sky-500 text-white rounded-lg text-xs font-medium transition shadow-sm"
          >
            <span>+ Ingest FNOL</span>
          </button>
        </div>
      </div>

      {/* Filter & Search Bar */}
      <div className="bg-slate-900 p-4 rounded-xl border border-slate-800 flex flex-col md:flex-row items-stretch md:items-center justify-between gap-3">
        {/* Status Tabs */}
        <div className="flex flex-wrap items-center gap-1.5 text-xs">
          {[
            { id: 'all', label: 'All Claims' },
            { id: 'awaiting_review', label: 'Needs Review' },
            { id: 'registered', label: 'Registered' },
            { id: 'approved', label: 'Approved' },
            { id: 'settled', label: 'Settled' },
            { id: 'rejected', label: 'Rejected' },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setStatusFilter(tab.id)}
              className={`px-3 py-1.5 rounded-lg font-medium transition ${
                statusFilter === tab.id
                  ? 'bg-sky-500/20 text-sky-300 border border-sky-500/40'
                  : 'text-slate-400 hover:text-white hover:bg-slate-800'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Search */}
        <form onSubmit={handleSearchSubmit} className="relative min-w-[260px]">
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search claim or policy..."
            className="w-full pl-9 pr-3 py-1.5 bg-slate-800 border border-slate-700 rounded-lg text-xs text-white placeholder-slate-400 focus:outline-none focus:border-sky-500"
          />
          <Search className="h-4 w-4 text-slate-500 absolute left-3 top-2 pointer-events-none" />
        </form>
      </div>

      {/* Error state */}
      {error && (
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-sm flex items-center space-x-2">
          <AlertCircle className="h-5 w-5 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Table */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-800/80 text-slate-400 uppercase tracking-wider font-semibold border-b border-slate-800">
              <tr>
                <th className="py-3 px-4">Claim ID</th>
                <th className="py-3 px-4">Policy</th>
                <th className="py-3 px-4">Product</th>
                <th className="py-3 px-4">Incident Date</th>
                <th className="py-3 px-4 text-right">Claimed (AZN)</th>
                <th className="py-3 px-4 text-center">A4 AI Recommendation</th>
                <th className="py-3 px-4 text-center">Confidence</th>
                <th className="py-3 px-4 text-center">Autonomy</th>
                <th className="py-3 px-4 text-center">Status</th>
                <th className="py-3 px-4 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800 text-slate-300">
              {loading ? (
                <tr>
                  <td colSpan={10} className="py-8 text-center text-slate-500">
                    Loading claims stream...
                  </td>
                </tr>
              ) : claims.length === 0 ? (
                <tr>
                  <td colSpan={10} className="py-12 text-center text-slate-500">
                    <p className="text-sm">No claims found matching active filter.</p>
                    <p className="text-xs text-slate-600 mt-1">Submit an FNOL or change filter to inspect cases.</p>
                  </td>
                </tr>
              ) : (
                claims.map((claim) => (
                  <tr
                    key={claim.id}
                    className="hover:bg-slate-800/50 transition cursor-pointer group"
                    onClick={() => onSelectClaim(claim.claim_number)}
                  >
                    <td className="py-3.5 px-4 font-mono font-semibold text-sky-400 group-hover:underline">
                      {claim.claim_number}
                    </td>
                    <td className="py-3.5 px-4 font-mono text-slate-300">{claim.policy_number}</td>
                    <td className="py-3.5 px-4">
                      <span className="px-1.5 py-0.5 rounded bg-slate-800 border border-slate-700 text-slate-300 text-[11px]">
                        {claim.product_code}
                      </span>
                    </td>
                    <td className="py-3.5 px-4 text-slate-400">{claim.incident_date}</td>
                    <td className="py-3.5 px-4 text-right font-semibold text-white font-mono">
                      {claim.claimed_amount.toLocaleString('en-US', { minimumFractionDigits: 2 })}
                    </td>
                    <td className="py-3.5 px-4 text-center">
                      {claim.recommendation ? (
                        <Badge type="recommendation" value={claim.recommendation} size="sm" />
                      ) : (
                        <span className="text-slate-500 italic text-[11px]">Untriaged</span>
                      )}
                    </td>
                    <td className="py-3.5 px-4 text-center font-mono">
                      {claim.confidence_score !== null && claim.confidence_score !== undefined ? (
                        <span
                          className={`font-semibold ${
                            claim.confidence_score >= 0.85
                              ? 'text-emerald-400'
                              : claim.confidence_score >= 0.70
                              ? 'text-amber-400'
                              : 'text-rose-400'
                          }`}
                        >
                          {(claim.confidence_score * 100).toFixed(0)}%
                        </span>
                      ) : (
                        <span className="text-slate-600">—</span>
                      )}
                    </td>
                    <td className="py-3.5 px-4 text-center">
                      <Badge type="autonomy" value={claim.autonomy_level} size="sm" />
                    </td>
                    <td className="py-3.5 px-4 text-center">
                      <Badge type="status" value={claim.status} size="sm" />
                    </td>
                    <td className="py-3.5 px-4 text-right">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          onSelectClaim(claim.claim_number);
                        }}
                        className="inline-flex items-center space-x-1 text-sky-400 hover:text-sky-300 font-semibold group-hover:translate-x-0.5 transition"
                      >
                        <span>Inspect</span>
                        <ArrowUpRight className="h-3.5 w-3.5" />
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
