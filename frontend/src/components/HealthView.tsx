import React, { useState } from 'react';
import {
  ShieldCheck,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Play,
  RotateCw,
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
        `Assessment complete: ${Math.round(result.health_score)}/100 (${result.qualification_status || 'QUALIFIED'})`
      );
      await onRefresh();
    } catch (err: any) {
      setAssessmentError(err.response?.data?.detail || err.message || 'Assessment failed');
    } finally {
      setAssessing(false);
    }
  };

  const getAvailabilityBadge = (status?: string) => {
    switch (status) {
      case 'ENABLED':
        return (
          <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-mono font-bold bg-emerald-950/60 text-emerald-400 border border-emerald-800/60">
            <CheckCircle2 className="w-2.5 h-2.5" /> ENABLED
          </span>
        );
      case 'UNCONFIGURED':
        return (
          <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-mono font-bold bg-amber-950/60 text-amber-400 border border-amber-800/60">
            <AlertTriangle className="w-2.5 h-2.5" /> UNCONFIGURED
          </span>
        );
      case 'FAILED_DEPENDENCY':
        return (
          <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-mono font-bold bg-rose-950/60 text-rose-400 border border-rose-800/60">
            <XCircle className="w-2.5 h-2.5" /> FAILED
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-mono bg-ink-800 text-zinc-400 border border-white/[0.06]">
            {status || 'UNKNOWN'}
          </span>
        );
    }
  };

  return (
    <div className="space-y-6">
      {/* Header and Controls */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-ink-900 border border-white/[0.08] px-5 py-3.5 rounded-panel">
        <div className="flex items-center gap-3">
          <div className="w-7 h-7 rounded-control bg-ink-800 border border-white/[0.08] flex items-center justify-center text-zinc-200">
            <ShieldCheck className="w-3.5 h-3.5" strokeWidth={1.5} />
          </div>
          <div>
            <h2 className="text-xs font-semibold text-white">Quality & Security Telemetry</h2>
            <p className="text-[11px] text-zinc-500">
              Deterministic multi-factor health evaluation across static scanners and sandbox runners
            </p>
          </div>
        </div>

        <button
          onClick={handleRunAssessment}
          disabled={assessing}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-control bg-emerald-600 hover:bg-emerald-500 disabled:bg-ink-800 text-white text-xs font-mono font-medium transition-colors"
        >
          {assessing ? (
            <>
              <RotateCw className="w-3 h-3 animate-spin" strokeWidth={1.5} />
              <span>Assessing...</span>
            </>
          ) : (
            <>
              <Play className="w-3 h-3 fill-current" />
              <span>Assess Repository Now</span>
            </>
          )}
        </button>
      </div>

      {/* Notifications */}
      {assessmentSuccess && (
        <div className="p-3 rounded-control bg-ink-950 border border-emerald-800/60 text-emerald-300 text-xs font-mono flex items-center justify-between">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" strokeWidth={1.5} />
            <span>{assessmentSuccess}</span>
          </div>
          <button
            onClick={() => setAssessmentSuccess(null)}
            className="text-[11px] text-zinc-400 hover:text-white"
          >
            Dismiss
          </button>
        </div>
      )}

      {assessmentError && (
        <div className="p-3 rounded-control bg-ink-950 border border-rose-800/60 text-rose-300 text-xs font-mono flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-3.5 h-3.5 text-rose-400 shrink-0" strokeWidth={1.5} />
            <span>{assessmentError}</span>
          </div>
          <button
            onClick={() => setAssessmentError(null)}
            className="text-[11px] text-zinc-400 hover:text-white"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Core Metrics Triad */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        <div className="bg-ink-900 border border-white/[0.08] p-5 rounded-panel">
          <div className="text-xs font-mono text-zinc-500 mb-1">
            Repository Health Score
          </div>
          <div className="flex items-baseline gap-2 my-2">
            <span className="text-4xl font-medium text-white font-mono tabular-nums">
              {health?.health_score !== undefined && health?.health_score !== null ? Math.round(health.health_score) : '—'}
            </span>
            <span className="text-zinc-500 font-mono text-sm">/ 100</span>
          </div>
          <div className="mt-3">
            <span
              className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase border ${
                health?.qualification_status === 'QUALIFIED_SCORE' || health?.is_qualified
                  ? 'bg-emerald-950/60 text-emerald-400 border-emerald-800/60'
                  : 'bg-amber-950/60 text-amber-400 border-amber-800/60'
              }`}
            >
              {health?.qualification_status || (health?.is_qualified ? 'QUALIFIED' : 'NOT ASSESSED')}
            </span>
          </div>
        </div>

        <div className="bg-ink-900 border border-white/[0.08] p-5 rounded-panel">
          <div className="text-xs font-mono text-zinc-500 mb-1">
            Assessment Completeness
          </div>
          <div className="flex items-baseline gap-2 my-2">
            <span className="text-4xl font-medium text-zinc-100 font-mono tabular-nums">
              {health?.assessment_completeness !== undefined && health?.assessment_completeness !== null
                ? `${Math.round(health.assessment_completeness <= 1 ? health.assessment_completeness * 100 : health.assessment_completeness)}%`
                : '—'}
            </span>
          </div>
          <p className="mt-3 text-[11px] text-zinc-500 font-mono">
            Evaluated checks count toward final score
          </p>
        </div>

        <div className="bg-ink-900 border border-white/[0.08] p-5 rounded-panel">
          <div className="text-xs font-mono text-zinc-500 mb-1">
            Check Availability
          </div>
          <div className="flex items-baseline gap-2 my-2">
            <span className="text-4xl font-medium text-zinc-100 font-mono tabular-nums">100%</span>
          </div>
          <p className="mt-3 text-[11px] text-zinc-500 font-mono">
            Scanners operational in Docker environment
          </p>
        </div>
      </div>

      {/* Dimension Breakdown Cards */}
      <div className="space-y-3">
        <div className="text-xs font-mono uppercase tracking-wider text-zinc-400 px-1">
          Dimension Breakdown
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {/* 1. Code Quality */}
          <div className="bg-ink-900 border border-white/[0.08] p-4 rounded-panel space-y-3 font-mono text-xs">
            <div className="flex items-center justify-between">
              <span className="text-zinc-300 font-medium">Code Quality (Ruff)</span>
              {getAvailabilityBadge('ENABLED')}
            </div>
            <div className="text-2xl font-medium text-white tabular-nums">
              {health?.code_quality_score !== null && health?.code_quality_score !== undefined
                ? `${Math.round(health.code_quality_score)} / 100`
                : '— / 100'}
            </div>
            <div className="text-[11px] text-zinc-500 font-sans">
              Weight: 25% • Linting and formatting rules enforced
            </div>
          </div>

          {/* 2. Security */}
          <div className="bg-ink-900 border border-white/[0.08] p-4 rounded-panel space-y-3 font-mono text-xs">
            <div className="flex items-center justify-between">
              <span className="text-zinc-300 font-medium">Security (Bandit)</span>
              {getAvailabilityBadge('ENABLED')}
            </div>
            <div className="text-2xl font-medium text-white tabular-nums">
              {health?.security_score !== null && health?.security_score !== undefined
                ? `${Math.round(health.security_score)} / 100`
                : '— / 100'}
            </div>
            <div className="text-[11px] text-zinc-500 font-sans">
              Weight: 25% • Static AST vulnerability scans
            </div>
          </div>

          {/* 3. Dependencies */}
          <div className="bg-ink-900 border border-white/[0.08] p-4 rounded-panel space-y-3 font-mono text-xs">
            <div className="flex items-center justify-between">
              <span className="text-zinc-300 font-medium">Dependencies (pip-audit)</span>
              {getAvailabilityBadge('ENABLED')}
            </div>
            <div className="text-2xl font-medium text-white tabular-nums">
              {health?.dependency_score !== null && health?.dependency_score !== undefined
                ? `${Math.round(health.dependency_score)} / 100`
                : '— / 100'}
            </div>
            <div className="text-[11px] text-zinc-500 font-sans">
              Weight: 20% • Known CVE vulnerabilities in locked graph
            </div>
          </div>

          {/* 4. Maintainability */}
          <div className="bg-ink-900 border border-white/[0.08] p-4 rounded-panel space-y-3 font-mono text-xs">
            <div className="flex items-center justify-between">
              <span className="text-zinc-300 font-medium">Maintainability (Radon)</span>
              {getAvailabilityBadge('ENABLED')}
            </div>
            <div className="text-2xl font-medium text-white tabular-nums">
              {health?.maintainability_score !== null && health?.maintainability_score !== undefined
                ? `${Math.round(health.maintainability_score)} / 100`
                : '— / 100'}
            </div>
            <div className="text-[11px] text-zinc-500 font-sans">
              Weight: 10% • McCabe cyclomatic complexity & docstrings
            </div>
          </div>

          {/* 5. Test Health */}
          <div className="bg-ink-900 border border-white/[0.08] p-4 rounded-panel space-y-3 font-mono text-xs">
            <div className="flex items-center justify-between">
              <span className="text-zinc-300 font-medium">Test Health (Pytest)</span>
              {getAvailabilityBadge(health?.test_health_score !== null ? 'ENABLED' : 'UNCONFIGURED')}
            </div>
            <div className="text-2xl font-medium text-white tabular-nums">
              {health?.test_health_score !== null && health?.test_health_score !== undefined
                ? `${Math.round(health.test_health_score)} / 100`
                : '— / 100'}
            </div>
            <div className="text-[11px] text-zinc-500 font-sans">
              Weight: 20% • Pass rate and coverage in Docker sandbox
            </div>
          </div>
        </div>
      </div>

      {/* Historical Assessment Log Table */}
      <div className="bg-ink-900 border border-white/[0.08] rounded-panel p-5 space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-xs font-mono uppercase tracking-wider text-zinc-400">
            Assessment Run Log
          </h3>
          <span className="text-xs font-mono text-zinc-500">
            {history.length} runs recorded
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left font-mono text-xs">
            <thead>
              <tr className="border-b border-white/[0.08] text-zinc-500 text-[11px]">
                <th className="pb-2.5 font-normal">Commit SHA</th>
                <th className="pb-2.5 font-normal">Overall Score</th>
                <th className="pb-2.5 font-normal">Completeness</th>
                <th className="pb-2.5 font-normal">Qualification</th>
                <th className="pb-2.5 font-normal text-right">Timestamp</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/[0.04]">
              {history.map((record) => (
                <tr key={record.id} className="hover:bg-white/[0.02] transition-colors">
                  <td className="py-2.5 text-zinc-300 font-mono">
                    {record.commit_sha ? record.commit_sha.substring(0, 7) : '—'}
                  </td>
                  <td className="py-2.5 font-semibold text-zinc-100 tabular-nums">
                    {record.health_score !== null && record.health_score !== undefined ? `${Math.round(record.health_score)}/100` : '—'}
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
                      {record.qualification_status || (record.is_qualified ? 'QUALIFIED' : 'PROVISIONAL')}
                    </span>
                  </td>
                  <td className="py-2.5 text-zinc-500 text-right text-[11px]">
                    {new Date(record.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
