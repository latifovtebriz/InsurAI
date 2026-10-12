import React, { useEffect, useState } from 'react';
import { api } from '../api/client';
import { FinancialKpiResponse, GeneralLedgerTransactionItem, InvoiceItem, LedgerCheckResponse, ReinsuranceTreatyItem } from '../types';

export const FinanceScreen: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'invoices' | 'ledger' | 'reinsurance'>('invoices');
  const [invoices, setInvoices] = useState<InvoiceItem[]>([]);
  const [ledgerTx, setLedgerTx] = useState<GeneralLedgerTransactionItem[]>([]);
  const [ledgerCheck, setLedgerCheck] = useState<LedgerCheckResponse | null>(null);
  const [kpis, setKpis] = useState<FinancialKpiResponse | null>(null);
  const [treaties, setTreaties] = useState<ReinsuranceTreatyItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [actionMsg, setActionMsg] = useState<string | null>(null);

  const loadData = async () => {
    setLoading(true);
    try {
      const [invData, txData, chkData, kpiData, treatyData] = await Promise.all([
        api.getInvoices(),
        api.getLedgerTransactions(30),
        api.getLedgerCheck(),
        api.getFinancialKpis(),
        api.getReinsuranceTreaties(),
      ]);
      setInvoices(invData);
      setLedgerTx(txData);
      setLedgerCheck(chkData);
      setKpis(kpiData);
      setTreaties(treatyData);
    } catch (err: unknown) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handlePayInvoice = async (invId: string, amount: number) => {
    try {
      const res = await api.payInvoice(invId, amount);
      setActionMsg(`Payment applied: ${res.payment_reference} (${res.amount} AZN). Double-entry journal posted.`);
      await loadData();
    } catch (err: unknown) {
      const error = err as Error;
      setActionMsg(`Payment failed: ${error.message}`);
    }
  };

  const handleRunDunning = async () => {
    try {
      const res = await api.runDunningJob();
      setActionMsg(`Dunning scan completed: ${res.notices_generated_count} overdue notices evaluated.`);
      await loadData();
    } catch (err: unknown) {
      const error = err as Error;
      setActionMsg(`Dunning error: ${error.message}`);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header & Ledger Status */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Finance & Double-Entry Ledger</h1>
          <p className="text-slate-500 text-sm mt-1">
            Constraint-enforced balanced accounting, premium invoicing, payment intake, and reinsurance treaties.
          </p>
        </div>
        <div className="flex items-center gap-3">
          {ledgerCheck && (
            <div className={`px-4 py-2 rounded-lg font-medium text-sm flex items-center gap-2 ${
              ledgerCheck.is_balanced
                ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                : 'bg-rose-50 text-rose-700 border border-rose-200'
            }`}>
              <span className={`w-2.5 h-2.5 rounded-full ${ledgerCheck.is_balanced ? 'bg-emerald-500' : 'bg-rose-500'}`} />
              <span>{ledgerCheck.is_balanced ? 'Ledger Balanced: Δ = 0.00 AZN' : `Imbalance: ${ledgerCheck.difference} AZN`}</span>
            </div>
          )}
          <button
            onClick={loadData}
            className="px-3 py-2 text-sm font-medium text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-lg transition"
          >
            Refresh
          </button>
        </div>
      </div>

      {actionMsg && (
        <div className="p-4 rounded-lg bg-sky-50 text-sky-800 border border-sky-200 text-sm flex justify-between items-center">
          <span>{actionMsg}</span>
          <button onClick={() => setActionMsg(null)} className="text-sky-600 font-bold ml-4">✕</button>
        </div>
      )}

      {/* KPI Summary Cards */}
      {kpis && (
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
            <span className="text-xs font-semibold uppercase text-slate-400">Gross Written Premium</span>
            <div className="text-xl font-bold text-slate-900 mt-1">{kpis.gross_written_premium.toLocaleString()} AZN</div>
            <span className="text-xs text-slate-500">In-force portfolio</span>
          </div>
          <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
            <span className="text-xs font-semibold uppercase text-slate-400">Incurred Losses</span>
            <div className="text-xl font-bold text-slate-900 mt-1">{kpis.incurred_losses.toLocaleString()} AZN</div>
            <span className="text-xs text-slate-500">Claims settled & reserves</span>
          </div>
          <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
            <span className="text-xs font-semibold uppercase text-slate-400">Loss Ratio</span>
            <div className={`text-xl font-bold mt-1 ${kpis.loss_ratio_pct > 70 ? 'text-rose-600' : 'text-emerald-600'}`}>
              {kpis.loss_ratio_pct.toFixed(1)}%
            </div>
            <span className="text-xs text-slate-500">Incurred / GWP</span>
          </div>
          <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
            <span className="text-xs font-semibold uppercase text-slate-400">Combined Ratio</span>
            <div className={`text-xl font-bold mt-1 ${kpis.combined_ratio_pct > 100 ? 'text-rose-600' : 'text-emerald-600'}`}>
              {kpis.combined_ratio_pct.toFixed(1)}%
            </div>
            <span className="text-xs text-slate-500">{kpis.combined_ratio_pct < 100 ? 'Underwriting Profit' : 'Underwriting Loss'}</span>
          </div>
          <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
            <span className="text-xs font-semibold uppercase text-slate-400">Operating Cash</span>
            <div className="text-xl font-bold text-indigo-600 mt-1">{kpis.cash_balance.toLocaleString()} AZN</div>
            <span className="text-xs text-slate-500">Account 1010 Bank Cash</span>
          </div>
        </div>
      )}

      {/* Navigation Tabs */}
      <div className="flex border-b border-slate-200">
        <button
          onClick={() => setActiveTab('invoices')}
          className={`py-3 px-6 text-sm font-semibold border-b-2 transition ${
            activeTab === 'invoices'
              ? 'border-indigo-600 text-indigo-600'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          Invoices & Payments ({invoices.length})
        </button>
        <button
          onClick={() => setActiveTab('ledger')}
          className={`py-3 px-6 text-sm font-semibold border-b-2 transition ${
            activeTab === 'ledger'
              ? 'border-indigo-600 text-indigo-600'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          General Ledger Journal ({ledgerTx.length})
        </button>
        <button
          onClick={() => setActiveTab('reinsurance')}
          className={`py-3 px-6 text-sm font-semibold border-b-2 transition ${
            activeTab === 'reinsurance'
              ? 'border-indigo-600 text-indigo-600'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          Reinsurance Treaties ({treaties.length})
        </button>
      </div>

      {loading ? (
        <div className="p-12 text-center text-slate-500">Loading financial records...</div>
      ) : activeTab === 'invoices' ? (
        <div className="space-y-4">
          <div className="flex justify-between items-center">
            <h2 className="text-base font-semibold text-slate-800">Premium Installment Invoices</h2>
            <button
              onClick={handleRunDunning}
              className="px-3 py-1.5 text-xs font-medium bg-amber-500 hover:bg-amber-600 text-white rounded-lg transition"
            >
              Run Automated Dunning Check
            </button>
          </div>
          <div className="bg-white rounded-xl border border-slate-200 overflow-hidden shadow-sm">
            <table className="w-full text-left text-sm text-slate-600">
              <thead className="bg-slate-50 text-slate-700 font-semibold border-b border-slate-200">
                <tr>
                  <th className="p-4">Invoice #</th>
                  <th className="p-4">Policy Number</th>
                  <th className="p-4">Installment</th>
                  <th className="p-4">Amount</th>
                  <th className="p-4">Due Date</th>
                  <th className="p-4">Status</th>
                  <th className="p-4">Dunning</th>
                  <th className="p-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {invoices.length === 0 ? (
                  <tr>
                    <td colSpan={8} className="p-6 text-center text-slate-400">No invoices recorded yet.</td>
                  </tr>
                ) : (
                  invoices.map((inv) => (
                    <tr key={inv.id} className="hover:bg-slate-50">
                      <td className="p-4 font-mono font-medium text-slate-900">{inv.invoice_number}</td>
                      <td className="p-4 font-medium text-indigo-600">{inv.policy_number}</td>
                      <td className="p-4">#{inv.installment_number}</td>
                      <td className="p-4 font-semibold text-slate-900">{inv.amount.toLocaleString()} AZN</td>
                      <td className="p-4 text-slate-500">{inv.due_date}</td>
                      <td className="p-4">
                        <span className={`px-2 py-0.5 rounded text-xs font-semibold ${
                          inv.status === 'paid'
                            ? 'bg-emerald-100 text-emerald-800'
                            : inv.status === 'overdue'
                            ? 'bg-rose-100 text-rose-800'
                            : 'bg-amber-100 text-amber-800'
                        }`}>
                          {inv.status.toUpperCase()}
                        </span>
                      </td>
                      <td className="p-4">
                        {inv.dunning_level > 0 ? (
                          <span className="text-xs font-bold text-rose-600">Level {inv.dunning_level} (T+{inv.dunning_level * 7})</span>
                        ) : (
                          <span className="text-xs text-slate-400">Current</span>
                        )}
                      </td>
                      <td className="p-4 text-right">
                        {inv.status !== 'paid' && (
                          <button
                            onClick={() => handlePayInvoice(inv.id, inv.amount)}
                            className="px-3 py-1 text-xs font-medium bg-emerald-600 hover:bg-emerald-700 text-white rounded transition shadow-sm"
                          >
                            Simulate Pay
                          </button>
                        )}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      ) : activeTab === 'ledger' ? (
        <div className="space-y-4">
          <div className="flex justify-between items-center">
            <h2 className="text-base font-semibold text-slate-800">Double-Entry Journal Ledger</h2>
            <span className="text-xs text-slate-500">Debits strictly equal Credits across all rows</span>
          </div>
          <div className="space-y-3">
            {ledgerTx.map((tx) => (
              <div key={tx.id} className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-3 border-b border-slate-100 gap-2">
                  <div>
                    <span className="font-mono text-sm font-bold text-slate-900">{tx.transaction_number}</span>
                    <span className="ml-3 px-2 py-0.5 rounded text-xs font-semibold bg-slate-100 text-slate-700">
                      {tx.reference_type}
                    </span>
                    <p className="text-xs text-slate-500 mt-0.5">{tx.description}</p>
                  </div>
                  <div className="text-right">
                    <span className="text-sm font-bold text-slate-900">{tx.total_amount.toLocaleString()} AZN</span>
                    <p className="text-xs text-slate-400">{tx.transaction_date}</p>
                  </div>
                </div>
                <div className="mt-3 grid grid-cols-1 md:grid-cols-2 gap-2 text-xs">
                  {tx.entries.map((e, idx) => (
                    <div
                      key={idx}
                      className={`p-2 rounded border flex justify-between items-center ${
                        e.debit > 0
                          ? 'bg-blue-50/50 border-blue-100 text-blue-900'
                          : 'bg-emerald-50/50 border-emerald-100 text-emerald-900'
                      }`}
                    >
                      <span>
                        <strong className="font-mono">Account {e.account_code}</strong>
                      </span>
                      <span>
                        {e.debit > 0 ? `Debit: ${e.debit.toFixed(2)} AZN` : `Credit: ${e.credit.toFixed(2)} AZN`}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      ) : (
        <div className="space-y-4">
          <h2 className="text-base font-semibold text-slate-800">Market Reinsurance Treaties (P13)</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {treaties.map((tr) => (
              <div key={tr.id} className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm space-y-3">
                <div className="flex justify-between items-start">
                  <div>
                    <span className="font-mono text-xs font-bold text-indigo-600">{tr.treaty_code}</span>
                    <h3 className="font-semibold text-slate-900 mt-1">{tr.treaty_name}</h3>
                  </div>
                  <span className="px-2 py-0.5 rounded text-xs font-semibold bg-indigo-50 text-indigo-700">
                    {tr.treaty_type}
                  </span>
                </div>
                <div className="text-xs space-y-1.5 text-slate-600 pt-2 border-t border-slate-100">
                  <div className="flex justify-between">
                    <span>Reinsurer:</span>
                    <strong className="text-slate-900">{tr.reinsurer_name}</strong>
                  </div>
                  <div className="flex justify-between">
                    <span>Ceded Share:</span>
                    <strong className="text-slate-900">{(tr.ceded_share_pct * 100).toFixed(0)}%</strong>
                  </div>
                  <div className="flex justify-between">
                    <span>Retention:</span>
                    <strong className="text-slate-900">{tr.retention_amount > 0 ? `${tr.retention_amount.toLocaleString()} AZN` : `${(tr.retention_share_pct * 100).toFixed(0)}%`}</strong>
                  </div>
                  <div className="flex justify-between">
                    <span>Treaty Limit:</span>
                    <strong className="text-slate-900">{tr.treaty_limit.toLocaleString()} AZN</strong>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
