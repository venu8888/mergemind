import React, { useState } from 'react';
import {
  Activity,
  ShieldCheck,
  Code2,
  Package,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Play,
  RotateCw,
  Info,
  Calendar,
  Layers,
} from 'lucide-react';
import type { RepositoryDashboard } from '../types';
import { triggerHealthAssessment } from '../services/api';

interface HealthViewProps {
  repositoryId: string;
  dashboard: RepositoryDashboard | null;
  onRefresh: () => Promise<void>;
}

export const HealthView: React.FC<HealthViewProps> = ({
  repositoryId,
  dashboard,
  onRefresh,
}) => {
  const [assessing, setAssessing] = useState(false);
  const [assessmentError, setAssessmentError] = useState<string | null>(null);
  const [assessmentSuccess, setAssessmentSuccess] = useState<string | null>(null);

  const health = dashboard?.current_health || dashboard?.latest_health;
  const history = dashboard?.health_history || [];

  const handleRunAssessment = async () => {
    setAssessing(true);
    setAssessmentError(null);
    setAssessmentSuccess(null);
    try {
      const result = await triggerHealthAssessment(repositoryId);
      setAssessmentSuccess(
        `Assessment complete! Overall score: ${Math.round(result.health_score)}/100 (${result.qualification_status || 'QUALIFIED'})`
      );
      await onRefresh();
    } catch (err: any) {
      setAssessmentError(err.response?.data?.detail || err.message || 'Assessment failed');
    } finally {
      setAssessing(false);
    }
  };

  const getDimensionIcon = (name: string) => {
    switch (name.toLowerCase()) {
      case 'code_quality':
      case 'code quality':
        return Code2;
      case 'security':
        return ShieldCheck;
      case 'dependency_health':
      case 'dependency health':
        return Package;
      case 'test_health':
      case 'test health':
        return Activity;
      default:
        return Layers;
    }
  };

  const getAvailabilityBadge = (status?: string) => {
    switch (status) {
      case 'ENABLED':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-semibold bg-emerald-950/60 text-emerald-400 border border-emerald-800/60">
            <CheckCircle2 className="w-3 h-3" /> ENABLED
          </span>
        );
      case 'UNCONFIGURED':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-semibold bg-amber-950/60 text-amber-400 border border-amber-800/60">
            <AlertTriangle className="w-3 h-3" /> UNCONFIGURED
          </span>
        );
      case 'FAILED_DEPENDENCY':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-semibold bg-rose-950/60 text-rose-400 border border-rose-800/60">
            <XCircle className="w-3 h-3" /> FAILED DEPENDENCY
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-semibold bg-slate-800 text-slate-400 border border-slate-700">
            {status || 'UNKNOWN'}
          </span>
        );
    }
  };

  return (
    <div className="space-y-6">
      {/* Header and Controls */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-slate-900 border border-slate-800 p-6 rounded-xl">
        <div>
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-400">
              <Activity className="w-6 h-6" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-white">Repository Health Assessment</h2>
              <p className="text-sm text-slate-400">
                Evidence-backed continuous evaluation across code quality, security, dependencies, and tests.
              </p>
            </div>
          </div>
        </div>

        <button
          onClick={handleRunAssessment}
          disabled={assessing}
          className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 disabled:bg-slate-800 text-white font-medium text-sm transition-colors shadow-lg shadow-emerald-900/20"
        >
          {assessing ? (
            <>
              <RotateCw className="w-4 h-4 animate-spin" />
              Assessing Repository...
            </>
          ) : (
            <>
              <Play className="w-4 h-4 fill-current" />
              Assess Repository Now
            </>
          )}
        </button>
      </div>

      {/* Notifications */}
      {assessmentSuccess && (
        <div className="p-4 rounded-lg bg-emerald-950/40 border border-emerald-800/60 text-emerald-300 text-sm flex items-center justify-between">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
            <span>{assessmentSuccess}</span>
          </div>
          <button
            onClick={() => setAssessmentSuccess(null)}
            className="text-xs text-emerald-400 hover:text-emerald-200"
          >
            Dismiss
          </button>
        </div>
      )}

      {assessmentError && (
        <div className="p-4 rounded-lg bg-rose-950/40 border border-rose-800/60 text-rose-300 text-sm flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0" />
            <span>{assessmentError}</span>
          </div>
          <button
            onClick={() => setAssessmentError(null)}
            className="text-xs text-rose-400 hover:text-rose-200"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Health Invariant Banner */}
      <div className="p-4 rounded-xl bg-blue-950/30 border border-blue-800/40 text-blue-300 text-xs flex items-start gap-3">
        <Info className="w-4 h-4 text-blue-400 shrink-0 mt-0.5" />
        <div>
          <span className="font-semibold text-blue-200">System Invariant:</span> Repository health scores are derived strictly from deterministic assessments of committed branch code. Remediation proposals, verified patches, and draft pull requests do <span className="font-bold underline">not</span> artificially inflate repository scores until reviewed and merged.
        </div>
      </div>

      {/* Core Metrics Triad */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        <div className="bg-slate-900/80 border border-slate-800 p-6 rounded-xl relative overflow-hidden">
          <div className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1">
            Repository Health Score
          </div>
          <div className="flex items-baseline gap-3">
            <span className="text-4xl font-extrabold text-white">
              {health?.health_score !== undefined && health?.health_score !== null ? Math.round(health.health_score) : '—'}
            </span>
            <span className="text-slate-400 text-sm">/ 100</span>
          </div>
          <div className="mt-3 flex items-center gap-2">
            <span
              className={`px-2 py-0.5 rounded text-xs font-medium ${
                health?.qualification_status === 'QUALIFIED_SCORE' || health?.is_qualified
                  ? 'bg-emerald-950 text-emerald-400 border border-emerald-800'
                  : health?.qualification_status === 'PROVISIONAL_PARTIAL'
                  ? 'bg-amber-950 text-amber-400 border border-amber-800'
                  : 'bg-rose-950 text-rose-400 border border-rose-800'
              }`}
            >
              {health?.qualification_status || (health?.is_qualified ? 'QUALIFIED' : 'NOT ASSESSED')}
            </span>
          </div>
        </div>

        <div className="bg-slate-900/80 border border-slate-800 p-6 rounded-xl">
          <div className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1">
            Assessment Completeness
          </div>
          <div className="flex items-baseline gap-3">
            <span className="text-4xl font-extrabold text-white">
              {health?.assessment_completeness !== undefined && health?.assessment_completeness !== null
                ? `${Math.round(health.assessment_completeness <= 1 ? health.assessment_completeness * 100 : health.assessment_completeness)}%`
                : '—'}
            </span>
          </div>
          <p className="mt-3 text-xs text-slate-400">
            Proportion of all required checks successfully executed.
          </p>
        </div>

        <div className="bg-slate-900/80 border border-slate-800 p-6 rounded-xl">
          <div className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1">
            Check Availability
          </div>
          <div className="flex items-baseline gap-3">
            <span className="text-4xl font-extrabold text-white">
              {health?.check_availability !== undefined && health?.check_availability !== null
                ? `${Math.round(health.check_availability <= 1 ? health.check_availability * 100 : health.check_availability)}%`
                : '100%'}
            </span>
          </div>
          <p className="mt-3 text-xs text-slate-400">
            Check runners configured and operational in this environment.
          </p>
        </div>
      </div>

      {/* Dimensions Breakdown */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
        <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
          <Layers className="w-5 h-5 text-indigo-400" />
          Dimension Breakdown
        </h3>

        {health?.breakdown ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {Object.entries(health.breakdown).map(([key, dim]: [string, any]) => {
              const Icon = getDimensionIcon(key);
              const score = typeof dim.score === 'number' ? Math.round(dim.score) : 0;
              const weight = typeof dim.weight === 'number' ? Math.round(dim.weight * 100) : 0;

              return (
                <div
                  key={key}
                  className="bg-slate-800/60 border border-slate-700/60 rounded-lg p-5 space-y-3"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2.5">
                      <div className="p-2 rounded bg-slate-700/50 text-indigo-300">
                        <Icon className="w-4 h-4" />
                      </div>
                      <div>
                        <div className="text-sm font-semibold text-white capitalize">
                          {key.replace('_', ' ')}
                        </div>
                        <div className="text-xs text-slate-400">Weight: {weight}%</div>
                      </div>
                    </div>
                    {getAvailabilityBadge(dim.availability || (dim.available ? 'ENABLED' : 'UNCONFIGURED'))}
                  </div>

                  {/* Progress Bar */}
                  <div>
                    <div className="flex justify-between text-xs mb-1">
                      <span className="text-slate-400">Score</span>
                      <span className="text-slate-200 font-semibold">{score}/100</span>
                    </div>
                    <div className="w-full bg-slate-700 rounded-full h-2 overflow-hidden">
                      <div
                        className={`h-2 rounded-full transition-all duration-500 ${
                          score >= 80
                            ? 'bg-emerald-500'
                            : score >= 60
                            ? 'bg-amber-500'
                            : 'bg-rose-500'
                        }`}
                        style={{ width: `${Math.min(100, Math.max(0, score))}%` }}
                      />
                    </div>
                  </div>

                  {/* Dimension Evidence / Findings Summary */}
                  {dim.findings_summary && (
                    <div className="text-xs text-slate-400 bg-slate-900/60 p-2.5 rounded border border-slate-800 font-mono">
                      {typeof dim.findings_summary === 'object'
                        ? JSON.stringify(dim.findings_summary, null, 2)
                        : String(dim.findings_summary)}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            <div className="bg-slate-800/60 border border-slate-700/60 rounded-lg p-5 space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2.5">
                  <div className="p-2 rounded bg-slate-700/50 text-indigo-300">
                    <Code2 className="w-4 h-4" />
                  </div>
                  <div>
                    <div className="text-sm font-semibold text-white">Code Quality (Ruff)</div>
                    <div className="text-xs text-slate-400">Weight: 25%</div>
                  </div>
                </div>
                {getAvailabilityBadge(health?.dimension_status?.code_quality || 'ENABLED')}
              </div>
              <div className="text-xl font-bold text-white">{health?.code_quality_score !== null && health?.code_quality_score !== undefined ? `${Math.round(health.code_quality_score)} / 100` : '—'}</div>
            </div>

            <div className="bg-slate-800/60 border border-slate-700/60 rounded-lg p-5 space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2.5">
                  <div className="p-2 rounded bg-slate-700/50 text-indigo-300">
                    <ShieldCheck className="w-4 h-4" />
                  </div>
                  <div>
                    <div className="text-sm font-semibold text-white">Security (Bandit)</div>
                    <div className="text-xs text-slate-400">Weight: 25%</div>
                  </div>
                </div>
                {getAvailabilityBadge(health?.dimension_status?.security || 'ENABLED')}
              </div>
              <div className="text-xl font-bold text-white">{health?.security_score !== null && health?.security_score !== undefined ? `${Math.round(health.security_score)} / 100` : '—'}</div>
            </div>

            <div className="bg-slate-800/60 border border-slate-700/60 rounded-lg p-5 space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2.5">
                  <div className="p-2 rounded bg-slate-700/50 text-indigo-300">
                    <Package className="w-4 h-4" />
                  </div>
                  <div>
                    <div className="text-sm font-semibold text-white">Dependency Health (pip-audit)</div>
                    <div className="text-xs text-slate-400">Weight: 20%</div>
                  </div>
                </div>
                {getAvailabilityBadge(health?.dimension_status?.dependencies || 'ENABLED')}
              </div>
              <div className="text-xl font-bold text-white">{health?.dependency_score !== null && health?.dependency_score !== undefined ? `${Math.round(health.dependency_score)} / 100` : '—'}</div>
            </div>

            <div className="bg-slate-800/60 border border-slate-700/60 rounded-lg p-5 space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2.5">
                  <div className="p-2 rounded bg-slate-700/50 text-indigo-300">
                    <Activity className="w-4 h-4" />
                  </div>
                  <div>
                    <div className="text-sm font-semibold text-white">Test Health (Pytest Sandbox)</div>
                    <div className="text-xs text-slate-400">Weight: 20%</div>
                  </div>
                </div>
                {getAvailabilityBadge(health?.dimension_status?.test_health || (health?.test_health_score !== null && health?.test_health_score !== undefined ? 'ENABLED' : 'UNCONFIGURED'))}
              </div>
              <div className="text-xl font-bold text-white">{health?.test_health_score !== null && health?.test_health_score !== undefined ? `${Math.round(health.test_health_score)} / 100` : '—'}</div>
            </div>

            <div className="bg-slate-800/60 border border-slate-700/60 rounded-lg p-5 space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2.5">
                  <div className="p-2 rounded bg-slate-700/50 text-indigo-300">
                    <Layers className="w-4 h-4" />
                  </div>
                  <div>
                    <div className="text-sm font-semibold text-white">Maintainability & Complexity</div>
                    <div className="text-xs text-slate-400">Weight: 10%</div>
                  </div>
                </div>
                {getAvailabilityBadge(health?.dimension_status?.maintainability || 'ENABLED')}
              </div>
              <div className="text-xl font-bold text-white">{health?.maintainability_score !== null && health?.maintainability_score !== undefined ? `${Math.round(health.maintainability_score)} / 100` : '—'}</div>
            </div>
          </div>
        )}
      </div>

      {/* Historical Assessments */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
        <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
          <Calendar className="w-5 h-5 text-emerald-400" />
          Assessment History
        </h3>

        {history.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-slate-300">
              <thead className="bg-slate-800/60 text-xs uppercase text-slate-400 border-b border-slate-700">
                <tr>
                  <th className="py-3 px-4">Timestamp</th>
                  <th className="py-3 px-4">Commit SHA</th>
                  <th className="py-3 px-4">Health Score</th>
                  <th className="py-3 px-4">Completeness</th>
                  <th className="py-3 px-4">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800">
                {history.map((record) => (
                  <tr key={record.id} className="hover:bg-slate-800/30 transition-colors">
                    <td className="py-3 px-4 text-xs font-mono text-slate-400">
                      {new Date(record.created_at).toLocaleString()}
                    </td>
                    <td className="py-3 px-4 text-xs font-mono text-indigo-300">
                      {record.commit_sha ? record.commit_sha.substring(0, 7) : 'head'}
                    </td>
                    <td className="py-3 px-4 font-semibold text-white">
                      {record.health_score !== null && record.health_score !== undefined ? `${Math.round(record.health_score)}/100` : '—'}
                    </td>
                    <td className="py-3 px-4 text-slate-400">
                      {record.assessment_completeness !== null && record.assessment_completeness !== undefined
                        ? `${Math.round(record.assessment_completeness <= 1 ? record.assessment_completeness * 100 : record.assessment_completeness)}%`
                        : '—'}
                    </td>
                    <td className="py-3 px-4">
                      <span
                        className={`px-2 py-0.5 rounded text-xs font-medium ${
                          record.qualification_status === 'QUALIFIED_SCORE' || record.is_qualified
                            ? 'bg-emerald-950 text-emerald-400 border border-emerald-800'
                            : 'bg-amber-950 text-amber-400 border border-amber-800'
                        }`}
                      >
                        {record.qualification_status || (record.is_qualified ? 'QUALIFIED' : 'PROVISIONAL')}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="text-center py-8 text-slate-500 text-sm">
            No historical health assessments recorded yet.
          </div>
        )}
      </div>
    </div>
  );
};
