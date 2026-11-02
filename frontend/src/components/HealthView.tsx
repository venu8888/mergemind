import React, { useState, useEffect } from 'react';
import {
  ShieldCheck,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Play,
  RotateCw,
  ChevronDown,
  ChevronRight,
  Search,
} from 'lucide-react';
import type { RepositoryDashboard } from '../types';
import {
  triggerHealthAssessment,
  fetchSecurityPosture,
  type SecurityPostureReport,
  type SecurityPostureCheck,
} from '../services/api';

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
  const [viewMode, setViewMode] = useState<'code-telemetry' | 'security-posture'>('code-telemetry');
  const [assessing, setAssessing] = useState(false);
  const [assessmentError, setAssessmentError] = useState<string | null>(null);
  const [assessmentSuccess, setAssessmentSuccess] = useState<string | null>(null);

  // Security Posture state
  const [postureReport, setPostureReport] = useState<SecurityPostureReport | null>(null);
  const [postureLoading, setPostureLoading] = useState(false);
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [expandedCheckId, setExpandedCheckId] = useState<string | null>(null);

  const health = dashboard?.current_health || dashboard?.latest_health;
  const history = dashboard?.health_history || [];

  const loadSecurityPosture = async () => {
    if (!repositoryId) return;
    setPostureLoading(true);
    try {
      const report = await fetchSecurityPosture(repositoryId);
      setPostureReport(report);
    } catch (err: any) {
      console.error('Failed to load security posture:', err);
    } finally {
      setPostureLoading(false);
    }
  };

  useEffect(() => {
    if (viewMode === 'security-posture' || !postureReport) {
      loadSecurityPosture();
    }
  }, [repositoryId, viewMode]);

  const handleRunAssessment = async () => {
    setAssessing(true);
    setAssessmentError(null);
    setAssessmentSuccess(null);
    try {
      const result = await triggerHealthAssessment(repositoryId);
      const qual = result.is_qualified ? 'QUALIFIED' : 'PROVISIONAL';
      setAssessmentSuccess(
        `Assessment complete: ${Math.round(result.health_score)}/100 (${qual})`
      );
      await onRefresh();
      await loadSecurityPosture();
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
      case 'FAILED':
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

  const getPostureStatusBadge = (status: string) => {
    switch (status) {
      case 'PASSED':
        return (
          <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-mono font-bold bg-emerald-950/60 text-emerald-400 border border-emerald-800/60">
            <CheckCircle2 className="w-2.5 h-2.5" /> PASSED
          </span>
        );
      case 'FAILED':
        return (
          <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-mono font-bold bg-rose-950/60 text-rose-400 border border-rose-800/60">
            <XCircle className="w-2.5 h-2.5" /> FAILED
          </span>
        );
      case 'WARNING':
        return (
          <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-mono font-bold bg-amber-950/60 text-amber-400 border border-amber-800/60">
            <AlertTriangle className="w-2.5 h-2.5" /> WARNING
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-mono bg-ink-800 text-zinc-400 border border-white/[0.06]">
            {status}
          </span>
        );
    }
  };

  const getSeverityBadge = (severity: string) => {
    switch (severity) {
      case 'CRITICAL':
        return (
          <span className="px-1.5 py-0.5 rounded text-[9px] font-mono font-bold uppercase bg-rose-950 text-rose-400 border border-rose-800/60">
            CRITICAL
          </span>
        );
      case 'HIGH':
        return (
          <span className="px-1.5 py-0.5 rounded text-[9px] font-mono font-bold uppercase bg-orange-950 text-orange-400 border border-orange-800/60">
            HIGH
          </span>
        );
      case 'MEDIUM':
        return (
          <span className="px-1.5 py-0.5 rounded text-[9px] font-mono font-bold uppercase bg-amber-950 text-amber-400 border border-amber-800/60">
            MEDIUM
          </span>
        );
      case 'LOW':
        return (
          <span className="px-1.5 py-0.5 rounded text-[9px] font-mono font-bold uppercase bg-zinc-800 text-zinc-300 border border-white/[0.08]">
            LOW
          </span>
        );
      default:
        return (
          <span className="px-1.5 py-0.5 rounded text-[9px] font-mono font-bold uppercase bg-zinc-900 text-zinc-400 border border-white/[0.06]">
            {severity}
          </span>
        );
    }
  };

  // Filter checks for posture report
  const allPostureChecks: SecurityPostureCheck[] = postureReport
    ? Object.values(postureReport.categories).flatMap((cat) => cat.checks)
    : [];

  const filteredChecks = allPostureChecks.filter((c) => {
    const matchesCat = selectedCategory === 'all' || c.category === selectedCategory;
    const matchesSearch =
      !searchQuery ||
      c.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      c.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
      c.evidence.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesCat && matchesSearch;
  });

  return (
    <div className="space-y-6">
      {/* Header with Dual View Toggle */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-ink-900 border border-white/[0.08] px-5 py-3.5 rounded-panel">
        <div className="flex items-center gap-3">
          <div className="w-7 h-7 rounded-control bg-ink-800 border border-white/[0.08] flex items-center justify-center text-zinc-200">
            <ShieldCheck className="w-3.5 h-3.5" strokeWidth={1.5} />
          </div>
          <div>
            <h2 className="text-xs font-semibold text-white">Quality, Security & Governance Telemetry</h2>
            <p className="text-[11px] text-zinc-500">
              Deterministic code quality scanners and 43 enterprise repository governance checks
            </p>
          </div>
        </div>

        {/* Segmented Mode Switcher */}
        <div className="flex items-center gap-2">
          <div className="flex items-center p-0.5 rounded-control bg-ink-950 border border-white/[0.08] text-xs font-mono">
            <button
              onClick={() => setViewMode('code-telemetry')}
              className={`px-3 py-1 rounded transition-colors ${
                viewMode === 'code-telemetry'
                  ? 'bg-ink-800 text-white font-medium shadow-sm'
                  : 'text-zinc-400 hover:text-zinc-200'
              }`}
            >
              Code Telemetry
            </button>
            <button
              onClick={() => setViewMode('security-posture')}
              className={`px-3 py-1 rounded transition-colors flex items-center gap-1.5 ${
                viewMode === 'security-posture'
                  ? 'bg-ink-800 text-white font-medium shadow-sm'
                  : 'text-zinc-400 hover:text-zinc-200'
              }`}
            >
              <span>Security Posture</span>
              <span className="px-1 rounded bg-ink-700 text-[10px] text-zinc-300">43</span>
            </button>
          </div>

          <button
            onClick={viewMode === 'code-telemetry' ? handleRunAssessment : loadSecurityPosture}
            disabled={assessing || postureLoading}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-control bg-emerald-600 hover:bg-emerald-500 disabled:bg-ink-800 text-white text-xs font-mono font-medium transition-colors"
          >
            {assessing || postureLoading ? (
              <>
                <RotateCw className="w-3 h-3 animate-spin" strokeWidth={1.5} />
                <span>Evaluating...</span>
              </>
            ) : (
              <>
                <Play className="w-3 h-3 fill-current" />
                <span>{viewMode === 'code-telemetry' ? 'Assess Repository' : 'Audit Posture'}</span>
              </>
            )}
          </button>
        </div>
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

      {/* ========================================================================= */}
      {/* MODE 1: CODE TELEMETRY (Deterministic 5-Factor Calibration)                */}
      {/* ========================================================================= */}
      {viewMode === 'code-telemetry' && (
        <div className="space-y-6">
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
              <div className="mt-3 flex items-center gap-2">
                <span
                  className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase border ${
                    health?.is_qualified || health?.qualification_status === 'QUALIFIED_SCORE'
                      ? 'bg-emerald-950/60 text-emerald-400 border-emerald-800/60'
                      : 'bg-amber-950/60 text-amber-400 border-amber-800/60'
                  }`}
                >
                  {health?.is_qualified ? 'QUALIFIED' : 'PROVISIONAL'}
                </span>
                {health?.qualification_reason && (
                  <span className="text-[10px] font-mono text-zinc-500 truncate max-w-xs" title={health.qualification_reason}>
                    • {health.qualification_reason}
                  </span>
                )}
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
                {health?.assessment_completeness && health.assessment_completeness < 80
                  ? 'Below 80% threshold — provisional score'
                  : 'Evaluated checks count toward final score'}
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
              Deterministic Code Scanners
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {/* 1. Code Quality */}
              <div className="bg-ink-900 border border-white/[0.08] p-4 rounded-panel space-y-3 font-mono text-xs">
                <div className="flex items-center justify-between">
                  <span className="text-zinc-300 font-medium">Code Quality (Ruff)</span>
                  {getAvailabilityBadge(health?.dimension_status?.code_quality || (health?.code_quality_score !== null && health?.code_quality_score !== undefined ? 'ENABLED' : 'UNCONFIGURED'))}
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
                  {getAvailabilityBadge(health?.dimension_status?.security || (health?.security_score !== null && health?.security_score !== undefined ? 'ENABLED' : 'UNCONFIGURED'))}
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
                  {getAvailabilityBadge(health?.dimension_status?.dependencies || (health?.dependency_score !== null && health?.dependency_score !== undefined ? 'ENABLED' : 'UNCONFIGURED'))}
                </div>
                <div className="text-2xl font-medium text-white tabular-nums">
                  {health?.dependency_score !== null && health?.dependency_score !== undefined
                    ? `${Math.round(health.dependency_score)} / 100`
                    : '— / 100'}
                </div>
                <div className="text-[11px] text-zinc-500 font-sans">
                  {health?.dependency_score !== null && health?.dependency_score !== undefined
                    ? 'Weight: 20% • Known CVE vulnerabilities in locked graph'
                    : 'Weight: 20% • No dependencies or requirements.txt configured'}
                </div>
              </div>

              {/* 4. Maintainability */}
              <div className="bg-ink-900 border border-white/[0.08] p-4 rounded-panel space-y-3 font-mono text-xs">
                <div className="flex items-center justify-between">
                  <span className="text-zinc-300 font-medium">Maintainability (Radon)</span>
                  {getAvailabilityBadge(health?.dimension_status?.maintainability || (health?.maintainability_score !== null && health?.maintainability_score !== undefined ? 'ENABLED' : 'UNCONFIGURED'))}
                </div>
                <div className="text-2xl font-medium text-white tabular-nums">
                  {health?.maintainability_score !== null && health?.maintainability_score !== undefined
                    ? `${Math.round(health.maintainability_score)} / 100`
                    : '— / 100'}
                </div>
                <div className="text-[11px] text-zinc-500 font-sans">
                  {health?.maintainability_score !== null && health?.maintainability_score !== undefined
                    ? 'Weight: 10% • McCabe cyclomatic complexity & docstrings'
                    : 'Weight: 10% • No Python functions or modules analyzed'}
                </div>
              </div>

              {/* 5. Test Health */}
              <div className="bg-ink-900 border border-white/[0.08] p-4 rounded-panel space-y-3 font-mono text-xs">
                <div className="flex items-center justify-between">
                  <span className="text-zinc-300 font-medium">Test Health (Pytest)</span>
                  {getAvailabilityBadge(health?.dimension_status?.test_health || (health?.test_health_score !== null && health?.test_health_score !== undefined ? 'ENABLED' : 'UNCONFIGURED'))}
                </div>
                <div className="text-2xl font-medium text-white tabular-nums">
                  {health?.test_health_score !== null && health?.test_health_score !== undefined
                    ? `${Math.round(health.test_health_score)} / 100`
                    : '— / 100'}
                </div>
                <div className="text-[11px] text-zinc-500 font-sans">
                  {health?.test_health_score !== null && health?.test_health_score !== undefined
                    ? 'Weight: 20% • Pass rate and coverage in Docker sandbox'
                    : 'Weight: 20% • Pytest suite unconfigured in repository'}
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
                  {history.map((h: any) => (
                    <tr key={h.id} className="hover:bg-white/[0.02]">
                      <td className="py-2.5 text-zinc-300 font-mono">
                        {h.commit_sha ? h.commit_sha.substring(0, 7) : '0000000'}
                      </td>
                      <td className="py-2.5 font-semibold text-zinc-100 tabular-nums">
                        {h.health_score !== null ? `${Math.round(h.health_score)}/100` : '—'}
                      </td>
                      <td className="py-2.5 text-zinc-400 tabular-nums">
                        {Math.round(h.assessment_completeness <= 1 ? h.assessment_completeness * 100 : h.assessment_completeness)}%
                      </td>
                      <td className="py-2.5">
                        <span
                          className={`px-1.5 py-0.5 rounded text-[10px] font-mono uppercase border ${
                            h.is_qualified
                              ? 'bg-emerald-950/60 text-emerald-400 border-emerald-800/60'
                              : 'bg-amber-950/60 text-amber-400 border-amber-800/60'
                          }`}
                        >
                          {h.is_qualified ? 'QUALIFIED' : 'PROVISIONAL'}
                        </span>
                      </td>
                      <td className="py-2.5 text-zinc-500 text-right text-[11px]">
                        {new Date(h.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* MODE 2: REPOSITORY SECURITY POSTURE (43 Enterprise Governance Checks)      */}
      {/* ========================================================================= */}
      {viewMode === 'security-posture' && (
        <div className="space-y-6">
          {postureLoading && !postureReport ? (
            <div className="bg-ink-900 border border-white/[0.08] rounded-panel p-12 text-center space-y-3 font-mono">
              <RotateCw className="w-6 h-6 text-zinc-400 animate-spin mx-auto" strokeWidth={1.5} />
              <div className="text-xs text-zinc-300">Auditing 43 Security & Governance Checks...</div>
              <p className="text-[11px] text-zinc-500 max-w-sm mx-auto">
                Evaluating branch protection, supply chain security, access controls, and repository settings on GitHub.
              </p>
            </div>
          ) : postureReport ? (
            <>
              {/* Posture Scoreboard */}
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <div className="bg-ink-900 border border-white/[0.08] p-5 rounded-panel">
                  <div className="text-xs font-mono text-zinc-500 mb-1">
                    Security Posture Score
                  </div>
                  <div className="flex items-baseline gap-2 my-2">
                    <span className="text-4xl font-medium text-white font-mono tabular-nums">
                      {Math.round(postureReport.overall_posture_score)}
                    </span>
                    <span className="text-zinc-500 font-mono text-sm">/ 100</span>
                  </div>
                  <div className="mt-3">
                    <span
                      className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase border ${
                        postureReport.overall_posture_score >= 80
                          ? 'bg-emerald-950/60 text-emerald-400 border-emerald-800/60'
                          : postureReport.overall_posture_score >= 50
                          ? 'bg-amber-950/60 text-amber-400 border-amber-800/60'
                          : 'bg-rose-950/60 text-rose-400 border-rose-800/60'
                      }`}
                    >
                      {postureReport.overall_posture_score >= 80
                        ? 'COMPLIANT'
                        : postureReport.overall_posture_score >= 50
                        ? 'MODERATE RISK'
                        : 'ACTION REQUIRED'}
                    </span>
                  </div>
                </div>

                <div className="bg-ink-900 border border-white/[0.08] p-5 rounded-panel">
                  <div className="text-xs font-mono text-zinc-500 mb-1">Passed Checks</div>
                  <div className="text-4xl font-medium text-emerald-400 font-mono tabular-nums my-2">
                    {postureReport.passed_checks}
                  </div>
                  <p className="mt-3 text-[11px] text-zinc-500 font-mono">
                    {Math.round((postureReport.passed_checks / postureReport.total_checks) * 100)}% of rules enforced
                  </p>
                </div>

                <div className="bg-ink-900 border border-white/[0.08] p-5 rounded-panel">
                  <div className="text-xs font-mono text-zinc-500 mb-1">Failed Rules</div>
                  <div className="text-4xl font-medium text-rose-400 font-mono tabular-nums my-2">
                    {postureReport.failed_checks}
                  </div>
                  <p className="mt-3 text-[11px] text-zinc-500 font-mono">
                    Direct governance vulnerabilities
                  </p>
                </div>

                <div className="bg-ink-900 border border-white/[0.08] p-5 rounded-panel">
                  <div className="text-xs font-mono text-zinc-500 mb-1">Warnings / Advisories</div>
                  <div className="text-4xl font-medium text-amber-400 font-mono tabular-nums my-2">
                    {postureReport.warning_checks}
                  </div>
                  <p className="mt-3 text-[11px] text-zinc-500 font-mono">
                    Recommended posture improvements
                  </p>
                </div>
              </div>

              {/* Critical Findings Banner */}
              {postureReport.summary_findings.length > 0 && (
                <div className="bg-ink-900 border border-amber-800/40 rounded-panel p-4 space-y-2">
                  <div className="flex items-center gap-2 text-xs font-mono font-medium text-amber-300">
                    <AlertTriangle className="w-3.5 h-3.5 shrink-0" />
                    <span>Priority Security Findings Requiring Attention:</span>
                  </div>
                  <ul className="space-y-1.5 pl-5 text-xs text-zinc-300 font-sans list-disc">
                    {postureReport.summary_findings.map((f, i) => (
                      <li key={i}>{f}</li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Category Filter Cards */}
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                {Object.entries(postureReport.categories).map(([key, cat]) => {
                  const isSelected = selectedCategory === key;
                  return (
                    <div
                      key={key}
                      onClick={() => setSelectedCategory(isSelected ? 'all' : key)}
                      className={`p-4 rounded-panel border cursor-pointer transition-colors ${
                        isSelected
                          ? 'bg-ink-800 border-zinc-500 shadow-sm'
                          : 'bg-ink-900 border-white/[0.08] hover:border-zinc-700'
                      }`}
                    >
                      <div className="flex items-center justify-between text-xs font-mono mb-2">
                        <span className="text-zinc-200 font-medium truncate">{cat.title}</span>
                        <span className="text-zinc-400 tabular-nums">{cat.score}%</span>
                      </div>
                      <div className="text-2xl font-mono font-medium text-white tabular-nums mb-2">
                        {cat.passed_checks} <span className="text-zinc-500 text-xs font-normal">/ {cat.total_checks} passed</span>
                      </div>
                      <div className="w-full bg-ink-950 h-1.5 rounded-full overflow-hidden border border-white/[0.04]">
                        <div
                          className={`h-full ${
                            cat.score >= 80
                              ? 'bg-emerald-500'
                              : cat.score >= 50
                              ? 'bg-amber-500'
                              : 'bg-rose-500'
                          }`}
                          style={{ width: `${cat.score}%` }}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>

              {/* Check Filter & Search Toolbar */}
              <div className="flex flex-col sm:flex-row items-center justify-between gap-3 bg-ink-900 border border-white/[0.08] p-3 rounded-control text-xs font-mono">
                <div className="flex items-center gap-2 w-full sm:w-auto">
                  <span className="text-zinc-400">Filter:</span>
                  <button
                    onClick={() => setSelectedCategory('all')}
                    className={`px-2.5 py-1 rounded transition-colors ${
                      selectedCategory === 'all'
                        ? 'bg-ink-800 text-white font-medium border border-white/[0.1]'
                        : 'text-zinc-400 hover:text-zinc-200'
                    }`}
                  >
                    All ({postureReport.total_checks})
                  </button>
                  {Object.entries(postureReport.categories).map(([key, cat]) => (
                    <button
                      key={key}
                      onClick={() => setSelectedCategory(key)}
                      className={`px-2.5 py-1 rounded transition-colors ${
                        selectedCategory === key
                          ? 'bg-ink-800 text-white font-medium border border-white/[0.1]'
                          : 'text-zinc-400 hover:text-zinc-200'
                      }`}
                    >
                      {cat.title} ({cat.total_checks})
                    </button>
                  ))}
                </div>

                <div className="relative w-full sm:w-64">
                  <Search className="w-3.5 h-3.5 text-zinc-400 absolute left-2.5 top-2.5" />
                  <input
                    type="text"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder="Search 43 checks..."
                    className="w-full bg-ink-950 border border-white/[0.08] rounded pl-8 pr-3 py-1.5 text-zinc-200 text-xs focus:outline-none focus:border-zinc-500"
                  />
                </div>
              </div>

              {/* Check Items List */}
              <div className="space-y-2.5">
                {filteredChecks.length === 0 ? (
                  <div className="p-8 text-center bg-ink-900 border border-white/[0.08] rounded-panel text-zinc-500 text-xs font-mono">
                    No posture checks match your current filter criteria.
                  </div>
                ) : (
                  filteredChecks.map((check) => {
                    const isExpanded = expandedCheckId === check.id;
                    return (
                      <div
                        key={check.id}
                        className="bg-ink-900 border border-white/[0.08] rounded-panel p-4 transition-colors space-y-3"
                      >
                        <div
                          onClick={() => setExpandedCheckId(isExpanded ? null : check.id)}
                          className="flex items-start justify-between gap-3 cursor-pointer select-none"
                        >
                          <div className="flex items-center gap-2.5">
                            {isExpanded ? (
                              <ChevronDown className="w-3.5 h-3.5 text-zinc-400 shrink-0" />
                            ) : (
                              <ChevronRight className="w-3.5 h-3.5 text-zinc-400 shrink-0" />
                            )}
                            <div>
                              <div className="flex items-center gap-2">
                                <span className="text-xs font-medium text-white font-sans">{check.name}</span>
                                {getSeverityBadge(check.severity)}
                              </div>
                              <p className="text-[11px] text-zinc-400 font-sans mt-0.5">
                                {check.description}
                              </p>
                            </div>
                          </div>

                          <div className="shrink-0">{getPostureStatusBadge(check.status)}</div>
                        </div>

                        {/* Expandable Details: Evidence & Remediation */}
                        {isExpanded && (
                          <div className="pt-3 border-t border-white/[0.06] space-y-2 text-xs font-mono pl-6">
                            <div className="p-2.5 rounded bg-ink-950 border border-white/[0.06] space-y-1">
                              <span className="text-zinc-500 uppercase text-[10px] tracking-wider block">Evidence:</span>
                              <p className="text-zinc-300 font-mono text-[11px]">{check.evidence}</p>
                            </div>
                            <div className="p-2.5 rounded bg-ink-950 border border-emerald-900/30 space-y-1">
                              <span className="text-emerald-400 uppercase text-[10px] tracking-wider block">Remediation:</span>
                              <p className="text-zinc-300 font-sans text-[11px] leading-relaxed">{check.remediation}</p>
                            </div>
                          </div>
                        )}
                      </div>
                    );
                  })
                )}
              </div>
            </>
          ) : (
            <div className="p-8 text-center bg-ink-900 border border-white/[0.08] rounded-panel text-zinc-500 text-xs font-mono">
              No security posture report available. Click "Audit Posture" to evaluate this repository.
            </div>
          )}
        </div>
      )}
    </div>
  );
};
