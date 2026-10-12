import React from 'react';
import {
  Shield,
  FileText,
  CheckCircle2,
  History,
  BarChart3,
  LogOut,
  PlusCircle,
  Calculator,
  Scale,
  DollarSign,
  RefreshCw,
  ShieldAlert,
  AlertTriangle,
  Headphones,
} from 'lucide-react';
import { UserProfile } from '../types';

interface HeaderProps {
  activeTab: string;
  onTabChange: (tab: string) => void;
  user: UserProfile | null;
  onLogout: () => void;
  isBackendOnline: boolean;
}

export const Header: React.FC<HeaderProps> = ({
  activeTab,
  onTabChange,
  user,
  onLogout,
  isBackendOnline,
}) => {
  const navItems = [
    { id: 'quotes', label: 'Quotes (A1)', icon: Calculator },
    { id: 'underwriting', label: 'UW (A2)', icon: Scale },
    { id: 'claims', label: 'Claims', icon: CheckCircle2 },
    { id: 'finance', label: 'Finance', icon: DollarSign },
    { id: 'renewals', label: 'Renewals (A7)', icon: RefreshCw },
    { id: 'siu', label: 'SIU (A5)', icon: ShieldAlert },
    { id: 'compliance', label: 'Compliance (A8)', icon: AlertTriangle },
    { id: 'service', label: 'Service (A6/A3)', icon: Headphones },
    { id: 'fnol', label: 'Submit FNOL', icon: PlusCircle },
    { id: 'policies', label: 'Policies', icon: FileText },
    { id: 'audit', label: 'Audit', icon: History },
    { id: 'metrics', label: 'Metrics', icon: BarChart3 },
  ];

  return (
    <header className="bg-slate-900 border-b border-slate-800 text-white sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo & Platform Name */}
          <div className="flex items-center space-x-3 cursor-pointer" onClick={() => onTabChange('claims')}>
            <div className="h-10 w-10 rounded-lg bg-sky-500/20 border border-sky-400 flex items-center justify-center text-sky-400">
              <Shield className="h-6 w-6" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="font-bold text-lg text-white tracking-tight">InsurAI</span>
                <span className="text-[10px] uppercase font-semibold tracking-wider px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                  Release R2
                </span>
              </div>
              <p className="text-xs text-slate-400">Autonomous P&C Insurance Platform</p>
            </div>
          </div>

          {/* Navigation Links */}
          <nav className="hidden md:flex space-x-1">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = activeTab === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => onTabChange(item.id)}
                  className={`flex items-center space-x-2 px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                    isActive
                      ? 'bg-sky-600 text-white shadow'
                      : 'text-slate-300 hover:bg-slate-800 hover:text-white'
                  }`}
                >
                  <Icon className="h-4 w-4" />
                  <span>{item.label}</span>
                </button>
              );
            })}
          </nav>

          {/* User profile & backend status */}
          <div className="flex items-center space-x-4">
            {/* System Health */}
            <div className="flex items-center space-x-1.5 text-xs text-slate-300 bg-slate-800/80 px-2.5 py-1 rounded-full border border-slate-700">
              <span
                className={`h-2 w-2 rounded-full ${
                  isBackendOnline ? 'bg-emerald-400 animate-pulse' : 'bg-rose-400'
                }`}
              />
              <span className="hidden sm:inline">
                {isBackendOnline ? 'API Connected' : 'API Offline'}
              </span>
            </div>

            {user && (
              <div className="flex items-center space-x-3">
                <div className="text-right hidden sm:block">
                  <div className="text-xs font-semibold text-white">{user.full_name || user.username}</div>
                  <div className="text-[11px] text-sky-400 capitalize font-mono">{user.role}</div>
                </div>
                <button
                  onClick={onLogout}
                  title="Sign Out"
                  className="p-1.5 rounded-lg text-slate-400 hover:text-rose-400 hover:bg-slate-800 transition"
                >
                  <LogOut className="h-4 w-4" />
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </header>
  );
};
