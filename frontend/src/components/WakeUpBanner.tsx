import React from 'react';
import { AlertCircle, RefreshCw } from 'lucide-react';

interface WakeUpBannerProps {
  isChecking: boolean;
  onRetry: () => void;
}

export const WakeUpBanner: React.FC<WakeUpBannerProps> = ({ isChecking, onRetry }) => {
  return (
    <div className="bg-amber-500/10 border-b border-amber-500/30 text-amber-200 px-4 py-3">
      <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-3 text-sm">
        <div className="flex items-center space-x-2 text-center sm:text-left">
          <AlertCircle className="h-5 w-5 text-amber-400 flex-shrink-0" />
          <span>
            <strong>Backend Waking Up:</strong> Connecting to InsurAI core service at <code className="bg-amber-950/40 px-1 py-0.5 rounded text-amber-300">http://localhost:8000</code>.
          </span>
        </div>
        <button
          onClick={onRetry}
          disabled={isChecking}
          className="flex items-center space-x-1.5 bg-amber-500/20 hover:bg-amber-500/30 text-amber-200 border border-amber-500/40 px-3 py-1 rounded text-xs font-medium transition disabled:opacity-50"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${isChecking ? 'animate-spin' : ''}`} />
          <span>{isChecking ? 'Probing...' : 'Check Again'}</span>
        </button>
      </div>
    </div>
  );
};
