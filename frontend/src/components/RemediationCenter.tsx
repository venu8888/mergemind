import React, { useState } from 'react';
import {
  Sparkles,
  GitPullRequest,
  CheckCircle2,
  AlertTriangle,
  RotateCw,
  Terminal,
  FileDiff,
  Play,
  ExternalLink,
  Copy,
  Check,
  Info,
} from 'lucide-react';
import type {
  RemediationProposal,
} from '../types';
import {
  verifyRemediationProposal,
  createRemediationPullRequest,
} from '../services/api';

interface RemediationCenterProps {
  repositoryId?: string;
  proposals: RemediationProposal[];
  initialSelectedProposalId?: string | null;
  onRefresh: () => Promise<void>;
}

export const RemediationCenter: React.FC<RemediationCenterProps> = ({
  proposals,
  initialSelectedProposalId,
  onRefresh,
}) => {
  const [selectedProposalId, setSelectedProposalId] = useState<string | null>(
    initialSelectedProposalId || (proposals.length > 0 ? proposals[0].id : null)
  );
  const [isVerifying, setIsVerifying] = useState(false);
  const [isCreatingPR, setIsCreatingPR] = useState(false);
  const [copiedDiff, setCopiedDiff] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);

  const selectedProposal =
    proposals.find((p) => p.id === selectedProposalId) || (proposals.length > 0 ? proposals[0] : null);

  const handleVerify = async (proposalId: string) => {
    setIsVerifying(true);
    setActionError(null);
    setActionSuccess(null);
    try {
      const verification = await verifyRemediationProposal(proposalId);
      const isVerified = verification.verification_status === 'VERIFIED' || verification.is_verified;
      setActionSuccess(
        `Dual-run verification completed: ${verification.verification_status}. ${
          isVerified
            ? 'Candidate patch is confirmed to resolve target failure without regressions.'
            : 'Candidate patch failed verification.'
        }`
      );
      await onRefresh();
    } catch (err: any) {
      setActionError(err.response?.data?.detail || err.message || 'Verification failed');
    } finally {
      setIsVerifying(false);
    }
  };

  const handleCreatePR = async (proposalId: string) => {
    setIsCreatingPR(true);
    setActionError(null);
    setActionSuccess(null);
    try {
      const pr = await createRemediationPullRequest(proposalId);
      setActionSuccess(
        `Draft pull request created successfully! Branch: ${pr.branch_name}. PR #${pr.github_pr_number || pr.pr_number || ''}`
      );
      await onRefresh();
    } catch (err: any) {
      setActionError(err.response?.data?.detail || err.message || 'Draft PR creation failed');
    } finally {
      setIsCreatingPR(false);
    }
  };

  const handleCopyDiff = (diffText: string) => {
    navigator.clipboard.writeText(diffText);
    setCopiedDiff(true);
    setTimeout(() => setCopiedDiff(false), 2000);
  };

  const getProviderInfo = (provider?: string | null, model?: string | null) => {
    const isGemini =
      provider === 'llm' ||
      provider === 'gemini-llm' ||
      provider?.includes('gemini') ||
      model?.includes('gemini');
    if (isGemini) {
      return {
        label: 'Gemini 2.5 Flash (AI Remediation)',
        badgeClass: 'bg-indigo-950/80 text-indigo-300 border-indigo-700/60',
        isAi: true,
      };
    }
    return {
      label: 'Deterministic AST Engine',
      badgeClass: 'bg-slate-800 text-slate-300 border-slate-700',
      isAi: false,
    };
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'VERIFIED':
        return (
          <span className="px-2 py-0.5 rounded text-xs font-semibold bg-emerald-950/70 text-emerald-300 border border-emerald-800">
            VERIFIED
          </span>
        );
      case 'PENDING_VERIFICATION':
        return (
          <span className="px-2 py-0.5 rounded text-xs font-semibold bg-amber-950/70 text-amber-300 border border-amber-800">
            PENDING VERIFICATION
          </span>
        );
      case 'VERIFICATION_FAILED':
        return (
          <span className="px-2 py-0.5 rounded text-xs font-semibold bg-rose-950/70 text-rose-300 border border-rose-800">
            VERIFICATION FAILED
          </span>
        );
      case 'PR_CREATED':
        return (
          <span className="px-2 py-0.5 rounded text-xs font-semibold bg-blue-950/70 text-blue-300 border border-blue-800">
            DRAFT PR CREATED
          </span>
        );
      case 'MERGED':
        return (
          <span className="px-2 py-0.5 rounded text-xs font-semibold bg-purple-950/70 text-purple-300 border border-purple-800">
            MERGED
          </span>
        );
      default:
        return (
          <span className="px-2 py-0.5 rounded text-xs font-semibold bg-slate-800 text-slate-300 border border-slate-700">
            {status}
          </span>
        );
    }
  };

  const getRiskBadge = (risk?: string) => {
    switch (risk?.toUpperCase()) {
      case 'LOW':
        return (
          <span className="px-2 py-0.5 rounded text-xs font-semibold bg-emerald-950 text-emerald-400 border border-emerald-800">
            LOW RISK
          </span>
        );
      case 'MEDIUM':
        return (
          <span className="px-2 py-0.5 rounded text-xs font-semibold bg-amber-950 text-amber-400 border border-amber-800">
            MEDIUM RISK
          </span>
        );
      case 'HIGH':
        return (
          <span className="px-2 py-0.5 rounded text-xs font-semibold bg-rose-950 text-rose-400 border border-rose-800">
            HIGH RISK
          </span>
        );
      default:
        return (
          <span className="px-2 py-0.5 rounded text-xs font-semibold bg-slate-800 text-slate-400 border border-slate-700">
            {risk || 'LOW RISK'}
          </span>
        );
    }
  };

  const renderUnifiedDiff = (diffText: string) => {
    const lines = diffText.split('\n');
    return (
      <div className="font-mono text-xs overflow-x-auto p-4 bg-slate-950 rounded-lg border border-slate-800 max-h-[350px] leading-relaxed select-text">
        {lines.map((line, idx) => {
          let lineClass = 'text-slate-300';
          if (line.startsWith('+') && !line.startsWith('+++')) {
            lineClass = 'bg-emerald-950/50 text-emerald-300 font-medium px-1';
          } else if (line.startsWith('-') && !line.startsWith('---')) {
            lineClass = 'bg-rose-950/50 text-rose-300 font-medium px-1';
          } else if (line.startsWith('@@')) {
            lineClass = 'text-cyan-400 font-semibold my-1';
          } else if (line.startsWith('diff --git') || line.startsWith('index ')) {
            lineClass = 'text-slate-500 font-bold';
          }

          return (
            <div key={idx} className={`${lineClass} whitespace-pre`}>
              {line || ' '}
            </div>
          );
        })}
      </div>
    );
  };

  const activePR = selectedProposal?.pull_request || selectedProposal?.remediation_pr;
  const activeVerification = selectedProposal?.verification || selectedProposal?.verifications?.[0];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-slate-900 border border-slate-800 p-6 rounded-xl">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-lg bg-indigo-500/10 border border-indigo-500/20 text-indigo-400">
            <Sparkles className="w-6 h-6" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-white">AI-Assisted Remediation Center</h2>
            <p className="text-sm text-slate-400">
              Deterministic patch generation, isolated dual-sandbox verification, and automated Draft PR lifecycle.
            </p>
          </div>
        </div>

        <button
          onClick={onRefresh}
          className="inline-flex items-center gap-2 px-3 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium border border-slate-700 transition-colors"
        >
          <RotateCw className="w-3.5 h-3.5" />
          Refresh Proposals
        </button>
      </div>

      {/* Notifications */}
      {actionSuccess && (
        <div className="p-4 rounded-lg bg-emerald-950/40 border border-emerald-800/60 text-emerald-300 text-sm flex items-center justify-between">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
            <span>{actionSuccess}</span>
          </div>
          <button
            onClick={() => setActionSuccess(null)}
            className="text-xs text-emerald-400 hover:text-emerald-200"
          >
            Dismiss
          </button>
        </div>
      )}

      {actionError && (
        <div className="p-4 rounded-lg bg-rose-950/40 border border-rose-800/60 text-rose-300 text-sm flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0" />
            <span>{actionError}</span>
          </div>
          <button
            onClick={() => setActionError(null)}
            className="text-xs text-rose-400 hover:text-rose-200"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* System Invariant Alert */}
      <div className="p-4 rounded-xl bg-purple-950/30 border border-purple-800/40 text-purple-300 text-xs flex items-start gap-3">
        <Info className="w-4 h-4 text-purple-400 shrink-0 mt-0.5" />
        <div>
          <span className="font-semibold text-purple-200">Release Gate Invariant:</span> Every candidate remediation patch must complete a dual-sandbox run (reproducing failure on baseline, followed by 100% test pass on patched workspace without regressions) before a GitHub Draft PR can be generated. Remediation proposals do not affect repository health scores until merged.
        </div>
      </div>

      {/* Main Content Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Proposals List */}
        <div className="lg:col-span-4 space-y-3">
          <div className="text-xs font-semibold uppercase tracking-wider text-slate-400 px-1">
            Remediation Proposals ({proposals.length})
          </div>

          <div className="space-y-2.5 max-h-[750px] overflow-y-auto pr-1">
            {proposals.length > 0 ? (
              proposals.map((proposal) => {
                const isSelected = proposal.id === selectedProposal?.id;
                const explanation = proposal.explanation || proposal.description || proposal.rationale || proposal.title;
                return (
                  <div
                    key={proposal.id}
                    onClick={() => setSelectedProposalId(proposal.id)}
                    className={`p-4 rounded-xl cursor-pointer transition-all border ${
                      isSelected
                        ? 'bg-slate-800/90 border-indigo-500 shadow-md shadow-indigo-950/30'
                        : 'bg-slate-900/80 border-slate-800 hover:border-slate-700 hover:bg-slate-850'
                    }`}
                  >
                    <div className="flex items-start justify-between gap-2 mb-2">
                      <div className="text-sm font-semibold text-white truncate">
                        Proposal #{proposal.id.substring(0, 8)}
                      </div>
                      {getStatusBadge(proposal.status)}
                    </div>

                    <p className="text-xs text-slate-400 line-clamp-2 mb-3">
                      {explanation || 'No explanation provided.'}
                    </p>

                    <div className="flex items-center justify-between text-xs mb-2">
                      <span className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-medium border ${getProviderInfo(proposal.provider_name, proposal.model_identifier).badgeClass}`}>
                        {getProviderInfo(proposal.provider_name, proposal.model_identifier).isAi && (
                          <Sparkles className="w-2.5 h-2.5 text-indigo-400" />
                        )}
                        {getProviderInfo(proposal.provider_name, proposal.model_identifier).label}
                      </span>
                    </div>

                    <div className="flex items-center justify-between text-xs">
                      {getRiskBadge(proposal.risk_level)}
                      <span className="text-slate-500 font-mono">
                        {Math.round(proposal.confidence_score * 100)}% conf
                      </span>
                    </div>
                  </div>
                );
              })
            ) : (
              <div className="p-8 text-center bg-slate-900/40 border border-slate-800 rounded-xl text-slate-500 text-sm">
                No remediation proposals available yet. Ingest a CI failure and generate a proposal to begin.
              </div>
            )}
          </div>
        </div>

        {/* Right Column: Proposal Deep-Dive & Verification Console */}
        <div className="lg:col-span-8">
          {selectedProposal ? (
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 space-y-6">
              {/* Proposal Header */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-800">
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-lg font-bold text-white">
                      Remediation #{selectedProposal.id.substring(0, 8)}
                    </span>
                    {getStatusBadge(selectedProposal.status)}
                    {getRiskBadge(selectedProposal.risk_level)}
                  </div>
                  <div className="text-xs text-slate-400 font-mono flex items-center gap-2 mt-1 flex-wrap">
                    <span>Target Failure: {selectedProposal.ci_failure_id ? selectedProposal.ci_failure_id.substring(0, 8) : '—'}</span>
                    <span>•</span>
                    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-medium border ${getProviderInfo(selectedProposal.provider_name, selectedProposal.model_identifier).badgeClass}`}>
                      {getProviderInfo(selectedProposal.provider_name, selectedProposal.model_identifier).isAi && (
                        <Sparkles className="w-3 h-3 text-indigo-400" />
                      )}
                      {getProviderInfo(selectedProposal.provider_name, selectedProposal.model_identifier).label}
                    </span>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  {/* Verify Action */}
                  <button
                    onClick={() => handleVerify(selectedProposal.id)}
                    disabled={isVerifying || selectedProposal.status === 'VERIFIED' || selectedProposal.status === 'PR_CREATED'}
                    className="inline-flex items-center gap-2 px-3.5 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 disabled:bg-slate-800 disabled:text-slate-500 text-white font-medium text-xs transition-colors shadow-lg shadow-emerald-900/20"
                  >
                    {isVerifying ? (
                      <>
                        <RotateCw className="w-3.5 h-3.5 animate-spin" />
                        Verifying in Sandbox...
                      </>
                    ) : (
                      <>
                        <Play className="w-3.5 h-3.5 fill-current" />
                        Verify in Sandbox
                      </>
                    )}
                  </button>

                  {/* Create Draft PR Action */}
                  <button
                    onClick={() => handleCreatePR(selectedProposal.id)}
                    disabled={
                      isCreatingPR ||
                      selectedProposal.status !== 'VERIFIED' ||
                      Boolean(activePR)
                    }
                    className="inline-flex items-center gap-2 px-3.5 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 disabled:bg-slate-800 disabled:text-slate-500 text-white font-medium text-xs transition-colors shadow-lg shadow-indigo-900/20"
                  >
                    {isCreatingPR ? (
                      <>
                        <RotateCw className="w-3.5 h-3.5 animate-spin" />
                        Creating Draft PR...
                      </>
                    ) : (
                      <>
                        <GitPullRequest className="w-3.5 h-3.5" />
                        Create Draft PR
                      </>
                    )}
                  </button>
                </div>
              </div>

              {/* Linked Pull Request Banner if existing */}
              {activePR && (
                <div className="p-4 rounded-xl bg-blue-950/40 border border-blue-800/60 text-blue-200 text-xs flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <GitPullRequest className="w-5 h-5 text-blue-400" />
                    <div>
                      <div className="font-semibold text-white">
                        Draft Pull Request Active: #{activePR.github_pr_number || activePR.pr_number || 'Pending'}
                      </div>
                      <div className="font-mono text-blue-300">
                        Branch: {activePR.branch_name}
                      </div>
                    </div>
                  </div>
                  {(activePR.html_url || activePR.pr_url) && (
                    <a
                      href={activePR.html_url || activePR.pr_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-xs font-medium"
                    >
                      View on GitHub
                      <ExternalLink className="w-3 h-3" />
                    </a>
                  )}
                </div>
              )}

              {/* Remediation Explanation */}
              <div className="bg-slate-800/50 p-4 rounded-xl border border-slate-700/60 space-y-2">
                <div className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                  Remediation Explanation
                </div>
                <p className="text-sm text-slate-200 leading-relaxed">
                  {selectedProposal.explanation || selectedProposal.description || selectedProposal.rationale || 'Candidate patch synthesized based on localized fault location.'}
                </p>
              </div>

              {/* Interactive Diff Viewer */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <div className="text-xs font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-2">
                    <FileDiff className="w-4 h-4 text-slate-400" />
                    Synthesized Unified Diff
                  </div>
                  <button
                    onClick={() => handleCopyDiff(selectedProposal.patch_diff)}
                    className="inline-flex items-center gap-1.5 text-xs text-slate-400 hover:text-slate-200 transition-colors"
                  >
                    {copiedDiff ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                    {copiedDiff ? 'Copied' : 'Copy Diff'}
                  </button>
                </div>
                {renderUnifiedDiff(selectedProposal.patch_diff)}
              </div>

              {/* Verification Details Console */}
              {activeVerification && (
                <div className="bg-slate-950/80 border border-slate-800 rounded-xl p-5 space-y-4">
                  <div className="flex items-center justify-between">
                    <div className="text-xs font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-2">
                      <Terminal className="w-4 h-4 text-indigo-400" />
                      Sandbox Verification Evidence
                    </div>
                    <span
                      className={`px-2.5 py-0.5 rounded text-xs font-semibold ${
                        activeVerification.verification_status === 'VERIFIED' || activeVerification.is_verified
                          ? 'bg-emerald-950 text-emerald-300 border border-emerald-800'
                          : 'bg-rose-950 text-rose-300 border border-rose-800'
                      }`}
                    >
                      {activeVerification.verification_status}
                    </span>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
                    <div className="p-3 bg-slate-900 border border-slate-800 rounded-lg">
                      <span className="text-slate-400 block mb-1">Baseline Run</span>
                      <span className="font-semibold text-rose-400">
                        {activeVerification.baseline_passed ? 'PASSED' : 'REPRODUCED FAILURE'}
                      </span>
                    </div>

                    <div className="p-3 bg-slate-900 border border-slate-800 rounded-lg">
                      <span className="text-slate-400 block mb-1">Patched Run</span>
                      <span className="font-semibold text-emerald-400">
                        {activeVerification.patched_passed || activeVerification.is_verified ? 'ALL PASSED' : 'FAILED'}
                      </span>
                    </div>

                    <div className="p-3 bg-slate-900 border border-slate-800 rounded-lg">
                      <span className="text-slate-400 block mb-1">Regressions</span>
                      <span className="font-semibold text-slate-200">
                        {activeVerification.regressions_detected || (activeVerification.regressions_count && activeVerification.regressions_count > 0) ? 'DETECTED' : 'NONE DETECTED'}
                      </span>
                    </div>
                  </div>

                  {(activeVerification.execution_log || activeVerification.sandbox_logs) && (
                    <div>
                      <div className="text-xs text-slate-500 mb-1">Sandbox Execution Log:</div>
                      <pre className="text-xs font-mono text-slate-400 bg-slate-900 p-3 rounded border border-slate-800 max-h-[160px] overflow-y-auto whitespace-pre-wrap">
                        {activeVerification.execution_log || activeVerification.sandbox_logs}
                      </pre>
                    </div>
                  )}
                </div>
              )}
            </div>
          ) : (
            <div className="h-full flex items-center justify-center p-12 bg-slate-900 border border-slate-800 rounded-xl text-slate-500 text-sm">
              Select a remediation proposal to review diffs and run dual-sandbox verification.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
