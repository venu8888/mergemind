import React, { useEffect, useState } from 'react';
import { Header } from './components/Header';
import { HealthCard } from './components/HealthCard';
import { fetchSystemHealth } from './services/api';
import type { SystemHealth } from './types';
import { GitBranch, Layers, ShieldAlert, CheckCircle, ArrowRight } from 'lucide-react';

export const App: React.FC = () => {
  const [health, setHealth] = useState<SystemHealth | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const loadHealth = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchSystemHealth();
      setHealth(data);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch health status');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadHealth();
  }, []);

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans">
      <Header />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
        {/* Phase 1 Verification Banner */}
        <div className="bg-gradient-to-r from-indigo-950/40 via-slate-900 to-slate-900 border border-indigo-900/40 rounded-xl p-6">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div className="space-y-1">
              <span className="text-xs font-semibold uppercase tracking-wider text-indigo-400">
                Phase 1 Complete
              </span>
              <h1 className="text-2xl font-bold text-white tracking-tight">
                Project Foundation & Scaffolding
              </h1>
              <p className="text-sm text-slate-400 max-w-2xl">
                The core architectural scaffolding for MergeMind is verified. FastAPI backend,
                asynchronous SQLAlchemy models, Alembic migrations, and React UI shell are connected.
              </p>
            </div>
            <div className="flex items-center gap-3">
              <a
                href="http://localhost:8000/api/v1/docs"
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold transition"
              >
                <span>Interactive OpenAPI Docs</span>
                <ArrowRight className="w-4 h-4" />
              </a>
            </div>
          </div>
        </div>

        {/* Live Backend Health Diagnostic */}
        <HealthCard
          health={health}
          loading={loading}
          error={error}
          onRefresh={loadHealth}
        />

        {/* Architectural Principles & Structural Overview */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 space-y-3">
            <div className="w-9 h-9 rounded-lg bg-emerald-950/60 border border-emerald-800/40 flex items-center justify-center text-emerald-400">
              <CheckCircle className="w-5 h-5" />
            </div>
            <h3 className="text-sm font-semibold text-white">Evidence-Backed Verification</h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              Findings are strictly separated into deterministic proof (Ruff, Bandit), actual test
              execution (Pytest), and contextual AI advisory. No AI assumption is ever presented as confirmed defect.
            </p>
          </div>

          <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 space-y-3">
            <div className="w-9 h-9 rounded-lg bg-cyan-950/60 border border-cyan-800/40 flex items-center justify-center text-cyan-400">
              <ShieldAlert className="w-5 h-5" />
            </div>
            <h3 className="text-sm font-semibold text-white">Fail-Closed Sandbox Security</h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              Untrusted pull-request code is never executed on the host server process. If an isolated container
              sandbox is unavailable, untrusted tests are explicitly disabled rather than run insecurely.
            </p>
          </div>

          <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 space-y-3">
            <div className="w-9 h-9 rounded-lg bg-purple-950/60 border border-purple-800/40 flex items-center justify-center text-purple-400">
              <Layers className="w-5 h-5" />
            </div>
            <h3 className="text-sm font-semibold text-white">Decoupled Quality Gates</h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              Quality Score (0-100) and Verification Completeness (0-100%) are evaluated independently.
              Critical security flaws and broken tests block merges regardless of numerical score.
            </p>
          </div>
        </div>

        {/* Roadmap Preview */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 space-y-4">
          <h2 className="text-sm font-semibold text-white flex items-center gap-2">
            <GitBranch className="w-4 h-4 text-indigo-400" />
            Development Milestone Progression
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="p-3.5 rounded-lg bg-emerald-950/20 border border-emerald-800/40">
              <span className="text-[10px] font-mono text-emerald-400 uppercase font-bold">Phase 1 (Completed)</span>
              <p className="text-xs font-semibold text-white mt-1">Foundation & Scaffolding</p>
              <p className="text-[11px] text-slate-400 mt-1">FastAPI, SQLAlchemy, Alembic, React shell, CI</p>
            </div>
            <div className="p-3.5 rounded-lg bg-slate-850 border border-slate-800">
              <span className="text-[10px] font-mono text-slate-400 uppercase font-bold">Phase 2 (Next)</span>
              <p className="text-xs font-semibold text-slate-300 mt-1">GitHub Integration</p>
              <p className="text-[11px] text-slate-400 mt-1">HMAC Webhooks, deduplication, diff parser</p>
            </div>
            <div className="p-3.5 rounded-lg bg-slate-850 border border-slate-800">
              <span className="text-[10px] font-mono text-slate-400 uppercase font-bold">Phase 3</span>
              <p className="text-xs font-semibold text-slate-300 mt-1">Deterministic Analysis</p>
              <p className="text-[11px] text-slate-400 mt-1">Ruff, Bandit AST scanning, diff line mapping</p>
            </div>
            <div className="p-3.5 rounded-lg bg-slate-850 border border-slate-800">
              <span className="text-[10px] font-mono text-slate-400 uppercase font-bold">Phase 4</span>
              <p className="text-xs font-semibold text-slate-300 mt-1">Test Execution Sandbox</p>
              <p className="text-[11px] text-slate-400 mt-1">Pytest runner, exit code & trace provenance</p>
            </div>
          </div>
        </div>
      </main>

      <footer className="border-t border-slate-800 py-4 text-center text-xs text-slate-500">
        MergeMind Framework &bull; Industry Track B.Tech AIML &bull; Professional Engineering Standard
      </footer>
    </div>
  );
};

export default App;
