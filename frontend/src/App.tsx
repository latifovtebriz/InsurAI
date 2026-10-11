import React from 'react';

export default function App(): React.JSX.Element {
  return (
    <div className="min-h-screen bg-slate-900 text-white flex flex-col items-center justify-center p-6">
      <div className="max-w-xl text-center space-y-4">
        <h1 className="text-4xl font-bold tracking-tight text-blue-400">InsurAI Console</h1>
        <p className="text-slate-300">
          Autonomous Agentic Core Insurance Platform for Property & Casualty.
        </p>
        <div className="p-4 rounded-lg bg-slate-800 border border-slate-700 text-sm text-left font-mono">
          <div>Status: Core Skeleton Online</div>
          <div>API Target: http://localhost:8000</div>
        </div>
      </div>
    </div>
  );
}
