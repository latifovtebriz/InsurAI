import React, { useState } from 'react';
import { Shield, Lock, User, ArrowRight } from 'lucide-react';
import { api } from '../api/client';
import { UserProfile } from '../types';

interface LoginScreenProps {
  onLoginSuccess: (user: UserProfile) => void;
}

export const LoginScreen: React.FC<LoginScreenProps> = ({ onLoginSuccess }) => {
  const [username, setUsername] = useState('adjuster');
  const [password, setPassword] = useState('password');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const demoAccounts = [
    {
      name: 'Leyla Mammadova',
      role: 'Claims Adjuster (L2)',
      username: 'adjuster',
      password: 'password',
      badge: 'Operational Role',
    },
    {
      name: 'Farid Huseynov',
      role: 'Senior Claims Lead (Four-Eyes)',
      username: 'senior_adjuster',
      password: 'password',
      badge: 'Supervisory Role',
    },
    {
      name: 'System Administrator',
      role: 'Full Platform Admin',
      username: 'admin',
      password: 'admin',
      badge: 'Admin Access',
    },
    {
      name: 'Eldar Aliyev',
      role: 'Underwriter',
      username: 'underwriter',
      password: 'password',
      badge: 'Product & UW',
    },
  ];

  const handleLogin = async (e?: React.FormEvent, customUser?: string, customPass?: string) => {
    if (e) e.preventDefault();
    setLoading(true);
    setError(null);

    const userToTry = customUser || username;
    const passToTry = customPass || password;

    try {
      await api.login(userToTry, passToTry);
      const profile = await api.getMe();
      onLoginSuccess(profile);
    } catch (err: any) {
      setError(err.message || 'Login failed. Please check credentials.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 flex flex-col justify-center py-12 sm:px-6 lg:px-8 text-white">
      <div className="sm:mx-auto sm:w-full sm:max-w-md text-center">
        <div className="inline-flex h-14 w-14 rounded-2xl bg-sky-500/10 border border-sky-400 items-center justify-center text-sky-400 mb-4 shadow-lg shadow-sky-500/10">
          <Shield className="h-8 w-8" />
        </div>
        <h2 className="text-3xl font-extrabold tracking-tight text-white">InsurAI Console</h2>
        <p className="mt-2 text-sm text-slate-400">
          Enterprise Agentic Core Insurance System (Property & Casualty)
        </p>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
        <div className="bg-slate-900 py-8 px-4 shadow-xl border border-slate-800 sm:rounded-xl sm:px-10">
          {error && (
            <div className="mb-4 bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs p-3 rounded-lg">
              {error}
            </div>
          )}

          {/* Quick Demo Logins */}
          <div className="mb-6">
            <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
              Select Demo Persona (Instant Login)
            </label>
            <div className="space-y-2">
              {demoAccounts.map((acc) => (
                <button
                  key={acc.username}
                  onClick={() => {
                    setUsername(acc.username);
                    setPassword(acc.password);
                    handleLogin(undefined, acc.username, acc.password);
                  }}
                  disabled={loading}
                  className="w-full flex items-center justify-between p-2.5 rounded-lg bg-slate-800/80 hover:bg-slate-800 border border-slate-700 hover:border-sky-500/50 text-left transition text-xs group"
                >
                  <div>
                    <div className="font-semibold text-white group-hover:text-sky-300">{acc.name}</div>
                    <div className="text-slate-400 text-[11px]">{acc.role}</div>
                  </div>
                  <ArrowRight className="h-4 w-4 text-slate-500 group-hover:text-sky-400 group-hover:translate-x-0.5 transition" />
                </button>
              ))}
            </div>
          </div>

          <div className="relative my-6">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-slate-800" />
            </div>
            <div className="relative flex justify-center text-xs">
              <span className="px-2 bg-slate-900 text-slate-500 uppercase tracking-wider">Or Manual Login</span>
            </div>
          </div>

          {/* Form */}
          <form className="space-y-4" onSubmit={handleLogin}>
            <div>
              <label className="block text-xs font-medium text-slate-300">Username</label>
              <div className="mt-1 relative rounded-md shadow-sm">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-500">
                  <User className="h-4 w-4" />
                </div>
                <input
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  required
                  className="block w-full pl-9 pr-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-sm text-white placeholder-slate-500 focus:outline-none focus:border-sky-500"
                  placeholder="adjuster or admin"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-300">Password</label>
              <div className="mt-1 relative rounded-md shadow-sm">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-500">
                  <Lock className="h-4 w-4" />
                </div>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  className="block w-full pl-9 pr-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-sm text-white placeholder-slate-500 focus:outline-none focus:border-sky-500"
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full flex justify-center py-2.5 px-4 border border-transparent rounded-lg shadow-sm text-sm font-medium text-white bg-sky-600 hover:bg-sky-500 focus:outline-none transition disabled:opacity-50"
            >
              {loading ? 'Authenticating...' : 'Sign In'}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
};
