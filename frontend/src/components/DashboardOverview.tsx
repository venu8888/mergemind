import React from 'react';
import {
  CheckCircle2,
  ArrowUpRight,
  Sparkles,
  TrendingUp,
} from 'lucide-react';
import type { RepositoryDashboard } from '../types';

interface DashboardOverviewProps {
  dashboard: RepositoryDashboard | null;
  onNavigateToTab: (tab: 'dashboard' | 'health' | 'ci-failures' | 'remediation') => void;
  onProposeForFailure?: (failureId: string) => void;
}

export const DashboardOverview: React.FC<DashboardOverviewProps> = ({
  dashboard,
  onNavigateToTab,
  onProposeForFailure,
}) => {
  if (!dashboard) {
    return (
      <div className="p-12 text-center bg-slate-900 border border-slate-800 rounded-xl text-slate-500 text-sm">
        No repository dashboard data available. Select a repository or run an initial health assessment.
      </div>
    );
  }

  const { repository, latest_health, health_history, open_ci_failures, active_remediations, actionable_recommendations } = dashboard;

  const score = latest_health?.health_score;
  const completeness = latest_health?.assessment_completeness ?? 0;
  const isQualified = latest_health?.is_qualified ?? false;

  const getScoreColor = (val: number | null | undefined) => {
    if (val === null || val === undefined) return 'text-slate-400';
    if (val >= 85) return 'text-emerald-400';
    if (val >= 70) return 'text-amber-400';
    return 'text-rose-400';
  };

  return (
    <div className="space-y-6">
      {/* Golden Invariant Notice */}
      <div className="bg-indigo-950/40 border border-indigo-800/40 rounded-xl p-4 text-xs text-indigo-300 flex items-start space-x-3">
        <Sparkles className="w-4 h-4 text-indigo-400 shrink-0 mt-0.5" />
        <div>
          <span className="font-semibold text-indigo-200">System Invariant:</span> Health scores are strictly post-merge evidence. Generated remediation patches and draft PRs do not inflate health scores until reviewed, merged, and deterministically reassessed on branch code.
        </div>
      </div>

      {/* Primary KPI Grid */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {/* Repository Health Score */}
        <div
          onClick={() => onNavigateToTab('health')}
          className="bg-slate-900/90 border border-slate-800 rounded-xl p-5 hover:border-slate-700 cursor-pointer transition shadow-md"
        >
          <div className="flex items-center justify-between text-xs text-slate-400 font-medium">
            <span>Repository Health Score</span>
            <ArrowUpRight className="w-3.5 h-3.5 text-slate-500" />
          </div>
          <div className="mt-2 flex items-baseline space-x-2">
            <span className={`text-3xl font-extrabold ${getScoreColor(score)}`}>
              {score !== null && score !== undefined ? Math.round(score) : '—'}
            </span>
            <span className="text-xs text-slate-500">/ 100</span>
          </div>
          <div className="mt-3 flex items-center space-x-2 text-[11px]">
            <span
              className={`px-2 py-0.5 rounded font-medium ${
                isQualified
                  ? 'bg-emerald-950/80 text-emerald-300 border border-emerald-800/60'
                  : 'bg-amber-950/80 text-amber-300 border border-amber-800/60'
              }`}
            >
              {isQualified ? 'Qualified' : 'Provisional'}
            </span>
            <span className="text-slate-400">
              {Math.round(completeness <= 1 ? completeness * 100 : completeness)}% complete
            </span>
          </div>
        </div>

        {/* Open CI Failures */}
        <div
          onClick={() => onNavigateToTab('ci-failures')}
          className="bg-slate-900/90 border border-slate-800 rounded-xl p-5 hover:border-slate-700 cursor-pointer transition shadow-md"
        >
          <div className="flex items-center justify-between text-xs text-slate-400 font-medium">
            <span>Active CI Failures</span>
            <ArrowUpRight className="w-3.5 h-3.5 text-slate-500" />
          </div>
          <div className="mt-2 flex items-baseline space-x-2">
            <span className="text-3xl font-extrabold text-rose-400">
              {open_ci_failures?.length ?? 0}
            </span>
            <span className="text-xs text-slate-500">unresolved</span>
          </div>
          <p className="mt-3 text-[11px] text-slate-400">
            Categorized & localized logs
          </p>
        </div>

        {/* Active Remediations */}
        <div
          onClick={() => onNavigateToTab('remediation')}
          className="bg-slate-900/90 border border-slate-800 rounded-xl p-5 hover:border-slate-700 cursor-pointer transition shadow-md"
        >
          <div className="flex items-center justify-between text-xs text-slate-400 font-medium">
            <span>Remediation Proposals</span>
            <ArrowUpRight className="w-3.5 h-3.5 text-slate-500" />
          </div>
          <div className="mt-2 flex items-baseline space-x-2">
            <span className="text-3xl font-extrabold text-indigo-400">
              {active_remediations?.length ?? 0}
            </span>
            <span className="text-xs text-slate-500">synthesized</span>
          </div>
          <p className="mt-3 text-[11px] text-slate-400">
            Candidate diffs & verifications
          </p>
        </div>

        {/* Repository Context */}
        <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-5 shadow-md">
          <div className="flex items-center justify-between text-xs text-slate-400 font-medium">
            <span>Target Repository</span>
          </div>
          <div className="mt-2 text-sm font-semibold text-white truncate font-mono">
            {repository?.full_name || 'mergemind'}
          </div>
          <div className="mt-3 flex items-center justify-between text-[11px] text-slate-400">
            <span>Branch: <span className="text-slate-200 font-mono">{repository?.default_branch || 'main'}</span></span>
            <span className="inline-flex items-center gap-1 text-emerald-400">
              <CheckCircle2 className="w-3 h-3" /> Active
            </span>
          </div>
        </div>
      </div>

      {/* Main Two-Column Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Dimensions Breakdown & History */}
        <div className="lg:col-span-2 space-y-6">
          {/* Dimension Scores Card */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-sm">
            <h3 className="text-sm font-bold text-white mb-4">
              Health Dimensions Evaluation
            </h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="p-3.5 rounded-lg bg-slate-800/40 border border-slate-800">
                <div className="flex justify-between items-center text-xs mb-1">
                  <span className="text-slate-300 font-medium">Code Quality (Ruff)</span>
                  <span className="font-semibold text-white font-mono">
                    {latest_health?.code_quality_score ?? '—'}
                  </span>
                </div>
                <div className="text-[11px] text-slate-500">Linting, formatting, complexity</div>
              </div>

              <div className="p-3.5 rounded-lg bg-slate-800/40 border border-slate-800">
                <div className="flex justify-between items-center text-xs mb-1">
                  <span className="text-slate-300 font-medium">Security (Bandit)</span>
                  <span className="font-semibold text-white font-mono">
                    {latest_health?.security_score ?? '—'}
                  </span>
                </div>
                <div className="text-[11px] text-slate-500">Static AST vulnerability analysis</div>
              </div>

              <div className="p-3.5 rounded-lg bg-slate-800/40 border border-slate-800">
                <div className="flex justify-between items-center text-xs mb-1">
                  <span className="text-slate-300 font-medium">Dependencies (pip-audit)</span>
                  <span className="font-semibold text-white font-mono">
                    {latest_health?.dependency_score ?? '—'}
                  </span>
                </div>
                <div className="text-[11px] text-slate-500">Known CVE vulnerability audits</div>
              </div>

              <div className="p-3.5 rounded-lg bg-slate-800/40 border border-slate-800">
                <div className="flex justify-between items-center text-xs mb-1">
                  <span className="text-slate-300 font-medium">Test Health (Pytest Sandbox)</span>
                  <span className="font-semibold text-white font-mono">
                    {latest_health?.test_health_score ?? '—'}
                  </span>
                </div>
                <div className="text-[11px] text-slate-500">Pass rate & coverage in Docker sandbox</div>
              </div>
            </div>
          </div>

          {/* Historical Health Trend */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-sm">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-bold text-white flex items-center space-x-2">
                <TrendingUp className="w-4 h-4 text-indigo-400" />
                <span>Historical Assessment Timeline</span>
              </h3>
              <span className="text-xs text-slate-500 font-mono">
                {health_history?.length ?? 0} checkpoints recorded
              </span>
            </div>

            {health_history && health_history.length > 0 ? (
              <div className="space-y-2">
                {health_history.slice(-5).reverse().map((h) => (
                  <div
                    key={h.id}
                    className="p-3 rounded-lg bg-slate-800/30 border border-slate-800 flex items-center justify-between text-xs font-mono"
                  >
                    <div className="flex items-center space-x-3">
                      <span className="text-indigo-400 font-bold">
                        {h.commit_sha ? h.commit_sha.substring(0, 7) : 'head'}
                      </span>
                      <span className="text-slate-400">
                        {new Date(h.created_at).toLocaleDateString()}
                      </span>
                    </div>
                    <div className="flex items-center space-x-4">
                      <span className="text-slate-300">
                        Score: <span className="font-bold text-white">{h.health_score !== null ? Math.round(h.health_score) : '—'}</span>
                      </span>
                      <span className={`px-1.5 py-0.5 rounded text-[10px] ${
                        h.is_qualified ? 'bg-emerald-950 text-emerald-400' : 'bg-amber-950 text-amber-400'
                      }`}>
                        {h.is_qualified ? 'QUALIFIED' : 'PROVISIONAL'}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-xs text-slate-500 text-center py-6">
                No historical assessments recorded for this repository yet.
              </p>
            )}
          </div>
        </div>

        {/* Right Column: Actionable Recommendations */}
        <div className="space-y-6">
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-sm">
            <h3 className="text-sm font-bold text-white mb-4">
              Actionable Recommendations
            </h3>

            {actionable_recommendations && actionable_recommendations.length > 0 ? (
              <div className="space-y-3">
                {actionable_recommendations.map((rec, idx) => (
                  <div
                    key={idx}
                    className="p-3.5 rounded-lg bg-slate-800/40 border border-slate-800 space-y-2"
                  >
                    <div className="flex items-start justify-between gap-2">
                      <span className="text-xs font-semibold text-slate-200">
                        {rec.title}
                      </span>
                      <span className="px-1.5 py-0.5 text-[10px] uppercase font-bold rounded bg-rose-950/80 text-rose-300 border border-rose-800/60">
                        {rec.severity}
                      </span>
                    </div>
                    <p className="text-xs text-slate-400">
                      {rec.description}
                    </p>
                    {rec.target_file && (
                      <p className="text-[11px] font-mono text-slate-500">
                        {rec.target_file}{rec.line_number ? `:${rec.line_number}` : ''}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            ) : open_ci_failures && open_ci_failures.length > 0 ? (
              <div className="space-y-3">
                <p className="text-xs text-slate-400 mb-2">
                  Failures requiring attention:
                </p>
                {open_ci_failures.slice(0, 3).map((f) => (
                  <div
                    key={f.id}
                    className="p-3 rounded-lg bg-slate-800/40 border border-slate-800 space-y-2"
                  >
                    <div className="flex items-center justify-between text-xs">
                      <span className="font-semibold text-white truncate max-w-[180px]">
                        {f.workflow_name}
                      </span>
                      <span className="px-1.5 py-0.5 rounded text-[10px] font-mono bg-rose-950 text-rose-300 border border-rose-800/60">
                        {f.failure_category || f.classification || 'FAILURE'}
                      </span>
                    </div>
                    <p className="text-[11px] text-slate-400 line-clamp-2">
                      {f.error_message || f.error_summary || 'CI run failure detected'}
                    </p>
                    {onProposeForFailure && (
                      <button
                        onClick={() => onProposeForFailure(f.id)}
                        className="text-[11px] font-semibold text-indigo-400 hover:text-indigo-300 flex items-center space-x-1"
                      >
                        <Sparkles className="w-3 h-3" />
                        <span>Synthesize Patch</span>
                      </button>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-xs text-slate-500 text-center py-6">
                All checks clean. No urgent recommendations for this repository.
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
