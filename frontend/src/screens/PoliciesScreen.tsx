import React, { useEffect, useState } from 'react';
import { Search, RefreshCw, FileText, X, Hash } from 'lucide-react';
import { api } from '../api/client';
import { PolicyDetail, PolicyListItem } from '../types';
import { Badge } from '../components/Badge';

export const PoliciesScreen: React.FC = () => {
  const [policies, setPolicies] = useState<PolicyListItem[]>([]);
  const [selectedPolicy, setSelectedPolicy] = useState<PolicyDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [error, setError] = useState<string | null>(null);

  const fetchPolicies = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.listPolicies(search || undefined);
      setPolicies(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load policies');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPolicies();
  }, []);

  const handleSelectPolicy = async (policyNumber: string) => {
    try {
      const detail = await api.getPolicy(policyNumber);
      setSelectedPolicy(detail);
    } catch (err: any) {
      alert(`Could not load policy details: ${err.message}`);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Policy Registry & Certificates</h1>
          <p className="text-sm text-slate-400">
            Active underwriting contracts, payment schedules, and cryptographic certificates of insurance.
          </p>
        </div>
        <button
          onClick={fetchPolicies}
          className="flex items-center space-x-1.5 px-3 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-xs font-medium border border-slate-700 transition"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} />
          <span>Refresh</span>
        </button>
      </div>

      {/* Search */}
      <div className="bg-slate-900 p-4 rounded-xl border border-slate-800">
        <div className="relative max-w-md">
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && fetchPolicies()}
            placeholder="Search by policy number or product code..."
            className="w-full pl-9 pr-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-xs text-white placeholder-slate-400 focus:outline-none focus:border-sky-500"
          />
          <Search className="h-4 w-4 text-slate-500 absolute left-3 top-2.5 pointer-events-none" />
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs">
          {error}
        </div>
      )}

      {/* Table */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-800/80 text-slate-400 uppercase tracking-wider font-semibold border-b border-slate-800">
              <tr>
                <th className="py-3 px-4">Policy Number</th>
                <th className="py-3 px-4">Policyholder</th>
                <th className="py-3 px-4">Product</th>
                <th className="py-3 px-4">Inception</th>
                <th className="py-3 px-4">Expiry</th>
                <th className="py-3 px-4 text-right">Sum Insured (AZN)</th>
                <th className="py-3 px-4 text-right">Total Premium</th>
                <th className="py-3 px-4 text-center">Status</th>
                <th className="py-3 px-4 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800 text-slate-300">
              {loading ? (
                <tr>
                  <td colSpan={9} className="py-8 text-center text-slate-500">
                    Loading policies...
                  </td>
                </tr>
              ) : policies.length === 0 ? (
                <tr>
                  <td colSpan={9} className="py-8 text-center text-slate-500">
                    No policies found.
                  </td>
                </tr>
              ) : (
                policies.map((pol) => (
                  <tr
                    key={pol.id}
                    className="hover:bg-slate-800/50 transition cursor-pointer group"
                    onClick={() => handleSelectPolicy(pol.policy_number)}
                  >
                    <td className="py-3.5 px-4 font-mono font-semibold text-sky-400 group-hover:underline">
                      {pol.policy_number}
                    </td>
                    <td className="py-3.5 px-4 text-white font-medium">
                      {pol.holder_name || <span className="text-slate-500 italic">Unknown</span>}
                    </td>
                    <td className="py-3.5 px-4">
                      <span className="px-1.5 py-0.5 rounded bg-slate-800 border border-slate-700 text-slate-300 text-[11px]">
                        {pol.product_code}
                      </span>
                    </td>
                    <td className="py-3.5 px-4 text-slate-400">{pol.start_date}</td>
                    <td className="py-3.5 px-4 text-slate-400">{pol.end_date}</td>
                    <td className="py-3.5 px-4 text-right font-mono font-semibold text-white">
                      {pol.sum_insured.toLocaleString('en-US', { minimumFractionDigits: 2 })}
                    </td>
                    <td className="py-3.5 px-4 text-right font-mono text-emerald-400">
                      {pol.total_premium.toLocaleString('en-US', { minimumFractionDigits: 2 })}
                    </td>
                    <td className="py-3.5 px-4 text-center">
                      <Badge type="status" value={pol.status} size="sm" />
                    </td>
                    <td className="py-3.5 px-4 text-right">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleSelectPolicy(pol.policy_number);
                        }}
                        className="text-sky-400 hover:text-sky-300 font-semibold"
                      >
                        Inspect
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Policy Detail Modal */}
      {selectedPolicy && (
        <div className="fixed inset-0 bg-black/80 flex items-center justify-center p-4 z-50">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-2xl w-full max-h-[85vh] flex flex-col shadow-2xl overflow-hidden text-xs">
            <div className="p-4 border-b border-slate-800 flex items-center justify-between bg-slate-950">
              <div className="flex items-center space-x-2">
                <FileText className="h-5 w-5 text-sky-400" />
                <h3 className="text-sm font-bold text-white">
                  Policy Contract: <span className="font-mono">{selectedPolicy.policy_number}</span>
                </h3>
              </div>
              <button
                onClick={() => setSelectedPolicy(null)}
                className="text-slate-400 hover:text-white p-1 rounded-lg"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <div className="p-6 overflow-y-auto space-y-5 text-slate-300">
              {/* Holder & Certificate Hash */}
              <div className="grid grid-cols-2 gap-4 bg-slate-950 p-4 rounded-xl border border-slate-800">
                <div>
                  <div className="text-slate-500 text-[11px] uppercase font-semibold">Policyholder</div>
                  <div className="text-white font-bold text-sm mt-0.5">
                    {selectedPolicy.holder_info?.full_name || 'Individual Insured'}
                  </div>
                  <div className="text-slate-400 text-[11px]">
                    FIN/TIN: {selectedPolicy.holder_info?.tax_id || 'N/A'} • {selectedPolicy.holder_info?.phone}
                  </div>
                </div>
                <div>
                  <div className="text-slate-500 text-[11px] uppercase font-semibold">Contract Status</div>
                  <div className="mt-1">
                    <Badge type="status" value={selectedPolicy.status} />
                  </div>
                  <div className="text-slate-400 text-[11px] mt-1">
                    Coverage: {selectedPolicy.start_date} to {selectedPolicy.end_date}
                  </div>
                </div>
              </div>

              {/* Financial Terms */}
              <div className="grid grid-cols-3 gap-3">
                <div className="bg-slate-950 p-3 rounded-lg border border-slate-800">
                  <div className="text-slate-500 text-[11px]">Sum Insured</div>
                  <div className="font-mono font-bold text-white text-sm mt-0.5">
                    {selectedPolicy.sum_insured.toLocaleString()} AZN
                  </div>
                </div>
                <div className="bg-slate-950 p-3 rounded-lg border border-slate-800">
                  <div className="text-slate-500 text-[11px]">Deductible</div>
                  <div className="font-mono font-bold text-amber-400 text-sm mt-0.5">
                    {selectedPolicy.deductible.toFixed(2)} AZN
                  </div>
                </div>
                <div className="bg-slate-950 p-3 rounded-lg border border-slate-800">
                  <div className="text-slate-500 text-[11px]">Total Premium</div>
                  <div className="font-mono font-bold text-emerald-400 text-sm mt-0.5">
                    {selectedPolicy.total_premium.toFixed(2)} AZN
                  </div>
                </div>
              </div>

              {/* Certificate Hash */}
              {selectedPolicy.certificate_hash && (
                <div className="bg-slate-950 p-3.5 rounded-lg border border-slate-800 space-y-1">
                  <div className="text-sky-400 font-semibold flex items-center space-x-1.5 text-[11px]">
                    <Hash className="h-3.5 w-3.5" />
                    <span>Cryptographic Certificate Integrity Digest (SHA-256)</span>
                  </div>
                  <div className="font-mono text-[11px] text-slate-400 break-all bg-slate-900 p-2 rounded border border-slate-800">
                    {selectedPolicy.certificate_hash}
                  </div>
                </div>
              )}

              {/* Installment Schedule */}
              <div className="space-y-2">
                <div className="text-xs font-semibold text-white uppercase tracking-wider">
                  Payment Installment Schedule
                </div>
                {selectedPolicy.payment_schedule.length === 0 ? (
                  <p className="text-slate-500 italic text-[11px]">Single annual settlement.</p>
                ) : (
                  <div className="divide-y divide-slate-800 border border-slate-800 rounded-lg overflow-hidden">
                    {selectedPolicy.payment_schedule.map((inst, i) => (
                      <div key={i} className="p-2.5 bg-slate-950 flex items-center justify-between text-[11px]">
                        <span className="text-slate-400">Due: {inst.due_date}</span>
                        <span className="font-mono font-semibold text-white">{inst.amount.toFixed(2)} AZN</span>
                        <Badge type="status" value={inst.status} size="sm" />
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
