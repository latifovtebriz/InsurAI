import React from 'react';
import { AlertTriangle, CheckCircle, Clock, ShieldAlert, Sparkles, XCircle } from 'lucide-react';

interface BadgeProps {
  type: 'status' | 'recommendation' | 'autonomy' | 'risk' | 'flag';
  value: string;
  size?: 'sm' | 'md';
}

export const Badge: React.FC<BadgeProps> = ({ type, value, size = 'md' }) => {
  const sizeClasses = size === 'sm' ? 'px-2 py-0.5 text-[11px]' : 'px-2.5 py-1 text-xs';

  if (type === 'recommendation') {
    switch (value?.toLowerCase()) {
      case 'approve':
        return (
          <span className={`inline-flex items-center space-x-1 font-semibold rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 ${sizeClasses}`}>
            <CheckCircle className="h-3.5 w-3.5" />
            <span>Approve Payout</span>
          </span>
        );
      case 'reject':
        return (
          <span className={`inline-flex items-center space-x-1 font-semibold rounded-full bg-rose-500/10 text-rose-400 border border-rose-500/30 ${sizeClasses}`}>
            <XCircle className="h-3.5 w-3.5" />
            <span>Repudiate Claim</span>
          </span>
        );
      case 'needs_human_review':
      default:
        return (
          <span className={`inline-flex items-center space-x-1 font-semibold rounded-full bg-amber-500/10 text-amber-400 border border-amber-500/30 ${sizeClasses}`}>
            <AlertTriangle className="h-3.5 w-3.5" />
            <span>Human Review Req.</span>
          </span>
        );
    }
  }

  if (type === 'autonomy') {
    if (value === 'L3') {
      return (
        <span className={`inline-flex items-center space-x-1 font-semibold rounded-full bg-purple-500/15 text-purple-300 border border-purple-500/40 ${sizeClasses}`}>
          <Sparkles className="h-3 w-3" />
          <span>L3 Auto-Approve</span>
        </span>
      );
    }
    return (
      <span className={`inline-flex items-center space-x-1 font-semibold rounded-full bg-blue-500/10 text-blue-300 border border-blue-500/30 ${sizeClasses}`}>
        <Clock className="h-3 w-3" />
        <span>L2 Copilot</span>
      </span>
    );
  }

  if (type === 'risk') {
    return (
      <span className={`inline-flex items-center space-x-1 font-semibold rounded-full bg-rose-950/60 text-rose-300 border border-rose-800 ${sizeClasses}`}>
        <ShieldAlert className="h-3 w-3" />
        <span>{value}</span>
      </span>
    );
  }

  // General Status Badge
  const getStatusColor = (st: string) => {
    switch (st?.toLowerCase()) {
      case 'settled':
      case 'active':
      case 'approved':
        return 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30';
      case 'triage_in_progress':
      case 'under_triage':
        return 'bg-sky-500/10 text-sky-400 border-sky-500/30 animate-pulse';
      case 'awaiting_review':
      case 'pending_payment':
      case 'registered':
      case 'fnol_received':
        return 'bg-amber-500/10 text-amber-400 border-amber-500/30';
      case 'rejected':
      case 'cancelled':
        return 'bg-rose-500/10 text-rose-400 border-rose-500/30';
      default:
        return 'bg-slate-700 text-slate-300 border-slate-600';
    }
  };

  return (
    <span className={`inline-flex items-center font-medium rounded-full border uppercase tracking-wider ${getStatusColor(value)} ${sizeClasses}`}>
      {value.replace(/_/g, ' ')}
    </span>
  );
};
