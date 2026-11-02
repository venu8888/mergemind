import React from 'react';
import {
  TrendingUp,
  Lock,
} from 'lucide-react';
import type { RepositoryDashboard } from '../types';

interface DashboardOverviewProps {
  dashboard: RepositoryDashboard | null;
  onNavigateToTab: (tab: any) => void;
}

export const DashboardOverview: React.FC<DashboardOverviewProps> = ({
  dashboard,
  onNavigateToTab,
}) => {
  if (!dashboard) {
    return (
      <div className="p-12 text-center bg-ink-900 border border-white/[0.08] rounded-panel text-zinc-500 text-xs font-mono">
        No repository dashboard telemetry available.
      </div>
    );
  }

  const { repository, latest_health, health_history, open_ci_failures, active_remediations, actionable_recommendations } = dashboard;

  const score = latest_health?.health_score;
  const completeness = latest_health?.assessment_completeness ?? 0;
  const isQualified = latest_health?.is_qualified ?? false;

  const getScoreColor = (val: number | null | undefined) => {
    if (val === null || val === undefined) return 'text-zinc-500';
    if (val >= 85) return 'text-emerald-400';
    if (val >= 70) return 'text-amber-400';
    return 'text-rose-400';
  };

  return (
    <div className="space-y-6">
      {/* Repository Context & Micro-Invariant Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-ink-900 border border-white/[0.08] px-5 py-3.5 rounded-panel">
        <div className="flex items-center gap-3">
          <span className="font-mono text-xs text-zinc-400">Repository:</span>
          <span className="font-mono text-xs font-semibold text-white">{repository?.full_name || 'mergemind'}</span>
          <span className="text-zinc-600">•</span>
          <span className="text-xs text-zinc-400 font-mono">
            Branch <span className="text-zinc-200">{repository?.default_branch || 'main'}</span>
          </span>
        </div>

        <div className="flex items-center gap-1.5 text-[11px] font-mono text-zinc-500">
          <Lock className="w-3 h-3 text-zinc-400" strokeWidth={1.5} />
          <span>Post-merge invariant enforced: health reflects evaluated branch code only</span>
        </div>
      </div>

      {/* Asymmetric Primary Telemetry Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
        {/* Left Hero Card: Calibrated Health Score (5 cols) */}
        <div
          onClick={() => onNavigateToTab('quality-security')}
          className="lg:col-span-5 bg-ink-900 border border-white/[0.08] hover:border-zinc-700 rounded-panel p-6 cursor-pointer transition-colors flex flex-col justify-between"
        >
          <div>
            <div className="flex items-center justify-between text-xs font-mono text-zinc-400 mb-2">
              <span>Repository Health Score</span>
              <span
                className={`px-2 py-0.5 rounded text-[10px] font-mono font-medium border ${
                  isQualified
                    ? 'bg-emerald-950/60 text-emerald-300 border-emerald-800/60'
                    : 'bg-amber-950/60 text-amber-300 border-amber-800/60'
                }`}
              >
                {isQualified ? 'QUALIFIED' : 'PROVISIONAL'}
              </span>
            </div>

            <div className="flex items-baseline gap-3 my-4">
              <span className={`text-5xl font-medium tracking-tight tabular-nums ${getScoreColor(score)}`}>
                {score !== null && score !== undefined ? Math.round(score) : '—'}
              </span>
              <span className="text-zinc-500 font-mono text-sm">/ 100</span>
            </div>

            <div className="text-xs text-zinc-400 leading-relaxed mb-4">
              Deterministic 5-factor calibration based on Ruff, Bandit, pip-audit, Radon AST, and Pytest.
            </div>
          </div>

          <div className="pt-4 border-t border-white/[0.08] flex items-center justify-between text-xs font-mono text-zinc-400">
            <span>Assessment Completeness</span>
            <span className="text-zinc-200 font-semibold tabular-nums">
              {Math.round(completeness <= 1 ? completeness * 100 : completeness)}%
            </span>
          </div>
        </div>

        {/* Right Column: 3 Compact Telemetry Blocks (7 cols) */}
        <div className="lg:col-span-7 grid grid-cols-1 sm:grid-cols-3 gap-4">
          {/* CI Failures */}
          <div
            onClick={() => onNavigateToTab('ci-intelligence')}
            className="bg-ink-900 border border-white/[0.08] hover:border-zinc-700 rounded-panel p-5 cursor-pointer transition-colors flex flex-col justify-between"
          >
            <div>
              <div className="text-xs font-mono text-zinc-400">Active CI Failures</div>
              <div className="mt-3 text-3xl font-medium text-rose-400 font-mono tabular-nums">
                {open_ci_failures?.length ?? 0}
              </div>
            </div>
            <div className="mt-4 pt-3 border-t border-white/[0.08] text-[11px] text-zinc-500">
              Sanitized logs & localized stacks
            </div>
          </div>

          {/* Remediation Proposals */}
          <div
            onClick={() => onNavigateToTab('remediation')}
            className="bg-ink-900 border border-white/[0.08] hover:border-zinc-700 rounded-panel p-5 cursor-pointer transition-colors flex flex-col justify-between"
          >
            <div>
              <div className="text-xs font-mono text-zinc-400">Remediation Proposals</div>
              <div className="mt-3 text-3xl font-medium text-zinc-100 font-mono tabular-nums">
                {active_remediations?.length ?? 0}
              </div>
            </div>
            <div className="mt-4 pt-3 border-t border-white/[0.08] text-[11px] text-zinc-500">
              Verified diffs & draft PRs
            </div>
          </div>

          {/* Tracked Monitoring */}
          <div className="bg-ink-900 border border-white/[0.08] rounded-panel p-5 flex flex-col justify-between">
            <div>
              <div className="text-xs font-mono text-zinc-400">Policy Engine</div>
              <div className="mt-3 text-sm font-semibold text-zinc-200 font-mono truncate">
                {latest_health?.scoring_policy_version || 'v2.2-calibrated'}
              </div>
            </div>
            <div className="mt-4 pt-3 border-t border-white/[0.08] text-[11px] text-zinc-500 font-mono">
              Docker sandbox isolation active
            </div>
          </div>
        </div>
      </div>

      {/* Main Two-Column Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Dimensions Breakdown & History (8 cols) */}
        <div className="lg:col-span-8 space-y-6">
          {/* Calibrated Health Dimensions */}
          <div className="bg-ink-900 border border-white/[0.08] rounded-panel p-5">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-xs font-mono uppercase tracking-wider text-zinc-400">
                Health Dimensions Telemetry
              </h3>
              <span className="text-xs font-mono text-zinc-500">Target: 100/100</span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 font-mono text-xs">
              <div className="p-3 rounded-control bg-ink-950 border border-white/[0.06] flex items-center justify-between">
                <div>
                  <div className="text-zinc-200">Code Quality (Ruff)</div>
                  <div className="text-[11px] text-zinc-500 mt-0.5">Linter & formatting</div>
                </div>
                <span className="font-semibold text-zinc-100 tabular-nums">
                  {latest_health?.code_quality_score !== null && latest_health?.code_quality_score !== undefined
                    ? `${Math.round(latest_health.code_quality_score)}`
                    : '—'}
                </span>
              </div>

              <div className="p-3 rounded-control bg-ink-950 border border-white/[0.06] flex items-center justify-between">
                <div>
                  <div className="text-zinc-200">Security (Bandit)</div>
                  <div className="text-[11px] text-zinc-500 mt-0.5">AST vulnerability scan</div>
                </div>
                <span className="font-semibold text-zinc-100 tabular-nums">
                  {latest_health?.security_score !== null && latest_health?.security_score !== undefined
                    ? `${Math.round(latest_health.security_score)}`
                    : '—'}
                </span>
              </div>

              <div className="p-3 rounded-control bg-ink-950 border border-white/[0.06] flex items-center justify-between">
                <div>
                  <div className="text-zinc-200">Dependencies (pip-audit)</div>
                  <div className="text-[11px] text-zinc-500 mt-0.5">Known CVE audits</div>
                </div>
                <span className="font-semibold text-zinc-100 tabular-nums">
                  {latest_health?.dependency_score !== null && latest_health?.dependency_score !== undefined
                    ? `${Math.round(latest_health.dependency_score)}`
                    : '—'}
                </span>
              </div>

              <div className="p-3 rounded-control bg-ink-950 border border-white/[0.06] flex items-center justify-between">
                <div>
                  <div className="text-zinc-200">Maintainability (Radon)</div>
                  <div className="text-[11px] text-zinc-500 mt-0.5">Cyclomatic complexity</div>
                </div>
                <span className="font-semibold text-zinc-100 tabular-nums">
                  {latest_health?.maintainability_score !== null && latest_health?.maintainability_score !== undefined
                    ? `${Math.round(latest_health.maintainability_score)}`
                    : '—'}
                </span>
              </div>
            </div>
          </div>

          {/* Historical Assessment Timeline Table */}
          <div className="bg-ink-900 border border-white/[0.08] rounded-panel p-5">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-xs font-mono uppercase tracking-wider text-zinc-400 flex items-center gap-2">
                <TrendingUp className="w-3.5 h-3.5 text-zinc-400" strokeWidth={1.5} />
                <span>Historical Assessments</span>
              </h3>
              <span className="text-xs font-mono text-zinc-500">
                {health_history?.length || 0} evaluations recorded
              </span>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left font-mono text-xs">
                <thead>
                  <tr className="border-b border-white/[0.08] text-zinc-500 text-[11px]">
                    <th className="pb-2.5 font-normal">Commit</th>
                    <th className="pb-2.5 font-normal">Health Score</th>
                    <th className="pb-2.5 font-normal">Completeness</th>
                    <th className="pb-2.5 font-normal">Qualification</th>
                    <th className="pb-2.5 font-normal text-right">Timestamp</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/[0.04]">
                  {health_history && health_history.length > 0 ? (
                    health_history.map((record) => (
                      <tr key={record.id} className="hover:bg-white/[0.02] transition-colors">
                        <td className="py-2.5 text-zinc-300 font-mono">
                          {record.commit_sha ? record.commit_sha.substring(0, 7) : '—'}
                        </td>
                        <td className="py-2.5 font-semibold text-zinc-100 tabular-nums">
                          {record.health_score !== null && record.health_score !== undefined
                            ? `${Math.round(record.health_score)}/100`
                            : '—'}
                        </td>
                        <td className="py-2.5 text-zinc-400 tabular-nums">
                          {record.assessment_completeness !== null && record.assessment_completeness !== undefined
                            ? `${Math.round(record.assessment_completeness <= 1 ? record.assessment_completeness * 100 : record.assessment_completeness)}%`
                            : '—'}
                        </td>
                        <td className="py-2.5">
                          <span
                            className={`px-1.5 py-0.5 rounded text-[10px] font-mono border ${
                              record.qualification_status === 'QUALIFIED_SCORE' || record.is_qualified
                                ? 'bg-emerald-950/60 text-emerald-400 border-emerald-800/60'
                                : 'bg-amber-950/60 text-amber-400 border-amber-800/60'
                            }`}
                          >
                            {record.is_qualified ? 'QUALIFIED' : 'PROVISIONAL'}
                          </span>
                        </td>
                        <td className="py-2.5 text-zinc-500 text-right text-[11px]">
                          {new Date(record.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan={5} className="py-6 text-center text-zinc-500 text-xs">
                        No previous assessments logged.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        {/* Right Column: Actionable Recommendations Drawer (4 cols) */}
        <div className="lg:col-span-4 bg-ink-900 border border-white/[0.08] rounded-panel p-5 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-mono uppercase tracking-wider text-zinc-400">
              Actionable Findings ({actionable_recommendations?.length || 0})
            </h3>
          </div>

          <div className="space-y-2.5 max-h-[500px] overflow-y-auto pr-1">
            {actionable_recommendations && actionable_recommendations.length > 0 ? (
              actionable_recommendations.map((rec, idx) => (
                <div
                  key={rec.remediation_proposal_id || `${rec.title}-${idx}`}
                  className="p-3 rounded-control bg-ink-950 border border-white/[0.06] text-xs space-y-2 font-mono"
                >
                  <div className="flex items-start justify-between gap-2">
                    <span className="text-zinc-200 font-medium truncate font-sans">{rec.title}</span>
                    <span
                      className={`px-1.5 py-0.5 rounded text-[10px] uppercase font-bold shrink-0 ${
                        rec.severity === 'CRITICAL' || rec.severity === 'HIGH'
                          ? 'bg-rose-950/60 text-rose-400 border border-rose-800/60'
                          : 'bg-amber-950/60 text-amber-400 border border-amber-800/60'
                      }`}
                    >
                      {rec.severity}
                    </span>
                  </div>

                  <p className="text-zinc-400 text-[11px] font-sans leading-relaxed line-clamp-2">
                    {rec.description}
                  </p>

                  <div className="pt-2 border-t border-white/[0.06] flex items-center justify-between text-[11px]">
                    <span className="text-zinc-500">{rec.category}</span>
                    <button
                      onClick={() => onNavigateToTab('remediation')}
                      className="text-zinc-300 hover:text-white transition-colors"
                    >
                      Remediate &rarr;
                    </button>
                  </div>
                </div>
              ))
            ) : (
              <div className="p-8 text-center text-zinc-500 text-xs font-mono">
                No critical or blocking vulnerabilities identified.
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
