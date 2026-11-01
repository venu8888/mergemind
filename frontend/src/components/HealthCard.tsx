import React from 'react';
import { Database, Box, Cpu, RefreshCw } from 'lucide-react';
import type { SystemHealth } from '../types';
import { StatusBadge } from './StatusBadge';

interface HealthCardProps {
  health: SystemHealth | null;
  loading: boolean;
  error: string | null;
  onRefresh: () => void;
}

export const HealthCard: React.FC<HealthCardProps> = ({
  health,
  loading,
  error,
  onRefresh,
}) => {
  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl">
      <div className="flex items-center justify-between pb-5 border-b border-slate-800">
        <div>
          <h2 className="text-base font-semibold text-white">System Foundation Health</h2>
          <p className="text-xs text-slate-400 mt-0.5">
            Phase 1 Scaffolding & Live Infrastructure Connectivity
          </p>
        </div>
        <div className="flex items-center space-x-3">
          {health ? (
            <StatusBadge status={health.status} />
          ) : error ? (
            <StatusBadge status="error" label="Backend Offline" />
          ) : (
            <StatusBadge status="pending" />
          )}
          <button
            onClick={onRefresh}
            disabled={loading}
            className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-white transition border border-slate-700 disabled:opacity-50"
            title="Refresh Status"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {error ? (
        <div className="mt-5 p-4 rounded-lg bg-rose-950/30 border border-rose-900/50 text-rose-300 text-sm">
          <p className="font-medium">Failed to communicate with FastAPI backend:</p>
          <p className="text-xs font-mono mt-1 text-rose-400">{error}</p>
          <p className="text-xs mt-2 text-slate-400">
            Ensure backend server is running (`uvicorn app.main:app --reload`).
          </p>
        </div>
      ) : health ? (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-5">
          <div className="p-4 rounded-lg bg-slate-800/40 border border-slate-800 flex flex-col justify-between">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-slate-400">Database Engine</span>
              <Database className="w-4 h-4 text-indigo-400" />
            </div>
            <div className="mt-3">
              <div className="flex items-center gap-2">
                <div
                  className={`w-2 h-2 rounded-full ${
                    health.database.connected ? 'bg-emerald-400' : 'bg-rose-400'
                  }`}
                />
                <span className="text-sm font-semibold text-white">
                  {health.database.connected ? 'Connected' : 'Disconnected'}
                </span>
              </div>
              <p className="text-xs font-mono text-slate-400 mt-1">
                Driver: {health.database.url_driver}
              </p>
            </div>
          </div>

          <div className="p-4 rounded-lg bg-slate-800/40 border border-slate-800 flex flex-col justify-between">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-slate-400">Execution Sandbox</span>
              <Box className="w-4 h-4 text-cyan-400" />
            </div>
            <div className="mt-3">
              <div className="flex items-center gap-2">
                <span className="text-xs px-2 py-0.5 rounded bg-cyan-950 text-cyan-300 border border-cyan-800/50 font-mono font-medium">
                  {health.sandbox.mode.toUpperCase()}
                </span>
                <span className="text-xs text-slate-400">
                  {health.sandbox.mode === 'container' ? 'Container Isolation' : 'Fail-Closed Disabled'}
                </span>
              </div>
              <p className="text-xs text-slate-400 mt-1 font-mono">
                Timeout: {health.sandbox.timeout_seconds}s | RAM: {health.sandbox.max_memory_mb}MB
              </p>
            </div>
          </div>

          <div className="p-4 rounded-lg bg-slate-800/40 border border-slate-800 flex flex-col justify-between">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-slate-400">Environment</span>
              <Cpu className="w-4 h-4 text-amber-400" />
            </div>
            <div className="mt-3">
              <span className="text-sm font-semibold text-white capitalize">
                {health.environment}
              </span>
              <p className="text-xs text-slate-400 mt-1 font-mono">
                {new Date(health.timestamp).toLocaleTimeString()}
              </p>
            </div>
          </div>
        </div>
      ) : (
        <div className="py-8 text-center text-slate-400 text-sm">
          Loading system health diagnostics...
        </div>
      )}
    </div>
  );
};
