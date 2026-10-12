import React, { useEffect, useState } from 'react';
import { api } from './api/client';
import { UserProfile } from './types';
import { Header } from './components/Header';
import { WakeUpBanner } from './components/WakeUpBanner';
import { LoginScreen } from './screens/LoginScreen';
import { ClaimsQueueScreen } from './screens/ClaimsQueueScreen';
import { ClaimDetailScreen } from './screens/ClaimDetailScreen';
import { FNOLIntakeScreen } from './screens/FNOLIntakeScreen';
import { PoliciesScreen } from './screens/PoliciesScreen';
import { QuotesScreen } from './screens/QuotesScreen';
import { UnderwritingScreen } from './screens/UnderwritingScreen';
import { FinanceScreen } from './screens/FinanceScreen';
import { RenewalScreen } from './screens/RenewalScreen';
import { AuditScreen } from './screens/AuditScreen';
import { MetricsScreen } from './screens/MetricsScreen';

export default function App(): React.JSX.Element {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [activeTab, setActiveTab] = useState<string>('claims');
  const [selectedClaimNumber, setSelectedClaimNumber] = useState<string | null>(null);

  // Backend Health Probing
  const [isBackendOnline, setIsBackendOnline] = useState<boolean>(true);
  const [isProbing, setIsProbing] = useState<boolean>(false);
  const [initialLoading, setInitialLoading] = useState<boolean>(true);

  const checkBackendHealth = async () => {
    setIsProbing(true);
    try {
      await api.checkHealth();
      setIsBackendOnline(true);
    } catch {
      setIsBackendOnline(false);
    } finally {
      setIsProbing(false);
    }
  };

  const loadUserProfile = async () => {
    const token = api.getToken();
    if (!token) {
      setInitialLoading(false);
      return;
    }

    try {
      const profile = await api.getMe();
      setUser(profile);
    } catch {
      api.logout();
      setUser(null);
    } finally {
      setInitialLoading(false);
    }
  };

  useEffect(() => {
    checkBackendHealth();
    loadUserProfile();

    // Periodic health heartbeat every 15 seconds
    const interval = setInterval(checkBackendHealth, 15000);
    return () => clearInterval(interval);
  }, []);

  const handleLogout = () => {
    api.logout();
    setUser(null);
    setSelectedClaimNumber(null);
  };

  if (initialLoading) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center text-white">
        <div className="text-center space-y-3">
          <div className="h-8 w-8 border-2 border-sky-500 border-t-transparent rounded-full animate-spin mx-auto" />
          <p className="text-xs text-slate-400 font-mono">Initializing InsurAI Console...</p>
        </div>
      </div>
    );
  }

  if (!user) {
    return <LoginScreen onLoginSuccess={(u) => setUser(u)} />;
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col">
      {!isBackendOnline && (
        <WakeUpBanner isChecking={isProbing} onRetry={checkBackendHealth} />
      )}

      <Header
        activeTab={activeTab}
        onTabChange={(tab) => {
          setActiveTab(tab);
          setSelectedClaimNumber(null);
        }}
        user={user}
        onLogout={handleLogout}
        isBackendOnline={isBackendOnline}
      />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {selectedClaimNumber ? (
          <ClaimDetailScreen
            claimNumber={selectedClaimNumber}
            currentUser={user}
            onBack={() => setSelectedClaimNumber(null)}
            onRefreshQueue={() => {}}
          />
        ) : (
          <>
            {activeTab === 'quotes' && <QuotesScreen />}
            {activeTab === 'underwriting' && <UnderwritingScreen />}
            {activeTab === 'finance' && <FinanceScreen />}
            {activeTab === 'renewals' && <RenewalScreen />}
            {activeTab === 'claims' && (
              <ClaimsQueueScreen
                onSelectClaim={(num) => setSelectedClaimNumber(num)}
                onNavigateFNOL={() => setActiveTab('fnol')}
              />
            )}
            {activeTab === 'fnol' && (
              <FNOLIntakeScreen
                onSuccess={(num) => {
                  setSelectedClaimNumber(num);
                }}
              />
            )}
            {activeTab === 'policies' && <PoliciesScreen />}
            {activeTab === 'audit' && <AuditScreen />}
            {activeTab === 'metrics' && <MetricsScreen />}
          </>
        )}
      </main>
    </div>
  );
}
