import React, { useEffect, useState } from 'react';
import { RefreshCw, ChevronDown, ChevronRight } from 'lucide-react';
import { api } from '../api/client';
import { AuditEvent } from '../types';

export const AuditScreen: React.FC = () => {
  const [logs, setLogs] = useState<AuditEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [expandedLogId, setExpandedLogId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const fetchLogs = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.listAuditEvents();
      setLogs(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load audit trail');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLogs();
  }, []);

  const toggleExpand = (id: string) => {
    setExpandedLogId((prev) => (prev === id ? null : id));
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Immutable Audit Ledger</h1>
          <p className="text-sm text-slate-400">
            Append-only compliance audit records captured transactionally across domain modules.
          </p>
        </div>
        <button
          onClick={fetchLogs}
          className="flex items-center space-x-1.5 px-3 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-xs font-medium border border-slate-700 transition"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} />
          <span>Refresh</span>
        </button>
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
                <th className="py-3 px-4 w-10"></th>
                <th className="py-3 px-4">Timestamp (UTC)</th>
                <th className="py-3 px-4">Actor</th>
                <th className="py-3 px-4">Action</th>
                <th className="py-3 px-4">Entity Type</th>
                <th className="py-3 px-4">Entity ID</th>
                <th className="py-3 px-4">Correlation ID</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800 text-slate-300">
              {loading ? (
                <tr>
                  <td colSpan={7} className="py-8 text-center text-slate-500">
                    Loading audit trail...
                  </td>
                </tr>
              ) : logs.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-8 text-center text-slate-500">
                    No audit records recorded yet.
                  </td>
                </tr>
              ) : (
                logs.map((log) => {
                  const isExpanded = expandedLogId === log.id;
                  return (
                    <React.Fragment key={log.id}>
                      <tr
                        onClick={() => toggleExpand(log.id)}
                        className="hover:bg-slate-800/50 transition cursor-pointer"
                      >
                        <td className="py-3.5 px-4 text-slate-500">
                          {isExpanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
                        </td>
                        <td className="py-3.5 px-4 font-mono text-slate-400">{log.timestamp}</td>
                        <td className="py-3.5 px-4 font-semibold text-white">{log.user_id || 'system'}</td>
                        <td className="py-3.5 px-4">
                          <span className="px-2 py-0.5 rounded font-mono bg-sky-500/10 text-sky-400 border border-sky-500/20 text-[11px]">
                            {log.action}
                          </span>
                        </td>
                        <td className="py-3.5 px-4 text-slate-300 capitalize">{log.entity_type}</td>
                        <td className="py-3.5 px-4 font-mono text-slate-400">{log.entity_id.slice(0, 8)}...</td>
                        <td className="py-3.5 px-4 font-mono text-slate-500 text-[11px]">
                          {log.correlation_id || '—'}
                        </td>
                      </tr>
                      {isExpanded && (
                        <tr className="bg-slate-950">
                          <td colSpan={7} className="p-4 border-t border-slate-800/60 font-mono text-[11px]">
                            <div className="grid grid-cols-2 gap-4">
                              <div>
                                <div className="text-slate-500 uppercase font-bold text-[10px] mb-1">
                                  Before State
                                </div>
                                <pre className="bg-slate-900 p-2.5 rounded border border-slate-800 text-amber-300/90 overflow-x-auto">
                                  {log.before_state ? JSON.stringify(log.before_state, null, 2) : 'null (initial)'}
                                </pre>
                              </div>
                              <div>
                                <div className="text-slate-500 uppercase font-bold text-[10px] mb-1">
                                  After State
                                </div>
                                <pre className="bg-slate-900 p-2.5 rounded border border-slate-800 text-emerald-300/90 overflow-x-auto">
                                  {log.after_state ? JSON.stringify(log.after_state, null, 2) : 'null'}
                                </pre>
                              </div>
                            </div>
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
